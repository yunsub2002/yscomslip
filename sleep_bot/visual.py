#!/usr/bin/env python3
"""잔잔한 배경 영상 — 외부 이미지·영상 0개, 전부 수학으로 그림.
장면: 밤하늘(night) · 비 오는 창(rainwin) · 달빛 바다(sea) · 반딧불 숲(firefly) · 눈 오는 밤(snow) · 오로라(aurora) · 파스텔 구름(pastel) · 따뜻한 불빛(warm)
· 장면 4개를 90초씩 이어 붙이고 6초 동안 서서히 바뀜 → 6분짜리 '끊김 없는 루프' → 1시간으로 반복(재인코딩 없이 복사)
· 모든 움직임이 시간 t의 주기 함수라 루프 이음새가 보이지 않음
"""
import math, os, subprocess
import numpy as np

W, H = 1280, 720            # 계산 해상도 (출력은 1920x1080 으로 확대)
FPS = 24


def hexc(h): h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


def vgrad(stops, h=H, w=W):
    """세로 그라데이션 stops=[(0~1 위치, '#색'), ...]"""
    y = np.linspace(0, 1, h, dtype=np.float32); col = np.zeros((h, 3), np.float32)
    for c in range(3): col[:, c] = np.interp(y, [s[0] for s in stops], [hexc(s[1])[c] for s in stops])
    return np.repeat(col[:, None, :], w, axis=1)


def tile_noise(h, w, scale, seed, octaves=3):
    """FFT로 만든 '이어 붙여도 이음새 없는' 부드러운 노이즈 (0~1)"""
    R = np.random.default_rng(seed); out = np.zeros((h, w), np.float32); amp = 1.0
    for o in range(octaves):
        ky = np.fft.fftfreq(h)[:, None]; kx = np.fft.fftfreq(w)[None, :]; k = np.sqrt(kx ** 2 + ky ** 2)
        s = scale / (2 ** o); f = np.exp(-(k * s) ** 2 * 8)
        z = np.real(np.fft.ifft2(np.fft.fft2(R.standard_normal((h, w))) * f)).astype(np.float32)
        out += amp * z / (z.std() + 1e-9); amp *= .5
    out -= out.min(); out /= out.max() + 1e-9; return out


def _taper(h):
    y = np.linspace(0, 1, h, dtype=np.float32); return (np.clip(np.sin(np.pi * y), 0, 1) ** 1.5)[:, None]


_SPR = {}


def sprite(r, sharp=2.0):
    k = (round(r, 1), sharp)
    if k not in _SPR:
        n = int(r * 3) + 2; y, x = np.mgrid[-n:n + 1, -n:n + 1].astype(np.float32)
        _SPR[k] = np.exp(-((x * x + y * y) / (r * r)) ** (sharp / 2))
    return _SPR[k]


def blit(img, x, y, spr, color, a=1.0):
    n = spr.shape[0] // 2; xi, yi = int(x), int(y)
    x0, x1, y0, y1 = xi - n, xi + n + 1, yi - n, yi + n + 1
    sx0, sy0 = max(0, -x0), max(0, -y0); x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(W, x1), min(H, y1)
    if x1 <= x0 or y1 <= y0: return
    s = spr[sy0:sy0 + y1 - y0, sx0:sx0 + x1 - x0]
    img[y0:y1, x0:x1] += s[..., None] * (color * a)


def ridge(seed, base, amp, freqs=3):
    R = np.random.default_rng(seed); x = np.arange(W) / W
    y = np.full(W, base, np.float32)
    for k in range(freqs):
        f = R.uniform(1, 4) * (k + 1); y += amp / (k + 1) * np.sin(2 * np.pi * f * x + R.uniform(0, 6.3))
    return (y * H).astype(np.int32)


def fill_below(img, ys, color, soft=2):
    yy = np.arange(H)[:, None]; m = np.clip((yy - ys[None, :]) / soft, 0, 1)[..., None]
    img[:] = img * (1 - m) + color * m


def vignette(strength=.45):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32); d = ((x / W - .5) ** 2 * 1.2 + (y / H - .5) ** 2 * 1.6)
    return (1 - strength * np.clip(d * 1.8, 0, 1) ** 1.3)[..., None].astype(np.float32)


