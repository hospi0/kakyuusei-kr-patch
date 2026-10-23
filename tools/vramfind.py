# -*- coding: utf-8 -*-
"""스테이트 VRAM 조각 → 디스크 파일 위치 찾기 (2026-10-23, 빠른 판).
VRAM(VDP1·VDP2)에서 1 KB 마다 «값이 여러 가지인» 32 B 조각 하나씩 표본으로 뽑아, 원천(work/disc1 파일 + 안의 elfpak 묶음을 푼 것)에서 bytes.find.
원천 하나를 다 볼 때마다 결과를 바로 찍는다(-u 로 실행). 먼저 볼 원천을 인수로 줄 수 있다.
  python -u tools/vramfind.py <mem 이름> [원천 이름 앞부분 ...]"""
import glob, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import elfpak

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def samples(v, step=1024, size=32):
    out = []
    for a in range(0, len(v) - size, step):
        for b in range(a, min(a + step, len(v) - size), size):
            c = v[b:b + size]
            if len(set(c)) >= 6:
                out.append((b, c)); break
    return out

def sources(prefer):
    files = sorted(glob.glob(os.path.join(ROOT, 'work', 'disc1', '*')))
    files = [f for f in files if not os.path.isdir(f) and os.path.basename(f) != 'MES.ARC']
    files.sort(key=lambda f: (not any(os.path.basename(f).startswith(p) for p in prefer), f))
    for f in files:
        n = os.path.basename(f); d = open(f, 'rb').read()
        yield n, d
        for k, m in enumerate(re.finditer(rb'elfpak\x1a\x00', d)):
            try:
                yield '%s#%d@%X' % (n, k, m.start()), elfpak.unpack(d[m.start():])[0]
            except Exception:
                pass

def main(name, prefer):
    sys.stdout.reconfigure(encoding='utf-8')
    vr = {t: open(os.path.join(ROOT, 'work', 'mem', name, t + '.bin'), 'rb').read() for t in ('VDP1_VRAM', 'VDP2_VRAM')}
    smp = {t: samples(v) for t, v in vr.items()}
    print('표본', {t: len(s) for t, s in smp.items()}, flush=True)
    for sn, d in sources(prefer):
        for t, s in smp.items():
            hit = [(a, d.find(c)) for a, c in s]
            hit = [(a, p) for a, p in hit if p >= 0]
            if hit:
                print('%-26s %s 조각 %3d  VRAM %05X~%05X  파일 %X~%X' % (sn, t[:4], len(hit), hit[0][0], hit[-1][0], min(p for _, p in hit), max(p for _, p in hit)), flush=True)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
