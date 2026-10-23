# -*- coding: utf-8 -*-
"""시험판 빌더 (2026-10-23): work/sat_tr.tsv(병합 번역) 전량 → MES.ARC·SJIS2.KNJ·0.BIN (+ PoC 이름 입력 그림) → work/build/discN/.
 - 글꼴: 한글 음절은 «남길 일본어 글자»에 들지 못한 칸에 덮어 그린다(대응표는 그대로, 그 칸의 원래 SJIS 코드를 쓴다).
   남길 일본어 = 번역 안 된 조각·번역에 남은 가나/한자·0.BIN 화면 글자를 빈도 순으로, 칸이 남는 만큼만.
 - 공백 = 전각 공백 0x8140(칸 0, 원래 빈칸). 조사 표시({이가} 등)는 기본 이름 «켄타로»(받침 없음) 기준.
 - 장면: 번역이 원래 문자열 길이(+NUL) 안이면 제자리, 넘치면 «다른 조각이 비운 자리» → 없으면 파일 끝(4 정렬)에 두고
   장면 안 32비트 절대 주소(0x060A0000+위치)를 전부 고친다. 장면 버퍼 = 0x060A0000~0x060C0000.
 - MES.ARC 는 600묶음을 앞에서부터 2048 정렬로 다시 채우고 0.BIN 위치표(섹터·크기)를 고친다. 커지면 디스크 끝으로(build_track).
 - 번역할것 파일(tools/todo_tr.py 가 읽고 검사): MES 줄은 같은 원문 조각 중 번역이 비었거나 가나·한자가 남은 것에 넣고,
   0BIN 줄은 0.BIN 제자리(원래 바이트 안, 남으면 NUL·전각 공백).
  python tools/build_kr.py [디스크번호=1]"""
import collections, os, re, shutil, struct, sys
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
import elfpak, fontprev, poc, todo_tr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = lambda *p: os.path.join(ROOT, 'work', *p)
BASE, LIMIT = 0x060A0000, 0x20000
CELLS = 2060
SPACE = 0x8140
PARTICLE = {'이가': '가', '을를': '를', '은는': '는', '와과': '와', '아야': '야', '이': ''}   # 켄타로 = 받침 없음
PUNCT = '，．、。？！…～・：'
is_kr = lambda c: 0xAC00 <= ord(c) <= 0xD7A3

def clean(k):
    k = re.sub(r'\{(이가|을를|은는|와과|아야|이)\}', lambda m: PARTICLE[m.group(1)], k)
    assert '{' not in k and '}' not in k, k
    k = k.replace('　', ' ')
    k = re.sub('([%s]) +' % re.escape(PUNCT), r'\1', k)          # 문장부호 뒤 공백은 빌더에서 지운다
    return k

JPCH = re.compile('[ぁ-ヾ一-鿿々]')

TAGJP = re.compile('［([^］]*[ぁ-ヺー-ヾ一-鿿々][^］]*)］：')
_fixes = None
FRIEND_TAGS = {'の死んで欲しいほど嫌いな友達': '의 죽도록 싫은 친구', 'の取るに足らない友達': '의 하찮은 친구',
               'のすごく嫌いな友達': '의 아주 싫은 친구', 'の嫌いな友達': '의 싫은 친구'}

