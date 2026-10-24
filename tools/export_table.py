# -*- coding: utf-8 -*-
"""작업 키트용 번역표·원문 뽑기 (2026-10-23).
지금까지의 번역(sat_tr + tr_user + 번역할것 파일 + tr_fix_kun + 빌드 때 자동 손질)을 build_kr 와 똑같이 합친 «최종 번역»을
번역표 두 개로 쓴다. 가운데 맞춤 채움은 빌더가 다시 하므로 표에는 넣지 않는다.
  <출력>/번역/번역표_대사.tsv   장면·위치(장면 파일 안 16진)·원문·번역 — 모든 대사·선택지 조각(번역 빈칸 = 원문 그대로)
  <출력>/번역/번역표_시스템.tsv 위치(디스크 1 0.BIN 16진, FMT = 세이브 화면 형식 문자열)·원문·번역·예산(원래 글자 수)
  <출력>/원문/원문_대사.txt      장면별 일본어 원문 읽기용(조각을 한 줄씩)
  <출력>/원문/원문_시스템.tsv    디스크 1 0.BIN 의 화면 문자열 전부(위치·원문)
  python tools/export_table.py <출력 폴더> [빈칸]   # 빈칸 = 번역 칸을 비운 키트용(원문·위치·예산만)"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import build_kr, todo_tr

def main():
    out = sys.argv[1]; blank = '빈칸' in sys.argv[2:]
    for d in ('번역', '원문'): os.makedirs(os.path.join(out, d), exist_ok=True)
    mes, binr, bad = todo_tr.load()
    rows, _ = build_kr.load_rows(mes, centered=False)
    n = nk = 0
    with open(os.path.join(out, '번역', '번역표_대사.tsv'), 'w', encoding='utf-8-sig', newline='\n') as w, \
         open(os.path.join(out, '원문', '원문_대사.txt'), 'w', encoding='utf-8-sig', newline='\n') as t:
        w.write('장면\t위치\t원문\t번역\n')
        for sc in sorted(rows):
            t.write('=== 장면 %03d ===\n' % sc)
            for pos, jp, kr in rows[sc]:
                assert '\t' not in kr and '\n' not in kr
                if blank: kr = ''
                w.write('%03d\t%X\t%s\t%s\n' % (sc, pos, jp, kr)); n += 1; nk += bool(kr)
                t.write(jp + '\n')
    with open(os.path.join(out, '번역', '번역표_시스템.tsv'), 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('위치\t원문\t번역\t예산\n')
        for jp, kr in build_kr.FMT_PATCHES:
            w.write('FMT\t%s\t%s\t%d\n' % (jp, '' if blank else kr, len(jp)))
        for off, (jp, tr, bud) in sorted(binr.items()):
            w.write('%X\t%s\t%s\t%d\n' % (off, jp, '' if blank else tr, bud))
    exe = open(build_kr.W('disc1', '0.BIN'), 'rb').read()
    m_all = 0
    with open(os.path.join(out, '원문', '원문_시스템.tsv'), 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('위치\t원문\n')
        for m in re.finditer(rb'(?:[\x81-\x84\x88-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc]){2,}(?=\x00)', exe):
            try:
                s = m.group().decode('cp932')
            except UnicodeDecodeError:
                continue
            if re.search('[ぁ-ヾ一-鿿]', s): w.write('%X\t%s\n' % (m.start(), s)); m_all += 1
    sys.stdout.reconfigure(encoding='utf-8')
    print('대사 조각 %d(번역 %d) · 시스템 %d(+형식 %d) · 0.BIN 원문 %d · 거부 %d' % (n, nk, len(binr), len(build_kr.FMT_PATCHES), m_all, len(bad)))

if __name__ == '__main__':
    main()