class Stars:
    def __init__(s, R, n, ymax=.6, size=(0.5, 1.6)):
        s.x = R.uniform(0, W, n); s.y = R.uniform(0, H * ymax, n) ** 1.0; s.r = R.uniform(*size, n); s.b = R.uniform(.3, 1, n) ** 2
        s.w = R.uniform(.3, 1.4, n); s.p = R.uniform(0, 6.3, n); s.c = [hexc(R.choice(['#ffffff', '#fff3d6', '#dfe8ff'])) for _ in range(n)]
    def draw(s, img, t, a=1.0):
        tw = .55 + .45 * np.sin(s.w * t * 2 * math.pi / 6 + s.p)
        for i in range(len(s.x)): blit(img, s.x[i], s.y[i], sprite(s.r[i]), s.c[i], s.b[i] * tw[i] * a)


def moon(img, cx, cy, r, col, glow=.35, phase=.42):
    y, x = np.ogrid[0:H, 0:W]; d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2).astype(np.float32)
    g = np.exp(-(d / (r * 5)) ** 2) * glow + np.exp(-(d / (r * 1.8)) ** 2) * glow * .6
    disc = np.clip(r - d + 1, 0, 1)
    d2 = np.sqrt((x - cx - r * phase * 1.6) ** 2 + (y - cy + r * phase * .5) ** 2).astype(np.float32)
    cut = np.clip(r * 1.02 - d2 + 1, 0, 1) if phase > .15 else 0
    img += g[..., None] * col * .6; img[:] = img * (1 - (disc * (1 - cut))[..., None]) + col * (disc * (1 - cut))[..., None]


# ----------------------------------------------------------------------------- 장면들
class Scene:
    def __init__(s, seed, pal=None): s.R = np.random.default_rng(seed); s.vig = vignette(); s.setup()
    def frame(s, t): raise NotImplementedError


