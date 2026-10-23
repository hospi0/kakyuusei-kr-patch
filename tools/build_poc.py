# -*- coding: utf-8 -*-
"""PoC 디스크 1 Track 1 만들기 (2026-10-23): 원본 Track 1 사본에 work/poc/ 의 0.BIN·SJIS2.KNJ·MES.ARC 를 제자리로 쓰고
MODE1 EDC/ECC 재계산 → work/poc/track1.bin. 파일 크기는 원본과 같아야 한다(디렉터리는 안 고침).
검산: 다시 ISO 로 읽은 세 파일 = work/poc 파일, 그 밖의 섹터는 원본과 같음.
  python tools/build_poc.py"""
import os, shutil, sys
sys.path.insert(0, os.path.dirname(__file__))
import cdmode1
from iso9660 import Iso
from extract import track1

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POC = os.path.join(ROOT, 'work', 'poc')
FILES = ('0.BIN', 'SJIS2.KNJ', 'MES.ARC', 'GP8.ARC', 'BMP.ARC')

def main():
    src = track1(1); dst = os.path.join(POC, 'track1.bin')
    shutil.copyfile(src, dst)
    iso = Iso(src); ent = {p.strip('/'): (l, s) for p, l, s in iso.walk()}
    touched = set()
    with open(dst, 'r+b') as f:
        for name in FILES:
            lba, size = ent[name]
            data = open(os.path.join(POC, name), 'rb').read()
            assert len(data) == size, (name, len(data), size)
            for k in range(0, size, 2048):
                chunk = data[k:k + 2048]
                f.seek((lba + k // 2048) * 2352); sec = bytearray(f.read(2352))
                old = bytes(sec[16:16 + 2048])
                sec[16:16 + len(chunk)] = chunk
                if bytes(sec[16:16 + 2048]) != old:
                    cdmode1.fix(sec); f.seek((lba + k // 2048) * 2352); f.write(sec)
                    touched.add(lba + k // 2048)
    # 검산
    out = Iso(dst)
    for name in FILES:
        lba, size = ent[name]
        assert out.read(lba, size) == open(os.path.join(POC, name), 'rb').read(), name
    with open(src, 'rb') as a, open(dst, 'rb') as b:
        diff = 0; n = 0
        while True:
            x = a.read(2352 * 512); y = b.read(2352 * 512)
            if not x: break
            for i in range(0, len(x), 2352):
                if x[i:i + 2352] != y[i:i + 2352] and (n + i // 2352) not in touched:
                    diff += 1
            n += len(x) // 2352
    assert diff == 0, ('바꾸지 않은 섹터가 달라짐', diff)
    # 바꾼 섹터 EDC/ECC 재검산
    with open(dst, 'rb') as f:
        for s in sorted(touched)[:50]:
            f.seek(s * 2352); sec = f.read(2352)
            assert bytes(cdmode1.fix(bytearray(sec))) == sec
    sys.stdout.reconfigure(encoding='utf-8')
    print('바뀐 섹터', len(touched), '→', dst)

if __name__ == '__main__':
    main()
