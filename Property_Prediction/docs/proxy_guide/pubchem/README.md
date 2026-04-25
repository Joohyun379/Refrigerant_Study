# PubChem API 접속 요청 안내

## 목적

냉매 물성 예측 모델 개발을 위한 분자구조 데이터 수집
(SMILES, 분자식, 분자량, InChI 등)

---

## 접속 대상

| 항목 | 내용 |
|------|------|
| 도메인 | `pubchem.ncbi.nlm.nih.gov` |
| 프로토콜 | HTTPS (443) |
| 방식 | REST API (GET 요청만 사용, 쓰기 없음) |
| 인증 | 없음 (공개 API) |
| Rate Limit | 최대 5 req/sec (0.3초 간격 준수) |

---

## 요청 URL 목록

### 1. CID 조회 (화합물명 → PubChem 내부 ID)

```
GET https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/cids/JSON
```

예시:
```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/1%2C1%2C1%2C2-Tetrafluoroethane/cids/JSON
```

Raw 응답 형식 (`raw_responses/step1_cid_*.json`):
```json
{
  "IdentifierList": {
    "CID": [13129]
  }
}
```

---

### 2. 분자구조 속성 조회

```
GET https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/{fields}/JSON
```

예시 (CID=13129, R-134a):
```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/13129/property/CanonicalSMILES,IsomericSMILES,InChI,InChIKey,MolecularFormula,MolecularWeight,IUPACName,XLogP,HeavyAtomCount/JSON
```

Raw 응답 형식 (`raw_responses/step2_props_*.json`):
```json
{
  "PropertyTable": {
    "Properties": [{
      "CID": 13129,
      "MolecularFormula": "C2H2F4",
      "MolecularWeight": 102.03,
      "CanonicalSMILES": "C(C(F)(F)F)(F)F",
      "IsomericSMILES": "CC(F)(F)F",
      "InChI": "InChI=1S/C2H2F4/...",
      "InChIKey": "LVGUZGTVOIAKKC-UHFFFAOYSA-N",
      "IUPACName": "1,1,1,2-tetrafluoroethane",
      "XLogP": 1.06,
      "HeavyAtomCount": 6
    }]
  }
}
```

---

### 3. 2D SDF 파일 다운로드 (분자 구조 시각화용)

```
GET https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/SDF
```

예시:
```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/13129/SDF
```

Raw 응답: SDF 텍스트 포맷 (`raw_responses/step3_sdf_*.sdf`)
→ RDKit 라이브러리로 2D 구조 시각화에 활용

---

## 실행 방법

```bash
pip install requests
python example.py
```

---

## Input

`input.csv`

| 컬럼 | 설명 |
|------|------|
| `identifier` | 프로젝트 내부 화합물 식별자 (R-계열 냉매명 등) |
| `search_name` | PubChem 검색에 사용하는 IUPAC명 또는 일반명 |

> R-계열 냉매명(R-134a 등)은 PubChem이 인식하지 못하므로
> IUPAC명으로 변환 후 요청 (`PUBCHEM_NAME_MAP`)

---

## Output

`output.csv`

| 컬럼 | 설명 | 예시 |
|------|------|------|
| `identifier` | 프로젝트 내부 식별자 | R-134a |
| `search_name` | PubChem 검색명 | 1,1,1,2-Tetrafluoroethane |
| `cid` | PubChem 화합물 ID | 13129 |
| `MolecularFormula` | 분자식 | C2H2F4 |
| `MolecularWeight` | 분자량 (g/mol) | 102.03 |
| `CanonicalSMILES` | 정규화 SMILES | C(C(F)(F)F)(F)F |
| `IsomericSMILES` | 입체화학 SMILES | CC(F)(F)F |
| `InChI` | 국제 화학 식별자 | InChI=1S/C2H2F4/... |
| `InChIKey` | InChI 해시 | LVGUZGTVOIAKKC-UHFFFAOYSA-N |
| `IUPACName` | IUPAC 명칭 | 1,1,1,2-tetrafluoroethane |
| `XLogP` | 옥탄올-물 분배계수 | 1.06 |
| `HeavyAtomCount` | 비수소 원자 수 | 6 |

---

## 수집 흐름

```
input.csv
  └── identifier → search_name (PUBCHEM_NAME_MAP 변환)
        ↓
   [URL 1] CID 조회
        ↓ CID
   [URL 2] 분자구조 속성 조회  → output.csv
        ↓ CID
   [URL 3] SDF 다운로드       → raw_responses/{cid}.sdf
```

---

## 파일 목록

```
pubchem/
├── README.md          ← 이 파일
├── example.py         ← 예시 실행 스크립트 (3종 화합물)
├── input.csv          ← 입력 예시
├── output.csv         ← 출력 예시 (example.py 실행 결과)
└── raw_responses/
    ├── step1_cid_1,1,1,2-Tetrafluoroethane.json  ← CID 조회 응답
    ├── step2_props_1,1,1,2-Tetrafluoroethane.json ← 속성 조회 응답
    ├── step3_sdf_1,1,1,2-Tetrafluoroethane.sdf    ← SDF 파일
    └── ...
```
