# -*- coding: utf-8 -*-
"""못 붙은 새턴 줄에 «가장 비슷한 PC 줄»의 번역을 참고로 붙인다 (2026-10-23).
입력 work/sat_match.tsv(방식 '-' 행), work/pc/pairs.tsv.
같은 장면에서 이어지는 '-' 조각은 이름 자리({N})로 한 줄로 묶는다: 앞 조각이 「［」로 끝나거나, 뒤 조각이 「］」·호칭(君 さん ちゃん 先輩 様 くん)으로 시작할 때.
후보 = 글자 3-gram 색인 상위 30개 → difflib 비율 최고.
출력 work/sat_ref.tsv: 장면, 조각위치, 새턴 원문, 유사도, PC 원문, PC 번역."""
import collections, difflib, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HON = ('］', '君', 'さん', 'ちゃん', '先輩', '様', 'くん')

def grams(s):
    return {s[i:i + 3] for i in range(len(s) - 2)}

def main():
    pairs = {}
    for ln in open(os.path.join(ROOT, 'work', 'pc', 'pairs.tsv'), encoding='utf-8'):
        f, a, j, k, kind = ln.rstrip('\n').split('\t')
        pairs.setdefault(j, k)
    pj = list(pairs); idx = collections.defaultdict(list)
    for n, s in enumerate(pj):
        for g in grams(s): idx[g].append(n)
    rows = [ln.rstrip('\n').split('\t') for ln in open(os.path.join(ROOT, 'work', 'sat_match.tsv'), encoding='utf-8')]
    lines = []
    for r in rows:
        if r[4] != '-':
            lines.append(None); continue
        if lines and lines[-1] and lines[-1][0] == r[0] and (lines[-1][2].endswith('［') or r[2].startswith(HON)):
            sc, pos, t = lines[-1]; lines[-1] = (sc, pos + ',' + r[1], t + '{N}' + r[2])
        else:
            lines.append((r[0], r[1], r[2]))
    lines = [x for x in lines if x]
    seen = {}; out = []
    for sc, pos, t in lines:
        if t not in seen:
            c = collections.Counter()
            for g in grams(t):
                if len(idx.get(g, ())) < 2000:
                    c.update(idx[g])
            best = (0.0, '', '')
            for n, _ in c.most_common(30):
                r = difflib.SequenceMatcher(None, t, pj[n], autojunk=False).ratio()
                if r > best[0]: best = (r, pj[n], pairs[pj[n]])
            seen[t] = best
        b = seen[t]; out.append((sc, pos, t, '%.2f' % b[0], b[1], b[2]))
    with open(os.path.join(ROOT, 'work', 'sat_ref.tsv'), 'w', encoding='utf-8') as w:
        for r in out: w.write('\t'.join(r) + '\n')
    u = {r[2]: float(r[3]) for r in out}
    bands = collections.Counter('0.9↑' if v >= .9 else '0.7~0.9' if v >= .7 else '0.5~0.7' if v >= .5 else '0.5↓' for v in u.values())
    chars = collections.Counter()
    for t, v in u.items():
        chars['0.9↑' if v >= .9 else '0.7~0.9' if v >= .7 else '0.5~0.7' if v >= .5 else '0.5↓'] += len(t)
    sys.stdout.reconfigure(encoding='utf-8')
    print('못 붙은 고유 줄', len(u), '유사도 분포(줄)', dict(bands), '(글자)', dict(chars))

if __name__ == '__main__':
    main()
