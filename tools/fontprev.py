# -*- coding: utf-8 -*-
"""한글 글꼴 후보 비교 미리보기 (2026-10-23). 원본 칸 형식 그대로: 28×14(가로 고해상도), 화소 4비트 1(글자)~7(옅음)·8(바탕).
외곽선 글꼴을 칸의 8배(112×112)로 그린 뒤 28×14 로 줄여(가로 4·세로 8 상자 평균) 덮임 비율을 7단계로 나눈다.
세로 1~12행(원본 한자 잉크 범위)에 맞춘다. 결과 work/poc/fontprev.png — 게임처럼 어두운 바탕에 밝은 글자.
  python tools/fontprev.py"""
import os, struct, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = lambda *p: os.path.join(ROOT, 'work', *p)
TABLE = 0x06060508 - 0x06004000
CANDS = [
    ('맑은 고딕', r'C:\Windows\Fonts\malgun.ttf'),
    ('맑은 고딕 굵게', r'C:\Windows\Fonts\malgunbd.ttf'),
    ('나눔고딕', r'C:\claude\utils\font\nanum-gothic\NanumGothic.ttf'),
    ('나눔고딕 굵게', r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'),
]
SS = 8                                     # 세로 확대 배율(칸 14 → 112)

def render(fontpath, ch, size_px=12):
    """한 글자 → 원본 형식 196 B. size_px = 칸 안 잉크 목표 높이(세로 화소)."""
    big = 14 * SS
    f = ImageFont.truetype(fontpath, int(size_px * SS * 1.18))
    im = Image.new('L', (big, big), 0)
    d = ImageDraw.Draw(im)
    l, t, r, b = d.textbbox((0, 0), '가', font=f)          # 한글 기준 상자로 모든 글자 위치를 맞춤(부호 기준선 유지)
    ox = (big - (r - l)) // 2 - l
    oy = SS * 1 + (size_px * SS - (b - t)) // 2 - t
    d.text((ox, oy), ch, font=f, fill=255)
    a = np.asarray(im, np.float32) / 255.0
    cov = a.reshape(14, SS, 28, big // 28).mean(axis=(1, 3))   # 14×28 (세로 8·가로 4 평균)
    lvl = np.clip(np.rint(cov * 7), 0, 7).astype(np.uint8)
    nib = (8 - lvl).astype(np.uint8)                         # 7단계 → 1(진함)~7(옅음), 0 → 8(바탕)
    return bytes((nib[:, 0::2] << 4 | nib[:, 1::2]).reshape(-1))

def cell_from(b):
    g = np.frombuffer(b, np.uint8).reshape(14, 14)
    return np.stack([g >> 4, g & 15], -1).reshape(14, 28)

def orig_line(s):
    exe = open(W('disc1', '0.BIN'), 'rb').read(); font = open(W('disc1', 'SJIS2.KNJ'), 'rb').read()
    out = []
    b = s.encode('cp932')
    for i in range(0, len(b), 2):
        c = (b[i] << 8) | b[i + 1]; l, t = c >> 8, c & 0xFF
        r = (l - 0x81) if l <= 0x9F else (l - 0xC1)
        gi = struct.unpack_from('>H', exe, TABLE + 2 * (r * 188 + (t - 0x40 if t <= 0x7E else t - 0x41)))[0] - 1
        out.append(cell_from(font[gi * 196:(gi + 1) * 196]))
    return np.concatenate(out, 1)

def main():
    jp = '［マスター］：お疲れさま、けんたろう君。'
    kr = '［마스터］：수고했어，켄타로군．'
    rows = [orig_line(jp)]
    for name, path in CANDS:
        rows.append(np.concatenate([cell_from(render(path, ch)) for ch in kr], 1))
    wmax = max(r.shape[1] for r in rows)
    img = np.full((len(rows) * 20, wmax), 8, np.uint8)
    for k, r in enumerate(rows):
        img[k * 20 + 3:k * 20 + 17, :r.shape[1]] = r
    ink = (8 - np.clip(img, 1, 8)) / 7.0                    # 1 → 1.0
    bg = np.array([20, 24, 70], np.float32); fg = np.array([235, 235, 235], np.float32)
    rgb = (bg[None, None] * (1 - ink[..., None]) + fg[None, None] * ink[..., None]).astype(np.uint8)
    Image.fromarray(rgb).resize((wmax * 2, img.shape[0] * 4), Image.NEAREST).save(W('poc', 'fontprev.png'))
    sys.stdout.reconfigure(encoding='utf-8')
    print('줄 순서: 원본 /', ' / '.join(n for n, _ in CANDS))

if __name__ == '__main__':
    main()
