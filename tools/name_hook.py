# -*- coding: utf-8 -*-
"""조합형 한글 이름 입력 훅 (2026-11-22 하급생, 하스피 «2000자 안에 넣자» — 코드R tools/name_hook.py 꼴)
원래 글자 넣기(디스크 1 0x0601FC9E~0x0601FD28, 3장 같은 바이트·주소만 밀림):
  FC9E pos==5 → FE5A(삑) / 아니면 R13(3)·0x060204BC(3) → 칸 코드(판+쪽×0xE4+줄 R10×0x26+칸 R11×2) →
  [@(20,R14)+@(44,R14)] = 윗바이트, [@(40,R14)+1] = 아랫바이트 → 0x06013FF8(25,0) → 그리기 0x060203D0(pos, 코드) →
  @(40)+=2·@(44)+=2·커서 x(@0x06069B2C)+=0x1A0000·pos(@(24))++ → pos==5 면 FD24(→FE50 깜빡임 0) 아니면 FD1A(깜빡임 1).
훅: FCA2 «BRA FE5A» → «BRA FCA6»(다 찬 때도 훅으로), FCA6 = jmp 블롭(0.BIN 끝 덧붙임 RAM — 덧붙인 화면 문자열과 같은 자리,
  부팅 때 0.BIN 과 함께 실리고 BSS 밖이라 계속 남는다).
규칙 = coder-kr-patch/tools/jamo.py 와 같음(겹받침·겹모음·받침 넘김). 음절 = 글꼴에 있는 한글만(없는 음절은 «안 합침»).
조합은 «바로 앞 칸이 이 훅이 마지막으로 쓴 글자»일 때만(지우기·기본 이름에는 안 붙음).
python tools/name_hook.py test → 흉내기로 조합기 전수 대조 + 입력 순서 시험"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
CODER = r'C:\claude\project\coder-kr-patch\tools'                 # sh2asm·sh2sim·jamo 재사용
sys.path.append(CODER)
import types
_saved = {m: sys.modules.pop(m) for m in ('font', 'poc') if m in sys.modules}
_f = types.ModuleType('font')                                      # jamo 는 font.ks_hangul 만 씀(코드R font 는 코드R poc 를 부름)
_f.ks_hangul = lambda: [bytes([h, l]).decode('euc_kr') for h in range(0xB0, 0xC9) for l in range(0xA1, 0xFF)]
sys.modules['font'] = _f
import sh2asm, sh2sim, jamo
del sys.modules['font']; sys.modules.update(_saved)
sys.path.remove(CODER)
for _m in [m for m, v in list(sys.modules.items())                 # 코드R 의 poc·font 등 같은 이름 모듈이 남지 않게
           if m not in ('sh2asm', 'sh2sim', 'jamo') and os.path.dirname(getattr(v, '__file__', '') or '') == CODER]:
    del sys.modules[_m]

JAMO = jamo.JAMO                                   # k 0~18 초성, 19~39 중성(호환 자모 글자)
EXE_BASE = 0x06004000
D1 = 0x1BC9E                                       # 디스크 1 훅 머리(0x0601FC9E) 파일 오프셋
SIG = (0x1BC9E, 0x1BD28)


def addrs(exe):
    """이 장 0.BIN 의 훅 자리·호출 주소 — 디스크 1 루틴 바이트로 찾고 리터럴 풀에서 읽는다"""
    e1 = open(os.path.join(ROOT, 'work', 'disc1', '0.BIN'), 'rb').read()
    sig = e1[SIG[0]:SIG[1]]
    i = bytes(exe).find(sig); assert i >= 0 and bytes(exe).find(sig, i + 1) < 0, '이름 입력 루틴 못 찾음/여럿'
    L = lambda a: struct.unpack_from('>I', exe, i + (a - 0x0601FC9E))[0]
    A = lambda a: EXE_BASE + i + (a - 0x0601FC9E)
    return dict(OFF=i, HOOK=A(0x0601FCA6), BRA=A(0x0601FCA2), FIN=A(0x0601FD1A), FIN_FULL=A(0x0601FD24), REJ=A(0x0601FE5A),
                BLINK=L(0x0601FD30), CURX=L(0x0601FD8C), SOUND=L(0x0601FD94), ERASE=L(0x0601FD98), BOARD=L(0x0601FD9C),
                DRAW=L(0x0601FDA0))


ASM = r'''
entry:
  mov.l #%(HB)d,r8
  mov.l @(24,r14),r7
  mov.l #%(V_POS)d,r0
  mov.b r7,@(r0,r8)
  mov.l @(28,r14),r2
  mov #0,r3
  tst r2,r2
  bt e_p0
  mov.l #228,r3
e_p0:
  mov r10,r1
  shll r1
  mov r1,r2
  shll r1
  add r1,r2
  shll2 r1
  shll r1
  add r1,r2
  add r2,r3
  mov r11,r1
  add r1,r1
  add r1,r3
  mov.l #%(BOARD)d,r1
  add r1,r3
  mov.w @r3,r9
  extu.w r9,r9
  mov r9,r4
  bsr jidx
  nop
  mov r0,r6
  mov.l #%(V_K)d,r0
  mov.b r6,@(r0,r8)
  mov #5,r1
  cmp/eq r1,r7
  bt full
  cmp/pz r6
  bf append
  bsr can_comb
  nop
  tst r0,r0
  bt append
  mov r0,r4
  mov.l #%(V_K)d,r0
  mov.b @(r0,r8),r5
  bsr combine
  nop
  tst r0,r0
  bt append
  mov.l #%(V_N)d,r2
  add r8,r2
  mov.w r1,@r2
  mov r0,r9
  bsr sound
  nop
  bsr put_prev
  nop
  mov.l #%(V_N)d,r0
  mov.w @(r0,r8),r9
  extu.w r9,r9
  tst r9,r9
  bf append_ns
  mov.l #%(FIN)d,r0
  jmp @r0
  nop
append:
  bsr sound
  nop
append_ns:
  mov.l @(20,r14),r1
  mov.l @(44,r14),r0
  mov r9,r2
  shlr8 r2
  mov.b r2,@(r0,r1)
  mov.l @(40,r14),r1
  add #1,r1
  mov.b r9,@r1
  mov.l @(24,r14),r4
  mov.l #%(V_LAST)d,r0
  mov.b r4,@(r0,r8)
  mov.l #%(V_LCODE)d,r0
  mov.w r9,@(r0,r8)
  mov r9,r5
  mov.l #%(DRAW)d,r0
  jsr @r0
  nop
  mov.l @(40,r14),r1
  add #2,r1
  mov.l r1,@(40,r14)
  mov.l @(44,r14),r1
  add #2,r1
  mov.l r1,@(44,r14)
  mov.l #%(CURX)d,r2
  mov.l @r2,r3
  mov.l #0x1A0000,r1
  add r1,r3
  mov.l r3,@r2
  mov.l @(24,r14),r1
  add #1,r1
  mov.l r1,@(24,r14)
  mov #5,r2
  cmp/eq r2,r1
  bt fin_full
  mov.l #%(FIN)d,r0
  jmp @r0
  nop
fin_full:
  mov.l #%(FIN_FULL)d,r0
  jmp @r0
  nop

full:
  cmp/pz r6
  bf full_rej
  bsr can_comb
  nop
  tst r0,r0
  bt full_rej
  mov r0,r4
  mov.l #%(V_K)d,r0
  mov.b @(r0,r8),r5
  bsr combine
  nop
  tst r0,r0
  bt full_rej
  tst r1,r1
  bf full_rej
  mov r0,r9
  mov #3,r4
  jsr @r13
  nop
  mov #3,r4
  mov.l #%(BLINK)d,r0
  jsr @r0
  nop
  bsr sound
  nop
  bsr put_prev
  nop
  mov.l #%(FIN_FULL)d,r0
  jmp @r0
  nop
full_rej:
  mov.l #%(REJ)d,r0
  jmp @r0
  nop

sound:
  sts.l pr,@-r15
  mov #25,r4
  mov #0,r5
  mov.l #%(SOUND)d,r0
  jsr @r0
  nop
  lds.l @r15+,pr
  rts
  nop

can_comb:
  mov.l #%(V_POS)d,r0
  mov.b @(r0,r8),r1
  add #-1,r1
  cmp/pz r1
  bf cc_no
  mov.l #%(V_LAST)d,r0
  mov.b @(r0,r8),r2
  cmp/eq r1,r2
  bf cc_no
  mov.l @(20,r14),r1
  mov.l @(44,r14),r0
  add #-2,r0
  mov.b @(r0,r1),r2
  extu.b r2,r2
  shll8 r2
  mov.l @(40,r14),r1
  add #-1,r1
  mov.b @r1,r3
  extu.b r3,r3
  or r3,r2
  mov.l #%(V_LCODE)d,r0
  mov.w @(r0,r8),r3
  extu.w r3,r3
  cmp/eq r2,r3
  bf cc_no
  mov r2,r0
  rts
  nop
cc_no:
  mov #0,r0
  rts
  nop

put_prev:
  sts.l pr,@-r15
  mov.l @(20,r14),r1
  mov.l @(44,r14),r0
  add #-2,r0
  mov r9,r2
  shlr8 r2
  mov.b r2,@(r0,r1)
  mov.l @(40,r14),r1
  add #-1,r1
  mov.b r9,@r1
  mov.l #%(V_POS)d,r0
  mov.b @(r0,r8),r4
  add #-1,r4
  mov.l #%(V_LAST)d,r0
  mov.b r4,@(r0,r8)
  mov.l #%(V_LCODE)d,r0
  mov.w r9,@(r0,r8)
  mov.l #%(ERASE)d,r0
  jsr @r0
  nop
  mov.l #%(V_POS)d,r0
  mov.b @(r0,r8),r4
  add #-1,r4
  mov r9,r5
  mov.l #%(DRAW)d,r0
  jsr @r0
  nop
  lds.l @r15+,pr
  rts
  nop

jidx:
  mov.l #%(T_JC)d,r1
  add r8,r1
  mov #0,r0
j_l:
  mov.w @r1+,r2
  extu.w r2,r2
  cmp/eq r4,r2
  bt j_ret
  add #1,r0
  mov #40,r3
  cmp/hs r3,r0
  bf j_l
  mov #-1,r0
j_ret:
  rts
  nop

combine:
  sts.l pr,@-r15
  mov r4,r7
  mov.l #%(V_K2)d,r0
  mov.b r5,@(r0,r8)
  bsr jidx
  nop
  cmp/pz r0
  bf c_syl
  mov #19,r1
  cmp/hs r1,r0
  bt c_fail
  mov r0,r4
  mov.l #%(V_K2)d,r0
  mov.b @(r0,r8),r5
  mov #19,r1
  cmp/hs r1,r5
  bf c_fail
  add #-19,r5
  mov #0,r6
  bsr syl
  nop
  mov #0,r1
  bra c_ret
  nop
c_syl:
  mov.l #%(T_CODE)d,r1
  add r8,r1
  mov.l #%(N_SYL)d,r2
  mov #0,r3
k_l:
  mov.w @r1+,r0
  extu.w r0,r0
  cmp/eq r7,r0
  bt k_hit
  add #1,r3
  cmp/hs r2,r3
  bf k_l
  bra c_fail
  nop
k_hit:
  mov r3,r0
  add r0,r0
  mov.l #%(T_KEY)d,r1
  add r8,r1
  mov.w @(r0,r1),r3
  extu.w r3,r3
  mov r3,r4
  shlr8 r4
  shlr2 r4
  mov r3,r5
  shlr2 r5
  shlr2 r5
  shlr r5
  mov #31,r1
  and r1,r5
  mov r3,r6
  and r1,r6
  mov.l #%(V_K2)d,r0
  mov.b @(r0,r8),r2
  extu.b r2,r2
  mov #19,r1
  cmp/hs r1,r2
  bt c_vowel
  tst r6,r6
  bf c_comp
  mov.l #%(T_JOC)d,r0
  add r8,r0
  mov.b @(r0,r2),r6
  extu.b r6,r6
  tst r6,r6
  bt c_fail
  bsr syl
  nop
  mov #0,r1
  bra c_ret
  nop
c_comp:
  mov.l #%(T_COMP)d,r7
  add r8,r7
  mov #%(N_COMP)d,r3
c_comp_l:
  mov.b @r7,r1
  cmp/eq r1,r6
  bf c_comp_n
  mov.b @(1,r7),r0
  cmp/eq r0,r2
  bf c_comp_n
  mov.b @(2,r7),r0
  extu.b r0,r6
  bsr syl
  nop
  mov #0,r1
  bra c_ret
  nop
c_comp_n:
  add #3,r7
  dt r3
  bf c_comp_l
  bra c_fail
  nop
c_vowel:
  add #-19,r2
  tst r6,r6
  bf c_split
  mov.l #%(T_VCOMP)d,r7
  add r8,r7
  mov #%(N_VCOMP)d,r3
c_v_l:
  mov.b @r7,r1
  cmp/eq r1,r5
  bf c_v_n
  mov.b @(1,r7),r0
  cmp/eq r0,r2
  bf c_v_n
  mov.b @(2,r7),r0
  extu.b r0,r5
  mov #0,r6
  bsr syl
  nop
  mov #0,r1
  bra c_ret
  nop
c_v_n:
  add #3,r7
  dt r3
  bf c_v_l
  bra c_fail
  nop
c_split:
  mov.l #%(V_V)d,r0
  mov.b r2,@(r0,r8)
  mov r6,r0
  add r0,r0
  mov.l #%(T_SPLIT)d,r1
  add r8,r1
  add r0,r1
  mov.b @r1,r6
  extu.b r6,r6
  mov.b @(1,r1),r0
  mov r0,r2
  mov.l #%(V_C2)d,r0
  mov.b r2,@(r0,r8)
  bsr syl
  nop
  tst r0,r0
  bt c_fail
  mov.l #%(V_P)d,r1
  add r8,r1
  mov.w r0,@r1
  mov.l #%(V_C2)d,r0
  mov.b @(r0,r8),r4
  extu.b r4,r4
  mov.l #%(V_V)d,r0
  mov.b @(r0,r8),r5
  extu.b r5,r5
  mov #0,r6
  bsr syl
  nop
  tst r0,r0
  bt c_fail
  mov r0,r1
  mov.l #%(V_P)d,r2
  add r8,r2
  mov.w @r2,r0
  extu.w r0,r0
  bra c_ret
  nop
c_fail:
  mov #0,r0
  mov #0,r1
c_ret:
  lds.l @r15+,pr
  rts
  nop

syl:
  mov r4,r7
  shll8 r7
  shll2 r7
  mov r5,r0
  shll2 r0
  shll2 r0
  shll r0
  or r0,r7
  or r6,r7
  mov #0,r1
  mov.l #%(N_SYL)d,r2
  mov.l #%(T_KEY)d,r6
  add r8,r6
s_loop:
  cmp/hs r2,r1
  bt s_none
  mov r1,r3
  add r2,r3
  shlr r3
  mov r3,r0
  add r0,r0
  mov.w @(r0,r6),r5
  extu.w r5,r5
  cmp/eq r7,r5
  bt s_found
  cmp/hs r7,r5
  bt s_hi
  mov r3,r1
  add #1,r1
  bra s_loop
  nop
s_hi:
  mov r3,r2
  bra s_loop
  nop
s_found:
  mov.l #%(T_CODE)d,r1
  add r8,r1
  mov.w @(r0,r1),r0
  extu.w r0,r0
  rts
  nop
s_none:
  mov #0,r0
  rts
  nop
.pool
'''


def far(text):
    """bt/bf 를 «반대 조건으로 건너뛰기 + bra» 로 펴서 거리 제한(±256 B) 없앰"""
    out = []; n = 0
    for ln in text.split('\n'):
        q = ln.strip().split()
        if len(q) == 2 and q[0] in ('bt', 'bf'):
            n += 1; inv = 'bf' if q[0] == 'bt' else 'bt'
            out += ['  %s _f%d' % (inv, n), '  bra %s' % q[1], '  nop', '_f%d:' % n]
        else: out.append(ln)
    return '\n'.join(out)


def key_of(ch):
    s = ord(ch) - 0xAC00
    return (s // 588) << 10 | (s // 28 % 21) << 5 | s % 28


def tables(cmap):
    """cmap = {글자: 코드} — 자모 40 코드 + 한글 음절(열쇠 순) 열쇠·코드"""
    jc = [cmap[c] for c in JAMO]
    syl = sorted((key_of(c), code) for c, code in cmap.items() if 0xAC00 <= ord(c) <= 0xD7A3)
    keys = [k for k, _ in syl]; codes = [c for _, c in syl]
    assert len(set(codes)) == len(codes) and not set(codes) & set(jc)
    return jc, keys, codes


def ref_combine(prev, k, jc, keys, codes):
    """기준 조합기(jamo.combine 과 같은 규칙, 음절 집합만 다름) → (P, N) 또는 None"""
    import bisect
    def syl(c, v, t):
        x = c << 10 | v << 5 | t; i = bisect.bisect_left(keys, x)
        return codes[i] if i < len(keys) and keys[i] == x else 0
    if prev in jc:
        pk = jc.index(prev)
        if pk < 19 and k >= 19:
            p = syl(pk, k - 19, 0); return (p, 0) if p else None
        return None
    if prev not in codes: return None
    key = keys[codes.index(prev)]; c, v, t = key >> 10, key >> 5 & 31, key & 31
    if k < 19:
        if t == 0:
            jt = jamo.JONG_OF_CHO[k]
            if not jt: return None
            p = syl(c, v, jt); return (p, 0) if p else None
        for a, b, cc in jamo.COMP:
            if a == t and b == k:
                p = syl(c, v, cc); return (p, 0) if p else None
        return None
    V = k - 19
    if t == 0:
        for a, b, cc in jamo.VCOMP:
            if a == v and b == V:
                p = syl(c, cc, 0); return (p, 0) if p else None
        return None
    t1, c2 = jamo.SPLIT[t]
    p = syl(c, v, t1); n = syl(c2, V, 0)
    return (p, n) if p and n else None


def blob(cmap, hb, ad):
    """hb = 블롭 RAM 주소(4 정렬). 돌려줌: (바이트, 기호표)"""
    jc, keys, codes = tables(cmap)
    T = dict(T_JC=b''.join(struct.pack('>H', c) for c in jc),
             T_KEY=b''.join(struct.pack('>H', k) for k in keys),
             T_CODE=b''.join(struct.pack('>H', c) for c in codes),
             T_JOC=bytes(jamo.JONG_OF_CHO) + b'\0',
             T_COMP=b''.join(bytes(x) for x in jamo.COMP),
             T_VCOMP=b''.join(bytes(x) for x in jamo.VCOMP),
             T_SPLIT=b''.join(bytes(x) for x in jamo.SPLIT))
    P = {k: v for k, v in ad.items() if k != 'OFF'}
    P.update(HB=hb, N_SYL=len(keys), N_COMP=len(jamo.COMP), N_VCOMP=len(jamo.VCOMP))
    VB = ('V_POS', 'V_LAST', 'V_K', 'V_K2', 'V_V', 'V_C2'); VW = ('V_LCODE', 'V_N', 'V_P')
    for n in list(T) + list(VB) + list(VW): P.setdefault(n, 0)
    for _ in range(4):
        code = sh2asm.assemble(far(ASM % P), hb)
        o = (len(code) + 3) & ~3; lay = {}
        for n, d in T.items(): lay[n] = o; o += len(d); o = (o + 1) & ~1
        for n in VW: lay[n] = o; o += 2
        for n in VB: lay[n] = o; o += 1
        if all(P[k] == v for k, v in lay.items()): break
        P.update(lay)
    else: raise SystemExit('블롭 배치가 안 맞음')
    out = bytearray(code) + bytes(o - len(code))
    for n, d in T.items(): out[P[n]:P[n] + len(d)] = d
    out[P['V_LAST']] = 0xFF
    return bytes(out), P


def stub(ad, hb):
    """FCA2 BRA FE5A → BRA FCA6(다 찬 때도 훅), FCA6 = mov.l @(lit),r0 / jmp @r0 / nop / 리터럴(FCAC)"""
    o = ad['OFF']
    s = {o + 4: struct.pack('>H', 0xA000)}                       # FCA2: bra +0 → FCA6 (지연 슬롯 FCA4 nop 그대로)
    assert (ad['HOOK'] & 3) == 2
    s[o + 8] = struct.pack('>HHH', 0xD001, 0x402B, 0x0009) + struct.pack('>I', hb)
    return s


def apply(exe, cmap, limit):
    """0.BIN(bytearray) 끝에 블롭 덧붙이고 훅을 건다 → 블롭 크기"""
    ad = addrs(exe)
    e1 = open(os.path.join(ROOT, 'work', 'disc1', '0.BIN'), 'rb').read()
    assert exe[ad['OFF']:ad['OFF'] + 18] == e1[D1:D1 + 18], '훅 자리 원본 아님(두 번 걸었나?)'
    while len(exe) % 4: exe += b'\0'
    hb = EXE_BASE + len(exe)
    b, P = blob(cmap, hb, ad)
    exe += b
    assert EXE_BASE + len(exe) <= limit, ('이름 훅 블롭이 덧붙임 한도 넘음', hex(EXE_BASE + len(exe)), hex(limit))
    for at, d in stub(ad, hb).items(): exe[at:at + len(d)] = d
    return len(b), hb


# ---------------- 시험 ----------------
def test():
    sys.stdout.reconfigure(encoding='utf-8')
    import random
    import build_kr
    # 시험용 cmap: 글꼴 계획과 같은 음절 집합(한글 = name_extra ∪ font_map) + 자모, 코드는 가짜(SJIS 꼴 아무 값)
    chars = sorted(build_kr.name_extra() | {l.split('\t')[0] for l in open(os.path.join(ROOT, 'work', 'font_map.tsv'), encoding='utf-8')
                                             if 0xAC00 <= ord(l[0]) <= 0xD7A3})
    cmap = {c: 0x8800 + i for i, c in enumerate(chars)}
    for k, c in enumerate(JAMO): cmap[c] = 0xE000 + k
    rev = {v: k for k, v in cmap.items()}
    exe = bytearray(open(os.path.join(ROOT, 'work', 'disc1', '0.BIN'), 'rb').read())
    ad = addrs(exe); hb = 0x0609CC7C
    bl, P = blob(cmap, hb, ad)
    jc, keys, codes = tables(cmap)
    print('블롭 %d B (코드 %d B · 음절 %d) → 0x%08X~0x%08X' % (len(bl), P['T_JC'], len(keys), hb, hb + len(bl)))
    mem = sh2sim.Mem(); mem.add(0x06000000, 0x100000)
    for k, v in enumerate(bl): mem.w8(hb + k, v)
    # 1) combine 전수 대조
    import re as _re
    labs = {}; pc = hb
    for ln in far(ASM % P).split('\n'):
        s = ln.split(';')[0].strip()
        if not s: continue
        m = _re.match(r'^(\w+):$', s)
        if m: labs[m.group(1)] = pc; continue
        if s == '.pool': continue
        pc += 2
    random.seed(1)
    prevs = jc + random.sample(codes, 600)
    bad = n = 0
    for pv in prevs:
        for k in range(40):
            regs = [0] * 16; regs[4] = pv; regs[5] = k; regs[8] = hb; regs[15] = 0x060FF000
            rr, _ = sh2sim.run(mem, labs['combine'], regs=regs)
            got = (rr[0] & 0xFFFF, rr[1] & 0xFFFF); exp = ref_combine(pv, k, jc, keys, codes) or (0, 0)
            n += 1
            if got != exp:
                bad += 1
                if bad < 10: print('다름', rev.get(pv), JAMO[k], got, exp)
    print('combine 대조 %d건, 다름 %d' % (n, bad))
    # 2) 입력 순서 — 진짜 진입(FCA6 스텁 → 블롭)부터, 그리기·소리·나가기는 흉내
    NAMEB, FR = 0x0604F900, 0x060F0000
    class Exit(Exception): pass
    def ex(name):
        def f(r, m): raise Exit(name)
        return f
    def nop(r, m): pass
    def typing(seq, page=0):
        for a in range(12): mem.w8(NAMEB + a, 0)
        mem.w32(FR + 20, NAMEB); mem.w32(FR + 44, 0); mem.w32(FR + 40, NAMEB); mem.w32(FR + 24, 0); mem.w32(FR + 28, page)
        mem.w8(hb + P['V_LAST'], 0xFF)
        mem.w32(ad['CURX'], 0)
        log = []
        for x in seq:
            k = JAMO.index(x)
            mem.w16(ad['BOARD'], cmap[x])                                  # 판 0쪽 0줄 0칸에 그 자모
            regs = [0] * 16; regs[14] = FR; regs[10] = 0; regs[11] = 0; regs[13] = 0x06001000; regs[15] = 0x060FE000
            calls = {ad['FIN']: ex('fin'), ad['FIN_FULL']: ex('full'), ad['REJ']: ex('rej'), ad['DRAW']: nop, ad['ERASE']: nop,
                     ad['SOUND']: nop, ad['BLINK']: nop, 0x06001000: nop}
            try:
                sh2sim.run(mem, hb, regs=regs, calls=calls, limit=500000); raise SystemExit('안 나감')
            except Exit as e:
                log.append(str(e))
        pos = mem.r32(FR + 24)
        nm = ''.join(rev.get(mem.r16(NAMEB + 2 * a), '_') if mem.r16(NAMEB + 2 * a) else '_' for a in range(5))
        assert mem.r32(FR + 40) == NAMEB + 2 * pos and mem.r32(FR + 44) == 2 * pos and mem.r32(ad['CURX']) == 0x1A0000 * pos
        return nm, pos, log
    ok = 0; cases = (('ㅎㅏㅅㅡㅍㅣ', '하스피__'), ('ㄱㅣㅁㅊㅓㄹㅅㅜ', '김철수__'), ('ㅎㅏㄴㄱㅡㄹ', '한글___'), ('ㄷㅏㄹㄱ', '닭____'),
                     ('ㄷㅏㄹㄱㅏ', '달가___'), ('ㄱㅗㅏ', '과____'), ('ㅇㅢㅅㅏ', '의사___'), ('ㅋㅔㄴㅌㅏㄹㅗ', '켄타로__'),
                     ('ㄱㅏㄱㅏㄱㅏㄱㅏㄱㅏ', '가가가가가'), ('ㄱㅏㄱㅏㄱㅏㄱㅏㄱㅏㅇ', '가가가가강'), ('ㄱㅏㄱㅏㄱㅏㄱㅏㄱㅏㅇㅏ', '가가가가강'),
                     ('ㄱㅏㄱㅏㄱㅏㄱㅏㄱㅏㅇㅅ', '가가가가강'), ('ㄱㅏㄱㅏㄱㅏㄱㅏㅇㅓㅂㅅ', '가가가가없'), ('ㅏㅏㄱ', 'ㅏㅏㄱ__'),
                     ('ㄱㄴㄷㄹㅁㅂ', 'ㄱㄴㄷㄹㅁ'), ('ㅂㅏㄹㅂㅏ', '발바___'), ('ㅇㅝㄴ', '원____'), ('ㄲㅗㅊ', '꽃____'))
    for seq, exp in cases:
        nm, pos, log = typing(seq)
        good = nm == exp; ok += good
        print('OK ' if good else '다름', seq, '→', nm, '(기대', exp + ')', 'pos', pos, log[-2:])
    print('입력 시험 %d/%d' % (ok, len(cases)))


if __name__ == '__main__':
    if sys.argv[1:] == ['test']: test()
