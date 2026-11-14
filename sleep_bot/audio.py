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
}
_NOTE = {}


def note(ins, m):
    k = (ins, m)
    if k in _NOTE: return _NOTE[k]
    P = INSTR[ins]; f0 = midi_hz(m); n = int(P['dur'] * SR); t = np.arange(n, dtype=np.float32) / SR
    y = np.zeros(n, np.float32); rng = _rng(ins, m)
    for r, a, tau in P['p']:
        f = f0 * r * (1 + P.get('inh', 0) * r * r)
        if f > SR * .42: continue
        te = tau * (523.0 / f0) ** P['bright']          # 높은 음일수록 조금 빨리 사라짐 (실제 악기처럼)
        y += (a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) * np.exp(-t / te)).astype(np.float32)
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
        cents = 0 if voices == 1 else [-6, 6, 0, 3][vi]; ch = vi % 2 if voices > 1 else None
        f = f0 * 2 ** (cents / 1200); drift = 1 + .004 * np.exp(-t / .12) * (1 if ins == 'flute' else 0)
        ph = 2 * np.pi * f * np.cumsum(vib * drift) / SR
        y = np.zeros(n, np.float32)
        for h in range(1, 14):
            fh = f * h
            if fh > SR * .42: break
            if 'formant' in P: a = _formant_w(fh, P['formant']) / h ** .6
            elif ins == 'flute': a = [1, .35, .14, .06, .03][h - 1] if h <= 5 else 0
            else: a = (.72 ** (h - 1)) / h
            if a > 1e-3: y += (a * np.sin(h * ph + rng.uniform(0, 6.28))).astype(np.float32)
        if ch is None: out += np.vstack([y, y]) * .5
        else: out[ch] += y; out[1 - ch] += y * .35
    if P.get('breath') or ins == 'flute':
        b = rng.standard_normal(n).astype(np.float32)
        b = signal.sosfilt(signal.butter(2, [min(f0 * 1.5, 9000), min(f0 * 5, 15000)], 'band', fs=SR, output='sos'), b).astype(np.float32)
        out += np.vstack([b, b]) * (P.get('breath', .02)) * (1 + .5 * np.sin(2 * np.pi * .7 * t))
    a = np.sin(np.clip(t / P['att'], 0, 1) * np.pi / 2) ** 2; r = np.clip((dur + rel - t) / rel, 0, 1) ** 1.5
    swell = 1 - .18 * np.cos(np.clip(t / max(dur, .5), 0, 1) * 2 * np.pi) if ins in ('flute', 'hum', 'choir', 'strings') else 1   # 가운데가 살짝 부푸는 호흡
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
    'musicbox': dict(mode='song', mel='musicbox', acc='harp', oct=6, meter=3, bpm=(54, 64), pad='pad', padv=.8, scales=['major', 'lydian']),
    'piano':    dict(mode='song', mel='piano', acc='piano', oct=5, meter=4, bpm=(52, 60), pad='pad', padv=1.0, gain=-2.8, scales=['major', 'mixo']),
    'harp':     dict(mode='song', mel='celesta', acc='harp', oct=6, meter=3, bpm=(56, 66), pad='pad', padv=.9, scales=['major']),
    'mixed':    dict(mode='song', mel='musicbox', acc='piano', oct=6, meter=3, bpm=(52, 62), pad='pad', padv=.9, scales=['major', 'lydian']),
    'guitar':   dict(mode='song', mel='guitar', acc='guitar', oct=5, meter=3, bpm=(50, 60), pad='strings', padv=.6, scales=['major', 'mixo']),
    'humming':  dict(mode='song', mel='hum', acc='harp', oct=5, meter=3, bpm=(48, 56), pad='choir', padv=.7, scales=['major'], gain=-1.5),
    'flute_song': dict(mode='song', mel='flute', acc='guitar', oct=6, meter=4, bpm=(50, 58), pad='strings', padv=.7, scales=['major', 'dorian']),
    'vibes':    dict(mode='song', mel='vibes', acc='epiano', oct=5, meter=4, bpm=(50, 58), pad='pad', padv=.7, scales=['major', 'lydian']),
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
    'kalimba_ambient': dict(mode='ambient', voices=['kalimba', 'kalimba', 'glass', 'pad', 'flute'], drone='pad', scales=['penta'], wet=.45),
    # --- drone: 선법 드론 위에 자유 박자 선율 (명상)
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
    for p, (ins, up, vel) in enumerate(passes):
        for i, br in enumerate(mel_bars):
            t0 = (intro + p * 16 + i) * bar
            for on, d, ix in br:
                acc = 1.08 if on == 0 else .95; m = to_midi(ix) + up
                if ins in SUS: ev.append((t0 + on * beat + hum(), ins, m - 12 if ins == 'hum' else m, vel * acc * float(R.uniform(.9, 1.02)), .15, d * beat * .96))
                else: ev.append((t0 + on * beat + hum(), ins, m, vel * acc * float(R.uniform(.88, 1.04)), .2 + .04 * (ix - 4), None))
    return ev, total_bars * bar, dict(tonic=tonic, bpm=round(bpm), meter=meter, scale=sc_name, mode='song', inst=mel)


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


