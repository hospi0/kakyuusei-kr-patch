# -*- coding: utf-8 -*-
"""번역하지 않고 원문으로 둔 새턴 대사를 한 파일로 모은다 (2026-10-23, 사용자 요청).
대상: tr_new/skip_NN.txt(16~43 건너뜀) + tr_new/drop_01_15.txt(01~15 에서 뺀 줄) + sat_tr_mismatch.tsv(이름 자리 안 맞는 줄)
열: 번호, 구분, 새턴 원문, 번역(빈칸). 참고 번역 칸은 넣지 않는다.
  python tools/export_untranslated.py <출력 파일>"""
import glob, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = lambda *p: os.path.join(ROOT, 'work', *p)

def main(dst):
    ids = {}
    for ln in open(W('tr_new', 'ids.tsv'), encoding='utf-8'):
        i, t = ln.rstrip('\n').split('\t', 1); ids[i] = t
    rows = [(l.strip(), 'drop') for l in open(W('tr_new', 'drop_01_15.txt')) if l.strip()]
    for f in sorted(glob.glob(W('tr_new', 'skip_*.txt'))):
        rows += [(l.strip(), 'skip') for l in open(f) if l.strip()]
    out = ['번호\t구분\t새턴 원문\t번역']
    for i, kind in sorted(rows):
        out.append('\t'.join((i, kind, ids[i], '')))
    for n, ln in enumerate(open(W('sat_tr_mismatch.tsv'), encoding='utf-8'), 1):
        sc, pos, t, _ = ln.rstrip('\n').split('\t')
        out.append('\t'.join(('M%03d' % n, 'mismatch:%s:%s' % (sc, pos), t, '')))
    with open(dst, 'w', encoding='utf-8-sig') as w:
        w.write('\n'.join(out) + '\n')
    sys.stdout.reconfigure(encoding='utf-8')
    print(dst, len(out) - 1, '줄', os.path.getsize(dst), 'B')

if __name__ == '__main__':
    main(sys.argv[1])
