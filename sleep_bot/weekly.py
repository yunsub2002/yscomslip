#!/usr/bin/env python3
"""GitHub Actions 에서 매주 화·금 실행: 수면음악 1시간 영상 → 릴리스 업로드 → 보관함 페이지(index.html) 갱신
환경변수: GH_TOKEN, GITHUB_REPOSITORY, COUNT(기본 1), THEME(auto 또는 테마 이름), MINUTES(기본 60)
"""
import datetime as dt, html, json, os, subprocess, sys
from pathlib import Path

BOT = Path(__file__).resolve().parent; ROOT = BOT.parent; sys.path.insert(0, str(BOT))
import make_video as MV, themes as T  # noqa: E402

REPO = os.environ.get('GITHUB_REPOSITORY', 'yunsub2002/yscomslip')
COUNT = int(os.environ.get('COUNT') or 1); THEME = (os.environ.get('THEME') or 'auto').strip(); MINUTES = int(os.environ.get('MINUTES') or 60)


def sh(*cmd, cwd=ROOT, check=True):
    print('  >', ' '.join(str(c) for c in cmd), flush=True); return subprocess.run([str(c) for c in cmd], cwd=cwd, check=check)


PAGE = r'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>수면음악 보관함</title><style>
:root{--bg:#0c0f1d;--card:#151a2e;--ln:#262c47;--tx:#ece9f6;--mut:#9aa0bd;--acc:#8fa8ff}
body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.6 -apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif}main{max-width:760px;margin:0 auto;padding:18px 16px 60px}
h1{font-size:22px;margin:6px 0 4px}p.s{color:var(--mut);margin:0 0 18px;font-size:13px}
.v{background:var(--card);border:1px solid var(--ln);border-radius:16px;overflow:hidden;margin-bottom:16px}.v img{display:block;width:100%;aspect-ratio:16/9;object-fit:cover;background:#000}
.b{padding:12px 14px 14px;display:grid;gap:8px}.b h2{margin:0;font-size:16.5px}.m{color:var(--mut);font-size:12.5px}.k{display:inline-block;font-size:11.5px;font-weight:700;border-radius:6px;padding:1px 7px;background:#2a2346;color:#d7c8ff;margin-left:4px}
.r{display:flex;gap:8px;flex-wrap:wrap}.r a,.r button{flex:1;min-width:96px;text-align:center;font:inherit;font-weight:700;font-size:14px;color:#fff;background:#4a5bd6;border:0;border-radius:10px;padding:11px;text-decoration:none;cursor:pointer}
.r a.t,.r button{background:#262c47}details{font-size:12.5px;color:var(--mut)}details pre{white-space:pre-wrap;font:inherit;background:#0a0d18;padding:10px;border-radius:8px}
</style></head><body><main><h1>🌙 수면음악 보관함</h1><p class="s">매주 화·금 저녁 새 1시간 영상이 자동으로 올라옵니다. 영상 받기 → 사진 앱에 저장 → YouTube 앱에서 업로드 → 제목·설명 복사해서 붙여 넣기 → 썸네일 지정</p>
__LIST__
</main><script>document.querySelectorAll('button[data-c]').forEach(b=>b.onclick=()=>{const t=document.getElementById(b.dataset.c).textContent;navigator.clipboard.writeText(t).then(()=>{const o=b.textContent;b.textContent='복사됨 ✓';setTimeout(()=>b.textContent=o,1500)})});</script></body></html>'''


def render_page(db):
    items = []
    for k, v in enumerate(db):
        title, body = v['yt'].split('\n\n', 1)
        items.append(f'''<div class="v"><img src="thumbs/{html.escape(v['thumbj'])}" alt="" loading="lazy"><div class="b"><h2>{html.escape(title)}</h2>
<div class="m">{v['date']} · {v['sec'] // 60}분 · {v['size'] / 1e6:.0f}MB<span class="k">{'아동용으로 설정' if v['kids'] else '아동용 아님'}</span></div>
<div class="r"><a href="{html.escape(v['url'])}">⬇ 영상 받기</a><a class="t" href="{html.escape(v['thumb_url'])}">⬇ 썸네일</a></div>
<div class="r"><button data-c="t{k}">📋 제목</button><button data-c="d{k}">📋 설명</button><button data-c="g{k}">📋 태그</button></div>
<div class="m">업로드 설정 → 시청자층: <b>{'예, 아동용입니다' if v['kids'] else '아니요, 아동용이 아닙니다'}</b> · 카테고리: 음악 · 썸네일: 위에서 받은 이미지</div>
<span id="t{k}" hidden>{html.escape(title)}</span><span id="g{k}" hidden>{html.escape(', '.join(v.get('tags', [])))}</span><details><summary>설명 보기</summary><pre id="d{k}">{html.escape(body)}</pre></details></div></div>''')
    (ROOT / 'index.html').write_text(PAGE.replace('__LIST__', '\n'.join(items) or '<p>아직 영상이 없습니다. 첫 영상은 Actions 실행 후 약 30분 뒤에 나타납니다.</p>'), encoding='utf-8')


def main():
    sh('git', 'config', '--global', 'user.name', 'sleep-bot'); sh('git', 'config', '--global', 'user.email', 'sleep-bot@users.noreply.github.com')
    dbp = ROOT / 'videos.json'; db = json.loads(dbp.read_text(encoding='utf-8')) if dbp.exists() else []
    (ROOT / 'thumbs').mkdir(exist_ok=True); out = ROOT / '_out'
    stamp = dt.datetime.utcnow() + dt.timedelta(hours=9); tag = 'sleep-' + stamp.strftime('%Y%m%d-%H%M'); made = []
    last = db[0]['theme'] if db else None
    for i in range(COUNT):
        if THEME in T.THEMES and i == 0: th = THEME
        else:
            idx = (T.ROTATION.index(last) + 1) % len(T.ROTATION) if last in T.ROTATION else 0; th = T.ROTATION[idx]
        vol = sum(1 for v in db if v['theme'] == th) + sum(1 for m in made if m['theme'] == th) + 1
        seed = int(stamp.strftime('%m%d%H%M')) * 10 + i
        print(f'\n===== [{i + 1}/{COUNT}] {T.THEMES[th]["name"]} Vol.{vol} (seed {seed}) =====', flush=True)
        m = MV.make(th, seed, MINUTES, out, vol=vol, seg=float(os.environ.get('SEG') or 90), log=lambda s: print(s, flush=True)); m['vol'] = vol; made.append(m); last = th
    files = [out / x for m in made for x in (m['file'], m['thumb'])]
    notes = '\n'.join(f"- {m['title']} ({m['size'] / 1e6:.0f}MB)" for m in made)
    sh('gh', 'release', 'create', tag, *files, '--repo', REPO, '--title', f'수면음악 {stamp:%Y-%m-%d}', '--notes', notes)
    base = f'https://github.com/{REPO}/releases/download/{tag}/'
    for m in made:
        jpg = ROOT / 'thumbs' / m['thumb']
        sh('ffmpeg', '-y', '-loglevel', 'error', '-i', out / m['thumb'], '-vf', 'scale=640:-1', '-q:v', '4', jpg)
        db.insert(0, dict(theme=m['theme'], vol=m['vol'], tags=m['tags'], date=f'{stamp:%Y-%m-%d}', sec=m['sec'], size=m['size'], kids=m['kids'], yt=m['yt'], thumbj=jpg.name,
                          url=base + m['file'], thumb_url=base + m['thumb']))
    dbp.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding='utf-8'); render_page(db)
    sh('git', 'add', 'videos.json', 'index.html', 'thumbs'); sh('git', 'commit', '-m', f'수면음악 {len(made)}편 추가 ({stamp:%Y-%m-%d})')
    br = os.environ.get('GITHUB_REF_NAME') or subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    for k in range(5):
        if subprocess.run(['git', 'push', 'origin', f'HEAD:{br}'], cwd=ROOT).returncode == 0: break
        sh('git', 'pull', '--rebase', '-X', 'theirs', 'origin', br, check=False)
    else: raise RuntimeError('git push 실패')
    user, rn = REPO.split('/'); print(f'\n완료 → https://{user}.github.io/{rn}/')


if __name__ == '__main__':
    main()
