# -*- coding: utf-8 -*-
"""번역할 것 추출 (2026-10-23, 사용자 요청) → work/todo/번역할것_NN.tsv (UTF-8 BOM, 20 KB 단위).
대상
  MES  = work/sat_tr.tsv 에서 번역이 비었거나(원문 유지) 번역에 한글이 하나도 없는 조각(PC 판이 안 옮긴 선택지·아이템 등).
         한글이 든 번역(일본어가 조금 남았어도)은 빌드가 그대로 넣는다(2026-10-23 사용자 지시).
         같은 원문은 한 줄로(처음 나온 장면·위치 순). 가나·한자가 없는 조각(「［」 등)은 뺀다.
         참고 칸은 비움(남은 줄의 PC «번역»은 원문 그대로).
  0BIN = 0.BIN 화면 문자열(장소 이름·저장/불러오기·디스크 교체·제목 메뉴·옵션 등). 제자리라 «예산»(전각 글자 수) 안에서.
         디버그 메뉴·이름 입력 글자판·기본 이름·이미 옮긴 「下級生を途中からする」·깨진 바이트는 뺀다.
열: 번호, 구분, 원문, 참고, 예산, 번역(빈칸). 원문의 「］：」·「［」·●·…… 등 원문 토큰은 번역에도 그대로 둔다.
  python tools/export_todo.py"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import build_kr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = lambda *p: os.path.join(ROOT, 'work', *p)
JP = re.compile('[ぁ-ヺー-ヾ一-鿿々]')   # ・ 는 빼고
HANGUL = re.compile('[가-힣]')
SPLIT = 20 * 1024
SKIP_0BIN = [(0x180c8, 0x18d10), (0x65898, 0x65a60)]          # 디버그 메뉴, 이름 입력 글자판
SKIP_TEXT = {'けんたろう', '下級生を途中からする'}

def mes_rows():
    seen, out = set(), []
    rows, _ = build_kr.load_rows({})                   # 빌드와 같은 번역(사용자 번역·이름표·君 고침 포함)
    for sc in sorted(rows):
        for pos, jp, kr in rows[sc]:
            if not JP.search(jp) or (kr and (HANGUL.search(kr) or not JP.search(kr))) or jp in seen:   # 한글이 들었거나 부호뿐인 번역은 빌드가 그대로 넣는다
                continue
            seen.add(jp)
            ref = ''                                          # 남은 줄의 PC «번역»은 원문 그대로라 참고가 안 됨
            out.append(('MES', jp, ref, ''))
    return out

def bin_rows():
    exe = open(W('disc1', '0.BIN'), 'rb').read(); out = []
    for m in re.finditer(rb'(?:[\x81-\x84\x88-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc]){2,}(?=\x00)', exe):
        p = m.start()
        if any(a <= p < b for a, b in SKIP_0BIN) or p % 2 or p >= 0x30000: continue   # 홀수·코드 영역 = 우연한 바이트
        try:
            s = m.group().decode('cp932')
        except UnicodeDecodeError:
            continue
        t = s.strip('　')
        if not re.search('[ぁ-ヾ]', s) and not re.search('[一-鿿]{2}', s): continue
        if t in SKIP_TEXT or re.search('[ｙ＿＆灘]', s): continue
        out.append(('0BIN:%X' % p, t, '', str(len(s))))
    return out

def main():
    rows = bin_rows() + mes_rows()
    d = W('todo'); os.makedirs(d, exist_ok=True)
    for f in os.listdir(d):
        if f.startswith('번역할것_'): os.remove(os.path.join(d, f))
    head = '번호\t구분\t원문\t참고\t예산\t번역\n'
    files, cur = [], head
    for i, (kind, jp, ref, bud) in enumerate(rows, 1):
        line = '\t'.join(('T%05d' % i, kind, jp, ref, bud, '')) + '\n'
        if len((cur + line).encode('utf-8')) + 3 > SPLIT:
            files.append(cur); cur = head
        cur += line
    files.append(cur)
    for k, body in enumerate(files, 1):
        open(os.path.join(d, '번역할것_%02d.tsv' % k), 'w', encoding='utf-8-sig').write(body)
    sys.stdout.reconfigure(encoding='utf-8')
    nm = sum(r[0] == 'MES' for r in rows)
    print('MES %d줄(%d자) · 0.BIN %d줄 → %s 파일 %d개' % (nm, sum(len(r[1]) for r in rows if r[0] == 'MES'),
                                                     len(rows) - nm, d, len(files)))

if __name__ == '__main__':
    main()
