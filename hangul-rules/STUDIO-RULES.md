# hangul-font-studio 적용 규칙

[`SPEC.md`](./SPEC.md)의 Noto Sans CJK KR 실측 결과를
[hangul-font-studio](https://github.com/poposnail61/hangul-font-studio)의
**재귀 이진 조합 + 가중치 패딩/갭** 모델로 변환한 것이다.

데이터: [`studio-rules.json`](./studio-rules.json)

---

> **이 문서의 수치는 Regular 하나로 잰 것이다.** 굵기에 따라 규칙이 크게
> 움직인다 — 중성 폭 +57%, 초성→종성 계수 2.2배, 종성 사다리 순위는 Thin 대비
> Black에서 3/27만 일치. 합획 조합도 9쌍이 뒤집힌다.
> [`WEIGHT-AXIS.md`](./WEIGHT-AXIS.md) 참고.
>
> **만드는 쪽은 마스터 두 벌을 쓴다.** 여기 설명한 구조 그대로 Thin(100)·Black(900)을
> 따로 뽑아 뒀다 — [MASTERS.md](./MASTERS.md),
> [`studio-rules-masters.json`](./studio-rules-masters.json). 중간 굵기는 선형 보간이다.
> 이 문서의 Regular 수치는 구조를 설명하기 위한 것으로 읽으면 된다.
>
> **합획**은 컴포넌트를 겹친 채로 두고 윤곽선을 합치지 않는다 — [FUSION.md](./FUSION.md).


## 0. 대상 모델

`crates/hangul-resolver/src/composition_tree.rs`의 `CompositionTree`와
`crates/project-model/src/v2.rs`의 `LayoutNodeValue`를 그대로 쓴다.

```
LayoutNodeValue {
  spaceWeight: Option<f64>,   // 형제 간 상대 가중치. 없으면 컴포넌트 intrinsic demand
  padding: { top, right, bottom, left },
  gap, overlap,
  intrusionBeforePercent, intrusionAfterPercent,
}
```

`crates/hangul-resolver/src/v2.rs`의 평가 순서를 읽어 확인한 의미:

| 필드 | 기준 | 비고 |
|---|---|---|
| `padding.*` | **노드 allocation 대비 %** | 좌우는 width, 상하는 height |
| `gap` / `overlap` | **패딩 적용 후 inner main 대비 %** | `separation = inner_main × (gap − overlap) / 100` |
| `spaceWeight` | 형제 합에 대한 비율 | `child_main = available × w / Σw` |

### `gap`과 `overlap`은 한 값의 두 쪽이다

이격량은 **부호가 있는 하나의 값 `gap − overlap`**이고, 이것을 음수를 안 쓰는 두 필드로
쪼개 놓은 것이다. 검증(`crates/validation/src/v2.rs`)이 강제하는 건 **각 필드가 개별적으로**
`0..=100`이라는 것뿐이다. 조합은 부호를 그대로 받는다:

```rust
let effective_extent = 100.0 - leading_padding - trailing_padding
    - (value.gap - value.overlap) * boundaries;
if effective_extent <= 0.0 { /* error */ }
```

`gap − overlap`이 음수면 이 항이 오히려 extent를 **늘리므로** 검사에 걸리지 않는다.
즉 **겹침에는 상한이 사실상 없다**(`overlap ≤ 100` 뿐).

둘을 동시에 0이 아니게 둘 수도 있지만 대수적으로 상쇄될 뿐이므로,
이 산출물은 **한쪽만 채운 정규형**으로 담았다(27개 노드 전부 해당).
읽을 때는 §4의 표를 `gap − overlap` 한 축으로 봐도 된다.

### 음수 금지가 실제로 문제되는 곳은 `padding`이다

`padding`은 짝이 되는 필드가 없다. 그래서 **"잉크가 자기 allocation 밖으로 나간다"를
표현할 수단이 없다.** §1의 프레임 결정이 필요한 이유가 이것이고, `gap`/`overlap`과는
성격이 다른 제약이다.

나머지 제약: 축별 패딩 합이 100 미만, 리프는 `gap = overlap = 0`,
`spaceWeight`는 유한하고 0보다 커야 한다, 한 split의 자식들은 `spaceWeight`를
**전부 지정하거나 전부 생략**해야 한다(`MixedLayoutSpaceWeight`).

세로 split은 `cursor = rect.y + rect.height`에서 시작해 내려가므로
**첫 자식이 위**, 가로 split은 **첫 자식이 왼쪽**이다. `composition_tree.rs`의
자식 순서와 그대로 맞는다.

## 1. 기준 프레임

정규화 `(0,0,1,1)`이 대응하는 em 박스를 먼저 고정해야 한다.
11,172자 전체의 잉크 봉투를 실측해 얻은 값:

```
cellEmBox = { x0: 27, y0: −107, x1: 895, y1: 842 }     // 868 × 949
```

**통합 시 결정할 것 하나.** `hangul-evaluator`의 `document_slot`은
`y = slot.y × unitsPerEm`으로 정규화 y=0을 베이스라인에 붙인다. 반면 한글 잉크는
베이스라인 아래로 내려간다(종성 하단 em −76, 봉투 하단 −107).

여기서 걸리는 건 **`padding`이 음수를 못 쓴다**는 점이다(§0). 루트 사각형이
`(0,0,1,1)`로 고정이고 패딩은 안쪽으로만 깎으므로, **어떤 노드의 사각형도 셀 밖으로
나갈 수 없다.** 두 가지 중 하나를 택해야 한다.

1. **셀 원점을 봉투 하단(em −107)에 맞춘다** — 모든 사각형이 셀 안에 들어오고
   아래 값이 그대로 맞는다. 대신 `document_slot`의 y 매핑에 오프셋이 하나 붙는다
2. **컴포넌트 소스 경로가 자기 사각형 아래로 내려가게 둔다** — 엔진은 사각형만
   배치하고 경로는 `width`/`height`로 스케일해 얹으므로 이것도 가능하다.
   대신 아래 값의 "리프 사각형 = 잉크 박스" 전제가 깨져 패딩을 다시 잡아야 한다

**1번을 권한다.** 규칙 값을 손대지 않아도 되고, 프레임 상수 하나로 끝난다.
어느 쪽이든 §2~§5의 비율 자체는 변하지 않는다.

## 2. 토폴로지 12종

트리 모양은 `(겹중성 여부, 중성 축, 받침 종류)`로 정해지고, 값은 여기에
**중성 계열**까지 곱해서 갈라진다. `studio-rules.json`의 `topologies` 키.

| id | 예 | 트리 | 표본 |
|---|---|---|---|
| `VR-none` / `VR-simple` / `VR-compound` | 가 / 각 / 갃 | `LeadingMedial(H)` | 95 / 1421 / 499 |
| `VL-none` / `VL-simple` / `VL-compound` | 거 / 걱 / 걳 | `LeadingMedial(H)` | 45 / 720 / 219 |
| `H-none` / `H-simple` / `H-compound` | 고 / 곡 / 곿 | `LeadingMedial(V)` | 67 / 685 / 159 |
| `M-none` / `M-simple` / `M-compound` | 과 / 관 / 괆 | `LeadingMedialBase(V)` + `MedialExtension(H)` | 93 / 460 / 122 |

`VR` = ㅏㅐㅑㅒㅣ, `VL` = ㅓㅔㅕㅖ, `H` = ㅗㅛㅜㅠㅡ, `M` = ㅘㅙㅚㅝㅞㅟㅢ.
`simple`/`compound`는 받침이 홑/겹인지다.

**`VR`과 `VL`은 트리가 같지만 값이 정반대라 반드시 분리해야 한다** — §4 참고.

### 예: `괆` (`M-compound`)

```
Root(V)  gap 5.09   pad t1.69 r6.34 b3.48 l2.53
├ LeadingMedial(H)      w 0.583  gap 6.09
│ ├ LeadingMedialBase(V) w 0.730  overlap 10.83   pad t8.08 b4.22
│ │ ├ Leading(ㄱ)         w 0.624  pad r5.95 l4.90
│ │ └ MedialBase(ㅗ)      w 0.376
│ └ MedialExtension(ㅏ)  w 0.270
└ Trailing(H)           w 0.417  gap 3.47   pad l12.42
  ├ TrailingFirst(ㄹ)    w 0.508
  └ TrailingSecond(ㅁ)   w 0.492
```

`spaceWeight`는 형제 합이 1이 되게 정규화했다. 엔진은 비율만 쓰므로 그대로 넣으면 된다.

## 3. 규칙 요약 — 어느 필드가 무엇을 담당하는가

| SPEC의 규칙 | studio 필드 |
|---|---|
| R3 종성 고유 높이 사다리 | `Trailing.spaceWeight` (종성별 보정표) |
| R4 중성 세로획 수 → 초성 폭 | `Medial.spaceWeight` (중성별 보정표) |
| R5 좌향 중성 맞물림 | `LeadingMedial.overlap` |
| R6 초성 세로 점유 → 종성 압축 | `Leading.spaceWeight` (초성별 보정표) |
| R7 ① 초성↔중성 접촉 | `LeadingMedialBase.overlap` (M), `LeadingMedial.overlap` (H) |
| R7 ② 중성↔종성 접촉 | `Root.overlap` (ㅜ·ㅠ 계열) |

## 4. `overlap`이 계열을 갈라놓는다

`LeadingMedial` 노드의 실측값. 트리는 똑같은데 값이 반대다.
`gap`과 `overlap`은 한 값의 두 쪽이므로(§0) 맨 오른쪽의 `gap − overlap` 한 열로 읽으면 된다.

| 토폴로지 | axis | `gap` | `overlap` | `gap − overlap` | `Leading.w` | `Medial.w` |
|---|---|---:|---:|---:|---:|---:|
| `VR-simple` (각) | H | 9.98 | 0 | **+9.98** | 0.686 | 0.314 |
| `VL-simple` (걱) | H | 0 | 3.10 | **−3.10** | 0.621 | 0.379 |
| `H-simple` (곡) | V | 10.60 | 0 | **+10.60** | 0.680 | 0.320 |
| `M-simple` (관) | H | 5.98 | 0 | **+5.98** | — | — |
| `M-simple` → `LeadingMedialBase` | V | 0 | 8.81 | **−8.81** | 0.624 | 0.376 |

- **`VR`은 갭, `VL`은 오버랩.** ㅓ계열의 가로획이 초성 칼럼을 파고들기 때문이다
  (SPEC R5: 회귀 기울기 0.69~0.74, r = 0.90~0.94, 1,064자 중 240자에서 획이 실제로 붙음)
- **`M`의 `LeadingMedialBase`는 오버랩 8.81.** 초성과 ㅗ가 세로로 서로 파고든다
  (SPEC R7 ①)
- `H`는 갭 10.60으로 나오지만 **표본 편향이다.** 가로모임은 46%만 분해돼 접촉하지 않는
  조합에 치우쳐 있다. 실제로는 ㅗ·ㅛ + 밑변이 평평한 초성에서 거의 항상 붙으므로
  `overlap`을 써야 한다. 조합별 접촉 자수는 `rules.json`의 `contactCho`/`contactJong`에 있다

## 5. 컨텍스트 보정표

`studio-rules.json`의 `contextTables`. 키는 `"계열|자모"`(예: `"VR|ㄼ"`)로,
계열마다 축이 달라 값을 섞으면 안 되기 때문에 나눠 두었다.

| 표 | 키 | 항목 수 |
|---|---|---|
| `Trailing.spaceWeight` | 계열\|종성 | 87 |
| `Root.gap` | 계열\|종성 | 87 |
| `Leading.spaceWeight` | 계열\|초성 | 76 |
| `Medial.spaceWeight` | 계열\|중성 | 14 |
| `MedialExtension.spaceWeight` | 계열\|중성 | 7 |
| `*.padding.{top,right,bottom,left}` | 같은 키 | — |

### 종성 사다리를 가중치로 (`VR` 계열)

```
ㄴ 0.298  ㅅ 0.363  ㄱ 0.371  ㄷ 0.374  ㅇ 0.377  ㅁ 0.378  ㅍ 0.385  ㅈ 0.386
ㅋ 0.386  ㄲ 0.391  ㅆ 0.399  ㄳ 0.403  ㅂ 0.416  ㅄ 0.425  ㅌ 0.437  ㅊ 0.438
ㄿ 0.441  ㄻ 0.444  ㄼ 0.444  ㄾ 0.444  ㄹ 0.445  ㅎ 0.463
```

Root의 V split에서 `Trailing`이 가져가는 비율이다. ㄴ 0.298 → ㅎ 0.463으로
**1.55배** 차이 난다. `LeadingMedial.spaceWeight = 1 − 이 값`.

### 초성 등급을 가중치로 (`낣` vs `랇`의 근거)

`LeadingMedial`의 H split에서 `Leading`이 가져가는 비율:

```
ㅃ 0.724  ㄴ 0.694  ㅎ 0.689  ㅇ 0.686  ㅊ 0.685  ㅉ 0.675  ㅆ 0.674  ㅂ 0.660
ㅁ 0.658  ㄹ 0.641  ㅋ 0.640  ㅌ 0.640  ㅍ 0.638  ㅅ 0.630  ㄸ 0.627  ㅈ 0.624
ㄲ 0.621  ㄷ 0.586  ㄱ 0.583
```

## 6. 충실도 — 어디까지 재현되는가

리프 박스의 최대 코너 편차를 em(셀 868 × 949)으로 측정했다.
`studio-rules.json`의 `fidelity`.

| 모드 | 중앙값 | p95 | 최대 |
|---|---:|---:|---:|
| `exact` (음절별 역산값 되돌리기) | **0.00** | 0.00 | 432 |
| `topologyMedianOnly` (기본 템플릿만) | 57.04 | 173.8 | 435 |
| `withContextTables` (보정표 적용) | **43.43** | 124.2 | 435 |

- `exact`는 **알고리즘 재현이 맞는지** 확인하는 용도다. 15,129개 리프 중 98.35%가
  오차 1em 이내로 되돌아왔다. 실패한 1.65%(250개)는 전부 섞임모임에서 초성과 ㅗ가
  크게 겹쳐 `union = a + gap + b` 항등식이 깨지는 경우다
- 실제 적용 충실도는 `withContextTables`를 봐야 한다. **43 em은 셀 높이의 4.6%**다
- **완전 일치는 원리적으로 불가능하다.** Noto는 11,172자를 개별 최적화한 폰트여서
  (SPEC §0) 규칙 하나로 환원되지 않는다. 이 값들은 **템플릿 초기값**으로 쓰고
  나머지는 `CorrectionRule`로 잡는 것이 맞는 사용법이다

## 7. 적용 순서 제안

1. `cellEmBox`로 프레임을 정하고 §1의 결정 사항을 확정한다
2. 토폴로지 12종에 `topologies[*].nodes`를 `LayoutNodeValue` 기본값으로 넣는다
3. `spaceWeight`를 지정할지 결정한다 — 지정하면 이 표대로 고정되고, 생략하면 컴포넌트의
   `LayoutDemand { widthWeight, heightWeight }`가 쓰인다. **후자가 더 이 앱답다**:
   §5의 보정표를 자모 컴포넌트의 demand로 넣으면 종성 사다리가 자동으로 반영된다
   (단 한 split의 자식은 전부 지정하거나 전부 생략해야 한다)
4. `VL`·`M`의 `overlap`을 반드시 넣는다. 빠지면 ㅓ계열 가로획이 허공에 뜨고
   섞임모임이 위아래로 벌어진다
5. 가로모임 접촉은 `rules.json`의 `contactCho`/`contactJong`를 보고 조합별로 판단한다
6. 남는 편차는 `CorrectionRule`의 `NodeDelta`(x/y)와 `SlotRectDelta`로 잡는다

## 8. 제품 명세(Notion)와의 접점

제품 명세 「한글 폰트 제작 프로그램」(기준일 2026-07-16)을 기준으로 확인한 것.

### 두 개의 진입점이 있다

명세 §8.2의 `Slot { rect: MasterVariable<NormalizedRect>, ... }`은 초·중·종성
**3슬롯 평면 모델**이고, `v2.rs`의 `LayoutNode` 그래프는 **재귀 이진 트리 모델**이다.
둘 다 쓸 수 있게 산출물을 나눠 두었다.

| 넣을 곳 | 쓸 파일 |
|---|---|
| §8.2 `Slot.rect` (평면 3슬롯) | [`rules.json`](./rules.json)의 `zones` — [SPEC.md §2](./SPEC.md) |
| `LayoutNodeValue` (이진 트리) | [`studio-rules.json`](./studio-rules.json) — 이 문서 |

`Slot.rect`도 0–1 정규화 좌표라 §1의 `cellEmBox`만 맞추면 바로 들어간다.

### §8.1 "여섯 유형"은 여덟이어야 한다

> 세로 중성, 가로 중성, 복합 중성, 종성 유무의 여섯 유형은 starter preset이다.
> 여섯 유형을 코드에 고정하지 않는다.

실측 결과 **세로 중성이 둘로 갈라진다**(SPEC.md R1). ㅏ계열은 갭, ㅓ계열은 오버랩으로
값이 정반대라(§4) 한 group으로 묶으면 ㅓ계열에서 가로획이 허공에 뜨거나 초성을 뚫는다.
starter preset을 **여덟 유형**으로 두는 것을 권한다:

```
VR-무받침  VR-받침   (ㅏㅐㅑㅒㅣ)
VL-무받침  VL-받침   (ㅓㅔㅕㅖ)
H-무받침   H-받침    (ㅗㅛㅜㅠㅡ)
M-무받침   M-받침    (ㅘㅙㅚㅝㅞㅟㅢ)
```

중성 21자를 남김 없이 4계열로 나누므로 §8.1의 "11,172자 전체에 정확히 하나의 group이
매칭" 조건을 만족한다. predicate가 선언적이라 코드 변경 없이 들어간다.

### §7.1 variant 태그에 대응

명세의 `ㄱ.initial.before-horizontal` 같은 문맥 variant 구분에 그대로 쓸 수 있는 근거가
`rules.json`에 있다.

- `contactCho` — 초성이 중성 기둥과 닿는 조합. ㅗ·ㅛ 앞에서 ㄴㄷㄹㅁㅂㅇㅌㅍ는 28자 중
  27~28자가 닿고 ㄱㄲㅅㅆㅉㅎ는 0~1자다. **`before-horizontal` variant가 실제로 필요한
  초성이 어느 것인지 이 표로 정해진다**
- `choGrade` — 초성 19자의 세로 점유 등급. variant를 몇 벌 둘지 판단할 때 쓸 수 있다

### §9.1 규칙 계층 배치 제안

명세의 적용 순서 `Template → Jamo → Jamo Correction → Combination Correction →
Exact Glyph → Direct Override`에 §5 보정표를 넣을 위치:

| 보정표 | 계층 | 근거 |
|---|---|---|
| `Trailing.spaceWeight` (종성별) | `combination` | 종성 정체성이 조건이다 |
| `Medial.spaceWeight` (중성별) | `combination` | |
| `Leading.spaceWeight` (초성별) | `combination` | |
| `*.padding.*` | `combination` | |

§16.1이 **같은 priority에서 같은 property를 건드리면 Error**로 막으므로, 위 넷은
서로 다른 property를 건드리게 두거나 priority를 달리 줘야 한다. 종성·중성·초성 표가
같은 split의 형제 가중치를 동시에 바꾸려 하면 충돌한다 — §7의 3번처럼
**`spaceWeight`를 비우고 컴포넌트 `LayoutDemand`로 옮기면 이 충돌이 원천적으로 없다.**

### 참고: 명세 §15.1과 이 작업의 성격

> 사용자가 디자인을 수정한 뒤 Noto 원본과 IoU가 낮아지는 것은 오류가 아니다.

이 규칙표도 같은 성격이다. **Noto를 닮게 만드는 목표값이 아니라 조합 규칙의 초기값**이다.
§6의 충실도 43 em은 "Noto 재현 실패"가 아니라 "규칙 하나로 환원되지 않는 폰트를
규칙으로 근사한 거리"로 읽어야 한다.

## 9. 한계

- **`VL`·`M`의 초성/중성 경계는 실측이 아니라 재구성이다.** Noto에서 이 둘은 크기가
  서로 연동돼 아웃라인만으로 분리되지 않는다. ㅔ·ㅖ는 'ㅓ 가로획+기둥'과 'ㅣ'가 별개
  도형인데 가로획 쪽이 초성 폭에 종속돼 초성축 불변량 판정에서 탈락한다.
  studio 트리가 ㅔ를 단일 `Medial` 리프로 보므로 오른쪽 40% 안에 있고 상단이 중성과
  같은 높이인 도형만 되돌려 합쳤다(`build/leaves.py`의 `reunite_medial`).
  초성 ㅊ·ㅎ처럼 위로 솟은 획을 잘못 가져가지 않도록 조건을 걸었지만, 이 경계는
  **판단이 들어간 값이다**
- **섞임모임의 `MedialBase`도 재구성이다.** ㅗ·ㅜ·ㅡ가 항상 단일 윤곽선이고 좌상
  블록에서 가장 아래·가장 넓다는 성질로 되찾았다(`pull_base`)
- **가로모임 표본 편향** — 46%만 분해돼 접촉하지 않는 조합에 치우쳐 있다
- 리프 단위까지 확보한 것은 **4,585자**다. 겹중성·겹종성을 쪼개야 하므로
  `SPEC.md`의 8,510자보다 적다
- `H-none`(67자), `VL-none`(45자), `M-none`(93자), `M-compound`(122자)는 표본이 적다

> **§10의 수치는 in-sample이다.** 홀드아웃을 붙여 구조를 다시 비교한 결과와
> 권장 벌 구성은 [`MODEL-SEARCH.md`](./MODEL-SEARCH.md)에 있다. 결론이 두 군데
> 바뀐다 — 받침별 초성 분리는 불필요하고, `낣`/`랇`의 초성→종성 압축은 규칙화하면
> 오히려 나빠진다.

## 10. 레이아웃/패딩 단위를 어디서 끊을지 — 실측 비교

"가~하는 레이아웃을 공유하고 ㄱ~ㅎ은 패딩만 다르게" 하는 구조를 포함해 여러 조합의
재현 오차를 실측했다. 데이터: [`studio-rules-layered.json`](./studio-rules-layered.json)

### 먼저 후보 비교

| 구조 | 레이아웃 | 패딩 | 파라미터 | 중앙값 | p95 |
|---|---:|---:|---:|---:|---:|
| 토폴로지 12 / 패딩 계열별 | 12 | 21 | 192 | 55.0 | 197.3 |
| 토폴로지 12 / **패딩 자모별** | 12 | 222 | **996** | **26.0** | 166.0 |
| 계열×종성 / 패딩 자모별 | 95 | 222 | 1,743 | 19.6 | 128.6 |
| **중성×종성 / 패딩 계열별** ← 제안하신 구조 | 371 | 21 | 3,423 | 20.6 | 140.3 |
| 중성×종성 / 패딩 자모별 | 371 | 222 | 4,227 | 12.0 | 127.6 |

**패딩을 자모별로 주는 쪽이 레이아웃을 쪼개는 쪽보다 훨씬 싸다.** 토폴로지 12개 +
자모 패딩은 996 파라미터로 26.0을 낸다. 제안하신 구조(컬럼 371개 + 초성 패딩)는
3,423 파라미터로 20.6이다. **파라미터를 3.4배 써서 오차 21%를 얻는 셈이다.**

자모별 패딩이 결정적인 이유는, 초성만 크기가 다른 게 아니라 **중성·종성도 자기 고유
크기를 갖기 때문**이다(SPEC R3의 종성 사다리 ㄴ 266 ~ ㅎ 420). 초성에만 패딩을 주면
그 몫을 레이아웃이 떠안아야 해서 컬럼을 588개로 쪼개게 된다.

### 권하는 구조: 4레이어 중첩

컬럼 레이아웃을 템플릿이 아니라 **가산 보정**으로 옮긴다. 명세 §9.1의 규칙 계층과
그대로 맞는다.

| 레이어 | 대응 | 단위 | 파라미터 | 중앙값 | p95 | 셀 대비 |
|---|---|---|---:|---:|---:|---:|
| **L1** split 값·슬롯 | `CompositionTemplate` | 토폴로지 12 | 698 | 62.7 | 225.1 | 6.61% |
| **L2** 자모 패딩 | `JamoVariant` 기본값 | 1,216 키 | 5,458 | 25.0 | 193.0 | 2.63% |
| **L3** 컬럼 보정 | `CorrectionRule` `combination` | (중성,종성) 585 | 14,270 | **7.0** | **36.4** | **0.74%** |
| **L4** 음절 보정 | exact glyph rule | 필요할 때만 | 127,266 | 0.0 | 0.0 | 0.00% |

L3까지 쓰면 **관측 상자의 최대 코너 편차 중앙값 7.0 em**(셀 높이 949의 0.74%)이다.
L3는 L2 위에 **가산되는 패딩 delta**라 컬럼별 템플릿이 필요 없다
(엔진에는 `SlotRectDelta`로 넣는다).

### L2 패딩 키에 상대 자모를 넣는다

자모 패딩을 자모 하나로만 키잉하면 p95가 195까지 벌어진다. **초성 키에 중성을,
중성 키에 초성을 넣으면** 중앙값 7.6 → 7.0, p95 45 → 36.4, `Leading` 잔차
12.0 → 8.1로 떨어진다. 키 262개를 더 쓰는 값이다.

- **초성 × 중성** — 전통 벌식의 문맥 변형체와 같은 개념이다. 초성 ㄱ이 ㅏ 앞과 ㅗ 앞에서
  다른 꼴인 것
- **중성 × 초성** — SPEC R5. ㅓ계열 가로획과 가로·섞임모임의 기둥이 초성과 상호
  침투하므로 중성 상자가 초성에 따라 달라진다
- 종성은 계열만으로 충분했다 (추가해도 개선 없음)

명세 §7.1의 `JamoVariant` 문맥 태그(`ㄱ.initial.before-horizontal`)에 그대로 대응한다.

### 커버리지 — 리프까지 못 가면 그룹 노드로 남긴다

획이 붙어 분리가 안 되는 자리에서 음절 전체를 버리지 않고, **측정 가능한 가장 깊은
노드까지만** 내려간다(`build/partial.py`). 붙은 자리는 그룹 노드가 terminal로 관측된다.

| | 이전 | 지금 |
|---|---:|---:|
| 음절 | 4,585 / 11,172 (41.0%) | **10,842 / 11,172 (97.0%)** |
| 컬럼 | 371 / 588 | **585 / 588** |
| 관측 상자 | 15,129 | **31,668** |

노드별 관측 수와 L3 잔차:

| 노드 | 관측 | L3 중앙값 (em) |
|---|---:|---:|
| `LeadingMedial` | 2,830 | 6.2 | 6.2 |
| `LeadingMedialBase` | 2,051 | 6.4 | 6.4 |
| `Leading` | 5,961 | 8.1 | 8.1 |
| `Medial` | 5,121 | 6.9 | 6.9 |
| `MedialBase` | 840 | 7.0 | 7.0 |
| `MedialExtension` | 2,891 | 4.3 | 4.3 |
| `Trailing` | 8,880 | 8.5 | 8.5 |
| `TrailingFirst` | 1,547 | 5.0 | 5.0 |
| `TrailingSecond` | 1,547 | 6.0 | 6.0 |

`LeadingMedial`·`LeadingMedialBase`가 관측되는 음절은 그 자리에서 초성과 중성이
붙어 있다는 뜻이다 — 규칙표로는 그룹까지만 정하고 내부는 L2 기본값에 맡긴다.

### 아직 못 채운 330자

전혀 측정되지 않는 음절이 330자(3.0%) 남는다. 초성 **ㄱ·ㄲ·ㅋ**(168자)이
**ㅜ·ㅠ**와 만나 초성·중성·종성이 한 윤곽선으로 완전히 융합되는 경우와,
**ㅓ·ㅕ**에서 초성과 가로획이 붙는 경우다(`구`, `국`, `굴`, `겨`, `견` 등).
윤곽선만으로는 어떤 방법으로도 분리되지 않는다. 이 조합은 §7의 합자 글리프 경로로
가거나, 손으로 슬롯을 지정해야 한다.

## 재현

```bash
pip install fonttools
cd build
python3 measure.py  /path/to/NotoSansCJKkr-Regular.otf   # rules.json  (SPEC.md용)
python3 leaves.py   /path/to/NotoSansCJKkr-Regular.otf   # 리프 단위 잉크 박스
python3 emit.py                                          # studio-rules.json
python3 verify.py                                        # 왕복 검증 + fidelity 기록
python3 grid.py                                          # 레이아웃/패딩 단위 비교 (§10)
python3 layers.py                                        # 4레이어 적합 + studio-rules-layered.json
```

마스터 두 벌은 한 번에 뽑는다. 파이프라인이 두 마스터에 공통 셀을 물려 주므로
따로 돌리지 말 것 (MASTERS.md §1).

```bash
python3 build/masters.py /path/to/노토_디렉터리   # studio-rules-*-{thin,black}.json + 색인
python3 build/fuse.py    /path/to/노토_디렉터리   # 합획 결정표 + fuse-pairs.json
```

`tree.py`는 `composition_tree.rs`를 이식한 것이다. studio 쪽 트리 구성이 바뀌면
여기도 같이 고쳐야 한다.