COMPOSE = {'song': compose_song, 'arp': compose_arp, 'ambient': compose_ambient, 'drone': compose_drone}


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
CAL = {'rain': -4.2, 'waves': 1.3, 'pink': 8.7, 'brown': -8.8, 'white': 11.6, 'heart': -12.7, 'fire': -10.9,
       'drips': -9.5, 'thunder': -10.0, 'stream': -20.5, 'wind': -13.5, 'chimes': 3.0, 'crickets': 29.5, 'clock': -3.0, 'purr': -2.7}
PINK_B, PINK_A = [0.049922035, -0.095993537, 0.050612699, -0.004408786], [1, -2.494956002, 2.017265875, -0.522189400]
PENTA_CHIME = [0, 2, 4, 7, 9, 12, 14, 16]


def _drip(R, f0=900, up=1.6, dur=.05):
    """물방울 '똑': 짧게 올라가는 사인 (실제 물방울은 기포가 커지며 음이 올라감)"""
    n = int(dur * SR); t = np.arange(n) / SR; f = f0 * (1 + (up - 1) * np.clip(t / dur, 0, 1) ** .6)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (dur * .35)); y[:16] *= np.linspace(0, 1, 16)
    return y.astype(np.float32)


class Ambience:
    """layers: {이름: dB} — rain, drips, thunder, waves, stream, wind, chimes, crickets, fire, clock, purr, pink, brown, white, heart"""
    def __init__(s, layers, seed=0):
        s.L = layers; s.R = np.random.default_rng(seed); s.t0 = 0; R = s.R
        s.pink = LF(PINK_B, PINK_A); s.brown = LF([1], [1, -.996]); s.dc = Filt(bw('high', 25, 1))
        s.rain_bp = Filt(bw('band', [380, 8500])); s.rain_lo = Filt(bw('low', 260))
        s.drops = [(LF(*resonator(f, .012), ch=1), f) for f in R.uniform(1700, 4600, 4)]
        s.wave_lp = Filt(bw('low', 1300)); s.wave_hs = Filt(bw('band', [1800, 7000]))
        s.white_lp = Filt(bw('low', 7500)); s.heart = LF(*resonator(52, .07), ch=1); s.heart_lp = Filt(bw('low', 420))
        s.fire_lo = Filt(bw('low', 320)); s.crk = LF(*resonator(2600, .004), ch=1); s.crk_hp = Filt(bw('high', 900), ch=1)
        # v2
        s.ev = Events(20.0)
        s.st_bp = Filt(bw('band', [500, 3200])); s.st_lo = Filt(bw('band', [90, 420]))
        s.bubbles = [(LF(*resonator(f, .006), ch=1), f) for f in R.uniform(700, 2400, 6)]
        s.wind_f = float(R.uniform(250, 500)); s.wind_bp = None; s.wind_lo = Filt(bw('low', 900))
        s.chime_root = 72 + int(R.choice([0, 2, 5, 7])); s.chime_next = 3.0
        s.crick = [(float(R.uniform(3900, 5200)), float(R.uniform(22, 34)), float(R.uniform(0, 6.3)), float(R.uniform(-.8, .8)), float(R.uniform(.5, 1.0)), float(R.uniform(2.5, 4.5))) for _ in range(5)]
        s.crick_lp = Filt(bw('low', 5600)); s.thunder_next = float(R.uniform(25, 60)); s.th_lp = Filt(bw('low', 110))
        s.clock_i = 0; s.purr_lp = Filt(bw('low', 320)); s.purr_bp = Filt(bw('band', [60, 240]))
        s.drip_cache = [_drip(R, float(R.uniform(650, 1500)), float(R.uniform(1.3, 2.0)), float(R.uniform(.035, .07))) for _ in range(12)]

    def noise(s, n, corr=.55):  # 좌우가 약간 다른 자연스러운 스테레오 노이즈
        a = s.R.standard_normal(n).astype(np.float32); b = s.R.standard_normal((2, n)).astype(np.float32)
        return corr * a + math.sqrt(1 - corr * corr) * b

    def __call__(s, n):
        t = (s.t0 + np.arange(n)) / SR; T0 = s.t0 / SR; out = np.zeros((2, n), np.float32); R = s.R
        g = lambda k: 10 ** ((s.L[k] + CAL[k]) / 20)
        s.ev.begin(n)
        need_pink = any(k in s.L for k in ('pink', 'rain', 'waves', 'stream', 'wind'))
        pk = s.pink(s.noise(n)) * 3.2 if need_pink else None
        if 'pink' in s.L: out += pk * .18 * g('pink')
        if any(k in s.L for k in ('brown', 'heart', 'fire', 'rain', 'thunder', 'wind', 'stream', 'purr')):
            br = s.dc(s.brown(s.noise(n, .7)) * .055)
            if 'brown' in s.L: out += br * .9 * g('brown')
        if 'white' in s.L: out += s.white_lp(s.noise(n, .3)) * .06 * g('white')
        if 'rain' in s.L:
            m = 1 + .14 * np.sin(2 * np.pi * t / 41) + .08 * np.sin(2 * np.pi * t / 13.7)
            base = s.rain_bp(pk) * .55 * m; dr = np.zeros((2, n), np.float32)
            for i, (rf, f) in enumerate(s.drops):
                imp = (R.random(n) < 9 / SR) * R.exponential(1, n) * R.choice([-1, 1], n)
                d = rf(imp[None].astype(np.float32))[0] * .5; dr[i % 2] += d; dr[1 - i % 2] += d * .45
            out += (base + dr * m + s.rain_lo(br) * .5) * g('rain')
        if 'drips' in s.L:   # 처마·지붕에서 떨어지는 물방울: 2~5초마다 몇 개씩 몰려 떨어짐
            rate = (2.2 + 1.5 * np.sin(2 * np.pi * T0 / 37)) / SR
            idx = np.where(R.random(n) < rate)[0]
            for i in idx:
                d = s.drip_cache[R.integers(len(s.drip_cache))] * float(R.uniform(.5, 1.0)) * .9
                s.ev.add(int(i), pan(d, float(R.uniform(-.7, .7))) * g('drips'))
        if 'thunder' in s.L:  # 먼 천둥: 1~3분에 한 번, 5~12초 낮은 울림
            while s.thunder_next < T0 + n / SR:
                dur = float(R.uniform(5, 12)); k = int(dur * SR); tt = np.arange(k) / SR
                env = (np.exp(-tt / (dur * .3)) * (1 - np.exp(-tt / .4))) * (1 + .5 * np.sin(2 * np.pi * tt * R.uniform(.3, 1.2)) * np.exp(-tt / 3))
                x = R.standard_normal((2, k)).astype(np.float32) * env.astype(np.float32)
                x = Filt(bw('low', float(R.uniform(70, 130))))(x) * 9.0 * float(R.uniform(.5, 1.0))
                s.ev.add(int((s.thunder_next - T0) * SR), x * g('thunder')); s.thunder_next += float(R.uniform(50, 170))
        if 'waves' in s.L:
            def env(off):
                ph = 2 * np.pi / 9.5 * (t - .15 * 71 / (2 * np.pi) * np.cos(2 * np.pi * t / 71) - .1 * 23 / (2 * np.pi) * np.cos(2 * np.pi * t / 23)) + off
                sw = .5 - .5 * np.cos(ph); return (.18 + .82 * sw ** 1.6).astype(np.float32)
            e = np.vstack([env(0), env(.35)]); wash = np.vstack([env(-.9), env(-.6)]) ** 2.2
            out += (s.wave_lp(pk) * .9 * e + s.wave_hs(pk) * .35 * wash) * g('waves')
        if 'stream' in s.L:   # 시냇물: 찰랑이는 중음 + 낮은 콸콸 + 보글보글 기포
            m = 1 + .12 * np.sin(2 * np.pi * t / 5.3) + .08 * np.sin(2 * np.pi * t / 1.7 + 1)
            bub = np.zeros((2, n), np.float32)
            for i, (rf, f) in enumerate(s.bubbles):
                imp = (R.random(n) < 14 / SR) * R.exponential(1, n) * R.choice([-1, 1], n)
                d = rf(imp[None].astype(np.float32))[0] * .45; bub[i % 2] += d; bub[1 - i % 2] += d * .4
            out += (s.st_bp(pk) * .5 * m + s.st_lo(br) * 6.0 * (1 + .3 * np.sin(2 * np.pi * t / 3.1)) + bub) * g('stream')
        if 'wind' in s.L:     # 바람: 천천히 움직이는 밴드패스 + 돌풍
            gust = (.45 + .55 * (.5 + .5 * np.sin(2 * np.pi * t / 23 + 1.3)) ** 2 * (.6 + .4 * np.sin(2 * np.pi * t / 7.1)))
            fc = s.wind_f * (1 + .35 * np.sin(2 * np.pi * T0 / 19))
            s.wind_bp = s.wind_bp or Filt(bw('band', [fc * .6, fc * 1.6], 1))
            out += (s.wind_bp(pk) * .8 * gust + s.wind_lo(br) * 2.5 * gust) * g('wind')
        if 'chimes' in s.L:   # 풍경: 바람이 불 때 2~6개 음이 흩어져 울림
            while s.chime_next < T0 + n / SR:
                k = int(R.choice([1, 2, 2, 3, 4, 5])); tt = s.chime_next
                for j in range(k):
                    m = s.chime_root + int(R.choice(PENTA_CHIME)); x = note('glass', m) * float(R.uniform(.25, .6))
                    s.ev.add(int((tt - T0) * SR), pan(x, float(R.uniform(-.8, .8))) * g('chimes')); tt += float(R.uniform(.08, .6))
                s.chime_next += float(R.uniform(2.5, 14))
        if 'crickets' in s.L: # 귀뚜라미: 몇 마리가 각자 박자로 찌르르
            cr = np.zeros((2, n), np.float32)
            for f, rate, ph, pn, lv, bp in s.crick:
                chirp = np.clip((np.sin(2 * np.pi * rate * t + ph) - .3) * 6, 0, 1).astype(np.float32)        # 찌르르 펄스 (모서리 둥글게)
                burst = np.clip((np.sin(2 * np.pi * t / bp + ph) + .2) * 3, 0, 1).astype(np.float32)          # 울었다 쉬었다
                tone = np.sin(2 * np.pi * f * t) * (.5 + .5 * np.sin(2 * np.pi * f * .0092 * t)) * chirp * burst * lv
                a = (pn + 1) * math.pi / 4; cr[0] += tone * math.cos(a); cr[1] += tone * math.sin(a)
            out += s.crick_lp(cr) * .012 * g('crickets')
        if 'fire' in s.L:
            roar = s.fire_lo(br) * (1.3 + .25 * np.sin(2 * np.pi * t / 7.3) + .15 * np.sin(2 * np.pi * t / 2.9))
            burst = (R.random(n) < 5 / SR) * R.exponential(1, n) ** 1.5
            burst += (R.random(n) < 40 / SR) * R.exponential(.15, n)
            ck = s.crk_hp(s.crk(burst[None].astype(np.float32)))[0] * 1.4
            out += (roar + np.vstack([ck, ck * .7])) * g('fire')
        if 'clock' in s.L:    # 괘종시계 똑·딱
            while s.clock_i * 1.0 < T0 + n / SR:
                f = 2300 if s.clock_i % 2 == 0 else 1900; k = int(.06 * SR); tt = np.arange(k) / SR
                x = (np.sin(2 * np.pi * f * tt) * .6 + np.sin(2 * np.pi * f * 2.3 * tt) * .25 + R.standard_normal(k) * .15 * np.exp(-tt / .003)) * np.exp(-tt / .012)
                s.ev.add(int((s.clock_i - T0) * SR), pan(x.astype(np.float32) * .55, -.3 if s.clock_i % 2 == 0 else -.2) * g('clock')); s.clock_i += 1
        if 'purr' in s.L:     # 고양이 골골: 25Hz 떨림 + 숨 들이쉬고 내쉬기
            breath = .5 + .5 * np.sin(2 * np.pi * t / 2.6); inh = (np.sin(2 * np.pi * t / 2.6) > 0)
            pulse = np.clip(np.sin(2 * np.pi * (25 + 3 * inh) * t), 0, 1) ** 3
            x = s.purr_bp(s.noise(n, .9)) * pulse * (.35 + .65 * breath) * 4.0
            out += s.purr_lp(x) * g('purr')
        if 'heart' in s.L:   # 엄마 뱃속: 낮은 '쉬익' + 66bpm 심장 박동
            per = 60 / 66; ph = (t % per); imp = np.zeros(n, np.float32)
            idx1 = np.where(np.diff(np.floor(t / per)) > 0)[0]
            imp[idx1] = 1.0; idx2 = np.clip(idx1 + int(.3 * SR), 0, n - 1); imp[idx2] += .62
            hb = s.heart(imp[None])[0] * 14
            whoosh = s.heart_lp(br) * (1.6 + .35 * np.exp(-ph / .25))
            out += (whoosh + np.vstack([hb, hb])) * g('heart')
        out += s.ev.end(); s.t0 += n
        return out


# =====================================================================
# 4) 트랙 만들기 (스트리밍)
# =====================================================================
def make_track(path, minutes, style, layers, seed, music_db=0.0, log=print):
    """style: None(자연음만) / 스타일 이름 / 스타일 이름 목록(곡마다 번갈아). 반환: (RMS dBFS, 곡 정보 목록)"""
    N = int(minutes * 60 * SR); amb = Ambience(layers, seed) if layers else None
    ir = make_ir(seed); wf = wave.open(str(path), 'wb'); wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR)
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
