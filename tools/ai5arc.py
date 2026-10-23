# -*- coding: utf-8 -*-
"""PC(DOS/V) 하급생 AI5 ARC 읽기 (읽기 전용).
머리 16 B('KAKYUSEI.ARC\x1aelf') 뒤 20 B 항목 × N. 항목 바이트는 x = rol1(b ^ 0xAA) 로 풀고
  이름 14 B(NUL 채움) + 위치 u32LE(파일 위치 그대로 — 목차 끝과 첫 파일 사이 1바이트 틈) + 크기 u16LE.
2026-10-23 확인: 위치[n+1] = 위치[n] + 크기[n], 마지막 끝 = 파일 크기(KAKYUHAN.ARC).
  python tools/ai5arc.py <ARC> [꺼낼 폴더]"""
import os, struct, sys

def dec(b):
    return bytes((((x ^ 0xAA) << 1) | ((x ^ 0xAA) >> 7)) & 0xFF for x in b)

def entries(d):
    out = []; p = 16
    while p + 20 <= len(d):
        e = dec(d[p:p + 20])
        name = e[:14].split(b'\0')[0]
        if not name or not all(32 < c < 127 for c in name):
            break
        off, size = struct.unpack_from('<IH', e, 14)
        out.append((name.decode(), off, size)); p += 20
    return out, p

if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    ents, end = entries(d)
    bad = sum(1 for i in range(len(ents) - 1) if ents[i][1] + ents[i][2] != ents[i + 1][1])
    print('항목', len(ents), '목차 끝', hex(end), '첫 위치', hex(ents[0][1]), '사슬 어긋남', bad,
          '마지막 끝', hex(ents[-1][1] + ents[-1][2]), '파일 크기', hex(len(d)))
    if len(sys.argv) > 2:
        os.makedirs(sys.argv[2], exist_ok=True)
        for n, o, s in ents:
            open(os.path.join(sys.argv[2], n), 'wb').write(d[o:o + s])
