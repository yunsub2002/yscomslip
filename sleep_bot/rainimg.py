#!/usr/bin/env python3
"""채널 주인이 준 그림(assets/*.png)을 그대로 배경으로 쓰고, 그 위에 비만 내리게 하는 장면.
그림은 손대지 않음 — 빗줄기 3겹(먼·중간·가까운) + 바닥에 튀는 물방울·번지는 물결만 얹음. 실내 그림은 창 영역에만 비.
"""
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
W, H = 1280, 720


def load(name):
    im = Image.open(os.path.join(ASSETS, name)).convert('RGB')
    s = max(W / im.width, H / im.height); im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x0, y0 = (im.width - W) // 2, (im.height - H) // 2; im = im.crop((x0, y0, x0 + W, y0 + H))
    return im.filter(ImageFilter.UnsharpMask(radius=1.6, percent=60, threshold=2))


class ImgRain:
    PIXEL = True; RAW = True; CITYPOP = False
    FILE = ''; GROUND = .85; SLANT = .12; RAIN_BOX = None; AMOUNT = 1.0; TINT = (205, 218, 240)
    def __init__(s, seed=1, pal=None):
        s.bg = load(s.FILE); R = np.random.default_rng(seed + 31); a = s.AMOUNT
        x0, y0, x1, y1 = s.RAIN_BOX or (0, 0, W, H); s.box = (x0, y0, x1, y1)
        def layer(n, l0, l1, v0, v1):
            n = int(n * a); return np.stack([R.uniform(x0 - 80, x1, n), R.uniform(0, H, n), R.uniform(v0, v1, n), R.uniform(l0, l1, n), R.uniform(.6, 1, n)], 1)
        s.layers = [(layer(620, 10, 18, 820, 1000), 1, 72), (layer(240, 22, 38, 1250, 1500), 1, 112), (layer(46, 54, 86, 1900, 2300), 2, 78)]
        if s.RAIN_BOX: m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).rectangle([x0, y0, x1, y1], fill=255); s.clip = m
        else: s.clip = None
    def frame(s, t):
        ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov); tc = s.TINT
        x0, y0, x1, y1 = s.box; span = y1 - y0 + 90
        for arr, wd, al in s.layers:
            for x, y_, sp, ln, br in arr:
                y = y0 + (y_ + t * sp) % span - 90; xx = x + (y - y0) * s.SLANT
                d.line([(xx, y), (xx + ln * s.SLANT, y + ln)], fill=tc + (int(al * br),), width=wd)
        if s.GROUND is not None:                                                             # 바닥: 튀는 물방울 + 번지는 물결
            gy = int(H * s.GROUND); now = int(abs(t) * 24)
            for b in range(now - 9, now + 1):
                R = np.random.default_rng(b * 7 + 100003); age = (abs(t) * 24 - b) / 9
                for _ in range(6):
                    x = R.uniform(x0, x1); y = R.uniform(gy, H - 4); z = .5 + (y - gy) / max(1, H - gy)
                    if age < .25: d.line([(x - 3 * z, y - 1), (x - 1, y - 5 * z)], fill=tc + (150,)); d.line([(x + 3 * z, y - 1), (x + 1, y - 5 * z)], fill=tc + (150,))
                    r = (4 + 16 * age) * z; d.ellipse([x - r, y - r * .3, x + r, y + r * .3], outline=tc + (int(90 * (1 - age)),))
        if s.clip is not None: ov.putalpha(Image.fromarray(np.minimum(np.asarray(ov.getchannel('A')), np.asarray(s.clip))))
        im = Image.alpha_composite(s.bg.convert('RGBA'), ov).convert('RGB')
        return np.asarray(im).astype(np.float32) / 255


class ImgShinjuku(ImgRain): FILE = 'rain_shinjuku.png'; GROUND = .9; SLANT = .1
class ImgOfficeStreet(ImgRain): FILE = 'rain_office_street.png'; GROUND = .88; SLANT = .14
class ImgLAMain(ImgRain): FILE = 'rain_la_main.png'; GROUND = .62; SLANT = .12
class ImgLASunset(ImgRain): FILE = 'rain_la_sunset.png'; GROUND = .9; SLANT = .16
class ImgManhattan(ImgRain): FILE = 'rain_manhattan.png'; GROUND = None; SLANT = .08; RAIN_BOX = (232, 66, 1250, 296); AMOUNT = .5; TINT = (170, 185, 220)   # 실내: 창밖에만 가는 비


IMG_SCENES = {'img_shinjuku': ImgShinjuku, 'img_office_street': ImgOfficeStreet, 'img_la_main': ImgLAMain, 'img_la_sunset': ImgLASunset, 'img_manhattan': ImgManhattan}
IMG_KO = {'img_shinjuku': '비 오는 신주쿠', 'img_office_street': '비 오는 도쿄 오피스 거리', 'img_la_main': '비 오는 LA 거리', 'img_la_sunset': '노을과 비, LA', 'img_manhattan': '비 오는 맨해튼 사무실'}
