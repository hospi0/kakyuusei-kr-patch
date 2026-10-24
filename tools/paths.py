# -*- coding: utf-8 -*-
"""경로 모음 (2026-10-23 작업 키트) — 키트 폴더 안 것이 있으면 그것, 없으면 원래 작업 PC 경로.
  원본 디스크: <키트>/원본/ 아래 어디든 «Kakyuusei (Japan) (Disc N)…(Track 1).bin»(+ Track 2·cue 같은 폴더)
  환경 변수 KAKYU_ROM 으로 다른 폴더를 줄 수도 있다."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _pick(*c):
    c = [p for p in c if p]
    return next((p for p in c if os.path.exists(p)), c[-1])

ROM = _pick(os.environ.get('KAKYU_ROM'), os.path.join(ROOT, '원본'), r'C:\claude\roms\ss')
KFONT = _pick(os.path.join(ROOT, 'fonts', 'NanumGothicBold.ttf'), r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf')
XDELTA = _pick(os.path.join(ROOT, 'tools', 'bin', 'xdelta.exe'), r'C:\claude\utils\xdelta.exe')
