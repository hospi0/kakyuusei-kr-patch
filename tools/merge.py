# -*- coding: utf-8 -*-
"""새턴 대사 조각 ↔ 한국어 번역 합치기 → work/sat_tr.tsv (2026-10-23).
출처 우선순위
  pc    = PC 한글판 완전 일치(work/sat_match.tsv 방식 f/b)
  mine  = work/tr_new/out_NN.tsv (drop_01_15.txt 에 든 번호는 뺀다)
  (없음) = 번역 비움 → 빌드 때 일본어 원문 유지
손보는 것(번역 내용은 그대로): 전각 공백→공백, 【】→［］, 문장부호 뒤 공백 삭제, 겹친 공백 하나로,
  본문만 일치(b)한 PC 줄의 이름표는 새턴 원문 이름표를 work/tags.tsv 대응으로 옮긴 것,
  {N} 으로 이은 줄을 새턴 조각 단위로 다시 나눔(조각 수가 다르면 그 줄은 비우고 보고).
출력 열: 장면, 조각위치(16진), 원문 조각, 번역 조각(비면 원문 유지), 출처"""
import collections, glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = lambda *p: os.path.join(ROOT, 'work', *p)
PUNCT = '，．、。？！…～・：'
EXTRA_TAGS = {'マスター': '마스터', 'おまかせじいさん': '오마카세 할아범', '怪しいじいさん': '수상한 할아범'}

def tag_map():
    m = dict(EXTRA_TAGS)
    for ln in open(W('tags.tsv'), encoding='utf-8'):
        jp, n, kr = ln.rstrip('\n').split('\t')
        if kr != '-' and jp not in m:
            m[jp] = re.sub(r'\(\d+\)$', '', kr.split(' / ')[0]).replace('　', ' ')
    return m

def norm(s):
    s = s.replace('　', ' ').replace('【', '［').replace('】', '］')
    s = re.sub(' {2,}', ' ', s)
    s = re.sub('([%s]) +' % re.escape(PUNCT), r'\1', s)
    return s.strip(' ')

def retag(jp, kr, tags):
    """본문만 일치한 줄: 번역 쪽 이름표를 새턴 원문 이름표의 한국어로."""
    m = re.match('［([^］{}]*)］：', jp)
    if not m or '］：' not in kr:
        return kr, True
    k = tags.get(m.group(1))
    if k is None:
        return kr, False
    return '［%s］：' % k + kr.split('］：', 1)[1], True

def main():
    tags = tag_map()
    ids = {}
    for ln in open(W('tr_new', 'ids.tsv'), encoding='utf-8'):
        i, t = ln.rstrip('\n').split('\t', 1); ids[t] = i
    drop = {l.strip() for l in open(W('tr_new', 'drop_01_15.txt')) if l.strip()}
    mine = {}
    for f in sorted(glob.glob(W('tr_new', 'out_*.tsv'))):
        for ln in open(f, encoding='utf-8'):
            if ln.strip():
                i, k = ln.rstrip('\n').split('\t');
                if i not in drop: mine[i] = k
    # '-' 줄은 sat_ref.tsv 가 이름 자리로 묶은 단위를 쓴다
    ref_lines = {}
    for ln in open(W('sat_ref.tsv'), encoding='utf-8'):
        sc, pos, t = ln.rstrip('\n').split('\t')[:3]
        ref_lines[(sc, pos.split(',')[0])] = (pos, t)
    fix = {}
    fp = W('tr_fix_mismatch.tsv')
    if os.path.exists(fp):                      # 조각 수 안 맞던 줄의 이름 자리 맞춤(tools/fixmismatch.py)
        for ln in open(fp, encoding='utf-8'):
            sc, pos, k = ln.rstrip('\n').split('\t'); fix[(sc, pos)] = k
    out = []; stat = collections.Counter(); bad = []; notag = collections.Counter()
    rows = [l.rstrip('\n').split('\t') for l in open(W('sat_match.tsv'), encoding='utf-8')]
    done = set()
    for sc, pos, t, kr, how in rows:
        if how == '-':
            key = (sc, pos.split(',')[0])
            if key in done or key not in ref_lines:
                continue
            pos, t = ref_lines[key]
            for p in pos.split(','):
                done.add((sc, p))
            i = ids.get(t); kr = mine.get(i, '') if i else ''
            src = 'mine' if kr else ''
        else:
            src = 'pc'
            if how == 'b':
                kr, ok = retag(t, kr, tags)
                if not ok: notag[re.match('［([^］]*)］', t).group(1)] += 1
        if (sc, pos) in fix:
            kr, src = fix[(sc, pos)], 'fix'
        poss = pos.split(',')
        jp_pieces = t.split('{N}')
        lead = len(jp_pieces) == len(poss) + 1          # 앞에 공유 「［」 를 붙여 맞춘 줄
        if lead: jp_pieces = jp_pieces[1:]
        kr_pieces = []
        if kr:
            kr_pieces = norm(kr).split('{N}')
            if lead:
                if kr_pieces and kr_pieces[0].strip() in ('［', ''):
                    kr_pieces = kr_pieces[1:]
                else:
                    kr_pieces = None
            if kr_pieces is None or len(kr_pieces) != len(jp_pieces):
                bad.append((sc, pos, t, kr)); kr_pieces = []; src = ''
        for k, (p, jpp) in enumerate(zip(poss, jp_pieces)):
            out.append((sc, p, jpp, kr_pieces[k] if kr_pieces else '', src if kr_pieces else ''))
        stat[src or 'jp'] += sum(len(x) for x in jp_pieces)
    with open(W('sat_tr.tsv'), 'w', encoding='utf-8') as w:
        for r in out: w.write('\t'.join(r) + '\n')
    with open(W('sat_tr_mismatch.tsv'), 'w', encoding='utf-8') as w:
        for r in bad: w.write('\t'.join(r) + '\n')
    sys.stdout.reconfigure(encoding='utf-8')
    tot = sum(stat.values())
    print('조각', len(out), '원문 글자', tot)
    for k in ('pc', 'mine', 'fix', 'jp'):
        print(' %-5s %8d자 %5.1f%%' % (k, stat[k], stat[k] * 100 / tot))
    print('조각 수 안 맞아 원문으로 둔 줄', len(bad), '→ work/sat_tr_mismatch.tsv')
    print('이름표 대응 없음(일본어 이름표 남음)', sum(notag.values()), notag.most_common(10))

if __name__ == '__main__':
    main()
