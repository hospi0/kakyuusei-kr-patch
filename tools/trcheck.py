# -*- coding: utf-8 -*-
"""새 번역(work/tr_new/out_NN.tsv = 번호<TAB>한국어) 검사 — 쓰는 즉시 돌린다 (2026-10-23).
막는 것: 없는 번호·중복 번호·빈 번역·{N} 개수 다름·《》『』「」（）［］ 개수 다름·가나 남음·탭/개행.
경고: 원문 줄 끝 부호(。？！…)와 번역 끝 부호 종류가 다름.
  python tools/trcheck.py [NN ...]   (없으면 있는 out 전부)"""
import glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOK = '《》『』「」（）［］￥'
KANA = re.compile('[ぁ-ゖァ-ヺ]')

def banner():
    print('[규칙] {N}·《》『』「」（）［］ 개수 그대로 / 가나 금지 / 이름표는 PC판 표기(work/tags.tsv) / '
          '인물 말투는 PC 번역을 따른다 / 부호 뒤 공백은 빌더가 뗀다')

def main(args):
    banner()
    src = dict(l.rstrip('\n').split('\t', 1) for l in open(os.path.join(ROOT, 'work', 'tr_new', 'ids.tsv'), encoding='utf-8'))
    files = [os.path.join(ROOT, 'work', 'tr_new', 'out_%s.tsv' % a) for a in args] if args else \
        sorted(glob.glob(os.path.join(ROOT, 'work', 'tr_new', 'out_*.tsv')))
    errs = []; warns = []; seen = {}
    for f in files:
        for n, ln in enumerate(open(f, encoding='utf-8'), 1):
            ln = ln.rstrip('\n')
            if not ln: continue
            if ln.count('\t') != 1:
                errs.append('%s:%d 열 수' % (os.path.basename(f), n)); continue
            i, kr = ln.split('\t')
            where = '%s:%s' % (os.path.basename(f), i)
            if i not in src: errs.append(where + ' 없는 번호'); continue
            if i in seen: errs.append(where + ' 중복(%s)' % seen[i])
            seen[i] = os.path.basename(f)
            jp = src[i]
            if not kr.strip(): errs.append(where + ' 빈 번역')
            if jp.count('{N}') != kr.count('{N}'): errs.append(where + ' {N} %d≠%d' % (jp.count('{N}'), kr.count('{N}')))
            for c in TOK:
                if jp.count(c) != kr.count(c): errs.append(where + ' %s %d≠%d' % (c, jp.count(c), kr.count(c)))
            if KANA.search(kr): errs.append(where + ' 가나 남음: ' + kr)
            ej = jp.rstrip('）」』')[-1:]; ek = kr.rstrip('）」』')[-1:]
            same = {'。': '.．', '？': '?？', '！': '!！'}
            if ej in same and ek not in same[ej]: warns.append(where + ' 끝 부호 %s→%s' % (ej, ek))
    for e in errs: print('막음', e)
    for w in warns[:30]: print('경고', w)
    print('검사 %d줄, 막음 %d, 경고 %d, 전체 %d줄 중 완료 %d' % (len(seen), len(errs), len(warns), len(src), len(seen)))
    return 1 if errs else 0

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main(sys.argv[1:]))
