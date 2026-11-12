#!/usr/bin/env python3
"""수면 음악 오디오 엔진 — 외부 음원 0개. 모든 소리를 수학적으로 직접 합성합니다.
  · 자장가: 매번 새로 작곡 (조성·박자·화성 진행·멜로디를 시드로 생성) → 오르골/피아노/하프/패드로 연주
  · 자연음: 빗소리 · 파도 · 핑크/브라운/화이트 노이즈 · 엄마 뱃속(심장박동) · 장작 타는 소리
  · 1시간 분량을 메모리에 다 올리지 않고 30초 단위로 이어 쓰기 (GitHub Actions 메모리 안전)
"""
import math, wave
import numpy as np
from scipy import signal

SR = 44100
SCALE = [0, 2, 4, 5, 7, 9, 11]


def midi_hz(m): return 440.0 * 2 ** ((m - 69) / 12)


# =====================================================================
# 1) 악기 (가산 합성) — 음 높이별로 한 번만 만들고 재사용
# =====================================================================
# (배음 비율, 세기, 감쇠 시간상수 초)
INSTR = {
    'musicbox': dict(p=[(1, 1.0, 1.05), (2, .30, .55), (3, .10, .35), (4.18, .09, .22), (5.43, .045, .15), (6.79, .025, .1)], att=.0025, dur=3.6, gain=.5, bright=.35),
    'piano':    dict(p=[(n, 1 / n ** 1.7, 2.6 / n ** .55) for n in range(1, 9)], att=.007, dur=5.0, gain=.62, inh=.00035, bright=.2),
    'harp':     dict(p=[(n, 1 / n ** 1.35, 1.6 / n ** .7) for n in range(1, 7)], att=.004, dur=3.4, gain=.5, bright=.25),
    'celesta':  dict(p=[(1, 1.0, .8), (2, .18, .4), (4, .07, .2), (6.2, .03, .12)], att=.002, dur=2.8, gain=.42, bright=.3),
}
_NOTE = {}


def note(ins, m):
    k = (ins, m)
    if k in _NOTE: return _NOTE[k]
    P = INSTR[ins]; f0 = midi_hz(m); n = int(P['dur'] * SR); t = np.arange(n, dtype=np.float32) / SR
    y = np.zeros(n, np.float32); rng = np.random.default_rng(m * 7 + len(ins))
    for r, a, tau in P['p']:
        f = f0 * r * (1 + P.get('inh', 0) * r * r)
        if f > SR * .42: continue
        te = tau * (523.0 / f0) ** P['bright']          # 높은 음일수록 조금 빨리 사라짐 (실제 악기처럼)
        y += (a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) * np.exp(-t / te)).astype(np.float32)
    na = max(1, int(P['att'] * SR)); y[:na] *= np.linspace(0, 1, na, dtype=np.float32)
    nf = int(.08 * SR); y[-nf:] *= np.linspace(1, 0, nf, dtype=np.float32)
    y *= P['gain'] / (np.abs(y).max() + 1e-9) * (523.0 / max(f0, 140)) ** .18   # 고음 귀 따가움 완화
    _NOTE[k] = y; return y


_PAD = {}


def pad_note(m, dur):
    """따뜻한 패드: 살짝 어긋난 3개 음 + 부드러운 배음, 천천히 나타났다 사라짐 (스테레오)"""
    k = (m, round(dur, 2))
    if k in _PAD: return _PAD[k]
    rel = 2.5; n = int((dur + rel) * SR); t = np.arange(n, dtype=np.float32) / SR; f0 = midi_hz(m)
    out = np.zeros((2, n), np.float32)
    for ch, cents in ((0, -5), (1, 5), (0, 0), (1, 0)):
        f = f0 * 2 ** (cents / 1200); vib = 1 + .0018 * np.sin(2 * np.pi * (4.3 + ch * .4) * t)
        ph = 2 * np.pi * f * np.cumsum(vib) / SR
        out[ch] += sum(np.sin(h * ph) * (.55 ** (h - 1)) / h for h in range(1, 5)).astype(np.float32)
    a = np.clip(t / 1.4, 0, 1) ** 2; r = np.clip((dur + rel - t) / rel, 0, 1) ** 1.5
    out *= (a * r).astype(np.float32) * .16
    _PAD[k] = out; return out


