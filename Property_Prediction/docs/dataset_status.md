# 데이터셋 현황 (2026-04-01 기준)

## 1. 전체 요약

| 항목 | 수치 |
|------|------|
| 총 화합물 수 | 485개 |
| 정례 (label=1) | 97개 |
| 반례 (label=0) | 388개 |
| valid=True | 476개 (98.1%) |
| valid=False | 9개 (1.9%) |

---

## 2. label 정의

- **label=1 (정례)**: 냉매로 구조적으로 유리한 화합물 (소형 분자, 적절한 불소 함량, 대칭성 등)
- **label=0 (반례)**: 냉매로 구조적으로 불리한 화합물 (대형 분자, F 없음, 수소결합, 고비점 등)

---

## 3. 열역학 물성 출처

| 출처 | 화합물 수 | 설명 |
|------|----------|------|
| CoolProp | 112 | CoolProp 라이브러리 자동 조회 |
| Manual | 190 | 문헌값 직접 입력 (`manual_props.py`) |
| NIST | 141 | NIST WebBook HTML 파싱 |
| NIST+Manual | 42 | NIST 기본값 + 누락 물성 수동 보완 |

---

## 4. SMILES 출처

| 출처 | 화합물 수 |
|------|----------|
| PubChem | 474 |
| Manual | 10 |
| 없음 (invalid) | 1 (R-1354myfz) |

Manual SMILES 항목: `data_pipeline/manual_smiles.py` 참고

---

## 5. 그룹별 분포

### 정례 그룹 (label=1, 97개)

| 그룹 | 수 | 설명 |
|------|----|------|
| C1_moderate_F | 4 | C1, 중간 불소 (R-41, R-32 등) |
| C2_doublebond_F | 1 | C2 이중결합 + F |
| C2_saturated_F | 5 | C2 포화 HFC |
| C2_HFO | 5 | C2 HFO |
| C2_HFO_Cl_add | 5 | C2 HFO + Cl |
| C2_mixed_halogen | 3 | C2 혼합 할로겐 |
| C2_HFC_additional | 2 | C2 HFC 추가 |
| C3_doublebond_F | 6 | C3 HFO 핵심 (R-1234yf 등) |
| C3_saturated_symmetric_F | 4 | C3 대칭 HFC |
| C3_HFC_isomers | 5 | C3 HFC 이성질체 |
| C3_HFO_additional | 5 | C3 HFO 추가 |
| C3_HCFC_additional | 3 | C3 HCFC 추가 |
| C3_HFO_ClF_add | 2 | C3 HFO+Cl+F 추가 |
| C4_symmetric_F | 2 | C4 대칭 불소화 |
| C4_HFO_additional | 1 | C4 HFO 추가 |
| HCFC | 11 | HCFC 계열 전체 |
| HFC_extended2 | 4 | HFC 확장 |
| HFE_small | 5 | HFE 소형 |
| HFE_extended | 2 | HFE 확장 |
| C1C2_BrF | 3 | C1~C2 Br+F |
| C1C2_HCFC_additional | 3 | C1~C2 HCFC 추가 |
| C1_additional | 2 | C1 추가 냉매 후보 |
| inorganic_refrigerant | 3 | 무기 냉매 (NH3, SO2, CO2) |
| inorganic_small_add | 3 | 무기 소형 추가 |
| misc_small_refrigerant | 3 | 기타 소형 냉매 |
| small_polar_inorganic | 3 | 소형 극성 무기물 |
| small_symmetric_inorganic | 2 | 소형 대칭 무기물 |

### 반례 그룹 (label=0, 388개) — 주요 범주

| 범주 | 그룹 수 | 수 | 설명 |
|------|--------|----|------|
| 장쇄/고분자 알케인 | 6 | ~24 | Tc_too_high_nalkane 등 |
| 방향족 | 8 | ~35 | aromatic_*, halogenated_aromatic 등 |
| 알코올/글리콜 | 6 | ~24 | alcohol_series, H_bonding 등 |
| 에스터/카보네이트 | 5 | ~26 | ester, short_ester 등 |
| 케톤/알데히드 | 3 | ~16 | ketone, aldehyde 등 |
| 아민/질소화합물 | 4 | ~20 | amine, nitrile 등 |
| 에테르 | 3 | ~14 | ether_*, glycol_ether 등 |
| 실록산 | 2 | ~9 | large_molecule_siloxane 등 |
| 할로겐화 | 6 | ~21 | halo_*, Cl_alkane 등 |
| PFC/불소화 | 5 | ~13 | fully_fluorinated, PFC_extended 등 |
| 극저온/특수 | 1 | 10 | Tc_too_low (He, Ne, H2 등) |
| 기타 | 다수 | ~126 | 산, 아마이드, 락톤, 인산염 등 |