def fix_row(jp, kr):
    """sat_tr 를 다시 만들지 않고 빌드 때 고치는 것(2026-10-23 실기 버그):
    ① PC 번역에 일본어 이름표가 남은 줄(［稔］ 등 616조각) → tags.tsv 대응으로 한국어 이름표
    ② 새턴이 음성 때문에 이름을 빼고 君(=너)만 쓴 줄을 PC 번역이 «군»으로 옮긴 것 → work/tr_fix_kun.tsv(원문 → 번역)"""
    global _fixes
    if _fixes is None:
        import merge
        _fixes = {'tags': merge.tag_map(), 'kun': {}}
        for ln in open(W('tr_fix_kun.tsv'), encoding='utf-8'):
            if ln.strip():
                j, k = ln.rstrip('\n').split('\t'); _fixes['kun'][j] = k
    if jp in _fixes['kun']:
        return _fixes['kun'][jp]
    if jp.startswith('］：') and kr.startswith('］') and not kr.startswith('］：'):   # PC 번역의 «］고，»·«］ ：» 깨짐
        kr = '］：' + kr[1:].lstrip(' ：')
    for a, b in FRIEND_TAGS.items():                # 「［」+주인공 이름+「の嫌いな友達］：」 꼴 이름표 뒷조각
        if kr.startswith(a + '］'): kr = b + kr[len(a):]
    m = TAGJP.match(kr)
    if m and m.group(1) in _fixes['tags']:
        kr = '［%s］：' % _fixes['tags'][m.group(1)] + kr[m.end():]
    if jp.startswith('君'):                         # 이름 바로 뒤 「君」 = «(이름)군» — 사용자 번역의 «너/네»를 «군» 꼴로(2026-10-23 «하스피너와»)
        for a, c in KUN_START:
            if kr.startswith(a): kr = c + kr[len(a):]; break
    # 번역에만 있는 괄호 설명 지우기(사용자 지시 2026-10-23: «알바（아르바이트）» 등). 말투 «（？）»는 남김.
    kr = re.sub('^(은（는）|와（과）|이（가）|을（를）)', lambda m: KUN_PART[m.group(1)], kr)   # 이름 뒤 조사 병기 → 켄타로(받침 없음)
    if kr.count('（') > jp.count('（') + jp.count('('):
        # 괄호 뒤가 조사·어미면 붙이고, 명사가 이어지면 한 칸(«알바（아르바이트）대금» → «알바 대금»)
        kr = GLOSS.sub(lambda m: '' if m.end() >= len(m.string) or GLUE.match(m.string[m.end()]) else ' ', kr)
    return kr

KUN_START = [('너는', '군은'), ('너도', '군도'), ('너한테', '군한테'), ('너에게', '군에게'), ('너와', '군과'), ('너랑', '군이랑'),
             ('너의', '군의'), ('너를', '군을'), ('너에', '군에'), ('너뿐', '군뿐'), ('너였', '군이었'), ('너지', '군이지'),
             ('너구나', '군이구나'), ('너라면', '군이라면'), ('너같', '군같'), ('네가', '군이'), ('네 ', '군의 '), ('너', '군')]
KUN_PART = {'은（는）': '는', '와（과）': '와', '이（가）': '가', '을（를）': '를'}
GLUE = re.compile('[했해하한겠냐가라이야는은을를지로다니에의와과도만’》，．？！…）) ]')
GLOSS = re.compile(r'(?<=[가-힣Ａ-Ｚａ-ｚ０-９])\s?（(?!？）)[^（）]{1,30}）')

