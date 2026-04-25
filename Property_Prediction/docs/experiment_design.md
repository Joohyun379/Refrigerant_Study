# 실험 설계 문서

**작성일**: 2026-04-07  
**목적**: 분자 구조 feature로부터 냉매 열역학 물성(Tc, Pc, ω) 예측 회귀 모델 실험

---

## 1. 문제 정의

### 타겟 변수 (3개)

| 변수 | 단위 | 범위 | 평균 ± 표준편차 | 비고 |
|------|------|------|----------------|------|
| `Tc_K` | K | 126 ~ 1000 | 551 ± 139 | log-transform 검토 필요 |
| `Pc_MPa` | MPa | 0.83 ~ 22.1 | 4.04 ± 1.64 | 비교적 선형 |
| `omega` | — | 0.00 ~ 1.48 | 0.37 ± 0.18 | 0 근처에서 MAPE 불안정 |

### 데이터셋

| 항목 | 값 |
|------|-----|
| 전체 유효 화합물 | 476개 |
| label=1 (냉매) | 96개 |
| label=0 (비냉매) | 380개 |
| Group 수 | 118개 |
| Feature 수 | 235개 (3D 제외 기준) |

---

## 2. Feature Set 정의

| ID | 이름 | 구성 | 차원 | 비고 |
|----|------|------|------|------|
| **FS1** | Tabular-Full | cat1(gc) + cat2(lg) + cat3(gt) + cat5(rf) + cat6(el) | 235 | 전체 engineered features |
| **FS2** | Tabular-Select | FS1 중 SHAP/importance 상위 N개 | ~40–60 | Phase 1 GBM 결과로 결정 |
| **FS3** | Tabular-Cat별 | 각 범주 단독 | 19–80 | Ablation 실험용 |
| **FS4** | Graph | cat2 그래프 데이터 (node/edge features) | — | GNN 전용, SMILES → PyG Data |
| **FS5** | Hybrid | FS4 + FS1 중 cat1, cat3, cat5, cat6 | — | GNN embedding + tabular |
| **FS6** | SMILES | Raw SMILES 문자열 | — | Pretrained transformer 전용 |

### 범주별 Feature 수 (FS1 기준)

| 접두사 | 범주 | 개수 |
|--------|------|------|
| `gc_` | Cat1 Group Contribution (Joback) | 45 |
| `lg_` | Cat2 Local Graph (원자/결합 통계) | 80 |
| `gt_` | Cat3 Global Topology | 47 |
| `rf_` | Cat5 Refrigerant-Specific | 44 |
| `el_` | Cat6 Electronic | 19 |
| | **합계** | **235** |

> Cat4 (3D Geometry)는 별도 실험으로 추가 가능. 현재 기본 feature set에서 제외.

---

## 3. 데이터 분할 전략

### Hold-out Test Set

- 전체의 **20%** (약 95개 화합물)를 group 단위로 고정
- Tc 구간(5개 구간)별 대표성 확보:

| 구간 | Tc 범위 | 의미 |
|------|--------|------|
| 1 | < 200 K | 극저온 기체 (He, H₂ 등) |
| 2 | 200 – 350 K | 냉매 핵심 구간 |
| 3 | 350 – 500 K | 중간 냉매·일부 반례 |
| 4 | 500 – 700 K | 고비점 반례 |
| 5 | > 700 K | 방향족 대분자 반례 |

### Cross-Validation

- **Group 5-Fold CV** (같은 group이 train/val에 동시에 포함되지 않도록 엄격 분리)
- Tc 구간 층화(Stratified)로 각 fold의 target 범위 균등화
- `label` 컬럼은 Tc 구간 층화의 보조 기준으로 활용

---

## 4. 실험 구성

### Phase 1: Single-output (전 모델)

**모든 모델**에 대해 타겟 3개(Tc, Pc, ω)를 **각각 독립적으로** 학습.  
각 모델은 **적용 가능한 모든 Feature Set**에 대해 실험하여 FS 간 성능을 비교한다.

#### Feature Set 적용 범위

