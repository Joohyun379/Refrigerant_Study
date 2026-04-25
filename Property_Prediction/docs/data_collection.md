# 데이터 수집 프로세스

냉매 물성 예측 프로젝트의 전체 데이터 수집 흐름을 설명합니다.

---

## 전체 흐름 개요

```
compound_list.py
      │
      ▼
┌─────────────────────────────────────────────────┐
│  화합물별 반복 (485종)                            │
│                                                 │
│  1. manual_smiles.py 확인 (등록된 경우 우선 적용) │
│  2. PubChem  → 분자구조 정보                     │
│  3. manual_smiles.py 덮어쓰기 (오류 화합물 보정)  │
│  4. 열역학 물성 수집 (fallback 체인)              │
│  5. 검증 (validate) + INVALID_COMPOUNDS 처리     │
└─────────────────────────────────────────────────┘
      │
      ▼
data/raw/refrigerants_raw.csv
data/processed/refrigerants_final.csv
data/raw/sdf/{cid}.sdf
```

---

## Step 1 — 화합물 목록 (`compound_list.py`)

`get_all_compounds()` 가 정례(label=1) + 반례(label=0) 전체 목록을 반환합니다.

| 구분 | 수 | 예시 그룹 |
|------|-----|-----------|
| 정례 (냉매 가능) | 97 | HFC, HFO, HCFC, 자연냉매, HFE 등 |
| 반례 (냉매 불가) | 388 | Tc_too_high, triple_bond_alkyne, halogenated_aromatic 등 |
| **합계** | **485** | |

각 항목은 `{"identifier": "R-134a", "label": 1, "group": "HFC"}` 형태입니다.

---

## Step 2 — 분자구조 수집 (PubChem)

**모듈:** `data_pipeline/pubchem_fetcher.py`
**외부 접근:** `https://pubchem.ncbi.nlm.nih.gov` (HTTPS 443)

### 수집 순서 (화합물당 최대 3회 요청)

```
① 이름으로 CID 조회
   GET /rest/pug/compound/name/{name}/cids/JSON

② CID로 물성 조회
   GET /rest/pug/compound/cid/{cid}/property/
       MolecularFormula,MolecularWeight,IsomericSMILES,
       InChI,InChIKey,IUPACName/JSON

③ 2D 구조 SDF 다운로드
   GET /rest/pug/compound/cid/{cid}/SDF?record_type=2d
```

### 수집 컬럼

| 컬럼 | 설명 |
|------|------|
| `cid` | PubChem Compound ID |
| `MolecularFormula` | 분자식 (e.g. C2H2F4) |
| `MolecularWeight` | 분자량 [g/mol] |
| `SMILES` | IsomericSMILES (입체화학 표기 포함) |
| `ConnectivitySMILES` | ConnectivitySMILES (입체화학 제거) |
| `InChI` / `InChIKey` | 표준 식별자 |
| `IUPACName` | IUPAC 명칭 |
| `smiles_source` | SMILES 출처 (`PubChem` / `Manual`) |
| `has_stereo` | SMILES에 `/`, `\`, `@` 포함 여부 |

SDF 파일은 `data/raw/sdf/{cid}.sdf` 에 저장됩니다.

### 이름 매핑

냉매 식별자(e.g. `R-134a`)와 PubChem 검색명이 다를 경우 `PUBCHEM_NAME_MAP` 딕셔너리에서 변환합니다.

### Manual SMILES 덮어쓰기

PubChem이 잘못된 CID를 반환하거나 SMILES를 제공하지 않는 경우, `data_pipeline/manual_smiles.py`의 값이 우선 적용됩니다.
SMILES뿐 아니라 **InChIKey, InChI도 함께 덮어씁니다.**

현재 등록된 화합물 (10개):

| 화합물 | 사유 |
|--------|------|
| CarbonDisulfide | PubChem SMILES 미제공 |
| R-1120 | PubChem SMILES 미제공 |
| DipentylEther | PubChem SMILES 미제공 |
| PerfluoroMethylDecalin | PubChem SMILES 미제공 |
| R-1234ze(Z) | PubChem이 (E) 이성질체 CID 반환 |
| R-1112a | PubChem이 R-1113 CID 반환 |
| R-244fa | PubChem이 R-243fa CID 반환 |
| R-1122 | pubchem_fetcher에 R-1112a 구조명 오등록 |
| R-123a | pubchem_fetcher에 R-124 구조명 오등록 |
| R-1232xf | pubchem_fetcher에 R-1233zd 구조명 오등록 |

---

## Step 3 — 열역학 물성 수집 (fallback 체인)

임계온도 Tc [K], 임계압력 Pc [MPa], 이심인자 ω 를 수집합니다.
세 개 소스를 아래 우선순위로 시도하며, 먼저 성공한 소스를 사용합니다.

```
CoolProp
   │ 실패 (Tc=None)
   ▼
