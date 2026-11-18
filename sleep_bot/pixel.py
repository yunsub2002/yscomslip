#!/usr/bin/env python3
"""드림코어 도트(픽셀아트) 장면 — 외부 이미지 0개, 전부 코드로 그림.
320x180 도트 캔버스에 그린 뒤 4배로 '각지게' 키워 1280x720 (출력 1920x1080 = 정확히 6배 도트).
장면 6종:
  px_train 막차 창밖 · px_city 노을 도시 옥상 · px_room 비 오는 방과 CRT · px_clouds 구름 복도(체크무늬 바닥)
  px_pool 밤의 실내 수영장 · px_street 비 오는 편의점 거리
"""
import math
import numpy as np

PW, PH = 320, 180          # 도트 캔버스
UP = 4                     # 1280x720 으로 확대
BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) + .5) / 16


def hx(h):
    h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


def dgrad(stops, h=PH, w=PW, y0=0):
    """세로 그라데이션을 색 몇 개로만 칠하고 그 사이를 바이어 디더링 (도트 느낌)"""
    cols = [hx(c) for _, c in stops]; pos = [p for p, _ in stops]
    y = (np.arange(h, dtype=np.float32) + y0) / (PH if h == PH else h)
    t = np.interp(y, pos, np.arange(len(stops), dtype=np.float32))              # 0..n-1 연속값
    base = np.floor(t).astype(int); frac = t - base
    yy, xx = np.mgrid[0:h, 0:w]; thr = BAYER[yy % 4, xx % 4]
    idx = np.clip(base[:, None] + (frac[:, None] > thr), 0, len(cols) - 1)
    return np.stack(cols)[idx].astype(np.float32)


def rect(C, x, y, w, h, col, a=1.0):
    x0, y0 = max(0, int(x)), max(0, int(y)); x1, y1 = min(C.shape[1], int(x + w)), min(C.shape[0], int(y + h))
    if x1 > x0 and y1 > y0: C[y0:y1, x0:x1] = C[y0:y1, x0:x1] * (1 - a) + col * a


def px(C, x, y, col, a=1.0):
    x, y = int(x), int(y)
    if 0 <= x < C.shape[1] and 0 <= y < C.shape[0]: C[y, x] = C[y, x] * (1 - a) + col * a


def disc(C, cx, cy, r, col, a=1.0):
    y0, y1 = max(0, int(cy - r - 1)), min(C.shape[0], int(cy + r + 2)); x0, x1 = max(0, int(cx - r - 1)), min(C.shape[1], int(cx + r + 2))
    if y1 <= y0 or x1 <= x0: return
    yy, xx = np.mgrid[y0:y1, x0:x1]; m = ((xx - cx) ** 2 + (yy - cy) ** 2) <= r * r
    C[y0:y1, x0:x1][m] = C[y0:y1, x0:x1][m] * (1 - a) + col * a


def glow(C, cx, cy, r, col, a=.35):
    """둥근 빛 번짐을 디더링으로 (계단식 원 3겹)"""
    for k, f in ((1.0, .35), (.66, .6), (.36, 1.0)): disc(C, cx, cy, r * k, col, a * f)


def cloud(C, cx, cy, s, col, shade):
    for dx, dy, r in ((0, 0, 1.0), (-1.3, .25, .75), (1.3, .3, .8), (-.6, -.45, .7), (.7, -.4, .65), (2.2, .45, .5), (-2.1, .5, .5)):
        disc(C, cx + dx * s, cy + dy * s, r * s, col)
    rect(C, cx - 2.4 * s, cy + .55 * s, 4.8 * s, .5 * s + 1, shade)


def strip(seed, w, hmin, hmax, wmin, wmax, gap=(0, 3)):
    """가로로 이어지는 건물 실루엣 높이 배열 (w 픽셀, 끝과 처음이 이어짐)"""
    R = np.random.default_rng(seed); hs = np.zeros(w, np.int32); x = 0; boxes = []
    while x < w:
        bw = int(R.integers(wmin, wmax + 1)); bh = int(R.integers(hmin, hmax + 1)); hs[x:x + bw] = bh; boxes.append((x, bw, bh)); x += bw + int(R.integers(*gap))
    return hs, boxes


