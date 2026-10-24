# -*- coding: utf-8 -*-
"""디스크 Track1 에서 지정 파일(또는 전부)을 work/discN/ 로 뽑는다 (원본 읽기 전용).
MES.ARC 를 뽑으면 장면 600개를 풀어 work/discN/mes/NNN.bin 으로도 둔다(빌더·추출기가 읽는 장면 원본).
  python tools/extract.py <디스크번호> [파일이름 …]"""
import os, re, sys, glob
sys.path.insert(0, os.path.dirname(__file__))
from iso9660 import Iso
from paths import ROM

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def track1(n):
    hit = glob.glob(os.path.join(ROM, '**', 'Kakyuusei (Japan) (Disc %d)*(Track 1).bin' % n), recursive=True)
    assert hit, '원본 디스크 %d 트랙 1 을 못 찾음: %s 아래 «Kakyuusei (Japan) (Disc %d)…(Track 1).bin»' % (n, ROM, n)
    return hit[0]

def split_mes(arc, out):
    import elfpak
    offs = [m.start() for m in re.finditer(rb'elfpak\x1a\x00', arc)] + [len(arc)]
    assert len(offs) == 601
    os.makedirs(out, exist_ok=True)
    for k in range(600):
        open(os.path.join(out, '%03d.bin' % k), 'wb').write(elfpak.unpack(arc[offs[k]:offs[k + 1]])[0])

if __name__ == '__main__':
    n = int(sys.argv[1]); names = set(sys.argv[2:])
    iso = Iso(track1(n)); out = os.path.join(HERE, 'work', 'disc%d' % n)
    os.makedirs(out, exist_ok=True)
    for path, lba, size in iso.walk():
        name = path.strip('/')
        if path.endswith('/') or (names and name not in names):
            continue
        try:
            data = iso.read(lba, size)
        except EOFError:   # CDDA.PCM 은 데이터 트랙 밖(오디오 트랙)을 가리킨다
            print(name, size, '건너뜀(트랙 밖)'); continue
        open(os.path.join(out, name), 'wb').write(data)
        print(name, size)
        if name == 'MES.ARC':
            split_mes(data, os.path.join(out, 'mes')); print(' → mes/000~599.bin')
