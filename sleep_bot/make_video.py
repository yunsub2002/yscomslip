#!/usr/bin/env python3
"""수면음악 영상 1편 만들기: 오디오(작곡·합성) + 배경 루프 영상 + 썸네일 + 유튜브 제목/설명/태그
사용: python sleep_bot/make_video.py rain_lullaby --minutes 60 --out _out
"""
import argparse, json, math, os, subprocess, sys, time
from pathlib import Path
import numpy as np

BOT = Path(__file__).resolve().parent; sys.path.insert(0, str(BOT))
import audio as A, visual as V, themes as T  # noqa: E402

FONT = next((p for p in ['/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc', 'C:/Windows/Fonts/malgunbd.ttf'] if os.path.exists(p)), None)
NOTE = ['도', '도#', '레', '미♭', '미', '파', '파#', '솔', '라♭', '라', '시♭', '시']
INST_KO = {'musicbox': '오르골', 'piano': '피아노', 'harp': '하프', 'celesta': '첼레스타', 'kalimba': '칼림바', 'glass': '유리 종', 'vibes': '비브라폰', 'guitar': '나일론 기타',
           'epiano': '일렉피아노', 'handpan': '핸드팬', 'bowl': '싱잉볼', 'flute': '플루트', 'hum': '허밍', 'choir': '합창', 'strings': '현악',
           'felt': '펠트 피아노', 'gayageum': '가야금', 'daegeum': '대금', 'ocarina': '오카리나', 'bell': '벨',
           'synth': '신스 패드', 'synthlead': '신스 리드', 'sub': '서브 베이스'}
PXFONT = str(BOT / 'fonts' / 'Galmuri11-Bold.ttf'); PXFONT_R = str(BOT / 'fonts' / 'Galmuri11.ttf')   # 한글 도트 글꼴 (OFL)


def _pxtext(d, xy, txt, size, fill, shadow=True, font=None):
    """도트 글꼴: 작은 캔버스에 그린 뒤 각지게 확대하므로 여기선 작게 그림. 베이퍼웨이브식 분홍·하늘 그림자"""
    from PIL import ImageFont
    f = ImageFont.truetype(font or PXFONT, size); x, y = xy
    if shadow:
        d.text((x + 2, y + 2), txt, font=f, fill=(255, 79, 200, 255)); d.text((x - 1, y + 1), txt, font=f, fill=(79, 230, 255, 200))
    d.text((x, y), txt, font=f, fill=fill); return f.getlength(txt)


def _osd(d, xy, txt, size, fill=(255, 255, 255, 255), stroke=3, anchor='la'):
    """캠코더 화면 글자: 굵은 도트 글꼴 + 검은 테두리"""
    from PIL import ImageFont
    cjk = any(0x3040 <= ord(c) <= 0x9fff for c in txt)                                  # 한자·가나는 굵은 도트 글꼴에 없음 → 일반 도트 글꼴
    f = ImageFont.truetype(PXFONT_R if cjk else PXFONT, size); d.text(xy, txt, font=f, fill=fill, stroke_width=stroke, stroke_fill=(10, 6, 20, 255), anchor=anchor)


