# -*- coding: utf-8 -*-
"""제목 로고 한글화 (2026-10-23). TITLE.DAT = 제목 화면 VDP1 스프라이트 그대로(424×152 8비트, 압축 없음, 색 은행 1 = CRAM 0x100~,
가로 고해상도라 화소 하나가 세로의 절반 폭). 사용자 스테이트 work/user_states/q183348.state(제목 화면) VDP1 명령표로 확인.
 - 「下級生」 큰 글자(y 57~131)만 지우고 «하급생»을 그린다: 빨강 채움 0xAF + 검정 테두리·그림자 0xDF + 가장자리 어두운 빨강.
   읽기 줄 「かきゅうせい」(y 41~55)와 «1997 PRODUCED BY ELF Co.» 는 그대로.
 - 미리보기 = 실제 배경(GP8 840)에 합성, 원본 | 새것 → work/poc/title_prev_<글꼴>.png
  python tools/titlegfx.py            # 후보 글꼴 전부 미리보기
  python tools/titlegfx.py bake <글꼴> # work/poc/TITLE.DAT"""
import io, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = lambda *p: os.path.join(ROOT, 'work', *p)
FONTS = {'myeongjo': r'C:\claude\utils\font\nanum-myeongjo\NanumMyeongjoExtraBold.ttf',
         'batang': r'C:\Windows\Fonts\HANBatangB.ttf',
         'yeonsung': r'C:\claude\utils\font\yeonsung\YeonSung-Regular.ttf'}
TEXT = '하급생'
SW, SH = 424, 152
BOX = (23, 57, 422, 136)                 # 큰 글자 영역(x0,y0,x1,y1) — 원본 잉크 범위(132~135 에 「生」 끝 조각)
RED, BLACK, EDGE, MID = 0xAF, 0xDF, 0xD7, 0xBB
SHEAR = 0.18                             # 원본처럼 오른쪽으로 기울임
READ_TEXT = '카큐세이'                    # 「かきゅうせい」(원제 읽기) — 거센소리 규칙
READ_FONT = r'C:\Windows\Fonts\HANBatangB.ttf'
READ_BOX = (44, 54, 160, 280)            # y0, y1, x0, x1 — 위아래 선 사이
READ_CORE, READ_MID, READ_LOW, READ_HALO = 0xDF, 0x70, 0x37, 0x09    # 원본 읽기 글자의 검정·회색·밝은 회색·흰 테두리

def palette():
    c = np.frombuffer(open(W('mem', 'titlelogo', 'CRAM.bin'), 'rb').read(), '<u2')[0x100:0x200].astype(int)
    return np.stack([(c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3], 1)

def text_mask(font, text, w_hi, h, fill=0.86, shear=SHEAR):
    """가로 고해상도 w_hi × h 덮임(0~1). 정사각 비율로 크게 그려 가로 화소(정사각의 절반 폭)마다 따로 평균 — 2배 늘림 없음."""
    K = 8; w = w_hi // 2
    big = Image.new('L', (w * K, h * K), 0); d = ImageDraw.Draw(big)
    size = h * K
    f = ImageFont.truetype(font, size)
    l, t, r, b = d.textbbox((0, 0), text, font=f)
    scale = min((w * K * fill) / (r - l), (h * K) / (b - t))
    f = ImageFont.truetype(font, int(size * scale))
    l, t, r, b = d.textbbox((0, 0), text, font=f)
    d.text(((w * K - (r - l)) // 2 - l, (h * K - (b - t)) // 2 - t), text, font=f, fill=255)
    if shear:
        big = big.transform(big.size, Image.AFFINE, (1, shear, -shear * h * K / 2, 0, 1, 0), Image.BICUBIC)
    return np.asarray(big, np.float32).reshape(h, K, w * 2, K // 2).mean((1, 3)) / 255

def dilate_hv(m, rx, ry):
    o = m.copy()
    for dy in range(-ry, ry + 1):
        for dx in range(-rx, rx + 1):
            o = o | np.roll(np.roll(m, dy, 0), dx, 1)
    return o

def dilate(m, r):
    o = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            o = np.maximum(o, np.roll(np.roll(m, dy, 0), dx, 1))
    return o

def build(font):
    a = np.frombuffer(open(W('disc1', 'TITLE.DAT'), 'rb').read(), np.uint8).reshape(SH, SW).copy()
    x0, y0, x1, y1 = BOX
    a[y0:y1, :] = 0                                     # 큰 글자 줄 전체 지움(이 줄엔 다른 그림 없음)
    w_hi, h = (x1 - x0) & ~1, y1 - y0 - 4
    cov = text_mask(font, TEXT, w_hi, h)
    fill = cov > 0.5
    edge = (cov > 0.2) & ~fill
    outline = dilate_hv(fill | edge, 2, 1) & ~fill & ~edge          # 가로 고해상도라 가로 반지름 2·세로 1
    shadow = np.roll(np.roll(dilate_hv(fill, 2, 1), 2, 0), 4, 1) & ~fill & ~edge & ~outline
    hi = np.zeros(cov.shape, np.uint8)
    hi[shadow | outline] = BLACK; hi[edge] = EDGE; hi[fill] = RED
    reg = a[y0 + 2:y0 + 2 + h, x0:x0 + w_hi]
    reg[...] = np.where(hi > 0, hi, reg)
    # 읽기 줄(위·아래 선 y41~43·54~55 는 그대로, 글자 y44~53 만): 진한 글자 + 흰 테두리 — 원본 색 단계만
    ry0, ry1, rx0, rx1 = READ_BOX
    a[ry0:ry1, rx0:rx1] = 0
    c = text_mask(READ_FONT, READ_TEXT, (rx1 - rx0) & ~1, ry1 - ry0, fill=0.8, shear=0)
    core = c > 0.45; mid = (c > 0.25) & ~core; low = (c > 0.1) & ~core & ~mid
    halo = dilate_hv(core | mid, 2, 1) & ~core & ~mid & ~low
    r = np.zeros(c.shape, np.uint8)
    r[halo] = READ_HALO; r[low] = READ_LOW; r[mid] = READ_MID; r[core] = READ_CORE
    a[ry0:ry1, rx0:rx0 + r.shape[1]] = r
    return a

def composite(spr, pal):
    import struct, re
    sys.path.insert(0, os.path.dirname(__file__)); import elfpak
    raw = elfpak.unpack(open(W('disc1', 'GP8.ARC'), 'rb').read()[0x3C56800:])[0]
    bg = np.array(Image.open(io.BytesIO(raw)).convert('RGB')).astype(int)
    img = bg.copy(); img[:SH, :SW][spr > 0] = pal[spr[spr > 0]]
    return img

def main():
    pal = palette()
    orig = np.frombuffer(open(W('disc1', 'TITLE.DAT'), 'rb').read(), np.uint8).reshape(SH, SW)
    for k, f in FONTS.items():
        new = build(f)
        img = np.concatenate([composite(orig, pal), np.full((4, 640, 3), 255), composite(new, pal)], 0).astype(np.uint8)
        Image.fromarray(img).resize((1280, img.shape[0] * 4), Image.NEAREST).save(W('poc', 'title_prev_%s.png' % k))
        print(W('poc', 'title_prev_%s.png' % k))

def bake(k):
    open(W('poc', 'TITLE.DAT'), 'wb').write(build(FONTS[k]).tobytes())
    print('work/poc/TITLE.DAT ←', k)

if __name__ == '__main__':
    bake(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == 'bake' else main()
