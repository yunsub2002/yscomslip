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


def thumbnail(th, seed, path, vol=None, minutes=60):
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
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


def yt_text(th, vol, songs, minutes):
    title = f"{th['emoji']} {th['name']} {dur_ko(minutes).strip()} | {th['sub']}" + (f' Vol.{vol}' if vol and vol > 1 else '')
    keys = []
    for s in songs[:6]:
        nm = NOTE[s['tonic'] % 12]; keys.append(f"{nm}장조 {s['meter']}/4박자 ♩={s['bpm']}")
    music = f"🎼 이번 영상의 곡: 새로 작곡한 자장가 {len(songs)}곡 ({', '.join(keys[:3])} 등)\n" if songs else ''
    tags = th['tags']
    body = f"""{th['desc']}

🌙 {dur_ko(minutes).strip()} 동안 끊김 없이 이어지고, 시작은 천천히 커지고 마지막 1분은 소리가 서서히 작아져 잠을 깨우지 않아요.
{music}💤 화면 밝기를 낮추고, 볼륨은 작게 틀어 주세요.

━━━━━━━━━━
🎵 음원·영상 안내
이 영상의 음악, 자연의 소리, 배경 영상은 모두 이 채널에서 직접 프로그램으로 작곡·합성·제작한 창작물입니다. 외부 음원이나 샘플, 스톡 영상을 사용하지 않았습니다.

🔔 매주 화요일·금요일 저녁, 새 수면음악이 올라옵니다. 구독하고 함께 푹 자요.

{' '.join('#' + t.replace(' ', '') for t in tags[:8])}"""
    return title[:100], body, tags


def make(theme, seed, minutes, out, vol=None, seg=90.0, log=print):
    th = T.THEMES[theme]; out = Path(out); out.mkdir(parents=True, exist_ok=True); name = f'{theme}_{seed}'
    t0 = time.time()
    log(f'[1/4] 오디오 — {th["name"]} ({minutes}분)')
    wav = out / f'{name}.wav'
    rms, songs = A.make_track(wav, minutes, th['style'], th['layers'], seed, th.get('music_db', 0.0), log=log)
    gain = max(-12, min(12, -21.0 - rms))                    # 평균 -21dBFS (잔잔하게)
    log(f'      평균 {rms:.1f}dBFS → {gain:+.1f}dB 보정 · 곡 {len(songs)}개 · {time.time() - t0:.0f}초')
    log(f'[2/4] 배경 영상 루프 — {", ".join(th["scenes"])}')
    loop = out / f'{name}_loop.mp4'; V.make_loop(th['scenes'], seed, str(loop), seg=seg, crf=21 if minutes <= 90 else 24, maxrate='1500k' if minutes <= 90 else '850k')
    log(f'      루프 {len(th["scenes"]) * seg / 60:.1f}분 · {loop.stat().st_size / 1e6:.0f}MB · {time.time() - t0:.0f}초')
    log('[3/4] 합치기 (영상은 재인코딩 없이 반복)')
    total = minutes * 60; reps = math.ceil(total / (len(th['scenes']) * seg)) + 1
    lst = out / f'{name}_list.txt'; lst.write_text(''.join(f"file '{loop.resolve()}'\n" for _ in range(reps)))
    mp4 = out / f'{name}.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-i', str(wav), '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-af', f'volume={gain:.2f}dB,alimiter=limit=0.89:level=false', '-c:a', 'aac', '-b:a', '192k' if minutes <= 90 else '160k', '-ar', '48000',
                    '-t', str(total), '-movflags', '+faststart', str(mp4)], check=True)
    for x in (wav, loop, lst): x.unlink()
    log('[4/4] 썸네일 · 설명')
    thumb = out / f'{name}_thumb.jpg'; thumbnail(th, seed, thumb, vol, minutes)
    title, body, tags = yt_text(th, vol, songs, minutes)
    kids = '아동용으로 설정' if th['kids'] else '아동용 아님'
    yt = f"{title}\n\n{body}"
    (out / f'{name}_youtube.txt').write_text(f"{yt}\n\n[태그] {', '.join(tags)}\n[업로드 설정] 시청자층: {kids} · 카테고리: 음악", encoding='utf-8')
    meta = dict(tags=tags, theme=theme, name=th['name'], title=title, sec=total, songs=len(songs), kids=th['kids'], file=mp4.name, thumb=thumb.name, yt=yt, size=mp4.stat().st_size)
    log(f'완료: {mp4.name} {mp4.stat().st_size / 1e6:.0f}MB · 총 {time.time() - t0:.0f}초')
    return meta


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('theme', choices=list(T.THEMES)); ap.add_argument('--minutes', type=int, default=60)
    ap.add_argument('--seed', type=int, default=int(time.time()) % 100000); ap.add_argument('--out', default='_out'); ap.add_argument('--seg', type=float, default=90.0)
    a = ap.parse_args(); print(json.dumps(make(a.theme, a.seed, a.minutes, a.out, seg=a.seg), ensure_ascii=False, indent=1)[:600])
