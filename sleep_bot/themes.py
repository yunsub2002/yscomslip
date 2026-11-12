# -*- coding: utf-8 -*-
"""채널 테마 (영상 1편 = 테마 1개). ROTATION 순서대로 돌아가며, 음악 테마와 자연음 테마가 번갈아 나옵니다.
style: 자장가 연주 방식(None=음악 없음) / layers: 자연음과 크기(dB, 0=음악과 같은 크기) / scenes: 배경 장면 4개(90초씩, 6분 루프)
"""
THEMES = {
    'rain_lullaby': dict(
        name='빗소리 오르골 자장가', short=['빗소리', '오르골 자장가'], emoji='🌧️', style='musicbox', layers={'rain': -7},
        scenes=['rainwin', 'night', 'rainwin', 'pastel'], thumb='rainwin', glow='#9fc4ff', kids=True,
        sub='아기 잠 잘 오는 음악 · 수면음악',
        desc='창밖에 조용히 내리는 빗소리 위로, 매번 새로 작곡한 오르골 자장가가 천천히 흘러갑니다.',
        tags=['빗소리 자장가', '오르골 자장가', '아기 수면음악', '자장가', '빗소리', '수면음악', '잠 잘오는 음악', '아기 잠재우기', 'lullaby', 'rain sounds']),
    'brown_noise': dict(
        name='브라운 노이즈', short=['브라운 노이즈', '깊은 잠'], emoji='🌌', style=None, layers={'brown': 0},
        scenes=['aurora', 'night', 'sea', 'snow'], thumb='aurora', glow='#8fe3c8', kids=False,
        sub='공부 · 집중 · 숙면을 위한 소리',
        desc='낮고 부드러운 브라운 노이즈입니다. 주변 소음을 덮어 주어 잠들기, 집중, 휴식에 좋아요. 음악이나 말소리는 없습니다.',
        tags=['브라운 노이즈', 'brown noise', '백색소음', '수면 소음', '집중 소음', '숙면', '공부할때 듣는', '수면음악', '이명', '1시간']),
    'waves_piano': dict(
        name='파도소리 잔잔한 피아노', short=['파도소리', '잔잔한 피아노'], emoji='🌊', style='piano', layers={'waves': -6},
        scenes=['sea', 'night', 'sea', 'aurora'], thumb='sea', glow='#ffe2a8', kids=False,
        sub='불면증 · 스트레스 해소 수면음악',
        desc='달빛 비치는 밤바다의 느린 파도 소리와, 이번 영상을 위해 새로 작곡한 잔잔한 피아노 연주입니다.',
        tags=['파도소리', '피아노 수면음악', '잔잔한 피아노', '수면음악', '힐링음악', '불면증', '명상음악', '잠잘때 듣는 음악', 'sleep music', 'ocean waves']),
    'womb': dict(
        name='엄마 뱃속 소리 자장가', short=['엄마 뱃속 소리', '자장가'], emoji='🤍', style='musicbox', layers={'heart': -3}, music_db=-7,
        scenes=['warm', 'pastel', 'warm', 'night'], thumb='warm', glow='#ffc48a', kids=True,
        sub='신생아 · 아기 울음 그치는 소리',
        desc='엄마 뱃속에서 듣던 낮은 쉬익 소리와 느린 심장 소리에, 아주 작은 오르골 자장가를 더했습니다. 신생아가 편안해하는 소리예요.',
        tags=['엄마 뱃속 소리', '심장소리', '신생아 수면', '아기 울음 그치는 소리', '자장가', '태교음악', '아기 재우기', '백색소음', '오르골', 'womb sounds']),
    'lullaby': dict(
        name='아기 자장가 오르골 모음', short=['아기 자장가', '오르골 모음'], emoji='🌙', style='harp', layers={},
        scenes=['pastel', 'night', 'firefly', 'pastel'], thumb='pastel', glow='#4a3a7a', kids=True,
        sub='맑고 포근한 꿀잠 음악',
        desc='맑은 첼레스타와 하프로 연주하는 자장가 모음입니다. 모든 곡이 이번 영상을 위해 새로 작곡된 곡이에요.',
        tags=['자장가', '아기 자장가', '오르골', '자장가 모음', '아기 수면음악', '꿀잠', '잠 잘오는 음악', '태교음악', 'baby lullaby', 'music box']),
    'rain_only': dict(
        name='창밖 빗소리', short=['창밖 빗소리', '음악 없음'], emoji='☔', style=None, layers={'rain': 0, 'brown': -14},
        scenes=['rainwin', 'night', 'rainwin', 'snow'], thumb='rainwin', glow='#b8d4ff', kids=False,
        sub='잠 잘 오는 빗소리 · 공부 · 휴식',
        desc='음악 없이 빗소리만 담았습니다. 창문에 부딪히는 빗방울과 멀리서 내리는 비의 낮은 소리가 1시간 동안 이어집니다.',
        tags=['빗소리', '빗소리 asmr', '잠잘때 빗소리', '수면 빗소리', '공부할때 빗소리', '백색소음', 'rain sounds', '수면음악', '자연의 소리', '1시간']),
    'fire_piano': dict(
        name='장작 타는 소리와 피아노', short=['장작 타는 소리', '따뜻한 피아노'], emoji='🔥', style='piano', layers={'fire': -6},
        scenes=['warm', 'snow', 'warm', 'night'], thumb='warm', glow='#ffb070', kids=False,
        sub='겨울밤 포근한 수면음악',
        desc='타닥타닥 장작 타는 소리와 포근한 피아노. 추운 겨울밤, 따뜻한 방 안에 누워 있는 느낌으로 만들었습니다.',
        tags=['장작 타는 소리', '모닥불 소리', '피아노', '수면음악', '겨울 음악', '힐링음악', '잠잘때 듣는 음악', 'asmr', 'fireplace', 'sleep music']),
    'white_noise': dict(
        name='아기 백색소음', short=['아기 백색소음', '쉬~ 소리'], emoji='☁️', style=None, layers={'white': -3, 'pink': -3},
        scenes=['pastel', 'night', 'pastel', 'firefly'], thumb='pastel', glow='#4a3a7a', kids=True,
        sub='신생아 재우기 · 울음 그치는 소리',
        desc='"쉬~" 하고 달래 주는 부드러운 백색소음입니다. 귀에 거슬리는 높은 소리를 줄여 오래 틀어 두어도 편안해요.',
        tags=['백색소음', '아기 백색소음', '신생아 백색소음', '아기 재우기', '울음 그치는 소리', 'white noise', '수면소음', '아기 수면', '쉬 소리', '1시간']),
    'snow_harp': dict(
        name='눈 오는 밤 하프 자장가', short=['눈 오는 밤', '하프 자장가'], emoji='❄️', style='harp', layers={'pink': -16},
        scenes=['snow', 'night', 'snow', 'aurora'], thumb='snow', glow='#e4ecff', kids=False,
        sub='포근한 겨울밤 수면음악',
        desc='소리 없이 눈이 쌓이는 밤, 맑은 하프와 첼레스타로 연주하는 새 자장가들입니다.',
        tags=['자장가', '하프', '수면음악', '겨울밤', '눈 오는 밤', '힐링음악', '잠 잘오는 음악', '오르골', 'lullaby', 'sleep music']),
    'firefly_lullaby': dict(
        name='반딧불 숲 오르골', short=['반딧불 숲', '오르골 자장가'], emoji='✨', style='mixed', layers={'pink': -18},
        scenes=['firefly', 'night', 'firefly', 'pastel'], thumb='firefly', glow='#d8ff9a', kids=True,
        sub='아이 잠자리 동화 같은 수면음악',
        desc='반딧불이 춤추는 여름밤 숲. 오르골과 부드러운 피아노가 번갈아 들려주는 새 자장가들입니다.',
        tags=['오르골', '자장가', '반딧불', '아기 수면음악', '어린이 자장가', '꿀잠', '수면음악', '잠 잘오는 음악', 'music box', 'lullaby']),
}
ROTATION = ['rain_lullaby', 'brown_noise', 'waves_piano', 'womb', 'lullaby', 'rain_only', 'fire_piano', 'white_noise', 'snow_harp', 'firefly_lullaby']