def load_rows(mes=None):
    """mes = 번역할것 파일의 {원문: 번역} — 같은 원문 조각 중 번역이 비었거나 가나·한자가 남은 것에 넣는다."""
    by = collections.defaultdict(list); n = 0
    user = {}                                       # 사용자 번역(건너뛴 줄·이름 자리 안 맞던 줄) — tools/import_user_tr.py
    if os.path.exists(W('tr_user.tsv')):
        for ln in open(W('tr_user.tsv'), encoding='utf-8'):
            sc, pos, k = ln.rstrip('\n').split('\t'); user[(sc, pos)] = k
    for ln in open(W('sat_tr.tsv'), encoding='utf-8'):
        sc, pos, jp, kr, src = ln.rstrip('\n').split('\t')
        if not kr and (sc, pos) in user: kr = user[(sc, pos)]
        if kr: kr = fix_row(jp, kr)
        if mes and jp in mes and (not kr or JPCH.search(kr)):
            kr = fix_row(jp, mes[jp]); n += 1         # 번역할것 파일 번역에도 같은 손질(괄호 설명 등)
        kr = clean(kr) if kr else ''
        if kr: kr = center(jp, kr)
        by[int(sc)].append((int(pos, 16), jp, kr))
    # 추출 때 빠진 조각(장면 파일 맨 앞 오프셋 4 — 앞 바이트가 포인터라 satlines 가 못 잡음, 282곳·49문장, 2026-10-23 «［麗子］：……。»):
    # 장면 안 32비트 주소가 가리키는 4정렬 전각 SJIS 문자열 중 표에 없는 것 → 같은 원문의 번역(가장 많이 쓴 것)으로 채운다
    same = collections.defaultdict(collections.Counter)
    for lst in by.values():
        for p, jp, kr in lst:
            if kr: same[jp][kr] += 1
    sj = re.compile(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc])+')
    for sc in range(600):
        raw = open(W('disc1', 'mes', '%03d.bin' % sc), 'rb').read()
        have = {p for p, j, k in by.get(sc, [])}
        tg = {struct.unpack_from('>I', raw, q)[0] - BASE for q in range(0, len(raw) - 3, 4)}
        for t in sorted(x for x in tg if 0 <= x < len(raw) and x % 4 == 0 and x not in have):
            e = raw.find(b'\0', t); m = sj.fullmatch(raw[t:e]) if e > t else None
            if not m: continue
            jp = raw[t:e].decode('cp932')
            if jp in same:
                by[sc].append((t, jp, same[jp].most_common(1)[0][0]))
            elif jp in _fixes['kun']:                   # 어디에도 없던 22문장 = PC 판 번역을 work/tr_fix_kun.tsv 에
                by[sc].append((t, jp, clean(fix_row(jp, _fixes['kun'][jp]))))
        if sc in by: by[sc].sort()
    # 이름 자리 앞 띄어쓰기:다음 조각이 「君」(이름 바로 뒤)이고 이 조각 번역이 한글로 끝나면 한 칸(«나는하스피» → «나는 하스피»)
    for sc, lst in by.items():
        raw = open(W('disc1', 'mes', '%03d.bin' % sc), 'rb').read()
        nxt = {p: j for p, j, k in lst}
        for i, (p, jp, kr) in enumerate(lst):
            e = p + len(jp.encode('cp932')); q = (e + 4) & ~3
            if kr and re.search('[가-힣]$', kr) and nxt.get(q, '').startswith('君') and not any(raw[e:q]):
                lst[i] = (p, jp, kr + ' ')
    return by, n

from fontTools.ttLib import TTFont
KFONT_CMAP = set(TTFont(poc.KFONT).getBestCmap())
FALLBACK_FONT = r'C:\Windows\Fonts\YuGothB.ttc'

CTRL = {'￥'}
NARROW = 0x818F                                     # 대사 루프(0x06014104)가 그리지 않고 x 만 12 진행하는 코드(원래 오프닝 들여쓰기용)
NARROW_PX = 12
CENTER_PX = 307                                     # 오프닝 가운데 줄 중심(원문: ￥ 줄 12+28×10.5, 아닌 줄 28×11)
DIALOG_FN = 0x0609C260                              # 장면 코드가 대사 문자열을 넘기는 함수(선택지·메뉴는 0x0609C5A8)                                       # 0x818F = 글꼴 없는 제어 코드(오프닝 등 가운데 줄) — 다시 그리지 않고 그대로

def center(jp, kr):
    """원문이 (￥)+전각 공백으로 가운데를 맞춘 줄(오프닝·엔딩 내레이션 234조각)은 번역도 같은 가운데로.
    가운데 칸 = ￥ 줄 10.5 · 아닌 줄 11.0 (원문 전부 이 둘 중 하나, 줄 폭 22칸). 한글 공백도 전각 한 칸."""
    m = re.match('(￥?)(　+)', jp)
    if not m: return kr
    yen = m.group(1)
    body = kr[1:] if yen and kr.startswith('￥') else kr
    body = body.lstrip(' ')
    px = lambda t: sum(NARROW_PX if c == ' ' else 28 for c in t)     # 대사 띄어쓰기 = 좁은 공백(12px)
    if px(body) > 21 * 28:                          # 줄 폭 21칸 넘으면 앞뒤 말줄임표만 한 칸씩(사용자 선택 2026-10-23)
        if body.startswith('……'): body = body[1:]
        if body.endswith('……'): body = body[:-1]
    lead = NARROW_PX if yen else 0                  # 「￥」 자체가 12px 진행
    n = max(0, int(round((CENTER_PX - lead - px(body) / 2) / 28)))
    return yen + '　' * n + body                    # 가운데 맞춤 채움은 전각 공백(28px)

