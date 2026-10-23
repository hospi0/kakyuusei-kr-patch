# -*- coding: utf-8 -*-
"""새턴 대사 조각에 PC 한글판 번역 붙이기 (2026-10-23, 시험판).
연속 조각 k개(5→1)를 {N} 으로 이어 PC 원문 줄과 «완전 일치»를 찾는다. 이름표가 달라도 «］：» 뒤 본문이 같으면 붙인다.
「］」로 시작하는 조각은 앞에 「［{N}」를 붙여 본다(새턴은 「［」 문자열 하나를 여러 줄이 같이 쓴다).
출력 work/sat_match.tsv: 장면, 조각위치들, 새턴 원문, PC 번역(없으면 빈칸), 방식(f=줄 전체 / b=본문만 / -=없음)."""
import collections, glob, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import satlines

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_pairs():
    full = {}; body = {}
    for ln in open(os.path.join(ROOT, 'work', 'pc', 'pairs.tsv'), encoding='utf-8'):
        f, a, j, k, kind = ln.rstrip('\n').split('\t')
        full.setdefault(j, k)
        if '］：' in j and '】：' in k:
            body.setdefault(j.split('］：', 1)[1], k.split('】：', 1)[1])
    return full, body

if __name__ == '__main__':
    full, body = load_pairs()
    tot = cov = 0; unm = collections.Counter(); rows = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'work', 'disc1', 'mes', '*.bin'))):
        sc = os.path.basename(f)[:3]
        ps = [(a, s.decode('cp932', 'replace')) for a, s in satlines.pieces(open(f, 'rb').read())]
        i = 0
        while i < len(ps):
            hit = None
            for k in (5, 4, 3, 2, 1):
                if i + k > len(ps): continue
                t = '{N}'.join(x[1] for x in ps[i:i + k])
                if t.startswith('］'):          # 「［」는 파일에 한 번만 두고 같이 쓴다(문자열 합치기)
                    t = '［{N}' + t
                if t in full: hit = (k, 'f', t, full[t]); break
                if '］：' in t and t.split('］：', 1)[1] in body:
                    hit = (k, 'b', t, t.split('］：', 1)[0] + '］：' + body[t.split('］：', 1)[1]]); break
            k = hit[0] if hit else 1
            t = hit[2] if hit else ps[i][1]
            n = sum(len(x[1]) for x in ps[i:i + k]); tot += n
            if hit: cov += n
            else: unm[t] += 1
            rows.append((sc, ','.join('%X' % x[0] for x in ps[i:i + k]), t, hit[3] if hit else '', hit[1] if hit else '-'))
            i += k
    with open(os.path.join(ROOT, 'work', 'sat_match.tsv'), 'w', encoding='utf-8') as w:
        for r in rows: w.write('\t'.join(r) + '\n')
    sys.stdout.reconfigure(encoding='utf-8')
    print('새턴 조각 글자', tot, '번역 붙음', cov, '%.1f%%' % (cov * 100 / tot), '못 붙은 고유', len(unm), '글자', sum(len(s) for s in unm))
    for s, n in sorted(unm.items(), key=lambda x: -len(x[0]) * x[1])[:int(os.environ.get('TOP', '12'))]:
        print(n, s[:70])
