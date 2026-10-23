# -*- coding: utf-8 -*-
"""디스크 Track1 에서 지정 파일(또는 전부)을 work/discN/ 로 뽑는다 (원본 읽기 전용)."""
import os, sys, glob
sys.path.insert(0, os.path.dirname(__file__))
from iso9660 import Iso

ROM = r'C:\claude\roms\ss'
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def track1(n):
    return glob.glob(os.path.join(ROM, 'Kakyuusei (Japan) (Disc %d)*' % n, '*(Track 1).bin'))[0]

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