| 계열 | 모델 ID | 모델명 | 적용 Feature Set | 출력 전략 |
|------|---------|--------|-----------------|----------|
| **Linear** | Ridge | Ridge Regression | FS1, FS2, FS3_gc, FS3_lg, FS3_gt, FS3_rf, FS3_el | 단독 3개 |
| | Lasso | Lasso Regression | FS1, FS2, FS3_gc, FS3_lg, FS3_gt, FS3_rf, FS3_el | 단독 3개 |
| | SVR-Lin | Linear SVR | FS1, FS2, FS3_gc, FS3_lg, FS3_gt, FS3_rf, FS3_el | 단독 3개 |
| **Kernel** | SVR-RBF | SVR (RBF kernel) | FS1, FS2, FS3_gc, FS3_lg, FS3_gt, FS3_rf, FS3_el | 단독 3개 |
| | GP | Gaussian Process Regressor | FS2, FS3_gc, FS3_lg, FS3_gt, FS3_rf, FS3_el | 단독 3개 |
| **Tree Ensemble** | RF | Random Forest | FS1, FS2, FS3_gc, FS3_lg, FS3_gt, FS3_rf, FS3_el | 단독 3개 |
| | XGB | XGBoost | FS1, FS2, FS3_gc, FS3_lg, FS3_gt, FS3_rf, FS3_el | 단독 3개 |
| | LGB | LightGBM | FS1, FS2, FS3_gc, FS3_lg, FS3_gt, FS3_rf, FS3_el | 단독 3개 |
| | CAT | CatBoost | FS1, FS2, FS3_gc, FS3_lg, FS3_gt, FS3_rf, FS3_el | 단독 3개 |
| **NN-Tabular** | MLP | Multi-layer Perceptron (sklearn) | FS1, FS2, FS3_gc, FS3_lg, FS3_gt, FS3_rf, FS3_el | 단독 3개 |
| | TabNet | TabNet | FS1, FS2, FS3_gc, FS3_lg, FS3_gt, FS3_rf, FS3_el | 단독 3개 |
| | FTT | FT-Transformer | FS1, FS2, FS3_gc, FS3_lg, FS3_gt, FS3_rf, FS3_el | 단독 3개 |
| **GNN** | GCN | Graph Convolutional Network | FS4 | 단독 3개 |
| | GAT | Graph Attention Network | FS4 | 단독 3개 |
| | GIN | Graph Isomorphism Network | FS4 | 단독 3개 |
| | AFP | AttentiveFP | FS4 | 단독 3개 |
| **Pretrained** | ChemBERTa | ChemBERTa-2 (fine-tuning) | FS6 | 단독 3개 |
| **Hybrid** | AFP+LGB | AttentiveFP embedding → LGB | FS5 | 단독 3개 |
| | AFP+MLP | AttentiveFP embedding → MLP | FS5 | 단독 3개 |

> **GP**: FS1(235차원) 제외 — 고차원 kernel 연산 비효율. FS2(50) 및 FS3_*(19~80)으로 적용.  
> **FS3_***: 범주별 단독 실험으로 어느 feature 범주가 가장 예측력이 높은지 판별 (ablation).  
> **TabNet**: 샘플별 feature importance 제공 → 냉매 유형별 핵심 feature 해석 가능.  
> **AttentiveFP**: 분자 property prediction 특화 GNN (Xiong et al., 2020, JACS).  
> **AFP+LGB**: GNN으로 분자 표현 추출 → GBM 입력. End-to-end가 아닌 2-stage.

---

### Phase 2: Multi-task (NN/GNN/Pretrained 계열)

Phase 1에서 **진짜 multi-task가 가능한 모델**에 한해 Tc/Pc/ω를 동시 예측.  
(GBM 계열은 내부적으로 독립 모델이므로 Phase 2 대상에서 제외)

| 모델 ID | 구조 | Feature Set | Loss 전략 |
|---------|------|------------|----------|
| MLP-MT | 공유 backbone → 3 출력 헤드 | FS1 | MT-B (정규화) |
| FTT-MT | 공유 transformer → 3 출력 헤드 | FS1 | MT-B |
| GCN-MT | 공유 GCN → 3 출력 헤드 | FS4 | MT-B |
| GAT-MT | 공유 GAT → 3 출력 헤드 | FS4 | MT-B |
| GIN-MT | 공유 GIN → 3 출력 헤드 | FS4 | MT-B |
| AFP-MT | 공유 AttentiveFP → 3 출력 헤드 | FS4 | MT-B |
| ChemBERTa-MT | 공유 transformer → 3 출력 헤드 | FS6 | MT-B |
| AFP+MLP-MT | 공유 GNN+MLP → 3 출력 헤드 | FS5 | MT-B |

