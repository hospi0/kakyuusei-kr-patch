# -*- coding: utf-8 -*-
"""elfpak 해제. 머리 'elfpak\x1a\0' + u32LE «압축 본문 크기» + Okumura LZSS(링 4096·시작 0xFEE·0 채움·12비트 위치+4비트 길이(+3)).

u32 는 원래 크기가 아니라 압축 본문 길이다 — 입력을 다 쓰면 끝(2026-10-23 확인)."""
import struct, sys

def unpack(d, ring_init=0xFEE, fill=0x00, lsb=True):
    assert d[:8] == b'elfpak\x1a\x00'
    csize = struct.unpack_from('<I', d, 8)[0]; end = 12 + csize
    ring = bytearray([fill]) * 4096; r = ring_init
    out = bytearray(); p = 12; flags = 0; nb = 0
    while p < end:
        if nb == 0:
            flags = d[p]; p += 1; nb = 8
        bit = (flags & 1) if lsb else (flags >> 7) & 1
        flags = (flags >> 1) if lsb else (flags << 1) & 0xFF
        nb -= 1
        if bit:
            c = d[p]; p += 1; out.append(c); ring[r] = c; r = (r + 1) & 0xFFF
        else:
            b0, b1 = d[p], d[p + 1]; p += 2
            pos = b0 | ((b1 & 0xF0) << 4); ln = (b1 & 0x0F) + 3
            for k in range(ln):
                c = ring[(pos + k) & 0xFFF]; out.append(c); ring[r] = c; r = (r + 1) & 0xFFF
    assert p == end, (p, end)
    return bytes(out), p

def pack(data, max_chain=256):
    """unpack 과 같은 규칙으로 압축(탐욕 + 해시 사슬). 결과를 unpack 으로 되풀어 같은지 반드시 확인한다.
    위치 = 링 위치((0xFEE + 출력 위치) & 0xFFF), 길이 3~18, 거리는 4096-18 이하만 쓴다."""
    n = len(data); out = bytearray(); i = 0
    heads = {}
    MAXD = 4096 - 18
    flags_at = None; nbits = 8
    def emit_flag():
        nonlocal flags_at, nbits
        if nbits == 8:
            flags_at = len(out); out.append(0); nbits = 0
    while i < n:
        best_len = 0; best_src = 0
        if i + 3 <= n:
            key = data[i:i + 3]
            chain = heads.get(key, [])
            cnt = 0
            for s in reversed(chain):
                if i - s > MAXD:
                    break
                l = 3
                lim = min(18, n - i)
                while l < lim and data[s + l] == data[i + l]:
                    l += 1
                if l > best_len:
                    best_len, best_src = l, s
                    if l == 18:
                        break
                cnt += 1
                if cnt >= max_chain:
                    break
        emit_flag()
        if best_len >= 3:
            pos = (0xFEE + best_src) & 0xFFF
            out.append(pos & 0xFF); out.append(((pos >> 4) & 0xF0) | (best_len - 3))
            step = best_len
        else:
            out[flags_at] |= 1 << nbits
            out.append(data[i]); step = 1
        nbits += 1
        for k in range(i, i + step):
            if k + 3 <= n:
                heads.setdefault(data[k:k + 3], []).append(k)
        i += step
    body = bytes(out)
    blob = b'elfpak\x1a\x00' + struct.pack('<I', len(body)) + body
    assert unpack(blob)[0] == bytes(data), '재압축 되풀기 불일치'
    return blob

def pack_opt(data, max_chain=512):
    """pack 과 같은 형식, 최적 파싱(뒤에서부터 비트 수 최소 DP: 리터럴 9비트·참조 17비트). 2026-10-23 한글 MES.ARC 용."""
    n = len(data); MAXD = 4096 - 18
    best = [(0, 0)] * n                    # 위치마다 (가장 긴 길이, 원본 위치)
    heads = {}
    for i in range(n):
        bl = bs = 0
        if i + 3 <= n:
            key = data[i:i + 3]; chain = heads.get(key)
            if chain:
                lim = min(18, n - i); cnt = 0
                for s in reversed(chain):
                    if i - s > MAXD: break
                    l = 3
                    while l < lim and data[s + l] == data[i + l]: l += 1
                    if l > bl:
                        bl, bs = l, s
                        if l == lim: break
                    cnt += 1
                    if cnt >= max_chain: break
                chain.append(i)
            else:
                heads[key] = [i]
        best[i] = (bl, bs)
    cost = [0] * (n + 1); choice = [0] * n
    for i in range(n - 1, -1, -1):
        c = cost[i + 1] + 9; ch = 0
        bl = best[i][0]
        for l in range(3, bl + 1):
            v = cost[i + l] + 17
            if v < c: c, ch = v, l
        cost[i] = c; choice[i] = ch
    out = bytearray(); i = 0; nbits = 8; flags_at = 0
    while i < n:
        if nbits == 8:
            flags_at = len(out); out.append(0); nbits = 0
        l = choice[i]
        if l:
            pos = (0xFEE + best[i][1]) & 0xFFF
            out.append(pos & 0xFF); out.append(((pos >> 4) & 0xF0) | (l - 3)); i += l
        else:
            out[flags_at] |= 1 << nbits; out.append(data[i]); i += 1
        nbits += 1
    body = bytes(out)
    blob = b'elfpak\x1a\x00' + struct.pack('<I', len(body)) + body
    assert unpack(blob)[0] == bytes(data), '재압축 되풀기 불일치'
    return blob

if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    out, used = unpack(d)
    print(len(out), used)