---

## 6. valid=False 화합물 (9개)

| 화합물 | label | 사유 | 조치 |
|--------|-------|------|------|
| R-1354myfz | 1 | SMILES 미확인 (R-1336mzz(Z) 구조 잘못 할당) | 올바른 구조 재조사 필요 |
| Helium | 0 | Tc=5.2 K (validator 범위 미달) | 의도적 포함 (극저온 반례) |
| Neon | 0 | Tc=44.4 K (validator 범위 미달) | 의도적 포함 (극저온 반례) |
| Hydrogen | 0 | Tc=33.1 K, MW=2.0 (범위 미달) | 의도적 포함 (극저온 반례) |
| ParaHydrogen | 0 | Tc=32.9 K, MW=2.0 (범위 미달) | 의도적 포함 (극저온 반례) |
| Deuterium | 0 | Tc=38.3 K, MW=4.0 (범위 미달) | 의도적 포함 (동위원소 반례) |
| CarbonDisulfide | 0 | Tc/Pc/omega 없음 | 신뢰 가능한 문헌값 필요 |
| CrownEther18c6 | 0 | Tc/Pc/omega 없음 | 신뢰 데이터 부재 |
| PhosphoricAcid | 0 | Tc/Pc/omega 없음 | 분해 반응으로 측정 불가 |

> **참고**: Helium~Deuterium 5개는 validator의 Tc 하한(100 K) 때문에 invalid 처리되지만,
> 구조 데이터와 물성은 정상적으로 존재함. ML 학습 시 별도 처리 필요.

---

## 7. 입체이성질체 쌍 (7그룹)

| 유형 | 쌍 |
|------|----|
| E/Z 기하이성질체 | R-1234ze(E/Z), R-1225ye(E/Z), R-1233zd(E/Z), R-1336mzz(E/Z) |
| cis/trans | R-1130(trans) / R-1130a(cis), cis/trans-2-Butene |
| 동위원소·스핀이성질체 | Hydrogen / ParaHydrogen / Deuterium |

InChIKey 기준으로 식별: 첫 14자(연결구조) 동일, 두 번째 블록 상이.

---

## 8. 주요 데이터 품질 이슈 및 수정 이력

### 수정 완료

| 항목 | 문제 | 조치 |
|------|------|------|
| R-1234ze(Z) | PubChem이 (E) CID 반환 → InChIKey 오류 | manual_smiles.py에 (Z) SMILES/InChIKey 등록 |
| R-1112a | PubChem이 R-1113 CID 반환 | manual_smiles.py 등록 (CID=6592) |
| R-244fa | PubChem이 R-243fa CID 반환 | manual_smiles.py 등록 (CID=54443433) |
| R-1122 | pubchem_fetcher에 R-1112a 이름 오등록 | 수정 + manual_smiles.py 등록 (CHCl=CF2) |
| R-123a | pubchem_fetcher에 R-124 이름 오등록 | 수정 + manual_smiles.py 등록 (CClF2-CHClF) |
| R-1232xf | R-1233zd 구조 잘못 할당 | 수정 (CHCl=CClCF3, C3HCl2F3) |
| Benzophenol | Benzophenone CID 잘못 할당 | CID·SMILES 수정 (4-hydroxybenzophenone) |
| R-1120, DipentylEther, PerfluoroMethylDecalin | PubChem SMILES 미제공 | manual_smiles.py 등록 |
| CarbonDisulfide | PubChem SMILES 미제공 | manual_smiles.py 등록 (S=C=S) |
| R245cb | R-245cb와 완전 중복 | 삭제 |
| Trichloroethylene | R-1120과 동일 구조 (label 충돌) | 삭제 |
| 동일구조 이름 중복 13개 | label 충돌 또는 데이터 누출 위험 | 삭제 |

### 미해결

| 항목 | 문제 | 비고 |
|------|------|------|
| R-1354myfz | 올바른 구조 미확인 | ASHRAE 34 문서 재조사 필요 |
| CarbonDisulfide | Tc/Pc/omega 없음 | 문헌값 조사 필요 |

---

## 9. 파이프라인 재실행 시 보존 사항

`run_pipeline.py` 또는 `patch_thermo.py` 재실행 시 아래 항목은 자동 보존됨:

- `data_pipeline/manual_smiles.py`: SMILES, InChIKey, InChI 덮어쓰기 (10개 화합물)
- `data_pipeline/manual_smiles.py` → `INVALID_COMPOUNDS`: R-1354myfz valid=False 강제 적용
- `data_pipeline/compound_list.py`: 중복 화합물 제거 반영
- `data_pipeline/pubchem_fetcher.py`: 이름 매핑 오류 수정 반영
