# Refrigerant Prediction

냉매 후보 물질의 열역학 물성(Tc, Pc, ω)과 분자구조(SMILES, InChI 등)를 수집하고,
머신러닝으로 물성을 예측하는 프로젝트.

---

## 실행 순서

```
1. python run0_data.py              # 데이터 수집 (PubChem / CoolProp / NIST)
2. python run1_features.py          # feature 추출 (분자구조 → 수치 벡터)
3. python run2_experiment_phase1.py # ML 학습 및 평가 (Phase 1)
```

---

## 실행 파일 설명

### `run0_data.py` — 데이터 수집

**어떨 때 사용하나?**

- 처음 데이터를 구축할 때
- `data_pipeline/compound_list.py`에 새 화합물을 추가했을 때
- PubChem 분자구조 데이터까지 새로 받아야 할 때

**주의:** PubChem API를 전체 화합물 수만큼 호출하므로 **30~40분** 소요됩니다.

```bash
python run0_data.py
```

**출력 파일:**

| 경로 | 내용 |
|------|------|
| `data/raw/refrigerants_raw.csv` | 검증 전 원본 데이터 |
| `data/processed/refrigerants_final.csv` | 검증 완료된 최종 데이터 |
| `data/raw/sdf/*.sdf` | 화합물별 2D 구조 파일 |

---

### `run0_patch_thermo.py` — 열역학 물성만 재적용

**어떨 때 사용하나?**

PubChem 분자구조는 그대로 두고, 열역학 물성(Tc/Pc/ω)만 다시 적용하고 싶을 때 사용합니다.
전체 파이프라인 대신 **1~2분** 안에 완료됩니다.

- `data_pipeline/manual_props.py`에 새 문헌값을 추가한 경우
- `nist_fetcher.py` 또는 `coolprop_fetcher.py`의 이름 매핑을 수정한 경우
- invalid 화합물의 thermo만 고치고 싶을 때

```bash
python run0_patch_thermo.py
```

**사용 예시 — invalid 화합물에 문헌값을 추가할 때:**

1. `data_pipeline/manual_props.py`에 값 추가:

```python
"CrownEther18c6": {"Tc_K": 780.0, "Pc_MPa": 1.800, "omega": 0.900},
```

2. patch 실행:

```bash
python run0_patch_thermo.py
```

실행 후 터미널에 여전히 invalid인 화합물 목록이 출력됩니다.

---

### `run1_features.py` — Feature 추출

**어떨 때 사용하나?**

- `run0_data.py` 실행 후 feature 벡터를 생성할 때
- feature 추출 코드(`features/`)를 수정한 후 재생성할 때

```bash
python run1_features.py            # 기본 (3D feature 제외, 캐시 활용)
python run1_features.py --force    # 캐시 무시하고 전체 재추출
python run1_features.py --include-3d               # Cat4 3D geometry 포함
python run1_features.py --identifier "R-134a"      # 특정 화합물만 (디버깅)
```

**출력 파일:**

| 경로 | 내용 |
|------|------|
| `data/processed/features_raw.csv` | 추출 직후 원본 (NaN 포함) |
| `data/processed/features_clean.csv` | NaN 처리 완료, ML 입력용 |

---

### `run2_experiment_phase1.py` — Phase 1 ML 실험

**어떨 때 사용하나?**

- `run1_features.py` 실행 후 ML 모델을 학습·평가할 때
- 새 모델이나 feature set을 추가한 후 재실험할 때

```bash
python run2_experiment_phase1.py                          # 전체 실행
python run2_experiment_phase1.py --models XGBoost,CatBoost  # 특정 모델만
python run2_experiment_phase1.py --targets Tc_K             # 특정 타겟만
python run2_experiment_phase1.py --skip-existing            # 기존 결과 건너뜀
python run2_experiment_phase1.py --no-test                  # hold-out 평가 생략
```

**출력 파일:**

| 경로 | 내용 |
|------|------|
| `results/cv_scores/phase1_cv_summary.csv` | 전체 모델 CV 성능 요약 |
| `results/cv_scores/phase1_test_summary.csv` | hold-out test 성능 요약 |
| `results/cv_scores/{model}_{fs}_{target}.json` | 모델별 상세 CV 결과 |
| `results/predictions/{model}_{fs}_{target}_oof.csv` | OOF 예측값 |
| `results/plots/` | Parity plot, RMSE 비교 그래프 |
| `results/shap/` | SHAP importance, FS2 feature 목록 |

---

## 데이터 파이프라인 구조

```
data_pipeline/compound_list.py    # 수집 대상 화합물 목록 (485개)
    │
    ├─ manual_smiles.py            # SMILES/InChIKey 수동 등록 (PubChem 오류 보정)
    │
    ├─ pubchem_fetcher.py          # PubChem → SMILES, InChI, MW 등 분자구조
    │
    └─ thermo fallback chain:
         CoolProp                  # 로컬, 빠름 (112개)
           └─ Manual               # 문헌값 직접 입력 (manual_props.py, 190개)
               └─ NIST             # WebBook HTML 파싱 (네트워크, 141개)
                   └─ NIST+Manual  # NIST 일부 누락 시 Manual로 보완 (42개)
```

thermo 출처는 `source_thermo` 컬럼에 기록됩니다: `CoolProp` / `Manual` / `NIST` / `NIST+Manual`

---

## 현재 데이터셋 현황

| 구분 | valid | 전체 |
|------|-------|------|
| 정례 (냉매 후보, label=1) | 96 | 97 |
| 반례 (비냉매, label=0) | 380 | 388 |
| **전체** | **476** | **485** |

> valid=False 9개 상세 내용: `docs/dataset_status.md` 참고

---

## 주의: 파이프라인 재실행 시 보존 사항

`run0_data.py` 재실행 시에도 아래 수동 수정사항은 자동으로 보존됩니다:

- **`data_pipeline/manual_smiles.py`**: PubChem 오류 화합물의 SMILES/InChIKey/InChI를 덮어씀
- **`INVALID_COMPOUNDS`**: 구조 미확인 화합물은 valid=False 강제 적용
- **`data_pipeline/compound_list.py`**: 중복 제거된 화합물은 재추가되지 않음

---

## 관련 문서

- [`docs/data_collection.md`](docs/data_collection.md) — 전체 데이터 수집 로직 상세 설명
- [`docs/dataset_status.md`](docs/dataset_status.md) — 데이터셋 현황 및 품질 이슈 이력
- [`docs/thermo_reliability.md`](docs/thermo_reliability.md) — 열역학 물성 소스별 신뢰도 분석
- [`docs/experiment_design.md`](docs/experiment_design.md) — ML 실험 설계 (모델, feature set, 평가 지표)
- [`docs/proxy_guide/`](docs/proxy_guide/) — API 연결 가이드 (PubChem, NIST)
