# -*- coding: utf-8 -*-
"""PoC — 글꼴 칸 덮어쓰기 + 대사 한 줄 + 제목 메뉴 한 줄 (2026-10-23). 결과는 work/poc/ 에만 쓴다(디스크 아님).
 - 첫 장면(MES 0번 = 01M): 「［マスター］：」「君、遅刻だよ。」 조각을 원래 바이트 안에서 바꾼다(주소 이동 없음).
 - 0.BIN 제목 메뉴 「下級生を途中からする」 → 「하급생 이어하기」.
 - 한글 음절·「，」는 원문에서 거의 안 쓰는 한자 칸(SJIS2.KNJ)에 덮어 그리고, 텍스트는 그 한자 코드를 쓴다(대응표 그대로).
 - 글자 = Galmuri11-Bold BDF 1비트(보통체는 원본보다 가늘어 보임), 세로 1~12행 가운데, 가로 2배(원본과 같은 28×14, 화소 4비트: 1=글자, 8=바탕).
 - 장면 파일 재압축 후 원래 묶음 칸에 들어가는지 확인, 0.BIN 위치표(이름 주소·섹터·크기)의 크기 갱신.
 - 미리보기 work/poc/preview.png (원본 | 시험판, 엔진 조회 규칙대로 그림)."""
import os, re, struct, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import bdf, elfpak, fontprev
KFONT = r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = lambda *p: os.path.join(ROOT, 'work', *p)
GALMURI = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11-Bold.bdf'
EXE_BASE = 0x06004000
TABLE = 0x06060508 - EXE_BASE          # SJIS → 글꼴 칸(값-1) u16BE 표
REC = (0x4B918, 0x4DB2C)               # MES 위치표(이름 주소, 섹터, 크기) 12 B
DONORS = [0x8ad5, 0x8af5, 0x8cd6, 0x92c1, 0x9453, 0x966e, 0x9cdf,
          0x88b9, 0x88c6, 0x8976, 0x89b1, 0x8a8b, 0x8ab3, 0x8abb, 0x8b9e, 0x8c4f,
          0x8c6d, 0x8c85, 0x8c9b, 0x8caa]
LINES = [  # (MES 묶음 번호, 원문 조각, 시험 번역)
    (0, '［マスター］：', '［마스터］：'),
    (0, '君、遅刻だよ。', '군，지각이야．'),
    (576, '［マスター］：お疲れさま、', '［마스터］：수고했어，'),   # 4/8 저녁 가게 — 처음부터 반드시 지나감
    (576, '君。', '군．'),
]
TITLE = ('下級生を途中からする', '하급생 이어하기')
# 이름 입력 글자판: 0.BIN 0x65898, 쪽(2)×228 B, 줄(6)×38 B, 5글자 묶음 3개(묶음 사이 빈 칸 2) — 코드가 base+쪽*0xE4+줄*0x26+칸*2 로 읽음
GRID_OFF, GRID_PAGES, GRID_ROWS = 0x65898, 2, 6
NAME_SYLL = ('가간갈감강개건경계고공관광교구국군권규근금기길김'
             '나남내노니다단담대덕도동두라란래량려련령로록룡루류리린림'
             '마만명모목무문미민박반배백범병보복봉부분비빈'
             '사산상서석선설성세소손송수숙순스승시식신실심'
             '아안애양어여연열영예오완요용우욱운웅원월위유윤은의이인일임'
             '자장재전정제조종주준중지진차찬창채천철청초최춘충'
             '켄타태파피필하학한해행혁현형혜호홍화환효후훈희')
DEFAULT_NAME = ('けんたろう', '켄타로')   # 0.BIN 세 곳 + 이름 레코드(0x4B900, 앞 u16 = 글자 수)
NAME_REC = 0x4B8F8

def sidx(c):
    l, t = c >> 8, c & 0xFF
    r = (l - 0x81) if l <= 0x9F else (l - 0xC1)
    return r * 188 + (t - 0x40 if t <= 0x7E else t - 0x41)

def glyph_no(exe, c):
    return struct.unpack_from('>H', exe, TABLE + 2 * sidx(c))[0] - 1