def ui_strings(exe, skip=()):
    """0.BIN 화면 문자열(가나가 든 SJIS 줄). skip = 번역해 넣을 자리(그 일본어 글자는 남길 필요 없음)."""
    out = []
    for m in re.finditer(rb'(?:[\x81-\x84\x88-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc]){2,}(?=\x00)', exe):
        try:
            s = m.group().decode('cp932')
        except UnicodeDecodeError:
            continue
        if re.search('[ぁ-ヾ]', s) and m.start() not in skip:
            out.append(s)
    return out

def plan_font(exe, rows, extra=(), skip=(), pinned=None):
    kr, jp = set(), collections.Counter()
    for s in extra:                                 # 0.BIN 에 넣을 번역(화면 글자라 우선)
        for c in s:
            if is_kr(c): kr.add(c)
            elif ord(c) >= 0x80: jp[c] += 100000           # 반각 ASCII(%2s 등)는 글꼴과 무관
    for lst in rows.values():
        for _, j, k in lst:
            for c in (k or j):
                if is_kr(c): kr.add(c)
                elif c != ' ' and c not in CTRL: jp[c] += 1
    for s in ui_strings(exe, skip):                 # 화면 글자는 우선
        for c in s: jp[c] += 100000
    for s in (poc.NAME_SYLL, poc.TITLE[1], poc.DEFAULT_NAME[1]):
        kr.update(c for c in s if is_kr(c))
    jp['　'] += 10 ** 9
    code = lambda c: struct.unpack('>H', c.encode('cp932'))[0]
    have = {}
    for c in jp:
        try:
            g = poc.glyph_no(exe, code(c))
        except (UnicodeEncodeError, struct.error):
            g = -1
        if 0 <= g < CELLS: have[c] = g
    nokeep = [c for c in jp if c not in have]       # 원래 글꼴에 없는 글자(전각 쉼표 «，» 등) → 한글처럼 새로 그린다
    kr |= set(nokeep)
    # 고정 배정(work/font_map.tsv): 전에 쓴 글자는 같은 코드 그대로 — 백업 RAM 에 저장된 주인공 이름이 빌드마다 바뀌지 않게
    pin = {}
    for ch, c in (pinned or {}).items():
        if ch in kr: pin[ch] = (c, poc.glyph_no(exe, c))
    pin_cells = {g for _, g in pin.values()}
    room = CELLS - len(kr)
    keep = [c for c, _ in sorted(((c, jp[c]) for c in have if have[c] not in pin_cells), key=lambda x: -x[1])][:room]
    kept_cells = {have[c] for c in keep}
    cell_code = {}
    for l in list(range(0x81, 0xA0)) + list(range(0xE0, 0xF0)):
        for t in range(0x40, 0xFD):
            if t == 0x7F: continue
            g = poc.glyph_no(exe, (l << 8) | t)
            if 0 <= g < CELLS and g not in kept_cells and g not in pin_cells: cell_code.setdefault(g, (l << 8) | t)
    free = sorted(cell_code)
    new = sorted(kr - set(pin))
    assert len(free) >= len(new), (len(free), len(new))
    cmap = dict(pin)
    for ch, g in zip(new, free):
        cmap[ch] = (cell_code[g], g)
    dropped = [c for c in have if have[c] not in kept_cells]
    lost = sum(jp[c] % 100000 for c in dropped)
    return cmap, keep, dropped, nokeep, lost, sum(v % 100000 for c, v in jp.items() if c != '　')

def make_enc(cmap, narrow=False):
    """narrow=True: 대사 창 문자열 — 띄어쓰기를 0x818F(12px)로. 선택지·메뉴·0.BIN 은 전각 공백(28px)."""
    def enc(s):
        b = bytearray()
        for ch in s:
            if ch in cmap: b += struct.pack('>H', cmap[ch][0])
            elif ch == ' ': b += struct.pack('>H', NARROW if narrow else SPACE)
            else: b += ch.encode('cp932')
        return bytes(b)
    return enc

