#!/usr/bin/env python3
"""잔잔한 배경 영상 v2 — 외부 이미지·영상 0개, 전부 수학으로 그림.
장면 14종:
  night 밤하늘 · rainwin 비 오는 창 · sea 달빛 바다 · firefly 반딧불 숲 · snow 눈 오는 밤 · aurora 오로라 · pastel 파스텔 구름 · warm 따뜻한 불빛
  eaves 처마에서 떨어지는 빗방울 · storm 번개 치는 비 오는 창 · nursery 아기 방(흔들의자·모빌) · stream 달빛 시냇물 · candle 촛불 · study 늦은 밤 서재(괘종시계)
질감: 필름 그레인 · 블룸(빛 번짐) · 색 보정 · 천천히 움직이는 카메라 · 비네트
· 장면 4개를 90초씩 이어 붙이고 6초 동안 서서히 바뀜 → 6분짜리 '끊김 없는 루프' → 1시간으로 반복(재인코딩 없이 복사)
"""
import math, os, subprocess
import numpy as np
from scipy.ndimage import gaussian_filter, zoom as _zoom

W, H = 1280, 720            # 계산 해상도 (출력은 1920x1080 으로 확대)
CW, CH = 1248, 702          # 카메라가 천천히 움직이며 잘라내는 창 (16:9)
FPS = 24


def hexc(h): h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


def vgrad(stops, h=H, w=W):
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


def vline(img, x, y0, y1, color, a=1.0, w=1):
    """세로 선분 (물방울 궤적용) — 양 끝이 부드럽게"""
    if not (np.isfinite(y0) and np.isfinite(y1)): return
    y0, y1 = int(y0), int(y1)
    if y1 <= y0: return
    ya, yb = max(0, y0), min(H, y1)
    if yb <= ya: return
    xi = int(x); xa, xb = max(0, xi - w), min(W, xi + w + 1)
    if xb <= xa: return
    k = np.linspace(0, 1, y1 - y0, dtype=np.float32)[ya - y0:yb - y0]; prof = (np.clip(np.sin(k * np.pi), 0, 1) ** .5)[:, None, None]
    img[ya:yb, xa:xb] += prof * color * a


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


def poly_mask(pts, blur=0.0):
    """다각형 실루엣 마스크 (0~1) — PIL로 그린 뒤 살짝 흐림"""
    from PIL import Image, ImageDraw
    im = Image.new('L', (W, H), 0); ImageDraw.Draw(im).polygon([(float(x), float(y)) for x, y in pts], fill=255)
    m = np.asarray(im, np.float32) / 255
    return gaussian_filter(m, blur) if blur else m


def chaikin(pts, it=3):
    """다각형 모서리를 둥글게 (실루엣을 사람·가구처럼 부드럽게)"""
    P = np.array(pts, np.float32)
    for _ in range(it):
        Q = np.roll(P, -1, axis=0); P = np.stack([P * .75 + Q * .25, P * .25 + Q * .75], 1).reshape(-1, 2)
    return [tuple(p) for p in P]


def ellipse_mask(cx, cy, rx, ry, blur=0.0):
    from PIL import Image, ImageDraw
    im = Image.new('L', (W, H), 0); ImageDraw.Draw(im).ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
    m = np.asarray(im, np.float32) / 255
    return gaussian_filter(m, blur) if blur else m


def shapes_mask(draw_fn, blur=0.0):
    """draw_fn(ImageDraw) 로 자유롭게 그린 실루엣 마스크"""
    from PIL import Image, ImageDraw
    im = Image.new('L', (W, H), 0); draw_fn(ImageDraw.Draw(im))
    m = np.asarray(im, np.float32) / 255
    return gaussian_filter(m, blur) if blur else m


def composite(img, mask, color):
    m = mask[..., None]; img[:] = img * (1 - m) + color * m


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


def bokeh_layer(R, n, ymin, ymax, rr, cols, amin, amax):
    return [(R.uniform(0, W), R.uniform(ymin, ymax), R.uniform(*rr), hexc(R.choice(cols)), R.uniform(amin, amax), R.uniform(0, 6.3), R.uniform(.05, .15)) for _ in range(n)]