#### Loss 가중치 전략 (Phase 2 기본: MT-B)

| ID | 전략 | 수식 | 비고 |
|----|------|------|------|
| MT-A | Naive sum | `L = L_Tc + L_Pc + L_ω` | 스케일 불균형 문제 |
| **MT-B** | **정규화 (기본)** | 각 타겟을 표준화 후 MSE 합산 | 구현 간단, 안정적 |
| MT-C | 수동 가중치 | `L = w1·L_Tc + w2·L_Pc + w3·L_ω` | Phase 2 우수 모델에 추가 실험 |
| MT-D | 불확실도 기반 | Kendall & Gal (2018) 자동 가중치 | Phase 2 우수 모델에 추가 실험 |

---

### Phase 3: Ablation (선택)

Phase 1/2 완료 후 최고 성능 모델(예: LGB, AFP-MT)에 한해 진행.

| 실험 | 목적 |
|------|------|
| Feature category별 단독 | 어느 범주가 가장 중요한가 |
| Tc log-transform 여부 | 로그 스케일이 RMSE를 낮추는가 |
| 3D Feature (Cat4) 추가 | 3D 정보가 실제로 도움이 되는가 |
| label 보조 분류 헤드 추가 | 냉매/비냉매 구분이 회귀 정확도를 높이는가 |
| 데이터 크기별 학습 곡선 | 데이터를 더 모으면 얼마나 개선되는가 |

---

## 5. 평가 지표

### 물성별 지표

각 타겟(Tc, Pc, ω)에 대해 아래 지표를 **CV fold 평균 ± 표준편차**로 보고.

| 지표 | 수식 | 비고 |
|------|------|------|
| **RMSE** | √(Σ(ŷ-y)²/n) | 주 지표. 단위 있음 |
| **MAE** | Σ\|ŷ-y\|/n | 이상값 덜 민감 |
| **MAPE** | Σ\|ŷ-y\|/\|y\|/n × 100 | % 단위, 직관적 비교 |
| **R²** | 1 - SS_res/SS_tot | 설명 분산 비율 |

> **ω 주의**: ω ≈ 0인 화합물(희귀 기체)에서 MAPE가 폭발 → SMAPE 또는 MAE를 병행 보고.

### 모델 간 종합 비교 지표

| 지표 | 수식 | 비고 |
|------|------|------|
| **Mean MAPE** | (MAPE_Tc + MAPE_Pc + MAPE_ω) / 3 | 3개 물성 통합 순위 |
| **Norm. RMSE** | RMSE / (target 범위) | 물성 간 스케일 제거 |

### Phase 1 vs Phase 2 비교 지표

| 지표 | 설명 |
|------|------|
| ΔMAPE | Phase2_MAPE − Phase1_MAPE (음수 = 개선) |
| ΔRMSE | Phase2_RMSE − Phase1_RMSE |

---

## 6. 출력 형식

### 6-1. CV 결과 (모델별)

```
results/cv_scores/{model_id}_{target}.json

{
  "model_id": "LGB",
  "target": "Tc_K",
  "feature_set": "FS1",
  "phase": 1,
  "cv_folds": 5,
  "rmse":  {"mean": 12.4, "std": 1.8},
  "mae":   {"mean":  8.1, "std": 1.2},
  "mape":  {"mean":  2.3, "std": 0.4},
  "r2":    {"mean":  0.98, "std": 0.01},
  "fold_scores": [
    {"fold": 0, "rmse": 11.2, "mae": 7.5, "mape": 2.1, "r2": 0.982},
    ...
  ],
  "train_time_sec": 4.2
}
```

### 6-2. Test Set 예측값

```
results/predictions/{model_id}_{target}_test.csv

identifier, y_true, y_pred, abs_error, pct_error
R-134a,     374.21,  372.1,      2.11,       0.56
...
```

### 6-3. 전체 비교 테이블

```
results/summary_phase1.csv   # Phase 1 전체 모델 비교
results/summary_phase2.csv   # Phase 2 multi-task 비교
results/summary_all.csv      # Phase 1+2 통합

컬럼:
model_id, phase, feature_set,
Tc_rmse, Tc_mae, Tc_mape, Tc_r2,
Pc_rmse, Pc_mae, Pc_mape, Pc_r2,
om_rmse, om_mae, om_mape, om_r2,
mean_mape, train_time_sec
```

