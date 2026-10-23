# -*- coding: utf-8 -*-
"""이름 입력 화면 그림 한글화 (2026-10-23). 결과는 work/poc/ 에만 쓴다(디스크 아님).
 1쪽 = GP8.ARC 807번(640×224 8비트 BMP): 글자판 90칸 + 머리말 + 버튼 4개 + 「名前：けんたろう」
 2쪽 = BMP.ARC 0x288800 가타카나 조각(480×100 8비트 BMP, 파일 줄 순서가 화면과 위아래 반대): 글자판 75칸(+빈 15칸)
 글자판 칸: 줄 y=45+16k(807 기준), 묶음 x=93/261/430, 글자 간격 23.75, 폭 22, 높이 12 (가로 고해상도라 폭이 2배).
 지우기: 정한 상자 안에서 «밝고 채도 낮은» 화소(+1화소 팽창)만 그 상자의 나머지 바탕 평균으로 메움.
 그리기: 나눔고딕 굵게를 8배로 그려 줄인 덮임 비율로 바탕↔글자색을 섞고 원본 팔레트에서 가장 가까운 색.
 출력: name_807.bmp·name_kana.bmp(원래 형식 그대로), 미리보기 name_p1.png·name_p2.png(위 원본 / 아래 새것, 2배)."""
import io, os, re, struct, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
import elfpak, poc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = lambda *p: os.path.join(ROOT, 'work', *p)
KFONT = r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'
ROW_Y = [45, 61, 77, 93, 109, 126]
GRP_X = [93, 261, 430]
PITCH, CW, CH = 23.75, 22, 12
KANA_BMP = 0x288800
HIRA_BMP = 0x1DB000                              # 「かな」로 돌아갈 때 덮는 히라가나 조각(같은 480×100)
HEADER = '주인공의 이름을 입력해 주세요'
BUTTONS = {(433, 142, 500, 160): '1쪽', (505, 142, 572, 160): '2쪽',
           (433, 164, 500, 182): '지우기', (505, 164, 572, 182): '결정'}
LABEL = '이름'                                  # 「名前」 자리, 「：」는 원본 그대로
NAME = '켄타로'

def load_807():
    d = open(W('disc1', 'GP8.ARC'), 'rb').read()
    o = [m.start() for m in re.finditer(rb'elfpak\x1a\x00', d)][807]
    return elfpak.unpack(d[o:])[0]

def load_kana(at=KANA_BMP):
    d = open(W('disc1', 'BMP.ARC'), 'rb').read()
    sz = struct.unpack_from('<I', d, at + 2)[0]
    return d[at:at + sz]

def bmp_split(raw):
    off = struct.unpack_from('<I', raw, 10)[0]
    w, h = struct.unpack_from('<ii', raw, 18)
    pal = np.frombuffer(raw[54:54 + 1024], np.uint8).reshape(256, 4)[:, [2, 1, 0]].astype(int)
    stride = (w + 3) & ~3
    rows = np.frombuffer(raw[off:off + stride * abs(h)], np.uint8).reshape(abs(h), stride)
    return off, w, abs(h), stride, pal, rows

def to_view(raw):
    """화면 방향(위가 위) 8비트 배열 — PIL 이 BMP 머리 규칙대로 뒤집어 준다."""
    return np.array(Image.open(io.BytesIO(raw)))

def from_view(raw, view):
    """화면 방향 배열을 원래 파일 줄 순서로 되돌려 같은 크기 BMP 바이트로."""
    off, w, h, stride, pal, rows = bmp_split(raw)
    filerows = view[::-1] if struct.unpack_from('<i', raw, 22)[0] > 0 else view
    buf = bytearray(raw)
    for y in range(h):
        buf[off + y * stride:off + y * stride + w] = filerows[y].tobytes()
    out = bytes(buf)
    assert np.array_equal(to_view(out), view)
    return out

def nearest(pal, rgb):
    d = ((pal[None, :, :] - rgb[:, None, :]) ** 2).sum(2)
    return d.argmin(1).astype(np.uint8)

