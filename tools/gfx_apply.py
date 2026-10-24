# -*- coding: utf-8 -*-
"""작업 키트: 한글 그림(이름 입력 글자판·버튼 = GP8.ARC·BMP.ARC·NAME.DAT, 제목 로고 = TITLE.DAT)과
GP8 807 크기를 적은 0.BIN 을 «원본 디스크 1 파일 + 그림/*.xdelta» 로 work/poc/ 에 만든다 (2026-10-23).
build_kr 는 이 work/poc/ 파일을 그대로 쓴다. 그림을 새로 그리려면 tools/poc.py → namegfx.py bake → titlegfx.py bake batang.
  python tools/gfx_apply.py          # 적용
  python tools/gfx_apply.py make     # (작업 PC) work/poc/ 에서 그림/*.xdelta 만들기"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from paths import ROOT, XDELTA

NAMES = ('GP8.ARC', 'BMP.ARC', 'NAME.DAT', 'TITLE.DAT', '0.BIN')
W = lambda *p: os.path.join(ROOT, 'work', *p)

def main(make=False, gdir=None):
    gdir = gdir or os.path.join(ROOT, '그림'); os.makedirs(gdir if make else W('poc'), exist_ok=True)
    for n in NAMES:
        src, new, pat = W('disc1', n), W('poc', n), os.path.join(gdir, n + '.xdelta')
        if make:
            subprocess.run([XDELTA, '-e', '-9', '-f', '-B', '1073741824', '-s', src, new, pat], check=True)
        else:
            subprocess.run([XDELTA, '-d', '-f', '-B', '1073741824', '-s', src, pat, new], check=True)
        print(n, os.path.getsize(pat))

if __name__ == '__main__':
    main('make' in sys.argv[1:], sys.argv[2] if len(sys.argv) > 2 else None)