def pan(x, p):  # p: -1(왼) ~ 1(오), 일정 파워
    a = (p + 1) * math.pi / 4; return np.vstack([x * math.cos(a), x * math.sin(a)])


# =====================================================================
# 2) 자장가 작곡기
# =====================================================================
PROGS = [[1, 6, 4, 5], [1, 4, 1, 5], [1, 3, 4, 1], [6, 4, 1, 5], [1, 5, 6, 4], [1, 4, 6, 5], [4, 1, 5, 1], [1, 6, 2, 5]]
RHY3 = [[2, 1], [1, 1, 1], [3], [1, 2], [1.5, .5, 1], [2, 1], [1, 1, 1]]
RHY4 = [[2, 2], [1, 1, 2], [3, 1], [4], [2, 1, 1], [1.5, .5, 2], [2, 2]]
STYLE = {   # 테마별 연주 방식
    'musicbox': dict(mel='musicbox', acc='harp', oct=6, meter=3, bpm=(54, 64), pad=.8),
    'piano':    dict(mel='piano', acc='piano', oct=5, meter=4, bpm=(52, 60), pad=1.0, gain=-2.8),
    'harp':     dict(mel='celesta', acc='harp', oct=6, meter=3, bpm=(56, 66), pad=.9),
    'mixed':    dict(mel='musicbox', acc='piano', oct=6, meter=3, bpm=(52, 62), pad=.9),
}


def chord_idx(deg):  # 화음 구성음 (음계 인덱스)
    r = deg - 1; return [r, r + 2, r + 4]


