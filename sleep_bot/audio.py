#!/usr/bin/env python3
"""수면 음악 오디오 엔진 v2 — 외부 음원 0개. 모든 소리를 수학적으로 직접 합성합니다.
  · 악기 13종: 오르골 · 피아노 · 하프 · 첼레스타 · 칼림바 · 글라스벨 · 비브라폰 · 나일론 기타 · 일렉피아노 · 핸드팬 · 싱잉볼 (타현)
              플루트 · 허밍(사람 목소리 느낌) · 합창 패드 · 현악 패드 (지속음)
  · 작곡 모드 4종: song(16마디 자장가) · arp(느린 아르페지오) · ambient(브라이언 이노식 생성 음악) · drone(선법 드론 + 자유 선율)
  · 음계 6종: 장조 · 5음계 · 도리안 · 리디안 · 믹솔리디안 · 단5음계
  · ASMR 자연음 15종: 빗소리 · 처마 빗방울 · 먼 천둥 · 파도 · 시냇물 · 바람 · 풍경 · 귀뚜라미 · 장작 · 똑딱 시계 · 고양이 골골
              핑크/브라운/화이트 노이즈 · 엄마 뱃속(심장)
  · 1시간 분량을 메모리에 다 올리지 않고 30초 단위로 이어 쓰기 (GitHub Actions 메모리 안전)
"""
import math, wave
import numpy as np
from scipy import signal

SR = 44100
SCALES = {'major': [0, 2, 4, 5, 7, 9, 11], 'dorian': [0, 2, 3, 5, 7, 9, 10], 'lydian': [0, 2, 4, 6, 7, 9, 11], 'mixo': [0, 2, 4, 5, 7, 9, 10],
          'penta': [0, 2, 4, 7, 9], 'mpenta': [0, 3, 5, 7, 10]}
SCALE_KO = {'major': '장조', 'dorian': '도리안', 'lydian': '리디안', 'mixo': '믹솔리디안', 'penta': '5음계', 'mpenta': '단5음계'}


def midi_hz(m): return 440.0 * 2 ** ((m - 69) / 12)


def _rng(*k): return np.random.default_rng(abs(hash(k)) % (2 ** 32))


# =====================================================================
# 1) 타현·타악 악기 (가산 합성) — 음 높이별로 한 번만 만들고 재사용
# =====================================================================
# p: (배음 비율, 세기, 감쇠 시간상수 초) / att: 어택 초 / dur: 길이 초 / bright: 고음일수록 빨리 사라지는 정도
INSTR = {
    'musicbox': dict(p=[(1, 1.0, 1.05), (2, .30, .55), (3, .10, .35), (4.18, .09, .22), (5.43, .045, .15), (6.79, .025, .1)], att=.0025, dur=3.6, gain=.5, bright=.35),
    'piano':    dict(p=[(n, 1 / n ** 1.7, 2.6 / n ** .55) for n in range(1, 9)], att=.007, dur=5.0, gain=.62, inh=.00035, bright=.2),
    'harp':     dict(p=[(n, 1 / n ** 1.35, 1.6 / n ** .7) for n in range(1, 7)], att=.004, dur=3.4, gain=.5, bright=.25),
    'celesta':  dict(p=[(1, 1.0, .8), (2, .18, .4), (4, .07, .2), (6.2, .03, .12)], att=.002, dur=2.8, gain=.42, bright=.3),
    'kalimba':  dict(p=[(1, 1.0, .9), (2.0, .06, .25), (5.4, .18, .12), (8.9, .05, .06)], att=.0015, dur=2.6, gain=.5, bright=.4, thump=.25),
    'glass':    dict(p=[(1, 1.0, 2.2), (2.76, .28, 1.3), (5.4, .10, .7), (8.93, .04, .35)], att=.003, dur=6.0, gain=.42, bright=.3),
    'vibes':    dict(p=[(1, 1.0, 2.4), (4, .22, .9), (10, .04, .3)], att=.003, dur=5.0, gain=.48, bright=.3, trem=(4.2, .35)),
    'guitar':   dict(p=[(n, 1 / n ** 1.15, 1.9 / n ** .95) for n in range(1, 11)], att=.003, dur=3.8, gain=.55, inh=.0002, bright=.3, pluck=.35),
    'epiano':   dict(p=[(1, 1.0, 2.6), (2, .22, 1.1), (3, .07, .6), (7, .025, .25)], att=.004, dur=5.0, gain=.5, bright=.25, trem=(.9, .12)),
    'handpan':  dict(p=[(1, 1.0, 2.6), (2, .5, 1.6), (3, .28, 1.1), (4.1, .08, .5)], att=.002, dur=5.0, gain=.48, bright=.25, thump=.4),
    'bowl':     dict(p=[(1, 1.0, 9.0), (1.004, .6, 8.0), (2.71, .35, 6.0), (5.1, .15, 4.0), (8.0, .06, 2.0)], att=.03, dur=16.0, gain=.4, bright=.1),
    # v3: 펠트 피아노(현 앞에 천을 대어 아주 부드럽고 가까운 소리) · 가야금(줄을 뜯은 뒤 음이 살짝 흔들리는 농현) · 맑은 벨
    'felt':     dict(p=[(n, 1 / n ** 2.2, 2.2 / n ** .9) for n in range(1, 7)], att=.012, dur=4.5, gain=.6, inh=.0003, bright=.25, felt=.5),
    'gayageum': dict(p=[(n, 1 / n ** 1.1, 1.5 / n ** .8) for n in range(1, 9)], att=.003, dur=3.6, gain=.55, bright=.3, pluck=.25, bend=(.012, .0075)),
    'bell':     dict(p=[(1, 1.0, 3.5), (2.0, .35, 2.0), (3.0, .12, 1.2), (4.2, .1, .8), (5.4, .05, .4)], att=.002, dur=6.0, gain=.38, bright=.25),
}
_NOTE = {}


def note(ins, m):
    k = (ins, m)
    if k in _NOTE: return _NOTE[k]
    P = INSTR[ins]; f0 = midi_hz(m); n = int(P['dur'] * SR); t = np.arange(n, dtype=np.float32) / SR
    y = np.zeros(n, np.float32); rng = _rng(ins, m)
    if 'bend' in P:                                      # 가야금 농현: 뜯는 순간 살짝 높았다가 내려오고, 뒤에서 천천히 떨림
        b0, vd = P['bend']; fac = 1 + b0 * np.exp(-t / .05) + vd * np.sin(2 * np.pi * 5.2 * t) * np.clip((t - .35) / .5, 0, 1)
        phase = 2 * np.pi * np.cumsum(fac) / SR
    else: phase = 2 * np.pi * t
    for r, a, tau in P['p']:
        f = f0 * r * (1 + P.get('inh', 0) * r * r)
        if f > SR * .42: continue
        te = tau * (523.0 / f0) ** P['bright']          # 높은 음일수록 조금 빨리 사라짐 (실제 악기처럼)
        y += (a * np.sin(f * phase + rng.uniform(0, 6.28)) * np.exp(-t / te)).astype(np.float32)
    if 'felt' in P:                                      # 펠트 해머의 부드러운 '툭' + 아주 작은 건반 소리
        nn = int(.05 * SR); b = rng.standard_normal(nn).astype(np.float32) * np.exp(-np.arange(nn) / SR / .012).astype(np.float32)
        y[:nn] += signal.sosfilt(signal.butter(2, [120, 900], 'band', fs=SR, output='sos'), b).astype(np.float32) * P['felt']
    if 'trem' in P:                                      # 비브라폰·일렉피아노 트레몰로
        fr, dp = P['trem']; y *= (1 - dp * .5 + dp * .5 * np.sin(2 * np.pi * fr * t + rng.uniform(0, 6.28))).astype(np.float32)
    if 'thump' in P:                                     # 칼림바·핸드팬: 손가락이 닿는 낮은 '툭'
        y += (P['thump'] * np.sin(2 * np.pi * f0 * .5 * t) * np.exp(-t / .04)).astype(np.float32)
    if 'pluck' in P:                                     # 기타: 손톱이 줄을 긁는 짧은 노이즈
        nn = int(.012 * SR); b = rng.standard_normal(nn).astype(np.float32) * np.linspace(1, 0, nn, dtype=np.float32)
        y[:nn] += signal.sosfilt(signal.butter(2, [800, 5000], 'band', fs=SR, output='sos'), b).astype(np.float32) * P['pluck']
    na = max(1, int(P['att'] * SR)); y[:na] *= np.linspace(0, 1, na, dtype=np.float32)
    nf = int(.08 * SR); y[-nf:] *= np.linspace(1, 0, nf, dtype=np.float32)
    y *= P['gain'] / (np.abs(y).max() + 1e-9) * (523.0 / max(f0, 140)) ** .18   # 고음 귀 따가움 완화
    _NOTE[k] = y; return y


# =====================================================================
# 1b) 지속음 악기 (플루트 · 허밍 · 합창 · 현악 · 패드) — 길이에 따라 만듦
# =====================================================================
def _formant_w(f, peaks):
    """포먼트(성도 공명) 가중치: peaks=[(중심Hz, 폭Hz, 세기)]"""
    return sum(a * np.exp(-((f - c) / bw) ** 2) for c, bw, a in peaks) + .02


SUS = {
    'flute':   dict(att=.12, rel=.3, vib=(5.2, .0035, .5), gain=.3),
    'hum':     dict(att=.16, rel=.28, vib=(5.4, .005, .35), gain=.34, formant=[(280, 90, 1.0), (850, 220, .25), (2400, 400, .05)], breath=.012),
    'choir':   dict(att=.9, rel=1.4, vib=(4.6, .004, 1.0), gain=.22, formant=[(300, 110, 1.0), (700, 200, .45), (2500, 500, .05)], voices=3),
    'strings': dict(att=.6, rel=1.2, vib=(5.0, .003, .8), gain=.2, voices=3),
    'pad':     dict(att=1.4, rel=2.5, vib=(4.3, .0018, 0), gain=.16, voices=4),
    'ocarina': dict(att=.09, rel=.25, vib=(5.0, .003, .4), gain=.3, harm=[1, .06, .1, .02], breath=.014),
    'daegeum': dict(att=.14, rel=.35, vib=(4.8, .008, .55), gain=.3, harm=[1, .55, .32, .2, .12, .07], breath=.045, scoop=-.012, buzz=.18),
    # 드림웨이브 (80년대 아날로그 신스 느낌): 톱니파를 둥글게 깎은 패드 · 부드러운 사각파 리드 · 서브 베이스
    'synth':     dict(att=1.6, rel=3.0, vib=(.35, .0016, 0), gain=.15, voices=4, det=[-9, 9, -3, 4], harm=[1 / h * max(0, 1 - (h - 1) / 12) ** 1.4 for h in range(1, 13)]),
    'synthlead': dict(att=.22, rel=.9, vib=(4.8, .0042, .6), gain=.2, voices=2, det=[-4, 4], harm=[1, 0, .28, 0, .12, 0, .05]),
    'sub':       dict(att=.25, rel=.8, vib=(1.0, 0, 0), gain=.3, harm=[1, .06]),
}
_SUS = {}