def draw_bokeh(img, bk, t, sway=6):
    for x, y, r, c, a, p, w in bk: blit(img, x + sway * math.sin(t * w + p), y, sprite(r, 4), c, a * (.8 + .2 * math.sin(t * w * 2 + p)))


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
        s.mist = tile_noise(H // 4, W * 2, 40, int(s.R.integers(1e6)), 2)
    def frame(s, t):
        img = s.bg.copy(); s.stars.draw(img, t)
        off = int((t * 7) % (W * 2)); c = np.roll(s.cloud, -off, axis=1)[:, :W]
        a = np.clip((c - .52) * 3.2, 0, 1) * .38 * s.taper; y0 = s.cy - H // 4
        reg = img[y0:y0 + H // 2]; reg[:] = reg * (1 - a[..., None]) + hexc('#9a93c4') * .55 * a[..., None]
        off = int((t * 3) % (W * 2)); m = np.roll(s.mist, -off, axis=1)[:, :W]; reg = img[H * 3 // 4:]   # 언덕 아래 안개
        reg += (np.clip((m - .4) * 1.5, 0, 1) * .07 * np.linspace(1, 0, H // 4)[:, None])[..., None] * hexc('#aab0ff')
        return img * s.vig


class RainWin(Scene):    # 비 오는 창가: 흐릿한 불빛(보케) + 빗줄기 + 창에 맺힌 물방울(굴절 느낌)
    def setup(s):
        s.bg = vgrad([(0, '#0d1424'), (.6, '#16233a'), (1, '#1c2333')]); R = s.R
        s.bk = bokeh_layer(R, 46, H * .25, H, (18, 60), ['#ffb36b', '#ffd59a', '#7fb4ff', '#ff8c7a', '#b3e0ff'], .06, .2)
        s.drops = [(R.uniform(0, W), R.uniform(0, H), R.uniform(500, 820), R.uniform(.05, .12), R.uniform(14, 34)) for _ in range(220)]
        s.beads = [(R.uniform(0, W), R.uniform(0, H), R.uniform(1.4, 4.0), R.uniform(.2, .5)) for _ in range(170)]
        s.slide = [(R.uniform(0, W), R.uniform(0, H), R.uniform(8, 24), R.uniform(2, 3.5), R.uniform(0, 6.3)) for _ in range(16)]
        s.streak = {}
    def frame(s, t):
        img = s.bg.copy(); draw_bokeh(img, s.bk, t)
        for x, y, v, a, L in s.drops:
            yy = (y + v * t) % (H + 60) - 30; xx = (x - .12 * v * t) % W
            k = int(L)
            if k not in s.streak:
                yy_, xx_ = np.mgrid[-k:k + 1, -2:3].astype(np.float32); s.streak[k] = np.exp(-(xx_ ** 2) / 1.2) * np.clip(1 - np.abs(yy_) / k, 0, 1)
            sp = s.streak[k]; y0, x0 = int(yy) - k, int(xx) - 2
            if 0 <= y0 and y0 + sp.shape[0] <= H and 0 <= x0 and x0 + 5 <= W: img[y0:y0 + sp.shape[0], x0:x0 + 5] += sp[..., None] * (hexc('#cfe0ff') * a)
        for x, y, r, a in s.beads:   # 유리에 맺힌 물방울: 아래쪽 그늘 + 위쪽 하이라이트 (렌즈처럼)
            blit(img, x + r * .4, y + r * .5, sprite(r * 1.3, 3), hexc('#000000'), -a * .5)
            blit(img, x, y, sprite(r, 3), hexc('#dbe8ff'), a * .6); blit(img, x - r * .35, y - r * .4, sprite(r * .35, 4), hexc('#ffffff'), a)
        for x, y, v, r, p in s.slide:  # 흘러내리는 물줄기: 좌우로 살짝 흔들리며
            yy = (y + v * t) % (H + 40) - 20; xs = x + 3 * math.sin(t * .8 + p)
            for k in range(7): blit(img, xs + 1.5 * math.sin(k + t), yy - k * r * 1.4, sprite(r * (1 - k * .12), 3), hexc('#dbe8ff'), .35 * (1 - k / 7))
            blit(img, xs - r * .3, yy - r * .3, sprite(r * .3, 4), hexc('#ffffff'), .6)
        return img * s.vig


class Storm(RainWin):    # 번개 치는 비 오는 창: 20~45초마다 멀리서 번쩍, 2~3번 깜빡임
    def setup(s):
        super().setup(); R = s.R; s.flash = []; tt = R.uniform(8, 20)
        while tt < 400: s.flash.append((tt, R.uniform(.25, .7), [R.uniform(0, .5) for _ in range(int(R.integers(2, 4)))])); tt += R.uniform(20, 45)
        s.sky = np.linspace(1, 0, H, dtype=np.float32)[:, None, None] ** .7
    def frame(s, t):
        img = super().frame(t) / s.vig; lv = 0.0
        for t0, amp, subs in s.flash:
            for dt in subs:
                d = t - t0 - dt
                if 0 <= d < .35: lv = max(lv, amp * (math.exp(-d / .06) + .3 * math.exp(-d / .25)))
        if lv > 0: img += (hexc('#cfd8ff') * lv * .9 * s.sky * (1 - .5 * np.clip(img, 0, 1)))
        return img * s.vig


class Eaves(Scene):      # 한옥 처마: 기와 골마다 빗방울이 맺혀 떨어지고, 몇 줄기는 낙숫물로 이어져 흐름 → 젖은 마당에 파문
    TP = 34                                                           # 기와 골 간격(px)
    def setup(s):
        R = s.R; s.yy, s.xx = np.mgrid[0:H, 0:W].astype(np.float32)
        s.bg = vgrad([(0, '#070b16'), (.35, '#0e1628'), (.7, '#16223a'), (1, '#0a101c')])
        s.bk = bokeh_layer(R, 30, H * .3, H * .7, (16, 46), ['#ffb36b', '#ffd59a', '#7fb4ff', '#ffe0b0'], .04, .13)
        for b, a, c in [(.62, .03, '#0c1626'), (.70, .025, '#09111d')]: fill_below(s.bg, ridge(int(R.integers(1e6)), b, a, 5), hexc(c), 4)   # 마당 너머 나무·담장
        s.py = int(H * .79)                                            # 젖은 마당 시작
        # 처마 지붕: 아래 가장자리가 수막새처럼 둥글게 이어짐
        TP = s.TP; s.off = float(R.uniform(0, TP)); xs = np.arange(W, dtype=np.float32)
        s.base = int(H * .19); ph = ((xs + s.off) % TP) / TP
        s.edge = (s.base + 9 * np.sin(np.pi * ph) ** .6).astype(np.float32)          # 막새 둥근 끝
        m = (s.yy < s.edge[None, :]).astype(np.float32); s.roof_m = gaussian_filter(m, .8)
        ridgeshade = .55 + .45 * np.cos(2 * np.pi * ((xs + s.off) / TP))[None, :] ** 2   # 골·등 음영
        s.roof_col = (hexc('#0b0d12')[None, None, :] * (.7 + .5 * ridgeshade[..., None]) + tile_noise(H, W, 6, int(R.integers(1e6)), 2)[..., None] * .03).astype(np.float32)
        s.wet = np.clip(1 - np.abs(s.yy - s.edge[None, :] + 2) / 3, 0, 1) * (.6 + .4 * ridgeshade)   # 젖어서 빛나는 가장자리
        # 서까래 끝(둥근 나무 끝) 줄
        s.raft = np.zeros((H, W), np.float32)
        for x in np.arange(-s.off + TP / 2, W, TP * 1.0): s.raft += ellipse_mask(float(x), s.base - 16, 7, 7, .8)
        s.raft = s.raft.clip(0, 1)
        # 왼쪽 나무 기둥 + 오른쪽 창호지 문(따뜻한 불빛)
        s.pil = shapes_mask(lambda d: d.rectangle([int(W * .06), s.base - 10, int(W * .06) + 38, H], fill=255), 1.0)
        dx0, dy0, dw, dh = int(W * .74), int(H * .50), int(W * .14), int(H * .29); s.door = (dx0, dy0, dw, dh)
        s.door_m = shapes_mask(lambda d: d.rectangle([dx0, dy0, dx0 + dw, dy0 + dh], fill=255), 1.0)
        lat = np.zeros((H, W), np.float32)
        for k in range(1, 4): lat[dy0:dy0 + dh, dx0 + k * dw // 4 - 1:dx0 + k * dw // 4 + 1] = 1
        for k in range(1, 6): lat[dy0 + k * dh // 6 - 1:dy0 + k * dh // 6 + 1, dx0:dx0 + dw] = 1
        lat[dy0:dy0 + 4, dx0:dx0 + dw] = 1; lat[dy0 + dh - 4:dy0 + dh, dx0:dx0 + dw] = 1; lat[dy0:dy0 + dh, dx0:dx0 + 4] = 1; lat[dy0:dy0 + dh, dx0 + dw - 4:dx0 + dw] = 1
        s.lat = gaussian_filter(lat, .6) * s.door_m
        s.paper = tile_noise(H, W, 3, int(R.integers(1e6)), 1)
        # 빗방울 떨어지는 골 위치 (골마다 주기·크기 다르게) + 낙숫물 줄기 3개
        valleys = [float(x) for x in np.arange(-s.off, W + TP, TP) if 0 < x < W]
        s.dr = [(x, float(R.uniform(1.6, 4.5)), float(R.uniform(0, 6.5)), float(R.uniform(3.0, 4.8))) for x in valleys]
        s.pour = [valleys[i] for i in R.choice(len(valleys), 3, replace=False)]
        s.dr = [d for d in s.dr if d[0] not in s.pour]
        s.drops = [(R.uniform(0, W), R.uniform(0, H), R.uniform(420, 640), R.uniform(.03, .07), R.uniform(10, 22)) for _ in range(150)]
        s.streak = {}; s.mist = tile_noise(H // 3, W * 2, 50, int(R.integers(1e6)), 2)
        s.gtex = tile_noise(H - s.py, W, 10, int(R.integers(1e6)), 3)
    def _ripple(s, img, cx, cy, age, size=1.0):
        rx = (8 + 80 * age) * size; ry = rx * .26; a = (1 - age) ** 1.6 * .55
        if a < .01: return
        x0, x1 = max(0, int(cx - rx - 3)), min(W, int(cx + rx + 4)); y0, y1 = max(0, int(cy - ry - 3)), min(H, int(cy + ry + 4))
        if x1 <= x0 or y1 <= y0: return
        d = np.sqrt(((s.xx[y0:y1, x0:x1] - cx) / rx) ** 2 + ((s.yy[y0:y1, x0:x1] - cy) / ry) ** 2)
        ring = np.exp(-((d - 1) * rx / 2.0) ** 2) + .5 * np.exp(-((d - .55) * rx / 2.0) ** 2) * (age > .2)
        img[y0:y1, x0:x1] += (ring * a)[..., None] * hexc('#b8cdf0')
    def frame(s, t):
        img = s.bg.copy(); draw_bokeh(img, s.bk, t, 3)
        for x, y, v, a, L in s.drops:                                  # 마당 너머 빗줄기
            yy = (y + v * t) % (H + 60) - 30; xx = (x - .08 * v * t) % W; k = int(L)
            if k not in s.streak:
                yy_, xx_ = np.mgrid[-k:k + 1, -1:2].astype(np.float32); s.streak[k] = np.exp(-(xx_ ** 2) / 1.0) * np.clip(1 - np.abs(yy_) / k, 0, 1)
            sp = s.streak[k]; y0, x0 = int(yy) - k, int(xx) - 1
            if 0 <= y0 and y0 + sp.shape[0] <= H and 0 <= x0 and x0 + 3 <= W: img[y0:y0 + sp.shape[0], x0:x0 + 3] += sp[..., None] * (hexc('#c4d4f4') * a)
        off = int((t * 4) % (W * 2)); m = np.roll(s.mist, -off, axis=1)[:, :W]
        img[H // 3:H * 2 // 3] += (np.clip((m - .45) * 1.4, 0, 1) * .06)[..., None] * hexc('#9fb4e0')
        # 창호지 문: 따뜻한 빛 (아주 천천히 일렁)
        dx0, dy0, dw, dh = s.door; fl = 1 + .03 * math.sin(t * 1.7) + .02 * math.sin(t * 4.3)
        glow = hexc('#e8a560') * (.36 + .08 * s.paper[..., None]) * (1 - .35 * ((s.yy - dy0) / dh).clip(0, 1))[..., None] * fl
        img[:] = img * (1 - s.door_m[..., None]) + glow * s.door_m[..., None]
        img[:] = img * (1 - s.lat[..., None] * .85) + hexc('#2a1a0e') * s.lat[..., None] * .85
        dd = np.sqrt(((s.xx - (dx0 + dw / 2)) / (dw * .9)) ** 2 + ((s.yy - (dy0 + dh / 2)) / (dh * .9)) ** 2)
        img += (np.exp(-np.clip(dd - .6, 0, 9) * 2.2) * .18 * (1 - s.door_m))[..., None] * hexc('#ff9a4a') * fl
        # 젖은 마당: 위쪽(문 불빛·보케)의 뒤집힌 반사 + 물결 흔들림 + 돌 질감
        n = H - s.py; src = img[s.py - n:s.py][::-1]
        wob = .5 + .5 * np.sin(s.yy[s.py:] * .45 + t * 1.6 + s.gtex * 8)
        img[s.py:] = src * (.38 + .12 * wob[..., None]) + hexc('#0a101a') * (.3 + .1 * s.gtex[..., None])
        # 기둥
        img[:] = img * (1 - s.pil[..., None]) + (hexc('#1a120c') + np.exp(-((s.xx - W * .06 - 30) / 12) ** 2)[..., None] * hexc('#3a2818') * .6) * s.pil[..., None]
        # 지붕 + 서까래 + 젖은 가장자리 반짝임
        img[:] = img * (1 - s.roof_m[..., None]) + s.roof_col * s.roof_m[..., None]
        img[:] = img * (1 - s.raft[..., None] * .9) + hexc('#2a1c12') * s.raft[..., None] * .9
        img += (s.wet * .22)[..., None] * hexc('#9fbaff')
        g = 1400.0
        # 낙숫물 줄기: 이어지는 물줄기 (출렁이며 가늘어졌다 굵어졌다)
        for x in s.pour:
            y0 = s.base + 4; yb = s.py
            for k, yy in enumerate(range(int(y0), yb, 3)):
                w = 1.3 + .7 * math.sin(yy * .09 - t * 22 + x)
                xo = 1.5 * math.sin(yy * .03 + t * 3 + x)
                blit(img, x + xo, yy, sprite(w, 3), hexc('#cfe0ff'), .28)
            blit(img, x, s.py + 1, sprite(9, 2), hexc('#dfeaff'), .25)
            for j in range(2): s._ripple(img, x, s.py + 3, ((t * 1.3 + j * .5 + x * .01) % 1.0), .7)
        # 빗방울: 맺힘 → 낙하(꼬리) → 착수 파문 + 튀는 물방울
        for x, per, ph, rmax in s.dr:
            u = ((t + ph) % per) / per; y_top = s.base + 6; grow = .6
            if u < grow:
                r = .8 + (rmax - .8) * (u / grow) ** 1.7; yd = y_top + r * 1.1
                blit(img, x, yd, sprite(r, 3), hexc('#c9dcff'), .6); blit(img, x - r * .35, yd - r * .35, sprite(max(.6, r * .32), 4), hexc('#ffffff'), .9)
            else:
                tf = (u - grow) * per; y = y_top + rmax + .5 * g * tf * tf; v = g * tf
                if y < s.py:
                    L = min(46, v / FPS * 1.1 + 3); vline(img, x, y - L, y, hexc('#d6e4ff'), .5 * min(1, rmax / 3)); blit(img, x, y, sprite(rmax * .8, 3), hexc('#e4eeff'), .85)
                    blit(img, x - rmax * .3, y - rmax * .3, sprite(rmax * .3, 4), hexc('#ffffff'), .8)
                else:
                    t_hit = math.sqrt(max(0.0, 2 * (s.py - y_top - rmax) / g)); age = (tf - t_hit) / 1.3
                    if 0 <= age < 1:
                        s._ripple(img, x, s.py + 4, age, rmax / 3.4)
                        a2 = age * 2.4
                        if a2 < 1:
                            for j in (-1, 0, 1): blit(img, x + j * 13 * a2, s.py + 2 - 24 * a2 * (1 - a2) * 2 * (1 - .3 * abs(j)), sprite(1.3, 3), hexc('#e4eeff'), .7 * (1 - a2))
        return img * s.vig


class Sea(Scene):        # 달빛 바다: 수평선 + 반짝이는 달빛 기둥 + 별
    def setup(s):
        R = s.R; s.hz = int(H * R.uniform(.56, .64)); s.mx = W * R.uniform(.35, .65)
        s.bg = vgrad([(0, '#060b1f'), (s.hz / H * .7, '#14244a'), (s.hz / H, '#2c3f6b'), (s.hz / H + .001, '#0b1630'), (1, '#050a18')])
        moon(s.bg, s.mx, s.hz - H * R.uniform(.22, .32), 30, hexc('#fff2d0'), .4, 0)
        s.stars = Stars(R, 170, s.hz / H * .85)
        s.bw = 340; x = np.arange(int(s.mx - s.bw / 2), int(s.mx + s.bw / 2)); s.xs = np.clip(x, 0, W - 1)
        s.yy = np.arange(s.hz, H)[:, None].astype(np.float32); s.dx = (s.xs - s.mx)[None, :].astype(np.float32)
        s.cloud = tile_noise(H // 3, W * 2, 70, int(R.integers(1e6)), 3); s.taper = _taper(H // 3)
    def frame(s, t):
        img = s.bg.copy(); s.stars.draw(img, t)
        off = int((t * 4) % (W * 2)); c = np.roll(s.cloud, -off, axis=1)[:, :W]; a = np.clip((c - .55) * 3, 0, 1) * .25 * s.taper
        reg = img[:H // 3]; reg[:] = reg * (1 - a[..., None]) + hexc('#8e95c8') * .5 * a[..., None]
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


class Candle(Scene):     # 촛불: 일렁이는 불꽃 + 따뜻한 방 + 떠다니는 먼지
    def setup(s):
        R = s.R; s.bg = vgrad([(0, '#0a0604'), (.6, '#1a0e08'), (1, '#120906')]); s.cx, s.cy = float(W * R.uniform(.3, .7)), int(H * .62)
        s.yy, s.xx = np.mgrid[0:H, 0:W].astype(np.float32)
        s.cand = shapes_mask(lambda d: d.rounded_rectangle([s.cx - 22, s.cy, s.cx + 22, s.cy + 150], 8, fill=255), 1.0)
        s.wax = tile_noise(H, W, 12, int(R.integers(1e6)), 2)
        s.hold = shapes_mask(lambda d: (d.ellipse([s.cx - 70, s.cy + 140, s.cx + 70, s.cy + 170], fill=255)), 1.0)
        s.dust = [(R.uniform(0, W), R.uniform(0, H), R.uniform(.6, 1.3), R.uniform(2, 6), R.uniform(0, 6.3), R.uniform(.1, .3)) for _ in range(70)]
        s.bk = bokeh_layer(R, 14, H * .2, H * .9, (30, 80), ['#ff9a4a', '#ffbf6e', '#ffd9a0'], .02, .06)
        s.fn = np.random.default_rng(int(R.integers(1e6))).standard_normal(4000).astype(np.float32)
        from scipy.ndimage import gaussian_filter1d; s.fn = gaussian_filter1d(s.fn, 2.0); s.fn /= np.abs(s.fn).max()
    def frame(s, t):
        img = s.bg.copy(); draw_bokeh(img, s.bk, t, 2)
        k = int(t * 30) % len(s.fn); fl = s.fn[k]; fl2 = s.fn[(k + 700) % len(s.fn)]
        br = 1 + .22 * fl                                                # 불꽃 세기 흔들림
        y, x = s.yy, s.xx; d = np.sqrt((x - s.cx) ** 2 + (y - s.cy) ** 2)
        img += (np.exp(-(d / 260) ** 2) * .35 * br + np.exp(-(d / 90) ** 2) * .5 * br)[..., None] * hexc('#ff9a3c')
        img[s.cy:] *= 1 - (np.clip((y[s.cy:] - s.cy) / 120, 0, 1) * .25)[..., None]   # 촛대 아래 그림자
        composite(img, s.hold, hexc('#2a1a10')); composite(img, s.cand, hexc('#f0e0c0') * (.55 + .25 * s.wax[..., None] * 0 + .2 * (1 - np.clip((y - s.cy) / 150, 0, 1))[..., None]))
        img += (s.cand * np.exp(-((x - s.cx) / 30) ** 2) * np.exp(-((y - s.cy) / 50) ** 2) * .5 * br)[..., None] * hexc('#ffc070')
        # 불꽃: 눈물 모양 (가우시안 여러 개), 바람에 살짝 기울고 떨림
        tilt = 6 * fl2; h = 42 * (1 + .12 * fl)
        for yy, rr, col, a in ((-10, 9, '#ffe9b0', .9), (-20, 7, '#ffd070', 1.0), (-32, 5, '#ffb040', .9), (-44, 3.2, '#ff8030', .7), (-6, 4, '#3a66ff', .35)):
            yy = yy * h / 42; blit(img, s.cx + tilt * (-yy / 44), s.cy + yy, sprite(rr, 2.2), hexc(col), a)
        blit(img, s.cx, s.cy - 2, sprite(2.2, 3), hexc('#201008'), .9)      # 심지
        for x0, y0, r, v, p, a in s.dust:
            yy = (y0 - v * t) % (H + 10) - 5; xx = (x0 + 14 * math.sin(t * .25 + p)) % W
            blit(img, xx, yy, sprite(r, 2), hexc('#ffd9a0'), a * (.5 + .5 * math.sin(t * 1.3 + p)) * min(1, 300 / (abs(xx - s.cx) + abs(yy - s.cy) + 1)))
        return img * s.vig


class Nursery(Scene):    # 아기 방: 창밖 달 · 흔들의자에서 아기를 안고 흔드는 엄마 실루엣 · 천천히 도는 모빌 · 야간등
    def setup(s):
        R = s.R; s.bg = vgrad([(0, '#120b1c'), (.6, '#1d1230'), (1, '#120a18')]); s.yy, s.xx = np.mgrid[0:H, 0:W].astype(np.float32)
        # 창문 (왼쪽): 밤하늘 + 달 + 커튼
        s.wx0, s.wy0, s.ww, s.wh = int(W * .08), int(H * .12), int(W * .26), int(H * .5)
        sky = vgrad([(0, '#0a1230'), (1, '#2a2a5a')], s.wh, s.ww); R2 = np.random.default_rng(int(R.integers(1e6)))
        s.sky = sky; s.stars = [(R2.uniform(0, s.ww), R2.uniform(0, s.wh * .7), R2.uniform(.5, 1.2), R2.uniform(0, 6.3)) for _ in range(40)]
        s.mx, s.my = s.ww * .62, s.wh * .28
        s.lamp = (W * R.uniform(.78, .86), H * .55)                           # 야간등
        # 흔들의자 + 엄마 + 아기 실루엣 (피벗 기준 좌표, 매 프레임 회전)
        cx, cy = W * .55, H * .80; s.piv = (cx, cy); s.sc = H / 720
        s.chair = [(-120, 0), (-110, -40), (-95, -40), (-95, -160), (-75, -250), (-40, -250), (-40, -150), (90, -150), (110, -40), (120, -40), (130, 0)]
        s.rocker = [(-150, 0), (150, 0), (150, 10), (-150, 10)]
        s.body = [(-70, -150), (-80, -230), (-60, -300), (-20, -335), (20, -335), (50, -300), (55, -250), (85, -230), (120, -200), (120, -150)]
        s.baby = [(-40, -235), (0, -255), (60, -245), (80, -215), (60, -190), (0, -185), (-40, -205)]
        s.mobile = [(R.uniform(0, 6.3), R.uniform(50, 85), R.uniform(2.5, 4.2), int(R.integers(0, 3))) for _ in range(5)]; s.mob_c = (W * .55, H * .16)
        s.dust = [(R.uniform(0, W), R.uniform(0, H), R.uniform(.5, 1.1), R.uniform(2, 5), R.uniform(0, 6.3), R.uniform(.08, .2)) for _ in range(50)]
        s.floor = int(H * .82)
    def _rot(s, pts, ang, dx=0, dy=0):
        c, sn = math.cos(ang), math.sin(ang); px, py = s.piv
        return [(px + (x * c - y * sn) * s.sc + dx, py + (x * sn + y * c) * s.sc + dy) for x, y in pts]
    def frame(s, t):
        img = s.bg.copy(); y, x = s.yy, s.xx
        # 야간등: 따뜻한 빛
        lx, ly = s.lamp; d = np.sqrt((x - lx) ** 2 + (y - ly) ** 2); fl = 1 + .04 * math.sin(t * 2.3) + .03 * math.sin(t * 5.1)
        img += (np.exp(-(d / 330) ** 2) * .32 + np.exp(-(d / 110) ** 2) * .45)[..., None] * hexc('#ffb36b') * fl
        blit(img, lx, ly, sprite(16, 2), hexc('#ffd9a0'), .9); blit(img, lx, ly + 40, sprite(22, 1.4), hexc('#3a2418'), .6)
        # 바닥
        fm = np.clip((y - s.floor) / 3, 0, 1)[..., None]; img[:] = img * (1 - fm) + (hexc('#2a1a24') + np.exp(-(np.abs(x - lx) / 260) ** 2)[..., None] * hexc('#5a3a22') * .5) * fm
        # 창문: 하늘 + 별 + 달 + 창틀 + 커튼
        w = s.sky.copy()
        for sx, sy, r, p in s.stars: blit_small(w, sx, sy, r, hexc('#ffffff'), .5 + .5 * math.sin(t * .9 + p))
        reg = img[s.wy0:s.wy0 + s.wh, s.wx0:s.wx0 + s.ww]; reg[:] = w
        moon_small(reg, s.mx, s.my, 22, hexc('#fff2d0'))
        for k in (0, 1): reg[:, int(s.ww * .5) - 3:int(s.ww * .5) + 3] = hexc('#2a1f3a'); reg[int(s.wh * .5) - 3:int(s.wh * .5) + 3, :] = hexc('#2a1f3a')
        glow = np.exp(-(np.clip(np.sqrt(((x - (s.wx0 + s.ww * .5)) / (s.ww * .9)) ** 2 + ((y - (s.wy0 + s.wh * .5)) / (s.wh * .9)) ** 2) - 1, 0, 9) * 6)) * .12
        img += glow[..., None] * hexc('#8fa0ff')
        for cxx in (s.wx0 - 10, s.wx0 + s.ww + 10):                        # 커튼
            cm = np.exp(-((x - cxx) / 34) ** 2) * (y > s.wy0 - 30) * (y < s.wy0 + s.wh + 60); img[:] = img * (1 - cm[..., None] * .9) + hexc('#4a2a40') * cm[..., None] * .9
        # 모빌: 별·달이 천천히 돌며 흔들림
        mx, my = s.mob_c; vline_soft(img, mx, 0, my - 4, hexc('#6a5a7a'), .5)
        for ph, rad, hang, kind in s.mobile:
            a = t * .25 + ph; X = mx + rad * math.cos(a); Y = my + hang * 3 * s.sc * .55 + 7 * math.sin(a)
            vline_soft(img, X, my, Y - 8, hexc('#6a5a7a'), .35)
            col = hexc(['#ffe08a', '#ffc9d6', '#c9d8ff'][kind]); blit(img, X, Y, sprite(7, 3), col, .55); blit(img, X, Y, sprite(3, 3), hexc('#ffffff'), .5)
        # 흔들의자 + 엄마 + 아기 (천천히 ±3.5도 흔들림)
        ang = math.radians(3.5) * math.sin(2 * math.pi * t / 4.2)
        for pts, col, bl in ((s.rocker, '#170e18', 1.0), (s.chair, '#1b1020', 1.0), (s.body, '#1a1018', 1.5), (s.baby, '#221620', 1.5)):
            m = poly_mask(chaikin(s._rot(pts, ang)) if pts is not s.rocker else s._rot(pts, ang), bl); composite(img, m, hexc(col))
        hx, hy = s._rot([(15, -370)], ang)[0]; m = ellipse_mask(hx, hy, 34 * s.sc, 40 * s.sc, 1.5); composite(img, m, hexc('#1a1018'))   # 머리
        bx, by = s._rot([(55, -232)], ang)[0]; m = ellipse_mask(bx, by, 17 * s.sc, 15 * s.sc, 1.5); composite(img, m, hexc('#241822'))  # 아기 머리
        bm = poly_mask(chaikin(s._rot(s.body, ang))); rim = (gaussian_filter(bm[::2, ::2], 3).repeat(2, 0).repeat(2, 1)[:H, :W] - bm).clip(0, 1)          # 등 뒤로 비치는 야간등 테두리 빛
        img += (rim * .5 * np.exp(-(np.abs(x - lx) / 500) ** 2))[..., None] * hexc('#ffb36b')
        for x0, y0, r, v, p, a in s.dust:
            yy = (y0 - v * t) % (H + 10) - 5; xx = (x0 + 10 * math.sin(t * .2 + p)) % W
            blit(img, xx, yy, sprite(r, 2), hexc('#ffd9a0'), a * (.5 + .5 * math.sin(t + p)) * min(1, 260 / (abs(xx - lx) + abs(yy - ly) + 1)))
        return img * s.vig


def blit_small(img, x, y, r, color, a):
    h, w = img.shape[:2]; spr = sprite(r); n = spr.shape[0] // 2; xi, yi = int(x), int(y)
    x0, x1, y0, y1 = max(0, xi - n), min(w, xi + n + 1), max(0, yi - n), min(h, yi + n + 1)
    if x1 <= x0 or y1 <= y0: return
    img[y0:y1, x0:x1] += spr[y0 - yi + n:y1 - yi + n, x0 - xi + n:x1 - xi + n][..., None] * color * a


def moon_small(img, cx, cy, r, col):
    h, w = img.shape[:2]; y, x = np.ogrid[0:h, 0:w]; d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2).astype(np.float32)
    g = np.exp(-(d / (r * 4)) ** 2) * .35; disc = np.clip(r - d + 1, 0, 1)
    d2 = np.sqrt((x - cx - r * .7) ** 2 + (y - cy + r * .2) ** 2); cut = np.clip(r * 1.02 - d2 + 1, 0, 1)
    img += g[..., None] * col * .6; m = (disc * (1 - cut))[..., None]; img[:] = img * (1 - m) + col * m


def vline_soft(img, x, y0, y1, color, a):
    xi = int(x); y0, y1 = int(max(0, y0)), int(min(H, y1))
    if y1 <= y0 or not (0 <= xi < W): return
    img[y0:y1, xi] += color * a;
    if xi + 1 < W: img[y0:y1, xi + 1] += color * a * .4


class Stream(Scene):     # 달빛 시냇물: 숲 실루엣 사이로 흐르는 물, 달빛 반짝임, 바위, 물안개, 반딧불 몇 마리
    def setup(s):
        R = s.R; s.bg = vgrad([(0, '#050c14'), (.45, '#0b1a24'), (.6, '#10262c'), (1, '#071015')]); s.stars = Stars(R, 120, .4)
        moon(s.bg, W * R.uniform(.55, .75), H * .14, 24, hexc('#f4f0ff'), .3, .35)
        for b, a, c in [(.42, .05, '#0a1c22'), (.52, .04, '#07151a'), (.60, .03, '#040e12')]: fill_below(s.bg, ridge(int(R.integers(1e6)), b, a, 4), hexc(c), 2)
        s.y0 = int(H * .60); s.yy, s.xx = np.mgrid[0:H, 0:W].astype(np.float32)
        s.bank_l = ridge(int(R.integers(1e6)), .0, .0, 1)
        s.tex = tile_noise(H - s.y0, W * 2, 18, int(R.integers(1e6)), 3); s.tex2 = tile_noise(H - s.y0, W * 2, 36, int(R.integers(1e6)), 2)
        s.depth = ((s.yy[s.y0:] - s.y0) / (H - s.y0))
        # 양쪽 강둑 (어두운 풀·바위) — 가운데로 갈수록 좁아지는 원근
        xl = W * .5 - (W * .08 + W * .42 * s.depth[:, 0]); xr = W * .5 + (W * .08 + W * .42 * s.depth[:, 0])
        s.water = ((s.xx[s.y0:] > xl[:, None]) & (s.xx[s.y0:] < xr[:, None])).astype(np.float32)
        s.water = gaussian_filter(s.water, 2.5); s.xl, s.xr = xl, xr
        s.rocks = [(W * (.5 + R.choice([-1, 1]) * R.uniform(.12, .3) * (.4 + dd)), s.y0 + (H - s.y0) * dd, R.uniform(10, 18) * (.5 + dd * 1.4)) for dd in R.uniform(.2, .95, 6)]
        s.rock_m = np.zeros((H, W), np.float32)
        for rx, ry, rr in s.rocks: s.rock_m += ellipse_mask(rx, ry, rr * 1.3, rr * .6, 1.5)
        s.rock_m = s.rock_m.clip(0, 1); s.rock_t = tile_noise(H, W, 10, int(R.integers(1e6)), 2)
        s.rock_lit = np.clip(s.rock_m - np.roll(s.rock_m, 5, axis=0), 0, 1) * s.rock_m
        s.mist = tile_noise(H // 3, W * 2, 60, int(R.integers(1e6)), 2)
        s.f = [(R.uniform(0, W), R.uniform(H * .3, H * .6), R.uniform(20, 50), R.uniform(8, 20), R.uniform(.05, .1), R.uniform(.05, .1), R.uniform(0, 6.3), R.uniform(0, 6.3), R.uniform(.15, .35), R.uniform(1.8, 3)) for _ in range(12)]
        s.mx = W * .6
    def frame(s, t):
        img = s.bg.copy(); s.stars.draw(img, t, .8)
        d = s.depth; off = (t * 55); k0 = int(off) % (W * 2)
        # 흐르는 물 질감 (아래로 흐르는 대신, 멀리서 가까이로 — 원근상 세로 스크롤)
        sh = int((t * 90) % (s.tex.shape[0])); tx = np.roll(np.roll(s.tex, sh, axis=0), -k0 // 3, axis=1)[:, :W]
        tx2 = np.roll(np.roll(s.tex2, int((t * 40) % s.tex2.shape[0]), axis=0), k0 // 5, axis=1)[:, :W]
        base = hexc('#0e2a3a') * (1 - d[..., None] * .3) + hexc('#1b4a5a') * (tx * .5 + tx2 * .3)[..., None] * (1 - d[..., None] * .4)
        spark = (np.clip((tx - .66) * 4, 0, 1) ** 2 * np.exp(-((s.xx[s.y0:] - s.mx) / (120 + 500 * d)) ** 2) * (1.0 - d * .5))
        base += (spark * .9)[..., None] * hexc('#fff0c8')
        base += (np.clip((tx2 - .6) * 3, 0, 1) * .12)[..., None] * hexc('#9fd0ff')
        reg = img[s.y0:]; wm = s.water[..., None]; reg[:] = reg * (1 - wm) + base * wm
        # 둑 가장자리 풀 그림자 + 바위 + 바위 주변 흰 물거품
        edge = (np.exp(-np.abs(s.xx[s.y0:] - s.xl[:, None]) / 14) + np.exp(-np.abs(s.xx[s.y0:] - s.xr[:, None]) / 14)) * s.water
        reg[:] = reg * (1 - edge[..., None] * .7)
        rm = s.rock_m[..., None]; img[:] = img * (1 - rm) + (hexc('#2a343c') + s.rock_t[..., None] * .10 + s.rock_lit[..., None] * hexc('#9aa8c0') * .55) * rm
        foam = (gaussian_filter(s.rock_m, 7) - s.rock_m).clip(0, 1); foam *= .5 + .5 * np.sin(s.yy * .4 + t * 8 + s.rock_t * 20)
        img += (foam * .35)[..., None] * hexc('#dfefff')
        offm = int((t * 6) % (W * 2)); m = np.roll(s.mist, -offm, axis=1)[:, :W]
        img[s.y0 - H // 6:s.y0 + H // 6] += (np.clip((m - .45) * 1.5, 0, 1) * .07)[..., None] * hexc('#a8c8d8')
        for x, y, ax, ay, wx, wy, px, py, wb, r in s.f:
            b = max(0, math.sin(t * wb * 2 * math.pi / 3 + px)) ** 2
            X = x + ax * math.sin(t * wx * 2 * math.pi / 3 + px); Y = y + ay * math.sin(t * wy * 2 * math.pi / 3 + py)
            blit(img, X, Y, sprite(r * 5, 2), hexc('#b8ff6a'), .12 * b); blit(img, X, Y, sprite(r, 2), hexc('#f2ffc0'), .9 * b)
        return img * s.vig


class Study(Scene):      # 늦은 밤 서재: 책장 실루엣, 스탠드 불빛, 창밖 비, 괘종시계 추가 2초에 한 번 왕복
    def setup(s):
        R = s.R; s.bg = vgrad([(0, '#0b0906'), (.7, '#1a120c'), (1, '#120c08')]); s.yy, s.xx = np.mgrid[0:H, 0:W].astype(np.float32)
        s.lx, s.ly = W * .72, H * .40
        # 책장: 선반 4단 + 책들 (실루엣)
        def books(d):
            x0, y0 = int(W * .05), int(H * .10); d.rectangle([x0, y0, x0 + int(W * .36), int(H * .86)], fill=90)
            for sh in range(4):
                y = y0 + 20 + sh * int(H * .18); x = x0 + 14
                while x < x0 + int(W * .36) - 20:
                    bw = int(R.uniform(10, 26)); bh = int(R.uniform(60, 100)); d.rectangle([x, y + 110 - bh, x + bw, y + 110], fill=int(R.uniform(120, 220))); x += bw + 3
                d.rectangle([x0, y + 112, x0 + int(W * .36), y + 118], fill=60)
        s.shelf = shapes_mask(books, .8); s.shelf_t = tile_noise(H, W, 8, int(R.integers(1e6)), 2)
        s.books_col = np.stack([hexc(c) for c in ['#3a2a2a', '#2a3a3a', '#4a3a2a', '#2a2a4a', '#4a2a3a']])
        s.bcol = tile_noise(H, W, 6, int(R.integers(1e6)), 1)
        # 창 (오른쪽 위) 비 오는 창
        s.wx0, s.wy0, s.ww, s.wh = int(W * .80), int(H * .10), int(W * .16), int(H * .38)
        s.drops = [(R.uniform(0, s.ww), R.uniform(0, s.wh), R.uniform(250, 400), R.uniform(.1, .25)) for _ in range(40)]
        s.beads = [(R.uniform(0, s.ww), R.uniform(0, s.wh), R.uniform(1.2, 2.6)) for _ in range(40)]
        # 괘종시계 (가운데 벽)
        s.cx, s.cy = W * .56, H * .30; s.clock_face = ellipse_mask(s.cx, s.cy, 46, 46, .8); s.clock_body = shapes_mask(lambda d: d.rounded_rectangle([s.cx - 54, s.cy - 56, s.cx + 54, s.cy + 230], 10, fill=255), .8)
        s.clock_glass = shapes_mask(lambda d: d.rounded_rectangle([s.cx - 40, s.cy + 70, s.cx + 40, s.cy + 215], 6, fill=255), .8)
        s.desk = int(H * .80); s.dust = [(R.uniform(W * .4, W), R.uniform(H * .2, s.desk), R.uniform(.5, 1.1), R.uniform(2, 5), R.uniform(0, 6.3), R.uniform(.08, .22)) for _ in range(50)]
    def frame(s, t):
        img = s.bg.copy(); y, x = s.yy, s.xx
        d = np.sqrt((x - s.lx) ** 2 + (y - s.ly) ** 2); fl = 1 + .02 * math.sin(t * 3.1)
        cone = np.exp(-((x - s.lx) / (40 + 1.1 * np.clip(y - s.ly, 0, 900))) ** 2) * (y > s.ly) * np.clip(1 - (y - s.ly) / 650, 0, 1)
        img += (np.exp(-(d / 420) ** 2) * .25 + np.exp(-(d / 900) ** 2) * .12 + cone * .55)[..., None] * hexc('#ffb86b') * fl
        blit(img, s.lx, s.ly - 12, sprite(30, 6), hexc('#4a2c14'), .8); blit(img, s.lx, s.ly + 2, sprite(8, 2), hexc('#ffe0a0'), .9)   # 스탠드 갓·전구
        # 책장
        sm = s.shelf[..., None]; bc = s.books_col[(s.bcol * 4.99).astype(int)] * (.25 + .9 * s.shelf[..., None]) * (.5 + .5 * np.exp(-(np.abs(x - s.lx) / 520) ** 2))[..., None]
        img[:] = img * (1 - sm) + (bc * 1.5 + s.shelf_t[..., None] * .04 + hexc('#3a2614') * .25) * sm
        # 창: 비
        reg = img[s.wy0:s.wy0 + s.wh, s.wx0:s.wx0 + s.ww]; reg[:] = hexc('#101a2c') * .9 + reg * .2
        for dx, dy, v, a in s.drops:
            yy = int((dy + v * t) % s.wh); xx = int(dx); reg[max(0, yy - 10):yy, xx:xx + 2] += hexc('#b8c8ff') * a
        for bx, by, r in s.beads: blit_small(reg, bx, by, r, hexc('#c8d8ff'), .5)
        frame_m = np.zeros((s.wh, s.ww), np.float32); frame_m[:, s.ww // 2 - 3:s.ww // 2 + 3] = 1; frame_m[s.wh // 2 - 3:s.wh // 2 + 3, :] = 1
        reg[:] = reg * (1 - frame_m[..., None]) + hexc('#2a1e14') * frame_m[..., None]
        # 괘종시계: 몸통, 유리창, 추(2초 주기 — 똑·딱이 1초마다)
        composite(img, s.clock_body, hexc('#2a1a10') + np.exp(-(np.abs(x - s.lx) / 500) ** 2)[..., None] * hexc('#3a2616') * .6)
        composite(img, s.clock_glass, hexc('#17100c')); composite(img, s.clock_face, hexc('#e8dcc0') * (.55 + .3 * np.exp(-(np.abs(x - s.lx) / 500) ** 2))[..., None])
        for k in range(12):
            a = k * math.pi / 6; blit(img, s.cx + 38 * math.sin(a), s.cy - 38 * math.cos(a), sprite(1.3, 3), hexc('#2a2018'), .9)
        hr = (t / 3600 * 2 * math.pi / 12) + math.radians(302); mn = (t / 60 * 2 * math.pi / 60) + math.radians(12)
        for a, L, wdt in ((hr, 22, 2), (mn, 33, 1.5)):
            for k in range(int(L)): blit(img, s.cx + k * math.sin(a), s.cy - k * math.cos(a), sprite(wdt, 3), hexc('#2a2018'), .9)
        ang = math.radians(9) * math.sin(2 * math.pi * t / 2.0); px, py = s.cx, s.cy + 75; L = 125
        bx, by = px + L * math.sin(ang), py + L * math.cos(ang)
        for k in range(0, L, 3): blit(img, px + k * math.sin(ang), py + k * math.cos(ang), sprite(1.2, 3), hexc('#d8b060'), .9)
        blit(img, bx, by, sprite(14, 3), hexc('#c9a040') * (.8 + .4 * math.cos(ang * 4)), .95); blit(img, bx - 4, by - 4, sprite(4, 4), hexc('#fff0c0'), .8)
        # 책상
        dm = np.clip((y - s.desk) / 3, 0, 1)[..., None]; img[:] = img * (1 - dm) + (hexc('#2e1c10') + cone[..., None] * hexc('#6a4420') * .8) * dm
        for x0, y0, r, v, p, a in s.dust:
            yy = (y0 - v * t) % (H + 10) - 5; xx = (x0 + 10 * math.sin(t * .2 + p)) % W
            blit(img, xx, yy, sprite(r, 2), hexc('#ffd9a0'), a * (.5 + .5 * math.sin(t + p)) * cone[int(yy) % H, int(xx) % W])
        return img * s.vig


SCENES = {'night': Night, 'rainwin': RainWin, 'sea': Sea, 'firefly': Firefly, 'snow': Snow, 'aurora': Aurora, 'pastel': Pastel, 'warm': Warm,
          'eaves': Eaves, 'storm': Storm, 'nursery': Nursery, 'stream': Stream, 'candle': Candle, 'study': Study}


# ----------------------------------------------------------------------------- 후처리 · 인코딩
def _grain(seed, n=48):
    R = np.random.default_rng(seed); return [(R.standard_normal((H, W, 1)).astype(np.float32) * .012) for _ in range(n)]


def grade(f, grain):
    """필름 느낌: 블룸(밝은 곳 빛 번짐) + 부드러운 S커브 + 살짝 들어 올린 검정 + 그레인"""
    small = f[::4, ::4]; bright = np.clip(small - .55, 0, 1); bl = gaussian_filter(bright, (3, 3, 0))
    bloom = np.repeat(np.repeat(bl, 4, axis=0), 4, axis=1)[:H, :W]
    f = f + bloom * .55
    f = np.clip(f, 0, 1); f = f * f * (3 - 2 * f) * .92 + f * .08                 # S커브
    f = .02 + f * .975                                                              # 검정 살짝 들기
    return f + grain * (1 - f * .6)


def camera(f, u):
    """천천히 움직이는 카메라: 1248x702 창을 서서히 이동"""
    dx = int((W - CW) * (.5 + .5 * math.sin(u * 2 * math.pi + 1.1))); dy = int((H - CH) * (.5 + .5 * math.cos(u * 2 * math.pi * .7)))
    return f[dy:dy + CH, dx:dx + CW]


def render_segment(args):
    """장면 k (seg초) — 끝 xf초 동안 다음 장면으로 서서히 바뀜. 파일 하나로 인코딩"""
    k, names, seed, seg, xf, out, crf, maxrate = args
    a = SCENES[names[k]](seed + k * 101); b = SCENES[names[(k + 1) % len(names)]](seed + ((k + 1) % len(names)) * 101)
    grains = _grain(seed + k); n = int(seg * FPS); T = seg * len(names)
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{CW}x{CH}', '-r', str(FPS), '-i', '-',
                           '-vf', 'scale=1920:1080:flags=lanczos', '-c:v', 'libx264', '-preset', 'medium', '-crf', str(crf), '-x264-params', 'aq-mode=3:keyint=96:min-keyint=96', '-maxrate', maxrate, '-bufsize', '3000k',
                           '-pix_fmt', 'yuv420p', '-an', out], stdin=subprocess.PIPE)
    for i in range(n):
        t = i / FPS; f = a.frame(t)
        if t > seg - xf:
            u = (t - (seg - xf)) / xf; u = u * u * (3 - 2 * u); f = f * (1 - u) + b.frame(t - seg) * u
        f = grade(f, grains[i % len(grains)]); f = camera(f, (k * seg + t) / T)
        ff.stdin.write((np.clip(f, 0, 1) * 255).astype(np.uint8).tobytes())
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
    f = grade(SCENES[name](seed).frame(t), 0.0); return np.clip(camera(f, .3), 0, 1)
