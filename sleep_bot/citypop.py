#!/usr/bin/env python3
"""시티팝 장면 (1980~90년대 일본 버블 시대 · 미국 80년대) — 640x360 고해상도 도트 + VHS·브라운관 후처리.
외부 이미지 0개, 전부 코드로 그림. 2배로 각지게 키워 1280x720 (출력 1920x1080 = 정확히 3배 도트).
장면: cp_room 버블 시대 맨션(노을 바다·블라인드 햇살·오디오·턴테이블·네온 야자수)
      cp_drive 밤의 고속도로 드라이브(오른쪽 핸들·네온 도시·철탑·가로등·카세트 카오디오)
      cp_boulevard 80년대 해변 대로(줄무늬 노을 해·야자수·아르데코 호텔 네온·오픈카)
"""
import os
from PIL import ImageFont
FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts', 'Galmuri11-Bold.ttf')
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
CW, CH = 640, 360
BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) + .5) / 16


def hx(h):
    h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


def rgb8(h): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def dgrad(stops, h, w, axis=0):
    """색 띠 + 바이어 디더 그라데이션 (axis 0 = 세로)"""
    cols = np.stack([hx(c) for _, c in stops]); pos = [p for p, _ in stops]
    n = h if axis == 0 else w
    t = np.interp(np.arange(n, dtype=np.float32) / max(1, n - 1), pos, np.arange(len(stops), dtype=np.float32))
    base = np.floor(t).astype(int); fr = t - base
    yy, xx = np.mgrid[0:h, 0:w]; thr = BAYER[yy % 4, xx % 4]
    if axis == 0: idx = base[:, None] + (fr[:, None] > thr)
    else: idx = base[None, :] + (fr[None, :] > thr)
    return cols[np.clip(idx, 0, len(stops) - 1)]


def mask(draw_fn, w=CW, h=CH):
    im = Image.new('L', (w, h), 0); draw_fn(ImageDraw.Draw(im)); return np.asarray(im) > 127


def paint(C, m, col, a=1.0):
    C[m] = C[m] * (1 - a) + (hx(col) if isinstance(col, str) else col) * a


def paint_grad(C, m, stops, axis=0):
    ys, xs = np.where(m)
    if not len(ys): return
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    g = dgrad(stops, y1 - y0, x1 - x0, axis); sub = m[y0:y1, x0:x1]
    C[y0:y1, x0:x1][sub] = g[sub]


def dither_alpha(C, m, col, a):
    """반투명을 디더 점으로 (도트 느낌의 빛줄기·그림자)"""
    yy, xx = np.mgrid[0:C.shape[0], 0:C.shape[1]]; on = m & (BAYER[yy % 4, xx % 4] < a)
    C[on] = hx(col) if isinstance(col, str) else col


def add_glow(C, m, col, radius=6, strength=.6):
    """빛나는 부분 주변으로 번짐 (블룸)"""
    from scipy.ndimage import gaussian_filter
    g = gaussian_filter(m.astype(np.float32), radius) * strength
    C += g[..., None] * (hx(col) if isinstance(col, str) else col)


def up2(C): return np.repeat(np.repeat(np.clip(C, 0, 1), 2, 0), 2, 1)


_NOISE = {}
def vhs(f, t, seed=0, strength=1.0):
    """VHS·브라운관 후처리 (1280x720): 색 번짐 · RGB 어긋남 · 주사선 · 테이프 잡음 줄 · 살짝 흔들림 · 비네트 · 블룸"""
    from scipy.ndimage import gaussian_filter
    H, W = f.shape[:2]; R = np.random.default_rng(int(t * 24) + seed * 7919)
    small = f[::4, ::4]; bl = gaussian_filter(np.clip(small - .55, 0, 1), (3, 3, 0))
    f = f + np.repeat(np.repeat(bl, 4, 0), 4, 1)[:H, :W] * .7                               # 블룸
    y = .299 * f[..., 0] + .587 * f[..., 1] + .114 * f[..., 2]                               # 색만 가로로 번지게 (VHS 색 번짐)
    cb = f[..., 2] - y; cr = f[..., 0] - y
    k = np.ones(9, np.float32) / 9
    cb = np.apply_along_axis(lambda r: np.convolve(r, k, 'same'), 1, cb[::2])[:, :].repeat(2, 0)[:H] if False else _hblur(cb, 7)
    cr = _hblur(cr, 7)
    r = y + cr; b = y + cb; g = (y - .299 * r - .114 * b) / .587
    f = np.stack([r, g, b], -1)
    sh = 3                                                                                   # 빨강·파랑 살짝 어긋남
    f[..., 0] = np.roll(f[..., 0], sh, axis=1); f[..., 2] = np.roll(f[..., 2], -sh + 1, axis=1)
    wob = (np.sin(np.arange(H) / 37 + t * 1.3) * .6 + R.normal(0, .25)).astype(int)          # 가로 흔들림
    if R.random() < .5: f = np.stack([np.roll(f[i], wob[i] if abs(wob[i]) < 2 else 0, axis=0) for i in range(H)])
    band = (t * 41) % (H * 3)                                                                # 아래로 흐르는 트래킹 잡음 띠
    if band < H:
        b0 = int(band); b1 = min(H, b0 + 10); nz = R.random((b1 - b0, W, 1)).astype(np.float32)
        f[b0:b1] = f[b0:b1] * .7 + nz * .35
        f[b0:b1] = np.roll(f[b0:b1], int(R.integers(-6, 7)), axis=1)
    f[1::2] *= .9                                                                            # 주사선
    yy, xx = np.mgrid[0:H, 0:W]
    key = (H, W)
    if key not in _NOISE: _NOISE[key] = (1 - .38 * (((xx / W - .5) * 1.6) ** 2 + ((yy / H - .5) * 1.9) ** 2)).clip(0, 1)[..., None]
    f = f * _NOISE[key]
    gk = ('g', H, W)                                                                         # 테이프 지글거림 (미리 만든 6장 돌려 씀 → 압축 잘 됨)
    if gk not in _NOISE: _NOISE[gk] = [np.random.default_rng(i).normal(0, .009, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1) for i in range(6)]
    f = f + _NOISE[gk][int(t * 8) % 6]
    return np.clip(f * (.97 + .03 * math.sin(t * 9.1)), 0, 1)