### 6-4. Parity Plot (물성별)

```
results/plots/parity_{model_id}_{target}.png
  x축: 실제값 (y_true)
  y축: 예측값 (y_pred)
  색상: Tc 구간 or group 범주
  대각선: y=x (완벽한 예측)
```

### 6-5. 해석 결과

```
results/shap/{model_id}_{target}_shap_summary.png   # SHAP summary plot
results/shap/{model_id}_{target}_shap_values.csv    # 화합물별 SHAP 값
results/attention/{gnn_model_id}_attn_weights.csv   # GNN attention 가중치
```

---

## 7. 실험 디렉토리 구조

```
experiments/
├── configs/
│   ├── base.yaml              # 공통 설정 (seed, CV, 평가 지표)
│   ├── linear.yaml
│   ├── gbm.yaml
│   ├── nn_tabular.yaml
│   ├── gnn.yaml
│   └── hybrid.yaml
│
├── models/
│   ├── base.py                # 추상 기반 클래스
│   ├── linear.py              # Ridge, LASSO, SVR
│   ├── kernel.py              # SVR-RBF, GP
│   ├── gbm.py                 # RF, XGB, LGB, CatBoost
│   ├── nn_tabular.py          # MLP, TabNet, FT-Transformer
│   ├── gnn.py                 # GCN, GAT, GIN, AttentiveFP
│   ├── pretrained.py          # ChemBERTa-2
│   └── hybrid.py              # GNN embedding + GBM/MLP
│
├── training/
│   ├── cross_validation.py    # GroupStratifiedKFold
│   ├── trainer.py             # 학습 루프 (single / multi-task)
│   └── hyperopt.py            # Optuna 하이퍼파라미터 탐색
│
├── evaluation/
│   ├── metrics.py             # RMSE, MAE, MAPE, R²
│   ├── parity_plot.py         # Parity plot 생성
│   └── interpretability.py    # SHAP, attention 시각화
│
├── notebooks/
│   ├── 03_baseline.ipynb      # Linear, SVR, GP
│   ├── 04_gbm.ipynb           # RF, XGB, LGB, CatBoost
│   ├── 05_nn_tabular.ipynb    # MLP, TabNet, FT-Transformer
│   ├── 06_gnn.ipynb           # GCN, GAT, GIN, AttentiveFP
│   ├── 07_pretrained.ipynb    # ChemBERTa-2
│   ├── 08_hybrid.ipynb        # Hybrid 모델
│   ├── 09_multitask.ipynb     # Phase 2 multi-task 실험
│   └── 10_comparison.ipynb    # 전체 결과 비교 및 해석
│
└── results/
    ├── cv_scores/
    ├── predictions/
    ├── summary_phase1.csv
    ├── summary_phase2.csv
    ├── summary_all.csv
    ├── plots/
    └── shap/
```

---

## 8. 실험 진행 순서

```
Phase 1-A: 기준선 확립 (Linear, SVR, GP, RF)
  → 빠르게 CV 점수 확보
  → FS2 (상위 feature 선택) 기준 마련

Phase 1-B: GBM 튜닝 (XGB, LGB, CatBoost)
  → Optuna 하이퍼파라미터 탐색
  → SHAP으로 핵심 feature 확정 → FS2 확정

Phase 1-C: NN-Tabular (MLP, TabNet, FT-Transformer)

Phase 1-D: GNN (GCN, GAT, GIN, AttentiveFP)

Phase 1-E: Pretrained (ChemBERTa-2) + Hybrid

Phase 1 비교: summary_phase1.csv 작성, 모델별 parity plot

Phase 2: Multi-task (MLP-MT, AFP-MT 등)
  기본: MT-B (정규화 합산)
  우수 모델 한정: MT-C, MT-D 추가 실험

Phase 3 (선택): Ablation 실험
```

---

## 9. 주요 의존성 (예정)

| 라이브러리 | 용도 |
|-----------|------|
| `scikit-learn` | Linear, SVR, GP, RF, CV |
| `xgboost`, `lightgbm`, `catboost` | GBM 계열 |
| `torch`, `torch-geometric` | NN, GNN |
| `pytorch-tabnet` | TabNet |
| `transformers` | ChemBERTa-2 |
| `optuna` | 하이퍼파라미터 탐색 |
| `shap` | Feature 해석 |
| `deepchem` | AttentiveFP (대안: 직접 구현) |
