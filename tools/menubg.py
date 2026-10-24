# -*- coding: utf-8 -*-
r"""메인 메뉴 배경(GP8.ARC 422번, 640×224 8비트 BMP, 가로 고해상도 — 화면에선 세로 2배) 한글화 (2026-10-24 사용자)
  ① 위 팻말 「下級生」(흰 판 안 x 259~380, y 2~27) → «하급생»(제목 로고와 같은 함초롬바탕 굵게, 원본 빨강)
     지우기: 빨강 계열 화소만, 같은 줄의 가장 가까운 «빨강 아닌» 판 화소로(판은 매끈한 밝은 판)
  ② 칠판 왼쪽 아래(메뉴 마지막 버튼 아래 y 164 ~ 칠판 안 아래 끝 187)에 두 줄 작은 분필 글씨:
     «제작 : hospi» / «번역 : 퇴사는 나의 꿈» — 화면 비율(세로 2배)로 그려 세로 절반으로 줄인 덮임 비율로 바탕색과 섞어 팔레트 최근접.
  python tools/menubg.py          → work/poc/menu_prev.png(위 원본 / 아래 새것, 화면 비율 2배)
  python tools/menubg.py bake     → work/poc/menu_422.bmp (GP8 422번 새 BMP — 다시 넣기는 빌드 연결 후)"""
import io, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = lambda *p: os.path.join(ROOT, 'work', *p)
sys.path.insert(0, os.path.dirname(__file__))
import elfpak  # noqa: E402

GP8_NO = 422
REC = 0x59070                                     # 디스크 1 0.BIN GP8 위치표 422번(섹터·크기, BE) = 807번 칸 0x5A27C − 12×385
PLATE = (259, 2, 380, 27)
PLATE_TEXT = '하 급 생'                     # 원본 「下 級 生」처럼 글자 사이를 띄움
PLATE_FONT = r'C:\Windows\Fonts\HANBatangB.ttf'
CREDIT = ['제작 : hospi', '번역 : 퇴사는 나의 꿈']
CREDIT_FONT = r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'
CREDIT_X, CREDIT_Y0, CREDIT_PITCH, CREDIT_H = 64, 330, 21, 18    # 화면 비율(세로 2배) 좌표·글자 높이(px) — 13px 은 뭉개짐(사용자), 9줄 높이로
CHALK = np.array([226, 230, 220])
SS = 4


def load_raw():
    d = open(W('disc1', 'GP8.ARC'), 'rb').read()
    import re
    o = [m.start() for m in re.finditer(rb'elfpak\x1a\x00', d)][GP8_NO]
    return elfpak.unpack(d[o:])[0]


def split(raw):
    im = Image.open(io.BytesIO(raw))
    pal = np.array(im.getpalette()[:768], int).reshape(256, 3)
    return np.array(im), pal


def text_cov(text, font, h_disp, width_max=None, stroke=0):
    """화면 비율 높이 h_disp 로 그린 덮임(0~1) → 세로 절반(데이터 줄)."""
    f = ImageFont.truetype(font, 100 * SS)
    bb = f.getbbox('한'); scale = h_disp * SS / (bb[3] - bb[1])
    f = ImageFont.truetype(font, max(8, int(100 * SS * scale)))
    top = f.getbbox('한')[1]
    w = int(f.getlength(text)) + SS * 4 + stroke * SS * 2
    im = Image.new('L', (w, h_disp * SS + SS * 4 + stroke * SS * 2), 0)
    ImageDraw.Draw(im).text((stroke * SS, -top + stroke * SS), text, font=f, fill=255, stroke_width=stroke * SS, stroke_fill=255)
    ww = max(1, round(w / SS)); hh = max(1, round(im.height / SS / 2))
    if width_max and ww > width_max: ww = width_max
    return np.array(im.resize((ww, hh), Image.BOX), float) / 255


def nearest(pal, used, rgb):
    c = pal[used]; return used[int(np.argmin(((c - rgb) ** 2).sum(1)))]


