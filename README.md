# 🌙 수면음악 자동 제작 (yscomslip)

매주 화·금 저녁 GitHub Actions가 1시간 수면음악 영상을 자동으로 만듭니다.
음악은 매번 새로 작곡하고, 빗소리·파도·노이즈·배경 영상까지 모두 프로그램으로 합성합니다(외부 음원·영상 없음).

- 보관함: https://yunsub2002.github.io/yscomslip/
- 지금 만들기: Actions → 수면음악 자동 제작 → Run workflow
- 코드: `sleep_bot/` (audio.py 작곡·합성 · visual.py 배경 영상 · themes.py 테마·문구 · make_video.py 1편 제작 · weekly.py 업로드·보관함)