def compose(seed, style):
    """16마디 노래(A A' B A'') → 반주 포함 음표 목록 [(시작초, 악기, midi, 세기, 팬)] + 길이"""
    R = np.random.default_rng(seed); S = STYLE[style]
    tonic = 60 + int(R.choice([0, 2, 5, 7, -3, -1]))          # C D F G A Bb(아래)
    meter = S['meter']; bpm = float(R.uniform(*S['bpm'])); beat = 60 / bpm; bar = meter * beat
    rhy = RHY3 if meter == 3 else RHY4
    P = [int(x) for x in PROGS[R.integers(len(PROGS))]]; Q = [int(x) for x in PROGS[R.integers(len(PROGS))]]
    while Q == P: Q = [int(x) for x in PROGS[R.integers(len(PROGS))]]
    lo, hi = 0, 10                                              # 멜로디 음역 (음계 인덱스, 으뜸음=0)

    def gen_bar(deg, prev, rh, last=False, end_tonic=False, center=4):
        out = []; cur = prev; on = 0.0
        for k, d in enumerate(rh):
            if k == 0 or last:
                cands = [c + 7 * o for c in chord_idx(deg) for o in (-1, 0, 1) if lo <= c + 7 * o <= hi]
                if end_tonic: cands = [c for c in cands if c % 7 == 0] or [0]
                cur = min(cands, key=lambda c: abs(c - cur) + .25 * abs(c - center) + R.uniform(0, 1.2))
            else:
                step = int(R.choice([-2, -1, -1, 1, 1, 2, 0]))
                cur = int(np.clip(cur + step, lo, hi))
            out.append((on, d, cur)); on += d
        return out

    def phrase(prog, prev, rhs=None, center=4, cad=False):
        bars = []; rhs = rhs or [rhy[R.integers(len(rhy))] for _ in range(3)] + [[meter]]
        for i, deg in enumerate(prog):
            b = gen_bar(deg, prev, rhs[i], last=(i == 3), end_tonic=(cad and i == 3), center=center); prev = b[-1][2]; bars.append(b)
        return bars, rhs, prev

    A, rA, pv = phrase(P, 4)
    A2 = A[:3] + [gen_bar(P[3], A[2][-1][2], [meter], last=True)]
    B, _, pv = phrase(Q, A2[-1][-1][2], center=6)
    Pc = P[:2] + [5, 1]
    A3 = A[:2] + phrase(Pc, A[1][-1][2], rhs=rA[:2] + [rhy[0], [meter]], cad=True)[0][2:]
    mel_bars = A + A2 + B + A3; chords = P + P + Q + Pc

    ev = []; base = tonic + 12 * (S['oct'] - 5)
    to_midi = lambda ix: base + SCALE[ix % 7] + 12 * (ix // 7)
    hum = lambda: float(R.normal(0, .008))
    intro = 2
    passes = [(S['mel'], 0, .78), (S['acc'] if S['acc'] != 'piano' else 'celesta', 0, .62), (S['mel'], 12 if S['oct'] < 6 else 0, .66)]
    n_pass = len(passes); total_bars = intro + 16 * n_pass + 3
    # 반주 + 패드 (전체 마디)
    for b in range(total_bars):
        deg = chords[(b - intro) % 16] if intro <= b < intro + 16 * n_pass else 1
        t0 = b * bar; ci = chord_idx(deg); root = tonic - 12 + SCALE[ci[0] % 7]
        if b < total_bars - 2:
            if meter == 3:
                notes = [(0, root, .42), (1, tonic + SCALE[ci[1] % 7] + (12 if ci[1] >= 7 else 0), .26), (2, tonic + SCALE[ci[2] % 7] + (12 if ci[2] >= 7 else 0), .24)]
            else:
                notes = [(0, root, .4), (1, tonic + SCALE[ci[2] % 7], .24), (2, tonic + 12 + SCALE[ci[1] % 7], .24), (3, tonic + SCALE[ci[2] % 7], .22)]
            for bt, m, v in notes: ev.append((t0 + bt * beat + hum(), S['acc'], int(m), v * float(R.uniform(.85, 1.05)), -.25))
        else:  # 마지막: 으뜸화음 길게
            if b == total_bars - 2:
                for m, v in ((tonic - 12, .36), (tonic + 4, .22), (tonic + 7, .2), (tonic + 12, .18)): ev.append((t0 + hum(), S['acc'], m, v, -.2))
        if S['pad'] > 0:
            for ix in ci: ev.append((t0, 'PAD', tonic - 12 + SCALE[ix % 7] + 12 * (ix // 7), S['pad'] * (.9 if b < total_bars - 2 else .7), bar if b < total_bars - 2 else bar * 2.5))
    # 멜로디 (3번 반복, 악기·옥타브 바꿔 가며)
    for p, (ins, up, vel) in enumerate(passes):
        for i, br in enumerate(mel_bars):
            t0 = (intro + p * 16 + i) * bar
            for on, d, ix in br:
                acc = 1.08 if on == 0 else .95
                ev.append((t0 + on * beat + hum(), ins, to_midi(ix) + up, vel * acc * float(R.uniform(.88, 1.04)), .2 + .04 * (ix - 4)))
    length = total_bars * bar
    info = dict(tonic=tonic, bpm=round(bpm), meter=meter, prog=P)
    return ev, length, info


def render_piece(ev, length):
    n = int((length + 4) * SR); out = np.zeros((2, n), np.float32)
    for t, ins, m, v, p in ev:
        i0 = max(0, int(t * SR))
        if ins == 'PAD':
            x = pad_note(m, p) * v; j = min(n, i0 + x.shape[1]); out[:, i0:j] += x[:, :j - i0]; continue
        x = pan(note(ins, m) * v, p); j = min(n, i0 + x.shape[1]); out[:, i0:j] += x[:, :j - i0]
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
# 3) 자연음 · 노이즈 (상태를 이어가며 블록 단위로 생성 → 이음새 없음)
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


CAL = {'rain': -4.2, 'waves': 1.3, 'pink': 8.7, 'brown': -8.8, 'white': 11.6, 'heart': -12.7, 'fire': -10.9}
PINK_B, PINK_A = [0.049922035, -0.095993537, 0.050612699, -0.004408786], [1, -2.494956002, 2.017265875, -0.522189400]


class Ambience:
    """layers: {'rain':dB, 'waves':dB, 'pink':dB, 'brown':dB, 'white':dB, 'heart':dB, 'fire':dB}"""
    def __init__(s, layers, seed=0):
        s.L = layers; s.R = np.random.default_rng(seed); s.t0 = 0
        s.pink = LF(PINK_B, PINK_A); s.brown = LF([1], [1, -.996]); s.dc = Filt(bw('high', 25, 1))
        s.rain_bp = Filt(bw('band', [380, 8500])); s.rain_lo = Filt(bw('low', 260))
        s.drops = [(LF(*resonator(f, .012), ch=1), f) for f in s.R.uniform(1700, 4600, 4)]
        s.wave_lp = Filt(bw('low', 1300)); s.wave_hs = Filt(bw('band', [1800, 7000]))
        s.white_lp = Filt(bw('low', 7500)); s.heart = LF(*resonator(52, .07), ch=1); s.heart_lp = Filt(bw('low', 420))
        s.fire_lo = Filt(bw('low', 320)); s.crk = LF(*resonator(2600, .004), ch=1); s.crk_hp = Filt(bw('high', 900), ch=1)

    def noise(s, n, corr=.55):  # 좌우가 약간 다른 자연스러운 스테레오 노이즈
        a = s.R.standard_normal(n).astype(np.float32); b = s.R.standard_normal((2, n)).astype(np.float32)
        return corr * a + math.sqrt(1 - corr * corr) * b

    def __call__(s, n):
        t = (s.t0 + np.arange(n)) / SR; out = np.zeros((2, n), np.float32)
        g = lambda k: 10 ** ((s.L[k] + CAL[k]) / 20)   # CAL: 0dB = 음악과 같은 크기(-20dBFS)로 보정
        need_pink = any(k in s.L for k in ('pink', 'rain', 'waves'))
        pk = s.pink(s.noise(n)) * 3.2 if need_pink else None
        if 'pink' in s.L: out += pk * .18 * g('pink')
        if any(k in s.L for k in ('brown', 'heart', 'fire', 'rain')):
            br = s.dc(s.brown(s.noise(n, .7)) * .055)
            if 'brown' in s.L: out += br * .9 * g('brown')
        if 'white' in s.L: out += s.white_lp(s.noise(n, .3)) * .06 * g('white')
        if 'rain' in s.L:
            m = 1 + .14 * np.sin(2 * np.pi * t / 41) + .08 * np.sin(2 * np.pi * t / 13.7)
            base = s.rain_bp(pk) * .55 * m
            dr = np.zeros((2, n), np.float32)
            for i, (rf, f) in enumerate(s.drops):
                imp = (s.R.random(n) < 9 / SR) * s.R.exponential(1, n) * s.R.choice([-1, 1], n)
                d = rf(imp[None].astype(np.float32))[0] * .5; dr[i % 2] += d; dr[1 - i % 2] += d * .45
            out += (base + dr * m + s.rain_lo(br) * .5) * g('rain')
        if 'waves' in s.L:
            def env(off):
                ph = 2 * np.pi / 9.5 * (t - .15 * 71 / (2 * np.pi) * np.cos(2 * np.pi * t / 71) - .1 * 23 / (2 * np.pi) * np.cos(2 * np.pi * t / 23)) + off
                sw = .5 - .5 * np.cos(ph); return (.18 + .82 * sw ** 1.6).astype(np.float32)
            e = np.vstack([env(0), env(.35)]); wash = np.vstack([env(-.9), env(-.6)]) ** 2.2
            out += (s.wave_lp(pk) * .9 * e + s.wave_hs(pk) * .35 * wash) * g('waves')
        if 'heart' in s.L:   # 엄마 뱃속: 낮은 '쉬익' + 66bpm 심장 박동
            per = 60 / 66; ph = (t % per)
            imp = np.zeros(n, np.float32)
            idx1 = np.where(np.diff(np.floor(t / per)) > 0)[0]
            imp[idx1] = 1.0; idx2 = np.clip(idx1 + int(.3 * SR), 0, n - 1); imp[idx2] += .62
            hb = s.heart(imp[None])[0] * 14
            whoosh = s.heart_lp(br) * (1.6 + .35 * np.exp(-ph / .25))
            out += (whoosh + np.vstack([hb, hb])) * g('heart')
        if 'fire' in s.L:
            roar = s.fire_lo(br) * (1.3 + .25 * np.sin(2 * np.pi * t / 7.3) + .15 * np.sin(2 * np.pi * t / 2.9))
            burst = (s.R.random(n) < 5 / SR) * s.R.exponential(1, n) ** 1.5
            burst += (s.R.random(n) < 40 / SR) * s.R.exponential(.15, n)
            ck = s.crk_hp(s.crk(burst[None].astype(np.float32)))[0] * 1.4
            out += (roar + np.vstack([ck, ck * .7])) * g('fire')
        s.t0 += n
        return out


# =====================================================================
# 4) 1시간 트랙 만들기 (스트리밍)
# =====================================================================
def make_track(path, minutes, style, layers, seed, music_db=0.0, log=print):
    """style=None 이면 음악 없이 자연음만. path=16bit 스테레오 WAV. 반환: (RMS dBFS, 곡 정보 목록)"""
    N = int(minutes * 60 * SR); amb = Ambience(layers, seed) if layers else None
    ir = make_ir(seed); wf = wave.open(str(path), 'wb'); wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR)
    fin, fout = int(10 * SR), int(50 * SR); written = 0; ss = 0.0; songs = []
    mg = 10 ** (music_db / 20)

    def flush(x):
        nonlocal written, ss
        x = x[:, :max(0, N - written)]
        if not x.shape[1]: return
        if amb is not None: x = x + amb(x.shape[1])
        i = written + np.arange(x.shape[1])
        f = np.minimum(1, np.minimum(i / fin, (N - i) / fout)).clip(0, 1).astype(np.float32)
        x = np.tanh(x * f * .9) / .9                      # 부드러운 리미터
        ss += float((x.astype(np.float64) ** 2).sum())
        wf.writeframes((np.clip(x.T, -1, 1) * 32000).astype('<i2').tobytes()); written += x.shape[1]

    if style is None:
        B = 30 * SR
        while written < N: flush(np.zeros((2, min(B, N - written)), np.float32))
    else:
        pend = np.zeros((2, 0), np.float32); out_pos = 0; cur = int(4 * SR); k = 0
        R = np.random.default_rng(seed)
        while cur < N:
            ev, L, info = compose(int(seed * 1000 + k), style); k += 1
            x = reverb(render_piece(ev, L), ir) * .55 * mg * 10 ** (STYLE[style].get('gain', 0) / 20)
            need = cur + x.shape[1] - out_pos
            if pend.shape[1] < need: pend = np.hstack([pend, np.zeros((2, need - pend.shape[1]), np.float32)])
            pend[:, cur - out_pos: cur - out_pos + x.shape[1]] += x
            songs.append(info); nxt = cur + int((L + R.uniform(3, 6)) * SR)
            cut = min(nxt, N) - out_pos; flush(pend[:, :cut]); pend = pend[:, cut:]; out_pos += cut; cur = nxt
            if k % 4 == 0: log(f'  작곡·연주 {k}곡 · {out_pos / SR / 60:.1f}/{minutes}분')
        while written < N:
            m = min(30 * SR, N - written); blk = pend[:, :m]
            if blk.shape[1] < m: blk = np.hstack([blk, np.zeros((2, m - blk.shape[1]), np.float32)])
            pend = pend[:, m:]; flush(blk)
    wf.close()
    rms = 10 * math.log10(ss / (2 * N) + 1e-12)
    return rms, songs
