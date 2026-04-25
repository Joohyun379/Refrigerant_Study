"""
수동 입력 SMILES (Manual SMILES)

사용 조건:
  - PubChem이 SMILES를 제공하지 않는 경우
  - PubChem이 잘못된 이성질체 SMILES를 반환하는 경우 (E/Z 혼동 등)
  - pubchem_fetcher 이름 매핑 오류로 잘못된 CID가 반환된 경우

주의: run_pipeline.py가 PubChem 결과를 얻은 후에도 이 파일의 값이 우선 적용됨.
      SMILES를 변경할 경우 반드시 이 파일을 수정할 것.

컬럼 설명:
  smiles       : IsomericSMILES (입체화학 표기 포함)
  connectivity : ConnectivitySMILES (입체화학 제거, 위상 구조만)
  inchikey     : InChIKey (RDKit으로 계산, PubChem 반환값 덮어씀)
  inchi        : InChI (RDKit으로 계산)
  reason       : 수동 입력 사유
"""

from typing import Optional


MANUAL_SMILES: dict = {

    # ── PubChem SMILES 미제공 ────────────────────────────────────────────────
    # CarbonDisulfide = CS2
    # PubChem CID=6348이지만 IsomericSMILES 필드 없음
    "CarbonDisulfide": {
        "smiles":       "S=C=S",
        "connectivity": "S=C=S",
        "inchikey":     "QGJOPFRUJISHPQ-UHFFFAOYSA-N",
        "inchi":        "InChI=1S/CS2/c2-1-3",
        "reason":       "PubChem CID=6348 SMILES 미제공",
    },

    # R-1120 = trichloroethylene (CHCl=CCl2)
    # PubChem CID=6575이지만 IsomericSMILES 필드 없음
    "R-1120": {
        "smiles":       "ClC=C(Cl)Cl",
        "connectivity": "ClC=C(Cl)Cl",
        "inchikey":     "XSTXAVWGXDQKEL-UHFFFAOYSA-N",
        "inchi":        "InChI=1S/C2HCl3/c3-1-2(4)5/h1H",
        "reason":       "PubChem CID=6575 SMILES 미제공",
    },

    # DipentylEther = di-n-pentyl ether (C10H22O)
    # PubChem CID=12743이지만 IsomericSMILES 필드 없음
    "DipentylEther": {
        "smiles":       "CCCCCOCCCCC",
        "connectivity": "CCCCCOCCCCC",
        "inchikey":     "AOPDRZXCEAKHHW-UHFFFAOYSA-N",
        "inchi":        "InChI=1S/C10H22O/c1-3-5-7-9-11-10-8-6-4-2/h3-10H2,1-2H3",
        "reason":       "PubChem CID=12743 SMILES 미제공",
    },

    # PerfluoroMethylDecalin = perfluorodecalin 유사체 (C9F16)
    # PubChem CID=9386이지만 IsomericSMILES 필드 없음
    "PerfluoroMethylDecalin": {
        "smiles":       "FC1(F)C(F)(F)C(F)(F)C2(F)C(F)(F)C(F)(F)C(F)(F)C2(F)C1(F)F",
        "connectivity": "FC1(F)C(F)(F)C(F)(F)C2(F)C(F)(F)C(F)(F)C(F)(F)C2(F)C1(F)F",
        "inchikey":     "NLQOEOVORMKOIY-UHFFFAOYSA-N",
        "inchi":        "InChI=1S/C9F16/c10-1-2(11,4(14,15)7(20,21)3(1,12)13)6(18,19)9(24,25)8(22,23)5(1,16)17",
        "reason":       "PubChem CID=9386 SMILES 미제공",
    },

    # ── PubChem 이성질체 오류 수정 ───────────────────────────────────────────
    # R-1234ze(Z) = (Z)-1,3,3,3-tetrafluoroprop-1-ene
    # PubChem이 (E) 이성질체 CID(5708720)를 반환 → 올바른 CID=11116025
    # (Z): F와 CF3가 이중결합 같은 쪽
    "R-1234ze(Z)": {
        "smiles":       "F/C=C\\C(F)(F)F",
        "connectivity": "C(=CF)C(F)(F)F",
        "inchikey":     "CDOOAUSHHFGWSA-UPHRSURJSA-N",
        "inchi":        "InChI=1S/C3H2F4/c4-2-1-3(5,6)7/h1-2H/b2-1-",
        "reason":       "PubChem이 (E) CID 반환. CID=11116025 기준 수동 입력.",
    },

    # R-1112a = 1,1-dichloro-2,2-difluoroethene (CCl2=CF2)
    # PubChem이 R-1113(CF2=CFCl) CID(6594)를 반환 → 올바른 CID=6592
    "R-1112a": {
        "smiles":       "ClC(=C(F)F)Cl",
        "connectivity": "ClC(=C(F)F)Cl",
        "inchikey":     "QDGONURINHVBEW-UHFFFAOYSA-N",
        "inchi":        "InChI=1S/C2Cl2F2/c3-1(4)2(5)6",
        "reason":       "PubChem이 R-1113 CID(6594) 반환. CID=6592 기준 수동 입력.",
    },

    # R-244fa = 4-chloro-1,1,1,2-tetrafluorobutane (CF3-CHF-CH2-CH2Cl)
    # PubChem이 R-243fa(3-chloro-1,1,1-trifluoropropane) CID(10000)를 반환
    # → 올바른 CID=54443433
    "R-244fa": {
        "smiles":       "FC(F)(F)C(F)CCCl",
        "connectivity": "FC(F)(F)C(F)CCCl",
        "inchikey":     "BSOMIPKMNNZUQC-UHFFFAOYSA-N",
        "inchi":        "InChI=1S/C4H5ClF4/c5-2-1-3(6)4(7,8)9/h3H,1-2H2",
        "reason":       "PubChem이 R-243fa CID(10000) 반환. CID=54443433 기준 수동 입력.",
    },

    # ── pubchem_fetcher 이름 오류 수정 ───────────────────────────────────────
    # R-1122 = 1-chloro-2,2-difluoroethylene (CHCl=CF2, C2HClF2)
    # pubchem_fetcher에 R-1112a 구조명이 잘못 매핑되어 있었음
    "R-1122": {
        "smiles":       "FC(F)=CCl",
        "connectivity": "FC(F)=CCl",
        "inchikey":     "HTHNTJCVPNKCPZ-UHFFFAOYSA-N",
        "inchi":        "InChI=1S/C2HClF2/c3-1-2(4)5/h1H",
        "reason":       "pubchem_fetcher 이름 오류(R-1112a 구조 반환). R-1122=CHCl=CF2(C2HClF2).",
    },

    # R-1232xf = 1,2-dichloro-3,3,3-trifluoroprop-1-ene (CHCl=CCl-CF3, C3HCl2F3)
    # pubchem_fetcher가 R-1233zd 구조("1-chloro-3,3,3-trifluoropropene") 반환
    "R-1232xf": {
        "smiles":       "ClC(=CCl)C(F)(F)F",
        "connectivity": "ClC(=CCl)C(F)(F)F",
        "inchikey":     "ZHJBJVPTRJNNIK-UHFFFAOYSA-N",
        "inchi":        "InChI=1S/C3HCl2F3/c4-1-2(5)3(6,7)8/h1H",
        "reason":       "pubchem_fetcher가 R-1233zd 구조 반환. R-1232xf=CHCl=CClCF3(C3HCl2F3).",
    },

    # R-123a = 1,2-dichloro-1,1,2-trifluoroethane (CClF2-CHClF, C2HCl2F3)
    # pubchem_fetcher에 R-124 구조명("1-Chloro-1,2,2,2-tetrafluoroethane")이 잘못 매핑
    "R-123a": {
        "smiles":       "FC(Cl)C(F)(F)Cl",
        "connectivity": "FC(Cl)C(F)(F)Cl",
        "inchikey":     "YMRMDGSNYHCUCL-UHFFFAOYSA-N",
        "inchi":        "InChI=1S/C2HCl2F3/c3-1(5)2(4,6)7/h1H",
        "reason":       "pubchem_fetcher가 R-124 구조 반환. R-123a=CClF2-CHClF(C2HCl2F3).",
    },
}


# 구조 미확인 또는 PubChem 데이터 신뢰 불가 → 파이프라인 실행 후 valid=False 강제 적용
INVALID_COMPOUNDS: dict = {
    "R-1354myfz": "SMILES 미확인 - R-1336mzz(Z) 구조가 잘못 할당됨. 올바른 구조 재조사 필요.",
}


def get_manual_smiles(identifier: str) -> Optional[dict]:
    """
    수동 입력 SMILES 반환.
    해당 항목 없으면 None 반환.

    Returns
    -------
    dict with 'smiles', 'connectivity', 'inchikey', 'inchi', 'reason'  또는  None
    """
    return MANUAL_SMILES.get(identifier)


def get_invalid_reason(identifier: str) -> Optional[str]:
    """
    INVALID_COMPOUNDS에 등록된 경우 invalid 사유 문자열 반환, 없으면 None.
    """
    return INVALID_COMPOUNDS.get(identifier)
