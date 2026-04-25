# 데이터 수집 API URL 정리

데이터 파이프라인에서 실제로 접속하는 외부 API URL 목록입니다.

---

## 1. PubChem PUG REST API (`pubchem_fetcher.py`)

Base URL: `https://pubchem.ncbi.nlm.nih.gov/rest/pug`

### 1-1. CID 조회 (화합물 이름 → PubChem ID)

```
GET /compound/name/{name}/cids/JSON
```

예시 (R-134a → PUBCHEM_NAME_MAP 변환 후):
```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/1%2C1%2C1%2C2-Tetrafluoroethane/cids/JSON
```

응답:
```json
{ "IdentifierList": { "CID": [13129] } }
```

> R-series 냉매명은 PubChem이 인식하지 못하므로 `PUBCHEM_NAME_MAP`에서 IUPAC명으로 변환 후 요청

---

### 1-2. 분자구조 속성 조회

```
GET /compound/cid/{cid}/property/{properties}/JSON
```

예시 (CID=13129, R-134a):
```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/13129/property/CanonicalSMILES,IsomericSMILES,InChI,InChIKey,MolecularFormula,MolecularWeight,IUPACName,XLogP,HeavyAtomCount/JSON
```

수집 필드:

| 필드 | 설명 |
|------|------|
| `CanonicalSMILES` | 정규화된 SMILES |
| `IsomericSMILES` | 입체화학 포함 SMILES |
| `InChI` | 국제 화학 식별자 |
| `InChIKey` | InChI 해시 키 |
| `MolecularFormula` | 분자식 (e.g. `C2H2F4`) |
| `MolecularWeight` | 분자량 (g/mol) |
| `IUPACName` | IUPAC 명칭 |
| `XLogP` | 옥탄올-물 분배계수 |
| `HeavyAtomCount` | 비수소 원자 수 |

---

### 1-3. 2D SDF 파일 다운로드

```
GET /compound/cid/{cid}/SDF
```

예시:
```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/13129/SDF
```

→ `data/raw/sdf/{cid}.sdf` 로 저장 (RDKit 2D 구조 시각화용)

---

### PubChem 수집 흐름

```
identifier ("R-134a")
    ↓ PUBCHEM_NAME_MAP
"1,1,1,2-Tetrafluoroethane"
    ↓ 1-1. CID 조회 → CID=13129
    ↓ 1-2. 분자구조 속성 조회 → SMILES, 분자식, 분자량 등
    ↓ 1-3. SDF 저장 → data/raw/sdf/13129.sdf
```

Rate limit: 최대 5 req/sec → 요청 간 0.3초 대기

---

## 2. NIST WebBook (`nist_fetcher.py`)

Base URL: `https://webbook.nist.gov/cgi/cbook.cgi`
Fluid URL: `https://webbook.nist.gov/cgi/fluid.cgi`

> CoolProp에 없는 화합물의 Tc, Pc, ω 보완용

### 2-1. 화합물 검색 (NIST ID 조회)

```
GET https://webbook.nist.gov/cgi/cbook.cgi?Name={name}&Units=SI
```

예시 (Acetone):
```
https://webbook.nist.gov/cgi/cbook.cgi?Name=acetone&Units=SI
```

→ 반환된 HTML 내 "Phase change data" 링크에서 NIST ID 추출
→ NIST ID 형식: `C{CAS 숫자}` (e.g. CAS 67-64-1 → `C67641`)

ID 추출 우선순위:
1. "Phase change data" 링크의 ID (가장 신뢰)
2. 검색 결과 목록 `<ol>` 첫 번째 항목
3. 페이지 내 링크 최빈 ID

---

### 2-2. Phase Change Data 페이지 (Tc, Pc 파싱)

```
GET https://webbook.nist.gov/cgi/cbook.cgi?ID={nist_id}&Units=SI&Mask=4
```

