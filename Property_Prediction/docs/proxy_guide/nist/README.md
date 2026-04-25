# NIST WebBook API 접속 요청 안내

## 목적

CoolProp 라이브러리에 없는 화합물의 열역학 물성 수집
(임계온도 Tc, 임계압력 Pc, 이심인자 ω)

---

## 접속 대상

| 항목 | 내용 |
|------|------|
| 도메인 | `webbook.nist.gov` |
| 프로토콜 | HTTPS (443) |
| 방식 | HTML 페이지 GET 요청 + 파싱 (쓰기 없음) |
| 인증 | 없음 (공개 웹사이트) |
| 요청 간격 | 0.5초 이상 준수 |

---

## 요청 URL 목록

### 1. 화합물 검색 → NIST ID 추출

```
GET https://webbook.nist.gov/cgi/cbook.cgi?Name={name}&Units=SI
```

예시:
```
https://webbook.nist.gov/cgi/cbook.cgi?Name=acetone&Units=SI
```

Raw 응답: HTML 페이지 (`raw_responses/step1_search_*.html`)

추출 대상: 페이지 내 **"Phase change data"** 링크의 `ID` 파라미터
```html
<a href="/cgi/cbook.cgi?ID=C67641&Units=SI&Mask=4#Thermo-Phase">Phase change data</a>
```
→ NIST ID = `C67641` (형식: `C` + CAS 번호 숫자)

---

### 2. Phase Change Data 페이지 (Tc, Pc, Antoine 계수)

```
GET https://webbook.nist.gov/cgi/cbook.cgi?ID={nist_id}&Units=SI&Mask=4
```

예시 (Acetone, ID=C67641):
```
https://webbook.nist.gov/cgi/cbook.cgi?ID=C67641&Units=SI&Mask=4
```

Raw 응답: HTML 페이지 (`raw_responses/step2_phase_*.html`)

파싱 대상 ① — 임계 물성 테이블:

```
Quantity | Value      | Units | Method | Reference | Comment
---------+------------+-------+--------+-----------+---------
Tc       | 508. ± 2.  | K     | AVG    | N/A       | Average of 19 values
Pc       | 48. ± 4.   | bar   | AVG    | N/A       | Average of 9 values
```

→ `Tc_K = 508.0 K`,  `Pc_MPa = 48 bar × 0.1 = 4.8 MPa`

파싱 대상 ② — Antoine 계수 테이블 (ω 계산 fallback용):

```
Temperature (K)      | A       | B        | C       | Reference
---------------------+---------+----------+---------+------------------
259.16 to 507.60     | 4.42448 | 1312.253 | -32.445 | Ambrose et al.
```

Antoine 방정식: `log₁₀(P/bar) = A − B / (T/K + C)`

---

### 3-A. 포화 증기압 API (ω 계산 1순위)

냉매, 탄화수소 등 NIST 유체 DB 수록 화합물에만 적용 가능.

```
GET https://webbook.nist.gov/cgi/fluid.cgi
    ?Action=Load
    &ID={nist_id}
    &Type=SatT
    &Digits=5
    &THigh={T_ref}    ← T_ref = 0.7 × Tc
    &TLow={T_ref}
    &TInc=1
    &RefState=DEF
    &TUnit=K
    &PUnit=MPa
    &DUnit=mol%2Fl
    &HUnit=kJ%2Fmol
    &WUnit=m%2Fs
    &VisUnit=uPa*s    ← * 문자 URL 인코딩 금지
    &STUnit=N%2Fm
```

예시 (Propane C74986, T_ref = 0.7 × 369.9 = 258.93 K):
```
https://webbook.nist.gov/cgi/fluid.cgi?Action=Load&ID=C74986&Type=SatT&Digits=5&THigh=258.93&TLow=258.93&TInc=1&RefState=DEF&TUnit=K&PUnit=MPa&DUnit=mol%2Fl&HUnit=kJ%2Fmol&WUnit=m%2Fs&VisUnit=uPa*s&STUnit=N%2Fm
```

Raw 응답: HTML 페이지 (`raw_responses/step3a_fluid_*.html`)

파싱 대상 — 포화 물성 테이블 헤더 예시:
```
Temperature (K) | Pressure (MPa) | Density (mol/l) | ...
----------------+----------------+-----------------+----
258.93          | 0.0070853      | ...             | ...
```

→ `Psat = 0.0070853 MPa`

**알코올, 케톤, 카르복실산 등은 NIST 유체 DB 미수록 → HTTP 400 반환 → 3-B로 전환**

---

### 3-B. Antoine 방정식 fallback (ω 계산 2순위)