class Night(Scene):      # 밤하늘 + 초승달 + 흘러가는 구름 + 언덕
    PALS = [['#070b24', '#141a45', '#3b2f63', '#6a4a7a'], ['#050a1a', '#0f2340', '#25456a', '#4f6f8f'], ['#0a0820', '#1d1645', '#463a78', '#8a6f9c']]
    def setup(s):
        p = s.PALS[s.R.integers(len(s.PALS))]
        s.bg = vgrad([(0, p[0]), (.45, p[1]), (.78, p[2]), (1, p[3])])
        moon(s.bg, W * s.R.uniform(.62, .82), H * s.R.uniform(.16, .26), 34, hexc('#fff4d8'), .32, s.R.uniform(.25, .5))
        s.stars = Stars(s.R, 260, .7)
        s.cloud = tile_noise(H // 2, W * 2, 60, int(s.R.integers(1e6)), 4); s.cy = int(H * .3); s.taper = _taper(H // 2)
        for k, (b, a, c) in enumerate([(.78, .05, '#1a1838'), (.86, .04, '#100f26')]):
            fill_below(s.bg, ridge(int(s.R.integers(1e6)), b, a), hexc(c), 3)
    def frame(s, t):
        img = s.bg.copy(); s.stars.draw(img, t)
        off = int((t * 7) % (W * 2)); c = np.roll(s.cloud, -off, axis=1)[:, :W]
        a = np.clip((c - .52) * 3.2, 0, 1) * .38 * s.taper; y0 = s.cy - H // 4
        reg = img[y0:y0 + H // 2]; reg[:] = reg * (1 - a[..., None]) + hexc('#9a93c4') * .55 * a[..., None]
        return img * s.vig


class RainWin(Scene):    # 비 오는 창가: 흐릿한 불빛(보케) + 빗줄기 + 창에 맺힌 물방울
    def setup(s):
        s.bg = vgrad([(0, '#0d1424'), (.6, '#16233a'), (1, '#1c2333')]); R = s.R
        s.bk = [(R.uniform(0, W), R.uniform(H * .25, H), R.uniform(18, 60), hexc(R.choice(['#ffb36b', '#ffd59a', '#7fb4ff', '#ff8c7a', '#b3e0ff'])), R.uniform(.06, .2), R.uniform(0, 6.3), R.uniform(.05, .15)) for _ in range(46)]
        s.drops = [(R.uniform(0, W), R.uniform(0, H), R.uniform(500, 820), R.uniform(.05, .12), R.uniform(14, 34)) for _ in range(220)]
        s.beads = [(R.uniform(0, W), R.uniform(0, H), R.uniform(1.2, 3.2), R.uniform(.15, .45)) for _ in range(160)]
        s.slide = [(R.uniform(0, W), R.uniform(0, H), R.uniform(8, 24), R.uniform(2, 3.5)) for _ in range(14)]
        s.streak = {}
    def frame(s, t):
        img = s.bg.copy()
        for x, y, r, c, a, p, w in s.bk: blit(img, x + 6 * math.sin(t * w + p), y, sprite(r, 4), c, a * (.8 + .2 * math.sin(t * w * 2 + p)))
        for x, y, v, a, L in s.drops:
            yy = (y + v * t) % (H + 60) - 30; xx = (x - .12 * v * t) % W
            k = int(L)
            if k not in s.streak:
                yy_, xx_ = np.mgrid[-k:k + 1, -2:3].astype(np.float32); s.streak[k] = np.exp(-(xx_ ** 2) / 1.2) * np.clip(1 - np.abs(yy_) / k, 0, 1)
            sp = s.streak[k]; y0, x0 = int(yy) - k, int(xx) - 2
            if 0 <= y0 and y0 + sp.shape[0] <= H and 0 <= x0 and x0 + 5 <= W: img[y0:y0 + sp.shape[0], x0:x0 + 5] += sp[..., None] * (hexc('#cfe0ff') * a)
        for x, y, r, a in s.beads: blit(img, x, y, sprite(r, 3), hexc('#dbe8ff'), a)
        for x, y, v, r in s.slide:
            yy = (y + v * t) % (H + 40) - 20
            for k in range(6): blit(img, x, yy - k * r * 1.4, sprite(r * (1 - k * .13), 3), hexc('#dbe8ff'), .35 * (1 - k / 6))
        return img * s.vig


class Sea(Scene):        # 달빛 바다: 수평선 + 반짝이는 달빛 기둥 + 별
    def setup(s):
        R = s.R; s.hz = int(H * R.uniform(.56, .64)); s.mx = W * R.uniform(.35, .65)
        s.bg = vgrad([(0, '#060b1f'), (s.hz / H * .7, '#14244a'), (s.hz / H, '#2c3f6b'), (s.hz / H + .001, '#0b1630'), (1, '#050a18')])
        moon(s.bg, s.mx, s.hz - H * R.uniform(.22, .32), 30, hexc('#fff2d0'), .4, 0)
        s.stars = Stars(R, 170, s.hz / H * .85)
        s.bw = 340; x = np.arange(int(s.mx - s.bw / 2), int(s.mx + s.bw / 2)); s.xs = np.clip(x, 0, W - 1)
        s.yy = np.arange(s.hz, H)[:, None].astype(np.float32); s.dx = (s.xs - s.mx)[None, :].astype(np.float32)
    def frame(s, t):
        img = s.bg.copy(); s.stars.draw(img, t)
        depth = (s.yy - s.hz) / (H - s.hz); width = 12 + 150 * depth
        col = np.exp(-(s.dx / width) ** 2)
        gl = (np.sin(s.yy * .9 + t * 2.1 + np.sin(s.dx * .05 + t * .7) * 2) * .5 + .5) ** 6
        gl2 = (np.sin(s.yy * .35 - t * 1.3 + s.dx * .02) * .5 + .5) ** 3
        v = col * (gl * .8 + gl2 * .3) * (1 - depth * .4) * .55
        img[s.hz:, s.xs] += v[..., None] * hexc('#ffe8b8')
        wav = (np.sin(s.yy * .25 + t * .9) * .5 + .5) ** 8 * .025 * (1 - depth)
        img[s.hz:] += wav[..., None] * hexc('#8fb0ff')
        return img * s.vig


class Firefly(Scene):    # 반딧불 숲: 겹겹이 언덕 실루엣 + 떠다니는 반딧불
    def setup(s):
        R = s.R; s.bg = vgrad([(0, '#04121a'), (.5, '#0b2a33'), (.8, '#123c3d'), (1, '#0a1f22')])
        s.stars = Stars(R, 90, .4, (.5, 1.1))
        for b, a, c in [(.55, .05, '#0d2c33'), (.66, .05, '#0a2229'), (.78, .04, '#06171c'), (.9, .03, '#030c0f')]: fill_below(s.bg, ridge(int(R.integers(1e6)), b, a, 4), hexc(c), 2)
        n = 60; s.f = [(R.uniform(0, W), R.uniform(H * .45, H * .95), R.uniform(20, 70), R.uniform(10, 40), R.uniform(.04, .12), R.uniform(.03, .1), R.uniform(0, 6.3), R.uniform(0, 6.3), R.uniform(.15, .45), R.uniform(2.2, 4.5)) for _ in range(n)]
    def frame(s, t):
        img = s.bg.copy(); s.stars.draw(img, t, .7)
        for x, y, ax, ay, wx, wy, px, py, wb, r in s.f:
            b = max(0, math.sin(t * wb * 2 * math.pi / 3 + px)) ** 2
            X = x + ax * math.sin(t * wx * 2 * math.pi / 3 + px); Y = y + ay * math.sin(t * wy * 2 * math.pi / 3 + py)
            blit(img, X, Y, sprite(r * 6, 2), hexc('#b8ff6a'), .16 * b); blit(img, X, Y, sprite(r * 1.1, 2), hexc('#f2ffc0'), .95 * b)
        return img * s.vig


class Snow(Scene):       # 눈 오는 밤: 3겹 눈송이 + 눈 덮인 언덕 + 멀리 따뜻한 창불
    def setup(s):
        R = s.R; s.bg = vgrad([(0, '#0b1430'), (.55, '#22325c'), (.75, '#3b4b78'), (1, '#4a5a86')])
        moon(s.bg, W * R.uniform(.15, .35), H * .18, 26, hexc('#f6f2ff'), .25, R.uniform(0, .4))
        fill_below(s.bg, ridge(int(R.integers(1e6)), .72, .04), hexc('#9fb0d6'), 3); fill_below(s.bg, ridge(int(R.integers(1e6)), .83, .03), hexc('#c9d4ee'), 3)
        wx, wy = W * R.uniform(.55, .8), H * .76; blit(s.bg, wx, wy, sprite(26, 2), hexc('#ffb35a'), .35); blit(s.bg, wx, wy, sprite(4, 6), hexc('#ffd48a'), .9)
        s.fl = [(R.uniform(0, W), R.uniform(0, H), d, R.uniform(.6, 1.6) * d, R.uniform(14, 32) * d, R.uniform(.2, .6), R.uniform(0, 6.3)) for d in (0.5, 1.0, 1.7) for _ in range({.5: 220, 1.0: 140, 1.7: 45}[d])]
    def frame(s, t):
        img = s.bg.copy()
        for x, y, d, r, v, w, p in s.fl:
            yy = (y + v * t) % (H + 20) - 10; xx = (x + 18 * d * math.sin(t * w + p) + 6 * d * t) % W
            blit(img, xx, yy, sprite(r * 1.2, 2), hexc('#ffffff'), .55 if d > .6 else .35)
        return img * s.vig


class Aurora(Scene):     # 오로라: 천천히 일렁이는 빛의 커튼 + 별 + 설산 실루엣
    def setup(s):
        R = s.R; s.bg = vgrad([(0, '#020611'), (.6, '#06142a'), (1, '#0b1d33')]); s.stars = Stars(R, 220, .75)
        s.tex = tile_noise(64, W * 2, 90, int(R.integers(1e6)), 3); s.y = np.linspace(0, 1, int(H * .62), dtype=np.float32)[:, None]
        s.c1, s.c2 = hexc(R.choice(['#3dffb0', '#4cf0c8', '#7dff9a'])), hexc(R.choice(['#7a5cff', '#3fa0ff', '#c46bff']))
        s.fg = np.zeros((H, W, 3), np.float32); s.mask = np.zeros((H, W, 1), np.float32)
        tmp = s.bg.copy(); fill_below(tmp, ridge(int(R.integers(1e6)), .8, .06, 5), hexc('#050b14'), 2)
        s.mask = (np.abs(tmp - s.bg).sum(-1, keepdims=True) > 1e-4).astype(np.float32); s.ground = tmp
    def frame(s, t):
        img = s.bg.copy(); s.stars.draw(img, t)
        off = (t * 10) % (W * 2); xs = (np.arange(W) + off).astype(np.int32) % (W * 2)
        band = s.tex[:, xs]; top = .18 + .14 * band[10] + .05 * np.sin(np.arange(W) / W * 6.28 * 2 + t * .2)
        k = int(s.y.shape[0]); y = s.y
        d = y - top[None]; rays = .35 + .65 * band[50][None] ** 1.5
        curtain = np.where(d < 0, np.exp(-(d / .035) ** 2), np.exp(-d / (.18 + .12 * band[30][None]))) * rays * np.clip((1 - y) / .35, 0, 1) ** 2
        col = s.c1 * (1 - y[..., None]) + s.c2 * y[..., None]
        img[:k] += curtain[..., None] * col * .5
        img = img * (1 - s.mask) + s.ground * s.mask
        return img * s.vig


class Pastel(Scene):     # 파스텔 구름 위 (아이용): 분홍·라벤더 하늘 + 몽글몽글 구름 + 반짝이
    def setup(s):
        R = s.R; s.bg = vgrad([(0, '#9fb7e8'), (.45, '#c6b6e6'), (.8, '#f2c6d8'), (1, '#ffe1d0')])
        moon(s.bg, W * R.uniform(.65, .85), H * .2, 30, hexc('#fffaf0'), .25, .45)
        s.taper = _taper(H // 2); s.stars = Stars(R, 60, .5, (.6, 1.6)); s.layers = [(tile_noise(H // 2, W * 2, 70, int(R.integers(1e6)), 4), int(H * yo), sp, a) for yo, sp, a in ((.35, 5, .5), (.62, 9, .75), (.85, 14, .95))]
    def frame(s, t):
        img = s.bg.copy(); s.stars.draw(img, t, .8)
        for tex, cy, sp, a in s.layers:
            off = int((t * sp) % (W * 2)); c = np.roll(tex, -off, axis=1)[:, :W]
            m = np.clip((c - .5) * 4, 0, 1) * a * s.taper; y0 = max(0, cy - H // 4); reg = img[y0:y0 + H // 2]; mm = m[:reg.shape[0], :, None]
            shade = .92 + .08 * np.clip((c[:reg.shape[0]] - .5) * 3, 0, 1)[..., None]
            reg[:] = reg * (1 - mm) + hexc('#fff6fb') * shade * mm
        return img * s.vig


class Warm(Scene):       # 따뜻한 불빛: 주황·호박색 보케가 천천히 떠오름 (엄마 뱃속·장작)
    def setup(s):
        R = s.R; s.bg = vgrad([(0, '#1a0a06'), (.6, '#33140a'), (1, '#45200f')])
        s.b = [(R.uniform(0, W), R.uniform(0, H), R.uniform(25, 90), hexc(R.choice(['#ff9a4a', '#ffbf6e', '#ff6f3c', '#ffd9a0'])), R.uniform(.05, .16), R.uniform(4, 14), R.uniform(0, 6.3)) for _ in range(40)]
    def frame(s, t):
        img = s.bg.copy()
        for x, y, r, c, a, v, p in s.b:
            yy = (y - v * t) % (H + 2 * r) - r
            blit(img, x + 12 * math.sin(t * .1 + p), yy, sprite(r, 4), c, a * (.75 + .25 * math.sin(t * .4 + p)))
        return img * s.vig


SCENES = {'night': Night, 'rainwin': RainWin, 'sea': Sea, 'firefly': Firefly, 'snow': Snow, 'aurora': Aurora, 'pastel': Pastel, 'warm': Warm}


# ----------------------------------------------------------------------------- 인코딩
def _dither():
    R = np.random.default_rng(5); return (R.random((H, W, 3)).astype(np.float32) - .5) / 255 * 1.6


def render_segment(args):
    """장면 k (seg초) — 끝 xf초 동안 다음 장면으로 서서히 바뀜. 파일 하나로 인코딩"""
    k, names, seed, seg, xf, out, crf, maxrate = args
    a = SCENES[names[k]](seed + k * 101); b = SCENES[names[(k + 1) % len(names)]](seed + ((k + 1) % len(names)) * 101)
    dt = _dither(); n = int(seg * FPS)
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-vf', 'scale=1920:1080:flags=lanczos', '-c:v', 'libx264', '-preset', 'medium', '-crf', str(crf), '-x264-params', 'aq-mode=3:keyint=96:min-keyint=96', '-maxrate', maxrate, '-bufsize', '3000k',
                           '-pix_fmt', 'yuv420p', '-an', out], stdin=subprocess.PIPE)
    for i in range(n):
        t = i / FPS; f = a.frame(t)
        if t > seg - xf:
            u = (t - (seg - xf)) / xf; u = u * u * (3 - 2 * u); f = f * (1 - u) + b.frame(t - seg) * u
        ff.stdin.write((np.clip(f + dt, 0, 1) * 255).astype(np.uint8).tobytes())
    ff.stdin.close(); ff.wait(); return out


def make_loop(names, seed, path, seg=90.0, xf=6.0, crf=21, procs=None, maxrate='1500k'):
    """장면들을 이어 붙인 끊김 없는 루프 영상 (len(names)*seg 초)"""
    from multiprocessing import Pool
    parts = [f'{path}.part{k}.mp4' for k in range(len(names))]
    jobs = [(k, names, seed, seg, xf, parts[k], crf, maxrate) for k in range(len(names))]
    with Pool(procs or min(len(names), os.cpu_count() or 2)) as p: p.map(render_segment, jobs)
    lst = f'{path}.txt'; open(lst, 'w').write(''.join(f"file '{os.path.abspath(x)}'\n" for x in parts))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', path], check=True)
    for x in parts + [lst]: os.remove(x)
    return path


def still(name, seed, t=20.0):
    return np.clip(SCENES[name](seed).frame(t), 0, 1)
