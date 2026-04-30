# Ep 1 일러스트 — 이미지 생성 가이드

> 차라투스트라 비주얼 노벨 Ep 1의 8장 일러스트 생성용 마스터 문서.
> 모든 일러스트는 **글자 없는 풀 페이지 이미지**. 텍스트는 프론트엔드에서 별도 렌더링.

---

## 0. 공통 스타일 토큰 (모든 화면에 적용)

매 화면 프롬프트 앞에 이 블록 그대로 사용. **일관성의 핵심.**

### 영문 토큰 (Midjourney / Nano Banana / DALL-E 3 / SD)

```
19th century book illustration, etching engraving style, 
Gustave Doré inspired, monochrome black ink on aged sepia parchment paper, 
fine cross-hatching, dramatic chiaroscuro, romantic sublime mood, 
wide landscape composition, human figures small relative to nature, 
figures shown from distance or back only, faces never visible, 
no text, no signature, no watermark
```

### 한국어 의도 메모

> 19세기 도레 풍 흑백 판화. 세피아 종이 위 검은 잉크. 
> 파인 크로스해칭. 드라마틱 명암. 풍경 중심. 인물은 작게, 멀리서 또는 뒷모습. 얼굴 안 보임.

### Negative Prompt (제외 키워드)

```
color, photorealistic, modern, anime, manga, cartoon, 
close-up faces, portrait, watermark, text, signature, letters, 
multiple panels, comic, frame, border, decorative
```

### 도구별 추천 파라미터

| 도구 | 파라미터 |
|---|---|
| Midjourney v6+ | `--ar 16:10 --style raw --stylize 100` |
| Nano Banana / Gemini | 영문 프롬프트 그대로 |
| DALL-E 3 | 프롬프트 끝에 *"Important: monochrome only, no color, no text"* 추가 |
| SD + LoRA | `etching_lora` 또는 `dore_style_lora` 0.7~0.9 강도 |

### 일관성 확보 절차

