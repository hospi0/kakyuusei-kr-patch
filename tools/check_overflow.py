# -*- coding: utf-8 -*-
"""넘침 검사 (2026-10-23, 그동안 즉석으로 돌리던 것을 도구로) — 빌드 전에 돌린다. 결과 work/넘침.tsv.
 ① 대사 창: 대사 루프(0.BIN 0x06014104)를 그대로 흉내 — 줄 시작 x=30, 2바이트 글자 x+28, 좁은 띄어쓰기·￥ x+12,
    «：» 건너뜀, x>595(0x253) 이면 다음 줄. 4줄째 마지막 칸(x≥590)은 커서가 가림 → 그 뒤 글자 = 넘침.
    한 창 = 이름표 「［」+이름+「］：…」 와 이름 뒤 「君·さん…」 조각을 이어 붙인 것. 주인공 이름은 5자(가나다라마)로 계산.
 ② 선택지: 「●」로 시작하는 조각 글자 수(띄어쓰기 포함) > 44 — 원문 최대 38자, 44자 넘으면 두 줄을 넘는 것으로 봄(작업 때 기준).
 ③ 시스템(0.BIN): 번역 글자 수 > 예산(원래 글자 수) — 빌더가 0.BIN 끝으로 옮기지만 메뉴 칸 일부는 원래 글자 수만 그림.
번역표(번역/번역표_*.tsv)가 있으면 그것을, 없으면 작업 PC 의 여러 겹 번역을 읽는다(build_kr 와 같음).
  python tools/check_overflow.py"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import build_kr as b

NAME = '가나다라마'
SUF = re.compile('^(君|さん|ちゃん|くん|様)')
END = re.compile('[。！？…」』）]$')
CHOICE_MAX = 44

def over_px(text):
    x = 30; line = 0; n = 0
    for c in text:
        if c == '：': continue
        if c in '￥ ': x += 12; continue
        if line >= 4 or (line == 3 and x >= 590): n += 1
        x += 28
        if x > 595: line += 1; x = 30
    return n

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    if os.path.exists(os.path.join(b.TABLE_DIR, '번역표_대사.tsv')):
        rows, binr, _ = b.load_table()
    else:
        import todo_tr
        mes, binr, _ = todo_tr.load(); rows, _ = b.load_rows(mes)
    out = ['종류\t장면\t위치\t원문\t번역\t넘침']
    nd = nc = ns = 0
    for sc, lst in sorted(rows.items()):
        raw = open(b.W('disc1', 'mes', '%03d.bin' % sc), 'rb').read()
        dlg = b.dialog_frags(raw)
        by = {p: (j, k) for p, j, k in lst}; nxt = {}
        for p, j, k in lst:
            e = p + len(j.encode('cp932')); q = (e + 4) & ~3
            if q in by and not any(raw[e:q]) and ((j == '［' and by[q][0].startswith('］')) or (SUF.match(by[q][0]) and not END.search(j))):
                nxt[p] = q
        for h in sorted(set(by) - set(nxt.values())):
            if h not in dlg: continue
            ps = [h]
            while ps[-1] in nxt: ps.append(nxt[ps[-1]])
            o = over_px(NAME.join(by[p][1] or by[p][0] for p in ps))
            if o:
                nd += 1
                out.append('대사\t%03d\t%X\t%s\t%s\t%d' % (sc, h, '…'.join(by[p][0] for p in ps), '…'.join(by[p][1] for p in ps), o))
        for p, j, k in lst:
            if j.startswith('●') and k and len(k) > CHOICE_MAX:
                nc += 1; out.append('선택지\t%03d\t%X\t%s\t%s\t%d' % (sc, p, j, k, len(k) - CHOICE_MAX))
    for off, (jp, tr, bud) in sorted(binr.items()):
        t = b.clean(tr)
        if len(t) > bud:
            ns += 1; out.append('시스템\t-\t%X\t%s\t%s\t%d' % (off, jp, t, len(t) - bud))
    p = b.W('넘침.tsv'); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8-sig', newline='\n').write('\n'.join(out) + '\n')
    print('대사 창 넘침 %d · 선택지 44칸 넘침 %d · 시스템 예산 넘침 %d(0.BIN 끝으로 옮겨짐) → %s' % (nd, nc, ns, p))

if __name__ == '__main__':
    main()
