# -*- coding: utf-8 -*-
"""PC(DOS/V) 하급생 .MES 해제 — AI5V.EXE 0x87A6 루틴을 옮김(2026-10-23).
비트 스트림(MSB 먼저): 1 → 글자 8비트 / 0 → 위치 12비트(0 이면 끝) + 길이 4비트(+2).
링 4096, 쓰기 시작 1. 링 초기값은 루틴이 지우지 않는다(0 으로 둠 — 앞 파일 찌꺼기를 참조하는지 검사: 'uninit').
  python tools/pcmes.py <입력 폴더> <출력 폴더>"""
import os, sys

def unpack(d):
    pos = 0; nbits = len(d) * 8
    def rd(n):
        nonlocal pos
        v = 0
        for _ in range(n):
            v = (v << 1) | ((d[pos >> 3] >> (7 - (pos & 7))) & 1); pos += 1
        return v
    ring = bytearray(4096); written = bytearray(4096); r = 1; out = bytearray(); uninit = 0
    while True:
        if rd(1):
            c = rd(8); out.append(c); ring[r] = c; written[r] = 1; r = (r + 1) & 0xFFF
        else:
            p = rd(12)
            if p == 0:
                break
            n = rd(4) + 2
            for _ in range(n):
                uninit += not written[p]
                c = ring[p]; p = (p + 1) & 0xFFF
                out.append(c); ring[r] = c; written[r] = 1; r = (r + 1) & 0xFFF
    return bytes(out), nbits - pos, uninit

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]; os.makedirs(dst, exist_ok=True)
    left = []; un = []
    for n in sorted(os.listdir(src)):
        if n.upper().endswith('.MES'):
            o, rest, u = unpack(open(os.path.join(src, n), 'rb').read())
            open(os.path.join(dst, n), 'wb').write(o); left.append(rest); un.append((u, n))
    print(len(left), 'files, leftover bits max', max(left), 'uninit refs', sum(u for u, _ in un), max(un))
