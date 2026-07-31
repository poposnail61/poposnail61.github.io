# 마스터 두 벌 — Thin 100 / Black 900

WEIGHT-AXIS.md에서 "규칙은 마스터별로 가져야 한다"고 결론 내렸다. 그 두 벌을 뽑았다.
중간 굵기는 선형 보간으로 얻는다.

| | 파일 |
|---|---|
| 색인 | [`studio-rules-masters.json`](./studio-rules-masters.json) |
| Thin 100 | [`studio-rules-layered-thin.json`](./studio-rules-layered-thin.json) · [`studio-rules-thin.json`](./studio-rules-thin.json) |
| Black 900 | [`studio-rules-layered-black.json`](./studio-rules-layered-black.json) · [`studio-rules-black.json`](./studio-rules-black.json) |
| 검증용 Regular 400 | [`studio-rules-layered-regular.json`](./studio-rules-layered-regular.json) |

레이어 구조(L1 토폴로지 템플릿 / L2 자모 패딩 / L3 컬럼 보정 / L4 음절 예외)는
[STUDIO-RULES.md](./STUDIO-RULES.md)와 같다. 여기서는 **두 마스터가 서로 얼마나
다른지**만 다룬다.

---

## 1. 두 마스터는 같은 셀을 쓴다

정규화 좌표 (0,0,1,1)이 대응하는 em 상자다.

```
셀  x 8 … 931,  y −121 … 852     923 × 973
```

마스터마다 잉크 봉투를 따로 재면 Thin은 860×941, Black은 923×973이 나온다.
**그러면 정규화 좌표가 마스터마다 다른 em 상자를 가리켜 보간이 어긋난다.** 두 봉투의
합집합 하나를 두 마스터에 공통으로 준다(`HFS_CELL`).

| | Thin 100 | Black 900 |
|---|---:|---:|
| 상자를 얻은 음절 | 10,843 (97.1%) | 10,707 (95.8%) |
| 관측 상자 | 35,339 | 31,534 |
| 덮인 (중성,종성) 컬럼 | 587 / 588 | 581 / 588 |
| L1 잔차 중앙 / p95 | 57.0 / 276.4 em | 55.0 / 254.0 em |
| L2 잔차 중앙 / p95 | 24.0 / 249.5 | 26.8 / 196.5 |
| **L3 잔차 중앙 / p95** | **8.5 / 40.0** | **7.5 / 40.0** |
| L3 파라미터 | 15,226 | 14,778 |

두 마스터의 적합도가 비슷하다(셀 높이의 0.8~0.9%). **Regular에서 세운 모델이 양 끝에서도
그대로 성립한다** — 굵기에 따라 값이 변할 뿐 구조는 안 변한다.

Black의 커버리지가 1.3%p 낮은 건 획이 굵어져 붙는 자리가 늘기 때문이다. 못 재는 음절이
329자 → 465자로 는다.

## 2. 무엇이 얼마나 움직이나

### L1 토폴로지 템플릿

12종 템플릿의 노드 값 중 |Black − Thin|이다.

| 필드 | 중앙 | 최대 |
|---|---:|---:|
| gap | 0.00 | 0.00 |
| **overlap** | **4.52** | **63.49** |
| spaceWeight | 0.02 | 0.23 |
| padding top / right / bottom / left | 0.00 | 17.87 / 24.92 / 24.88 / 9.37 |

**gap은 두 마스터 어디서도 0이다.** 한글 음절의 노드는 떨어지는 법이 없고 늘 맞닿거나
겹친다. 굵기 축에서 움직이는 것은 `overlap` 하나다.

1 이상 움직인 자리는 이렇다.

| 토폴로지 | 노드 | overlap Δ | spaceWeight Δ |
|---|---|---:|---:|
| M-none | LeadingMedialBase | **+63.49** | −0.00 |
| M-compound | LeadingMedialBase | −29.95 | 0.00 |
| M-simple | LeadingMedialBase | +24.90 | −0.01 |
| M-compound | Root | +16.07 | · |
| H-none | LeadingMedial | −13.14 | · |
| M-compound | LeadingMedial | +7.27 | −0.06 |
| VR-none | LeadingMedial | +6.41 | · |
| VR-simple | LeadingMedial | +6.16 | −0.01 |
| VL-none | LeadingMedial | +5.82 | · |
| M-simple | LeadingMedial | +5.79 | −0.01 |
| M-simple / H-compound / H-simple | Root | +5.02 / +4.66 / +4.51 | · |
| M-compound | Trailing | −5.36 | +0.06 |
| VL-compound / H-compound | LeadingMedial | −4.52 / −4.42 | −0.01 / −0.03 |

**섞임모임(M)이 압도적으로 크다.** 초성과 중성 기둥이 서로 파고드는 계열이라 굵기가
바뀌면 침투 깊이가 크게 달라진다. `M-none`의 `LeadingMedialBase` overlap이 63%p
움직이는 것이 그 극단이다.

### L2 자모 패딩

두 마스터에 다 있는 1,087개 항목의 |Black − Thin|(부모 사각형 대비 %p).

```
중앙 8.72   p90 22.81   최대 67.81
```