def _hblur(x, n):
    c = np.cumsum(np.pad(x, ((0, 0), (n // 2 + 1, n // 2)), mode='edge'), axis=1)
    return (c[:, n:] - c[:, :-n]) / n




class CpRoom:
    """버블 시대 맨션: 노을 진 바다 건너 도시, 블라인드 사이 햇살 줄무늬, 오디오 컴포넌트·턴테이블·네온 야자수"""
    PIXEL = True; CITYPOP = True
    def __init__(s, seed=1, pal=None):
        s.R = np.random.default_rng(seed); R = s.R; W, H = CW, CH
        # ── 창밖 (x 250~630, y 24~236)
        s.wx0, s.wy0, s.wx1, s.wy1 = 250, 22, 632, 238
        ww, wh = s.wx1 - s.wx0, s.wy1 - s.wy0
        V = dgrad([(0, '#2a2a6e'), (.22, '#5b3f8f'), (.42, '#b8578f'), (.6, '#ff7f7f'), (.72, '#ffa86b'), (.8, '#ffd08a')], wh, ww)
        hz = 160 - s.wy0                                                                       # 수평선
        sx, sy, sr = 255, hz + 2, 38                                                           # 지는 해
        yy, xx = np.mgrid[0:wh, 0:ww]
        sun = ((xx - sx) ** 2 + (yy - sy) ** 2 <= sr * sr) & (yy < hz)
        V[sun] = dgrad([(0, '#fff6c8'), (.6, '#ffc078'), (1, '#ff8a6a')], wh, ww)[sun]
        for k, (cy, cl) in enumerate(((40, 120), (62, 200), (84, 90))):                       # 길쭉한 노을 구름
            cx = int(R.uniform(40, ww - 80)); m = ((xx - cx) / cl) ** 2 + ((yy - cy) / 5) ** 2 <= 1
            V[m] = V[m] * .35 + hx('#ff9fb8' if k != 1 else '#e86fa0') * .65
            m2 = ((xx - cx) / cl) ** 2 + ((yy - cy - 3) / 3) ** 2 <= 1; V[m2 & m] = hx('#7a3f86') * .5 + V[m2 & m] * .5
        # 바다 건너 스카이라인
        x = 0; s.lit = []
        while x < ww:
            bw_ = int(R.integers(6, 18)); bh = int(R.integers(8, 46)) if not (150 < x < 200) else int(R.integers(4, 12))
            V[hz - bh:hz, x:x + bw_] = hx('#3a2458'); V[hz - bh:hz - bh + 1, x:x + bw_] = hx('#5a3a78')
            for _ in range(bw_ * bh // 14): s.lit.append((s.wx0 + x + int(R.integers(1, max(2, bw_ - 1))), s.wy0 + hz - int(R.integers(2, max(3, bh))), float(R.uniform(0, 1))))
            x += bw_ + int(R.integers(0, 3))
        tx = 70                                                                                 # 격자 철탑 (도쿄타워풍)
        for yy_ in range(hz - 92, hz):
            half = int(1 + (yy_ - (hz - 92)) * .14)
            V[yy_, tx - half] = hx('#e8544a'); V[yy_, tx + half] = hx('#e8544a')
            if (yy_ - hz) % 6 == 0: V[yy_, tx - half:tx + half + 1] = hx('#e8544a')
            if (yy_ - hz) % 12 == 3: V[yy_, tx - half:tx + half + 1] = hx('#f4ece0')
        s.lit = [l for l in s.lit if s.wx0 <= l[0] < s.wx1 and s.wy0 <= l[1] < s.wy1]
        s.tower = (s.wx0 + tx, s.wy0 + hz - 93)
        V[hz:] = dgrad([(0, '#8a4f8a'), (.4, '#4a3a7a'), (1, '#1e2450')], wh - hz, ww)       # 바다
        s.V = V; s.hz = hz; s.sx = sx
        # ── 방 (정적)
        C = dgrad([(0, '#2a1a3c'), (.6, '#3a2246'), (1, '#4a2a4a')], H, W)
        C[s.wy0:s.wy1, s.wx0:s.wx1] = 0
        s.wallmask = np.ones((H, W), bool); s.wallmask[s.wy0:s.wy1, s.wx0:s.wx1] = False
        s.C0 = C
    # 정적 가구 레이어 (PIL로 각지게)
    def furniture(s, d, t):
        W, H = CW, CH
        d.rectangle([0, 286, W, H], fill=rgb8('#2a1630'))                                       # 바닥 카펫
        d.rectangle([0, 284, W, 287], fill=rgb8('#1c0f22'))
        # 창틀·블라인드
        for x in (s.wx0 - 4, s.wx1, 440):
            d.rectangle([x, s.wy0 - 4, x + 4, s.wy1 + 4], fill=rgb8('#1a1028'))
        d.rectangle([s.wx0 - 4, s.wy0 - 6, s.wx1 + 4, s.wy0], fill=rgb8('#1a1028')); d.rectangle([s.wx0 - 8, s.wy1, s.wx1 + 8, s.wy1 + 6], fill=rgb8('#3a2440'))
        for k in range(9):                                                                   # 위쪽만 내린 블라인드
            y = s.wy0 + 2 + k * 6
            d.rectangle([s.wx0, y, s.wx1, y + 3], fill=rgb8('#e8c8b0')); d.line([(s.wx0, y + 3), (s.wx1, y + 3)], fill=rgb8('#a07a80'))
        d.rectangle([s.wx0, s.wy0 + 56, s.wx1, s.wy0 + 59], fill=rgb8('#c8a890'))
        for x in (300, 470, 580): d.line([(x, s.wy0), (x, s.wy0 + 57)], fill=rgb8('#8a6a70'))
        # 사이드보드 + 오디오
        d.rectangle([20, 214, 236, 290], fill=rgb8('#3a2018')); d.rectangle([20, 210, 236, 216], fill=rgb8('#5a3424'))
        d.rectangle([24, 226, 232, 286], outline=rgb8('#26140e'))
        for x in (24, 128): d.rectangle([x + 2, 270, x + 100, 284], fill=rgb8('#2a160f'))
        # 앰프 (은색, VU 미터 2개)
        d.rectangle([30, 220, 226, 248], fill=rgb8('#c9c4c8')); d.rectangle([30, 246, 226, 248], fill=rgb8('#8a8488'))
        for k, vx in enumerate((38, 82)):
            d.rectangle([vx, 224, vx + 36, 242], fill=rgb8('#f0d48a')); d.rectangle([vx, 224, vx + 36, 242], outline=rgb8('#5a5054'))
            ang = -2.2 + .9 * (.5 + .5 * math.sin(t * (3.1 + k) + k)) * (.6 + .4 * math.sin(t * 7.3 + k * 2))
            cx, cy = vx + 18, 244; d.line([(cx, cy), (cx + 16 * math.cos(ang), cy + 16 * math.sin(ang))], fill=rgb8('#c0302a'))
        for k in range(5): d.ellipse([132 + k * 18, 228, 142 + k * 18, 238], fill=rgb8('#8a8488'))   # 노브
        d.rectangle([132, 241, 220, 243], fill=rgb8('#3a3438'))
        # 카세트 데크 (위층)
        d.rectangle([30, 252, 226, 268], fill=rgb8('#1c1a20')); d.rectangle([40, 255, 110, 266], fill=rgb8('#2e2a36'))
        for k, rx in enumerate((55, 95)):
            a = t * 3 + k; d.ellipse([rx - 5, 256, rx + 5, 266], fill=rgb8('#d8d0c8'))
            d.line([(rx, 261), (rx + 4 * math.cos(a), 261 + 4 * math.sin(a))], fill=rgb8('#3a3438'))
        for k in range(12):                                                                  # 이퀄라이저 LED
            lv = int(5 * (.5 + .5 * math.sin(t * (4 + k * .7) + k * 1.3)) * (.6 + .4 * math.sin(t * 2.1 + k)))
            for j in range(5): d.rectangle([124 + k * 8, 265 - j * 2, 129 + k * 8, 265 - j * 2], fill=rgb8(('#3aff9a' if j < 3 else '#ffd84a' if j < 4 else '#ff4a5a') if j <= lv else '#203028'))
        # 턴테이블 (위)
        d.rectangle([40, 186, 200, 210], fill=rgb8('#2a2228')); d.rectangle([40, 186, 200, 188], fill=rgb8('#4a4048'))
        d.ellipse([60, 180, 150, 202], fill=rgb8('#0c0a0e')); d.ellipse([92, 187, 118, 195], fill=rgb8('#e0505a'))
        for r in (38, 30, 22): d.arc([105 - r, 191 - r * .25, 105 + r, 191 + r * .25], 0, 360, fill=rgb8('#1e1a22'))
        a = t * 3.5; d.point((105 + 9 * math.cos(a), 191 + 2.3 * math.sin(a)), fill=rgb8('#ffffff'))
        d.line([(186, 184), (178, 190), (148, 192)], fill=rgb8('#c9c4c8'), width=2)
        # 스피커 (왼쪽 큰 것)

        # 스탠드 조명 + 전화기 + 칵테일 (오른쪽 낮은 테이블)
        d.rectangle([440, 268, 600, 274], fill=rgb8('#e8e0e8')); d.rectangle([450, 274, 456, 300], fill=rgb8('#c0b8c0')); d.rectangle([584, 274, 590, 300], fill=rgb8('#c0b8c0'))
        d.rectangle([462, 254, 500, 268], fill=rgb8('#f0eef0')); d.rectangle([466, 248, 496, 254], fill=rgb8('#e4e0e4'))
        for k in range(9): d.rectangle([470 + (k % 3) * 8, 256 + (k // 3) * 4, 474 + (k % 3) * 8, 258 + (k // 3) * 4], fill=rgb8('#c8c0c8'))
        d.polygon([(530, 236), (552, 236), (541, 250)], fill=rgb8('#bfe8ff')); d.line([(541, 250), (541, 264)], fill=rgb8('#e8f4ff')); d.line([(534, 266), (548, 266)], fill=rgb8('#e8f4ff'))
        d.polygon([(533, 238), (549, 238), (541, 247)], fill=rgb8('#ff8aa8')); d.ellipse([546, 230, 554, 238], fill=rgb8('#ffb340'))
        # 몬스테라 화분
        d.rectangle([606, 250, 636, 290], fill=rgb8('#e8e0d8'))
        for k, (lx, ly, rr) in enumerate(((600, 214, 16), (622, 196, 18), (632, 226, 14), (610, 236, 12))):
            d.ellipse([lx - rr, ly - rr * .7, lx + rr, ly + rr * .7], fill=rgb8('#1f5a3a')); d.line([(lx, ly), (620, 252)], fill=rgb8('#1f4a30'))
        # 벽 포스터 (시티팝 앨범 아트풍: 줄무늬 해 + 야자수 + 바다)
        d.rectangle([168, 60, 236, 150], fill=rgb8('#e8e0d4')); d.rectangle([174, 66, 230, 144], fill=rgb8('#3ac8d0'))
        d.rectangle([174, 66, 230, 100], fill=rgb8('#ff8aa8')); d.rectangle([174, 100, 230, 112], fill=rgb8('#ffb070'))
        d.pieslice([186, 88, 218, 120], 180, 360, fill=rgb8('#ffe080'))
        for k in range(3): d.rectangle([186, 106 - k * 5, 218, 107 - k * 5], fill=rgb8('#ffb070'))
        d.rectangle([174, 112, 230, 144], fill=rgb8('#2aa8c0')); d.line([(176, 120), (228, 120)], fill=rgb8('#8ae8f0')); d.line([(180, 130), (224, 130)], fill=rgb8('#8ae8f0'))
        d.line([(206, 142), (210, 96)], fill=rgb8('#1a3040'), width=2); d.arc([196, 88, 216, 104], 200, 340, fill=rgb8('#1a5040'), width=2); d.arc([206, 88, 226, 104], 200, 340, fill=rgb8('#1a5040'), width=2)
        # 키 큰 스피커
        d.rectangle([228, 156, 246, 290], fill=rgb8('#3a2018')); d.ellipse([229, 230, 245, 246], fill=rgb8('#1a0e0a')); d.ellipse([233, 234, 241, 242], fill=rgb8('#4a3028'))
        d.ellipse([231, 196, 243, 208], fill=rgb8('#1a0e0a')); d.ellipse([233, 166, 241, 174], fill=rgb8('#1a0e0a'))
        # 러그
        d.polygon([(60, 330), (420, 318), (480, 360), (20, 360)], fill=rgb8('#3a1e48'))
        for k in range(6): d.line([(80 + k * 64, 328), (60 + k * 76, 360)], fill=rgb8('#4a2a5a'))
        return d

    def neon(s, t):
        on = not (11.0 < (t % 17) < 11.15)
        m = mask(lambda d: (d.line([(120, 150), (124, 120), (130, 98)], fill=255, width=2),
                            d.arc([96, 84, 132, 112], 200, 330, fill=255, width=2), d.arc([126, 84, 162, 112], 210, 340, fill=255, width=2),
                            d.arc([104, 92, 134, 128], 230, 330, fill=255, width=2), d.arc([126, 92, 156, 128], 210, 310, fill=255, width=2)))
        m2 = mask(lambda d: d.arc([86, 136, 176, 164], 180, 360, fill=255, width=2))
        return m, m2, on

    def draw(s, t):
        C = s.C0.copy(); W, H = CW, CH
        V = s.V.copy(); ww = s.wx1 - s.wx0
        for k in range(26):                                                                  # 바다 위 햇빛 반짝임
            y = s.hz + 3 + (k * 7) % 70; x = s.sx + int((math.sin(k * 3.7 + t * .9) * .5 + .5) * (18 + y - s.hz) - (9 + (y - s.hz) / 2))
            if math.sin(t * 2.3 + k * 1.9) > -.2 and 0 <= x < ww - 6: V[y, x:x + 4 + (k % 3)] = hx('#ffe0a0') * .8 + V[y, x] * .2
        C[s.wy0:s.wy1, s.wx0:s.wx1] = V
        for x, y, ph in s.lit:
            if math.sin(t * .17 + ph * 40) > -.3: C[y, x] = hx('#ffe08a') if ph < .75 else hx('#9ff0ff')
        if (t % 1.6) < .8: C[s.tower[1], s.tower[0]] = hx('#ff3040')
        # 햇살 줄무늬 (블라인드 사이로 왼쪽 벽·바닥에 비스듬히)
        if not hasattr(s, 'yy'):
            s.yy, s.xx = np.mgrid[0:H, 0:W]; s.warm = (np.clip(1 - np.hypot((s.xx - 420) / 420, (s.yy - 140) / 260), 0, 1) ** 1.5)[..., None] * np.array([1.0, .78, .62])
            s.sunm = (np.abs(s.xx - (s.wx0 + s.sx)) + np.abs(s.yy - (s.wy0 + s.hz)) * 2 < 60) & ~s.wallmask
        yy, xx = s.yy, s.xx
        shift = 6 * math.sin(t * .05)
        u = (xx * .55 + yy + shift) % 14
        stripes = (u < 4) & (xx < s.wx0 - 6) & (yy > 40) & (yy < 300) & (xx > 20 + (300 - yy) * .4)
        dither_alpha(C, stripes & (yy < 286) & (xx > 150), hx('#c8607a'), .3)
        im = Image.fromarray((np.clip(C, 0, 1) * 255).astype('uint8')); d = ImageDraw.Draw(im)
        s.furniture(d, t)
        C = np.asarray(im).astype(np.float32) / 255
        flo = (yy >= 288) & (xx > (s.wx0 - (yy - 288) * 1.6)) & (xx < (s.wx1 - (yy - 288) * .9))          # 창에서 바닥으로 떨어지는 빛
        dither_alpha(C, flo, hx('#7a3a6a'), .55); dither_alpha(C, flo & (u < 4), hx('#c8607a'), .45)
        # 노을빛 받는 방: 창 쪽에서 오는 따뜻한 빛, 왼쪽은 보라 그늘
        inside = s.wallmask[..., None]
        C = np.where(inside, C * (.72 + .5 * s.warm) + hx('#3a1e5a') * .06, C)
        # 네온
        m, m2, on = s.neon(t)
        if on:
            paint(C, m, '#3affc8'); paint(C, m2, '#ff4fd0'); add_glow(C, m, '#3affc8', 5, .9); add_glow(C, m2, '#ff4fd0', 5, .9)
        add_glow(C, s.sunm, '#ffb070', 14, .35)
        return C

    def frame(s, t): return up2(s.draw(t))






class CpDrive:
    """밤의 수도고속도로: 오른쪽 핸들 차 안에서 보는 네온 도시 · 다가오는 가로등 · 앞차 미등 · 카세트 데크"""
    PIXEL = True; CITYPOP = True
    VP = (300, 150)
    def __init__(s, seed=1, pal=None):
        R = np.random.default_rng(seed); s.R = R; W, H = CW, CH; vx, vy = s.VP
        S = dgrad([(0, '#070720'), (.25, '#14143e'), (.36, '#3a1f5e'), (.42, '#a03a7a'), (.45, '#ff6f8a')], H, W)
        yy, xx = np.mgrid[0:H, 0:W]
        st = R.random((H, W)) < .0025; S[st & (yy < 100)] = hx('#e8e8ff')
        x = 0; s.lit = []
        while x < W:                                                                        # 스카이라인 (네온 간판 포함)
            bw_ = int(R.integers(8, 26)); bh = int(R.integers(14, 70)) * (1 if abs(x - vx) > 30 else 0.5)
            bh = int(bh); col = hx(['#1a1640', '#221a4a', '#16163a'][int(R.integers(3))])
            S[vy - bh:vy, x:x + bw_] = col
            for _ in range(bw_ * bh // 12): s.lit.append((x + int(R.integers(1, max(2, bw_ - 1))), vy - int(R.integers(2, max(3, bh))), float(R.uniform(0, 1))))
            if R.random() < .25 and bh > 30:
                s.lit.append((-1, 0, 0)); ny = vy - bh + 4; S[ny:ny + 8, x + 2:x + bw_ - 2] = hx(['#ff4fa0', '#3ae0ff', '#ffd04a', '#9a5aff'][int(R.integers(4))])
            x += bw_ + int(R.integers(0, 3))
        tx = 470                                                                            # 붉은 격자 철탑
        for y in range(vy - 100, vy):
            half = int(1 + (y - (vy - 100)) * .12)
            if 0 <= tx - half and tx + half < W:
                S[y, tx - half] = hx('#ff5a3a'); S[y, tx + half] = hx('#ff5a3a')
                if y % 7 == 0: S[y, tx - half:tx + half + 1] = hx('#ffb070')
        s.tower = (tx, vy - 101)
        s.sky = S
    def draw(s, t):
        W, H = CW, CH; vx, vy = s.VP; C = s.sky.copy()
        for x, y, ph in s.lit:
            if 0 <= x < W and math.sin(t * .2 + ph * 50) > -.4: C[y, x] = hx('#ffe08a') if ph < .7 else hx('#a0f0ff')
        if (t % 1.4) < .7: C[s.tower[1], s.tower[0]] = hx('#ffffff')
        im = Image.fromarray((np.clip(C, 0, 1) * 255).astype('uint8')); d = ImageDraw.Draw(im)
        bot = 236
        d.rectangle([0, vy, W, bot], fill=rgb8('#0b0a1a'))                                                  # 고가 아래 어둠
        d.polygon([(vx - 8, vy), (vx + 8, vy), (W + 260, bot), (-260, bot)], fill=rgb8('#15122a'))      # 고가도로 노면
        for side in (-1, 1):                                                                              # 방음벽 + 위쪽 반사 띠
            d.polygon([(vx + side * 8, vy - 1), (vx + side * 8, vy + 1), (W / 2 + side * (W / 2 + 280), bot), (W / 2 + side * (W / 2 + 280), bot - 60)], fill=rgb8('#221c3c'))
            d.line([(vx + side * 8, vy - 1), (W / 2 + side * (W / 2 + 280), bot - 60)], fill=rgb8('#6a4a8a'), width=2)
        sp = .055
        for i in range(14):                                                                 # 차선 점선 (다가옴)
            z = ((i / 14) + t * sp * 1.6) % 1; z2 = min(1, z + .03)
            ya, yb = vy + (bot - vy) * z ** 2.2, vy + (bot - vy) * z2 ** 2.2
            for lane in (-.55, .55):
                xa, xb = vx + lane * (ya - vy) * 3.2, vx + lane * (yb - vy) * 3.2; wd = max(1, int((yb - vy) / 18))
                d.line([(xa, ya), (xb, yb)], fill=rgb8('#e8e0d0'), width=wd)
        lights = []
        for i in range(8):                                                                  # 가로등 (양쪽, 다가오며 바깥으로)
            z = ((i / 8) + t * sp) % 1; yb = vy + (bot - vy) * z ** 2.2; sc = (yb - vy) / (bot - vy)
            for side in (-1, 1):
                px_ = vx + side * (yb - vy) * 4.4; top = yb - 160 * sc - 4
                d.line([(px_, yb), (px_, top)], fill=rgb8('#3a3458'), width=max(1, int(3 * sc)))
                hxp = px_ - side * 22 * sc; d.line([(px_, top), (hxp, top)], fill=rgb8('#3a3458'), width=max(1, int(2 * sc)))
                lights.append((hxp, top + 2, sc))
        for k in range(2):                                                                  # 앞차 두 대
            z = .5 + .06 * k + .015 * math.sin(t * .3 + k); yb = vy + (bot - vy) * z ** 2.2; sc = (yb - vy) / (bot - vy)
            cx = vx + (-.55 + 1.1 * k) * (yb - vy) * 1.6 + 2 * math.sin(t * .2 + k); cw = 70 * sc; ch_ = 34 * sc
            d.rounded_rectangle([cx - cw / 2, yb - ch_, cx + cw / 2, yb], int(4 * sc) + 1, fill=rgb8('#0e0c1c'))
            d.rectangle([cx - cw / 2 + 2, yb - ch_ * .55, cx - cw / 2 + 2 + cw * .22, yb - ch_ * .4], fill=rgb8('#ff2a3a'))
            d.rectangle([cx + cw / 2 - 2 - cw * .22, yb - ch_ * .55, cx + cw / 2 - 2, yb - ch_ * .4], fill=rgb8('#ff2a3a'))
            lights.append((cx - cw * .35, yb - ch_ * .47, -sc)); lights.append((cx + cw * .35, yb - ch_ * .47, -sc))
        sg = ((t % 26) / 26)                                                                # 가끔 지나가는 초록 표지판
        if sg < .45:
            z = sg / .45; yb = vy + (bot - vy) * z ** 2.2; sc = (yb - vy) / (bot - vy); top = yb - 190 * sc
            d.rectangle([vx + 10 * sc, top - 28 * sc, vx + 150 * sc, top], fill=rgb8('#1f7a4a')); d.rectangle([vx + 14 * sc, top - 24 * sc, vx + 146 * sc, top - 4 * sc], outline=rgb8('#e8f4e8'))
            for k in range(3): d.rectangle([vx + (24 + k * 40) * sc, top - 18 * sc, vx + (50 + k * 40) * sc, top - 12 * sc], fill=rgb8('#e8f4e8'))
        # ── 차 안 (오른쪽 핸들)
        d.polygon([(0, 0), (70, 0), (20, 250), (0, 250)], fill=rgb8('#07060e')); d.polygon([(W, 0), (W - 60, 0), (W - 10, 250), (W, 250)], fill=rgb8('#07060e'))   # A필러
        d.rectangle([0, 0, W, 10], fill=rgb8('#07060e'))
        d.rounded_rectangle([250, 6, 350, 30], 6, fill=rgb8('#0c0a16')); d.rectangle([258, 12, 342, 24], fill=rgb8('#2a2448'))                             # 룸미러
        d.polygon([(0, 236), (W, 236), (W, H), (0, H)], fill=rgb8('#0e0c18')); d.polygon([(0, 236), (W, 236), (W, 250), (0, 252)], fill=rgb8('#1c1828'))       # 대시보드
        # 계기판 (오른쪽)
        for k, (gx, r) in enumerate(((440, 30), (520, 30))):
            d.ellipse([gx - r, 262 - r, gx + r, 262 + r], fill=rgb8('#06060c')); d.arc([gx - r + 3, 262 - r + 3, gx + r - 3, 262 + r - 3], 140, 400, fill=rgb8('#3ae0ff'), width=2)
            for j in range(9):
                a = math.radians(140 + j * 32.5); d.line([(gx + (r - 8) * math.cos(a), 262 + (r - 8) * math.sin(a)), (gx + (r - 4) * math.cos(a), 262 + (r - 4) * math.sin(a))], fill=rgb8('#a0f8ff'))
            a = math.radians(140 + (150 if k == 0 else 100) + 6 * math.sin(t * .7 + k)); d.line([(gx, 262), (gx + (r - 8) * math.cos(a), 262 + (r - 8) * math.sin(a))], fill=rgb8('#ff6a3a'), width=2)
        d.ellipse([400, 230, 560, 390], outline=rgb8('#1a1626'), width=12)                                                                                   # 핸들
        d.rectangle([466, 300, 494, 360], fill=rgb8('#1a1626'))
        # 카세트 카오디오 (가운데)
        d.rectangle([200, 262, 340, 300], fill=rgb8('#16141e')); d.rectangle([204, 266, 336, 296], outline=rgb8('#3a3448'))
        d.rectangle([210, 270, 300, 284], fill=rgb8('#0a1a12'))
        for k in range(14):
            lv = int(6 * (.5 + .5 * math.sin(t * (3 + k * .6) + k)) * (.55 + .45 * math.sin(t * 1.7 + k * .4)))
            for j in range(6):
                if j <= lv: d.point((213 + k * 6, 282 - j * 2), fill=rgb8('#3affa0' if j < 4 else '#ffe04a')); d.point((214 + k * 6, 282 - j * 2), fill=rgb8('#3affa0' if j < 4 else '#ffe04a'))
        d.rectangle([306, 270, 330, 284], fill=rgb8('#0a1a12')); d.text((308, 271), '88.5', fill=rgb8('#3affa0'))
        d.rectangle([212, 288, 300, 291], fill=rgb8('#2a2634'))
        for k in range(5): d.rectangle([214 + k * 18, 292, 226 + k * 18, 295], fill=rgb8('#4a4458'))
        C = np.asarray(im).astype(np.float32) / 255
        L = np.zeros((H, W), bool); Lr = np.zeros((H, W), bool)
        for x, y, sc in lights:
            r = max(1, abs(sc) * 5)
            m = mask(lambda dd: dd.ellipse([x - r, y - r * .6, x + r, y + r * .6], fill=255))
            if sc > 0: paint(C, m, '#ffd890'); L |= m
            else: Lr |= m
        add_glow(C, L, '#ffa040', 7, 1.6); add_glow(C, Lr, '#ff2a3a', 5, 1.8)
        yy, xx = np.mgrid[0:H, 0:W]
        dash = (yy > 250)
        add_glow(C, dash & (np.hypot(xx - 480, yy - 262) < 34) & (np.hypot(xx - 480, yy - 262) > 26), '#3ae0ff', 4, .25)
        g = np.clip(1 - np.abs(yy - vy) / 50, 0, 1) * (yy < vy); C += (g * .14)[..., None] * hx('#ff4f8a')      # 지평선 도시 빛
        return C
    def frame(s, t): return up2(s.draw(t))






def palm(d, x, base, h, t, ph, col='#120a1e', lean=.18):
    pts = []
    for k in range(13):
        u = k / 12; pts.append((x + lean * h * u * u + 3 * math.sin(t * .6 + ph) * u * u, base - h * u))
    for k in range(12): d.line([pts[k], pts[k + 1]], fill=rgb8(col), width=max(2, int(6 - k * .35)))
    tx, ty = pts[-1]
    for j in range(9):                                                                       # 잎: 줄기 + 양옆 작은 잎 (바람에 살랑)
        a = -math.pi / 2 + (j - 4) * .5 + .07 * math.sin(t * .9 + ph + j); L = h * .4
        side = 1 if math.cos(a) >= 0 else -1; prev = (tx, ty); pts2 = []
        for k in range(1, 11):
            u = k / 10
            p = (tx + math.cos(a) * L * u, ty + math.sin(a) * L * u * .6 + (L * .45) * u * u * (1 if abs(math.cos(a)) > .25 else .3))
            pts2.append((p, u)); d.line([prev, p], fill=rgb8(col), width=3 if u < .5 else 2); prev = p
        for k in range(1, len(pts2) - 1):                                                    # 잎맥에서 아래로 늘어진 작은 잎들
            (px1, py1), u = pts2[k]; ln = 14 * (1 - u * .6)
            dx, dy = pts2[k + 1][0][0] - px1, pts2[k + 1][0][1] - py1; nn = math.hypot(dx, dy) + 1e-6
            for sg in (-1, 1):
                ex = px1 + (-dy / nn * sg * .7 + dx / nn * .5) * ln; ey = py1 + (dx / nn * sg * .7 + dy / nn * .5) * ln + ln * .5
                d.line([(px1, py1), (ex, ey)], fill=rgb8(col), width=2)


class CpBoulevard:
    """80년대 미국 해변 대로: 줄무늬 노을 해 · 야자수 · 아르데코 호텔 네온 · 오픈카 · 바다 반짝임"""
    PIXEL = True; CITYPOP = True
    def __init__(s, seed=1, pal=None):
        R = np.random.default_rng(seed); s.R = R; W, H = CW, CH
        S = dgrad([(0, '#1a1050'), (.18, '#4a1f7a'), (.36, '#b0307a'), (.48, '#ff5a6a'), (.56, '#ff9a5a'), (.6, '#ffc870')], H, W)
        s.hz = 214; yy, xx = np.mgrid[0:H, 0:W]
        st = (R.random((H, W)) < .002) & (yy < 70); S[st] = hx('#ffe8ff')
        s.sun = (230, s.hz - 6, 70)
        s.sky = S; s.sea = dgrad([(0, '#ff7a7a'), (.25, '#b04a8a'), (1, '#2a2068')], H - s.hz, W)
        s.font = ImageFont.truetype(FONT, 22) if os.path.exists(FONT) else None
        s.gulls = [(float(R.uniform(0, 640)), float(R.uniform(40, 120)), float(R.uniform(8, 14))) for _ in range(3)]
    def draw(s, t):
        W, H = CW, CH; C = s.sky.copy(); cx, cy, r = s.sun; hz = s.hz
        yy, xx = np.mgrid[0:H, 0:W]
        m = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
        cut = ((yy - cy + t * 1.5) % 10 < np.clip((yy - (cy - 30)) / 7, 0, 6)) & (yy > cy - 30)
        sun = dgrad([(0, '#fff4a0'), (.5, '#ffb050'), (1, '#ff3a7a')], H, W)
        sm = m & ~cut & (yy < hz); C[sm] = sun[sm]
        add_glow(C, m & (yy < hz), '#ff8a5a', 24, .5)
        for k, (cy_, cl, sp) in enumerate(((70, 150, 1.5), (96, 220, 2.2), (124, 120, 1.1))):      # 길쭉한 구름
            ccx = (100 + k * 210 + t * sp) % (W + 300) - 150
            cm = ((xx - ccx) / cl) ** 2 + ((yy - cy_) / 4) ** 2 <= 1; C[cm] = C[cm] * .3 + hx('#ff8ab8' if k != 1 else '#7a3a9a') * .7
        C[hz:] = s.sea
        for k in range(40):                                                                  # 해 반사
            y = hz + 2 + (k * 5) % 60; w_ = int(6 + (y - hz) * .9) * (1 if math.sin(t * 1.7 + k * 2.3) > -.3 else 0)
            x = cx - w_ // 2 + int(6 * math.sin(t * .8 + k))
            if w_: C[y, max(0, x):x + w_] = hx('#ffd080') * .8 + C[y, max(0, x):x + w_] * .2
        im = Image.fromarray((np.clip(C, 0, 1) * 255).astype('uint8')); d = ImageDraw.Draw(im)
        for gx, gy, sp in s.gulls:                                                           # 갈매기
            x = (gx + t * sp) % (W + 40) - 20; y = gy + 3 * math.sin(t + gx); f = 2 + int(2 * (math.sin(t * 4 + gx) > 0))
            d.line([(x - 5, y - f), (x, y), (x + 5, y - f)], fill=rgb8('#2a1440'))
        # 호텔 (오른쪽, 아르데코: 둥근 모서리 + 파스텔 + 네온 띠)
        hx0, hy0 = 410, 70
        d.rectangle([hx0, hy0, 640, 300], fill=rgb8('#f2a8b8')); d.pieslice([hx0 - 40, hy0, hx0 + 40, hy0 + 80], 180, 270, fill=rgb8('#f2a8b8'))
        d.rectangle([hx0 - 40, hy0 + 40, hx0, 300], fill=rgb8('#f2a8b8'))
        d.rectangle([hx0 - 40, hy0 + 40, hx0 - 30, 300], fill=rgb8('#d88aa0'))
        for k in range(9):
            y = hy0 + 24 + k * 24
            d.rectangle([hx0 - 34, y, 640, y + 3], fill=rgb8('#3ad8d0'))                         # 가로 띠
            for j in range(9):
                wx = hx0 - 20 + j * 24; lit = (math.sin(j * 3.1 + k * 1.7) > -.1)
                d.rectangle([wx, y + 8, wx + 12, y + 18], fill=rgb8('#ffe0a0' if lit else '#6a4a7a'))
        d.rectangle([hx0 + 60, hy0 - 40, hx0 + 200, hy0], fill=rgb8('#1a0e2a'))               # 옥상 간판
        on = not (9.0 < (t % 15) < 9.2)
        if s.font is not None and on:
            for dx, dy, c in ((0, 0, '#ff4fd0'),): d.text((hx0 + 74 + dx, hy0 - 36 + dy), 'HOTEL', font=s.font, fill=rgb8(c))
            d.text((hx0 + 144, hy0 - 32), '★', font=ImageFont.truetype(FONT, 11), fill=rgb8('#3affe0'))
        # 해변 도로 + 인도
        d.rectangle([0, 268, W, H], fill=rgb8('#2a1a3a')); d.rectangle([0, 262, W, 270], fill=rgb8('#e8b8a8'))
        d.rectangle([0, 300, W, H], fill=rgb8('#1e1430'))
        for k in range(10): d.rectangle([k * 80 - int(t * 0) % 80, 330, k * 80 + 40, 333], fill=rgb8('#f0d080'))
        # 야자수
        for x, h, ph, lean in ((70, 210, 0, .2), (150, 170, 1.3, -.1), (360, 230, 2.1, .12), (600, 190, .7, -.18)):
            palm(d, x, 268, h, t, ph, lean=lean)
        # 오픈카 (흰색, 크롬)
        cx0 = 190
        d.polygon([(cx0, 308), (cx0 + 14, 292), (cx0 + 60, 288), (cx0 + 82, 280), (cx0 + 120, 280), (cx0 + 140, 290), (cx0 + 190, 294), (cx0 + 196, 312), (cx0, 314)], fill=rgb8('#f4eef4'))
        d.line([(cx0 + 4, 300), (cx0 + 192, 302)], fill=rgb8('#3ad8d0'), width=2)
        d.polygon([(cx0 + 86, 280), (cx0 + 96, 266), (cx0 + 100, 266), (cx0 + 94, 280)], fill=rgb8('#8ad0f0'))
        for wx in (cx0 + 36, cx0 + 160): d.ellipse([wx - 13, 302, wx + 13, 328], fill=rgb8('#120a1a')); d.ellipse([wx - 6, 309, wx + 6, 321], fill=rgb8('#c8c0d0'))
        d.rectangle([cx0 + 190, 298, cx0 + 196, 302], fill=rgb8('#ff3a4a'))
        C = np.asarray(im).astype(np.float32) / 255
        warm = np.clip(1 - np.hypot((xx - cx) / 500, (yy - cy) / 300), 0, 1)
        C = C * (.85 + .3 * warm[..., None] * np.array([1, .8, .7]))
        if s.font is not None and on:
            nm = (np.abs(C - hx('#ff4fd0')).sum(-1) < .12) & (yy < 80) & (xx > 450); add_glow(C, nm, '#ff4fd0', 4, 1.2)
        return C
    def frame(s, t): return up2(s.draw(t))




CP_SCENES = {'cp_room': CpRoom, 'cp_drive': CpDrive, 'cp_boulevard': CpBoulevard}
CP_KO = {'cp_room': '버블 시대 맨션의 노을', 'cp_drive': '밤의 고속도로 드라이브', 'cp_boulevard': '80년대 해변 대로'}