def sus_note(ins, m, dur):
    k = (ins, m, round(dur, 1))
    if k in _SUS: return _SUS[k]
    P = SUS[ins]; rel = P['rel']; n = int((dur + rel) * SR); t = np.arange(n, dtype=np.float32) / SR; f0 = midi_hz(m)
    rng = _rng(ins, m, round(dur, 1)); out = np.zeros((2, n), np.float32)
    vf, vd, vdelay = P['vib']; vib = 1 + vd * np.sin(2 * np.pi * vf * t + rng.uniform(0, 6.28)) * np.clip((t - vdelay) / .6, 0, 1)
    voices = P.get('voices', 1)
    for vi in range(voices):
        cents = 0 if voices == 1 else P.get('det', [-6, 6, 0, 3])[vi]; ch = vi % 2 if voices > 1 else None
        f = f0 * 2 ** (cents / 1200); drift = 1 + .004 * np.exp(-t / .12) * (1 if ins == 'flute' else 0) + P.get('scoop', 0) * np.exp(-t / .09)
        ph = 2 * np.pi * f * np.cumsum(vib * drift) / SR
        y = np.zeros(n, np.float32)
        for h in range(1, 14):
            fh = f * h
            if fh > SR * .42: break
            if 'formant' in P: a = _formant_w(fh, P['formant']) / h ** .6
            elif ins == 'flute': a = [1, .35, .14, .06, .03][h - 1] if h <= 5 else 0
            elif 'harm' in P: a = P['harm'][h - 1] if h <= len(P['harm']) else 0
            else: a = (.72 ** (h - 1)) / h
            if a > 1e-3: y += (a * np.sin(h * ph + rng.uniform(0, 6.28))).astype(np.float32)
        if P.get('buzz'):                                # 대금 청(갈대막) 울림: 높은 배음이 거칠게 떨림
            bz = signal.sosfilt(signal.butter(2, [min(f * 3, 9000), min(f * 8, 16000)], 'band', fs=SR, output='sos'), np.sin(5 * ph) * (1 + rng.standard_normal(n) * .6)).astype(np.float32)
            y += bz * P['buzz']
        if ch is None: out += np.vstack([y, y]) * .5
        else: out[ch] += y; out[1 - ch] += y * .35
    if P.get('breath') or ins == 'flute':
        b = rng.standard_normal(n).astype(np.float32)
        b = signal.sosfilt(signal.butter(2, [min(f0 * 1.5, 9000), min(f0 * 5, 15000)], 'band', fs=SR, output='sos'), b).astype(np.float32)
        out += np.vstack([b, b]) * (P.get('breath', .02)) * (1 + .5 * np.sin(2 * np.pi * .7 * t))
    a = np.sin(np.clip(t / P['att'], 0, 1) * np.pi / 2) ** 2; r = np.clip((dur + rel - t) / rel, 0, 1) ** 1.5
    swell = 1 - .18 * np.cos(np.clip(t / max(dur, .5), 0, 1) * 2 * np.pi) if ins in ('flute', 'hum', 'choir', 'strings', 'ocarina', 'daegeum') else 1   # 가운데가 살짝 부푸는 호흡
    out *= (a * r * swell).astype(np.float32)
    out *= P['gain'] / (np.abs(out).max() + 1e-9) * (300.0 / max(f0, 110)) ** .12
    _SUS[k] = out; return out


def pan(x, p):  # p: -1(왼) ~ 1(오), 일정 파워
    a = (p + 1) * math.pi / 4; return np.vstack([x * math.cos(a), x * math.sin(a)])


# =====================================================================
# 2) 작곡기 — 4가지 모드
# =====================================================================
PROGS = [[1, 6, 4, 5], [1, 4, 1, 5], [1, 3, 4, 1], [6, 4, 1, 5], [1, 5, 6, 4], [1, 4, 6, 5], [4, 1, 5, 1], [1, 6, 2, 5], [1, 2, 4, 1], [1, 7, 4, 1]]
RHY3 = [[2, 1], [1, 1, 1], [3], [1, 2], [1.5, .5, 1], [2, 1], [1, 1, 1]]
RHY4 = [[2, 2], [1, 1, 2], [3, 1], [4], [2, 1, 1], [1.5, .5, 2], [2, 2]]
PERC = set(INSTR)

# 스타일 = 작곡 모드 + 악기 편성. 테마는 style 하나 또는 여러 개(곡마다 번갈아)를 고릅니다.
STYLE = {
    # --- song: 16마디 자장가 (A A' B A''), 멜로디 3번 반복하며 악기·옥타브 바꿈
    'musicbox': dict(mode='song', mel='musicbox', acc='harp', oct=6, meter=3, bpm=(54, 64), pad='pad', padv=.8, scales=['major', 'lydian'], counter='strings'),
    'piano':    dict(mode='song', mel='piano', acc='piano', oct=5, meter=4, bpm=(52, 60), pad='pad', padv=1.0, gain=-2.8, scales=['major', 'mixo']),
    'harp':     dict(mode='song', mel='celesta', acc='harp', oct=6, meter=3, bpm=(56, 66), pad='pad', padv=.9, scales=['major'], counter='ocarina', counterv=.22),
    'mixed':    dict(mode='song', mel='musicbox', acc='piano', oct=6, meter=3, bpm=(52, 62), pad='pad', padv=.9, scales=['major', 'lydian']),
    'guitar':   dict(mode='song', mel='guitar', acc='guitar', oct=5, meter=3, bpm=(50, 60), pad='strings', padv=.6, scales=['major', 'mixo'], counter='hum', counterv=.25),
    'humming':  dict(mode='song', mel='hum', acc='harp', oct=5, meter=3, bpm=(48, 56), pad='choir', padv=.7, scales=['major'], gain=-1.5),
    'flute_song': dict(mode='song', mel='flute', acc='guitar', oct=6, meter=4, bpm=(50, 58), pad='strings', padv=.7, scales=['major', 'dorian']),
    'vibes':    dict(mode='song', mel='vibes', acc='epiano', oct=5, meter=4, bpm=(50, 58), pad='pad', padv=.7, scales=['major', 'lydian'], counter='choir', counterv=.28),
    'ocarina_song': dict(mode='song', mel='ocarina', acc='harp', oct=6, meter=3, bpm=(50, 58), pad='pad', padv=.6, scales=['major', 'lydian'], counter='strings', counterv=.25),
    'bell_song':    dict(mode='song', mel='bell', acc='celesta', oct=5, meter=3, bpm=(52, 60), pad='choir', padv=.55, scales=['major', 'lydian']),
    # --- nocturne: 펠트 피아노 녹턴 (가까이서 듣는 아주 부드러운 피아노, 루바토)
    'felt_nocturne':  dict(mode='nocturne', inst='felt', bpm=(46, 54), scales=['major', 'mixo', 'dorian'], wet=.42, gain=-1.0),
    'piano_nocturne': dict(mode='nocturne', inst='piano', bpm=(44, 52), scales=['major', 'lydian'], pad='strings', padv=.35, wet=.42, gain=-3.0),
    # --- canon: 돌림노래
    'musicbox_canon': dict(mode='canon', voices=[('musicbox', 12, .3, .55), ('celesta', 24, -.4, .42), ('bell', 0, .1, .36)], bass='harp', bpm=(54, 62), meter=4, pad='pad', padv=.55, scales=['major', 'lydian']),
    'harp_canon':     dict(mode='canon', voices=[('harp', 12, -.3, .55), ('ocarina', 12, .35, .4), ('glass', 24, .1, .3)], bass='harp', bpm=(50, 58), meter=3, pad='strings', padv=.45, scales=['major']),
    'felt_canon':     dict(mode='canon', voices=[('felt', 12, -.2, .55), ('felt', 24, .3, .38), ('hum', 0, 0.0, .3)], bass='felt', bpm=(48, 56), meter=4, pad='pad', padv=.4, scales=['major', 'mixo']),
    # --- folk: 한국 전통 자장가풍 (5음 음계, 화음 없이)
    'gayageum_folk': dict(mode='folk', mel='gayageum', mel2='daegeum', acc='gayageum', bpm=(40, 48), scales=['penta', 'mpenta'], drone='strings', wet=.4),
    'daegeum_folk':  dict(mode='folk', mel='daegeum', mel2='gayageum', acc='gayageum', bpm=(38, 46), scales=['mpenta', 'penta'], wet=.45),
    # --- arp: 느린 아르페지오 + 드문 선율
    'kalimba_arp': dict(mode='arp', arp='kalimba', mel='celesta', bpm=(50, 58), pad='pad', padv=.8, scales=['penta', 'major']),
    'guitar_arp':  dict(mode='arp', arp='guitar', mel='flute', bpm=(46, 54), pad='strings', padv=.6, scales=['major', 'mixo']),
    'epiano_arp':  dict(mode='arp', arp='epiano', mel='vibes', bpm=(48, 56), pad='choir', padv=.5, scales=['major', 'lydian', 'dorian']),
    'harp_arp':    dict(mode='arp', arp='harp', mel='musicbox', bpm=(50, 60), pad='pad', padv=.8, scales=['major', 'penta']),
    'handpan_arp': dict(mode='arp', arp='handpan', mel='flute', bpm=(44, 52), pad='choir', padv=.5, scales=['mpenta', 'dorian']),
    # --- ambient: 박자 없이 여러 목소리가 각자 주기로 음을 띄움 (이노식 생성 음악)
    'glass_ambient': dict(mode='ambient', voices=['glass', 'celesta', 'pad', 'glass', 'vibes'], drone='pad', scales=['penta', 'lydian'], wet=.5),
    'bowl_ambient':  dict(mode='ambient', voices=['bowl', 'bowl', 'glass', 'choir', 'handpan'], drone='choir', scales=['mpenta', 'penta'], wet=.55),
    'piano_ambient': dict(mode='ambient', voices=['piano', 'piano', 'epiano', 'strings', 'glass'], drone='strings', scales=['penta', 'major'], wet=.5),
    'felt_ambient':  dict(mode='ambient', voices=['felt', 'felt', 'felt', 'bell', 'ocarina'], drone='pad', scales=['penta', 'major', 'lydian'], wet=.45),
    'ocean_ambient': dict(mode='ambient', voices=['glass', 'bell', 'choir', 'handpan', 'pad'], drone='choir', scales=['lydian', 'penta'], wet=.6),
    'kalimba_ambient': dict(mode='ambient', voices=['kalimba', 'kalimba', 'glass', 'pad', 'flute'], drone='pad', scales=['penta'], wet=.45),
    # --- drone: 선법 드론 위에 자유 박자 선율 (명상)
    'dreamwave':     dict(mode='dream', pad='synth', padv=.75, keys='epiano', keysv=.3, mel='synthlead', melv=.28, meld=.55, bpm=(60, 70), scales=['major', 'lydian', 'major'], wet=.5, width=1.45, tape=True, gain=-1.0),
    'dream_vibes':   dict(mode='dream', pad='synth', padv=.7, keys='epiano', keysv=.28, mel='vibes', melv=.3, meld=.6, bpm=(58, 66), scales=['major', 'dorian'], wet=.52, width=1.45, tape=True, gain=-1.0),
    'dream_glass':   dict(mode='dream', pad='synth', padv=.8, keys='epiano', keysv=.24, mel='glass', melv=.26, meld=.5, bpm=(54, 62), scales=['lydian', 'major'], wet=.58, width=1.5, tape=True, gain=-1.5),
    'citypop':       dict(mode='dream', pad='synth', padv=.68, keys='epiano', keysv=.34, mel='synthlead', melv=.3, meld=.7, bpm=(64, 74), scales=['major', 'lydian'], wet=.46, width=1.4, tape=True, gain=-1.0),
    'citypop_vibes': dict(mode='dream', pad='synth', padv=.66, keys='epiano', keysv=.32, mel='vibes', melv=.32, meld=.7, bpm=(62, 72), scales=['major', 'mixo'], wet=.48, width=1.4, tape=True, gain=-1.0),
    'dream_ambient': dict(mode='ambient', voices=['epiano', 'glass', 'synthlead', 'epiano', 'vibes'], drone='synth', scales=['lydian', 'major'], wet=.58, width=1.5, tape=True),
    'flute_drone': dict(mode='drone', mel='flute', drone='strings', chord='choir', scales=['dorian', 'mixo', 'lydian'], wet=.5),
    'hum_drone':   dict(mode='drone', mel='hum', drone='choir', chord='pad', scales=['dorian', 'major'], wet=.5),
    'bowl_drone':  dict(mode='drone', mel='bowl', drone='choir', chord='strings', scales=['mpenta', 'dorian'], wet=.55),
}