| 노드 | 항목 | 중앙 | p90 |
|---|---:|---:|---:|
| LeadingMedial | 139 | 3.82 | 6.83 |
| LeadingMedialBase | 59 | 6.80 | 36.70 |
| Leading | 313 | 5.73 | 22.62 |
| **Medial** | 224 | **15.80** | 24.14 |
| **MedialBase** | 89 | **18.62** | 31.06 |
| **MedialExtension** | 117 | **14.52** | 17.82 |
| Trailing | 98 | 4.76 | 20.24 |
| TrailingFirst | 24 | 6.58 | 17.64 |
| TrailingSecond | 24 | 8.92 | 37.43 |

**중성 계열이 초성·종성의 세 배로 움직인다.** WEIGHT-AXIS §1에서 본 "중성 폭이
178 → 280으로 57% 늘어난다"가 여기서 다시 나온다. 획이 굵어지면 세로기둥 하나가
차지하는 폭이 커지고, 그 몫을 초성이 내준다.

가장 많이 움직이는 항목 열둘.

| 노드 | 계열 | 키 | Δ |
|---|---|---|---:|
| Leading | H | ㅎ\|ㅗ | 67.81 |
| Medial | H | ㅗ\|ㅎ | 61.70 |
| MedialExtension | M | ㅞ\|ㅆ | 61.43 |
| MedialExtension | M | ㅞ\|ㅉ | 59.92 |
| LeadingMedialBase | M | ㅃ\|ㅟ | 58.74 |
| MedialExtension | M | ㅞ\|ㅅ | 57.81 |
| Medial | VL | ㅖ\|ㄴ | 57.22 |
| MedialExtension | M | ㅞ\|ㅈ | 56.95 |
| Leading | H | ㅎ\|ㅛ | 54.65 |
| Trailing | H | ㄼ | 52.78 |
| Medial | H | ㅛ\|ㅎ | 52.54 |
| Trailing | VL | ㄳ | 52.51 |

`ㅎ|ㅗ`(고, 호 계열의 초성 ㅎ)와 `ㅞ|ㅅㅆㅈㅉ`가 눈에 띈다. 둘 다 굵어지면서 획이
붙기 시작하는 자리라 관측 자체가 흔들린 몫이 섞여 있다. 규칙으로 못 박기 전에
FUSION.md의 처리를 먼저 정해야 한다.

## 3. 한쪽에서만 관측된 항목 — 메워야 한다

| | 개수 |
|---|---:|
| Thin에만 있는 L2 항목 | 106 |
| Black에만 있는 L2 항목 | 79 |

보간하려면 **양쪽 마스터에 값이 있어야 한다.** 한쪽에만 있는 항목은 다른 쪽에서
획이 붙어 못 잰 것이다. 없는 쪽은 상위 레이어 기본값(L1의 계열별 값)으로 메우면 된다.
빈 채로 두면 그 자모 변형체가 한쪽 마스터에서 정의되지 않는다.

## 4. 선형 보간이 중간을 맞히나

Thin·Black에서 wght 400을 예측해 **실측 Regular**와 견줬다(같은 셀로 다시 잰
`studio-rules-layered-regular.json`).

| | 패딩 %p |
|---|---:|
| 보간 오차 중앙 | **2.12** |
| p90 | 12.97 |
| 최대 | 42.64 |
| (참고) 두 마스터 사이 이동량 중앙 | 8.72 |
| (참고) 보간 없이 Thin을 그대로 썼을 때 | 3.81 |

**두 마스터 사이 8.72 만큼 움직이는 값을 2.12 오차로 맞힌다.** 이동량의 3/4를
선형으로 설명한다. WEIGHT-AXIS §6의 스칼라 수준 검증(중앙 3.2 em)과 같은 결론이다 —
**마스터는 100/900 둘이면 되고 `avar`도 필요 없다.**

남는 오차(p90 12.97)는 대부분 붙어서 못 재는 자리 근처의 관측 잡음이다. 정 신경
쓰이면 500 근처에 보정 source 하나를 두면 되지만, 규칙 모델 자체의 잔차(L3 8.5 em)보다
작으므로 안 둬도 무방하다.

## 5. 벌 구성과 합획

- **변형체(벌) 구성**은 두 마스터 모두에서 성립하는 것으로 쓴다.
  **초성 11벌 × 중성 2벌 × 종성 8벌** — WEIGHT-AXIS §7,
  [`variant-groups-stable.json`](./variant-groups-stable.json)
- **합획**은 컴포넌트를 겹친 채로 두고 윤곽선을 합치지 않는다. 그러면 두 마스터의
  컴포넌트 수·윤곽선 수가 같아 보간이 성립한다 — [FUSION.md](./FUSION.md)

## 재현

```bash
python3 build/masters.py /path/to/노토_디렉터리
# partial → 공통 셀 결정 → layers2 → emit2 → leaves → emit, 마스터마다
# 마지막에 studio-rules-masters.json

# 검증용 Regular (선택)
HFS_MASTER=regular HFS_CELL=8,-121,931,852 \
  python3 build/partial.py .../NotoSansCJKkr-Regular.otf &&
HFS_MASTER=regular HFS_CELL=8,-121,931,852 python3 build/layers2.py &&
HFS_MASTER=regular HFS_CELL=8,-121,931,852 python3 build/emit2.py &&
python3 build/masters.py --index-only
```
