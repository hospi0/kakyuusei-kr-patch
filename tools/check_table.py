# -*- coding: utf-8 -*-
"""받은 번역표 검사 (2026-10-24, 사용자 «번역 내용은 확인하지 말고 넘치거나 문제 있는 곳만»).
번역 내용은 보지 않고 기계 검사만:
  ① 조각 검사 = todo_tr.check(토큰 ［］『』「」●￥ 개수·이름표·「］：」 시작·반각·SJIS 에 없는 글자·{} 표시) + 원문은 있는데 번역 빈칸
  ② 시스템 표: 예산(원래 글자 수) 넘침(빌더가 0.BIN 끝으로 옮김 — 메뉴 칸이면 잘림)·형식 문자열 %… 개수·순서
  ③ 글꼴: plan_font 를 font_map.tsv 고정 그대로 돌려 칸 부족(assert)·새로 필요한 글자 수·칸 잃는 일본어 글자 수(쓰지 않음)
비교 기준 = 다른 폴더의 번역표(지금 패치 = export_table 결과)에 같은 검사 → «새로 생긴 문제»만 따로 셈.
  python tools/check_table.py <번역표 폴더> [<기준 폴더>]  → work/check_table.tsv"""
import collections, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import build_kr as b, todo_tr

def rows_of(d):
    out = []
    for ln in open(os.path.join(d, '번역표_대사.tsv'), encoding='utf-8-sig').read().split('\n')[1:]:
        if not ln.strip(): continue
        sc, pos, jp, kr = (ln.rstrip('\r').split('\t') + [''])[:4]
        out.append((sc, pos, jp, kr))
    sysr = []
    for ln in open(os.path.join(d, '번역표_시스템.tsv'), encoding='utf-8-sig').read().split('\n')[1:]:
        if not ln.strip(): continue
        sysr.append(tuple((ln.rstrip('\r').split('\t') + ['', ''])[:4]))
    return out, sysr

FMT = re.compile(r'%[0-9]*[a-z]')

def problems(d):
    rows, sysr = rows_of(d); P = []
    for sc, pos, jp, kr in rows:
        if not kr.strip():
            if re.search('[ぁ-ヾ一-鿿]', jp): P.append(('빈 번역', sc, pos, jp, kr))
            continue
        why = todo_tr.check(jp, kr)
        if why: P.append((why, sc, pos, jp, kr))
    for o, jp, kr, bud in sysr:
        if not kr.strip(): continue
        if FMT.findall(jp) != FMT.findall(kr): P.append(('형식 %… 다름', 'SYS', o, jp, kr))
        why = todo_tr.check(jp, kr)
        if why and o != 'FMT': P.append(('시스템 ' + why, 'SYS', o, jp, kr))
        if o != 'FMT' and len(b.clean(kr)) > int(bud): P.append(('시스템 예산 %s > %s' % (len(b.clean(kr)), bud), 'SYS', o, jp, kr))
    return P

def font(d):
    old = b.TABLE_DIR; b.TABLE_DIR = d
    try:
        rows, binr, fmt = b.load_table()
    finally:
        b.TABLE_DIR = old
    exe = open(b.W('disc1', '0.BIN'), 'rb').read()
    pinned = {}
    for ln in open(b.W('font_map.tsv'), encoding='utf-8'):
        ch, c = ln.rstrip('\n').split('\t'); pinned[ch] = int(c, 16)
    others = [s for dd in (2, 3) for s in b.ui_strings(open(b.W('disc%d' % dd, '0.BIN'), 'rb').read())]
    extra = [b.clean(kr) for _, (jp, kr, bud) in binr.items()] + others + [k for _, k in fmt]
    try:
        cmap, keep, dropped, nokeep, lost, tot = b.plan_font(exe, rows, extra, set(binr), pinned)
    except AssertionError as e:
        return '칸 부족 %s' % (e,)
    new = [c for c in cmap if c not in pinned]
    return '배정 %d자(새 글자 %d: %s) · 칸 잃는 일본어 %d자 · 남은 일본어 중 깨져 보일 글자 %d/%d' % (
        len(cmap), len(new), ''.join(sorted(new))[:80], len(dropped), lost, tot)

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    d = sys.argv[1]; base = sys.argv[2] if len(sys.argv) > 2 else None
    P = problems(d)
    seen = set()
    if base:
        seen = {(w.split(' ')[0], sc, pos) for w, sc, pos, _, _ in problems(base)}
    out = ['구분\t새로 생김\t장면\t위치\t원문\t번역']
    cnt = collections.Counter(); newc = collections.Counter()
    for why, sc, pos, jp, kr in P:
        k = why.split(' ')[0]; isnew = (k, sc, pos) not in seen
        cnt[k] += 1; newc[k] += isnew
        out.append('\t'.join((why, 'Y' if isnew else '', sc, pos, jp, kr)))
    open(b.W('check_table.tsv'), 'w', encoding='utf-8-sig').write('\n'.join(out) + '\n')
    print('조각·시스템 문제 %d (새로 생김 %d) → work/check_table.tsv' % (len(P), sum(newc.values())))
    for k, v in cnt.most_common(): print('  %s %d (새 %d)' % (k, v, newc[k]))
    print('글꼴:', font(d))
    if base: print('기준 글꼴:', font(base))

if __name__ == '__main__':
    main()
