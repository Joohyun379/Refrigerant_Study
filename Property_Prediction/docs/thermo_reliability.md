# 열역학 물성 신뢰도 분석

Tc (임계온도), Pc (임계압력), ω (이심인자) 각 수집 소스의 신뢰도와 ML 적용 시 고려사항을 정리합니다.

---

## 1. 소스별 신뢰도 요약

| 소스 | 화합물 수 | 신뢰도 | 자기 일관성 | 주요 근거 |
|------|----------|--------|------------|----------|
| CoolProp | 112 | ★★★★★ | 완전 | 다중매개변수 Helmholtz EOS |
| NIST (파싱) | 141 | ★★★★☆ | 완전 | 동일 페이지에서 Tc/Pc/Psat 수집 |
| Manual – ASHRAE | ~80 | ★★★★☆ | 높음 | 냉매 전용 EOS, REFPROP 기반 |
| Manual – Poling | ~90 | ★★★☆☆ | 중간 | 실험값 컴파일, 일부 추산값 혼재 |
| Manual – CRC | ~20 | ★★★☆☆ | 중간 | 일반 화학 컴파일, 이질적 출처 |
| NIST+Manual | 42 | ★★★☆☆ | 불완전 가능 | NIST와 문헌값 혼합 |

---

## 2. 소스별 상세 특성

### 2-1. CoolProp (신뢰도 최상)

**데이터 성격**: CoolProp 라이브러리에 내장된 다중매개변수 Helmholtz 에너지 방정식(HEOS)으로부터 직접 계산.

```python
state = CoolProp.AbstractState("HEOS", cp_name)
Tc    = CP.PropsSI("Tcrit", cp_name)
Pc    = CP.PropsSI("Pcrit", cp_name) / 1e6
omega = state.acentric_factor()
```

**장점:**
- Tc, Pc, ω가 동일한 EOS에서 파생 → **완전한 자기 일관성**
- 많은 냉매의 경우 NIST, ASHRAE 실험 데이터를 기반으로 수십~수백 개 실험점에 피팅된 EOS
- 주요 냉매(R-134a, R-410A 성분, R-1234yf 등)는 REFPROP 수준의 정확도

**한계:**
- 수록 화합물이 약 120종으로 제한적 (주로 상업 냉매, 탄화수소, 주요 유기용매)
- 비표준 화합물이나 신규 HFO 일부는 미수록

**전형적 불확실도**: Tc ±0.1~1 K, Pc ±0.01~0.05 MPa, ω ±0.002~0.005

---

### 2-2. NIST WebBook HTML 파싱 (신뢰도 높음)

**데이터 성격**: NIST WebBook의 Phase Change Data 페이지에서 Tc, Pc를 파싱하고, 동일 NIST 데이터에서 Psat(Tr=0.7)를 구해 ω를 직접 계산.

```
ω = -log₁₀(Psat / Pc) - 1   at T = 0.7 × Tc
```

Psat 계산 경로:
1. `fluid.cgi` API (NIST 유체 DB 수록 화합물)
2. Antoine 방정식 fallback (Phase Change 페이지 내 테이블)

**장점:**
- Tc, Pc, Psat(→ω) 모두 동일 NIST 페이지 기원 → **자기 일관성 유지**
- NIST는 여러 문헌의 weighted average를 제공 (참고문헌 수가 많을수록 신뢰도 ↑)

**한계:**
- 참고문헌 수가 적은 화합물은 불확실도가 매우 큼
  - 예: R-1113 (CTFE) → NIST Pc = 260 ± 200 bar (실제값 40.7 bar)
  - 이 문제 때문에 파이프라인에서 NIST보다 Manual을 우선 적용
- Antoine 방정식으로 외삽할 경우 유효 범위 밖에서 오차 커짐
- HTML 파싱 특성상 페이지 구조 변경 시 파싱 실패 가능

**전형적 불확실도 (참고문헌 ≥5)**: Tc ±1~3 K, Pc ±0.05~0.2 MPa, ω ±0.005~0.02
**전형적 불확실도 (참고문헌 <5)**: 수 % ~ 수십 % 불확실도 가능

---

### 2-3. Manual – ASHRAE Handbook (신뢰도 높음)

**출처**: ASHRAE Handbook – Fundamentals (2017, 2022)
**대상**: 냉매 후보 화합물 중 ASHRAE 수록 신규 HFO/HFC (R-1225ye, R-1224yd, R-1233zd, R-1336mzz, HFE 계열 등 약 80개)

**장점:**
- 냉매 전용 데이터베이스, REFPROP EOS 기반 또는 실험 추천값
- ASHRAE에 수록된 냉매는 상업화 수준의 검증을 거침

**한계:**
- 같은 화합물이라도 2017판과 2022판 사이 값이 소폭 다를 수 있음
- 일부 신규 화합물(특히 E/Z 이성질체)은 측정값이 아닌 추산값일 수 있음

---

### 2-4. Manual – Poling et al. (신뢰도 중간~높음)

**출처**: Poling, Prausnitz, O'Connell, *The Properties of Gases and Liquids*, 5th ed.
**대상**: 일반 유기화합물 반례 (알케인, 방향족, 할로겐화합물 등 약 90개)