예시 (Acetone, ID=C67641):
```
https://webbook.nist.gov/cgi/cbook.cgi?ID=C67641&Units=SI&Mask=4
```

파싱 대상 테이블 (형식: `Quantity | Value | Units | Method | Reference | Comment`):

| Quantity | Value 예시 | Units | 변환 |
|----------|-----------|-------|------|
| `Tc` | `508. ± 2.` | K | 그대로 사용 |
| `Pc` | `48. ± 4.` | bar | × 0.1 → MPa |

---

### 2-3-A. 포화 증기압 API — ω 계산 (1순위)

```
GET https://webbook.nist.gov/cgi/fluid.cgi
    ?Action=Load&ID={nist_id}&Type=SatT&Digits=5
    &THigh={T_ref}&TLow={T_ref}&TInc=1&RefState=DEF
    &TUnit=K&PUnit=MPa&DUnit=mol%2Fl&HUnit=kJ%2Fmol
    &WUnit=m%2Fs&VisUnit=uPa*s&STUnit=N%2Fm
```

예시 (Propane, C74986, Tr=0.7×369.9=258.9 K):
```
https://webbook.nist.gov/cgi/fluid.cgi?Action=Load&ID=C74986&Type=SatT&Digits=5&THigh=258.9&TLow=258.9&TInc=1&RefState=DEF&TUnit=K&PUnit=MPa&DUnit=mol%2Fl&HUnit=kJ%2Fmol&WUnit=m%2Fs&VisUnit=uPa*s&STUnit=N%2Fm
```

> ⚠️ `VisUnit=uPa*s`의 `*`는 URL 인코딩하면 안 됨 → URL 직접 조립

→ HTML 테이블에서 `Pressure (MPa)` 열 값 = Psat
→ `ω = -log₁₀(Psat / Pc) - 1`

알코올, 케톤, 산 등 NIST 유체 DB 미수록 화합물은 **400 에러** → 2-3-B로 fallback

---

### 2-3-B. Antoine 방정식 fallback — ω 계산 (2순위)

fluid.cgi 실패 시 **2-2에서 이미 가져온 Phase Change 페이지**의 Antoine 테이블 사용:

```
log₁₀(P / bar) = A - B / (T / K + C)
```

예시 (Acetone, T_ref = 0.7 × 508.0 = 355.6 K):

| A | B | C | T 범위 |
|---|---|---|--------|
| 4.42448 | 1312.253 | -32.445 | 259~508 K |

```
log₁₀(Psat) = 4.42448 - 1312.253 / (355.6 + (-32.445)) = 0.364
Psat = 10^0.364 × 0.1 MPa = 0.231 MPa
ω = -log₁₀(0.231 / 4.8) - 1 = 0.317
```

T_ref가 Antoine 유효 범위 밖이면 T_high 기준으로 가장 가까운 계수 사용 (외삽)

---

### NIST 수집 흐름

```
identifier ("Acetone")
    ↓ NIST_NAME_MAP
"acetone"
    ↓ 2-1. 검색 → NIST ID = C67641
    ↓ 2-2. Phase Change 페이지 → Tc=508 K, Pc=4.8 MPa
    ↓ 2-3-A. fluid.cgi → Psat (성공 시)
      또는
    ↓ 2-3-B. Antoine 방정식 → Psat (fallback)
    ↓ ω = -log₁₀(Psat / Pc) - 1 = 0.317
```

요청 간 0.5초 대기

---

## 3. 전체 파이프라인 데이터 소스 우선순위

```
화합물
  ├── 분자구조        → PubChem (항상)
  └── 열역학 물성
        ├── 1순위: CoolProp (로컬 라이브러리, 빠름)
        └── 2순위: NIST WebBook (HTTP 요청, 느림)
              ├── Tc, Pc → Phase Change 페이지 HTML 파싱
              └── ω      → fluid.cgi API → Antoine 방정식 (fallback)
```
