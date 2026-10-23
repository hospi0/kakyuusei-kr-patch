# -*- coding: utf-8 -*-
"""PC 번역 거르기용 훑어보기(2026-10-23). sat_tr.tsv 행 번호(0부터)로 대사 단위 출력: «행번호 원문앞W».
거를 범위는 work/filter/excl.txt 에 «시작행-끝행 이유» 로 적는다(끝행 포함).
  python tools/filtdump.py 시작행 개수 [W]"""
import sys
s0, n = int(sys.argv[1]), int(sys.argv[2]); W = int(sys.argv[3]) if len(sys.argv) > 3 else 30
sys.stdout.reconfigure(encoding='utf-8')
rows = [l.rstrip('\n').split('\t') for l in open('work/sat_tr.tsv', encoding='utf-8')]
out = []; cur = None; last_sc = None
for i in range(s0, min(s0 + n, len(rows))):
    sc, pos, j, k, src = rows[i]
    if sc != last_sc:
        out.append('\n#%s' % sc); last_sc = sc; cur = None
    if cur is not None and (out[-1].endswith('［') or (out[-1].endswith('］：') is False and out[-1].endswith('：') and not j.startswith('］'))):
        out[-1] += j; continue
    out.append("%d %s" % (i, j)); cur = i
print('\n'.join(x if x.startswith('\n') else x[:W + 7] for x in out))