def cov_text(text, cw, ch, pitch):
    """글자열 덮임(세로 ch, 가로 고해상도). 글자마다 정사각 비율로 그려 가로 2배."""
    S = 8
    f = ImageFont.truetype(KFONT, int(ch * S * 1.18))
    lw = int(round(cw / 2))
    xs = []; x = 0.0
    for c in text:                                   # 띄어쓰기는 반 칸
        xs.append(x); x += pitch * (0.5 if c in ' 　' else 1.0)
    total = int(round(xs[-1] + cw))
    out = np.zeros((ch, total), np.float32)
    for k, c in enumerate(text):
        if c in ' 　':
            continue
        big = Image.new('L', (lw * S, ch * S), 0); dr = ImageDraw.Draw(big)
        l, t, r, b = dr.textbbox((0, 0), '가', font=f)
        cl, ct, cr, cb = dr.textbbox((0, 0), c, font=f)
        dr.text(((lw * S - (cr - cl)) // 2 - cl, (ch * S - (b - t)) // 2 - t), c, font=f, fill=255)
        cov = np.repeat((np.asarray(big, np.float32) / 255).reshape(ch, S, lw, S).mean((1, 3)), 2, 1)
        x = int(round(xs[k])); out[:, x:x + cov.shape[1]] = np.maximum(out[:, x:x + cov.shape[1]], cov[:, :total - x])
    return out

def erase(view, pal, box, thr=22):
    x0, y0, x1, y1 = box
    rgb = pal[view[y0:y1, x0:x1]].astype(float)
    lum = rgb.mean(2); sat = rgb.max(2) - rgb.min(2)
    # 분필 글자 = 그 상자 바탕(중앙값)보다 뚜렷이 밝고 채도 낮은 화소 — 칠판 그러데이션(왼쪽 위 밝은 빛)을 글자로 잡지 않도록 상대 기준
    m = (lum > np.median(lum) + thr) & (sat < 70)
    mm = m.copy()
    for _ in range(2):                                    # 2화소 팽창(옅은 안티 테두리까지)
        n = mm.copy(); n[1:] |= mm[:-1]; n[:-1] |= mm[1:]; n[:, 1:] |= mm[:, :-1]; n[:, :-1] |= mm[:, 1:]; mm = n
    bg = rgb[~mm].mean(0) if (~mm).any() else rgb.mean((0, 1))
    # 바탕에 그러데이션이 있어 평균 한 색으로 메우면 네모 자국이 남는다 → 세로·가로 선형 보간 평균
    h, w = mm.shape
    est = np.zeros_like(rgb); cnt = np.zeros((h, w, 1))
    for axis in (0, 1):
        M = mm if axis == 0 else mm.T; R = rgb if axis == 0 else rgb.transpose(1, 0, 2)
        E = np.zeros_like(R); C = np.zeros(M.shape + (1,))
        for j in range(M.shape[1]):
            ok = np.where(~M[:, j])[0]
            if len(ok) < 2: continue
            for c in range(3):
                E[:, j, c] = np.interp(np.arange(M.shape[0]), ok, R[ok, j, c])
            C[:, j] = 1
        if axis == 1: E = E.transpose(1, 0, 2); C = C.transpose(1, 0, 2)
        est += E * C; cnt += C
    fill = np.where(cnt > 0, est / np.maximum(cnt, 1), bg)
    rgb[mm] = fill[mm]
    return rgb

def put(view, pal, box, rgb):
    x0, y0, x1, y1 = box
    view[y0:y1, x0:x1] = nearest(pal, rgb.reshape(-1, 3)).reshape(rgb.shape[:2])

def draw_on(rgb, cov, x, y, color=255.0):
    h, w = cov.shape; c = cov[..., None]
    sub = rgb[y:y + h, x:x + w]
    rgb[y:y + h, x:x + w] = sub * (1 - c[:sub.shape[0], :sub.shape[1]]) + color * c[:sub.shape[0], :sub.shape[1]]

def grid(view, pal, ox, oy, chars):
    k = 0
    for y in ROW_Y:
        for gx in GRP_X:
            for c in range(5):
                x = int(round(gx + c * PITCH)) - ox; yy = y - oy
                box = (x - 2, yy - 2, x + CW + 2, yy + CH + 2)
                if box[0] < 0 or box[1] < 0 or box[2] > view.shape[1] or box[3] > view.shape[0]:
                    k += 1; continue
                rgb = erase(view, pal, box)
                ch = chars[k] if k < len(chars) else '　'; k += 1
                if ch != '　':
                    draw_on(rgb, cov_text(ch, CW, CH, PITCH), 2, 2)
                put(view, pal, box, rgb)

def page1(view, pal):
    grid(view, pal, 0, 0, poc.NAME_SYLL[:90])
    # 머리말(회색 띠 안, 글자 y12~23, x138~495 → 띠 가운데 맞춤)
    box = (104, 10, 536, 26); rgb = erase(view, pal, box, thr=40)
    cov = cov_text(HEADER, CW, CH, PITCH)
    draw_on(rgb, cov, (box[2] - box[0] - cov.shape[1]) // 2, 2, 240.0); put(view, pal, box, rgb)
    # 버튼(테두리 안쪽 3화소)
    for (x0, y0, x1, y1), t in BUTTONS.items():
        ib = (x0 + 3, y0 + 3, x1 - 2, y1 - 2); rgb = erase(view, pal, ib)
        pitch = min(PITCH, (ib[2] - ib[0] - 4) / max(len(t), 1))
        cw = min(CW, int(pitch) - 1)
        cov = cov_text(t, cw, CH, pitch)
        draw_on(rgb, cov, max(0, (ib[2] - ib[0] - cov.shape[1]) // 2), max(0, (ib[3] - ib[1] - CH) // 2)); put(view, pal, ib, rgb)
    # 「名前」 → 「이름」, 「：」 그대로
    box = (113, 155, 171, 170); rgb = erase(view, pal, box)      # 「名前」 y157~168, 「：」(x174~) 는 남김
    draw_on(rgb, cov_text(LABEL, CW, CH, PITCH), 3, 2); put(view, pal, box, rgb)
    # 이름(밑줄 위만 지움, 옅은 안티까지 지우도록 기준 낮춤)
    ul = underline_row(view, pal)
    box = (184, 153, 330, ul); rgb = erase(view, pal, box, thr=15)
    draw_on(rgb, cov_text(NAME, CW, CH, PITCH), 3, max(0, (box[3] - box[1] - CH) // 2)); put(view, pal, box, rgb)

def underline_row(view, pal):
    rgb = pal[view].astype(float); lum = rgb.mean(2)
    for y in range(150, 184):
        if (lum[y, 190:320] > 150).mean() > 0.8:
            return y
    raise SystemExit('이름 밑줄을 못 찾음')

def find_offset(kv, v807, pal):
    """가타카나 조각이 807 의 어디에 덮이는지 — 바탕(어두운 화소)이 가장 많이 일치하는 위치."""
    best = None
    dark = pal[kv].mean(2) < 90
    for oy in range(30, 60):
        for ox in range(60, 110):
            if oy + kv.shape[0] > v807.shape[0] or ox + kv.shape[1] > v807.shape[1]: continue
            s = (v807[oy:oy + kv.shape[0], ox:ox + kv.shape[1]][dark] == kv[dark]).mean()
            if best is None or s > best[0]: best = (s, ox, oy)
    return best

def preview(a, b, pal, path):
    A = pal[a].astype(np.uint8); B = pal[b].astype(np.uint8)
    img = np.concatenate([A, np.full((4, A.shape[1], 3), 255, np.uint8), B], 0)
    Image.fromarray(img).resize((img.shape[1] * 2, img.shape[0] * 2), Image.NEAREST).save(path)

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    raw = load_807(); off, w, h, stride, pal, _ = bmp_split(raw)
    v0 = to_view(raw); v1 = v0.copy(); page1(v1, pal)
    open(W('poc', 'name_807.bmp'), 'wb').write(from_view(raw, v1))
    preview(v0, v1, pal, W('poc', 'name_p1.png'))
    kraw = load_kana(); koff, kw, kh, ks, kpal, _ = bmp_split(kraw)
    k0 = to_view(kraw)[::-1]                     # 이 조각은 PIL 방향과 위아래 반대로 화면에 찍힌다
    s, ox, oy = find_offset(k0, v0, kpal)
    print('가타카나 조각 위치(807 기준) x=%d y=%d 바탕 일치 %.1f%%' % (ox, oy, s * 100))
    assert s > 0.6, '조각 위치를 못 찾음'
    k1 = k0.copy(); grid(k1, kpal, ox, oy, poc.NAME_SYLL[90:])
    open(W('poc', 'name_kana.bmp'), 'wb').write(from_view(kraw, k1[::-1]))
    preview(k0, k1, kpal, W('poc', 'name_p2.png'))
    hraw = load_kana(HIRA_BMP); hpal = bmp_split(hraw)[4]
    h0 = to_view(hraw)[::-1]
    s, hx, hy = find_offset(h0, v0, hpal)
    print('히라가나 조각 위치 x=%d y=%d 바탕 일치 %.1f%%' % (hx, hy, s * 100)); assert s > 0.6
    h1 = h0.copy(); grid(h1, hpal, hx, hy, poc.NAME_SYLL[:90])
    # 원본 조각은 807 같은 자리와 색 번호가 99.7% 같다 → 같던 화소는 1쪽 새 그림 번호를 그대로 써서 전환 때 깜빡임이 없게
    reg0 = v0[hy:hy + h0.shape[0], hx:hx + h0.shape[1]]; reg1 = v1[hy:hy + h0.shape[0], hx:hx + h0.shape[1]]
    h1 = np.where(reg0 == h0, reg1, h1).astype(np.uint8)
    open(W('poc', 'name_hira.bmp'), 'wb').write(from_view(hraw, h1[::-1]))
    v1c = v1[hy:hy + h1.shape[0], hx:hx + h1.shape[1]]
    print('히라가나 조각 새것 = 1쪽 새 그림 같은 자리 일치 %.1f%%' % ((v1c == h1).mean() * 100))
    print('완료:', W('poc', 'name_p1.png'), W('poc', 'name_p2.png'))

# ── 선택된(초록) 버튼 스프라이트: NAME.DAT 앞 4장(かな·カナ·消す·決定, 80×22 8비트, VDP1 색 은행 1) (2026-10-23) ──
# 사용자 스테이트 namein_v4 의 VDP1 명령표(바이트 뒤집음)로 확인: VRAM 0x520A0 80×22 → 화면 (505,142) = 「2쪽」 자리.
HL_SIZE, HL_W, HL_H = 1760, 80, 22
HL_LABELS = ['1쪽', '2쪽', '지우기', '결정']
HL_CRAM = W('mem', 'namein_v4', 'CRAM.bin')              # u16 LE, 은행 1(0x100~)
HL_BG = 0x34                                              # 초록 바탕
HL_STEPS = [0.15, 0.4, 0.6, 0.85]                         # 덮임 → 원본 글자 색 단계(바탕·0x36·0x10·0x03·0x01 흰색)
HL_RAMP = [HL_BG, 0x36, 0x10, 0x03, 0x01]

def hl_palette():
    c = np.frombuffer(open(HL_CRAM, 'rb').read(), '<u2')[0x100:0x200].astype(int)
    return np.stack([(c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3], 1)

def highlight():
    d = open(W('disc1', 'NAME.DAT'), 'rb').read()
    pal = hl_palette()
    olds = [np.frombuffer(d[k * HL_SIZE:(k + 1) * HL_SIZE], np.uint8).reshape(HL_H, HL_W) for k in range(4)]
    news = []
    for o, t in zip(olds, HL_LABELS):
        v = o.copy(); ib = (3, 3, 65, 18)                     # 테두리 안쪽(초록 x2~65·y2~18) — 바탕은 0x34 한 색
        v[ib[1]:ib[3], ib[0]:ib[2]] = HL_BG
        ref_w = 62                                            # page1 버튼 안쪽 폭 → 같은 글자 크기
        pitch = min(PITCH, (ref_w - 4) / max(len(t), 1)); cw = min(CW, int(pitch) - 1)
        cov = cov_text(t, cw, CH, pitch)
        x = ib[0] + max(0, (ib[2] - ib[0] - cov.shape[1]) // 2); y = ib[1] + max(0, (ib[3] - ib[1] - CH) // 2)
        reg = v[y:y + cov.shape[0], x:x + cov.shape[1]]
        lvl = np.digitize(cov[:reg.shape[0], :reg.shape[1]], HL_STEPS)    # 원본 글자 가장자리 색 단계만 씀
        reg[...] = np.where(lvl > 0, np.array(HL_RAMP, np.uint8)[lvl], reg)
        news.append(v)
    out = bytearray(d)
    for k, v in enumerate(news):
        out[k * HL_SIZE:(k + 1) * HL_SIZE] = v.tobytes()
    open(W('poc', 'NAME.DAT'), 'wb').write(out)
    A = np.concatenate([pal[o] for o in olds], 1); B = np.concatenate([pal[v] for v in news], 1)
    img = np.concatenate([A, np.full((2, A.shape[1], 3), 255), B], 0).astype(np.uint8)
    Image.fromarray(img).resize((img.shape[1] * 4, img.shape[0] * 4), Image.NEAREST).save(W('poc', 'name_hl.png'))
    print('선택 버튼 4장 → work/poc/NAME.DAT, 미리보기', W('poc', 'name_hl.png'))

if __name__ == '__main__' and 'bake' not in sys.argv:
    main()
    highlight()

# ── 디스크 파일로 굽기 (poc.py 다음에 돌린다: work/poc/0.BIN 의 GP8 위치표 크기만 고침) ──
GP8_807 = 0x3AD4800
GP8_REC_SIZE = 0x5A280                      # 0.BIN 위치표(이름 포인터·섹터·크기 BE) 중 807 의 크기 칸, 섹터 칸 = 0x5A27C

def bake():
    import shutil
    gp8 = bytearray(open(W('disc1', 'GP8.ARC'), 'rb').read())
    nxt = [m.start() for m in re.finditer(rb'elfpak\x1a\x00', gp8) if m.start() > GP8_807][0]
    slot = nxt - GP8_807
    blob = elfpak.pack(open(W('poc', 'name_807.bmp'), 'rb').read())
    assert len(blob) <= slot, ('807 재압축이 자리를 넘음', len(blob), slot)
    gp8[GP8_807:nxt] = blob + bytes(slot - len(blob))
    open(W('poc', 'GP8.ARC'), 'wb').write(gp8)
    exe = bytearray(open(W('poc', '0.BIN'), 'rb').read())
    assert struct.unpack_from('>I', exe, GP8_REC_SIZE - 4)[0] == GP8_807 // 2048
    struct.pack_into('>I', exe, GP8_REC_SIZE, len(blob))
    open(W('poc', '0.BIN'), 'wb').write(exe)
    bmp = bytearray(open(W('disc1', 'BMP.ARC'), 'rb').read())
    for at, fn in ((KANA_BMP, 'name_kana.bmp'), (HIRA_BMP, 'name_hira.bmp')):
        b = open(W('poc', fn), 'rb').read()
        assert b[:2] == b'BM' and len(b) == struct.unpack_from('<I', bmp, at + 2)[0]
        bmp[at:at + len(b)] = b
    open(W('poc', 'BMP.ARC'), 'wb').write(bmp)
    print('807 재압축 %d / 자리 %d B · BMP 조각 2장 · 0.BIN 위치표 크기 갱신' % (len(blob), slot))

if __name__ == '__main__' and 'bake' in sys.argv:
    bake()