**장점:**
- 화학공학 분야 표준 참고서, 광범위한 화합물 커버
- 대부분 실험값 직접 수록

**한계:**
- Tc/Pc는 실험값이지만 ω는 Pitzer correlation으로 **재계산된 값**인 경우 있음
  → 이 경우 다른 출처의 Tc/Pc와 조합하면 ω에 수 % 오차 발생 가능
- 1970~1990년대 데이터가 많아 신규 화합물 누락

---

### 2-5. NIST+Manual (신뢰도 중간, ω 일관성 주의)

NIST가 Tc 또는 Pc 중 일부만 제공하고, 나머지를 manual_props.py로 보완한 경우.

**자기 일관성 위험 시나리오:**

```
시나리오 A: NIST에서 Tc/Pc 획득 → ω를 NIST Psat으로 계산
  → 완전 일관성 (문제 없음)

시나리오 B: NIST에서 Tc/Pc 획득 → Psat 계산 실패 → ω를 Manual에서 보완
  → ω가 다른 출처의 Pc 기준으로 계산된 값일 수 있음 → 수 % 오차 가능

시나리오 C: Tc/Pc 일부 누락 → Manual로 보완 → NIST Psat으로 ω 계산
  → Psat이 Manual로 보완된 Tc에서 벗어난 온도에서 계산될 수 있음
```

**해당 화합물 예시** (manual_props.py에서 일부 필드만 None이 아닌 경우):
- `Cyclohexanone`, `Decalin`, `DiethyleneGlycol` 등 — ω만 Poling에서 보완
- `CarbonDisulfide` — Pc=7.9 MPa만 있고 Tc 없음 (NIST+Manual 미적용, invalid)

---

## 3. 물성별 신뢰도 특성

### Tc (임계온도)

- 정의가 명확한 상태점이므로 출처 간 일치도가 가장 높음
- 소스 간 전형적 차이: 1~5 K (잘 연구된 화합물), 5~20 K (희귀 화합물)

### Pc (임계압력)

- 실험 측정이 어려운 편 (Tc 근처 고온·고압 조건 필요)
- 소스 간 전형적 차이: 0.05~0.2 MPa (잘 연구된 화합물), 0.5~수 MPa (희귀 화합물)
- **R-1113 주의**: NIST Pc 값이 40.7 bar가 아닌 260 ± 200 bar로 잘못 수록됨 → Manual로 덮어씀

### ω (이심인자)

- **유도량**이므로 자기 일관성이 중요: ω를 계산할 때 사용된 Pc와 Psat이 같은 출처여야 함
- 소스 간 전형적 차이: ±0.01~0.03 (자기 일관 출처), ±0.05~0.1 (혼합 출처)
- CoolProp은 EOS 내장값이라 가장 신뢰도 높음
- Poling의 ω는 독립적으로 측정·계산된 값으로, 다른 출처의 Tc/Pc와 조합 시 수 % 오차 가능

---

## 4. ML 분류 목적에서의 실질적 영향

### 영향이 작은 이유

1. **label 간 물성 차이가 크다**: 정례(냉매)와 반례(비냉매)의 Tc 분포가 대체로 100K 이상 차이
   - 정례: Tc ≈ 230~450 K 집중
   - 반례: Tc > 500 K 또는 Tc < 100 K가 다수

2. **분류 경계에서의 오차 영향**: 물성 오차가 label을 바꿀 수 있는 구간은 Tc ≈ 430~500 K 영역의 소수 화합물

3. **물성 패턴이 중요**: 정확한 수치보다 "낮은 Tc + 적당한 Pc + 낮은~중간 ω" 패턴이 label을 결정

### 주의가 필요한 화합물군

| 상황 | 해당 화합물 예시 | 권장 조치 |
|------|---------------|----------|
| NIST 참고문헌 수 적음 | 신규 HFO (R-1232xf, R-1354myfz 등) | 예측 결과 해석 시 물성 불확실도 고려 |
| NIST+Manual 혼합 | ω만 Poling에서 보완된 42개 | ω ± 0.05 수준의 불확실도 감안 |
| 측정값 없음 | CrownEther18c6, PhosphoricAcid | 추산 불가, valid=False |
| NIST 오류값 | Propionaldehyde (Tc=600K→504K로 수정) | manual_props.py로 덮어씀 |

### 권장 해석 방식

- **CoolProp / NIST / ASHRAE 출처**: 예측 결과를 높은 신뢰도로 해석 가능
- **Manual (Poling/CRC) 또는 NIST+Manual**: 경계값 근처 화합물의 경우 ±5~10% 물성 불확실도를 감안하여 해석
- **모델 calibration**: 가능하면 CoolProp 지원 화합물만으로 먼저 검증 후 일반화 성능 확인 권장

---

## 5. 관련 파일

| 파일 | 역할 |
|------|------|
| `data_pipeline/coolprop_fetcher.py` | CoolProp EOS 조회 |
| `data_pipeline/nist_fetcher.py` | NIST WebBook HTML 파싱 + ω 계산 |
| `data_pipeline/manual_props.py` | 문헌값 직접 입력 (출처 주석 포함) |
| `data/processed/refrigerants_final.csv` | `source_thermo` 컬럼: 각 화합물의 실제 적용 소스 |
