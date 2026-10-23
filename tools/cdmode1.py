# -*- coding: utf-8 -*-
"""MODE 1 / 2352 B 섹터의 EDC·ECC 재계산 (세가 새턴 Track 1)

  python tools/cdmode1.py        # 원본 섹터로 규약 검산

## 섹터 배치 (MODE 1)
| 자리 | 크기 | 내용 |
|---|---|---|
| 0 | 12 | 동기 `00 FF×10 00` |
| 12 | 4 | 헤더(분·초·프레임 BCD + 모드 1) |
| 16 | 2048 | **유저 데이터** |
| 2064 | 4 | **EDC** — `0 ~ 2063` 을 덮는다(동기·헤더 포함) |
| 2068 | 8 | 0 |
| 2076 | 172 | P 패리티 |
| 2248 | 104 | Q 패리티 |

⚠️MODE 2 Form 1 과 헷갈리지 말 것 — 그쪽은 EDC 가 **2072** 에 있고 «서브헤더부터»
  2056 B 를 덮으며, ECC 계산 동안 헤더를 0 으로 만든다. **MODE 1 은 헤더를 그대로 둔다.**
★[[feedback_gdm_build_and_font]] — ECC 를 안 맞추면 «내용과 무관하게» 크래시한다.
  그래서 새 디스크는 **무수정 원본 섹터로 규약부터 검산**한다.
"""
import struct, sys

_EDC = [0] * 256
for _n in range(256):
    _c = _n
    for _ in range(8):
        _c = (_c >> 1) ^ (0xD8018001 if _c & 1 else 0)
    _EDC[_n] = _c

_F = [0] * 256
_B = [0] * 256
for _i in range(256):
    _F[_i] = ((_i << 1) ^ (0x11D if _i & 0x80 else 0)) & 0xFF
    _B[_i ^ _F[_i]] = _i


def edc(data):
    e = 0
    for b in data:
        e = (e >> 8) ^ _EDC[(e ^ b) & 0xFF]
    return e & 0xFFFFFFFF


def _ecc_block(sec, major_count, minor_count, major_mult, minor_inc, doff):
    """⚠️Q 는 «방금 쓴 P 패리티»를 읽으므로 반드시 P 를 먼저 쓴다."""
    size = major_count * minor_count
    for major in range(major_count):
        index = (major >> 1) * major_mult + (major & 1)
        a = b = 0
        for _ in range(minor_count):
            t = sec[12 + index]
            index += minor_inc
            if index >= size:
                index -= size
            a ^= t
            b ^= t
            a = _F[a]
        a = _B[_F[a] ^ b]
        sec[doff + major] = a
        sec[doff + major + major_count] = (a ^ b) & 0xFF


def fix(sec):
    """2352 B 섹터(bytearray)를 제자리에서 EDC/ECC 재계산"""
    assert len(sec) == 2352
    sec[2064:2068] = struct.pack('<I', edc(sec[0:2064]))
    sec[2068:2076] = bytes(8)
    _ecc_block(sec, 86, 24, 2, 86, 2076)     # P
    _ecc_block(sec, 52, 43, 86, 88, 2248)    # Q
    return sec


def verify(path, lbas):
    """무수정 원본 섹터를 다시 계산해 **바이트가 그대로인지** 본다"""
    f = open(path, 'rb')
    ok = bad = 0
    for lba in lbas:
        f.seek(lba * 2352)
        s = f.read(2352)
        if len(s) < 2352:
            break
        t = fix(bytearray(s))
        if bytes(t) == s:
            ok += 1
        else:
            bad += 1
            if bad < 4:
                print('   ⚠️LBA %d 어긋남' % lba)
    return ok, bad


if __name__ == '__main__':
    p = (sys.argv[1] if len(sys.argv) > 1 else
         "F:/hospi/roms/ss roms/Dragon Force II - Kami Sarishi Daichi ni (Japan) "
         "(Rev A)/Dragon Force II - Kami Sarishi Daichi ni (Japan) (Rev A) (Track 1).bin")
    import random
    random.seed(1)
    lbas = [0, 16, 17, 100, 183772] + [random.randrange(1000, 258000) for _ in range(60)]
    ok, bad = verify(p, lbas)
    print('원본 섹터 %d개 재계산 -> 일치 %d / 어긋남 %d' % (len(lbas), ok, bad))
