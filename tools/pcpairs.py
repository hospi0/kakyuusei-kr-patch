# -*- coding: utf-8 -*-
"""PC 원본 MES ↔ 1999 한글판 MES 대사 짝 → work/pc/pairs.tsv (파일, 위치JP, 원문, 번역, 종류).
종류 M = 대사 끝 명령(0x11) 앞에서 끝나는 줄 — 609개 파일 모두 줄 수가 같아야 한다(다르면 실패).
종류 O = 그 밖의 줄(선택지·아이템 등) — 줄 뒤 명령 바이트 열을 difflib 로 맞춘 같은 구간만 짝(잡음 조각 섞임).
이름 자리 = {N}. 한글판 글꼴에 그림이 없는 음절 = □."""
import difflib, glob, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import pctext, pckr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def msgs(d):
    out = []
    for at, s in pctext.lines(d):
        e = at + pctext._srclen(d, at, s)
        if e < len(d) and d[e] == 0x11:
            out.append((at, s))
    return out

_KANA = re.compile('[ぁ-ヶ]')
_CJK = re.compile('[一-鿿]')

def ok_other(jt, kt):
    """O 짝 거르기: 원문이 ［ 인데 번역이 【 가 아니면 어긋남, 번역에 원문에 없는 한자가 있으면 한글판 쪽 잡음.
    (가나 없는 잡음 줄은 남지만 새턴 원문과 일치할 일이 없어 무해 — 아이템 이름은 한자뿐이라 가나 조건을 걸면 안 된다)"""
    if jt.startswith('［') and not kt.startswith('【'): return False
    if any(c not in jt for c in _CJK.findall(kt)): return False
    return True

def others(d):
    """대사 끝(0x11)이 아닌 줄: (위치, 바이트열, 뒤 명령 4바이트)."""
    out = []
    for at, s in pctext.lines(d):
        e = at + pctext._srclen(d, at, s)
        if e < len(d) and d[e] != 0x11:
            out.append((at, s, d[e:e + 4]))
    return out

if __name__ == '__main__':
    rows = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'work', 'pc', 'KAKYUSEI_mes', '*.MES'))):
        n = os.path.basename(f)
        j = msgs(open(f, 'rb').read())
        k = msgs(open(os.path.join(ROOT, 'work', 'pc', 'KAKYUHAN_mes', n), 'rb').read())
        assert len(j) == len(k), (n, len(j), len(k))
        for (a, sj), (_, sk) in zip(j, k):
            rows.append((n, '%X' % a, sj.decode('cp932', 'replace'), pckr.decode(sk), 'M'))
        dj = open(f, 'rb').read(); dk = open(os.path.join(ROOT, 'work', 'pc', 'KAKYUHAN_mes', n), 'rb').read()
        oj = others(dj); ok = others(dk)
        sm = difflib.SequenceMatcher(None, [x[2] for x in oj], [x[2] for x in ok], autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal':
                for x, y in zip(oj[i1:i2], ok[j1:j2]):
                    jt = x[1].decode('cp932', 'replace'); kt = pckr.decode(y[1])
                    if len(x[1]) >= 4 and ok_other(jt, kt):
                        rows.append((n, '%X' % x[0], jt, kt, 'O'))
    with open(os.path.join(ROOT, 'work', 'pc', 'pairs.tsv'), 'w', encoding='utf-8') as w:
        for r in rows:
            w.write('\t'.join(x.replace('\t', ' ') for x in r) + '\n')
    same = sum(1 for r in rows if r[2] == r[3])
    print('O 짝', sum(1 for r in rows if r[4] == 'O'))
    print('짝', len(rows), '고유 원문', len({r[2] for r in rows}), '번역=원문(미번역 의심)', same,
          '□ 든 줄', sum(1 for r in rows if '□' in r[3]))