def make(a, pal):
    out = a.copy(); used = np.array(sorted(set(a.ravel().tolist())))
    rgb = pal[a]
    # ① 팻말
    x0, y0, x1, y1 = PLATE
    sub = rgb[y0:y1, x0:x1].astype(int)
    red = (sub[..., 0] - sub[..., 1] > 14) & (sub[..., 0] - sub[..., 2] > 8)   # 옅은 분홍 번짐까지(판은 회백색)
    ink = sub[(sub[..., 0] - sub[..., 1] > 40)]; red_rgb = ink[np.argmax(ink[:, 0] - ink[:, 1])] if len(ink) else np.array([230, 20, 30])
    for yy in range(y1 - y0):
        good = np.nonzero(~red[yy])[0]
        for xx in np.nonzero(red[yy])[0]:
            j = good[np.argmin(np.abs(good - xx))]
            out[y0 + yy, x0 + xx] = a[y0 + yy, x0 + j]
    bg = pal[out].astype(float)
    cov = text_cov(PLATE_TEXT, PLATE_FONT, 2 * 14, stroke=1)   # 굵게(사용자)          # 원본 글자 높이 ≈ 데이터 15줄 — 판 테두리 안에 들게 14줄
    ch, cw = cov.shape
    ox = (x0 + x1) // 2 - cw // 2; oy = (y0 + y1) // 2 - ch // 2 + 2   # 조금 아래로(사용자)
    for r, c in zip(*np.nonzero(cov > 0.08)):
        y, x = oy + r, ox + c
        m = min(1, cov[r, c] * 1.3)
        out[y, x] = nearest(pal, used, bg[y, x] * (1 - m) + red_rgb * m)
    # ② 크레딧
    bg = pal[out].astype(float)
    for i, line in enumerate(CREDIT):
        cov = text_cov(line, CREDIT_FONT, CREDIT_H)
        oy = (CREDIT_Y0 + i * CREDIT_PITCH) // 2
        for r, c in zip(*np.nonzero(cov > 0.28)):
            y, x = oy + r, CREDIT_X + c
            m = 1.0 if cov[r, c] > 0.5 else 0.5                     # 두 단계만(반투명 섞임이 많으면 뭉개짐)
            out[y, x] = nearest(pal, used, bg[y, x] * (1 - m) + CHALK * m)
    return out


def to_bmp(raw, idx):
    im = Image.open(io.BytesIO(raw)); new = Image.fromarray(idx.astype(np.uint8)); new.putpalette(im.getpalette())
    b = io.BytesIO(); new.save(b, 'BMP'); b = b.getvalue()
    off = int.from_bytes(raw[10:14], 'little'); assert len(b) == len(raw) and b[10:14] == raw[10:14]
    return raw[:off] + b[off:]                      # 원본 머리·팔레트 그대로, 화소만(PIL 은 해상도·색 개수 칸을 바꿔 씀)


def preview():
    raw = load_raw(); a, pal = split(raw); new = make(a, pal)
    top = Image.fromarray(pal[a].astype(np.uint8)); bot = Image.fromarray(pal[new].astype(np.uint8))
    cv = Image.new('RGB', (640, 448 * 2 + 8), (255, 255, 255))
    cv.paste(top.resize((640, 448), Image.NEAREST), (0, 0)); cv.paste(bot.resize((640, 448), Image.NEAREST), (0, 456))
    os.makedirs(W('poc'), exist_ok=True)
    cv.resize((1280, cv.height * 2), Image.NEAREST).save(W('poc', 'menu_prev.png'))
    return new


if __name__ == '__main__':
    if sys.argv[1:] == ['bake']:
        # namegfx bake 가 만든 work/poc/GP8.ARC·0.BIN 위에 422번을 덮는다(namegfx bake 다음에 실행)
        import re, struct
        raw = load_raw(); a, pal = split(raw); bmp = to_bmp(raw, make(a, pal))
        open(W('poc', 'menu_422.bmp'), 'wb').write(bmp)
        gp8 = bytearray(open(W('poc', 'GP8.ARC'), 'rb').read())
        offs = [m.start() for m in re.finditer(rb'elfpak\x1a\x00', gp8)]
        o, nxt = offs[GP8_NO], offs[GP8_NO + 1]
        blob = elfpak.pack_opt(bmp); assert elfpak.unpack(blob)[0] == bmp
        assert len(blob) <= nxt - o, ('422 재압축이 자리를 넘음', len(blob), nxt - o)
        gp8[o:nxt] = blob + bytes(nxt - o - len(blob))
        open(W('poc', 'GP8.ARC'), 'wb').write(gp8)
        exe = bytearray(open(W('poc', '0.BIN'), 'rb').read())
        assert struct.unpack_from('>I', exe, REC)[0] == o // 2048
        struct.pack_into('>I', exe, REC + 4, len(blob))
        open(W('poc', '0.BIN'), 'wb').write(exe)
        print('422 재압축 %d / 자리 %d B · 0.BIN 위치표 크기 갱신' % (len(blob), nxt - o))
    else:
        preview()