def render_char(glyphs, asc, ch):
    g = glyphs[ord(ch)]
    w, h, xo, yo, adv, rows = g
    a = np.zeros((14, 14), np.uint8)
    bm = np.array(rows, np.uint8)
    ys, xs = np.nonzero(bm)
    if len(ys):
        bm = bm[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    hh, ww = bm.shape
    if ch in '，．':                       # 부호는 아래쪽 왼편
        top, left = 12 - hh, 3
    else:
        top, left = 1 + (12 - hh) // 2, (14 - ww) // 2
    a[top:top + hh, left:left + ww] = bm
    px = np.repeat(a, 2, axis=1)            # 가로 2배 → 28×14
    nib = np.where(px, 1, 8).astype(np.uint8)
    return bytes((nib[:, 0::2] << 4 | nib[:, 1::2]).reshape(-1))

def rare_kanji(exe):
    """원문(MES 해제본 + 0.BIN)에서 적게 쓰는 순서의 한자 코드(글꼴 칸이 있는 것만)."""
    import collections, glob
    use = collections.Counter()
    pat = re.compile(rb'[\x88-\x9f\xe0-\xea][\x40-\xfc]')
    for f in glob.glob(W('disc1', 'mes', '*.bin')):
        use.update(m.group() for m in pat.finditer(open(f, 'rb').read()))
    use.update(m.group() for m in pat.finditer(bytes(exe)))
    c = []
    for l in list(range(0x88, 0xA0)) + list(range(0xE0, 0xEB)):
        for t in range(0x40, 0xFD):
            if t == 0x7F:
                continue
            code = (l << 8) | t
            if 0 <= glyph_no(exe, code) < 2060:
                c.append((use[bytes([l, t])], code))
    return [code for n, code in sorted(c)]

def write_name_grid(exe, enc):
    """이름 입력 글자판(5글자 묶음 칸만, 묶음 사이 빈 칸은 그대로) + 기본 이름 세 곳 + 이름 레코드 글자 수."""
    cells = list(NAME_SYLL) + ['　'] * (GRID_PAGES * GRID_ROWS * 15 - len(NAME_SYLL))
    k = 0
    for pg in range(GRID_PAGES):
        for row in range(GRID_ROWS):
            base = GRID_OFF + pg * 0xE4 + row * 0x26
            for grp in range(3):
                for c in range(5):
                    a = base + (grp * 7 + c) * 2
                    assert bytes(exe[a:a + 2]) != b'\0\0', hex(a)
                    exe[a:a + 2] = enc(cells[k]); k += 1
    nj = DEFAULT_NAME[0].encode('cp932'); nk = enc(DEFAULT_NAME[1])
    hits = [m.start() for m in re.finditer(re.escape(nj + b'\0'), exe)]
    assert len(hits) == 3, hits
    for p in hits:
        exe[p:p + len(nj)] = nk + bytes(len(nj) - len(nk))
    assert struct.unpack_from('>H', exe, NAME_REC)[0] == len(DEFAULT_NAME[0])   # 레코드 맨 앞 u16 = 글자 수
    struct.pack_into('>H', exe, NAME_REC, len(DEFAULT_NAME[1]))

def main():
    out = W('poc'); os.makedirs(out, exist_ok=True)
    exe = bytearray(open(W('disc1', '0.BIN'), 'rb').read())
    font = bytearray(open(W('disc1', 'SJIS2.KNJ'), 'rb').read())
    arc = bytearray(open(W('disc1', 'MES.ARC'), 'rb').read())
    glyphs, asc = bdf.load(GALMURI)
    # 필요한 글자 → 덮어쓸 칸
    need = []
    assert len(NAME_SYLL) == len(set(NAME_SYLL)) and len(NAME_SYLL) <= GRID_PAGES * GRID_ROWS * 15, len(NAME_SYLL)
    for s in [t for _, _, t in LINES] + [TITLE[1], DEFAULT_NAME[1], NAME_SYLL]:
        for ch in s:
            if (0xAC00 <= ord(ch) <= 0xD7A3 or ch == '，') and ch not in need:
                need.append(ch)
    donors = DONORS + [c for c in rare_kanji(exe) if c not in DONORS]
    assert len(need) <= len(donors), (len(need), len(donors))
    cmap = {}
    for ch, code in zip(need, donors):
        gi = glyph_no(exe, code)
        assert 0 <= gi < 2060, (ch, hex(code), gi)
        font[gi * 196:(gi + 1) * 196] = fontprev.render(KFONT, ch)   # 나눔고딕 굵게, 안티 7단계(사용자 선택 2026-10-23)
        cmap[ch] = code
    def enc(s):
        b = bytearray()
        for ch in s:
            b += struct.pack('>H', cmap[ch]) if ch in cmap else ch.encode('cp932')
        return bytes(b)
    # 장면 조각 바꾸기(원래 바이트 안, 주소 이동 없음) → 재압축 → 같은 묶음 칸 → 위치표 크기 갱신
    offs = [m.start() for m in re.finditer(rb'elfpak\x1a\x00', arc)] + [len(arc)]
    sizes = {}
    for k in sorted({k for k, _, _ in LINES}):
        raw = bytearray(elfpak.unpack(bytes(arc[offs[k]:offs[k + 1]]))[0])
        for kk, jp, kr in LINES:
            if kk != k: continue
            jb = jp.encode('cp932') + b'\0'; kb = enc(kr) + b'\0'
            p = 0
            while True:                      # 4바이트 정렬 조각 시작에서만
                p = raw.find(jb, p)
                assert p >= 0, (k, jp)
                if p % 4 == 0 and (p == 0 or raw[p - 1] in (0, 9)): break
                p += 1
            assert len(kb) <= len(jb), (jp, len(kb), len(jb))
            raw[p:p + len(jb)] = kb + bytes(len(jb) - len(kb))
        blob = elfpak.pack(bytes(raw))
        cap = offs[k + 1] - offs[k]
        assert len(blob) <= cap, ('묶음 칸 초과', k, len(blob), cap)
        arc[offs[k]:offs[k + 1]] = blob + bytes(cap - len(blob))
        sizes[offs[k] // 2048] = (k, len(blob), cap)
    hit = 0
    for p in range(REC[0], REC[1], 12):
        nptr, sec, size = struct.unpack_from('>III', exe, p)
        name = exe[nptr - EXE_BASE:exe.index(b'\0', nptr - EXE_BASE)]
        if name.endswith(b'.MES') and sec in sizes:
            struct.pack_into('>I', exe, p + 8, sizes[sec][1]); hit += 1
    assert hit == len(sizes), (hit, sizes)
    # 제목 메뉴
    # 0.BIN 에 두 번 있고 둘 다 전각 공백으로 폭을 맞춘 고정 폭 칸 → 같은 글자 수(10)로 가운데 맞춤
    tj = TITLE[0].encode('cp932')
    kr = TITLE[1].replace(' ', '　'); padn = len(TITLE[0]) - len(kr); assert padn >= 0
    kr = '　' * (padn // 2) + kr + '　' * (padn - padn // 2)
    tk = enc(kr); assert len(tk) == len(tj)
    hits = [m.start() for m in re.finditer(re.escape(tj), exe)]
    assert len(hits) == 2, hits
    for p in hits:
        exe[p:p + len(tj)] = tk
    write_name_grid(exe, enc)
    for name, data in (('0.BIN', exe), ('SJIS2.KNJ', font), ('MES.ARC', arc)):
        open(os.path.join(out, name), 'wb').write(data)
    # 미리보기(엔진 조회 규칙)
    def draw(exe_b, font_b, s):
        cells = []
        i = 0; b = s
        while i < len(b):
            c = (b[i] << 8) | b[i + 1]; i += 2
            gi = glyph_no(exe_b, c)
            g = np.frombuffer(bytes(font_b[gi * 196:(gi + 1) * 196]), np.uint8).reshape(14, 14)
            cells.append(np.stack([g >> 4, g & 15], -1).reshape(14, 28))
        return np.concatenate(cells, 1) if cells else np.zeros((14, 28))
    name_jp = 'けんたろう'.encode('cp932')
    o_exe = open(W('disc1', '0.BIN'), 'rb').read(); o_font = open(W('disc1', 'SJIS2.KNJ'), 'rb').read()
    L = {jp: kr for _, jp, kr in LINES}
    rows = []
    for a, b in (('［マスター］：', '君、遅刻だよ。'), ('［マスター］：お疲れさま、', '君。')):
        rows.append(draw(o_exe, o_font, a.encode('cp932') + name_jp + b.encode('cp932')))
        rows.append(draw(exe, font, enc(L[a]) + name_jp + enc(L[b])))
    rows += [draw(o_exe, o_font, tj), draw(exe, font, tk)]
    wmax = max(r.shape[1] for r in rows)
    img = np.full((len(rows) * 18, wmax), 8, np.uint8)
    for k, r in enumerate(rows):
        img[k * 18 + 2:k * 18 + 16, :r.shape[1]] = r
    lum = (255 - (8 - np.clip(img, 1, 8)) * 255 // 7).astype(np.uint8)
    Image.fromarray(lum).resize((wmax * 2, img.shape[0] * 4), Image.NEAREST).save(os.path.join(out, 'preview.png'))
    sys.stdout.reconfigure(encoding='utf-8')
    print('덮어쓴 칸', {ch: hex(c) for ch, c in cmap.items()})
    print('재압축(묶음, 크기, 칸)', list(sizes.values()), '· 0.BIN·SJIS2.KNJ·MES.ARC →', out)

if __name__ == '__main__':
    main()