def chord_idx(deg):  # 화음 구성음 (음계 인덱스)
    r = deg - 1; return [r, r + 2, r + 4]


def _tonic(R): return 60 + int(R.choice([0, 2, 5, 7, -3, -1, -5, 4]))


def compose_song(seed, S):
    R = np.random.default_rng(seed); sc_name = str(R.choice(S['scales'])); SC = SCALES[sc_name]
    tonic = _tonic(R); meter = S['meter']; bpm = float(R.uniform(*S['bpm'])); beat = 60 / bpm; bar = meter * beat
    rhy = RHY3 if meter == 3 else RHY4
    P = [int(x) for x in PROGS[R.integers(len(PROGS))]]; Q = [int(x) for x in PROGS[R.integers(len(PROGS))]]
    while Q == P: Q = [int(x) for x in PROGS[R.integers(len(PROGS))]]
    lo, hi = 0, 10

    def gen_bar(deg, prev, rh, last=False, end_tonic=False, center=4):
        out = []; cur = prev; on = 0.0
        for k, d in enumerate(rh):
            if k == 0 or last:
                cands = [c + 7 * o for c in chord_idx(deg) for o in (-1, 0, 1) if lo <= c + 7 * o <= hi]
                if end_tonic: cands = [c for c in cands if c % 7 == 0] or [0]
                cur = min(cands, key=lambda c: abs(c - cur) + .25 * abs(c - center) + R.uniform(0, 1.2))
            else:
                cur = int(np.clip(cur + int(R.choice([-2, -1, -1, 1, 1, 2, 0])), lo, hi))
            out.append((on, d, cur)); on += d
        return out

    def phrase(prog, prev, rhs=None, center=4, cad=False):
        bars = []; rhs = rhs or [rhy[R.integers(len(rhy))] for _ in range(3)] + [[meter]]
        for i, deg in enumerate(prog):
            b = gen_bar(deg, prev, rhs[i], last=(i == 3), end_tonic=(cad and i == 3), center=center); prev = b[-1][2]; bars.append(b)
        return bars, rhs, prev

    A, rA, pv = phrase(P, 4); A2 = A[:3] + [gen_bar(P[3], A[2][-1][2], [meter], last=True)]
    B, _, pv = phrase(Q, A2[-1][-1][2], center=6); Pc = P[:2] + [5, 1]
    A3 = A[:2] + phrase(Pc, A[1][-1][2], rhs=rA[:2] + [rhy[0], [meter]], cad=True)[0][2:]
    mel_bars = A + A2 + B + A3; chords = P + P + Q + Pc
    ev = []; base = tonic + 12 * (S['oct'] - 5)
    to_midi = lambda ix: base + SC[ix % 7] + 12 * (ix // 7)
    hum = lambda: float(R.normal(0, .008))
    intro = 2; mel = S['mel']; sus_mel = mel in SUS
    acc2 = S['acc'] if S['acc'] != 'piano' else 'celesta'
    passes = [(mel, 0, .78), (acc2 if not sus_mel else mel, 0, .62), (mel, 12 if S['oct'] < 6 and not sus_mel else 0, .66)]
    if sus_mel: passes[1] = (S['acc'] if S['acc'] in PERC else 'celesta', 12, .55)   # 허밍·플루트 곡은 가운데 한 번 악기 독주
    n_pass = len(passes); total_bars = intro + 16 * n_pass + 3
    for b in range(total_bars):
        deg = chords[(b - intro) % 16] if intro <= b < intro + 16 * n_pass else 1
        t0 = b * bar; ci = chord_idx(deg); root = tonic - 12 + SC[ci[0] % 7]
        if b < total_bars - 2:
            if meter == 3: notes = [(0, root, .42), (1, tonic + SC[ci[1] % 7] + (12 if ci[1] >= 7 else 0), .26), (2, tonic + SC[ci[2] % 7] + (12 if ci[2] >= 7 else 0), .24)]
            else: notes = [(0, root, .4), (1, tonic + SC[ci[2] % 7], .24), (2, tonic + 12 + SC[ci[1] % 7], .24), (3, tonic + SC[ci[2] % 7], .22)]
            for bt, m, v in notes: ev.append((t0 + bt * beat + hum(), S['acc'], int(m), v * float(R.uniform(.85, 1.05)), -.25, None))
        elif b == total_bars - 2:
            for m, v in ((tonic - 12, .36), (tonic + SC[2], .22), (tonic + 7, .2), (tonic + 12, .18)): ev.append((t0 + hum(), S['acc'], m, v, -.2, None))
        if S.get('pad'):
            for ix in ci: ev.append((t0, S['pad'], tonic - 12 + SC[ix % 7] + 12 * (ix // 7), S['padv'] * (.9 if b < total_bars - 2 else .7), 0.0, bar if b < total_bars - 2 else bar * 2.5))
    cprev = 9
    for p, (ins, up, vel) in enumerate(passes):
        for i, br in enumerate(mel_bars):
            t0 = (intro + p * 16 + i) * bar
            arch = .84 + .24 * math.sin(math.pi * ((i % 4) + .5) / 4)            # 프레이즈마다 부풀었다 가라앉는 셈여림
            for on, d, ix in br:
                acc = 1.08 if on == 0 else .95; m = to_midi(ix) + up; v = vel * acc * arch
                if ins in SUS: ev.append((t0 + on * beat + hum(), ins, m - 12 if ins == 'hum' else m, v * float(R.uniform(.9, 1.02)), .15, d * beat * .96))
                else:
                    if p == n_pass - 1 and d >= 2 and R.random() < .3:            # 마지막 반복: 가끔 윗음에서 꾸밈음
                        ev.append((t0 + on * beat - .11 * beat, ins, to_midi(ix + 1) + up, v * .45, .2, None))
                    ev.append((t0 + on * beat + hum(), ins, m, v * float(R.uniform(.88, 1.04)), .2 + .04 * (ix - 4), None))
            if S.get('counter') and p >= 1:                                       # 두 번째 반복부터 대선율(길게 받쳐 주는 음)
                ci = chord_idx(chords[i % 16]); cands = [c + 7 for c in ci] + [c + 14 for c in ci]
                cprev = min(cands, key=lambda c: abs(c - cprev) + R.uniform(0, 1.5))
                ev.append((t0 + hum(), S['counter'], to_midi(cprev) - 12, S.get('counterv', .32) * arch, -.35, bar * .98))
    return ev, total_bars * bar, dict(tonic=tonic, bpm=round(bpm), meter=meter, scale=sc_name, mode='song', inst=mel)


def compose_nocturne(seed, S):
    """녹턴: 왼손은 셋잇단 분산화음, 오른손은 느린 노래. 프레이즈 끝마다 템포가 살짝 느려짐(루바토)"""
    R = np.random.default_rng(seed); sc_name = str(R.choice(S['scales'])); SC = SCALES[sc_name]; tonic = _tonic(R)
    bpm = float(R.uniform(*S['bpm'])); beat = 60 / bpm; ins = S['inst']
    P = [int(x) for x in PROGS[R.integers(len(PROGS))]]; Q = [int(x) for x in PROGS[R.integers(len(PROGS))]]
    plan = [('A', P), ('A', P), ('B', Q), ('A2', P)]; prog = sum([p[1] + p[1] for p in plan], [])     # 32마디
    total = 1 + len(prog) + 2
    lens = [4 * beat * (1 + (.09 if (i - 1) % 4 == 3 else 0) + (.18 if i >= total - 2 else 0)) for i in range(total)]   # 루바토
    starts = np.concatenate([[0], np.cumsum(lens)]); ev = []
    to_m = lambda ix: tonic + SC[ix % 7] + 12 * (ix // 7)
    LH = [0, 4, 9, 4, 7, 4, 0, 4, 9, 4, 11, 4]                                       # 근음·5도·10도 셋잇단 12개
    mel_rh = [[2, 2], [3, 1], [4], [1, 1, 2], [2, 1, 1], [1.5, .5, 2]]
    prev = 9; cache = {}
    for b in range(total):
        t0 = starts[b]; L = lens[b]; tri = L / 12
        if b == 0 or b >= total - 2: deg = 1
        else: deg = prog[b - 1]
        ci = chord_idx(deg); root = tonic - 24 + SC[ci[0] % 7] + (12 if ci[0] >= 4 else 0)
        third = SC[ci[1] % 7] - SC[ci[0] % 7]; third += 12 if third < 0 else 0
        offs = [0, 7, 12 + third, 7, 12, 7, 0, 7, 12 + third, 7, 19 if b % 2 else 12 + third, 7]
        if b >= total - 2:
            if b == total - 2:
                for k, o in enumerate([0, 7, 12 + third, 19, 24]): ev.append((t0 + k * tri * 1.5, ins, root + o, .3 - .03 * k, -.3 + .12 * k, None))
            continue
        for k, o in enumerate(offs):
            v = (.34 if k == 0 else .2 if k % 3 == 0 else .15) * float(R.uniform(.9, 1.05))
            ev.append((t0 + k * tri + float(R.normal(0, .006)), ins, root + o, v, -.35 + .03 * k, None))
        if b == 0: continue
        sec = plan[(b - 1) // 8][0]; bi = (b - 1) % 8; key = (sec, bi)
        if sec == 'A' and key in cache and (b - 1) // 8 == 1: notes = cache[key]                      # 두 번째 A는 첫 A를 그대로 (기억에 남는 선율)
        else:
            rh = [4] if bi in (3, 7) else mel_rh[R.integers(len(mel_rh))]; notes = []; on = 0.0
            center = 11 if sec == 'B' else 9
            for j, d in enumerate(rh):
                if j == 0 or bi in (3, 7):
                    cands = [c + 7 * o for c in ci for o in (1, 2) if 6 <= c + 7 * o <= 14]
                    if bi == 7 and sec == 'A2': cands = [c for c in cands if c % 7 == 0] or [7]
                    prev = min(cands, key=lambda c: abs(c - prev) + .3 * abs(c - center) + R.uniform(0, 1.2))
                else: prev = int(np.clip(prev + int(R.choice([-2, -1, -1, 1, 1, 2])), 5, 15))
                notes.append((on, d, prev)); on += d
            cache[key] = notes
        arch = .82 + .26 * math.sin(math.pi * (bi % 4 + .5) / 4)
        for on, d, ix in notes:
            m = to_m(ix) + (12 if sec == 'A2' else 0)
            if d >= 2 and R.random() < .2: ev.append((t0 + on * L / 4 - .08, ins, to_m(ix + 1) + (12 if sec == 'A2' else 0), .22 * arch, .2, None))
            ev.append((t0 + on * L / 4 + float(R.normal(0, .01)), ins, m, .5 * arch * (1.06 if on == 0 else .95), .15, None))
            if S.get('octave') and on == 0: ev.append((t0 + on * L / 4 + .012, ins, m - 12, .2 * arch, .1, None))
        if S.get('pad'):
            for ix in ci: ev.append((t0, S['pad'], tonic - 12 + SC[ix % 7] + 12 * (ix // 7), S['padv'], 0.0, L))
    return ev, float(starts[-1]), dict(tonic=tonic, bpm=round(bpm), meter=4, scale=sc_name, mode='nocturne', inst=ins)


def compose_canon(seed, S):
    """돌림노래(캐논): 4마디 화음 고리 위에 8마디 선율이 4마디 간격으로 악기를 바꿔 차례로 들어옴"""
    R = np.random.default_rng(seed); sc_name = str(R.choice(S['scales'])); SC = SCALES[sc_name]; tonic = _tonic(R)
    bpm = float(R.uniform(*S['bpm'])); beat = 60 / bpm; meter = S.get('meter', 4); bar = meter * beat
    loop = [int(x) for x in PROGS[R.integers(len(PROGS))]]
    rh = RHY3 if meter == 3 else RHY4; mel = []; prev = 7
    for b in range(8):
        ci = chord_idx(loop[b % 4]); r = [meter] if b in (3, 7) else rh[R.integers(len(rh))]; on = 0.0
        for j, d in enumerate(r):
            if j == 0: prev = min([c + 7 * o for c in ci for o in (0, 1, 2) if 3 <= c + 7 * o <= 13], key=lambda c: abs(c - prev) + R.uniform(0, 1.5))
            else: prev = int(np.clip(prev + int(R.choice([-1, -1, 1, 1, 2, -2])), 3, 13))
            mel.append((b, on, d, prev)); on += d
    voices = S['voices']; n_v = len(voices); body = 4 * (n_v - 1) + 16 + 4; total = 1 + body + 2; ev = []
    to_m = lambda ix: tonic + SC[ix % 7] + 12 * (ix // 7)
    for b in range(total):
        t0 = b * bar; deg = loop[(b - 1) % 4] if 1 <= b <= body else 1; ci = chord_idx(deg)
        if b < total - 2:
            ev.append((t0, S['bass'], tonic - 24 + SC[ci[0] % 7] + (12 if ci[0] >= 4 else 0), .34, -.1, None))
            if meter == 4: ev.append((t0 + 2 * beat, S['bass'], tonic - 12 + SC[ci[2] % 7] - (12 if ci[2] >= 7 else 0), .2, -.1, None))
        elif b == total - 2: ev.append((t0, S['bass'], tonic - 24, .34, -.1, None))
        if S.get('pad'):
            for ix in ci: ev.append((t0, S['pad'], tonic - 12 + SC[ix % 7] + 12 * (ix // 7), S['padv'], 0.0, bar if b < total - 2 else bar * 2.5))
    for vi, (ins, up, pn, vel) in enumerate(voices):
        start = 1 + 4 * vi
        for rr in range(3):
            for b, on, d, ix in mel:
                bb = start + b + 8 * rr
                if bb > body: continue
                fade = 1 - .4 * max(0, bb - (body - 4)) / 4
                t = bb * bar + on * beat + float(R.normal(0, .008))
                if ins in SUS: ev.append((t, ins, to_m(ix) + up, vel * fade, pn, d * beat * .95))
                else: ev.append((t, ins, to_m(ix) + up, vel * fade * (1.06 if on == 0 else .95), pn, None))
    for k, ix in enumerate([0, 2, 4, 7]): ev.append(((total - 2) * bar + k * beat * .5, voices[0][0] if voices[0][0] in PERC else 'harp', to_m(ix), .3, -.2 + .15 * k, None))
    return ev, total * bar, dict(tonic=tonic, bpm=round(bpm), meter=meter, scale=sc_name, mode='canon', inst=voices[0][0])


def compose_folk(seed, S):
    """한국 전통 자장가풍: 5음 음계(평조·계면조), 느린 3박(길게-짧게), 가야금 반주 위로 대금·가야금이 주고받음 (화음 없이)"""
    R = np.random.default_rng(seed); sc_name = str(R.choice(S['scales'])); SC = SCALES[sc_name]; n5 = len(SC); tonic = _tonic(R)
    bpm = float(R.uniform(*S['bpm'])); beat = 60 / bpm; bar = 3 * beat; ev = []
    to_m = lambda ix: tonic + SC[ix % n5] + 12 * (ix // n5)
    RH = [[2, 1], [3], [1, 1, 1], [2, 1], [1.5, .5, 1]]
    def phrase(center, end):
        out = []; cur = center
        for b in range(4):
            r = [3] if b == 3 else RH[R.integers(len(RH))]; on = 0.0; bb = []
            for j, d in enumerate(r):
                if b == 3: cur = end
                elif j == 0 and b == 0: cur = center
                else: cur = int(np.clip(cur + int(R.choice([-2, -1, -1, 1, 1, 2, 0])), center - 3, center + 4))
                bb.append((on, d, cur)); on += d
            out.append(bb)
        return out
    A = phrase(n5 + 2, n5 + 1); A2 = A[:3] + phrase(n5 + 2, n5)[3:]; B = phrase(n5 + 4, n5 + 2); A3 = A[:2] + phrase(n5 + 1, n5)[2:]
    song = A + A2 + B + A3; passes = [(S['mel'], 0, .62), (S['mel2'], 12 if S['mel2'] in PERC else 0, .5), (S['mel'], 0, .56)]
    intro = 2; total = intro + 16 * len(passes) + 3
    for b in range(total):
        t0 = b * bar
        if b < total - 2:                                                               # 가야금 반주: 1박 근음, 3박 5도, 가끔 옥타브
            ev.append((t0 + float(R.normal(0, .01)), S['acc'], to_m(0) - 12, .36, -.3, None))
            ev.append((t0 + 2 * beat + float(R.normal(0, .01)), S['acc'], to_m(n5 - 2 if n5 == 5 else 4) - 12, .24, -.25, None))
            if b % 4 == 3: ev.append((t0 + 2.5 * beat, S['acc'], to_m(n5) - 12, .18, -.2, None))
        elif b == total - 2:
            for k, ix in enumerate([0, 2, n5, n5 + 2]): ev.append((t0 + k * .35, S['acc'], to_m(ix) - 12, .3, -.3 + .15 * k, None))
        if S.get('drone') and b < total - 1: ev.append((t0, S['drone'], to_m(0) - 24, .35, 0.0, bar * 1.02))
    for p, (ins, up, vel) in enumerate(passes):
        for i, br in enumerate(song):
            t0 = (intro + p * 16 + i) * bar; arch = .84 + .24 * math.sin(math.pi * ((i % 4) + .5) / 4)
            for on, d, ix in br:
                t = t0 + on * beat + float(R.normal(0, .015)); m = to_m(ix) + up
                if ins in SUS: ev.append((t, ins, m, vel * arch, .15, d * beat * .97))
                else: ev.append((t, ins, m, vel * arch * (1.06 if on == 0 else .95), .15, None))
    return ev, total * bar, dict(tonic=tonic, bpm=round(bpm), meter=3, scale=sc_name, mode='folk', inst=S['mel'])


def compose_arp(seed, S):
    R = np.random.default_rng(seed); sc_name = str(R.choice(S['scales'])); SC = SCALES[sc_name]; n7 = len(SC) == 7
    tonic = _tonic(R); bpm = float(R.uniform(*S['bpm'])); beat = 60 / bpm; bar = 4 * beat
    P = [int(x) for x in PROGS[R.integers(len(PROGS))]]; Q = [int(x) for x in PROGS[R.integers(len(PROGS))]]
    prog = (P + Q) if n7 else [1, 1, 5, 5, 6, 6, 4, 4]
    arp, mel = S['arp'], S['mel']; ev = []; hum = lambda: float(R.normal(0, .01))
    patterns = [[0, 1, 2, 3, 4, 3, 2, 1], [0, 2, 1, 3, 2, 4, 3, 5], [0, 1, 2, 4, 3, 2, 1, 0], [0, 2, 4, 2, 1, 3, 5, 3]]
    pat = patterns[R.integers(len(patterns))]; bars_per_chord = 2; total = len(prog) * bars_per_chord * 2 + 3; melprev = 7
    def tone(ix): return tonic + SC[ix % len(SC)] + 12 * (ix // len(SC))
    for b in range(total):
        t0 = b * bar
        if b >= total - 3:
            if b == total - 3:
                for i, ix in enumerate(chord_idx(1) + [7]): ev.append((t0 + i * beat * .5 + hum(), arp, tone(ix) - 12, .3, -.3 + .2 * i, None))
                if S.get('pad'): ev.append((t0, S['pad'], tonic - 12, S['padv'] * .7, 0.0, bar * 2.6)); ev.append((t0, S['pad'], tonic - 5, S['padv'] * .5, 0.0, bar * 2.6))
            continue
        deg = prog[(b // bars_per_chord) % len(prog)]; ci = chord_idx(deg) if n7 else [deg - 1, deg + 1, deg + 3]
        tones = [c + o for c in ci for o in (0, len(SC), 2 * len(SC))]; tones.sort()
        for k, pi in enumerate(pat):
            ix = tones[pi % len(tones)]; v = .42 * (1.1 if k == 0 else (1.0 if k % 2 == 0 else .85)) * float(R.uniform(.9, 1.05))
            if R.random() < .08: continue                             # 가끔 한 음을 쉬어 사람이 치는 느낌
            ev.append((t0 + k * beat * .5 + hum(), arp, tone(ix) - 12, v, -.35 + .1 * (pi % 4), None))
        if S.get('pad'):
            for ix in ci: ev.append((t0, S['pad'], tonic - 12 + SC[ix % len(SC)] + 12 * (ix // len(SC)), S['padv'] * .8, 0.0, bar * 1.05))
        if b % bars_per_chord == 0 and R.random() < .6 and 2 <= b:   # 드문 선율: 화음 구성음 근처에서 2~3음
            cands = [c + len(SC) * o for c in ci for o in (1, 2) if 5 <= c + len(SC) * o <= 2 * len(SC) + 4]
            ix = min(cands, key=lambda c: abs(c - melprev) + R.uniform(0, 2)); melprev = ix
            nn = int(R.choice([1, 2, 3])); on = 0.0
            for j in range(nn):
                d = float(R.choice([1.5, 2, 3])) * beat
                if mel in SUS: ev.append((t0 + on + hum(), mel, tone(ix), .5, .25, d * .95))
                else: ev.append((t0 + on + hum(), mel, tone(ix), .5, .25, None))
                on += d; ix = int(np.clip(ix + R.choice([-2, -1, 1, 1, 2]), 4, 2 * len(SC) + 5))
    return ev, total * bar, dict(tonic=tonic, bpm=round(bpm), meter=4, scale=sc_name, mode='arp', inst=arp)


def compose_ambient(seed, S):
    R = np.random.default_rng(seed); sc_name = str(R.choice(S['scales'])); SC = SCALES[sc_name]; tonic = _tonic(R) - 12
    L = float(R.uniform(200, 300)); ev = []
    pool = [tonic + s + 12 * o for o in (0, 1, 2) for s in SC]
    for t in np.arange(0, L - 20, 22.0):                                  # 드론: 으뜸음 + 5도, 겹치며 이어짐
        ev.append((t, S['drone'], tonic - 12, .55, 0.0, 26.0)); ev.append((t + 11, S['drone'], tonic - 5, .4, 0.0, 26.0))
    for vi, ins in enumerate(S['voices']):
        per = float(R.uniform(7, 19)); t = float(R.uniform(2, per)); pn = float(R.uniform(-.6, .6))
        sub = [p for p in pool if (36 + 12 * (vi % 3)) <= p <= (60 + 12 * (vi % 3) + 7)] or pool
        prev = sub[len(sub) // 2]
        while t < L - 8:
            m = min(sub, key=lambda p: abs(p - prev) * .3 + R.uniform(0, 7)); prev = m
            v = float(R.uniform(.28, .55)) * (1 - .35 * (t / L) ** 3)
            if ins in SUS: ev.append((t, ins, m, v, pn, float(R.uniform(5, 12))))
            else: ev.append((t, ins, m, v, pn, None))
            t += per * float(R.uniform(.6, 1.5))
    return ev, L, dict(tonic=tonic + 12, bpm=0, meter=0, scale=sc_name, mode='ambient', inst=S['voices'][0])


def compose_drone(seed, S):
    R = np.random.default_rng(seed); sc_name = str(R.choice(S['scales'])); SC = SCALES[sc_name]; tonic = _tonic(R) - 12
    L = float(R.uniform(180, 260)); ev = []; mel = S['mel']
    for t in np.arange(0, L - 15, 24.0):
        ev.append((t, S['drone'], tonic - 12, .6, 0.0, 28.0)); ev.append((t + 12, S['drone'], tonic - 5, .42, 0.0, 28.0))
    for t in np.arange(6, L - 20, 32.0):                                 # 가끔 바뀌는 색채 화음
        ix = int(R.choice([0, 3, 4, 5] if len(SC) == 7 else [0, 2, 3]))
        for o, v in ((0, .5), (2, .35), (4, .3)): ev.append((t + R.uniform(0, 3), S['chord'], tonic + SC[(ix + o) % len(SC)] + 12 * ((ix + o) // len(SC)), v, float(R.uniform(-.4, .4)), 22.0))
    t = 8.0; ix = len(SC)
    while t < L - 14:
        n = int(R.choice([2, 3, 4, 5]))
        for j in range(n):
            d = float(R.uniform(1.6, 4.5)); m = tonic + 12 + SC[ix % len(SC)] + 12 * (ix // len(SC))
            if mel in SUS: ev.append((t, mel, m, float(R.uniform(.4, .6)), .1, d * .97))
            else: ev.append((t, mel, m, float(R.uniform(.4, .6)), .1, None)); d = max(d, 5.0)
            t += d + float(R.uniform(0, .4)); ix = int(np.clip(ix + R.choice([-2, -1, -1, 1, 1, 2, 3]), 2, 2 * len(SC) + 1))
        ix = int(np.clip(ix, len(SC) - 2, len(SC) + 4)) if R.random() < .4 else ix
        t += float(R.uniform(3, 8))
    return ev, L, dict(tonic=tonic + 12, bpm=0, meter=0, scale=sc_name, mode='drone', inst=mel)


DREAM_PROGS = [[4, 3, 6, 1], [1, 6, 4, 5], [4, 5, 3, 6], [2, 5, 1, 6], [6, 4, 1, 5], [4, 3, 2, 5], [1, 3, 4, 4], [6, 5, 4, 3]]


def compose_dream(seed, S):
    """드림웨이브·시티팝풍 수면곡: 7화음(가끔 9화음)을 2마디씩 길게 — 신스 패드 + 일렉피아노 반주 + 서브 베이스,
    두 번째 반복부터 드문드문 긴 선율. 북·드럼 없음 (잠들기 좋게)"""
    R = np.random.default_rng(seed); sc_name = str(R.choice(S['scales'])); SC = SCALES[sc_name]
    tonic = _tonic(R); bpm = float(R.uniform(*S['bpm'])); beat = 60 / bpm; bar = 4 * beat
    P = [int(x) for x in DREAM_PROGS[R.integers(len(DREAM_PROGS))]]
    reps = int(S.get('reps', 4)); intro = 2; body = len(P) * 2 * reps; total = intro + body + 3
    tone = lambda ix, base: base + SC[ix % 7] + 12 * (ix // 7)
    hum = lambda: float(R.normal(0, .012)); sw = .07 * beat; ev = []; mp = 9; pat = None
    PATS = [[(0, (0, 1, 2)), (1.5, (2, 3)), (3, (1, 3))], [(0, (1, 3)), (2.5, (2, 3))], [(.5, (0, 2, 3)), (2, (3,)), (3.5, (2,))], [(0, (0, 2)), (1, (3,)), (2.5, (1, 2))]]
    for b in range(intro + body):
        t0 = b * bar
        if b < intro: deg, first, rep = P[0], b == 0, -1
        else: deg = P[((b - intro) // 2) % len(P)]; first = (b - intro) % 2 == 0; rep = (b - intro) // (len(P) * 2)
        r = deg - 1; vo = [r, r + 2, r + 4, r + 6] + ([r + 8] if R.random() < .35 else [])
        if first:
            for j, ix in enumerate(vo): ev.append((t0, S['pad'], tone(ix, tonic - 12), S['padv'] * (1.0 if j == 0 else .8), float((j - 2) * .25), bar * 2 * .98))
            if b >= intro or b == 0: ev.append((t0, 'sub', tonic - 24 + SC[r % 7], S.get('subv', .6), 0.0, bar * 2 * .94))
        if b >= 1:
            pat = PATS[int(R.integers(len(PATS)))] if first or pat is None or R.random() < .5 else pat
            for on, ks in pat:
                for k in ks:
                    if k < len(vo): ev.append((t0 + on * beat + (sw if on % 1 else 0) + hum(), S['keys'], tone(vo[k], tonic), S.get('keysv', .3) * float(R.uniform(.78, 1.04)), (-.35, .35)[k % 2], None))
        if rep >= 1 and S.get('mel') and R.random() < S.get('meld', .6):
            for on in sorted(R.choice([0, 1, 1.5, 2, 2.5, 3], int(R.choice([1, 2, 2, 3])), replace=False)):
                cands = [x + 7 for x in vo] + [r + 8, r + 12]
                mp = min(cands, key=lambda c: abs(c - mp) + R.uniform(0, 2.2)); d = (4 - on) * beat * float(R.uniform(.55, 1.0))
                if S['mel'] in SUS: ev.append((t0 + on * beat + hum(), S['mel'], tone(mp, tonic), S.get('melv', .3), .2, d))
                else: ev.append((t0 + on * beat + hum(), S['mel'], tone(mp, tonic), S.get('melv', .35), .2, None))
    tE = (intro + body) * bar                                               # 끝: 으뜸 7화음을 길게
    for j, ix in enumerate((0, 2, 4, 6, 8)): ev.append((tE, S['pad'], tone(ix, tonic - 12), S['padv'] * .8, float((j - 2) * .25), bar * 2.6))
    ev.append((tE, 'sub', tonic - 24, S.get('subv', .6) * .8, 0.0, bar * 2.4))
    for j, ix in enumerate((0, 4, 6, 9)): ev.append((tE + j * .22, S['keys'], tone(ix, tonic), .24, (-.3, .3)[j % 2], None))
    return ev, total * bar, dict(tonic=tonic, bpm=round(bpm), meter=4, scale=sc_name, mode='dream', inst=S['keys'], insts=[S['keys'], S['pad'], S.get('mel'), 'sub'])


def tape(x, seed, depth=.0024, rate=.29, fl=.00016, frate=5.1, lp=6800):
    """카세트테이프 느낌: 느린 음정 울렁임(wow) + 미세한 떨림(flutter) + 살짝 둥근 고음 + 부드러운 포화"""
    n = x.shape[1]; t = np.arange(n) / SR; R = np.random.default_rng(seed)
    d = depth * SR * .5 * (1 + np.sin(2 * np.pi * rate * t + R.uniform(0, 6.28)) * (.7 + .3 * np.sin(2 * np.pi * .043 * t))) + fl * SR * np.sin(2 * np.pi * frate * t)
    idx = np.clip(np.arange(n) - d, 0, n - 1); base = np.arange(n)
    y = np.vstack([np.interp(idx, base, x[c]) for c in range(2)]).astype(np.float32)
    y = signal.sosfilt(bw('low', lp), y, axis=-1).astype(np.float32)
    return (np.tanh(y * 1.15) / 1.15).astype(np.float32)


COMPOSE = {'dream': compose_dream, 'song': compose_song, 'arp': compose_arp, 'ambient': compose_ambient, 'drone': compose_drone, 'nocturne': compose_nocturne, 'canon': compose_canon, 'folk': compose_folk}


def compose(seed, style):
    S = STYLE[style]; return COMPOSE[S['mode']](seed, S)


def render_piece(ev, length):
    n = int((length + 6) * SR); out = np.zeros((2, n), np.float32)
    for t, ins, m, v, p, dur in ev:
        i0 = max(0, int(t * SR))
        if ins in SUS: x = sus_note(ins, m, dur) * v
        else: x = pan(note(ins, m) * v, p)
        if ins in SUS and p: x = x * np.array([[1 - max(0, p) * .6], [1 + min(0, p) * .6]], np.float32)
        j = min(n, i0 + x.shape[1]); out[:, i0:j] += x[:, :j - i0]
    return out


def make_ir(seed=1, secs=3.2, t60=2.6):
    """인공 잔향 (작은 방~홀): 지수 감쇠 노이즈, 시간이 지날수록 고음이 먼저 사라짐"""
    R = np.random.default_rng(seed); n = int(secs * SR); t = np.arange(n) / SR
    ir = np.zeros((2, n), np.float32)
    for ch in range(2):
        x = R.normal(0, 1, n) * np.exp(-6.91 * t / t60)
        sos_lo = signal.butter(1, 2500, 'low', fs=SR, output='sos'); dark = signal.sosfilt(sos_lo, x)
        mix = np.clip(t / 1.2, 0, 1); x = x * (1 - mix) * .6 + dark * mix * 1.4
        pre = int(.022 * SR); x[:pre] = 0
        ir[ch] = x.astype(np.float32)
    ir /= np.sqrt((ir ** 2).sum(axis=1, keepdims=True)) + 1e-9
    return ir


def reverb(x, ir, wet=.32):
    y = np.vstack([signal.oaconvolve(x[c], ir[c])[:x.shape[1]] for c in range(2)]).astype(np.float32)
    return x * (1 - wet * .5) + y * wet * 1.6


# =====================================================================
# 3) 자연음 · ASMR (상태를 이어가며 블록 단위로 생성 → 이음새 없음)
# =====================================================================
class Filt:
    def __init__(s, sos, ch=2): s.sos = sos; s.zi = np.zeros((ch, sos.shape[0], 2))
    def __call__(s, x):
        y = np.empty_like(x)
        for c in range(x.shape[0]): y[c], s.zi[c] = signal.sosfilt(s.sos, x[c], zi=s.zi[c])
        return y


class LF:  # 1차/2차 IIR (b, a) 상태 유지
    def __init__(s, b, a, ch=2): s.b, s.a = b, a; s.zi = np.zeros((ch, max(len(a), len(b)) - 1))
    def __call__(s, x):
        y = np.empty_like(x)
        for c in range(x.shape[0]): y[c], s.zi[c] = signal.lfilter(s.b, s.a, x[c], zi=s.zi[c])
        return y


def bw(kind, f, order=2): return signal.butter(order, f, kind, fs=SR, output='sos')


def resonator(f, decay):
    r = math.exp(-1 / (decay * SR)); w = 2 * math.pi * f / SR
    return [1 - r], [1, -2 * r * math.cos(w), r * r]


class Events:
    """블록 경계를 넘어가는 짧은 소리(물방울·풍경·천둥·시계)를 겹쳐 쓰는 버퍼"""
    def __init__(s, maxlen): s.tail = np.zeros((2, int(maxlen * SR)), np.float32)
    def begin(s, n):
        s.buf = np.zeros((2, n + s.tail.shape[1]), np.float32); s.buf[:, :s.tail.shape[1]] += s.tail; s.n = n
    def add(s, i, x):            # i: 블록 안 샘플 위치, x: (2, k)
        if i < 0 or i >= s.n: return
        k = min(x.shape[1], s.buf.shape[1] - i); s.buf[:, i:i + k] += x[:, :k]
    def end(s):
        out = s.buf[:, :s.n]; s.tail = s.buf[:, s.n:].copy(); return out


# CAL: 0dB = 음악과 같은 크기(약 -20dBFS)가 되도록 하는 보정값 (dB)
# CAL: 0dB = 음악과 같은 크기(약 -20dBFS)가 되도록 하는 보정값 (dB)
CAL = {'rain': -4.2, 'waves': 1.3, 'pink': 8.7, 'brown': -8.8, 'white': 11.6, 'heart': -12.7, 'fire': -10.9,
       'drips': -9.5, 'thunder': -10.0, 'stream': -20.5, 'wind': -13.5, 'chimes': 3.0, 'crickets': 29.5, 'clock': -3.0, 'purr': -2.7,
       'leaves': 5.5, 'tent': 3.6, 'underwater': -29.7, 'frogs': -4.0, 'owl': -2.0, 'bamboo': -7.0, 'pages': -11.0,
       'vinyl': -7.9, 'city': -18.8, 'train': -22.6}
LAYER_KO = {'rain': '빗소리', 'drips': '처마 빗방울', 'thunder': '먼 천둥', 'waves': '파도', 'stream': '시냇물', 'wind': '바람', 'chimes': '풍경',
            'crickets': '귀뚜라미', 'fire': '장작', 'clock': '괘종시계', 'purr': '고양이 골골', 'pink': '핑크 노이즈', 'brown': '브라운 노이즈',
            'white': '백색소음', 'heart': '심장 박동', 'leaves': '나뭇잎 빗소리', 'tent': '텐트 빗소리', 'underwater': '깊은 물속', 'frogs': '개구리',
            'owl': '부엉이', 'bamboo': '대나무 부딪힘', 'pages': '책장 넘김', 'vinyl': 'LP 잡음', 'city': '먼 도시 소리', 'train': '기차 소리'}
PINK_B, PINK_A = [0.049922035, -0.095993537, 0.050612699, -0.004408786], [1, -2.494956002, 2.017265875, -0.522189400]
PENTA_CHIME = [0, 2, 4, 7, 9, 12, 14, 16]

# 장면마다 함께 들리는 자연음 (dB). 화면이 바뀌면 소리도 같은 시점에 서서히 바뀝니다.
SCENE_AMB = {
    'night': {'wind': -24, 'crickets': -24}, 'rainwin': {'rain': -7}, 'storm': {'rain': -5, 'thunder': -5}, 'eaves': {'rain': -10, 'drips': -4},
    'sea': {'waves': -6}, 'firefly': {'crickets': -15, 'frogs': -24}, 'snow': {'wind': -18}, 'aurora': {'wind': -21}, 'pastel': {'pink': -24},
    'warm': {'fire': -14}, 'candle': {'fire': -19}, 'nursery': {'pink': -24, 'clock': -26}, 'stream': {'stream': -7, 'crickets': -24},
    'study': {'clock': -14, 'pages': -8, 'rain': -22}, 'bamboo': {'wind': -13, 'bamboo': -7, 'leaves': -18}, 'pond': {'leaves': -9, 'frogs': -15, 'drips': -14},
    'camp': {'fire': -10, 'crickets': -21, 'owl': -14}, 'underwater': {'underwater': -6}, 'meadow': {'wind': -16, 'crickets': -18, 'owl': -17},
    'snowwin': {'wind': -20, 'fire': -21, 'clock': -28}, 'tentrain': {'tent': -5, 'thunder': -16},
    'px_train': {'train': -9, 'city': -26}, 'px_city': {'city': -15, 'wind': -24}, 'px_room': {'rain': -12, 'vinyl': -18},
    'px_clouds': {'wind': -22, 'chimes': -22}, 'px_pool': {'drips': -15, 'underwater': -22}, 'px_street': {'rain': -8, 'city': -21},
    'cp_room': {'city': -21, 'vinyl': -15}, 'cp_drive': {'brown': -14, 'wind': -24, 'city': -24}, 'cp_boulevard': {'waves': -11, 'wind': -24},
}


class SceneMix:
    """영상 장면 일정과 똑같이 장면별 자연음 크기(선형 배수)를 계산. 영상: 장면 seg초 + 끝 xf초 동안 다음 장면으로 전환"""
    def __init__(s, scenes, seg, xf, db=0.0):
        s.sc, s.seg, s.xf = list(scenes), float(seg), float(xf)
        s.keys = sorted({k for nm in s.sc for k in SCENE_AMB.get(nm, {})})
        s.tab = np.array([[10 ** ((SCENE_AMB.get(nm, {}).get(k, -200) + db) / 20) for k in s.keys] for nm in s.sc], np.float32)   # (장면, 레이어)
    def __call__(s, t):
        n = len(s.sc); tl = t % (n * s.seg); k = (tl // s.seg).astype(int) % n; w = tl - k * s.seg
        u = np.clip((w - (s.seg - s.xf)) / s.xf, 0, 1); u = u * u * (3 - 2 * u)
        a = s.tab[k] * (1 - u)[:, None] + s.tab[(k + 1) % n] * u[:, None]
        return {key: a[:, i] for i, key in enumerate(s.keys)}


def _drip(R, f0=900, up=1.6, dur=.05):
    """물방울 '똑': 짧게 올라가는 사인 (실제 물방울은 기포가 커지며 음이 올라감)"""
    n = int(dur * SR); t = np.arange(n) / SR; f = f0 * (1 + (up - 1) * np.clip(t / dur, 0, 1) ** .6)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (dur * .35)); y[:16] *= np.linspace(0, 1, 16)
    return y.astype(np.float32)


def _frog(R):
    """개구리 '개굴': 짧은 펄스 2~3개, 펄스마다 거친 목울림"""
    f = float(R.uniform(450, 1100)); am = float(R.uniform(35, 70)); k = int(R.integers(2, 4)); L = int(.11 * SR); gap = int(R.uniform(.08, .14) * SR)
    y = np.zeros(k * (L + gap), np.float32); t = np.arange(L) / SR
    for j in range(k):
        env = np.sin(np.pi * t / (L / SR)) ** 1.5; tone = (np.sin(2 * np.pi * f * t) + .4 * np.sin(2 * np.pi * f * 2 * t)) * (.55 + .45 * np.sign(np.sin(2 * np.pi * am * t)))
        y[j * (L + gap): j * (L + gap) + L] = (tone * env * (1 - .15 * j)).astype(np.float32)
    return signal.sosfilt(bw('low', 2600), y).astype(np.float32)


def _owl(R):
    """부엉이 '부엉~ 부엉': 낮고 둥근 소리 두 번"""
    f = float(R.uniform(330, 420)); out = []
    for d, fr in ((.42, 1.0), (.22, .1), (.55, .97)):
        n = int(d * SR); t = np.arange(n) / SR
        if fr < .5: out.append(np.zeros(n, np.float32)); continue
        env = np.sin(np.pi * t / d) ** 2; ff = f * fr * (1 + .03 * np.sin(np.pi * t / d))
        out.append((np.sin(2 * np.pi * np.cumsum(ff) / SR) * env + .08 * np.sin(4 * np.pi * np.cumsum(ff) / SR) * env).astype(np.float32))
    return np.concatenate(out)


def _clack(R):
    """대나무끼리 '딱': 속이 빈 나무 공명"""
    f = float(R.uniform(500, 1100)); n = int(.18 * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * f * t) * np.exp(-t / .035) + .5 * np.sin(2 * np.pi * f * 2.7 * t) * np.exp(-t / .015) + R.standard_normal(n) * np.exp(-t / .002) * .3
    return y.astype(np.float32)


def _page(R):
    """책장 넘기는 '사락'"""
    d = float(R.uniform(.5, .9)); n = int(d * SR); t = np.arange(n) / SR
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 1.5 * (1 + .6 * np.sin(2 * np.pi * 9 * t) ** 2)
    x = signal.sosfilt(bw('band', [1800, 7000]), R.standard_normal(n)) * env
    x[-int(.06 * SR):] += signal.sosfilt(bw('band', [300, 1500]), R.standard_normal(int(.06 * SR))) * np.exp(-np.arange(int(.06 * SR)) / SR / .015) * 1.5   # 종이가 내려앉는 '툭'
    return x.astype(np.float32)


class Ambience:
    """layers: {이름: dB} (항상 들림) + scene: SceneMix (장면 따라 바뀜)
    rain drips thunder waves stream wind chimes crickets fire clock purr pink brown white heart leaves tent underwater frogs owl bamboo pages"""
    def __init__(s, layers, seed=0, scene=None):
        s.L = dict(layers or {}); s.scene = scene; s.R = np.random.default_rng(seed); s.t0 = 0; R = s.R
        s.on = set(s.L) | set(scene.keys if scene else [])
        s.pink = LF(PINK_B, PINK_A); s.brown = LF([1], [1, -.996]); s.dc = Filt(bw('high', 25, 1))
        s.rain_bp = Filt(bw('band', [380, 8500])); s.rain_lo = Filt(bw('low', 260))
        s.drops = [(LF(*resonator(f, .012), ch=1), f) for f in R.uniform(1700, 4600, 4)]
        s.wave_lp = Filt(bw('low', 1300)); s.wave_hs = Filt(bw('band', [1800, 7000]))
        s.white_lp = Filt(bw('low', 7500)); s.heart = LF(*resonator(52, .07), ch=1); s.heart_lp = Filt(bw('low', 420))
        s.fire_lo = Filt(bw('low', 320)); s.crk = LF(*resonator(2600, .004), ch=1); s.crk_hp = Filt(bw('high', 900), ch=1)
        s.ev = Events(20.0)
        s.st_bp = Filt(bw('band', [500, 3200])); s.st_lo = Filt(bw('band', [90, 420]))
        s.bubbles = [(LF(*resonator(f, .006), ch=1), f) for f in R.uniform(700, 2400, 6)]
        s.wind_f = float(R.uniform(250, 500)); s.wind_bp = Filt(bw('band', [s.wind_f * .6, s.wind_f * 1.6], 1)); s.wind_lo = Filt(bw('low', 900))
        s.chime_root = 72 + int(R.choice([0, 2, 5, 7])); s.chime_next = 3.0
        s.crick = [(float(R.uniform(3900, 5200)), float(R.uniform(22, 34)), float(R.uniform(0, 6.3)), float(R.uniform(-.8, .8)), float(R.uniform(.5, 1.0)), float(R.uniform(2.5, 4.5))) for _ in range(5)]
        s.crick_lp = Filt(bw('low', 5600)); s.thunder_next = float(R.uniform(25, 60))
        s.clock_i = 0; s.purr_lp = Filt(bw('low', 320)); s.purr_bp = Filt(bw('band', [60, 240]))
        s.drip_cache = [_drip(R, float(R.uniform(650, 1500)), float(R.uniform(1.3, 2.0)), float(R.uniform(.035, .07))) for _ in range(12)]
        # v3
        s.leaf_bp = Filt(bw('band', [1400, 6500])); s.leaf_res = [(LF(*resonator(f, .004), ch=1), f) for f in R.uniform(2500, 6000, 4)]
        s.leaf_drip = [_drip(R, float(R.uniform(400, 800)), float(R.uniform(1.2, 1.5)), float(R.uniform(.05, .09))) for _ in range(8)]
        s.tent_res = [(LF(*resonator(f, .02), ch=1), f) for f in R.uniform(160, 420, 5)]; s.tent_bp = Filt(bw('band', [200, 1600]))
        s.uw_lp = Filt(bw('low', 280)); s.uw_bp = Filt(bw('band', [80, 500])); s.uw_next = float(R.uniform(3, 9))
        s.frogs = [(float(R.uniform(1.2, 4.5)), float(R.uniform(0, 4)), float(R.uniform(-.8, .8)), _frog(R), float(R.uniform(.4, 1.0))) for _ in range(4)]
        s.frog_next = [f[1] for f in s.frogs]
        s.owl_next = float(R.uniform(20, 50)); s.owl_snd = _owl(R)
        s.bam_next = float(R.uniform(2, 6)); s.page_next = float(R.uniform(15, 40))
        # v4 드림코어: LP 잡음 · 먼 도시 · 기차
        s.vin_hiss = Filt(bw('band', [1800, 9000])); s.vin_click = Filt(bw('band', [700, 5000]), ch=1); s.vin_lo = Filt(bw('low', 120))
        s.city_lo = Filt(bw('band', [40, 260])); s.city_mid = Filt(bw('band', [250, 900])); s.car_next = float(R.uniform(3, 12))
        s.train_lo = Filt(bw('band', [30, 160])); s.train_mid = Filt(bw('band', [180, 700])); s.train_next = 0.4; s.train_k = 0
        s.thump = [Filt(bw('low', float(f)), ch=1) for f in (180, 240)]

    def noise(s, n, corr=.55):  # 좌우가 약간 다른 자연스러운 스테레오 노이즈
        a = s.R.standard_normal(n).astype(np.float32); b = s.R.standard_normal((2, n)).astype(np.float32)
        return corr * a + math.sqrt(1 - corr * corr) * b

    def __call__(s, n):
        t = (s.t0 + np.arange(n)) / SR; T0 = s.t0 / SR; T1 = T0 + n / SR; out = np.zeros((2, n), np.float32); R = s.R
        env = s.scene(t) if s.scene else {}
        G = {}
        for k in s.on:
            base = 10 ** (s.L[k] / 20) if k in s.L else 0.0
            G[k] = ((base + env[k]) if k in env else np.float32(base)) * 10 ** (CAL[k] / 20)
        g = lambda k: G[k]
        gi = lambda k, i: float(G[k][min(max(i, 0), n - 1)]) if np.ndim(G[k]) else float(G[k])   # 순간 소리(이벤트)용
        live = lambda k: k in G and (np.max(G[k]) > 1e-5)
        s.ev.begin(n)
        pk = s.pink(s.noise(n)) * 3.2
        br = s.dc(s.brown(s.noise(n, .7)) * .055)
        if live('pink'): out += pk * .18 * g('pink')
        if live('brown'): out += br * .9 * g('brown')
        if live('white'): out += s.white_lp(s.noise(n, .3)) * .06 * g('white')
        if live('rain'):
            m = 1 + .14 * np.sin(2 * np.pi * t / 41) + .08 * np.sin(2 * np.pi * t / 13.7)
            base = s.rain_bp(pk) * .55 * m; dr = np.zeros((2, n), np.float32)
            for i, (rf, f) in enumerate(s.drops):
                imp = (R.random(n) < 9 / SR) * R.exponential(1, n) * R.choice([-1, 1], n)
                d = rf(imp[None].astype(np.float32))[0] * .5; dr[i % 2] += d; dr[1 - i % 2] += d * .45
            out += (base + dr * m + s.rain_lo(br) * .5) * g('rain')
        if live('drips'):   # 처마·지붕에서 떨어지는 물방울
            rate = (2.2 + 1.5 * np.sin(2 * np.pi * T0 / 37)) / SR
            for i in np.where(R.random(n) < rate)[0]:
                d = s.drip_cache[R.integers(len(s.drip_cache))] * float(R.uniform(.5, 1.0)) * .9
                s.ev.add(int(i), pan(d, float(R.uniform(-.7, .7))) * gi('drips', i))
        if 'thunder' in G:  # 먼 천둥: 1~3분에 한 번
            while s.thunder_next < T1:
                i0 = int((s.thunder_next - T0) * SR); a = gi('thunder', i0)
                if a > 1e-5:
                    dur = float(R.uniform(5, 12)); k = int(dur * SR); tt = np.arange(k) / SR
                    e = (np.exp(-tt / (dur * .3)) * (1 - np.exp(-tt / .4))) * (1 + .5 * np.sin(2 * np.pi * tt * R.uniform(.3, 1.2)) * np.exp(-tt / 3))
                    x = Filt(bw('low', float(R.uniform(70, 130))))(R.standard_normal((2, k)).astype(np.float32) * e.astype(np.float32)) * 9.0 * float(R.uniform(.5, 1.0))
                    s.ev.add(i0, x * a)
                s.thunder_next += float(R.uniform(50, 170))
        if live('waves'):
            def wenv(off):
                ph = 2 * np.pi / 9.5 * (t - .15 * 71 / (2 * np.pi) * np.cos(2 * np.pi * t / 71) - .1 * 23 / (2 * np.pi) * np.cos(2 * np.pi * t / 23)) + off
                sw = .5 - .5 * np.cos(ph); return (.18 + .82 * sw ** 1.6).astype(np.float32)
            e = np.vstack([wenv(0), wenv(.35)]); wash = np.vstack([wenv(-.9), wenv(-.6)]) ** 2.2
            out += (s.wave_lp(pk) * .9 * e + s.wave_hs(pk) * .35 * wash) * g('waves')
        if live('stream'):
            m = 1 + .12 * np.sin(2 * np.pi * t / 5.3) + .08 * np.sin(2 * np.pi * t / 1.7 + 1); bub = np.zeros((2, n), np.float32)
            for i, (rf, f) in enumerate(s.bubbles):
                imp = (R.random(n) < 14 / SR) * R.exponential(1, n) * R.choice([-1, 1], n)
                d = rf(imp[None].astype(np.float32))[0] * .45; bub[i % 2] += d; bub[1 - i % 2] += d * .4
            out += (s.st_bp(pk) * .5 * m + s.st_lo(br) * 6.0 * (1 + .3 * np.sin(2 * np.pi * t / 3.1)) + bub) * g('stream')
        if live('wind'):
            gust = (.45 + .55 * (.5 + .5 * np.sin(2 * np.pi * t / 23 + 1.3)) ** 2 * (.6 + .4 * np.sin(2 * np.pi * t / 7.1)))
            out += (s.wind_bp(pk) * .8 * gust + s.wind_lo(br) * 2.5 * gust) * g('wind')
        if 'chimes' in G:
            while s.chime_next < T1:
                tt = s.chime_next; a = gi('chimes', int((tt - T0) * SR))
                if a > 1e-5:
                    for j in range(int(R.choice([1, 2, 2, 3, 4, 5]))):
                        x = note('glass', s.chime_root + int(R.choice(PENTA_CHIME))) * float(R.uniform(.25, .6))
                        s.ev.add(int((tt - T0) * SR), pan(x, float(R.uniform(-.8, .8))) * a); tt += float(R.uniform(.08, .6))
                s.chime_next += float(R.uniform(2.5, 14))
        if live('crickets'):
            cr = np.zeros((2, n), np.float32)
            for f, rate, ph, pn, lv, bp in s.crick:
                chirp = np.clip((np.sin(2 * np.pi * rate * t + ph) - .3) * 6, 0, 1).astype(np.float32)
                burst = np.clip((np.sin(2 * np.pi * t / bp + ph) + .2) * 3, 0, 1).astype(np.float32)
                tone = np.sin(2 * np.pi * f * t) * (.5 + .5 * np.sin(2 * np.pi * f * .0092 * t)) * chirp * burst * lv
                a = (pn + 1) * math.pi / 4; cr[0] += tone * math.cos(a); cr[1] += tone * math.sin(a)
            out += s.crick_lp(cr) * .012 * g('crickets')
        if live('fire'):
            roar = s.fire_lo(br) * (1.3 + .25 * np.sin(2 * np.pi * t / 7.3) + .15 * np.sin(2 * np.pi * t / 2.9))
            burst = (R.random(n) < 5 / SR) * R.exponential(1, n) ** 1.5 + (R.random(n) < 40 / SR) * R.exponential(.15, n)
            ck = s.crk_hp(s.crk(burst[None].astype(np.float32)))[0] * 1.4
            out += (roar + np.vstack([ck, ck * .7])) * g('fire')
        if 'clock' in G:
            while s.clock_i * 1.0 < T1:
                i0 = int((s.clock_i - T0) * SR); a = gi('clock', i0)
                if a > 1e-5:
                    f = 2300 if s.clock_i % 2 == 0 else 1900; k = int(.06 * SR); tt = np.arange(k) / SR
                    x = (np.sin(2 * np.pi * f * tt) * .6 + np.sin(2 * np.pi * f * 2.3 * tt) * .25 + R.standard_normal(k) * .15 * np.exp(-tt / .003)) * np.exp(-tt / .012)
                    s.ev.add(i0, pan(x.astype(np.float32) * .55, -.3 if s.clock_i % 2 == 0 else -.2) * a)
                s.clock_i += 1
        if live('purr'):
            breath = .5 + .5 * np.sin(2 * np.pi * t / 2.6); inh = (np.sin(2 * np.pi * t / 2.6) > 0)
            pulse = np.clip(np.sin(2 * np.pi * (25 + 3 * inh) * t), 0, 1) ** 3
            out += s.purr_lp(s.purr_bp(s.noise(n, .9)) * pulse * (.35 + .65 * breath) * 4.0) * g('purr')
        if live('heart'):
            per = 60 / 66; ph = (t % per); imp = np.zeros(n, np.float32)
            idx1 = np.where(np.diff(np.floor(t / per)) > 0)[0]
            imp[idx1] = 1.0; idx2 = np.clip(idx1 + int(.3 * SR), 0, n - 1); imp[idx2] += .62
            hb = s.heart(imp[None])[0] * 14; whoosh = s.heart_lp(br) * (1.6 + .35 * np.exp(-ph / .25))
            out += (whoosh + np.vstack([hb, hb])) * g('heart')
        # ---- v3 ASMR
        if live('leaves'):   # 나뭇잎에 떨어지는 가는 비: 촘촘한 '토독토독' + 잎에서 떨어지는 큰 물방울
            m = 1 + .2 * np.sin(2 * np.pi * t / 17) + .1 * np.sin(2 * np.pi * t / 5.3)
            pat = np.zeros((2, n), np.float32)
            for i, (rf, f) in enumerate(s.leaf_res):
                imp = (R.random(n) < 70 / SR) * R.exponential(1, n) * R.choice([-1, 1], n)
                d = rf(imp[None].astype(np.float32))[0] * .35; pat[i % 2] += d; pat[1 - i % 2] += d * .5
            out += (s.leaf_bp(pk) * .22 * m + pat * m) * g('leaves')
            for i in np.where(R.random(n) < 1.4 / SR)[0]:
                s.ev.add(int(i), pan(s.leaf_drip[R.integers(len(s.leaf_drip))] * float(R.uniform(.3, .7)), float(R.uniform(-.8, .8))) * gi('leaves', i))
        if live('tent'):     # 텐트 천에 떨어지는 비: 낮고 둥근 '투둑투둑'
            m = 1 + .25 * np.sin(2 * np.pi * t / 29) + .1 * np.sin(2 * np.pi * t / 7.7)
            th = np.zeros((2, n), np.float32)
            for i, (rf, f) in enumerate(s.tent_res):
                imp = (R.random(n) < 45 / SR) * R.exponential(1, n) * R.choice([-1, 1], n)
                d = rf(imp[None].astype(np.float32))[0] * 1.6; th[i % 2] += d; th[1 - i % 2] += d * .6
            out += (th * m + s.tent_bp(pk) * .25 * m) * g('tent')
        if live('underwater'):  # 깊은 물속: 웅웅대는 저음 + 가끔 올라가는 기포
            sw = 1 + .35 * np.sin(2 * np.pi * t / 11) + .2 * np.sin(2 * np.pi * t / 4.3)
            out += (s.uw_lp(br) * 7.0 * sw + s.uw_bp(pk) * .12 * sw) * g('underwater')
        if 'underwater' in G:
            while s.uw_next < T1:
                i0 = int((s.uw_next - T0) * SR); a = gi('underwater', i0)
                if a > 1e-5:
                    for j in range(int(R.integers(3, 9))):
                        d = _drip(R, float(R.uniform(300, 700)), float(R.uniform(1.4, 2.2)), float(R.uniform(.05, .1))) * .7
                        s.ev.add(i0 + int(j * R.uniform(.05, .14) * SR), pan(d, float(R.uniform(-.5, .5))) * a)
                s.uw_next += float(R.uniform(4, 14))
        if 'frogs' in G:     # 개구리: 몇 마리가 각자 박자로 개굴개굴, 가끔 다 같이 쉼
            for j, (per, ph, pn, snd, lv) in enumerate(s.frogs):
                while s.frog_next[j] < T1:
                    tt = s.frog_next[j]; i0 = int((tt - T0) * SR); a = gi('frogs', i0)
                    rest = math.sin(2 * math.pi * tt / 47 + j) > -.4
                    if a > 1e-5 and rest: s.ev.add(i0, pan(snd * lv * .5 * float(R.uniform(.7, 1.0)), pn) * a)
                    s.frog_next[j] += per * float(R.uniform(.8, 1.3))
        if 'owl' in G:
            while s.owl_next < T1:
                i0 = int((s.owl_next - T0) * SR); a = gi('owl', i0)
                if a > 1e-5: s.ev.add(i0, pan(s.owl_snd * .5, float(R.uniform(-.9, .9))) * a)
                s.owl_next += float(R.uniform(35, 110))
        if 'bamboo' in G:    # 바람이 불면 대나무가 서로 부딪혀 '딱 딱'
            while s.bam_next < T1:
                i0 = int((s.bam_next - T0) * SR); a = gi('bamboo', i0)
                if a > 1e-5:
                    tt = 0.0
                    for j in range(int(R.integers(1, 5))):
                        s.ev.add(i0 + int(tt * SR), pan(_clack(R) * float(R.uniform(.2, .5)), float(R.uniform(-.8, .8))) * a); tt += float(R.uniform(.15, .7))
                s.bam_next += float(R.uniform(2.5, 11))
        if 'pages' in G:
            while s.page_next < T1:
                i0 = int((s.page_next - T0) * SR); a = gi('pages', i0)
                if a > 1e-5: s.ev.add(i0, pan(_page(R) * .5, float(R.uniform(-.3, .3))) * a)
                s.page_next += float(R.uniform(35, 120))
        if live('vinyl'):    # LP판: 아주 작은 쉬- 소리 + 톡톡 튀는 먼지 소리 + 느린 회전 웅웅
            hiss = s.vin_hiss(s.noise(n, .85)) * .035 * (1 + .15 * np.sin(2 * np.pi * t / 1.8))
            imp = (R.random(n) < 9 / SR) * R.exponential(1, n) ** 2 * R.choice([-1, 1], n) + (R.random(n) < .3 / SR) * R.exponential(3, n) * R.choice([-1, 1], n)
            c = s.vin_click(imp[None].astype(np.float32))[0] * .55; rum = s.vin_lo(br) * .8 * (1 + .3 * np.sin(2 * np.pi * .555 * t))
            out += (hiss + np.vstack([c, c * .75]) + rum) * g('vinyl')
        if live('city'):     # 먼 도시: 낮은 웅웅거림 + 가끔 멀리 지나가는 차
            out += (s.city_lo(br) * 3.2 * (1 + .18 * np.sin(2 * np.pi * t / 29)) + s.city_mid(pk) * .07 * (1 + .25 * np.sin(2 * np.pi * t / 11))) * g('city')
        if 'city' in G:
            while s.car_next < T1:
                i0 = int((s.car_next - T0) * SR); a_ = gi('city', i0)
                if a_ > 1e-5:
                    d = float(R.uniform(4, 8)); k = int(d * SR); tt = np.arange(k) / SR; e = np.sin(np.pi * tt / d) ** 3
                    x = signal.sosfilt(bw('band', [float(R.uniform(250, 400)), float(R.uniform(1400, 2600))]), R.standard_normal(k)).astype(np.float32) * e.astype(np.float32) * .35
                    ang = (np.linspace(0, 1, k) if R.random() < .5 else np.linspace(1, 0, k)) * np.pi / 2
                    s.ev.add(i0, np.vstack([x * np.cos(ang), x * np.sin(ang)]).astype(np.float32) * a_)
                s.car_next += float(R.uniform(6, 22))
        if live('train'):    # 달리는 기차: 낮은 진동 + 바퀴 소리
            out += (s.train_lo(br) * 5.0 * (1 + .12 * np.sin(2 * np.pi * .9 * t)) + s.train_mid(pk) * .09 * (1 + .2 * np.sin(2 * np.pi * t / 7))) * g('train')
        if 'train' in G:     # 레일 이음새: '덜-컹' 두 번씩, 일정한 간격
            while s.train_next < T1:
                i0 = int((s.train_next - T0) * SR); a_ = gi('train', i0)
                if a_ > 1e-5:
                    for j, off in enumerate((0.0, .14)):
                        k = int(.12 * SR); tt = np.arange(k) / SR
                        x = (np.sin(2 * np.pi * 62 * tt) * .9 + R.standard_normal(k) * .5) * np.exp(-tt / .035)
                        x = s.thump[j](x[None].astype(np.float32))[0] * (.9 if j == 0 else .75) * (1.15 if s.train_k % 4 == 0 else 1.0)
                        s.ev.add(i0 + int(off * SR), pan(x.astype(np.float32), -.15 + .3 * j) * a_)
                s.train_k += 1; s.train_next += 1.08 + float(R.uniform(-.015, .015))
        out += s.ev.end(); s.t0 += n
        return out


# =====================================================================
# 4) 트랙 만들기 (스트리밍)
# =====================================================================
def make_track(path, minutes, style, layers, seed, music_db=0.0, log=print, scenes=None, seg=90.0, xf=8.0, scene_db=0.0):
    """style: None(자연음만) / 스타일 이름 / 스타일 이름 목록(곡마다 번갈아).
    scenes: 영상 장면 목록 — 주면 장면에 맞는 자연음이 화면 전환과 같은 시점에 바뀜 (scene_db=None 이면 끔). 반환: (RMS dBFS, 곡 정보 목록)"""
    N = int(minutes * 60 * SR)
    sm = SceneMix(scenes, seg, xf, scene_db) if scenes and scene_db is not None else None
    amb = Ambience(layers, seed, sm) if (layers or sm) else None
    ir = make_ir(seed, secs=3.6, t60=3.0); wf = wave.open(str(path), 'wb'); wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR)
    fin, fout = int(10 * SR), int(50 * SR); written = 0; ss = 0.0; songs = []
    mg = 10 ** (music_db / 20); styles = [style] if isinstance(style, str) else list(style or [])
    soft = Filt(signal.butter(1, 11000, 'low', fs=SR, output='sos'))        # 귀에 거슬리는 초고음을 아주 살짝 둥글게

    def flush(x):
        nonlocal written, ss
        x = x[:, :max(0, N - written)]
        if not x.shape[1]: return
        if amb is not None: x = x + amb(x.shape[1])
        i = written + np.arange(x.shape[1])
        f = np.minimum(1, np.minimum(i / fin, (N - i) / fout)).clip(0, 1).astype(np.float32)
        x = np.tanh(soft(x) * f * .9) / .9                      # 부드러운 리미터
        ss += float((x.astype(np.float64) ** 2).sum())
        wf.writeframes((np.clip(x.T, -1, 1) * 32000).astype('<i2').tobytes()); written += x.shape[1]

    if not styles:
        B = 30 * SR
        while written < N: flush(np.zeros((2, min(B, N - written)), np.float32))
    else:
        pend = np.zeros((2, 0), np.float32); out_pos = 0; cur = int(4 * SR); k = 0
        R = np.random.default_rng(seed); order = list(styles)
        while cur < N:
            st = order[k % len(order)] if len(order) > 1 else order[0]
            if len(order) > 1 and k % len(order) == 0 and k: R.shuffle(order)
            S = STYLE[st]; ev, L, info = compose(int(seed * 1000 + k), st); k += 1; info['style'] = st
            x = reverb(render_piece(ev, L), ir, S.get('wet', .32)) * .55 * mg * 10 ** (S.get('gain', 0) / 20)
            if S.get('tape'): x = tape(x, int(seed * 7 + k))
            x = widen(x, S.get('width', 1.25))
            need = cur + x.shape[1] - out_pos
            if pend.shape[1] < need: pend = np.hstack([pend, np.zeros((2, need - pend.shape[1]), np.float32)])
            pend[:, cur - out_pos: cur - out_pos + x.shape[1]] += x
            songs.append(info); gap = R.uniform(-8, -2) if S['mode'] in ('ambient', 'drone') else R.uniform(3, 6)
            nxt = cur + int((L + gap) * SR)
            cut = min(nxt, N) - out_pos; flush(pend[:, :cut]); pend = pend[:, cut:]; out_pos += cut; cur = nxt
            if k % 4 == 0: log(f'  작곡·연주 {k}곡 · {out_pos / SR / 60:.1f}/{minutes}분')
        while written < N:
            m = min(30 * SR, N - written); blk = pend[:, :m]
            if blk.shape[1] < m: blk = np.hstack([blk, np.zeros((2, m - blk.shape[1]), np.float32)])
            pend = pend[:, m:]; flush(blk)
    wf.close()
    rms = 10 * math.log10(ss / (2 * N) + 1e-12)
    return rms, songs


def widen(x, w=1.25):
    """스테레오를 살짝 넓혀 소리가 귀를 감싸는 느낌 (가운데·양옆 비율 조절)"""
    m = (x[0] + x[1]) * .5; sd = (x[0] - x[1]) * .5 * w; return np.vstack([m + sd, m - sd])
