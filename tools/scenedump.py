# -*- coding: utf-8 -*-
"""장면 훑어보기(내용 분류용, 2026-10-23): 장면별로 조각을 {N}·［이름］ 단위 대사로 이어 한 줄씩, 앞 W 글자만.
  python tools/scenedump.py 000 009 [W]"""
import sys, collections
a, b = sys.argv[1], sys.argv[2]; W = int(sys.argv[3]) if len(sys.argv) > 3 else 28
sys.stdout.reconfigure(encoding='utf-8')
cur = None; buf = []
def flush():
    if cur is None: return
    print('=== %s (%d) ===' % (cur, len(buf)))
    print(' | '.join(x[:W] for x in buf))
for l in open('work/sat_tr.tsv', encoding='utf-8'):
    sc, pos, j, k, src = l.rstrip('\n').split('\t')
    if not (a <= sc <= b): continue
    if sc != cur: flush(); cur = sc; buf = []
    if j in ('［',) or j.startswith('］'):
        buf.append(j) if not buf else None
        if buf: buf[-1] += j
        continue
    if buf and (buf[-1].endswith('［') or buf[-1].endswith('：') and len(buf[-1]) < 12):
        buf[-1] += j
    else:
        buf.append(j)
flush()
