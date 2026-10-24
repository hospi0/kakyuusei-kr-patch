# -*- coding: utf-8 -*-
r"""배포 묶음 (2026-10-23) — dist/<NAME>/ : 디스크별 트랙 1 xdelta 3개 + xdelta.exe + readme.txt(CP949) + 한글패치_적용.bat(CP949)
  (virus-kr-patch tools/make_dist.py 를 그대로 옮김)
  바뀌는 트랙: 디스크마다 트랙 1 만(트랙 2·cue 는 원본 그대로 — 트랙 1 이 늘어나도 cue 는 파일별이라 그대로 맞음)
  검증: 원본 트랙 1 → xdelta 적용 → md5 = 빌드(work/build/discN) 트랙 1 md5.
  python tools/make_dist.py   (먼저 build_kr·build_track 3장)
  readme 본문 = tools/dist_readme.txt (없으면 readme 없이)
"""
import glob, hashlib, os, shutil, subprocess, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)

VER = 'v0.9'
sys.path.insert(0, HERE)
from paths import XDELTA
from extract import track1
OUT = os.path.join(ROOT, 'work', 'build')
NAME = 'Kakyuusei_KR_' + VER
TITLE = '하급생 (세가 새턴 일본판, 3장) 한글 패치 ' + VER
ROMS = ['Kakyuusei (Japan) (Disc 1)', 'Kakyuusei (Japan) (Disc 2) (2M)', 'Kakyuusei (Japan) (Disc 3) (2M)']


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest().upper()


_rd = os.path.join(HERE, 'dist_readme.txt')
README = open(_rd, encoding='utf-8').read() if os.path.exists(_rd) else None   # 없으면 readme 없이(작업 키트)

BAT_HEAD = '@echo off\nchcp 949 >nul\nset "XD=%~dp0xdelta.exe"\nset OK=0\n'
BAT_ONE = r"""if exist "%~dp0{bin}" (
  "%XD%" -d -f -s "%~dp0{bin}" "%~dp0{patch}" "%~dp0{kbin}"
  if errorlevel 1 (
    echo   [오류] 디스크 {n} 패치 실패 - 원본이 다를 수 있습니다 - 원본 트랙 1 md5 확인.
  ) else (
    echo   완료: "{kbin}"
    set OK=1
  )
)
"""
BAT_TAIL = r"""if "%OK%"=="0" echo   [오류] 원본 트랙 1 파일을 이 폴더에 넣어 주세요.
pause
"""


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    d = os.path.join(ROOT, 'dist', NAME)
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)
    bat = BAT_HEAD; md = {}
    for n, rom in enumerate(ROMS, 1):
        b = '%s (Track 1).bin' % rom
        src, out = track1(n), os.path.join(OUT, 'disc%d' % n, b)
        patch = '%s_Disc%d_Track1.xdelta' % (NAME, n); pp = os.path.join(d, patch)
        subprocess.run([XDELTA, '-e', '-9', '-B', '1073741824', '-f', '-s', src, out, pp], check=True)
        chk = os.path.join(d, '_check.bin')
        subprocess.run([XDELTA, '-d', '-f', '-B', '1073741824', '-s', src, pp, chk], check=True)
        o, want, got = md5(src), md5(out), md5(chk)
        os.remove(chk)
        assert got == want, ('패치 적용 결과가 빌드와 다름', n, got, want)
        md['o%d' % n], md['d%d' % n] = o, want
        print('디스크 %d 트랙 1 원본md5 %s → 패치md5 %s · %s %d B' % (n, o, want, patch, os.path.getsize(pp)), flush=True)
        bat += BAT_ONE.format(n=n, bin=b, patch=patch, kbin='%s (Track 1) [KR].bin' % rom)
    bat += BAT_TAIL
    shutil.copy2(XDELTA, os.path.join(d, 'xdelta.exe'))
    if README:
        readme = README.format(title=TITLE, line='=' * 60, name=NAME, **md)
        open(os.path.join(d, 'readme.txt'), 'wb').write(readme.replace('\n', '\r\n').encode('cp949'))
    open(os.path.join(d, '한글패치_적용.bat'), 'wb').write(bat.replace('\n', '\r\n').encode('cp949'))
    z = os.path.join(ROOT, 'dist', NAME + '.zip')
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(os.listdir(d)):
            zf.write(os.path.join(d, f), NAME + '/' + f)
    print('✅', d)
    for f in sorted(os.listdir(d)):
        print('  %-56s %12d' % (f, os.path.getsize(os.path.join(d, f))))
    print('  zip %s %d B · md5 %s' % (os.path.basename(z), os.path.getsize(z), md5(z)))


if __name__ == '__main__':
    main()
