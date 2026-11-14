# -*- coding: utf-8 -*-
"""채널 테마 (영상 1편 = 테마 1개). ROTATION 순서대로 돌아가며, 음악 테마와 자연음(ASMR) 테마가 번갈아 나옵니다.
style: 작곡 스타일 이름 또는 목록(곡마다 번갈아 연주) / None = 음악 없음
layers: 자연음과 크기(dB, 0 = 음악과 같은 크기, 작을수록 조용함)
  rain 빗소리 · drips 처마 빗방울 · thunder 먼 천둥 · waves 파도 · stream 시냇물 · wind 바람 · chimes 풍경 · crickets 귀뚜라미
  fire 장작 · clock 괘종시계 · purr 고양이 골골 · pink/brown/white 노이즈 · heart 엄마 뱃속
scenes: 배경 장면 4개(90초씩, 6분 루프) / thumb: 썸네일 장면 / kids: 유튜브 '아동용' 권장 여부
"""
THEMES = {
    # ───────── 아기·어린이 (kids=True)
    'rain_lullaby': dict(
        name='처마 빗소리 오르골 자장가', short=['처마 빗소리', '오르골 자장가'], emoji='🌧️', style=['musicbox', 'harp_arp', 'mixed'], layers={'rain': -8, 'drips': -6},
        scenes=['eaves', 'rainwin', 'eaves', 'night'], thumb='eaves', glow='#9fc4ff', kids=True,
        sub='아기 잠 잘 오는 음악 · 수면음악',
        desc='처마 끝에서 똑똑 떨어지는 빗방울 소리 위로, 매번 새로 작곡한 오르골과 하프 자장가가 천천히 흘러갑니다.',
        tags=['빗소리 자장가', '오르골 자장가', '아기 수면음악', '자장가', '빗소리', '수면음악', '잠 잘오는 음악', '아기 잠재우기', 'lullaby', 'rain sounds']),
    'humming_lullaby': dict(
        name='엄마 허밍 자장가', short=['엄마 허밍', '자장가'], emoji='🤱', style=['humming', 'hum_drone', 'harp'], layers={'pink': -22},
        scenes=['nursery', 'pastel', 'nursery', 'night'], thumb='nursery', glow='#ffc9d6', kids=True,
        sub='품에 안겨 듣는 자장가 · 아기 수면음악',
        desc='엄마가 나지막이 흥얼거리는 듯한 허밍 목소리와 하프로 부르는 자장가입니다. 가사는 없고, 모든 곡은 이번 영상을 위해 새로 지었어요.',
        tags=['허밍 자장가', '자장가', '아기 자장가', '엄마 목소리', '신생아 수면', '아기 수면음악', '잠 잘오는 음악', '태교음악', 'humming lullaby', 'baby sleep']),
    'womb': dict(
        name='엄마 뱃속 소리 자장가', short=['엄마 뱃속 소리', '자장가'], emoji='🤍', style=['musicbox', 'hum_drone'], layers={'heart': -3}, music_db=-7,
        scenes=['warm', 'pastel', 'warm', 'nursery'], thumb='warm', glow='#ffc48a', kids=True,
        sub='신생아 · 아기 울음 그치는 소리',
        desc='엄마 뱃속에서 듣던 낮은 쉬익 소리와 느린 심장 소리에, 아주 작은 오르골과 허밍을 더했습니다. 신생아가 편안해하는 소리예요.',
        tags=['엄마 뱃속 소리', '심장소리', '신생아 수면', '아기 울음 그치는 소리', '자장가', '태교음악', '아기 재우기', '백색소음', '오르골', 'womb sounds']),
    'lullaby': dict(
        name='아기 자장가 오르골 모음', short=['아기 자장가', '오르골 모음'], emoji='🌙', style=['harp', 'musicbox', 'vibes', 'kalimba_arp'], layers={},
        scenes=['nursery', 'pastel', 'firefly', 'pastel'], thumb='pastel', glow='#4a3a7a', kids=True,
        sub='맑고 포근한 꿀잠 음악',
        desc='첼레스타·오르골·비브라폰·칼림바가 번갈아 연주하는 자장가 모음입니다. 모든 곡이 이번 영상을 위해 새로 작곡된 곡이에요.',
        tags=['자장가', '아기 자장가', '오르골', '자장가 모음', '아기 수면음악', '꿀잠', '잠 잘오는 음악', '태교음악', 'baby lullaby', 'music box']),
    'white_noise': dict(
        name='아기 백색소음', short=['아기 백색소음', '쉬~ 소리'], emoji='☁️', style=None, layers={'white': -3, 'pink': -3},
        scenes=['pastel', 'nursery', 'pastel', 'firefly'], thumb='pastel', glow='#4a3a7a', kids=True,
        sub='신생아 재우기 · 울음 그치는 소리',
        desc='"쉬~" 하고 달래 주는 부드러운 백색소음입니다. 귀에 거슬리는 높은 소리를 줄여 오래 틀어 두어도 편안해요.',
        tags=['백색소음', '아기 백색소음', '신생아 백색소음', '아기 재우기', '울음 그치는 소리', 'white noise', '수면소음', '아기 수면', '쉬 소리', '1시간']),
    'firefly_lullaby': dict(
        name='반딧불 숲 오르골', short=['반딧불 숲', '오르골 자장가'], emoji='✨', style=['mixed', 'kalimba_ambient', 'musicbox'], layers={'crickets': -16, 'wind': -24},
        scenes=['firefly', 'night', 'firefly', 'stream'], thumb='firefly', glow='#d8ff9a', kids=True,
        sub='아이 잠자리 동화 같은 수면음악',
        desc='반딧불이 춤추는 여름밤 숲. 멀리서 귀뚜라미가 울고, 오르골과 칼림바가 번갈아 새 자장가를 들려줍니다.',
        tags=['오르골', '자장가', '반딧불', '아기 수면음악', '어린이 자장가', '꿀잠', '수면음악', '잠 잘오는 음악', 'music box', 'lullaby']),
    'kalimba_lullaby': dict(
        name='칼림바 자장가', short=['칼림바', '자장가'], emoji='🎶', style=['kalimba_arp', 'kalimba_ambient', 'harp'], layers={'pink': -24},
        scenes=['pastel', 'nursery', 'night', 'pastel'], thumb='pastel', glow='#ffe6a8', kids=True,
        sub='맑은 엄지 피아노 소리 · 아기 수면음악',
        desc='손가락으로 튕기는 맑은 칼림바(엄지 피아노) 소리로 느리게 연주하는 자장가입니다. 아르페지오와 잔잔한 선율이 번갈아 나와요.',
        tags=['칼림바', '칼림바 자장가', '자장가', '아기 수면음악', '잠 잘오는 음악', '힐링음악', 'kalimba', 'lullaby', '꿀잠', '태교음악']),
    # ───────── 어른 숙면·힐링 (kids=False)
    'brown_noise': dict(
        name='브라운 노이즈', short=['브라운 노이즈', '깊은 잠'], emoji='🌌', style=None, layers={'brown': 0},
        scenes=['aurora', 'night', 'sea', 'snow'], thumb='aurora', glow='#8fe3c8', kids=False,
        sub='공부 · 집중 · 숙면을 위한 소리',
        desc='낮고 부드러운 브라운 노이즈입니다. 주변 소음을 덮어 주어 잠들기, 집중, 휴식에 좋아요. 음악이나 말소리는 없습니다.',
        tags=['브라운 노이즈', 'brown noise', '백색소음', '수면 소음', '집중 소음', '숙면', '공부할때 듣는', '수면음악', '이명', '1시간']),
    'waves_piano': dict(
        name='파도소리 잔잔한 피아노', short=['파도소리', '잔잔한 피아노'], emoji='🌊', style=['piano', 'piano_ambient', 'epiano_arp'], layers={'waves': -6},
        scenes=['sea', 'night', 'sea', 'aurora'], thumb='sea', glow='#ffe2a8', kids=False,
        sub='불면증 · 스트레스 해소 수면음악',
        desc='달빛 비치는 밤바다의 느린 파도 소리와, 이번 영상을 위해 새로 작곡한 잔잔한 피아노 연주입니다.',
        tags=['파도소리', '피아노 수면음악', '잔잔한 피아노', '수면음악', '힐링음악', '불면증', '명상음악', '잠잘때 듣는 음악', 'sleep music', 'ocean waves']),
    'rain_only': dict(
        name='처마 빗소리 ASMR', short=['처마 빗소리', '음악 없음'], emoji='☔', style=None, layers={'rain': 0, 'drips': -3, 'brown': -14, 'thunder': -8},
        scenes=['eaves', 'rainwin', 'storm', 'eaves'], thumb='eaves', glow='#b8d4ff', kids=False,
        sub='잠 잘 오는 빗소리 · 공부 · 휴식',
        desc='음악 없이 빗소리만 담았습니다. 처마 끝에서 떨어지는 빗방울, 멀리서 들려오는 낮은 천둥, 창에 부딪히는 비가 이어집니다.',
        tags=['빗소리', '빗소리 asmr', '잠잘때 빗소리', '수면 빗소리', '공부할때 빗소리', '천둥소리', 'rain sounds', '수면음악', '자연의 소리', '처마 빗소리']),
    'fire_piano': dict(
        name='장작 타는 소리와 피아노', short=['장작 타는 소리', '따뜻한 피아노'], emoji='🔥', style=['piano', 'guitar_arp', 'piano_ambient'], layers={'fire': -6},
        scenes=['candle', 'snow', 'warm', 'candle'], thumb='candle', glow='#ffb070', kids=False,
        sub='겨울밤 포근한 수면음악',
        desc='타닥타닥 장작 타는 소리와 포근한 피아노, 기타. 추운 겨울밤, 따뜻한 방 안에 누워 있는 느낌으로 만들었습니다.',
        tags=['장작 타는 소리', '모닥불 소리', '피아노', '수면음악', '겨울 음악', '힐링음악', '잠잘때 듣는 음악', 'asmr', 'fireplace', 'sleep music']),
    'snow_harp': dict(
        name='눈 오는 밤 하프 자장가', short=['눈 오는 밤', '하프 자장가'], emoji='❄️', style=['harp', 'glass_ambient', 'vibes'], layers={'wind': -20},
        scenes=['snow', 'night', 'snow', 'aurora'], thumb='snow', glow='#e4ecff', kids=False,
        sub='포근한 겨울밤 수면음악',
        desc='소리 없이 눈이 쌓이는 밤, 맑은 하프와 유리 종소리, 비브라폰으로 연주하는 새 자장가들입니다. 멀리서 바람이 살짝 지나가요.',
        tags=['자장가', '하프', '수면음악', '겨울밤', '눈 오는 밤', '힐링음악', '잠 잘오는 음악', '오르골', 'lullaby', 'sleep music']),
    'stream_kalimba': dict(
        name='시냇물 소리와 칼림바', short=['시냇물 소리', '칼림바'], emoji='🏞️', style=['kalimba_arp', 'kalimba_ambient', 'guitar_arp'], layers={'stream': -7},
        scenes=['stream', 'firefly', 'stream', 'night'], thumb='stream', glow='#a8ffd8', kids=False,
        sub='계곡 물소리 · 힐링 수면음악',
        desc='돌 틈을 흐르는 시냇물 소리와 맑은 칼림바·기타 아르페지오. 숲속 계곡 옆에 누워 있는 것처럼 편안해요.',
        tags=['시냇물 소리', '물소리', '칼림바', '계곡 소리', '수면음악', '힐링음악', '자연의 소리', 'asmr', 'stream sounds', 'kalimba']),
    'night_guitar': dict(
        name='여름밤 귀뚜라미와 기타', short=['여름밤 귀뚜라미', '나일론 기타'], emoji='🦗', style=['guitar', 'guitar_arp', 'flute_song'], layers={'crickets': -13, 'wind': -26},
        scenes=['firefly', 'night', 'stream', 'night'], thumb='night', glow='#c8e8a0', kids=False,
        sub='시골 평상에 누운 밤 · 수면음악',
        desc='귀뚜라미 우는 여름밤, 나일론 기타와 플루트가 느리게 연주합니다. 모든 곡은 이번 영상을 위해 새로 지은 곡이에요.',
        tags=['귀뚜라미 소리', '여름밤', '기타 수면음악', '통기타', '수면음악', '힐링음악', '자연의 소리', 'asmr', 'crickets', 'guitar sleep music']),
    'windchime': dict(
        name='풍경 소리 앰비언트', short=['풍경 소리', '앰비언트'], emoji='🎐', style=['glass_ambient', 'bowl_ambient', 'piano_ambient'], layers={'chimes': -10, 'wind': -18},
        scenes=['night', 'aurora', 'sea', 'night'], thumb='aurora', glow='#d0f0ff', kids=False,
        sub='바람에 흔들리는 풍경 · 명상 수면음악',
        desc='바람이 불 때마다 흩어지는 풍경 소리와, 박자 없이 천천히 떠다니는 유리 종·싱잉볼·피아노 앰비언트입니다.',
        tags=['풍경 소리', '앰비언트', '명상음악', '수면음악', '힐링음악', 'asmr', 'wind chimes', 'ambient sleep', '요가음악', '마음 안정']),
    'thunder_piano': dict(
        name='먼 천둥 빗소리와 피아노', short=['먼 천둥 빗소리', '피아노'], emoji='⛈️', style=['piano_ambient', 'piano', 'epiano_arp'], layers={'rain': -6, 'thunder': -4, 'drips': -12},
        scenes=['storm', 'rainwin', 'storm', 'eaves'], thumb='storm', glow='#b0c4ff', kids=False,
        sub='비 오는 밤 깊은 잠 · 수면음악',
        desc='창밖 빗소리 사이로 가끔 멀리서 천둥이 낮게 울립니다. 그 위로 느린 피아노가 띄엄띄엄 흘러요.',
        tags=['천둥소리', '빗소리', '피아노 수면음악', '비 오는 밤', '수면음악', '불면증', 'asmr', 'thunderstorm', 'rain piano', '잠 잘오는 음악']),
    'cat_purr': dict(
        name='고양이 골골송과 오르골', short=['고양이 골골송', '오르골'], emoji='🐈', style=['musicbox', 'glass_ambient'], layers={'purr': -5, 'fire': -16}, music_db=-4,
        scenes=['candle', 'warm', 'candle', 'snow'], thumb='candle', glow='#ffd0a0', kids=False,
        sub='고양이 품에 안긴 듯한 수면음악',
        desc='무릎 위에서 골골대는 고양이 소리와 작은 오르골, 멀리서 타는 난로 소리. 포근하게 잠드는 밤을 위해 만들었습니다.',
        tags=['고양이 골골송', '고양이 소리', '골골송', '오르골', '수면음악', 'asmr', 'cat purring', '힐링음악', '잠 잘오는 음악', '마음 안정']),
    'clock_epiano': dict(
        name='늦은 밤 서재, 시계와 일렉피아노', short=['늦은 밤 서재', '일렉피아노'], emoji='🕰️', style=['epiano_arp', 'vibes', 'piano_ambient'], layers={'clock': -14, 'fire': -20},
        scenes=['study', 'candle', 'study', 'rainwin'], thumb='study', glow='#ffd9a8', kids=False,
        sub='재즈 느낌 잔잔한 수면음악',
        desc='똑딱이는 괘종시계와 따뜻한 일렉피아노·비브라폰. 늦은 밤 스탠드 하나 켜 둔 서재에서 잠드는 느낌이에요.',
        tags=['일렉피아노', '재즈 수면음악', '시계 소리', '수면음악', '힐링음악', 'lofi', 'asmr', 'jazz sleep', '잠 잘오는 음악', '늦은 밤']),
    'flute_meditation': dict(
        name='명상 플루트 드론', short=['명상 플루트', '드론 음악'], emoji='🧘', style=['flute_drone', 'handpan_arp', 'bowl_drone'], layers={'wind': -22, 'stream': -20},
        scenes=['aurora', 'stream', 'night', 'aurora'], thumb='aurora', glow='#c0b0ff', kids=False,
        sub='깊은 호흡 · 명상 · 수면',
        desc='낮게 깔린 현악 드론 위로 플루트·핸드팬·싱잉볼이 박자 없이 천천히 노래합니다. 명상과 깊은 잠을 위한 음악이에요.',
        tags=['명상음악', '플루트', '드론 음악', '수면음악', '요가음악', '싱잉볼', '핸드팬', 'meditation music', 'deep sleep', '마음 안정']),
    'singing_bowl': dict(
        name='싱잉볼 앰비언트', short=['싱잉볼', '앰비언트'], emoji='🔔', style=['bowl_ambient', 'bowl_drone', 'glass_ambient'], layers={'pink': -24},
        scenes=['candle', 'aurora', 'night', 'candle'], thumb='candle', glow='#ffe0b0', kids=False,
        sub='티베탄 싱잉볼 · 깊은 이완',
        desc='길게 울리는 싱잉볼과 유리 종이 겹치며 천천히 사라지는 앰비언트. 머릿속이 조용해지는 깊은 이완 음악입니다.',
        tags=['싱잉볼', '티베탄 싱잉볼', '명상음악', '수면음악', '힐링음악', '앰비언트', 'singing bowl', 'deep relaxation', '마음 안정', '이완']),
}
# 아기 테마와 어른 테마가 번갈아 나오도록
ROTATION = ['rain_lullaby', 'brown_noise', 'humming_lullaby', 'waves_piano', 'womb', 'rain_only', 'lullaby', 'fire_piano', 'white_noise', 'stream_kalimba',
            'firefly_lullaby', 'night_guitar', 'kalimba_lullaby', 'windchime', 'thunder_piano', 'cat_purr', 'clock_epiano', 'flute_meditation', 'snow_harp', 'singing_bowl']
assert set(ROTATION) == set(THEMES) and len(ROTATION) == len(THEMES)