fluid.cgi에서 400 에러 발생 시, Step 2에서 파싱한 Antoine 계수로 계산.

```
log₁₀(P/bar) = A − B / (T/K + C)
Psat [MPa] = 10^{log₁₀(P)} × 0.1
```

Acetone 예시 (T_ref = 0.7 × 508.0 = 355.6 K):
```
A=4.42448, B=1312.253, C=-32.445  (T 범위: 259.16~507.60 K)

log₁₀(P/bar) = 4.42448 - 1312.253 / (355.6 + (-32.445))
             = 4.42448 - 4.0607
             = 0.3637

Psat = 10^0.3637 × 0.1 = 0.2311 MPa
```

추가 HTTP 요청 없음 (Step 2 HTML 재활용)

---

### ω (이심인자) 계산

```
ω = -log₁₀(Psat / Pc) - 1   (Tr = 0.7 에서)
```

Acetone 예시:
```
ω = -log₁₀(0.2311 / 4.8) - 1 = -(-1.3175) - 1 = 0.3175
```

---

## 실행 방법

```bash
pip install requests beautifulsoup4
python example.py
```

---

## Input

`input.csv`

| 컬럼 | 설명 |
|------|------|
| `identifier` | 프로젝트 내부 화합물 식별자 |
| `search_name` | NIST WebBook 검색명 |
| `note` | fluid.cgi 지원 여부 |

---

## Output

`output.csv`

| 컬럼 | 설명 | 예시 |
|------|------|------|
| `identifier` | 화합물 식별자 | Acetone |
| `nist_id` | NIST 내부 ID | C67641 |
| `Tc_K` | 임계온도 [K] | 508.0 |
| `Pc_MPa` | 임계압력 [MPa] | 4.8 |
| `T_ref_K` | Tr=0.7 기준 온도 [K] | 355.6 |
| `Psat_MPa` | T_ref 에서의 포화 증기압 [MPa] | 0.231064 |
| `omega` | 이심인자 ω | 0.317515 |
| `omega_method` | ω 계산 방법 | `fluid_api` 또는 `Antoine` |
| `Antoine_A` | Antoine 계수 A (fallback 시) | 4.42448 |
| `Antoine_B` | Antoine 계수 B (fallback 시) | 1312.253 |
| `Antoine_C` | Antoine 계수 C (fallback 시) | -32.445 |

---

## 수집 흐름

```
input.csv
  └── search_name
        ↓
   [URL 1] 화합물 검색  → NIST ID (C67641)
        ↓
   [URL 2] Phase Change 페이지
        ├── Tc [K], Pc [bar → MPa]
        └── Antoine 계수 (A, B, C)
        ↓
   [URL 3-A] fluid.cgi  → Psat [MPa]  (성공 시)
      또는
   [계산]  Antoine 방정식 → Psat [MPa]  (400 에러 시 fallback)
        ↓
   ω = -log₁₀(Psat / Pc) - 1  → output.csv
```

---

## 화합물별 ω 계산 방법 분류

| 화합물 | fluid.cgi | Antoine | 사유 |
|--------|-----------|---------|------|
| Propane | ✅ 사용 | - | NIST 유체 DB 수록 |
| Acetone | ❌ 400 에러 | ✅ 사용 | NIST 유체 DB 미수록 |
| 1-Propanol | ❌ 400 에러 | ✅ 사용 | NIST 유체 DB 미수록 |

---

## 파일 목록

```
nist/
├── README.md               ← 이 파일
├── example.py              ← 예시 실행 스크립트 (3종 화합물)
├── input.csv               ← 입력 예시
├── output.csv              ← 출력 예시 (example.py 실행 결과)
└── raw_responses/
    ├── step1_search_propane.html      ← [URL 1] 검색 결과 HTML
    ├── step1_search_acetone.html
    ├── step1_search_1-propanol.html
    ├── step2_phase_C74986.html        ← [URL 2] Phase Change 페이지 HTML (Propane)
    ├── step2_phase_C67641.html        ← [URL 2] Phase Change 페이지 HTML (Acetone)
    ├── step2_phase_C71238.html        ← [URL 2] Phase Change 페이지 HTML (1-Propanol)
    ├── step3a_fluid_C74986.html       ← [URL 3-A] fluid.cgi 응답 HTML (성공)
    ├── step3a_fluid_C67641.html       ← [URL 3-A] fluid.cgi 응답 HTML (400 에러)
    └── step3a_fluid_C71238.html       ← [URL 3-A] fluid.cgi 응답 HTML (400 에러)
```
