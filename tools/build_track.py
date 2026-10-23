# -*- coding: utf-8 -*-
"""시험판 Track 1 만들기 (2026-10-23): work/build/discN/ 의 파일을 원본 Track 1 에 넣는다 → work/build/discN/*.bin + .cue
 - 크기가 같은 파일(0.BIN·SJIS2.KNJ·GP8.ARC·BMP.ARC)은 제자리.
 - MES.ARC 가 원래보다 크면 데이터 끝(마지막 파일 뒤)에 새로 두고 트랙을 늘린다: 디렉터리 기록(LBA·크기),
   PVD 볼륨 크기, CDDA.PCM(오디오 트랙을 가리킴) LBA 를 늘린 만큼 고친다. 원래 MES.ARC 자리는 그대로 둔다.
   게임은 MES.ARC 를 GFS 이름으로 연다(0x0600CA78) — 위치표 섹터는 파일 안 상대값.
 - 트랙 끝 빈 섹터(postgap 150)는 새 주소로 다시 만든다. 바꾼 섹터는 MODE1 EDC/ECC 재계산.
 - Track 2(CD-DA)는 원본 파일을 그대로 복사한다.
  python tools/build_track.py [디스크번호=1]"""
import glob, os, shutil, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import cdmode1
from iso9660 import Iso
from extract import track1

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEC = 2352
SAME = ('0.BIN', 'SJIS2.KNJ', 'GP8.ARC', 'BMP.ARC', 'NAME.DAT', 'TITLE.DAT')

def bcd(v): return ((v // 10) << 4) | (v % 10)

def new_sector(lba, data):
    f = lba + 150
    sec = bytearray(SEC)
    sec[0:12] = b'\x00' + b'\xff' * 10 + b'\x00'
    sec[12:16] = bytes([bcd(f // 4500), bcd(f // 75 % 60), bcd(f % 75), 1])
    sec[16:16 + len(data)] = data
    cdmode1.fix(sec)
    return bytes(sec)

def both(v): return struct.pack('<I', v) + struct.pack('>I', v)

def main():
    disc = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    bdir = os.path.join(ROOT, 'work', 'build', 'disc%d' % disc)
    src = track1(disc); srcdir = os.path.dirname(src)
    base = os.path.basename(src)
    dst = os.path.join(bdir, base)
    iso = Iso(src); nsec = iso.nsec
    ent = {p.strip('/'): (l, s) for p, l, s in iso.walk() if not p.endswith('/')}
    data_end = max(l + (s + 2047) // 2048 for n, (l, s) in ent.items() if n != 'CDDA.PCM')
    tail = nsec - data_end
    # 꼬리 섹터는 빈 MODE1 이어야 한다
    for s in range(data_end, nsec):
        assert not any(iso.sector(s)), ('트랙 꼬리가 비어 있지 않음', s)
    mes = open(os.path.join(bdir, 'MES.ARC'), 'rb').read()
    mlba, msize = ent['MES.ARC']
    grow = len(mes) > msize
    nnew = (len(mes) + 2047) // 2048 if grow else 0
    shutil.copyfile(src, dst)
    touched = set()
    with open(dst, 'r+b') as f:
        def put(lba, data):
            for k in range(0, len(data), 2048):
                chunk = data[k:k + 2048]
                f.seek((lba + k // 2048) * SEC); sec = bytearray(f.read(SEC))
                old = bytes(sec[16:2064]); sec[16:16 + len(chunk)] = chunk
                if bytes(sec[16:2064]) != old:
                    cdmode1.fix(sec); f.seek((lba + k // 2048) * SEC); f.write(sec); touched.add(lba + k // 2048)
        exe_size = None
        for n in SAME:
            p = os.path.join(bdir, n)
            if not os.path.exists(p): continue
            d = open(p, 'rb').read()
            if n == '0.BIN' and len(d) > ent[n][1]:
                # 0.BIN 이 커짐(예산 넘친 화면 문자열 덧붙임) → 바로 뒤 원래 MES.ARC 자리(옮겨서 비었음)로 늘린다
                assert grow and ent[n][0] + (len(d) + 2047) // 2048 <= mlba + (msize + 2047) // 2048, '0.BIN 늘릴 자리 없음'
                exe_size = len(d)
            else:
                assert len(d) == ent[n][1], n
            put(ent[n][0], d)
        if not grow:
            put(mlba, mes + bytes(msize - len(mes)) if len(mes) < msize else mes)
        else:
            f.seek(data_end * SEC); f.truncate()
            for k in range(nnew):
                f.write(new_sector(data_end + k, mes[k * 2048:(k + 1) * 2048]))
            for k in range(tail):
                f.write(new_sector(data_end + nnew + k, b''))
            # 디렉터리 기록·PVD
            rl, rs = iso.root()
            d = bytearray(iso.read(rl, rs))
            def setrec(name, lba, size):
                i = d.find(name.encode() + b';1'); assert i > 0 and d.count(name.encode() + b';1') == 1, name
                r = i - 33; assert d[r + 32] == len(name) + 2
                d[r + 2:r + 10] = both(lba); d[r + 10:r + 18] = both(size)
            setrec('MES.ARC', data_end, len(mes))
            if exe_size: setrec('0.BIN', ent['0.BIN'][0], exe_size)     # IP.BIN 첫 읽기 크기 = 0 → BIOS 는 디렉터리 크기만큼 읽음
            cl, cs = ent['CDDA.PCM']; setrec('CDDA.PCM', cl + nnew, cs)
            put(rl, bytes(d))
            pvd = bytearray(iso.pvd()); vs = struct.unpack_from('<I', pvd, 80)[0]
            pvd[80:88] = both(vs + nnew); put(16, bytes(pvd))
    # Track 2 + cue
    t2 = glob.glob(os.path.join(srcdir, '*(Track 2).bin'))[0]
    if not os.path.exists(os.path.join(bdir, os.path.basename(t2))):
        shutil.copyfile(t2, os.path.join(bdir, os.path.basename(t2)))
    cue = glob.glob(os.path.join(srcdir, '*.cue'))[0]
    shutil.copyfile(cue, os.path.join(bdir, os.path.basename(cue)))
    # 검산: 새 트랙을 ISO 로 다시 읽어 파일이 빌드 결과와 같은지
    out = Iso(dst); oent = {p.strip('/'): (l, s) for p, l, s in out.walk() if not p.endswith('/')}
    for n in SAME + ('MES.ARC',):
        p = os.path.join(bdir, n)
        if os.path.exists(p):
            assert out.read(*oent[n]) == open(p, 'rb').read(), n
    assert oent['CDDA.PCM'][0] == ent['CDDA.PCM'][0] + nnew
    assert out.nsec == nsec + nnew
    with open(dst, 'rb') as f:                     # 새/바뀐 섹터 EDC·ECC 재검산(표본)
        for s in sorted(touched)[:40] + list(range(data_end, data_end + nnew + tail, 97)):
            f.seek(s * SEC); sec = f.read(SEC)
            assert bytes(cdmode1.fix(bytearray(sec))) == sec, s
    sys.stdout.reconfigure(encoding='utf-8')
    print('디스크 %d: 바뀐 섹터 %d · MES.ARC %s (새 섹터 %d) → %s' %
          (disc, len(touched), ('LBA %d 로 옮김' % data_end) if grow else '제자리', nnew, dst))

if __name__ == '__main__':
    main()
