# -*- coding: utf-8 -*-
"""채널 테마 (영상 1편 = 테마 1개). ROTATION 순서대로 돌아가며, 아기용 테마와 어른용 테마가 번갈아 나옵니다.
style: 작곡 스타일 이름 또는 목록(곡마다 번갈아 연주) / None = 음악 없음
layers: 처음부터 끝까지 깔리는 자연음과 크기(dB, 0 = 음악과 같은 크기, 작을수록 조용함)
scenes: 배경 장면 6개(90초씩, 9분 루프). 장면마다 그 장면의 자연음(audio.SCENE_AMB)이 화면 전환과 같이 바뀝니다.
scene_db: 장면 자연음 전체 크기 조절(dB) / None = 장면 소리 끔(노이즈 테마처럼 일정한 소리만 원할 때)
  자연음: rain 빗소리 · drips 처마 빗방울 · thunder 먼 천둥 · waves 파도 · stream 시냇물 · wind 바람 · chimes 풍경 · crickets 귀뚜라미
         fire 장작 · clock 괘종시계 · purr 고양이 골골 · pink/brown/white 노이즈 · heart 엄마 뱃속
         leaves 나뭇잎 빗소리 · tent 텐트 빗소리 · underwater 깊은 물속 · frogs 개구리 · owl 부엉이 · bamboo 대나무 부딪힘 · pages 책장 넘김
  장면: night rainwin storm eaves sea firefly snow aurora pastel warm candle nursery stream study bamboo pond camp underwater meadow snowwin tentrain
thumb: 썸네일 장면 / kids: 유튜브 '아동용' 권장 여부
pixel: 도트(드림코어) 테마 — 도트 썸네일, 영문 와이드 제목(en) / 장면 px_train px_city px_room px_clouds px_pool px_street
"""
THEMES = {
    # ───────── 아기·어린이 (kids=True)
    'rain_lullaby': dict(
        name='처마 빗소리 오르골 자장가', short=['처마 빗소리', '오르골 자장가'], emoji='🌧️', style=['musicbox', 'harp_arp', 'musicbox_canon', 'mixed'], layers={'rain': -14},
        scenes=['eaves', 'rainwin', 'nursery', 'eaves', 'pond', 'night'], thumb='eaves', glow='#9fc4ff', kids=True, scene_db=-3,
        sub='아기 잠 잘 오는 음악 · 수면음악',
        desc='처마 끝에서 똑똑 떨어지는 빗방울 소리 위로, 매번 새로 작곡한 오르골과 하프 자장가가 천천히 흘러갑니다.',
        tags=['빗소리 자장가', '오르골 자장가', '아기 수면음악', '자장가', '빗소리', '수면음악', '잠 잘오는 음악', '아기 잠재우기', 'lullaby', 'rain sounds']),
    'humming_lullaby': dict(
        name='엄마 허밍 자장가', short=['엄마 허밍', '자장가'], emoji='🤱', style=['humming', 'hum_drone', 'harp', 'felt_canon'], layers={'pink': -24},
        scenes=['nursery', 'pastel', 'snowwin', 'nursery', 'meadow', 'night'], thumb='nursery', glow='#ffc9d6', kids=True, scene_db=-5,
        sub='품에 안겨 듣는 자장가 · 아기 수면음악',
        desc='엄마가 나지막이 흥얼거리는 듯한 허밍 목소리와 하프로 부르는 자장가입니다. 가사는 없고, 모든 곡은 이번 영상을 위해 새로 지었어요.',
        tags=['허밍 자장가', '자장가', '아기 자장가', '엄마 목소리', '신생아 수면', '아기 수면음악', '잠 잘오는 음악', '태교음악', 'humming lullaby', 'baby sleep']),
    'womb': dict(
        name='엄마 뱃속 소리 자장가', short=['엄마 뱃속 소리', '자장가'], emoji='🤍', style=['musicbox', 'hum_drone'], layers={'heart': -3}, music_db=-7,
        scenes=['warm', 'pastel', 'nursery', 'warm', 'underwater', 'nursery'], thumb='warm', glow='#ffc48a', kids=True, scene_db=None,
        sub='신생아 · 아기 울음 그치는 소리',
        desc='엄마 뱃속에서 듣던 낮은 쉬익 소리와 느린 심장 소리에, 아주 작은 오르골과 허밍을 더했습니다. 신생아가 편안해하는 소리예요.',
        tags=['엄마 뱃속 소리', '심장소리', '신생아 수면', '아기 울음 그치는 소리', '자장가', '태교음악', '아기 재우기', '백색소음', '오르골', 'womb sounds']),
    'lullaby': dict(
        name='아기 자장가 오르골 모음', short=['아기 자장가', '오르골 모음'], emoji='🌙', style=['harp', 'musicbox', 'bell_song', 'musicbox_canon', 'kalimba_arp'], layers={},
        scenes=['nursery', 'pastel', 'firefly', 'meadow', 'pastel', 'snowwin'], thumb='pastel', glow='#4a3a7a', kids=True, scene_db=-6,
        sub='맑고 포근한 꿀잠 음악',
        desc='첼레스타·오르골·벨·칼림바가 번갈아 연주하고, 가끔은 돌림노래처럼 서로 이어 부르는 자장가 모음입니다. 모든 곡이 이번 영상을 위해 새로 작곡된 곡이에요.',
        tags=['자장가', '아기 자장가', '오르골', '자장가 모음', '아기 수면음악', '꿀잠', '잠 잘오는 음악', '태교음악', 'baby lullaby', 'music box']),
    'white_noise': dict(
        name='아기 백색소음', short=['아기 백색소음', '쉬~ 소리'], emoji='☁️', style=None, layers={'white': -3, 'pink': -3},
        scenes=['pastel', 'nursery', 'pastel', 'firefly', 'meadow', 'nursery'], thumb='pastel', glow='#4a3a7a', kids=True, scene_db=None,
        sub='신생아 재우기 · 울음 그치는 소리',
        desc='"쉬~" 하고 달래 주는 부드러운 백색소음입니다. 귀에 거슬리는 높은 소리를 줄여 오래 틀어 두어도 편안해요.',
        tags=['백색소음', '아기 백색소음', '신생아 백색소음', '아기 재우기', '울음 그치는 소리', 'white noise', '수면소음', '아기 수면', '쉬 소리', '1시간']),
    'firefly_lullaby': dict(
        name='반딧불 숲 오르골', short=['반딧불 숲', '오르골 자장가'], emoji='✨', style=['mixed', 'kalimba_ambient', 'musicbox', 'harp_canon'], layers={},
        scenes=['firefly', 'meadow', 'stream', 'firefly', 'pond', 'night'], thumb='firefly', glow='#d8ff9a', kids=True, scene_db=-3,
        sub='아이 잠자리 동화 같은 수면음악',
        desc='반딧불이 춤추는 여름밤 숲과 초원. 귀뚜라미와 개구리가 멀리서 울고, 오르골과 칼림바가 번갈아 새 자장가를 들려줍니다.',
        tags=['오르골', '자장가', '반딧불', '아기 수면음악', '어린이 자장가', '꿀잠', '수면음악', '잠 잘오는 음악', 'music box', 'lullaby']),
    'kalimba_lullaby': dict(
        name='칼림바 자장가', short=['칼림바', '자장가'], emoji='🎶', style=['kalimba_arp', 'kalimba_ambient', 'harp', 'bell_song'], layers={'pink': -26},
        scenes=['pastel', 'nursery', 'meadow', 'pastel', 'stream', 'night'], thumb='pastel', glow='#ffe6a8', kids=True, scene_db=-5,
        sub='맑은 엄지 피아노 소리 · 아기 수면음악',
        desc='손가락으로 튕기는 맑은 칼림바(엄지 피아노) 소리로 느리게 연주하는 자장가입니다. 아르페지오와 잔잔한 선율이 번갈아 나와요.',
        tags=['칼림바', '칼림바 자장가', '자장가', '아기 수면음악', '잠 잘오는 음악', '힐링음악', 'kalimba', 'lullaby', '꿀잠', '태교음악']),
    'lotus_gayageum': dict(
        name='비 오는 연못, 가야금 자장가', short=['비 오는 연못', '가야금 자장가'], emoji='🪷', style=['gayageum_folk', 'daegeum_folk', 'harp_canon'], layers={},
        scenes=['pond', 'eaves', 'bamboo', 'pond', 'nursery', 'night'], thumb='pond', glow='#ffc0d8', kids=True, scene_db=-2,
        sub='우리 소리로 듣는 자장가 · 아기 수면음악',
        desc='연못에 가는 비가 내리고 개구리가 멀리서 웁니다. 가야금과 대금이 우리 옛 자장가처럼 다섯 음으로 느리게 주고받는 새 곡들이에요.',
        tags=['가야금', '국악 자장가', '전통 자장가', '아기 수면음악', '대금', '국악 태교', '자장가', '빗소리', '연못', 'korean lullaby']),
    'meadow_ocarina': dict(
        name='별 쏟아지는 초원, 오카리나 자장가', short=['별 쏟아지는 초원', '오카리나 자장가'], emoji='🌠', style=['ocarina_song', 'musicbox_canon', 'bell_song', 'harp'], layers={},
        scenes=['meadow', 'pastel', 'firefly', 'meadow', 'nursery', 'aurora'], thumb='meadow', glow='#c8d0ff', kids=True, scene_db=-4,
        sub='별빛 아래 포근한 꿀잠 음악',
        desc='은하수가 흐르고 가끔 별똥별이 떨어지는 초원. 동그란 오카리나와 벨, 오르골이 돌림노래처럼 이어지는 새 자장가입니다.',
        tags=['오카리나', '자장가', '별', '은하수', '아기 수면음악', '꿀잠', '수면음악', '잠 잘오는 음악', 'ocarina', 'lullaby']),
    # ───────── 어른 숙면·힐링 (kids=False)
    'brown_noise': dict(
        name='브라운 노이즈', short=['브라운 노이즈', '깊은 잠'], emoji='🌌', style=None, layers={'brown': 0},
        scenes=['aurora', 'night', 'sea', 'snow', 'meadow', 'underwater'], thumb='aurora', glow='#8fe3c8', kids=False, scene_db=None,
        sub='공부 · 집중 · 숙면을 위한 소리',
        desc='낮고 부드러운 브라운 노이즈입니다. 주변 소음을 덮어 주어 잠들기, 집중, 휴식에 좋아요. 음악이나 말소리는 없습니다.',
        tags=['브라운 노이즈', 'brown noise', '백색소음', '수면 소음', '집중 소음', '숙면', '공부할때 듣는', '수면음악', '이명', '1시간']),
    'waves_piano': dict(
        name='파도소리 잔잔한 피아노', short=['파도소리', '잔잔한 피아노'], emoji='🌊', style=['piano', 'piano_ambient', 'piano_nocturne', 'epiano_arp'], layers={'waves': -12},
        scenes=['sea', 'night', 'underwater', 'sea', 'aurora', 'meadow'], thumb='sea', glow='#ffe2a8', kids=False, scene_db=0,
        sub='불면증 · 스트레스 해소 수면음악',
        desc='달빛 비치는 밤바다의 느린 파도 소리와, 이번 영상을 위해 새로 작곡한 잔잔한 피아노 연주입니다.',
        tags=['파도소리', '피아노 수면음악', '잔잔한 피아노', '수면음악', '힐링음악', '불면증', '명상음악', '잠잘때 듣는 음악', 'sleep music', 'ocean waves']),
    'rain_only': dict(
        name='처마 빗소리 ASMR', short=['처마 빗소리', '음악 없음'], emoji='☔', style=None, layers={'rain': -6, 'brown': -16},
        scenes=['eaves', 'rainwin', 'pond', 'storm', 'eaves', 'tentrain'], thumb='eaves', glow='#b8d4ff', kids=False, scene_db=2,
        sub='잠 잘 오는 빗소리 · 공부 · 휴식',
        desc='음악 없이 빗소리만 담았습니다. 처마 끝 빗방울, 연잎에 떨어지는 비, 멀리서 울리는 천둥, 텐트 천을 두드리는 비가 장면마다 바뀌며 이어집니다.',
        tags=['빗소리', '빗소리 asmr', '잠잘때 빗소리', '수면 빗소리', '공부할때 빗소리', '천둥소리', 'rain sounds', '수면음악', '자연의 소리', '처마 빗소리']),
    'fire_piano': dict(
        name='장작 타는 소리와 피아노', short=['장작 타는 소리', '따뜻한 피아노'], emoji='🔥', style=['piano', 'guitar_arp', 'felt_nocturne', 'piano_ambient'], layers={'fire': -12},
        scenes=['candle', 'snowwin', 'warm', 'camp', 'candle', 'snow'], thumb='candle', glow='#ffb070', kids=False, scene_db=0,
        sub='겨울밤 포근한 수면음악',
        desc='타닥타닥 장작 타는 소리와 포근한 피아노, 기타. 추운 겨울밤, 따뜻한 방 안에 누워 있는 느낌으로 만들었습니다.',
        tags=['장작 타는 소리', '모닥불 소리', '피아노', '수면음악', '겨울 음악', '힐링음악', '잠잘때 듣는 음악', 'asmr', 'fireplace', 'sleep music']),
    'snow_harp': dict(
        name='눈 오는 밤 하프 자장가', short=['눈 오는 밤', '하프 자장가'], emoji='❄️', style=['harp', 'glass_ambient', 'vibes', 'harp_canon'], layers={},
        scenes=['snow', 'snowwin', 'aurora', 'snow', 'candle', 'night'], thumb='snow', glow='#e4ecff', kids=False, scene_db=-2,
        sub='포근한 겨울밤 수면음악',
        desc='소리 없이 눈이 쌓이는 밤, 맑은 하프와 유리 종소리, 비브라폰으로 연주하는 새 자장가들입니다. 창밖으로 바람이 살짝 지나가요.',
        tags=['자장가', '하프', '수면음악', '겨울밤', '눈 오는 밤', '힐링음악', '잠 잘오는 음악', '오르골', 'lullaby', 'sleep music']),
    'stream_kalimba': dict(
        name='시냇물 소리와 칼림바', short=['시냇물 소리', '칼림바'], emoji='🏞️', style=['kalimba_arp', 'kalimba_ambient', 'guitar_arp'], layers={'stream': -12},
        scenes=['stream', 'bamboo', 'firefly', 'stream', 'pond', 'meadow'], thumb='stream', glow='#a8ffd8', kids=False, scene_db=0,
        sub='계곡 물소리 · 힐링 수면음악',
        desc='돌 틈을 흐르는 시냇물 소리와 맑은 칼림바·기타 아르페지오. 숲속 계곡 옆에 누워 있는 것처럼 편안해요.',
        tags=['시냇물 소리', '물소리', '칼림바', '계곡 소리', '수면음악', '힐링음악', '자연의 소리', 'asmr', 'stream sounds', 'kalimba']),
    'night_guitar': dict(
        name='여름밤 귀뚜라미와 기타', short=['여름밤 귀뚜라미', '나일론 기타'], emoji='🦗', style=['guitar', 'guitar_arp', 'flute_song'], layers={'crickets': -18},
        scenes=['firefly', 'meadow', 'camp', 'stream', 'firefly', 'night'], thumb='night', glow='#c8e8a0', kids=False, scene_db=0,
        sub='시골 평상에 누운 밤 · 수면음악',
        desc='귀뚜라미 우는 여름밤, 나일론 기타와 플루트가 느리게 연주합니다. 모든 곡은 이번 영상을 위해 새로 지은 곡이에요.',
        tags=['귀뚜라미 소리', '여름밤', '기타 수면음악', '통기타', '수면음악', '힐링음악', '자연의 소리', 'asmr', 'crickets', 'guitar sleep music']),
    'windchime': dict(
        name='풍경 소리 앰비언트', short=['풍경 소리', '앰비언트'], emoji='🎐', style=['glass_ambient', 'bowl_ambient', 'felt_ambient'], layers={'chimes': -12},
        scenes=['eaves', 'bamboo', 'aurora', 'night', 'pond', 'sea'], thumb='bamboo', glow='#d0f0ff', kids=False, scene_db=-2,
        sub='바람에 흔들리는 풍경 · 명상 수면음악',
        desc='처마 끝 풍경이 바람에 흔들리고, 박자 없이 천천히 떠다니는 유리 종·싱잉볼·펠트 피아노 앰비언트가 흐릅니다.',
        tags=['풍경 소리', '앰비언트', '명상음악', '수면음악', '힐링음악', 'asmr', 'wind chimes', 'ambient sleep', '요가음악', '마음 안정']),
    'thunder_piano': dict(
        name='먼 천둥 빗소리와 피아노', short=['먼 천둥 빗소리', '피아노'], emoji='⛈️', style=['piano_ambient', 'piano_nocturne', 'epiano_arp'], layers={'rain': -10},
        scenes=['storm', 'rainwin', 'study', 'storm', 'eaves', 'tentrain'], thumb='storm', glow='#b0c4ff', kids=False, scene_db=0,
        sub='비 오는 밤 깊은 잠 · 수면음악',
        desc='창밖 빗소리 사이로 가끔 멀리서 천둥이 낮게 울립니다. 그 위로 느린 피아노 녹턴이 띄엄띄엄 흘러요.',
        tags=['천둥소리', '빗소리', '피아노 수면음악', '비 오는 밤', '수면음악', '불면증', 'asmr', 'thunderstorm', 'rain piano', '잠 잘오는 음악']),
    'cat_purr': dict(
        name='고양이 골골송과 오르골', short=['고양이 골골송', '오르골'], emoji='🐈', style=['musicbox', 'glass_ambient', 'felt_ambient'], layers={'purr': -5}, music_db=-4,
        scenes=['candle', 'snowwin', 'warm', 'candle', 'study', 'snowwin'], thumb='candle', glow='#ffd0a0', kids=False, scene_db=-4,
        sub='고양이 품에 안긴 듯한 수면음악',
        desc='무릎 위에서 골골대는 고양이 소리와 작은 오르골, 멀리서 타는 난로 소리. 포근하게 잠드는 밤을 위해 만들었습니다.',
        tags=['고양이 골골송', '고양이 소리', '골골송', '오르골', '수면음악', 'asmr', 'cat purring', '힐링음악', '잠 잘오는 음악', '마음 안정']),
    'clock_epiano': dict(
        name='늦은 밤 서재, 시계와 일렉피아노', short=['늦은 밤 서재', '일렉피아노'], emoji='🕰️', style=['epiano_arp', 'vibes', 'felt_nocturne'], layers={},
        scenes=['study', 'candle', 'rainwin', 'study', 'snowwin', 'storm'], thumb='study', glow='#ffd9a8', kids=False, scene_db=0,
        sub='재즈 느낌 잔잔한 수면음악',
        desc='똑딱이는 괘종시계, 가끔 책장 넘기는 소리, 따뜻한 일렉피아노와 비브라폰. 늦은 밤 스탠드 하나 켜 둔 서재에서 잠드는 느낌이에요.',
        tags=['일렉피아노', '재즈 수면음악', '시계 소리', '수면음악', '힐링음악', 'lofi', 'asmr', 'jazz sleep', '잠 잘오는 음악', '늦은 밤']),
    'flute_meditation': dict(
        name='명상 플루트 드론', short=['명상 플루트', '드론 음악'], emoji='🧘', style=['flute_drone', 'handpan_arp', 'bowl_drone'], layers={},
        scenes=['aurora', 'stream', 'bamboo', 'night', 'meadow', 'aurora'], thumb='aurora', glow='#c0b0ff', kids=False, scene_db=-2,
        sub='깊은 호흡 · 명상 · 수면',
        desc='낮게 깔린 현악 드론 위로 플루트·핸드팬·싱잉볼이 박자 없이 천천히 노래합니다. 명상과 깊은 잠을 위한 음악이에요.',
        tags=['명상음악', '플루트', '드론 음악', '수면음악', '요가음악', '싱잉볼', '핸드팬', 'meditation music', 'deep sleep', '마음 안정']),
    'singing_bowl': dict(
        name='싱잉볼 앰비언트', short=['싱잉볼', '앰비언트'], emoji='🔔', style=['bowl_ambient', 'bowl_drone', 'glass_ambient'], layers={'pink': -26},
        scenes=['candle', 'aurora', 'underwater', 'night', 'bamboo', 'candle'], thumb='candle', glow='#ffe0b0', kids=False, scene_db=-4,
        sub='티베탄 싱잉볼 · 깊은 이완',
        desc='길게 울리는 싱잉볼과 유리 종이 겹치며 천천히 사라지는 앰비언트. 머릿속이 조용해지는 깊은 이완 음악입니다.',
        tags=['싱잉볼', '티베탄 싱잉볼', '명상음악', '수면음악', '힐링음악', '앰비언트', 'singing bowl', 'deep relaxation', '마음 안정', '이완']),
    'bamboo_daegeum': dict(
        name='달빛 대숲, 대금 소리', short=['달빛 대숲', '대금'], emoji='🎋', style=['daegeum_folk', 'gayageum_folk', 'flute_drone'], layers={},
        scenes=['bamboo', 'pond', 'eaves', 'bamboo', 'stream', 'night'], thumb='bamboo', glow='#b8f0d0', kids=False, scene_db=0,
        sub='국악 명상 · 깊은 잠',
        desc='바람에 대나무가 서로 부딪히는 소리, 그 사이로 대금과 가야금이 다섯 음으로 느리게 노래합니다. 한옥 처마와 연못으로 장면이 이어져요.',
        tags=['대금', '국악 명상', '대나무 숲', '가야금', '국악 수면음악', '명상음악', '수면음악', '자연의 소리', 'asmr', 'korean traditional music']),
    'felt_nocturne': dict(
        name='눈 오는 창가, 펠트 피아노 녹턴', short=['눈 오는 창가', '펠트 피아노'], emoji='🎹', style=['felt_nocturne', 'felt_ambient', 'felt_canon', 'piano_nocturne'], layers={},
        scenes=['snowwin', 'study', 'candle', 'rainwin', 'snowwin', 'snow'], thumb='snowwin', glow='#ffe0c0', kids=False, scene_db=-2,
        sub='귓가에서 들리는 부드러운 피아노 · 수면음악',
        desc='현에 천을 대어 아주 부드럽게 만든 펠트 피아노를 귓가에서 듣는 것 같은 녹턴입니다. 창밖에는 눈이 내리고, 방 안엔 시계와 난로 소리가 작게 들려요.',
        tags=['펠트 피아노', '피아노 수면음악', '녹턴', '잔잔한 피아노', '수면음악', '힐링음악', 'asmr', 'felt piano', 'sleep piano', '잠 잘오는 음악']),
    'camping_guitar': dict(
        name='별빛 캠핑, 모닥불과 기타', short=['별빛 캠핑', '모닥불과 기타'], emoji='🏕️', style=['guitar', 'guitar_arp', 'ocarina_song'], layers={},
        scenes=['camp', 'meadow', 'tentrain', 'camp', 'firefly', 'night'], thumb='camp', glow='#ffc080', kids=False, scene_db=0,
        sub='캠핑장 밤공기 · 힐링 수면음악',
        desc='타닥이는 모닥불, 멀리서 우는 부엉이와 귀뚜라미, 나일론 기타와 오카리나. 텐트 위로 비가 지나가기도 하는 캠핑의 밤입니다.',
        tags=['캠핑', '모닥불 소리', '불멍', '기타 수면음악', '캠핑 asmr', '수면음악', '힐링음악', '자연의 소리', 'campfire', 'camping sounds']),
    'deep_sea': dict(
        name='깊은 바닷속 앰비언트', short=['깊은 바닷속', '앰비언트'], emoji='🪼', style=['ocean_ambient', 'glass_ambient', 'felt_ambient'], layers={},
        scenes=['underwater', 'sea', 'underwater', 'aurora', 'underwater', 'night'], thumb='underwater', glow='#8fe0ff', kids=False, scene_db=0,
        sub='해파리와 함께 떠다니는 수면음악',
        desc='수면에서 내려오는 빛줄기 아래로 해파리가 천천히 떠오릅니다. 웅웅대는 깊은 물소리와 보글보글 기포, 박자 없는 유리 종 앰비언트.',
        tags=['바닷속', '해파리', '앰비언트', '수면음악', '명상음악', '물속 소리', 'asmr', 'underwater sounds', 'deep sleep', '힐링음악']),
    'tent_rain': dict(
        name='텐트 안에서 듣는 빗소리', short=['텐트 빗소리', '음악 없음'], emoji='⛺', style=None, layers={'brown': -20},
        scenes=['tentrain', 'camp', 'tentrain', 'storm', 'tentrain', 'pond'], thumb='tentrain', glow='#ffc890', kids=False, scene_db=2,
        sub='캠핑 빗소리 ASMR · 깊은 잠',
        desc='랜턴 하나 켜 둔 텐트 안, 천 위로 투둑투둑 떨어지는 빗소리. 가끔 멀리서 천둥이 울리고, 비가 그친 사이엔 모닥불과 풀벌레 소리가 들립니다.',
        tags=['텐트 빗소리', '캠핑 빗소리', '빗소리 asmr', '수면 빗소리', '캠핑 asmr', 'rain on tent', '자연의 소리', '수면음악', '백색소음', '천둥소리']),
    # ───────── 드림코어 도트 (pixel=True: 도트 장면 · 도트 썸네일 · 영문 와이드 제목)
    'dream_lasttrain': dict(
        name='퇴근길 막차, 꿈속 드림웨이브', en='ｌａｓｔ　ｔｒａｉｎ　ｈｏｍｅ', short=['ｌａｓｔ　ｔｒａｉｎ　ｈｏｍｅ', '퇴근길 막차에서 잠들기'], emoji='🌃',
        style=['dreamwave', 'dream_vibes', 'dream_ambient', 'dreamwave'], layers={'vinyl': -20}, pixel=True,
        scenes=['px_train', 'px_city', 'px_street', 'px_train', 'px_room', 'px_clouds'], thumb='px_train', glow='#ff8fd0', kids=False, scene_db=-2,
        sub='도트 드림코어 로파이 · 잠들기 전 수면음악',
        desc='야근 끝, 막차 창밖으로 노을 진 도시가 천천히 지나갑니다. 80년대 신스 패드와 일렉피아노가 오래된 테이프처럼 살짝 울렁이며 흐르고, 덜컹이는 레일 소리에서 비 오는 편의점 거리, 작은 내 방까지 이어지는 꿈속 퇴근길이에요.',
        tags=['드림코어', 'dreamcore', '로파이', 'lofi', '베이퍼웨이브', 'vaporwave', '신스웨이브', '도트', '픽셀아트', 'pixel art', '퇴근길 음악', '수면음악', '잠잘때 듣는 음악', 'sleep music', 'chill', '시티팝']),
    'dream_rainroom': dict(
        name='비 오는 새벽 3시, 내 방 로파이', en='ｍｉｄｎｉｇｈｔ　ｒａｉｎ　ｒｏｏｍ', short=['ｍｉｄｎｉｇｈｔ　ｒａｉｎ', '비 오는 새벽, 내 방'], emoji='🌧️',
        style=['dream_vibes', 'dream_glass', 'dreamwave', 'dream_ambient'], layers={'vinyl': -16}, pixel=True,
        scenes=['px_room', 'px_street', 'px_room', 'px_pool', 'px_city', 'px_room'], thumb='px_room', glow='#7fffd0', kids=False, scene_db=-1,
        sub='빗소리 · LP 잡음 · 도트 로파이 수면음악',
        desc='창밖엔 비가 내리고 CRT 모니터만 조용히 빛나는 새벽의 작은 방. 고양이는 침대 위에서 잠들었고, LP 잡음과 빗소리 위로 느린 일렉피아노와 비브라폰이 흐릅니다.',
        tags=['로파이', 'lofi', '빗소리', '드림코어', 'dreamcore', '도트', '픽셀아트', 'pixel art', 'lofi rain', 'LP 잡음', '새벽 감성', '수면음악', '공부할때 듣는 음악', 'sleep music', 'chill beats', '베이퍼웨이브']),
    'dream_cloudhall': dict(
        name='구름 복도, 끝나지 않는 꿈', en='ｃｌｏｕｄ　ｈａｌｌｗａｙ', short=['ｃｌｏｕｄ　ｈａｌｌｗａｙ', '끝나지 않는 꿈'], emoji='☁️',
        style=['dream_glass', 'dream_ambient', 'dreamwave'], layers={'vinyl': -22}, pixel=True,
        scenes=['px_clouds', 'px_pool', 'px_clouds', 'px_city', 'px_clouds', 'px_train'], thumb='px_clouds', glow='#c9a8ff', kids=False, scene_db=-2,
        sub='드림코어 · 리미널 스페이스 앰비언트 수면음악',
        desc='분홍 체크무늬 바닥이 끝없이 이어지는 구름 위 복도, 아무도 없는 밤의 실내 수영장. 어디선가 본 것 같은 낯익은 꿈속 공간에서 유리 종과 신스 패드가 천천히 퍼집니다.',
        tags=['드림코어', 'dreamcore', '리미널 스페이스', 'liminal space', '앰비언트', 'ambient', '도트', '픽셀아트', 'pixel art', '베이퍼웨이브', 'vaporwave', '수면음악', '명상음악', 'sleep music', '꿈', 'weirdcore']),
    # ───────── 시티팝 (1980~90년대 일본 버블 · 미국 80년대) — 고해상도 도트 + VHS, 썸네일에 캠코더식 연도
    'citypop_drive': dict(
        name='1988 도쿄, 퇴근길 밤의 고속도로', en='ｍｉｄｎｉｇｈｔ　ｄｒｉｖｅ', year='1988.', short=['ｍｉｄｎｉｇｈｔ　ｄｒｉｖｅ', '퇴근길 밤의 고속도로'], emoji='🌃',
        style=['citypop', 'dreamwave', 'dream_vibes'], layers={'vinyl': -22}, pixel=True,
        scenes=['cp_drive', 'cp_room', 'cp_drive', 'cp_boulevard'], thumb='cp_drive', glow='#ff4fa0', kids=False, scene_db=-2,
        sub='시티팝 · 80년대 드림웨이브 수면음악',
        desc='1988년 도쿄, 야근을 마치고 올라탄 밤의 고속도로. 네온 간판과 붉은 철탑이 창밖으로 흐르고, 카오디오에서는 오래된 카세트가 돌아갑니다. 80년대 신스와 일렉피아노로 새로 작곡한 시티팝풍 수면음악이에요.',
        tags=['시티팝', 'city pop', '80년대 음악', '1980s', '버블 시대', '베이퍼웨이브', 'vaporwave', '신스웨이브', 'synthwave', '레트로', '드라이브 음악', '퇴근길 음악', '수면음악', 'lofi', 'VHS', '도트']),
    'citypop_mansion': dict(
        name='1989 버블 시대, 바닷가 맨션의 노을', en='ｂｕｂｂｌｅ　ｓｕｎｓｅｔ', year='1989.', short=['ｂｕｂｂｌｅ　ｓｕｎｓｅｔ', '바닷가 맨션의 노을'], emoji='🌇',
        style=['citypop_vibes', 'dream_glass', 'dreamwave'], layers={'vinyl': -18}, pixel=True,
        scenes=['cp_room', 'cp_boulevard', 'cp_room', 'cp_drive'], thumb='cp_room', glow='#ff9a6a', kids=False, scene_db=-1,
        sub='시티팝 · 레트로 로파이 · 잠들기 전 음악',
        desc='1989년, 버블 시대의 바닷가 맨션. 블라인드 사이로 노을빛 줄무늬가 들어오고, 턴테이블 위 레코드와 오디오의 VU 미터가 천천히 흔들립니다. LP 잡음과 함께 듣는 느린 시티팝 수면음악이에요.',
        tags=['시티팝', 'city pop', '버블 시대', '80년대', '90년대', '레트로', 'retro', '로파이', 'lofi', 'LP', '턴테이블', '노을', '수면음악', 'vaporwave', 'VHS', '도트']),
    'citypop_miami': dict(
        name='1986 해변 대로, 야자수와 노을', en='ｏｃｅａｎ　ｂｏｕｌｅｖａｒｄ', year='1986.', short=['ｏｃｅａｎ　ｂｏｕｌｅｖａｒｄ', '야자수와 노을, 해변 대로'], emoji='🌴',
        style=['dreamwave', 'citypop', 'dream_ambient'], layers={'vinyl': -22}, pixel=True,
        scenes=['cp_boulevard', 'cp_drive', 'cp_boulevard', 'cp_room'], thumb='cp_boulevard', glow='#ffb050', kids=False, scene_db=-1,
        sub='80년대 아웃런 · 신스웨이브 수면음악',
        desc='1986년 여름, 줄무늬 노을 해가 바다로 내려앉는 해변 대로. 야자수가 바람에 흔들리고 호텔 네온이 하나둘 켜집니다. 파도 소리 위로 흐르는 80년대 신스웨이브 수면음악이에요.',
        tags=['신스웨이브', 'synthwave', '아웃런', 'outrun', '80년대', '1980s', '레트로', 'retrowave', '마이애미', '야자수', '노을', '시티팝', '수면음악', 'vaporwave', 'VHS', '도트']),
    # ───────── 비 오는 80~90년대 도시 — 채널 주인이 준 그림 그대로 + 비만 내림 (rainimg.py · assets/rain_*.png)
    'rain_tokyo1989': dict(
        name='1989 도쿄, 비 오는 퇴근길', en='ｔｏｋｙｏ　ｒａｉｎ　１９８９', year='平成元年', short=['ｔｏｋｙｏ　ｒａｉｎ　１９８９', '비 오는 신주쿠 퇴근길'], emoji='🌧️',
        style=['dream_vibes', 'citypop', 'dream_glass', 'dreamwave'], layers={'vinyl': -22}, pixel=True,
        thumb_file='rain_crt.png', thumb_text=False, minutes=154,                     # 썸네일 브라운관 속 '♪ 2:34:01' 과 같은 길이
        scenes=['img_shinjuku', 'img_office_street', 'img_shinjuku', 'img_office_street'], thumb='img_shinjuku', glow='#ff4f7a', kids=False, scene_db=-1,
        sub='비 오는 시티팝 · 드림코어 로파이 수면음악',
        desc='1989년, 헤이세이가 막 시작된 도쿄. 네온 간판이 빛나는 신주쿠 거리와 오래된 오피스 골목에 밤비가 조용히 내립니다. 빗소리와 함께 흐르는 80년대 신스·일렉피아노 드림코어 수면음악입니다.',
        tags=['시티팝', 'city pop', '드림코어', 'dreamcore', '빗소리', 'rain', '80년대', '1989', '도쿄', '신주쿠', '로파이', 'lofi', '베이퍼웨이브', 'vaporwave', '도트', '픽셀아트', 'pixel art', '수면음악', 'sleep music', 'VHS']),
    'rain_ny1985': dict(
        name='1985 뉴욕에서 LA까지, 비 오는 밤', en='ｒａｉｎｙ　ｎｉｇｈｔ　１９８５', year='1985.', short=['ｒａｉｎｙ　ｎｉｇｈｔ　１９８５', '비 오는 밤, 맨해튼과 LA'], emoji='🌃',
        style=['dreamwave', 'dream_ambient', 'citypop_vibes', 'dream_vibes'], layers={'vinyl': -22}, pixel=True,
        thumb_file='rain_la_main.png',
        scenes=['img_la_main', 'img_manhattan', 'img_la_sunset', 'img_manhattan'], thumb='img_la_main', glow='#4ae0ff', kids=False, scene_db=-1,
        sub='80년대 신스웨이브 · 빗소리 드림코어 수면음악',
        desc='1985년, 비 내리는 LA 거리의 네온과 트렌치코트, 창밖으로 비가 내리는 맨해튼의 오래된 사무실, 그리고 노을 속 야자수. 빗소리 위로 흐르는 80년대 신스웨이브 드림코어 수면음악입니다.',
        tags=['신스웨이브', 'synthwave', '드림코어', 'dreamcore', '빗소리', 'rain', '80년대', '1985', '뉴욕', '맨해튼', 'LA', '로스앤젤레스', '레트로', 'retrowave', '로파이', 'lofi', '도트', '픽셀아트', '수면음악', 'VHS']),
}
# 아기 테마와 어른 테마가 번갈아 나오도록
ROTATION = ['rain_lullaby', 'brown_noise', 'humming_lullaby', 'waves_piano', 'lotus_gayageum', 'felt_nocturne', 'womb', 'rain_only', 'lullaby', 'camping_guitar',
            'meadow_ocarina', 'fire_piano', 'white_noise', 'stream_kalimba', 'firefly_lullaby', 'bamboo_daegeum', 'kalimba_lullaby', 'deep_sea',
            'night_guitar', 'tent_rain', 'windchime', 'citypop_drive', 'thunder_piano', 'cat_purr', 'clock_epiano', 'citypop_mansion', 'flute_meditation', 'snow_harp', 'singing_bowl', 'citypop_miami']
DREAM3 = ['dream_lasttrain', 'dream_rainroom', 'dream_cloudhall']          # 320 도트 드림코어 (자동 순서에서는 뺌, 직접 고를 때만)
CITYPOP3 = ['citypop_drive', 'citypop_mansion', 'citypop_miami']
RAIN2 = ['rain_tokyo1989', 'rain_ny1985']                                 # 비 오는 80~90년대 도시 (직접 고를 때만)
assert set(ROTATION) | set(DREAM3) | set(RAIN2) == set(THEMES) and len(ROTATION) == len(set(ROTATION))
