# -*- coding: utf-8 -*-
"""새턴 장면 파일(work/disc1/mes/NNN.bin, elfpak 해제본)에서 대사 조각 뽑기 (2026-10-23).
조각 = 4바이트 정렬 위치에서 시작해 NUL 로 끝나는 SJIS 문자열(전각만, 반각 ASCII 는 파일 이름 등이라 뺌).
pieces(d) → [(위치, SJIS 바이트열)]"""
import re

_SJ = re.compile(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc])+\x00')

def pieces(d):
    out = []
    for m in _SJ.finditer(d):
        a = m.start()
        if a % 4 == 0 and (a == 0 or d[a - 1] in (0, 9)):
            out.append((a, m.group()[:-1]))
    return out