Manual 문헌값  ─── 완전(Tc+Pc+ω 모두 있음) ──▶  사용 (source="Manual")
   │ 불완전
   ▼
NIST WebBook HTML 파싱
   │ 일부 누락
   ▼
Manual 문헌값으로 누락 필드만 보완        (source="NIST+Manual")
```

`source_thermo` 컬럼에 실제 사용된 소스가 기록됩니다.

### 현재 출처별 분포

| 출처 | 수 |
|------|-----|
| CoolProp | 112 |
| Manual | 190 |
| NIST | 141 |
| NIST+Manual | 42 |

### 3-1. CoolProp (로컬 라이브러리)

**모듈:** `data_pipeline/coolprop_fetcher.py`
**외부 접근 없음** — pip 설치 후 로컬에서 동작 (방화벽 무관)

```python
state = CoolProp.AbstractState("HEOS", cp_name)
Tc    = CP.PropsSI("Tcrit", cp_name)          # K
Pc    = CP.PropsSI("Pcrit", cp_name) / 1e6    # Pa → MPa
omega = state.acentric_factor()
```

`COOLPROP_NAME_MAP`에 냉매 식별자 → CoolProp 내부 이름 매핑이 정의되어 있습니다.

### 3-2. Manual 문헌값 (로컬)

**모듈:** `data_pipeline/manual_props.py`
**외부 접근 없음**

NIST가 오류값을 반환하거나 데이터 자체가 없는 화합물의 물성을 ASHRAE/Poling 문헌에서 직접 입력한 딕셔너리입니다.

이 소스가 CoolProp보다 앞이 아닌, NIST보다 앞에 위치하는 이유:

> NIST WebBook은 여러 문헌의 평균값을 제공하므로, 참고문헌 수가 적거나 상충하는 경우 불확실도가 매우 큰 오류값이 나올 수 있습니다.
> 예: R-1113 (Chlorotrifluoroethylene) → NIST Pc = 260 ± 200 bar (실제 값 40.7 bar)

**출처:**
- [1] Poling, Prausnitz, O'Connell, *The Properties of Gases and Liquids*, 5th ed.
- [2] ASHRAE Handbook – Fundamentals (2017)
- [3] CRC Handbook of Chemistry and Physics, 103rd ed.

### 3-3. NIST WebBook HTML 파싱

**모듈:** `data_pipeline/nist_fetcher.py`
**외부 접근:** `https://webbook.nist.gov` (HTTPS 443)

#### 수집 순서 (화합물당 최대 4회 요청)

```
① 이름으로 NIST ID 검색
   GET /cgi/cbook.cgi?Name={name}&Units=SI
   → HTML 파싱으로 NIST ID (e.g. C67641) 추출
     우선순위: "Phase change data" 링크 > 검색결과 목록 첫 항목 > 최빈 ID

② Phase Change Data 페이지에서 Tc, Pc 파싱
   GET /cgi/cbook.cgi?ID={id}&Units=SI&Mask=4
   → HTML 테이블에서 Quantity="Tc" / "Pc" 행 추출
   → Pc 단위 자동 변환: bar×0.1, kPa/1000, atm×0.101325 → MPa

③ Psat(Tr=0.7) 조회 → ω 계산
   ω = -log₁₀(Psat / Pc) - 1  (at Tr = T/Tc = 0.7)

   3-a. fluid.cgi API (NIST 유체 DB 수록 화합물)
        GET /cgi/fluid.cgi?Action=Load&ID={id}&Type=SatT&...
        ※ VisUnit의 * 는 URL 인코딩 금지 (%2A 불가 → 400 오류 발생)

   3-b. Antoine 방정식 fallback (Phase Change 페이지 내 테이블)
        log₁₀(P/bar) = A - B / (T/K + C)
        T_ref가 유효 범위 밖일 경우 가장 가까운 Antoine 행으로 외삽
```

