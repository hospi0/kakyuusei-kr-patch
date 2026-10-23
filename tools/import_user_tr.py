# -*- coding: utf-8 -*-
"""사용자 번역(export_untranslated.py 형식: 번호·구분·새턴 원문·번역) → 새턴 조각 단위 work/tr_user.tsv (2026-10-23).
구분 skip/drop = tr_new/ids.tsv 번호 → sat_ref.tsv 의 조각 위치들(같은 원문이면 전부), mismatch:장면:위치[,위치] = 그 위치.
{N}(주인공 이름 자리)으로 나눠 조각에 붙인다(merge.py 와 같은 규칙: 원문 조각이 위치보다 하나 많으면 맨 앞 공유 「［」 를 뺌).
손보는 것(번역 내용은 그대로): 반각 부호·숫자 → 전각(PC 판 표기와 같게), 「。、」→「．，」, 이름표 → tags.tsv 표기,
  문장부호 뒤 공백은 build_kr.clean 이 지운다. 원문 토큰(［］『』「」●￥·{N} 개수·「］：」 시작)이 안 맞으면 넣지 않고 보고.
출력 열: 장면, 위치(16진), 번역 조각 — build_kr 가 번역이 빈 조각에 씀.
  python tools/import_user_tr.py <번역 파일>"""
import collections, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import merge, todo_tr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = lambda *p: os.path.join(ROOT, 'work', *p)
HALF = str.maketrans({'.': '．', ',': '，', '?': '？', '!': '！', ':': '：', '(': '（', ')': '）', '~': '～', '%': '％',
                      '。': '．', '、': '，', '·': '・', '[': '［', ']': '］', **{str(d): chr(0xFF10 + d) for d in range(10)}})

HALF.update({c: c - 0x41 + 0xFF21 for c in range(0x41, 0x5B)})       # A-Z → Ａ-Ｚ
HALF.update({c: c - 0x61 + 0xFF41 for c in range(0x61, 0x7B)})       # a-z → ａ-ｚ

def quotes(s):
    """반각 ' " → ‘’ “”(번갈아 여닫음). ⛔전각 ＇＂ 는 cp932 에서 IBM 확장 코드라 쓰지 않는다."""
    for q, (o, c) in (("'", '‘’'), ('"', '“”')):
        parts = s.split(q)
        s = parts[0] + ''.join((o if i % 2 == 0 else c) + p for i, p in enumerate(parts[1:]))
    return s

def norm(jp, kr, tags):
    k = quotes(kr.replace('{N}', '\0')).translate(HALF).replace('\0', '{N}')
    k = k.replace('　', ' ')
    m = re.match('［([^］{}]*)］：', jp)
    if m and m.group(1) in tags:                      # 이름표는 대응표 표기로(시즈카 선생님 → 시즈카 선생 등)
        k = re.sub('^［[^］]*］：', '［%s］：' % tags[m.group(1)], k)
    return k.strip(' ')

def main(src):
    sys.stdout.reconfigure(encoding='utf-8')
    tags = merge.tag_map()
    ids = {}
    for ln in open(W('tr_new', 'ids.tsv'), encoding='utf-8'):
        i, t = ln.rstrip('\n').split('\t', 1); ids[i] = t
    units = collections.defaultdict(list)            # 원문 단위 → [(장면, [위치…])]
    for ln in open(W('sat_ref.tsv'), encoding='utf-8'):
        sc, pos, t = ln.rstrip('\n').split('\t')[:3]
        units[t].append((sc, pos.split(',')))
    done = set()
    for ln in open(W('sat_tr.tsv'), encoding='utf-8'):
        c = ln.rstrip('\n').split('\t')
        if c[3]: done.add(c[2])
    lines = open(src, encoding='utf-8-sig').read().split('\n')
    out, bad, stat = {}, [], collections.Counter()
    for ln in lines[1:]:
        if not ln.strip(): continue
        no, kind, jp, kr = ln.split('\t')[:4]
        kr = norm(jp, kr.strip(), tags)
        if kind.startswith('mismatch:'):
            _, sc, pos = kind.split(':'); targets = [(sc, pos.split(','))]
        else:
            if ids.get(no) != jp: bad.append((no, '번호↔원문 불일치', jp, kr)); continue
            targets = units.get(jp, [])
        if not targets:
            if jp in done: stat['이미 번역됨'] += 1; continue      # 7차에서 PC 번역이 붙은 줄
            bad.append((no, '위치 없음', jp, kr)); continue
        jps, krs = jp.split('{N}'), kr.split('{N}')
        if len(jps) != len(krs): bad.append((no, '{N} 개수', jp, kr)); continue
        for sc, poss in targets:
            jj, kk = jps, krs
            if len(jj) == len(poss) + 1:              # 맨 앞 공유 「［」
                if kk[0].strip() not in ('［', ''): bad.append((no, '앞 「［」', jp, kr)); break
                jj, kk = jj[1:], kk[1:]
            if len(jj) != len(poss): bad.append((no, '조각 수', jp, kr)); break
            for p, j, k in zip(poss, jj, kk):
                why = todo_tr.check(j, k.strip(' '))
                if why: bad.append((no, why, j, k)); break
            else:
                for p, k in zip(poss, kk): out[(sc, p)] = k.strip(' ')
                stat[kind.split(':')[0]] += 1
    with open(W('tr_user.tsv'), 'w', encoding='utf-8') as w:
        for (sc, p), k in sorted(out.items()): w.write('%s\t%s\t%s\n' % (sc, p, k))
    with open(W('tr_user_rejected.tsv'), 'w', encoding='utf-8-sig') as w:
        w.write('번호\t이유\t원문\t번역\n')
        for r in bad: w.write('\t'.join(r) + '\n')
    print('넣은 줄', dict(stat), '· 조각', len(out), '→ work/tr_user.tsv · 거부', len(bad), '→ work/tr_user_rejected.tsv')
    for r in bad[:15]: print(' ', r[0], r[1], '|', r[2][:30], '→', r[3][:30])

if __name__ == '__main__':
    main(sys.argv[1])