def dialog_frags(raw):
    """장면 코드에서 문자열 주소를 레지스터에 싣고 몇 명령 안에 JSR 하는 곳을 찾아, 대사 함수(DIALOG_FN)로만 가는 조각 위치."""
    n = len(raw); calls = collections.defaultdict(set)
    def lit(p):
        w = struct.unpack_from('>H', raw, p)[0]
        if (w >> 12) == 0xD:
            a = ((p + 4) & ~3) + (w & 0xFF) * 4
            if a + 4 <= n: return (w >> 8) & 0xF, struct.unpack_from('>I', raw, a)[0]
    for p in range(0, n - 1, 2):
        x = lit(p)
        if not x or not (BASE <= x[1] < BASE + n): continue
        regs = {}
        for q in range(p + 2, min(n - 1, p + 30), 2):
            y = lit(q)
            if y: regs[y[0]] = y[1]
            w = struct.unpack_from('>H', raw, q)[0]
            if (w & 0xF0FF) == 0x400B:
                calls[x[1] - BASE].add(regs.get((w >> 8) & 0xF)); break
    return {p for p, s in calls.items() if s == {DIALOG_FN}}

def rebuild_scene(raw, lst, enc, enc_dialog=None):
    narrow = dialog_frags(raw) if enc_dialog else set()
    raw = bytearray(raw); n0 = len(raw)
    frag = {}
    for pos, jp, kr in lst:
        jb = jp.encode('cp932')
        assert raw[pos:pos + len(jb)] == jb and raw[pos + len(jb)] == 0, (pos, jp)
        e = enc_dialog if pos in narrow else enc
        frag[pos] = (jb, e(kr) + b'\0' if kr else None)
    inside = set()
    for pos, (jb, _) in frag.items():
        inside.update(range(pos & ~3, pos + len(jb) + 1, 4))
    refs = collections.defaultdict(list)
    for p in range(0, n0 - 3, 4):
        if p in inside: continue
        v = struct.unpack_from('>I', raw, p)[0]
        if BASE <= v < BASE + n0: refs[v - BASE].append(p)
    gaps, move = [], []
    for pos, (jb, nb) in sorted(frag.items()):
        if nb is None: continue
        end = pos + len(jb) + 1                    # 원래 문자열 + NUL 까지만(정렬 패딩은 안 씀)
        if len(nb) <= len(jb) + 1:
            raw[pos:end] = nb + bytes(end - pos - len(nb))
            g = (pos + len(nb) + 3) & ~3
            if end - g >= 4: gaps.append([g, end])
        else:
            raw[pos:end] = bytes(end - pos)
            gaps.append([pos, end]); move.append((pos, nb))
    nmoved_tail = 0
    for pos, nb in sorted(move, key=lambda x: -len(x[1])):
        assert refs.get(pos), ('참조 없는 조각을 옮기려 함', hex(pos))
        best = None
        for g in gaps:
            if g[1] - g[0] >= len(nb) and (best is None or g[1] - g[0] < best[1] - best[0]): best = g
        if best:
            at = best[0]; best[0] = (at + len(nb) + 3) & ~3
        else:
            at = (len(raw) + 3) & ~3; raw += bytes(at - len(raw)); nmoved_tail += 1
        raw[at:at + len(nb)] = nb
        for p in refs[pos]:
            struct.pack_into('>I', raw, p, BASE + at)
    if len(raw) % 4: raw += bytes(4 - len(raw) % 4)
    return bytes(raw), len(move), nmoved_tail

FMT_PATCHES = [                                    # 세이브·로드 칸 표시(sprintf 형식) — 같은 바이트 안
    ('%2s番　　%4s月%4s日　%4s時%4s分', '%2s번　　%4s월%4s일　%4s시%4s분'),
    ('%2s番　　%4s月%4s日', '%2s번　　%4s월%4s일'),
    ('%2s番　　データなし', '%2s번　데이터 없음'),
    ('］：よっしゃあ、%sのポスターをＧＥＴしたぜ！！', '］：좋았어，%s의 포스터를 ＧＥＴ했다！！'),     # 게임센터 포스터 뽑기
    ('］：%sのポスターはもう持ってるけど……まあいいか。', '］：%s의 포스터는 이미 있지만……뭐 괜찮겠지．'),
]
EXT_LIMIT = 0x0609F000                             # 0.BIN 덧붙임 상한(RAM) — 장면 버퍼 0x060A0000 앞 4 KB 여유
GP8_REC = 0x5A27C                                 # 디스크 1 기준 GP8 807 위치표(섹터·크기) — namegfx.GP8_REC_SIZE-4

