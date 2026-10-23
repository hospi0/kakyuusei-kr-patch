# -*- coding: utf-8 -*-
"""PC 한글판(1999) 글자 대응 (2026-10-23 확인).
엔진(AI5V.EXE 0x2D9E): 전각 칸 f = (선행-0x81, 7 이상이면 -3)*189 + (후행-0x40), 189 이상 후행·0x1269 이상은 0번.
JISHAN.FNT 전각 칸 1134 부터 KS X 1001 한글이 94칸씩 완성형 순서(가=1134 — 「게」1185·「도」1624 로 확인). 비어 있는 칸도 있다.
decode(SJIS 바이트열) → 한글판 화면 문자열(한글 칸이 아니면 SJIS 그대로)."""
import os
import numpy as np

_FONT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work', 'pc_font_full.npy')
_INK = None

def fidx(L, T):
    ch = L - 0x81
    if ch >= 7:
        ch -= 3
    if T - 0x40 >= 0xBD:
        return 0
    f = ch * 189 + (T - 0x40)
    return f if f < 0x1269 else 0

def sjis_to_kr(b):
    global _INK
    k = fidx(b[0], b[1]) - 1134
    if 0 <= k < 2350:
        if _INK is None:
            _INK = np.load(_FONT).reshape(-1, 256).sum(1)
        if _INK[1134 + k] == 0:
            return '□'          # 글꼴에 그림이 없는 칸
        return bytes([0xB0 + k // 94, 0xA1 + k % 94]).decode('cp949')
    return None

# 이름 뒤 조사 선택 코드(한글판이 이름 받침에 따라 고른다, 2026-10-23 글꼴 칸 그림으로 확인)
PARTICLE = {bytes([0x83, 0x98]): '{이가}', bytes([0x83, 0x99]): '{을를}', bytes([0x83, 0x9a]): '{아야}',
            bytes([0x83, 0x9b]): '{은는}', bytes([0x83, 0x9c]): '{와과}', bytes([0x83, 0x9d]): '{이}'}

def decode(raw):
    out = []; i = 0
    while i < len(raw):
        if raw[i:i + 3] == b'{N}':
            out.append('{N}'); i += 3; continue
        b = raw[i:i + 2]
        if b in PARTICLE:
            out.append(PARTICLE[b]); i += 2; continue
        k = sjis_to_kr(b) if len(b) == 2 else None
        out.append(k if k else b.decode('cp932', 'replace')); i += 2
    return ''.join(out)