def thumbnail_cp(th, seed, path, vol=None, minutes=60):
    """시티팝 썸네일: VHS 장면 + 가운데 큰 캠코더식 연도('1988.') + ▶ PLAY 화면 표시 + 와이드 영문 제목"""
    from PIL import Image, ImageDraw
    f = V.still(th['thumb'], seed + 999, 37.0)
    img = Image.fromarray((np.clip(f, 0, 1) * 255).astype('uint8')).convert('RGBA')
    lay = Image.new('RGBA', (640, 360), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for y in range(250, 360): d.line([(0, y), (640, y)], fill=(8, 4, 24, int(150 * ((y - 250) / 110) ** 1.3)))
    _osd(d, (24, 20), '▶ PLAY', 22, stroke=2); _osd(d, (616, 20), f'{dur_ko(minutes).strip()}', 22, stroke=2, anchor='ra')
    _osd(d, (322, 152), th['year'], 66, fill=(255, 79, 200, 255), stroke=4, anchor='mm')                      # 분홍 그림자
    _osd(d, (318, 148), th['year'], 66, fill=(255, 255, 255, 255), stroke=4, anchor='mm')
    en, ko = th['short']
    _pxtext(d, (26, 272), en, 22, (255, 255, 255, 255)); _osd(d, (28, 306), ko, 22, fill=(255, 236, 250, 255), stroke=2)
    if vol and vol > 1: _osd(d, (616, 326), f'Vol.{vol}', 11, stroke=1, anchor='ra')
    img = Image.alpha_composite(img, lay.resize((1280, 720), Image.NEAREST))
    img.convert('RGB').save(path, quality=93)


def thumbnail_file(th, seed, path, vol=None, minutes=60):
    """채널 주인이 준 그림을 그대로 썸네일로 (16:9 로 맞추기만). text=True 면 아래에 작은 도트 제목"""
    from PIL import Image, ImageDraw
    im = Image.open(BOT / 'assets' / th['thumb_file']).convert('RGB'); s_ = max(1280 / im.width, 720 / im.height)
    im = im.resize((round(im.width * s_), round(im.height * s_)), Image.LANCZOS); x0, y0 = (im.width - 1280) // 2, (im.height - 720) // 2
    img = im.crop((x0, y0, x0 + 1280, y0 + 720)).convert('RGBA')
    if th.get('thumb_text', True):
        lay = Image.new('RGBA', (640, 360), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        for y in range(270, 360): d.line([(0, y), (640, y)], fill=(8, 4, 24, int(160 * ((y - 270) / 90) ** 1.3)))
        en, ko = th['short']; _pxtext(d, (24, 296), en, 22, (255, 255, 255, 255)); _osd(d, (26, 328), ko, 13, fill=(255, 236, 250, 255), stroke=2)
        _osd(d, (616, 18), f'♪ {dur_ko(minutes).strip()}', 16, stroke=2, anchor='ra')
        img = Image.alpha_composite(img, lay.resize((1280, 720), Image.NEAREST))
    img.convert('RGB').save(path, quality=93)

def thumbnail_px(th, seed, path, vol=None, minutes=60):
    """도트 테마 썸네일: 도트 장면 전체 + 와이드 영문 제목 + 한글 도트 부제 + 길이 배지 (모두 각진 도트)"""
    from PIL import Image, ImageDraw
    if th.get('thumb_file'): return thumbnail_file(th, seed, path, vol, minutes)
    if th.get('year'): return thumbnail_cp(th, seed, path, vol, minutes)
    f = V.still(th['thumb'], seed + 999, 37.0)
    img = Image.fromarray((np.clip(f, 0, 1) * 255).astype('uint8')).convert('RGBA')        # 1280x720
    lay = Image.new('RGBA', (640, 360), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for y in range(190, 360): d.line([(0, y), (640, y)], fill=(10, 6, 30, int(170 * ((y - 190) / 170) ** 1.2)))   # 아래쪽 어둠
    d.rectangle([24, 22, 24 + 132, 22 + 22], fill=(20, 10, 44, 190), outline=(255, 255, 255, 190))
    _pxtext(d, (31, 27), f'▶ {dur_ko(minutes).strip()} · sleep', 11, (255, 255, 255, 255), shadow=False)
    en, ko = th['short']
    _pxtext(d, (28, 248), en, 33, (255, 255, 255, 255))
    _pxtext(d, (30, 296), ko, 22, (255, 236, 250, 255), shadow=False)
    if vol and vol > 1: _pxtext(d, (560, 326), f'Vol.{vol}', 11, (255, 255, 255, 210), shadow=False)
    lay = lay.resize((1280, 720), Image.NEAREST); img = Image.alpha_composite(img, lay)
    img.convert('RGB').save(path, quality=93)


SHORT_X = {'px_room': .64, 'px_street': .62, 'cp_room': .7, 'cp_drive': .47, 'cp_boulevard': .34, 'img_shinjuku': .45, 'img_la_main': .12, 'img_office_street': .5, 'img_la_sunset': .55, 'img_manhattan': .3}       # 세로 쇼츠로 자를 때 장면별 가운데 위치


def make_short(th, theme, seed, wav, out, name, minutes, secs=45, start=300.0, log=print):
    """세로 쇼츠(1080x1920, 45초): 썸네일 장면을 9:16으로 잘라 움직이는 영상 + 본편 음악 한 구간 + 도트 글자"""
    from PIL import Image, ImageDraw
    sc = V.SCENES[th['thumb']](seed + 999); pix = V.is_pixel(th['thumb'])
    cw, ch = (360, 640) if pix else (405, 720); x0 = int((V.W - cw) * SHORT_X.get(th['thumb'], .5)); y0 = (V.H - ch) // 2
    ov = Image.new('RGBA', (360, 640), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for y in range(0, 150): d.line([(0, y), (360, y)], fill=(10, 6, 30, int(150 * (1 - y / 150))))
    for y in range(470, 640): d.line([(0, y), (360, y)], fill=(10, 6, 30, int(170 * ((y - 470) / 170))))
    en = th.get('en') or th['name']; ko = th['name'] if th.get('en') else th['sub'].split('·')[0].strip()
    wl = _pxtext(ImageDraw.Draw(Image.new('RGBA', (1, 1))), (0, 0), en, 22, (0, 0, 0, 0), shadow=False)
    if wl > 300:                                                                    # 길면 두 줄
        parts = en.split('　'); half = len(parts) // 2 or 1; lines = ['　'.join(parts[:half]), '　'.join(parts[half:])]
    else: lines = [en]
    y = 46
    if th.get('year'):
        _osd(d, (180, 40), th['year'], 44, stroke=3, anchor='mt'); y = 104
    for ln in lines:
        w_ = _pxtext(ImageDraw.Draw(Image.new('RGBA', (1, 1))), (0, 0), ln, 22, (0, 0, 0, 0), shadow=False)
        _pxtext(d, ((360 - w_) / 2, y), ln, 22, (255, 255, 255, 255)); y += 30
    from PIL import ImageFont
    fk = ImageFont.truetype(PXFONT, 11); wk = fk.getlength(ko); d.text(((360 - wk) / 2, y + 6), ko, font=fk, fill=(255, 236, 250, 255))
    full = f'풀버전 {dur_ko(minutes).strip()} ▶ 채널에서'; wf_ = fk.getlength(full)
    d.rectangle([(360 - wf_) / 2 - 10, 560, (360 + wf_) / 2 + 10, 584], fill=(255, 79, 200, 210)); d.text(((360 - wf_) / 2, 566), full, font=fk, fill=(255, 255, 255, 255))
    ovp = out / f'{name}_short_ov.png'; ov.resize((1080, 1920), Image.NEAREST).save(ovp)
    mp4 = out / f'{name}_short.mp4'; FPS = V.FPS; n = int(secs * FPS)
    raw = V.is_raw(th['thumb'])
    flt = f"[0:v]scale=1080:1920:flags={'neighbor' if pix and not raw else 'lanczos'}[b];[b][1:v]overlay=0:0,format=yuv420p[v]"
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{cw}x{ch}', '-r', str(FPS), '-i', '-',
                           '-loop', '1', '-i', str(ovp), '-ss', str(start), '-t', str(secs), '-i', str(wav),
                           '-filter_complex', flt, '-map', '[v]', '-map', '2:a', '-af', f'afade=t=in:d=1.5,afade=t=out:st={secs - 3}:d=3,volume=3dB,alimiter=limit=0.89:level=false',
                           '-c:v', 'libx264', '-preset', 'medium', '-crf', '22', '-maxrate', '7M', '-bufsize', '14M', '-c:a', 'aac', '-b:a', '160k', '-t', str(secs), '-shortest', '-movflags', '+faststart', str(mp4)], stdin=subprocess.PIPE)
    first = None
    for i in range(n):
        f = sc.frame(i / FPS); f = f if raw else V._CP.vhs(f, i / FPS, seed) if V.is_vhs(th['thumb']) else V._PX.grade_px(f) if pix else np.clip(V.grade(f, 0.0), 0, 1)
        f = (np.clip(f[y0:y0 + ch, x0:x0 + cw], 0, 1) * 255).astype(np.uint8)
        if first is None: first = f
        ff.stdin.write(f.tobytes())
    ff.stdin.close(); ff.wait()
    th_img = Image.fromarray(first).resize((1080, 1920), Image.NEAREST if pix and not raw else Image.LANCZOS).convert('RGBA')
    thumb = out / f'{name}_short_thumb.jpg'; Image.alpha_composite(th_img, Image.open(ovp)).convert('RGB').save(thumb, quality=92); ovp.unlink()
    title = (f"{en} {th['emoji']} 잠들기 전 1분 | {th['name']} #shorts")[:100]
    tags = list(dict.fromkeys(th['tags'][:10] + ['shorts', '쇼츠']))
    body = f"""{th['desc'].split('.')[0]}.
🌙 풀버전({dur_ko(minutes).strip()})은 채널에서 끊김 없이 들을 수 있어요.
🔔 구독하면 매주 화·금 새 수면음악 → https://www.youtube.com/channel/UCV2yZPs2ZaFXZE3x-gXfFBg?sub_confirmation=1

음악·소리·영상은 모두 이 채널이 직접 프로그램으로 작곡·합성·제작했습니다.

{' '.join('#' + x.replace(' ', '') for x in tags[:6])}"""
    log(f'  쇼츠 {mp4.name} {mp4.stat().st_size / 1e6:.1f}MB')
    return dict(file=mp4.name, thumb=thumb.name, title=title, yt=f'{title}\n\n{body}', tags=tags, sec=secs)


def thumbnail(th, seed, path, vol=None, minutes=60):
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    if th.get('pixel'): return thumbnail_px(th, seed, path, vol, minutes)
    f = V.still(th['thumb'], seed + 999, 37.0)
    f = f * (1.0 + .18) ** 1                                             # 썸네일은 살짝 밝게
    img = Image.fromarray((np.clip(f, 0, 1) * 255).astype('uint8'))
    W, H = img.size
    # 왼쪽에 글자가 잘 보이도록 부드러운 어둠
    sh = Image.new('L', (W, H)); d = ImageDraw.Draw(sh)
    for x in range(W): d.line([(x, 0), (x, H)], fill=int(150 * max(0, 1 - x / (W * .62)) ** 1.6))
    dark = Image.new('RGB', (W, H), (8, 10, 24)); img = Image.composite(dark, img, sh)
    big = ImageFont.truetype(FONT, 118); mid = ImageFont.truetype(FONT, 50); sm = ImageFont.truetype(FONT, 40)
    l1, l2 = th['short']; x0, y0 = 70, 205
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0)); g = ImageDraw.Draw(glow)
    gc = tuple(int(th['glow'].lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
    for (txt, fnt, y) in ((l1, big, y0), (l2, mid if len(l2) > 6 else big, y0 + 140)):
        g.text((x0, y), txt, font=fnt, fill=gc + (255,))
    glow = glow.filter(ImageFilter.GaussianBlur(16)); img = Image.alpha_composite(img.convert('RGBA'), glow)
    d = ImageDraw.Draw(img)
    d.text((x0, y0), l1, font=big, fill=(255, 248, 236))
    f2 = mid if len(l2) > 6 else big; d.text((x0, y0 + 140 + (8 if f2 is mid else 0)), l2, font=f2, fill=(255, 236, 214) if f2 is mid else (255, 248, 236))
    # '1시간' 배지 + 초승달 아이콘
    bx, by = x0, 112; ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.rounded_rectangle([bx, by, bx + 196, by + 66], 33, fill=(255, 255, 255, 40), outline=(255, 255, 255, 140), width=2)
    img = Image.alpha_composite(img, ov); d = ImageDraw.Draw(img)
    moon = Image.new('RGBA', (40, 40), (0, 0, 0, 0)); md = ImageDraw.Draw(moon); md.ellipse([2, 2, 38, 38], fill=(255, 226, 150, 255)); md.ellipse([14, -4, 48, 30], fill=(0, 0, 0, 0))
    img.alpha_composite(moon, (bx + 18, by + 13))
    d.text((bx + 70, by + 6), dur_ko(minutes).strip(), font=sm, fill=(255, 255, 255))
    if vol and vol > 1: d.text((x0, H - 92), f'Vol.{vol}', font=sm, fill=(255, 255, 255, 170))
    img.convert('RGB').save(path, quality=92)


def dur_ko(minutes):
    h, m = divmod(int(minutes), 60)
    return (f'{h}시간' if h else '') + (f' {m}분' if m else '') if h else f'{m}분'


SCENE_KO = {'night': '밤하늘', 'rainwin': '비 오는 창', 'sea': '달빛 바다', 'firefly': '반딧불 숲', 'snow': '눈 오는 밤', 'aurora': '오로라', 'pastel': '파스텔 구름',
            'warm': '따뜻한 불빛', 'eaves': '한옥 처마', 'storm': '번개 치는 창', 'nursery': '아기 방', 'stream': '달빛 시냇물', 'candle': '촛불', 'study': '늦은 밤 서재',
            'bamboo': '달빛 대숲', 'pond': '비 오는 연못', 'camp': '별빛 캠핑', 'underwater': '깊은 바닷속', 'meadow': '별 쏟아지는 초원', 'snowwin': '눈 오는 창가', 'tentrain': '텐트 안 빗소리',
            **V._PX.PX_KO, **V._CP.CP_KO, **V._RI.IMG_KO}


def yt_text(th, vol, songs, minutes, seg=90.0):
    title = f"{th['emoji']} {th['name']} {dur_ko(minutes).strip()} | {th['sub']}" + (f' Vol.{vol}' if vol and vol > 1 else '')
    if th.get('en'): title = f"{th['en']} {th['emoji']} {th['name']} {dur_ko(minutes).strip()}" + (f' Vol.{vol}' if vol and vol > 1 else '') + f" | {th['sub']}"
    keys = []; seen = set()
    for s in songs:
        nm = NOTE[s['tonic'] % 12]; sc = A.SCALE_KO.get(s.get('scale', 'major'), '장조'); ins = INST_KO.get(s.get('inst'), '')
        MODE = {'nocturne': ' 녹턴', 'canon': ' 돌림노래', 'folk': ' 전통 자장가풍', 'dream': ' 드림웨이브'}.get(s.get('mode'), '')
        if s.get('meter'): k = f"{ins}{MODE} {nm} {sc} {s['meter']}/4박자 ♩={s['bpm']}".strip()
        else: k = f"{ins} {nm} {sc} 앰비언트 (박자 없음)".strip()
        if k.split(' ♩')[0] in seen: continue
        seen.add(k.split(' ♩')[0]); keys.append(k)
    insts = []
    for s in songs:
        for ins in [s.get('inst')] + list(s.get('insts') or []):
            ko = INST_KO.get(ins)
            if ko and ko not in insts: insts.append(ko)
    sc = list(dict.fromkeys(th['scenes']))
    scene_line = ''
    if th.get('scene_db', 0.0) is not None and len(sc) > 1:
        def snd(nm): return '·'.join(A.LAYER_KO[k] for k in sorted(A.SCENE_AMB.get(nm, {}), key=lambda k: -A.SCENE_AMB[nm][k])[:2])
        steps = [f"{SCENE_KO[x]}({snd(x)})" for x in sc[:4]]
        m, sx = divmod(int(seg), 60); every = (f'{m}분' if m else '') + (f' {sx}초' if sx else '')
        scene_line = f"🎧 {every.strip()}마다 장면이 천천히 바뀌고, 그 장면의 소리도 함께 바뀝니다: {' → '.join(steps)}\n"
    music = scene_line + (f"🎼 이번 영상의 곡: 새로 작곡한 곡 {len(songs)}곡 — {', '.join(keys[:3])} 등\n" + (f"🎻 악기: {' · '.join(insts[:6])}\n" if insts else '')) if songs else ''
    tags = th['tags']
    body = f"""{th['desc']}

🌙 {dur_ko(minutes).strip()} 동안 끊김 없이 이어지고, 시작은 천천히 커지고 마지막 1분은 소리가 서서히 작아져 잠을 깨우지 않아요.
{music}💤 화면 밝기를 낮추고, 볼륨은 작게 틀어 주세요.

━━━━━━━━━━
🎵 음원·영상 안내
이 영상의 음악, 자연의 소리, 배경 영상은 모두 이 채널에서 직접 프로그램으로 작곡·합성·제작한 창작물입니다. 외부 음원이나 샘플, 스톡 영상을 사용하지 않았습니다.

🔔 매주 화요일·금요일 저녁, 새 수면음악이 올라옵니다. 구독하고 함께 푹 자요.
👉 https://www.youtube.com/channel/UCV2yZPs2ZaFXZE3x-gXfFBg?sub_confirmation=1

📺 같이 보면 좋은 채널
· 이상한 이야기 귀담 — 잠들기 전 듣는 실화 괴담·미스터리 https://www.youtube.com/@귀담스토리
· 세상의 모든 이야기 — 매일 1분 경제·생활 뉴스 https://www.youtube.com/@세상의모든이야기g1-c

{' '.join('#' + t.replace(' ', '') for t in tags[:8])}"""
    return title[:100], body, tags


XF = 8.0   # 장면 전환 시간(초) — 영상과 소리가 같은 시점에 바뀜


def make(theme, seed, minutes, out, vol=None, seg=90.0, log=print):
    th = T.THEMES[theme]; out = Path(out); out.mkdir(parents=True, exist_ok=True); name = f'{theme}_{seed}'
    t0 = time.time()
    log(f'[1/4] 오디오 — {th["name"]} ({minutes}분)')
    wav = out / f'{name}.wav'
    trans = V.pick_transitions(len(th['scenes']), seed)
    rms, songs = A.make_track(wav, minutes, th['style'], th['layers'], seed, th.get('music_db', 0.0), log=log,
                              scenes=th['scenes'], seg=seg, xf=XF, scene_db=th.get('scene_db', 0.0))
    gain = max(-12, min(12, -21.0 - rms))                    # 평균 -21dBFS (잔잔하게)
    log(f'      평균 {rms:.1f}dBFS → {gain:+.1f}dB 보정 · 곡 {len(songs)}개 · {time.time() - t0:.0f}초')
    log(f'[2/4] 배경 영상 루프 — {", ".join(th["scenes"])}')
    loop = out / f'{name}_loop.mp4'; V.make_loop(th['scenes'], seed, str(loop), seg=seg, xf=XF, trans=trans, crf=21 if minutes <= 90 else 23 if th.get('year') else 24,
                maxrate='1500k' if minutes <= 90 else '1800k' if (th.get('year') and minutes <= 130) else '850k')   # VHS 질감은 비트레이트가 조금 더 필요 (2시간 1.7GB 이하)
    log(f'      루프 {len(th["scenes"]) * seg / 60:.1f}분 · {loop.stat().st_size / 1e6:.0f}MB · {time.time() - t0:.0f}초')
    log('[3/4] 합치기 (영상은 재인코딩 없이 반복)')
    total = minutes * 60; reps = math.ceil(total / (len(th['scenes']) * seg)) + 1
    lst = out / f'{name}_list.txt'; lst.write_text(''.join(f"file '{loop.resolve()}'\n" for _ in range(reps)))
    mp4 = out / f'{name}.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-i', str(wav), '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-af', f'volume={gain:.2f}dB,alimiter=limit=0.89:level=false', '-c:a', 'aac', '-b:a', '192k' if minutes <= 90 else '160k', '-ar', '48000',
                    '-t', str(total), '-movflags', '+faststart', str(mp4)], check=True)
    short = None
    if os.environ.get('SHORTS', '1') == '1':
        log('[+] 쇼츠 (세로 45초)')
        try: short = make_short(th, theme, seed, wav, out, name, minutes, start=min(300.0, max(20.0, total * .1)), log=log)
        except Exception as e: log(f'  쇼츠 실패(본편은 계속): {e}')
    for x in (wav, loop, lst): x.unlink()
    log('[4/4] 썸네일 · 설명')
    thumb = out / f'{name}_thumb.jpg'; thumbnail(th, seed, thumb, vol, minutes)
    title, body, tags = yt_text(th, vol, songs, minutes, seg)
    kids = '아동용으로 설정' if th['kids'] else '아동용 아님'
    yt = f"{title}\n\n{body}"
    (out / f'{name}_youtube.txt').write_text(f"{yt}\n\n[태그] {', '.join(tags)}\n[업로드 설정] 시청자층: {kids} · 카테고리: 음악", encoding='utf-8')
    meta = dict(tags=tags, theme=theme, name=th['name'], title=title, sec=total, songs=len(songs), kids=th['kids'], file=mp4.name, thumb=thumb.name, yt=yt, size=mp4.stat().st_size, short=short)
    log(f'완료: {mp4.name} {mp4.stat().st_size / 1e6:.0f}MB · 총 {time.time() - t0:.0f}초')
    return meta


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('theme', choices=list(T.THEMES)); ap.add_argument('--minutes', type=int, default=60)
    ap.add_argument('--seed', type=int, default=int(time.time()) % 100000); ap.add_argument('--out', default='_out'); ap.add_argument('--seg', type=float, default=90.0)
    a = ap.parse_args(); print(json.dumps(make(a.theme, a.seed, a.minutes, a.out, seg=a.seg), ensure_ascii=False, indent=1)[:600])