def locate(exe):
    """디스크 2·3 의 0.BIN 은 코드 길이가 달라 표 위치가 밀려 있다(2026-10-23: 2장 +0x41C/-0x20, 3장 -0x3F80/-0x460).
    디스크 1 의 표 내용으로 찾아 poc 의 위치 상수를 이 장 값으로 바꾼다. → GP8 위치표 오프셋."""
    e1 = open(W('disc1', '0.BIN'), 'rb').read()
    def shift(o, n):
        hits = [m.start() for m in re.finditer(re.escape(e1[o:o + n]), exe)]
        assert len(hits) == 1, ('표를 못 찾음', hex(o), len(hits))
        return hits[0] - o
    t = shift(poc.TABLE, 64); poc.TABLE += t
    assert shift(poc.GRID_OFF, 40) == t and shift(GP8_REC, 8) == t
    poc.GRID_OFF += t
    r = shift(poc.REC[0] + 12 * 300, 24)
    assert shift(poc.REC[1] - 24, 24) == r and shift(poc.NAME_REC, 16) == r
    poc.REC = (poc.REC[0] + r, poc.REC[1] + r); poc.NAME_REC += r
    return GP8_REC + t

def _pack(a):
    return elfpak.pack_opt(a)

def main():
    disc = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    out = W('build', 'disc%d' % disc); os.makedirs(out, exist_ok=True)
    src = W('disc%d' % disc)
    exe = bytearray(open(os.path.join(src, '0.BIN'), 'rb').read())
    gp8_rec = locate(exe) if disc != 1 else GP8_REC
    font = bytearray(open(os.path.join(src, 'SJIS2.KNJ'), 'rb').read())
    arc = open(os.path.join(src, 'MES.ARC'), 'rb').read()
    mes, binr, bad = todo_tr.load()
    rows, nmes = load_rows(mes)
    # 0.BIN 번역: 오프셋은 디스크 1 기준 → 다른 장은 같은 원래 문자열(+NUL)이 한 곳뿐일 때만
    exe1 = open(W('disc1', '0.BIN'), 'rb').read()
    bins, bin_skip, moved = [], 0, []
    for off, (jp, tr, bud) in sorted(binr.items()):
        tr = clean(tr)
        o = off
        if disc != 1:
            s1 = exe1[off:exe1.index(b'\0', off) + 1]
            hits = [m.start() for m in re.finditer(re.escape(s1), exe) if m.start() % 2 == off % 2]
            hits1 = [m.start() for m in re.finditer(re.escape(s1), exe1) if m.start() % 2 == off % 2]
            if len(hits) != len(hits1): bin_skip += 1; continue
            o = hits[hits1.index(off)]                  # 같은 문자열이 여러 벌이면 디스크 1 에서의 순서로
        if len(tr) > bud:                           # 예산 넘침 → 0.BIN 끝에 덧붙이고 포인터를 옮긴다(아래)
            moved.append((o, tr)); continue
        r = todo_tr.bin_text(exe, o, jp, tr, bud)
        if r is None: bin_skip += 1; continue
        bins.append((o, r[0], r[1]))
    # 글꼴 배정은 3장이 똑같아야 한다(저장된 주인공 이름 코드가 디스크를 바꿔도 같은 글자) → 다른 장 화면 글자도 같이 센다
    others = [s for d in (1, 2, 3) if d != disc for s in ui_strings(open(W('disc%d' % d, '0.BIN'), 'rb').read())]
    fmap = W('font_map.tsv')                          # 글자 → 코드 고정표(빌드마다 이어 씀, 지우면 저장된 이름이 깨진다)
    pinned = {}
    if os.path.exists(fmap):
        for ln in open(fmap, encoding='utf-8'):
            ch, c = ln.rstrip('\n').split('\t'); pinned[ch] = int(c, 16)
    cmap, keep, dropped, nokeep, lost, tot = plan_font(exe, rows, [t for _, t, _ in bins] + [t for _, t in moved] + others
                                                       + [k for _, k in FMT_PATCHES],
                                                       {o for o, _, _ in bins} | {o for o, _ in moved}, pinned)
    for ch, (code, g) in cmap.items():
        pinned[ch] = code
    with open(fmap, 'w', encoding='utf-8') as w:
        for ch, c in sorted(pinned.items()): w.write('%s\t%04X\n' % (ch, c))
    for ch, (code, g) in cmap.items():
        f = poc.KFONT if ord(ch) in KFONT_CMAP else FALLBACK_FONT          # 나눔고딕에 없는 글자(゛゜ヽ 등)는 유고딕
        font[g * 196:(g + 1) * 196] = fontprev.render(f, ch)
    enc = make_enc(cmap); enc_dialog = make_enc(cmap, narrow=True)
    fmt_ranges = []
    for jp, kr in FMT_PATCHES:                      # 세이브 화면 printf 형식 문자열(%2s 등 반각 섞임, 홀수 주소라 추출 밖)
        jb = jp.encode('cp932') + b'\0'; kb = enc(kr) + b'\0'
        hits = [m.start() for m in re.finditer(re.escape(jb), exe)]
        assert len(hits) == 1 and len(kb) <= len(jb), (jp, hits, len(kb), len(jb))
        exe[hits[0]:hits[0] + len(jb)] = kb + bytes(len(jb) - len(kb)); fmt_ranges.append((hits[0], hits[0] + len(jb)))
    for o, t, ln in bins:
        if any(a <= o < b for a, b in fmt_ranges): continue      # 형식 문자열 뒷조각(예: 「のポスターを…」)은 위에서 통째로
        b = enc(t); assert len(b) <= ln, (hex(o), t)
        exe[o:o + ln] = b + bytes(ln - len(b))
    # 예산 넘친 화면 문자열: 0.BIN 파일 끝 뒤 RAM(0x0609C6D8~0x060A0000 — 스테이트 10장 모두 0, 참조 없음, BSS 0x0606E8D0~0x06099944 밖)
    # 에 덧붙이고 그 문자열을 가리키는 32비트 주소를 전부 옮긴다. 0.BIN 이 커지므로 build_track 이 디렉터리 크기를 고친다.
    ptrs = collections.defaultdict(list)
    for p in range(0, len(exe) - 3, 4):
        v = struct.unpack_from('>I', exe, p)[0]
        if poc.EXE_BASE <= v < poc.EXE_BASE + len(exe): ptrs[v - poc.EXE_BASE].append(p)
    n_ext = 0
    for o, t in moved:
        if not ptrs.get(o) or any(a <= o < b for a, b in fmt_ranges): bin_skip += 1; continue
        if len(exe) % 2: exe += b'\0'
        at = len(exe); exe += enc(t) + b'\0'
        assert poc.EXE_BASE + len(exe) <= EXT_LIMIT, ('0.BIN 덧붙임 한도 초과', hex(len(exe)))
        for p in ptrs[o]: struct.pack_into('>I', exe, p, poc.EXE_BASE + at)
        n_ext += 1
    # 장면
    offs = [m.start() for m in re.finditer(rb'elfpak\x1a\x00', arc)] + [len(arc)]
    assert len(offs) == 601
    raws, stat = [], collections.Counter()
    for k in range(600):
        raw = elfpak.unpack(arc[offs[k]:offs[k + 1]])[0]
        if rows.get(k):
            raw, nm, nt = rebuild_scene(raw, rows[k], enc, enc_dialog)
            stat['moved'] += nm; stat['tail'] += nt
        assert len(raw) <= LIMIT, ('장면 버퍼 초과', k, len(raw))
        raws.append(raw)
    with ProcessPoolExecutor() as ex:
        blobs = list(ex.map(_pack, raws, chunksize=8))
    newarc = bytearray(); newsec = {}
    for k, b in enumerate(blobs):
        newsec[offs[k] // 2048] = (len(newarc) // 2048, len(b))
        newarc += b + bytes(-len(b) % 2048)
    # 원래 크기를 넘으면 MES.ARC 는 디스크 끝으로 옮긴다(tools/build_track.py — 게임은 GFS 이름으로 연다: 0x0600CA78)
    hit = 0
    for p in range(poc.REC[0], poc.REC[1], 12):
        nptr, sec, size = struct.unpack_from('>III', exe, p)
        name = exe[nptr - poc.EXE_BASE:exe.index(b'\0', nptr - poc.EXE_BASE)]
        if name.endswith(b'.MES') and sec in newsec:
            struct.pack_into('>II', exe, p + 4, *newsec[sec]); hit += 1
    assert hit >= 600, hit
    # 제목 메뉴 · 이름 입력(PoC 그대로)
    tj = poc.TITLE[0].encode('cp932')
    kr = poc.TITLE[1].replace(' ', '　'); padn = len(poc.TITLE[0]) - len(kr)
    tk = enc('　' * (padn // 2) + kr + '　' * (padn - padn // 2)); assert len(tk) == len(tj)
    hits = [m.start() for m in re.finditer(re.escape(tj), exe)]; assert len(hits) == 2
    for p in hits: exe[p:p + len(tj)] = tk
    poc.write_name_grid(exe, enc)
    files = {'0.BIN': exe, 'SJIS2.KNJ': font, 'MES.ARC': newarc}
    # 이름 입력 그림(namegfx bake 결과, GP8·BMP·NAME 은 3장 같은 파일) + GP8 807 위치표 크기(bake 가 디스크 1 기준 PoC 0.BIN 에 적은 값)
    pexe = open(W('poc', '0.BIN'), 'rb').read()
    assert exe[gp8_rec:gp8_rec + 4] == pexe[GP8_REC:GP8_REC + 4]
    exe[gp8_rec + 4:gp8_rec + 8] = pexe[GP8_REC + 4:GP8_REC + 8]
    for n in ('GP8.ARC', 'BMP.ARC', 'NAME.DAT', 'TITLE.DAT'):                     # TITLE.DAT = 제목 로고(tools/titlegfx.py bake)
        assert open(W('disc%d' % disc, n), 'rb').read() == open(W('disc1', n), 'rb').read(), n
        shutil.copyfile(W('poc', n), os.path.join(out, n))          # NAME.DAT = 선택 버튼 4장
    for n, d in files.items():
        open(os.path.join(out, n), 'wb').write(d)
    # 검산: 새 위치표대로 MES.ARC 를 읽어 풀면 새 장면과 같아야 한다(재압축 되풀기는 elfpak.pack 이 이미 확인)
    for k in range(600):
        s, n = newsec[offs[k] // 2048]
        assert elfpak.unpack(bytes(newarc[s * 2048:s * 2048 + n]))[0] == raws[k], k
    sys.stdout.reconfigure(encoding='utf-8')
    print('디스크', disc, '→', out)
    print('새로 그린 글자 %d(글꼴에 없던 부호 %d 포함) · 남긴 일본어 글자 %d · 칸 잃은 글자 %d · 깨져 보일 글자 %d / %d (%.2f%%)'
          % (len(cmap), len(nokeep), len(keep), len(dropped), lost, tot, lost * 100 / tot))
    print('번역할것 파일: MES 원문 %d개 → 조각 %d곳 · 0.BIN 제자리 %d곳 + 끝에 덧붙임 %d곳(0.BIN %d B)(못 넣음 %d) · 거부 %d줄(work/todo/rejected.tsv)'
          % (len(mes), nmes, len(bins), n_ext, len(exe), bin_skip, len(bad)))
    print('옮긴 조각 %d (파일 끝 %d) · 최대 장면 %d / %d · MES.ARC %d / %d' %
          (stat['moved'], stat['tail'], max(map(len, raws)), LIMIT, len(newarc.rstrip(b'\0')), len(arc)))
    open(os.path.join(out, 'font_dropped.txt'), 'w', encoding='utf-8').write(''.join(dropped) + '\n' + ''.join(nokeep))

if __name__ == '__main__':
    main()