---

## Step 4 — 검증 (`validate.py`)

수집된 데이터의 합리적 범위를 검사하고 `valid` 컬럼을 추가합니다.

| 컬럼 | 유효 범위 | 비고 |
|------|-----------|------|
| `Tc_K` | 100 ~ 1000 K | |
| `Pc_MPa` | 0.01 ~ 100 MPa | |
| `omega` | -0.5 ~ 2.0 | |
| `MolecularWeight` | 10 ~ 2000 g/mol | |

범위를 벗어나거나 결측인 경우 `validation_notes` 컬럼에 상세 내용 기록, `valid=False` 처리.

`INVALID_COMPOUNDS` (`manual_smiles.py`)에 등록된 화합물은 검증 통과 여부와 무관하게 `valid=False`로 강제 처리됩니다.

### 현재 유효성 결과

| 상태 | 수 |
|------|-----|
| valid=True | 476 (98.1%) |
| valid=False | 9 (1.9%) |

valid=False 상세 사유는 `docs/dataset_status.md` 참고.

---

## 출력 파일

| 경로 | 내용 |
|------|------|
| `data/raw/refrigerants_raw.csv` | 검증 전 전체 수집 데이터 |
| `data/processed/refrigerants_final.csv` | 검증 후 최종 데이터 (`valid`, `validation_notes` 포함) |
| `data/raw/sdf/{cid}.sdf` | PubChem 2D 구조 파일 |

### 주요 컬럼 목록

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `identifier` | str | 화합물 식별자 (e.g. R-134a) |
| `label` | int | 1=정례(냉매 가능), 0=반례 |
| `group` | str | 화합물 그룹 (e.g. HFC, triple_bond_alkyne) |
| `cid` | int | PubChem CID |
| `MolecularFormula` | str | 분자식 |
| `MolecularWeight` | float | 분자량 [g/mol] |
| `SMILES` | str | IsomericSMILES (입체화학 포함) |
| `ConnectivitySMILES` | str | ConnectivitySMILES (입체화학 제거) |
| `InChIKey` | str | 표준 해시 식별자 |
| `smiles_source` | str | SMILES 출처 (`PubChem` / `Manual`) |
| `has_stereo` | bool | SMILES에 입체화학 표기 포함 여부 |
| `Tc_K` | float | 임계온도 [K] |
| `Pc_MPa` | float | 임계압력 [MPa] |
| `omega` | float | 이심인자 [-] |
| `source_thermo` | str | 열역학 데이터 출처 |
| `valid` | bool | 유효성 검사 통과 여부 |
| `validation_notes` | str | 유효성 검사 상세 내용 |

---

## 관련 파일 구조

```
data_pipeline/
├── compound_list.py      # 화합물 목록 정의 (485개)
├── pubchem_fetcher.py    # PubChem 분자구조 수집 + 이름 매핑
├── manual_smiles.py      # 수동 입력 SMILES/InChIKey (10개) + INVALID_COMPOUNDS
├── coolprop_fetcher.py   # CoolProp 열역학 물성 (로컬)
├── nist_fetcher.py       # NIST WebBook HTML 파싱
├── manual_props.py       # 문헌값 직접 입력 (로컬)
└── validate.py           # 데이터 품질 검증
run_pipeline.py           # 전체 파이프라인 실행 (30~40분)
patch_thermo.py           # 열역학 물성만 재적용 (1~2분)
```
