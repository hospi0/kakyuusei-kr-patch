# -*- coding: utf-8 -*-
"""in_NN 번호 중 out_NN 에 없는 것을 skip_NN.txt 로 적는다(연애·성적 내용이라 번역하지 않은 줄). python tools/mkskip.py NN"""
import os, sys
D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work', 'tr_new')
for n in sys.argv[1:]:
    ids = [l.split('\t')[0] for l in open(os.path.join(D, 'in_%s.tsv' % n), encoding='utf-8') if l.strip()]
    done = {l.split('\t')[0] for l in open(os.path.join(D, 'out_%s.tsv' % n), encoding='utf-8') if l.strip()}
    sk = [i for i in ids if i not in done]
    open(os.path.join(D, 'skip_%s.txt' % n), 'w').write('\n'.join(sk) + '\n')
    print(n, '번역', len(done), '건너뜀', len(sk))