def up(C):
    return np.repeat(np.repeat(np.clip(C, 0, 1), UP, axis=0), UP, axis=1)


class PxScene:
    PIXEL = True
    def __init__(s, seed, pal=None): s.R = np.random.default_rng(seed); s.seed = seed; s.setup()
    def setup(s): pass
    def draw(s, t): raise NotImplementedError
    def frame(s, t): return up(s.draw(t))


# ───────────────────────────────────────────── 1. 막차 창밖
class PxTrain(PxScene):
    def setup(s):
        R = s.R
        s.sky = dgrad([(0, '#1b1440'), (.22, '#3a2368'), (.42, '#7a3f86'), (.55, '#d36f8f'), (.62, '#f2a27a')], h=110)
        far, _ = strip(int(R.integers(1e6)), 640, 8, 26, 6, 16, (0, 2)); mid, midb = strip(int(R.integers(1e6)), 640, 18, 52, 10, 26, (2, 9))
        yy = np.arange(96)[:, None]
        s.far_m = (yy >= 82 - far[None, :]) & (yy < 82)                         # 먼 건물 (가로 640, 이어짐)
        s.mid_m = (yy >= 96 - mid[None, :])
        s.mid_c = np.zeros((96, 640, 3), np.float32); s.mid_c[:] = hx('#241a40'); s.blink = []
        for x, bw, bh in midb:
            for _ in range(max(1, bw * bh // 40)):
                wx_, wy_ = x + int(R.integers(2, max(3, bw - 2))), int(R.integers(3, max(4, bh - 3))); col = hx('#ffd27a') if R.random() < .7 else hx('#9fe8ff')
                if wx_ + 2 <= 640: s.mid_c[96 - wy_, wx_:wx_ + 2] = col
                if R.random() < .12: s.blink.append((wx_ % 640, 96 - wy_, float(R.uniform(0, 6.3))))
        s.stars = [(int(R.integers(0, 640)), int(R.integers(2, 40)), float(R.uniform(0, 6.3))) for _ in range(60)]
        s.moonbg = s.sky[28, 238].copy()
        s.wall = hx('#2b2347'); s.wall2 = hx('#221c3a'); s.seat = hx('#6b2f4f'); s.seat2 = hx('#8a3d5f'); s.metal = hx('#9a93b8')
    def draw(s, t):
        C = np.zeros((PH, PW, 3), np.float32); C[:] = s.wall
        bob = 1 if (t % 1.1) < .08 else 0                                        # 레일 이음새에서 살짝 덜컹
        wx, wy, ww, wh = 18, 22, 284, 96
        V = s.sky[:96, :ww].copy()
        for x, y, ph in s.stars:
            xx = int((x - t * 1.0) % 640)
            if xx < ww and .5 + .5 * math.sin(t * 1.3 + ph) > .35: px(V, xx, y, hx('#fff2d6'), .9)
        disc(V, 232, 30, 7, hx('#ffe9c4')); disc(V, 236, 27, 6, s.moonbg)       # 초승달
        off_f = int(t * 6) % 640; off_m = int(t * 22) % 640
        fm = np.roll(s.far_m, -off_f, axis=1)[:, :ww]; V[fm] = hx('#4a2f6e')
        mm = np.roll(s.mid_m, -off_m, axis=1)[:, :ww]; mc = np.roll(s.mid_c, -off_m, axis=1)[:, :ww]; V[mm] = mc[mm]
        for x0, y, ph in s.blink:
            xx = (x0 - off_m) % 640
            if xx < ww - 1 and math.sin(t * .4 + ph) < -.3: rect(V, xx, y, 2, 1, hx('#241a40'))
        for k in range(3):                                                       # 지나가는 전신주
            xp = int((k * 230 - t * 70) % 690) - 30
            rect(V, xp, 0, 3, 96, hx('#120d22')); rect(V, xp - 6, 10, 15, 1, hx('#120d22'))
        V = V * .92 + hx('#3a2a66') * .08                                        # 유리 색
        C[wy:wy + wh, wx:wx + ww] = V
        rect(C, wx + ww // 2 - 2, wy, 4, wh, s.wall2)                            # 창틀
        for e in ((wx - 3, wy - 3, ww + 6, 3), (wx - 3, wy + wh, ww + 6, 4), (wx - 3, wy, 3, wh), (wx + ww, wy, 3, wh)): rect(C, *e, s.wall2)
        rect(C, 0, 2, PW, 4, hx('#e9e4ff'), .85); rect(C, 0, 6, PW, 1, hx('#8f86c4'))   # 천장 조명
        rect(C, 0, 12, PW, 2, s.metal)                                          # 손잡이 봉
        for k in range(9):                                                       # 흔들리는 손잡이
            sx = 26 + k * 34 + int(round(1.5 * math.sin(t * 1.4 + k * .7))); rect(C, sx, 14, 1, 7, s.metal); rect(C, sx - 2, 21, 5, 4, s.metal); rect(C, sx - 1, 22, 3, 2, s.wall)
        rect(C, 0, 128 + bob, PW, 52, s.seat); rect(C, 0, 128 + bob, PW, 3, s.seat2)    # 좌석
        for k in range(8): rect(C, k * 42 + 18, 131 + bob, 1, 49, hx('#4e2139'))
        rect(C, 0, 118 + bob, PW, 10, s.wall2)
        return C


# ───────────────────────────────────────────── 2. 노을 도시 옥상
class PxCity(PxScene):
    def setup(s):
        R = s.R
        s.sky = dgrad([(0, '#16123a'), (.18, '#352a6e'), (.36, '#7b4a9a'), (.5, '#e0779c'), (.62, '#ffb38a'), (.7, '#ffd9a0')])
        s.city, s.cityb = strip(int(R.integers(1e6)), PW, 16, 58, 8, 22, (0, 2))
        s.win = [(x + int(R.integers(1, max(2, bw - 1))), int(R.integers(3, max(4, bh - 2))), float(R.uniform(0, 1))) for x, bw, bh in s.cityb for _ in range(max(1, bw * bh // 30))]
        s.win = [w for w in s.win if w[0] < PW]
        s.cl = [(float(R.uniform(0, 420)), float(R.uniform(14, 60)), float(R.uniform(5, 9)), float(R.uniform(1.5, 3.5))) for _ in range(5)]
        s.stars = [(int(R.integers(0, PW)), int(R.integers(2, 40)), float(R.uniform(0, 6.3))) for _ in range(40)]
    def draw(s, t):
        C = s.sky.copy()
        for x, y, ph in s.stars:
            if .5 + .5 * math.sin(t * 1.1 + ph) > .45: px(C, x, y, hx('#fff2e0'), .8)
        cx, cy, r = 160, 112, 34                                                 # 줄무늬 해 (천천히 내려가는 줄)
        yy, xx = np.mgrid[0:PH, 0:PW]; m = ((xx - cx) ** 2 + (yy - cy) ** 2 <= r * r) & (yy < 126)
        band = ((yy - cy + t * 2.0) % 9 < (2 + np.clip((yy - cy + 6) / 6, 0, 4))) & (yy > cy - 6)
        sun = dgrad([(0, '#fff3b0'), (.5, '#ffb070'), (1, '#ff5f8f')], h=PH)
        C[m & ~band] = sun[m & ~band]
        for x0, y, sp, sc in s.cl:
            x = (x0 + t * sp) % 420 - 50; cloud(C, x, y, sc * 2.2, hx('#f7c3d6'), hx('#c9809f'))
        base = 140
        for x in range(PW): C[base - s.city[x]:base, x] = hx('#2a1a48')
        for x, y, ph in s.win:
            if s.city[x] > y + 1 and math.sin(t * .15 + ph * 20) > -.4: px(C, x, base - y, hx('#ffd98a') if ph < .75 else hx('#a8f0ff'), .95)
        tx = 250; rect(C, tx, base - 80, 2, 80, hx('#2a1a48')); rect(C, tx - 3, base - 60, 8, 1, hx('#2a1a48'))   # 송신탑
        if (t % 2.4) < 1.1: glow(C, tx + 1, base - 81, 3, hx('#ff4f6f'), .9)
        rect(C, 0, base, PW, PH - base, hx('#1c1233'))                            # 옥상
        for k in range(0, PW, 10): rect(C, k, base - 10, 1, 10, hx('#140d26'))      # 난간
        rect(C, 0, base - 10, PW, 1, hx('#140d26')); rect(C, 0, base - 5, PW, 1, hx('#140d26'))
        rect(C, 30, base - 26, 22, 26, hx('#140d26')); rect(C, 28, base - 28, 26, 3, hx('#140d26'))   # 물탱크
        vx = 270; rect(C, vx, base - 1, 18, 30, hx('#3a63c9')); rect(C, vx + 2, base + 2, 14, 10, hx('#bfe9ff'))   # 자판기
        for k in range(3): rect(C, vx + 3 + k * 4, base + 5, 3, 5, [hx('#ff6f8f'), hx('#ffd36f'), hx('#7fffd0')][k])
        glow(C, vx + 9, base + 10, 16, hx('#7fbfff'), .18)
        return C


# ───────────────────────────────────────────── 3. 비 오는 방과 CRT
class PxRoom(PxScene):
    def setup(s):
        R = s.R
        s.bg = dgrad([(0, '#141a33'), (1, '#1d2344')])
        s.out = dgrad([(0, '#0b1030'), (.6, '#27215a'), (1, '#4a2f6e')], h=70, w=110)
        s.bk = [(float(R.uniform(0, 110)), float(R.uniform(25, 68)), float(R.uniform(1, 2.5)), ['#ffb36b', '#ff7fb0', '#7fd0ff', '#ffe08a'][int(R.integers(4))], float(R.uniform(0, 6.3))) for _ in range(22)]
        s.rain = [(float(R.uniform(0, 110)), float(R.uniform(0, 70)), float(R.uniform(40, 70))) for _ in range(40)]
        s.drops = [(float(R.uniform(2, 108)), float(R.uniform(0, 70)), float(R.uniform(3, 9))) for _ in range(9)]
    def draw(s, t):
        C = s.bg.copy()
        wx, wy, ww, wh = 196, 26, 110, 70                                        # 창문
        V = s.out.copy()
        for x, y, r, c, ph in s.bk: disc(V, x, y, r, hx(c), .55 + .25 * math.sin(t * .7 + ph))
        for x, y, v in s.rain:
            yy = (y + v * t) % 76 - 4; xx = (x - .15 * v * t) % 110
            rect(V, xx, yy, 1, 3, hx('#9fb8ff'), .6)
        for x, y0, sp in s.drops:
            yy = (y0 + sp * t) % 74; rect(V, x, yy, 1, 2, hx('#d8e6ff'), .9); rect(V, x, yy - 3, 1, 3, hx('#d8e6ff'), .3)
        C[wy:wy + wh, wx:wx + ww] = V
        for e in ((wx - 3, wy - 3, ww + 6, 3), (wx - 3, wy + wh, ww + 6, 4), (wx - 3, wy, 3, wh), (wx + ww, wy, 3, wh), (wx + ww // 2 - 1, wy, 2, wh), (wx, wy + wh // 2 - 1, ww, 2)):
            rect(C, *e, hx('#2e2a52'))
        rect(C, wx - 6, wy + wh + 4, ww + 12, 3, hx('#3a3566'))
        rect(C, 0, 132, PW, 48, hx('#191e3a'))                                  # 바닥
        # 침대 + 자는 고양이
        rect(C, 8, 104, 120, 30, hx('#3b3f7a')); rect(C, 8, 100, 120, 6, hx('#5b5fb0')); rect(C, 8, 96, 10, 40, hx('#2a2a55'))
        rect(C, 22, 92, 28, 10, hx('#d8d4f0')); rect(C, 60, 98, 68, 8, hx('#6d4fa0'))
        br = 1 if (t % 4.0) < 2.0 else 0
        cx = 88; rect(C, cx, 92 - br, 16, 7 + br, hx('#f0a86a')); rect(C, cx + 13, 89 - br, 6, 6, hx('#f0a86a'))
        px(C, cx + 14, 88 - br, hx('#f0a86a')); px(C, cx + 18, 88 - br, hx('#f0a86a')); rect(C, cx + 15, 92 - br, 3, 1, hx('#7a4a2a'))
        rect(C, cx - 4, 96, 6, 2, hx('#f0a86a'))
        # 책상 + CRT
        rect(C, 140, 112, 70, 4, hx('#5a3a3a')); rect(C, 144, 116, 4, 22, hx('#4a2e2e')); rect(C, 202, 116, 4, 22, hx('#4a2e2e'))
        mx, my = 150, 78; rect(C, mx, my, 44, 34, hx('#c9c3d8')); rect(C, mx + 3, my + 3, 38, 26, hx('#0d1a2a'))
        fl = .85 + .15 * math.sin(t * 17) * math.sin(t * 3.1)
        for k in range(6):                                                       # 화면 속 천천히 흐르는 글줄
            yy = my + 6 + ((k * 4 - int(t * 3)) % 24); ln = 6 + int(14 * (.5 + .5 * math.sin(k * 2.3 + int(t * 3 + k) // 8)))
            if yy < my + 28: rect(C, mx + 6, yy, ln, 1, hx('#7fffd0'), .8 * fl)
        if (t % 1.0) < .5: rect(C, mx + 6, my + 25, 3, 2, hx('#7fffd0'), fl)
        glow(C, mx + 22, my + 16, 30, hx('#5fe0d0'), .07 * fl)
        rect(C, mx + 14, my + 34, 16, 4, hx('#a7a0bd'))
        # 스탠드
        lx = 196; rect(C, lx, 92, 2, 20, hx('#c0b090')); rect(C, lx - 6, 86, 14, 7, hx('#ffcf7a'))
        glow(C, lx + 1, 96, 22, hx('#ffc070'), .12)
        # 화분
        rect(C, 290, 118, 14, 14, hx('#b0603a'));
        for k, (dx, h) in enumerate(((-4, 14), (0, 20), (4, 16), (8, 12), (-7, 9))): rect(C, 296 + dx, 118 - h, 2, h, hx('#3f8f5a'))
        return C


# ───────────────────────────────────────────── 4. 구름 복도 (드림코어)
class PxClouds(PxScene):
    def setup(s):
        R = s.R
        s.sky = dgrad([(0, '#8fa8ff'), (.3, '#b9b4ff'), (.5, '#f5c4e8'), (.58, '#ffe0d6')])
        s.cl = [(float(R.uniform(0, 420)), float(R.uniform(8, 70)), float(R.uniform(1.5, 4)), float(R.uniform(2, 4.5))) for _ in range(9)]
        s.sp = [(int(R.integers(0, PW)), int(R.integers(5, 90)), float(R.uniform(0, 6.3))) for _ in range(30)]
        hz = 104; s.hz = hz
        yy, xx = np.mgrid[hz:PH, 0:PW].astype(np.float32); s.z = 300.0 / (yy - hz + 2.0); s.xw = (xx - PW / 2) * s.z / 160.0
        s.fog = np.clip(1 - (yy - hz) / 16, 0, 1) ** 1.3
    def draw(s, t):
        C = s.sky.copy()
        for x, y, ph in s.sp:
            if math.sin(t * 2 + ph) > .6: px(C, x, y, hx('#ffffff')); px(C, x - 1, y, hx('#ffffff'), .5); px(C, x + 1, y, hx('#ffffff'), .5)
        for x0, y, sp, sc in s.cl:
            x = (x0 + t * sp) % 420 - 50; cloud(C, x, y, sc * 2.3, hx('#ffffff'), hx('#e7d8ff'))
        zz = s.z - t * .5                                                       # 바닥이 천천히 다가옴
        chk = ((np.floor(s.xw).astype(int) + np.floor(zz).astype(int)) % 2 == 0)
        fl = np.where(chk[..., None], hx('#ffd3ec'), hx('#ffffff')).astype(np.float32)
        thr = BAYER[(np.arange(s.hz, PH)[:, None]) % 4, np.arange(PW)[None, :] % 4]
        mix = (s.fog > thr)[..., None]
        C[s.hz:] = np.where(mix, hx('#ffe9f2'), fl)
        # 떠 있는 문틀 + 아치
        dx, dy = 150, 58 + int(round(2 * math.sin(t * .5)))
        rect(C, dx, dy, 22, 40, hx('#ffffff')); rect(C, dx + 3, dy + 3, 16, 37, hx('#aee7ff'))
        rect(C, dx + 3, dy + 3, 16, 37, hx('#fff7c8'), .35 + .25 * math.sin(t * .8)); px(C, dx + 16, dy + 22, hx('#e0b860'))
        rect(C, dx - 2, dy + 40, 26, 2, hx('#e7d8ff'))
        for ax in (40, 248):                                                     # 양옆 기둥 아치
            rect(C, ax, 72, 6, 34, hx('#ffffff')); rect(C, ax + 26, 72, 6, 34, hx('#ffffff')); rect(C, ax, 66, 32, 7, hx('#ffffff')); rect(C, ax + 6, 73, 20, 2, hx('#f0e6ff'))
        return C


# ───────────────────────────────────────────── 5. 밤의 실내 수영장
class PxPool(PxScene):
    def setup(s):
        s.wall = dgrad([(0, '#0e2a3a'), (1, '#174a5a')], h=100)
        yy, xx = np.mgrid[0:60, 0:PW].astype(np.float32); s.yy, s.xx = yy, xx
    def draw(s, t):
        C = np.zeros((PH, PW, 3), np.float32); C[:100] = s.wall
        for y in range(4, 100, 8): rect(C, 0, y, PW, 1, hx('#0b2230'))            # 타일 줄눈
        for x in range(0, PW, 8): rect(C, x, 0, 1, 100, hx('#0b2230'))
        for k, wx in enumerate((30, 120, 210)):                                   # 높은 창 (밤하늘)
            rect(C, wx, 12, 70, 34, hx('#081428')); rect(C, wx + 34, 12, 2, 34, hx('#1a3a4a')); rect(C, wx, 28, 70, 2, hx('#1a3a4a'))
            for j in range(6): px(C, wx + 5 + (j * 13 + k * 7) % 64, 15 + (j * 7) % 12, hx('#dfefff'), .5 + .5 * math.sin(t + j + k))
        for x in (60, 160, 260): rect(C, x - 10, 0, 20, 3, hx('#f4fbff')); glow(C, x, 3, 14, hx('#d8f6ff'), .1)
        rect(C, 0, 100, PW, 20, hx('#d9eef0')); [rect(C, x, 100, 1, 20, hx('#b7d4d8')) for x in range(0, PW, 10)]
        # 물: 일렁이는 빛 무늬 (양자화)
        w = (np.sin(s.xx * .21 + t * 1.3 + np.sin(s.yy * .35 - t)) + np.sin(s.xx * .07 - s.yy * .4 + t * .9)) * .5
        lv = np.floor((w + 1) * 2.5).astype(int).clip(0, 4)
        pal = np.stack([hx('#0a5a7a'), hx('#0e7290'), hx('#1690a8'), hx('#3ab8c8'), hx('#9ff0f0')])
        C[120:180] = pal[lv]
        for x in (60, 160, 260): rect(C, x - 8, 122 + int(2 * math.sin(t * 1.5 + x)), 16, 2, hx('#e8ffff'), .7)   # 조명 반사
        for x in (40, 52): rect(C, x, 96, 2, 34, hx('#c8d8e0'))                   # 사다리
        for y in (104, 112, 120): rect(C, 40, y, 14, 1, hx('#c8d8e0'))
        rect(C, 0, 119, PW, 1, hx('#0a3a50'))
        return C


# ───────────────────────────────────────────── 6. 비 오는 편의점 거리
class PxStreet(PxScene):
    def setup(s):
        R = s.R
        s.sky = dgrad([(0, '#0c0b22'), (.5, '#1d1840'), (.7, '#2e2458')])
        s.rain = [(float(R.uniform(0, PW)), float(R.uniform(0, PH)), float(R.uniform(90, 140))) for _ in range(140)]
        s.bld, _ = strip(int(R.integers(1e6)), PW, 30, 80, 14, 34, (0, 1))
        s.rip = [(float(R.uniform(10, 310)), float(R.uniform(138, 176)), float(R.uniform(0, 1.5))) for _ in range(16)]
    def draw(s, t):
        C = s.sky.copy(); gy = 128
        for x in range(PW): C[gy - s.bld[x]:gy, x] = hx('#151230')
        for y in (18, 24): rect(C, 0, y + int(2 * math.sin(y)), PW, 1, hx('#0a0918'))     # 전선
        rect(C, 40, 10, 3, 118, hx('#0a0918')); rect(C, 34, 18, 15, 2, hx('#0a0918'))
        # 편의점
        sx, sw = 150, 140
        rect(C, sx, 66, sw, 62, hx('#2b2f46')); rect(C, sx, 66, sw, 10, hx('#f4f7ff'))
        for k, c in enumerate(('#2fb06a', '#3b7cf0', '#ff6f8f')): rect(C, sx + 4 + k * 46, 68, 40, 6, hx(c))
        rect(C, sx + 8, 82, sw - 16, 42, hx('#dff6ff'))
        for k in range(4): rect(C, sx + 12 + k * 30, 92, 22, 2, hx('#8fb8d0')); rect(C, sx + 12 + k * 30, 104, 22, 2, hx('#8fb8d0'))
        rect(C, sx + 58, 84, 24, 40, hx('#bfe6f6'))
        glow(C, sx + sw / 2, 104, 70, hx('#d0f2ff'), .1)
        # 자판기 두 대
        for k, (vx, c) in enumerate(((100, '#e0384f'), (122, '#2f6fe0'))):
            rect(C, vx, 92, 18, 36, hx(c)); rect(C, vx + 2, 95, 14, 14, hx('#f6fbff'))
            for j in range(3): rect(C, vx + 3 + j * 4, 98, 3, 6, hx(['#ffd36f', '#7fffd0', '#ff9fd0'][j]))
            glow(C, vx + 9, 106, 14, hx(c), .14)
        # 네온 간판 (가끔 깜빡)
        on = not (8.0 < (t % 13.0) < 8.25 or 8.4 < (t % 13.0) < 8.5)
        nx, ny = 58, 50
        if on:
            disc(C, nx + 6, ny + 7, 7, hx('#ff6fd8')); disc(C, nx + 9, ny + 5, 6, C[ny + 5, nx + 22])                      # 네온 초승달
            for dx, dy, w_, h_ in ((18, 0, 8, 2), (24, 0, 2, 7), (18, 6, 8, 2), (18, 6, 2, 8), (18, 12, 8, 2), (30, 0, 2, 8), (30, 6, 8, 2), (36, 0, 2, 14)):
                rect(C, nx + dx, ny + dy, w_, h_, hx('#7ff6ff'))                                                             # 24
            glow(C, nx + 20, ny + 7, 28, hx('#ff6fd8'), .13)
        # 바닥 + 물웅덩이 반사
        rect(C, 0, gy, PW, PH - gy, hx('#121024'))
        refl = C[gy - 52:gy][::-1].copy()
        for y in range(refl.shape[0]):
            sh = int(round(1.5 * math.sin(t * 2.2 + y * .9)))
            refl[y] = np.roll(refl[y], sh, axis=0)
        C[gy:gy + 52] = C[gy:gy + 52] * .55 + refl * .45
        for x, y, ph in s.rip:
            k = ((t + ph) % 1.5) / 1.5; r = int(1 + k * 5)
            if k < .8: rect(C, x - r, y, 2 * r + 1, 1, hx('#a8b8ff'), .5 * (1 - k))
        for x, y, v in s.rain:
            yy = (y + v * t) % (PH + 6) - 6; xx = (x - .12 * v * t) % PW
            rect(C, xx, yy, 1, 4, hx('#9aa8e8'), .55)
        return C


PX_SCENES = {'px_train': PxTrain, 'px_city': PxCity, 'px_room': PxRoom, 'px_clouds': PxClouds, 'px_pool': PxPool, 'px_street': PxStreet}
PX_KO = {'px_train': '막차 창밖', 'px_city': '노을 도시 옥상', 'px_room': '비 오는 방', 'px_clouds': '구름 복도', 'px_pool': '밤의 수영장', 'px_street': '비 오는 편의점 거리'}


def grade_px(f):
    """도트 장면용 후처리: 밝은 곳만 살짝 번지게 + CRT 주사선 (그레인·카메라 이동 없음 → 도트가 또렷하게)"""
    from scipy.ndimage import gaussian_filter
    small = f[::4, ::4]; bl = gaussian_filter(np.clip(small - .6, 0, 1), (2.5, 2.5, 0))
    f = f + np.repeat(np.repeat(bl, 4, 0), 4, 1)[:f.shape[0], :f.shape[1]] * .45
    f = f.copy(); f[3::4] *= .88                                                 # 주사선
    return np.clip(f, 0, 1)
