# -*- coding: utf-8 -*-
"""PC 하급생 MES(해제본) 글줄 뽑기 (2026-10-23).
머리 u16 = 스크립트 시작 위치, [2, 시작) = 2바이트 글자표(최대 48칸, 빈도순).
본문 글자 = 0xD0+i → 표[i] / 선행 0x61~0x7F·0xC0~0xCF → +0x20 한 SJIS 2바이트. 그 밖은 AI5 명령(의미 미확정).
  python tools/pctext.py <MES> [개수]"""
import sys

def table(d):
    start = int.from_bytes(d[:2], 'little')
    return [d[2 + 2 * i:4 + 2 * i] for i in range((start - 2) // 2)], start

def runs(d, minlen=2):
    tbl, start = table(d); out = []; cur = bytearray(); at = None; i = start
    def flush():
        nonlocal cur, at
        if len(cur) >= 2 * minlen: out.append((at, bytes(cur)))
        cur = bytearray(); at = None
    while i < len(d):
        b = d[i]
        if b >= 0xD0 and b - 0xD0 < len(tbl):
            if at is None: at = i
            cur += tbl[b - 0xD0]; i += 1
        elif (0x61 <= b <= 0x7F or 0xC0 <= b <= 0xCF) and i + 1 < len(d) and 0x40 <= d[i + 1] <= 0xFC:   # 한글판은 후행 0x7F 도 글꼴 칸(엔진 식 T-0x40)
            if at is None: at = i
            cur += bytes([b + 0x20, d[i + 1]]); i += 2
        else:
            flush(); i += 1
    flush()
    return out

NAME = b'3'   # 주인공 이름 출력(01M 에서 확인)

def lines(d):
    """글자 조각을 이름 명령(13 33 03)으로 이어 붙인 줄 목록 [(위치, SJIS 바이트열)] — 이름 자리는 b'{N}'."""
    rs = runs(d, minlen=1); out = []
    for at, s in rs:
        if out:
            pat, prev = out[-1]
            end = pat + _srclen(d, pat, prev)
            if d[end:at] == NAME:
                out[-1] = (pat, prev + b'{N}' + s); continue
        out.append((at, s))
    return out

def _srclen(d, at, s):
    """해제본에서 at 부터 글자 토큰이 차지한 바이트 수(이름 명령 포함)."""
    i = at; n = 0; tbl, _ = table(d)
    while n < len(s):
        if s[n:n + 3] == b'{N}':
            i += 3; n += 3; continue
        b = d[i]
        if b >= 0xD0 and b - 0xD0 < len(tbl):
            i += 1
        else:
            i += 2
        n += 2
    return i - at

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    for at, s in lines(open(sys.argv[1], 'rb').read())[:int(sys.argv[2]) if len(sys.argv) > 2 else 40]:
        print(hex(at), s.decode('cp932', 'replace'))
