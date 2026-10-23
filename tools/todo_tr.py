# -*- coding: utf-8 -*-
"""번역할것_NN.tsv(tools/export_todo.py 형식)에 채운 번역을 읽어 검사한다 (2026-10-23).
읽는 곳: work/todo_tr/*.tsv(사용자가 준 번역 파일 — 받으면 여기로 복사) → 없으면 work/todo/*.tsv. 같은 번호는 todo_tr 우선.
열 이름으로 찾는다(번호·구분·원문·예산·번역). 번역 칸이 빈 줄은 건너뛴다.
적재 때 막는 것(어기면 그 줄은 넣지 않고 work/todo/rejected.tsv 에 이유와 함께 남김):
  - 원문 토큰: 「］：」로 시작하면 번역도, 「［이름］：」 이름표가 있으면 번역도, ［］『』「」● 개수가 같아야 함
  - 조사 표시는 {이가}{을를}{은는}{와과}{아야}{이} 만, 탭·줄바꿈 없음, 글자는 한글 또는 SJIS 로 쓸 수 있는 것
  - 0BIN: 번역 글자 수(공백 포함) ≤ 예산
  python tools/todo_tr.py      # 검사만(몇 줄 들어가는지·거부 목록)"""
import glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = lambda *p: os.path.join(ROOT, 'work', *p)
TOKENS = '［］『』「」●￥'
PART = re.compile(r'\{(이가|을를|은는|와과|아야|이)\}')

_tag_cache = []

def _tags():
    if not _tag_cache:
        import merge
        _tag_cache.append(merge.tag_map())
    return _tag_cache[0]

def _files():
    seen = {}
    for d in ('todo', 'todo_tr'):                      # 뒤가 앞을 덮는다
        for f in sorted(glob.glob(W(d, '*.tsv'))):
            if os.path.basename(f).startswith('rejected'): continue
            seen.setdefault(d, []).append(f)
    return seen.get('todo', []) + seen.get('todo_tr', [])

def check(jp, tr):
    if '\t' in tr or '\n' in tr: return '탭·줄바꿈'
    if jp.startswith('］：') and not tr.startswith('］：'): return '「］：」로 시작해야 함'
    if re.match('［[^］]*］：', jp) and not re.match('［[^］]+］：', tr): return '이름표 「［…］：」 없음'
    for t in TOKENS:
        if jp.count(t) != tr.count(t): return '「%s」 개수 %d≠%d' % (t, jp.count(t), tr.count(t))
    rest = PART.sub('', tr)
    if '{' in rest or '}' in rest: return '알 수 없는 {} 표시'
    for c in rest:
        if 0xAC00 <= ord(c) <= 0xD7A3 or c == ' ': continue
        try:
            if len(c.encode('cp932')) != 2: return '반각 글자 「%s」' % c
        except UnicodeEncodeError:
            return 'SJIS 에 없는 글자 「%s」' % c
    return None

def load():
    """→ mes {원문: 번역}, bin {0.BIN 오프셋(디스크 1): (원문, 번역, 예산)}, 거부 목록"""
    import import_user_tr                              # 서로 부르므로 여기서
    rows = {}
    for f in _files():
        lines = open(f, encoding='utf-8-sig').read().split('\n')
        head = lines[0].split('\t'); col = {n: i for i, n in enumerate(head)}
        if not {'번호', '구분', '원문', '번역'} <= set(col): continue          # 다른 표(넘침 목록 등)는 건너뜀
        for ln in lines[1:]:
            if not ln.strip(): continue
            c = ln.split('\t') + [''] * len(head)
            tr = c[col['번역']].strip()
            if tr: rows[c[col['번호']]] = (c[col['구분']], c[col['원문']], tr, c[col['예산']], os.path.basename(f))
    mes, binr, bad = {}, {}, []
    for no, (kind, jp, tr, bud, fn) in sorted(rows.items()):
        if kind == 'MES':                              # 반각 부호·숫자 → 전각, 이름표 → tags.tsv 표기(import_user_tr 와 같은 손질)
            tr = import_user_tr.norm(jp, tr, _tags())
        tr = import_user_tr.quotes(tr).translate(import_user_tr.HALF).replace('　', ' ')
        for tok in ('］：', '●', '￥'):                  # 원문 맨 앞 토큰이 번역에서 빠졌으면 붙인다(사용자 지시: 맞는 토큰으로)
            if jp.startswith(tok) and not tr.startswith(tok) and tr.count(tok[0]) < jp.count(tok[0]):
                tr = tok + tr.lstrip(' ')
        tr = re.sub('([，．、。？！…～・：]) +', r'\1', tr)        # 문장부호 뒤 공백(빌더 규칙) — 예산 재기 전에
        if kind.startswith('0BIN'):                    # 화면 문자열의 ［］(장소 이름 등)는 제어 토큰이 아님 — 글자 수 예산만
            why = check(jp.replace('［', '').replace('］', ''), tr.replace('［', '').replace('］', ''))
        else:
            why = check(jp, tr)
        # 0BIN 예산 넘침은 거부하지 않는다 — build_kr 가 0.BIN 끝(RAM 0x0609C6D8~)에 덧붙이고 포인터를 옮긴다
        if why:
            bad.append((no, kind, jp, tr, why, fn)); continue
        if kind == 'MES':
            mes[jp] = tr
        else:
            binr[int(kind.split(':')[1], 16)] = (jp, tr, int(bud))
    with open(W('todo', 'rejected.tsv'), 'w', encoding='utf-8-sig') as w:
        w.write('번호\t구분\t원문\t번역\t이유\t파일\n')
        for r in bad: w.write('\t'.join(r) + '\n')
    return mes, binr, bad

def bin_text(exe, off, jp, tr, bud):
    """0.BIN 제자리 문자열: 원래 앞쪽 전각 공백(들여쓰기)은 남는 만큼 살리고, 원래 뒤를 전각 공백으로 채웠으면 같은 폭으로 채움.
    → (새 문자열, 원래 바이트 길이). 원문 확인 실패면 None."""
    end = exe.index(b'\0', off)
    try:
        s = bytes(exe[off:end]).decode('cp932')
    except UnicodeDecodeError:
        return None
    if s.strip('　') != jp or len(s) != bud: return None
    lead = len(s) - len(s.lstrip('　'))
    padded = s.endswith('　')
    if padded or lead:                                 # 메뉴 칸(공백으로 채운 줄)은 원문 글자 가운데에 맞춤(「하급생 이어하기」와 같게)
        lead += max(0, len(jp) - len(tr)) // 2
    lead = min(lead, bud - len(tr))                  # ⛔메뉴 칸은 원래 글자 수만 그린다 — 예산 넘기는 정렬 금지(2026-10-23 «機» 깨짐, 사용자 «정렬하지마»)
    t = '　' * lead + tr
    if padded: t += '　' * (bud - len(t))
    return t, end - off

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    mes, binr, bad = load()
    print('읽은 파일', len(_files()), '· MES %d · 0.BIN %d · 거부 %d → work/todo/rejected.tsv' % (len(mes), len(binr), len(bad)))
    for r in bad[:20]: print(' ', r[0], r[4], '|', r[2], '→', r[3])