1. **첫 화면을 *베이스 이미지*로 정한다** (#1 타이틀 권장 — 가장 정적)
2. 베이스 이미지 결정 후, **나머지 화면은 *image-to-image* 또는 *style reference*로 생성**
3. 도구 섞지 말 것. 한 도구로 8장 다 생성.
4. 시드(seed) 패밀리 통일: 비슷한 시드 범위 사용 (예: 12000~12100)

### 공통 파일 규격

- 해상도: **1600 × 1000 px** (16:10)
- 포맷: PNG (메인) + WebP (웹 최적화)
- 색공간: sRGB
- 배경 톤: 세피아 #f5ecd9 (베이스), 잉크 #1a1610

### 파일 구조

```
illustrations/
  screen_01_title.png
  screen_01_title.webp
  screen_02_prologue_summit.png
  screen_02_prologue_summit.webp
  screen_03_prologue_forest.png
  screen_03_prologue_forest.webp
  screen_04_prologue_road.png
  screen_04_prologue_road.webp
  screen_05_meeting.png
  screen_05_meeting.webp
  screen_06_walking.png
  screen_06_walking.webp
  screen_07_market_distant.png
  screen_07_market_distant.webp
  screen_08_ending.png
  screen_08_ending.webp
```

---

## 화면 일람

| # | 파일명 | 장면 | 핵심 모티프 |
|---|---|---|---|
| 1 | `screen_01_title` | 타이틀 | 새벽 알프스 능선, 동굴 입구, 작은 인영 |
| 2 | `screen_02_prologue_summit` | 프롤로그 — 산 정상 | 동굴 앞 인물(뒷모습), 떠오르는 해, 아래로 펼쳐진 길 |
| 3 | `screen_03_prologue_forest` | 프롤로그 — 숲의 성자 | 깊은 숲, 두 인물 만남, 빛줄기, 새 |
| 4 | `screen_04_prologue_road` | 프롤로그 — 길로 나섬 | 혼자 멀어지는 인물(뒷모습), 광활한 앞길 |
| 5 | `screen_05_meeting` | 만남 — 길 | 두 인물 마주봄, 학습자 뒷모습, 길의 교차 |
| 6 | `screen_06_walking` | 동행 — 길 진행 | 두 인물 함께 걷음(뒷모습), 굽이진 길 |
| 7 | `screen_07_market_distant` | 종결 — 시장 원경 | 언덕 위 두 인물, 멀리 골짜기 마을, 황혼 |
| 8 | `screen_08_ending` | 엔딩 — 빈 길 | 인물 없음, 발자국 두 줄, 갈림길, 황혼 |

---

## 화면 #1 — 타이틀

### 컨셉
새벽녘 알프스 능선. 한 사람의 형상이 정상 부근에 작게 서 있다. 차라투스트라가 *아직 하산하지 않은* 시점. 정적, 거대한 자연, 작은 인간. 동굴 입구가 바위벽에 희미하게 보인다.

### 분위기
- 시간대: 새벽 (dawn)
- 정서: 정적, 숭고, 영원한 고독, 사색적
- 인물 위치: 능선 정상 부근, 매우 작게, 멀리서 본 실루엣만
- 인물 디테일: 얼굴 안 보임, 옆/뒷모습

### 프롬프트 (위 공통 토큰 + 아래)

```
Wide landscape view of alpine mountain ridges at dawn, 
sharp jagged peaks rising into a vast pale sky, 
a single human figure standing very small near the peak silhouette, 
seen from far distance as a tiny silhouette against the sky, 
face not visible. 
A cave entrance faintly visible in the rock face below the figure. 
Dramatic chiaroscuro: bright dawn sky behind peaks, 
deep shadows in the valleys below. 
Fine cross-hatching for sky gradient and rock textures. 
Sublime romantic mood, eternal solitude, contemplative atmosphere.
```

### 풀 프롬프트 (복붙용)

```
19th century book illustration, etching engraving style, 
Gustave Doré inspired, monochrome black ink on aged sepia parchment paper, 
fine cross-hatching, dramatic chiaroscuro, romantic sublime mood, 
wide landscape composition, human figures small relative to nature, 
figures shown from distance or back only, faces never visible, 
no text, no signature, no watermark.

Wide landscape view of alpine mountain ridges at dawn, 
sharp jagged peaks rising into a vast pale sky, 
a single human figure standing very small near the peak silhouette, 
seen from far distance as a tiny silhouette against the sky, 
face not visible. 
A cave entrance faintly visible in the rock face below the figure. 
Dramatic chiaroscuro: bright dawn sky behind peaks, 
deep shadows in the valleys below. 
Fine cross-hatching for sky gradient and rock textures. 
Sublime romantic mood, eternal solitude, contemplative atmosphere.

Negative: color, photorealistic, modern, anime, manga, cartoon, 
close-up faces, portrait, watermark, text, signature, letters, 
multiple panels, comic, frame, border, decorative.
```

### 구도 가이드

- 화면 상단 60%: 하늘 (밝은 새벽빛, 부드러운 해칭)
- 화면 중단 30%: 능선 (날카로운 검은 실루엣, 거친 해칭)
- 화면 하단 10%: 계곡 그림자 (가장 짙은 잉크)
- 인물: 화면 중앙 약간 좌측, 능선 위 작은 점 + 짧은 직선
- 동굴: 인물 아래쪽 바위벽, 검은 사각 영역

### 체크리스트

- [ ] 컬러 없음 (순수 흑백 + 세피아 베이스)
- [ ] 글자/서명/워터마크 없음
- [ ] 인물 얼굴 안 보임
- [ ] 인물이 풍경 대비 충분히 작음 (전체 높이의 5% 이하)
- [ ] 도레 스타일 크로스해칭 디테일 살아있음
- [ ] 새벽 분위기 (해 뜨기 직전 톤)
- [ ] 16:10 비율
- [ ] 1600×1000 이상 해상도

---

## 화면 #2 — 프롤로그 — 산 정상

### 컨셉
차라투스트라가 동굴 앞에 서 있다. 10년의 고독을 마치고 하산하기로 결심한 순간. 동굴 입구가 그의 *지난 시간*이고, 아래로 펼쳐진 산길이 그의 *앞으로의 길*이다. 인물은 동굴 입구에 서서 *아래를 내려다본다* — 뒷모습으로.

### 분위기
- 시간대: 새벽 후, 막 떠오르는 해
- 정서: 결심, 전환점, 떠남의 직전
- 인물 위치: 동굴 입구, 화면 중앙, 약간 작게
- 인물 디테일: 뒷모습, 망토 또는 긴 옷자락, 아래를 향한 자세

### 프롬프트 (위 공통 토큰 + 아래)

```
A solitary figure stands at the entrance of a mountain cave, 
seen from behind, looking down at a winding path that descends into a vast valley below. 
Morning sun rising over distant peaks casts long dramatic shadows. 
The cave entrance is a dark archway in jagged rock, the figure small in the foreground. 
Below stretches an immense alpine landscape with descending paths, 
wisps of cloud in the valley. 
The figure wears a flowing cloak, only silhouette and back visible, no face. 
Composition emphasizes the threshold moment — cave behind, world below. 
Heavy cross-hatching for the cave's interior darkness, 
delicate hatching for the bright valley far below.
```

### 풀 프롬프트 (복붙용)

```
19th century book illustration, etching engraving style, 
Gustave Doré inspired, monochrome black ink on aged sepia parchment paper, 
fine cross-hatching, dramatic chiaroscuro, romantic sublime mood, 
wide landscape composition, human figures small relative to nature, 
figures shown from distance or back only, faces never visible, 
no text, no signature, no watermark.

A solitary figure stands at the entrance of a mountain cave, 
seen from behind, looking down at a winding path that descends into a vast valley below. 
Morning sun rising over distant peaks casts long dramatic shadows. 
The cave entrance is a dark archway in jagged rock, the figure small in the foreground. 
Below stretches an immense alpine landscape with descending paths, 
wisps of cloud in the valley. 
The figure wears a flowing cloak, only silhouette and back visible, no face. 
Composition emphasizes the threshold moment — cave behind, world below. 
Heavy cross-hatching for the cave's interior darkness, 
delicate hatching for the bright valley far below.

Negative: color, photorealistic, modern, anime, manga, cartoon, 
close-up faces, portrait, watermark, text, signature, letters, 
multiple panels, comic, frame, border, decorative.
```

### 구도 가이드

- 화면 좌측 30%: 동굴 입구 — 짙은 검정, 거친 해칭
- 화면 중앙: 인물 (뒷모습) — 동굴과 풍경 경계에 서 있음
- 화면 우측 70%: 아래로 펼쳐진 계곡 풍경 — 부드러운 해칭, 원근감
- 상단: 떠오르는 해 빛 (밝은 영역, 거의 백지 가까움)
- 하단: 굽이진 산길의 시작점 (인물 발 아래)

### 체크리스트

- [ ] 컬러 없음
- [ ] 글자/서명 없음
- [ ] 인물 *뒷모습* 강조, 얼굴 안 보임
- [ ] 동굴(과거)과 계곡(미래)의 *대조* 명확
- [ ] 해 떠오르는 빛이 풍경에 비침
- [ ] 16:10 비율, 1600×1000 이상

---

## 화면 #3 — 프롤로그 — 숲의 성자

### 컨셉
울창한 숲 속, 두 인물이 만난다. 한쪽은 차라투스트라(걸어가는 자), 다른 쪽은 늙은 성자(나무 옆에 서서 노래하는 자). 둘 다 *멀리서, 작게* 보이며, 빛이 나뭇잎 사이로 부서져 내린다. 노인은 새들과 함께 있다는 암시 — 작은 새 형상 또는 비둘기.

### 분위기
- 시간대: 한낮, 숲 속 빛
- 정서: 우연한 만남, 마지막 권유, 거절
- 인물 위치: 좌측 차라투스트라 (걸어가는 자세), 우측 성자 (정적, 나무 옆)
- 인물 디테일: 둘 다 작고 멀리, 얼굴 안 보임. 차라투스트라는 망토, 성자는 노인 형상 (긴 수염은 불필요, 굽은 자세 정도)

### 프롬프트 (위 공통 토큰 + 아래)

```
Deep forest scene with tall ancient trees, dappled sunlight piercing through dense canopy. 
Two distant human figures meet on a narrow forest path: 
on the left, a traveler walking down the path with a flowing cloak, seen from behind in mid-stride; 
on the right, an old hermit standing beside a great tree trunk, slightly hunched, 
small birds gathered near him. 
Both figures are small and distant, no faces visible. 
Shafts of light cut through the trees, illuminating the meeting point on the path. 
Rich cross-hatching for tree bark and foliage shadows, 
finer hatching for light shafts and forest floor. 
Atmosphere of unexpected encounter in vast wilderness.
```

### 풀 프롬프트 (복붙용)

```
19th century book illustration, etching engraving style, 
Gustave Doré inspired, monochrome black ink on aged sepia parchment paper, 
fine cross-hatching, dramatic chiaroscuro, romantic sublime mood, 
wide landscape composition, human figures small relative to nature, 
figures shown from distance or back only, faces never visible, 
no text, no signature, no watermark.

Deep forest scene with tall ancient trees, dappled sunlight piercing through dense canopy. 
Two distant human figures meet on a narrow forest path: 
on the left, a traveler walking down the path with a flowing cloak, seen from behind in mid-stride; 
on the right, an old hermit standing beside a great tree trunk, slightly hunched, 
small birds gathered near him. 
Both figures are small and distant, no faces visible. 
Shafts of light cut through the trees, illuminating the meeting point on the path. 
Rich cross-hatching for tree bark and foliage shadows, 
finer hatching for light shafts and forest floor. 
Atmosphere of unexpected encounter in vast wilderness.

Negative: color, photorealistic, modern, anime, manga, cartoon, 
close-up faces, portrait, watermark, text, signature, letters, 
multiple panels, comic, frame, border, decorative.
```

### 구도 가이드

- 화면 전체 80%: 거대한 나무들, 숲의 깊이감
- 화면 중앙 하단: 좁은 길, 두 인물의 만남 지점
- 좌측 인물 (차라투스트라): 길 위, 걸어가는 자세, 뒷모습
- 우측 인물 (성자): 큰 나무 옆, 정적인 자세, 옆모습 또는 뒤
- 상단: 나뭇잎 사이로 비추는 빛줄기 — 만남 지점 조명
- 작은 새 2~3마리: 성자 주변 (노인이 새와 노래한다는 원전 모티프)

### 체크리스트

- [ ] 두 인물 *모두* 작고 멀리, 얼굴 안 보임
- [ ] 숲의 깊이감 (큰 나무 + 빛 사이 음영)
- [ ] 만남 지점에 빛 집중 (드라마 효과)
- [ ] 새 형상 살짝 (성자의 동물 동반자 모티프)
- [ ] 컬러 없음, 글자 없음
- [ ] 16:10 비율

---

## 화면 #4 — 프롤로그 — 길로 나섬

### 컨셉
숲을 빠져나와 펼쳐진 길. 차라투스트라 혼자 — *방금 성자와 헤어진 직후*. 그가 멀어지는 뒷모습. 그의 입에서 *"신이 죽었다는 소식을 아직 듣지 못했구나"*라는 혼잣말이 막 흘러나오는 순간이지만, **그림에는 글자가 없으므로 정적·고독의 분위기로만 표현**.

이 화면이 *학습자 등장 직전 마지막 정적*. 다음 #5에서 *"그대. 어디서 왔는가"*로 차라투스트라가 학습자에게 말을 건넨다.

### 분위기
- 시간대: 한낮 → 오후 전환
- 정서: 사색적 혼잣말, 고독, 길의 시작
- 인물 위치: 화면 중앙, 멀어지는 뒷모습
- 인물 디테일: 뒷모습, 망토, 약간 굽은 어깨 (사색의 자세)

### 프롬프트 (위 공통 토큰 + 아래)

```
A solitary cloaked figure walking down an open path, 
seen from behind, slightly stooped as if in deep thought. 
The path emerges from a forest edge on the left and stretches 
into rolling hills on the right. 
The figure is small in the middle distance, walking away from the viewer. 
Vast sky above with scattered clouds, soft cross-hatching for atmospheric depth. 
Late morning light, the road empty except for the figure. 
Mood of contemplative solitude, the moment after parting from someone, 
a soliloquy unspoken but felt in the posture. 
Detailed ground textures of the path, distant rolling landscape.
```

### 풀 프롬프트 (복붙용)

```
19th century book illustration, etching engraving style, 
Gustave Doré inspired, monochrome black ink on aged sepia parchment paper, 
fine cross-hatching, dramatic chiaroscuro, romantic sublime mood, 
wide landscape composition, human figures small relative to nature, 
figures shown from distance or back only, faces never visible, 
no text, no signature, no watermark.

A solitary cloaked figure walking down an open path, 
seen from behind, slightly stooped as if in deep thought. 
The path emerges from a forest edge on the left and stretches 
into rolling hills on the right. 
The figure is small in the middle distance, walking away from the viewer. 
Vast sky above with scattered clouds, soft cross-hatching for atmospheric depth. 
Late morning light, the road empty except for the figure. 
Mood of contemplative solitude, the moment after parting from someone, 
a soliloquy unspoken but felt in the posture. 
Detailed ground textures of the path, distant rolling landscape.

Negative: color, photorealistic, modern, anime, manga, cartoon, 
close-up faces, portrait, watermark, text, signature, letters, 
multiple panels, comic, frame, border, decorative.
```

### 구도 가이드

- 화면 좌측: 숲의 가장자리 (방금 빠져나온 곳, 어두운 잔영)
- 화면 중앙: 길과 인물 — 인물은 길의 1/3 지점에 위치
- 화면 우측~상단: 광활한 풍경 (앞으로 갈 길의 방향)
- 하늘: 화면 상단 50%, 부드러운 해칭, 구름 약간
- 인물: 화면 높이의 8% 정도, 뒷모습, 약간 굽은 자세

### 체크리스트

- [ ] 인물 *혼자*, 뒷모습
- [ ] 자세에 *사색·혼잣말*의 분위기 (어깨 약간 굽음)
- [ ] 숲(과거 만남)에서 *멀어지는* 방향
- [ ] 광활한 *앞길*이 화면에 펼쳐짐
- [ ] 컬러 없음, 글자 없음
- [ ] 16:10 비율

---

## 화면 #5 — 만남 — 길

### 컨셉
**핵심 화면.** 학습자가 차라투스트라와 처음 만나는 순간. 길의 한 지점에서 두 형상이 마주친다. 차라투스트라는 *멈춰서 학습자를 향해 몸을 돌렸고*, 학습자는 *길 한가운데에 서 있다*. 둘 다 작고 멀리, 얼굴은 안 보인다. 

이 화면이 **두 결 융합의 시각적 시작점.** 외부 결(차라투스트라의 길) + 내부 결(학습자의 등장). 풍경이 *길의 교차점* 같은 느낌이면 좋다.

### 분위기
- 시간대: 오후
- 정서: 첫 만남, 잠시 멈춤, 어색함과 호기심의 사이
- 인물 위치: 두 인물이 *마주보는* 구도, 약간의 거리
- 인물 디테일: 차라투스트라는 측면(학습자를 향해 몸을 튼 자세), 학습자는 화면을 등진 뒷모습 (시청자 = 학습자 시점 가까움)

### 프롬프트 (위 공통 토큰 + 아래)

```
Two figures meeting on an open road in rolling alpine countryside. 
On the left mid-distance, a cloaked figure has paused mid-walk and turned 
to face the other, body in profile, no face visible due to cloak hood. 
On the right foreground, a smaller figure stands on the path facing the cloaked one, 
seen from behind so the viewer shares this figure's perspective. 
Wide landscape opens around them: hills, distant mountains, scattered trees. 
Afternoon light, neutral atmosphere — neither welcoming nor hostile, 
simply the moment of unexpected meeting. 
Both figures small, integrated into the vast landscape. 
Cross-hatching emphasizes the depth between them and the world they share.
```

### 풀 프롬프트 (복붙용)

```
19th century book illustration, etching engraving style, 
Gustave Doré inspired, monochrome black ink on aged sepia parchment paper, 
fine cross-hatching, dramatic chiaroscuro, romantic sublime mood, 
wide landscape composition, human figures small relative to nature, 
figures shown from distance or back only, faces never visible, 
no text, no signature, no watermark.

Two figures meeting on an open road in rolling alpine countryside. 
On the left mid-distance, a cloaked figure has paused mid-walk and turned 
to face the other, body in profile, no face visible due to cloak hood. 
On the right foreground, a smaller figure stands on the path facing the cloaked one, 
seen from behind so the viewer shares this figure's perspective. 
Wide landscape opens around them: hills, distant mountains, scattered trees. 
Afternoon light, neutral atmosphere — neither welcoming nor hostile, 
simply the moment of unexpected meeting. 
Both figures small, integrated into the vast landscape. 
Cross-hatching emphasizes the depth between them and the world they share.

Negative: color, photorealistic, modern, anime, manga, cartoon, 
close-up faces, portrait, watermark, text, signature, letters, 
multiple panels, comic, frame, border, decorative.
```

### 구도 가이드

- 화면 중앙 약간 좌측: 차라투스트라 (멈춰선 자세, 측면, 망토 후드)
- 화면 우측 전경: 학습자 (뒷모습, 약간 더 작거나 비슷한 크기)
- 두 인물 사이 거리: 화면 폭의 약 1/3 (대화 가능한 거리)
- 화면 전체 70%: 풍경 (구릉, 멀리 산, 길)
- 길: 학습자 발 밑에서 시작해 차라투스트라를 지나 멀리 사라짐 (시각적 *계속*)
- 햇빛: 측면에서 비춤, 두 인물 모두 약간의 그림자

### 체크리스트

- [ ] 두 인물 *마주보는 구도* 명확
- [ ] 학습자 *뒷모습* (시청자 = 학습자 시점 공유)
- [ ] 차라투스트라 *측면* + 후드로 얼굴 가림
- [ ] 두 인물 사이의 *공간*(거리감) 살아있음
- [ ] 길이 *계속 이어짐* (앞으로의 동행 암시)
- [ ] 분위기 중립적 (드라마 X, 정적)
- [ ] 컬러 없음, 글자 없음
- [ ] 16:10 비율

---

## 화면 #6 — 동행 — 길 진행

### 컨셉
두 인물이 *나란히 또는 앞뒤로* 길을 걷는다. 동행의 시간. 풍경이 #5보다 약간 변화 — 시간이 흘렀다는 암시 (해의 위치, 그림자 길이, 풍경의 약간 다른 디테일). **이 화면은 5턴 인터랙션 동안 사용되는 메인 배경**이므로 *너무 특별한 순간이 아닌* 자연스러운 동행 장면이어야 한다.

### 분위기
- 시간대: 오후 → 저녁 전환
- 정서: 함께 걷는 자연스러운 시간, 대화 또는 침묵 모두 가능한 톤
- 인물 위치: 두 인물 *앞뒤* 또는 *나란히*, 길 위
- 인물 디테일: 둘 다 뒷모습 (시청자 = 따라가는 시점), 차라투스트라가 약간 앞 또는 옆

### 프롬프트 (위 공통 토큰 + 아래)

```
Two cloaked figures walking together along a winding country road, 
both seen from behind, mid-stride. 
The cloaked figure on the left walks slightly ahead, the other follows beside or just behind. 
The road winds through gentle hills toward distant mountains on the horizon. 
Long afternoon shadows stretch across the path. 
Sparse trees punctuate the landscape, a few clouds drift in the wide sky. 
Mood of quiet companionship, neither hurrying nor lingering, 
simply two travelers sharing a road. 
Detailed cross-hatching for the road's texture, soft hatching for sky and distant hills. 
The composition leads the viewer's eye along the path with the figures.
```

### 풀 프롬프트 (복붙용)

```
19th century book illustration, etching engraving style, 
Gustave Doré inspired, monochrome black ink on aged sepia parchment paper, 
fine cross-hatching, dramatic chiaroscuro, romantic sublime mood, 
wide landscape composition, human figures small relative to nature, 
figures shown from distance or back only, faces never visible, 
no text, no signature, no watermark.

Two cloaked figures walking together along a winding country road, 
both seen from behind, mid-stride. 
The cloaked figure on the left walks slightly ahead, the other follows beside or just behind. 
The road winds through gentle hills toward distant mountains on the horizon. 
Long afternoon shadows stretch across the path. 
Sparse trees punctuate the landscape, a few clouds drift in the wide sky. 
Mood of quiet companionship, neither hurrying nor lingering, 
simply two travelers sharing a road. 
Detailed cross-hatching for the road's texture, soft hatching for sky and distant hills. 
The composition leads the viewer's eye along the path with the figures.

Negative: color, photorealistic, modern, anime, manga, cartoon, 
close-up faces, portrait, watermark, text, signature, letters, 
multiple panels, comic, frame, border, decorative.
```

### 구도 가이드

- 화면 중앙 하단: 두 인물 (뒷모습), 길 위, 시청자 시점에서 *앞으로 걸어감*
- 길: 화면 하단에서 시작해 굽이지며 멀리 사라짐
- 화면 중앙~상단: 구릉, 멀리 산, 하늘
- 그림자: 길 위에 길게 (오후 시간 암시)
- 작은 디테일: 길가 풀, 작은 나무 — 풍경의 살아있음

### 체크리스트

- [ ] 두 인물 *함께 걷는* 자세 (속도·방향 일치)
- [ ] 둘 다 뒷모습
- [ ] 길이 *앞으로 펼쳐짐* (목적지 암시)
- [ ] 시간 흐름 표현 (그림자 길이, 빛 변화)
- [ ] 분위기 *조용한 동행*
- [ ] 인터랙션 동안 *주의 산만하지 않은* 톤 (너무 강한 디테일 X)
- [ ] 컬러 없음, 글자 없음
- [ ] 16:10 비율

> **개발 메모:** 이 화면은 5턴 인터랙션의 *기본 배경*. 매 턴마다 약간의 시간 흐름을 표현하고 싶다면 *#6의 변형 2~3장* 추가 생성 가능 (그림자 길이만 다른 버전, 구름 위치 다른 버전 등). 시간 부족하면 1장으로 충분.

---

## 화면 #7 — 종결 — 시장 원경

### 컨셉
멀리 시장이 보인다. 산골짜기의 작은 마을. 차라투스트라와 학습자가 *언덕 위*에 서서 마을을 내려다본다 — 또는 차라투스트라가 *먼저 내려가기 시작*하고 학습자는 멈춰 서 있다. 작별의 직전. 두 결의 융합이 *외부 결의 종착(시장 도착)*으로 마무리되는 순간.

### 분위기
- 시간대: 늦은 오후 → 황혼 직전
- 정서: 작별, 도착, 동행의 끝
- 인물 위치: 언덕 위 두 인물, 멀리 마을
- 인물 디테일: 차라투스트라는 *살짝 앞으로 나아간* 자세 (떠나는 자), 학습자는 *멈춤* (남는 자)

### 프롬프트 (위 공통 토큰 + 아래)

```
View from a hilltop overlooking a small medieval marketplace village 
nestled in a valley below. The village has clustered rooftops, 
a central square, narrow streets, surrounded by terraced fields. 
Two cloaked figures stand on the hilltop in the foreground: 
the one on the left has begun walking down the slope toward the village, 
turned slightly back as if in farewell; 
the other stands still, watching, seen from behind. 
Late afternoon light bathes the village, long shadows stretch from the hill. 
Smoke rises faintly from a few chimneys. 
Mood of arrival and parting simultaneously. 
Rich detail in the distant village, soft hatching for the foreground hill.
```

### 풀 프롬프트 (복붙용)

```
19th century book illustration, etching engraving style, 
Gustave Doré inspired, monochrome black ink on aged sepia parchment paper, 
fine cross-hatching, dramatic chiaroscuro, romantic sublime mood, 
wide landscape composition, human figures small relative to nature, 
figures shown from distance or back only, faces never visible, 
no text, no signature, no watermark.

View from a hilltop overlooking a small medieval marketplace village 
nestled in a valley below. The village has clustered rooftops, 
a central square, narrow streets, surrounded by terraced fields. 
Two cloaked figures stand on the hilltop in the foreground: 
the one on the left has begun walking down the slope toward the village, 
turned slightly back as if in farewell; 
the other stands still, watching, seen from behind. 
Late afternoon light bathes the village, long shadows stretch from the hill. 
Smoke rises faintly from a few chimneys. 
Mood of arrival and parting simultaneously. 
Rich detail in the distant village, soft hatching for the foreground hill.

Negative: color, photorealistic, modern, anime, manga, cartoon, 
close-up faces, portrait, watermark, text, signature, letters, 
multiple panels, comic, frame, border, decorative.
```

### 구도 가이드

- 화면 하단 30%: 언덕 위 — 두 인물의 위치
- 화면 중단~상단 70%: 골짜기 마을 + 풍경
- 마을: 화면 중앙, 디테일 풍부 (지붕, 광장, 길)
- 차라투스트라: 언덕 비탈을 *내려가기 시작한* 자세, 살짝 뒤를 돌아본 듯
- 학습자: *멈춰선* 자세, 화면 우측 또는 약간 뒤
- 빛: 마을에 황금빛 후광 (늦은 오후), 언덕은 그림자에 가까움

### 체크리스트

- [ ] 마을이 *멀리, 디테일 있게* 보임 (도착 시각화)
- [ ] 두 인물의 *분리* 시작 (한 명은 떠남, 한 명은 남음)
- [ ] 시간 흐름 (하루의 끝, 빛의 톤)
- [ ] 정서: *작별 + 도착*의 양가성
- [ ] 컬러 없음, 글자 없음
- [ ] 16:10 비율

---

## 화면 #8 — 엔딩 — 빈 길

### 컨셉
차라투스트라는 떠났고, 학습자도 떠났다. 길에 *아무도 없다*. 다만 길 위에 *발자국 두 줄*이 남아있다 — 한 줄은 마을 쪽으로, 다른 한 줄은 다른 방향으로. 동행의 *흔적*만이 남은 풍경. 

이 화면이 Ep 1의 마지막 정적. 학습자에게 *"이 만남은 끝났지만 흔적은 남는다"*는 메시지.

### 분위기
- 시간대: 황혼, 해 지기 직전
- 정서: 여운, 부재, 흔적, 고요
- 인물: **없음** — 풍경만
- 핵심 디테일: 빈 길 + 발자국 두 줄

### 프롬프트 (위 공통 토큰 + 아래)

```
An empty country road at dusk, no human figures visible. 
On the road, two sets of footprints can be seen in the dirt: 
one set heading toward a distant village on the right, 
another set heading off into open countryside on the left. 
The road forks gently in the foreground. 
Long shadows from sparse trees, the sky tinted with the last light of day. 
Empty landscape, vast and silent. 
Atmosphere of presence-in-absence — the figures are gone but their passage remains. 
Detailed hatching for the road's texture and the footprints, 
soft cross-hatching for the dimming sky.
```

### 풀 프롬프트 (복붙용)

```
19th century book illustration, etching engraving style, 
Gustave Doré inspired, monochrome black ink on aged sepia parchment paper, 
fine cross-hatching, dramatic chiaroscuro, romantic sublime mood, 
wide landscape composition, no human figures present, 
no text, no signature, no watermark.

An empty country road at dusk, no human figures visible. 
On the road, two sets of footprints can be seen in the dirt: 
one set heading toward a distant village on the right, 
another set heading off into open countryside on the left. 
The road forks gently in the foreground. 
Long shadows from sparse trees, the sky tinted with the last light of day. 
Empty landscape, vast and silent. 
Atmosphere of presence-in-absence — the figures are gone but their passage remains. 
Detailed hatching for the road's texture and the footprints, 
soft cross-hatching for the dimming sky.

Negative: color, photorealistic, modern, anime, manga, cartoon, 
human figures, people, person, walking figures, 
watermark, text, signature, letters, 
multiple panels, comic, frame, border, decorative.
```

> **주의:** 이 화면은 *인물 없음*. 공통 토큰의 *"figures shown from distance or back only"* 부분을 *"no human figures present"*로 바꿔야 한다. Negative에도 *"human figures, people"* 추가.

### 구도 가이드

- 화면 중앙: 빈 길 — 시청자 시점에서 *앞으로 펼쳐짐*
- 길의 분기: 화면 중앙 약간 멀리, Y자 또는 갈래길
- 발자국: 길 위, 두 줄, 각각 다른 방향으로 향함 (디테일 살아있게)
- 우측 멀리: 마을 실루엣 (어둑하게)
- 좌측 멀리: 열린 풍경 (학습자가 간 방향)
- 하늘: 화면 상단 50%, 황혼 톤 (밝은 회색~중간 회색 그라데이션)
- 사람: **없음**

### 체크리스트

- [ ] **인물 없음** (이 화면만 다름)
- [ ] 빈 길의 *고요함* 전달
- [ ] 발자국 *두 줄*이 명확히 보임 + 다른 방향
- [ ] 갈림길 또는 분기 구조
- [ ] 황혼의 톤 (하루의 끝)
- [ ] 컬러 없음, 글자 없음
- [ ] 16:10 비율

---

## 부록 A — 일관성 검증 절차

8장 다 생성 후 다음 항목 확인:

1. **톤 통일**: 모든 이미지의 종이 베이스 톤이 같은 세피아인지
2. **잉크 농도**: 가장 짙은 부분의 검은색이 모든 이미지에서 일관된지
3. **선 굵기**: 해칭 패턴의 선 굵기가 비슷한지
4. **인물 표현**: 모든 인물이 *작고 얼굴 없음* 원칙 지키는지
5. **공간감**: 풍경의 깊이감(원근)이 일관된 스타일인지

문제 발견 시: 해당 이미지만 *재생성* 또는 *후처리*로 톤 보정 (Lightroom/Photoshop 흑백 곡선).

---

## 부록 B — 라이선스 메모

- Midjourney 결과물: 유료 플랜 시 상업 이용 가능, 단 본 캡스톤은 학술 이용
- Nano Banana / Gemini Image: Google 정책 확인 필요
- DALL-E 3: 생성자에게 권리, 학술/개인 이용 OK
- SD: 모델별 라이선스 (대부분 OK)

발표 자료 / 시연 영상에서 이미지 출처 표기 권장:
> *"일러스트: [도구명]으로 생성, 도레 스타일 흑백 판화"*
