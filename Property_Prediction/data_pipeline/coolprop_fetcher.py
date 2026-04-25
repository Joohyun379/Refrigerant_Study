"""
CoolProp 기반 열역학 물성 수집
- 임계온도 Tc [K]
- 임계압력 Pc [MPa]
- 이심인자 ω [-]
"""

import CoolProp
import CoolProp.CoolProp as CP
import logging

logger = logging.getLogger(__name__)

# 냉매 이름 → CoolProp 내부 이름 매핑
COOLPROP_NAME_MAP = {
    # ── 기존 냉매 ──────────────────────────────────────────────────────────
    "R-22":       "R22",
    "R-32":       "R32",
    "R-40":       "R40",
    "R-41":       "R41",
    "R-125":      "R125",
    "R-134a":     "R134a",
    "R-143a":     "R143a",
    "R-152a":     "R152A",
    "R-161":      "R161",
    "R-227ea":    "R227EA",
    "R-236ea":    "R236EA",
    "R-236fa":    "R236FA",
    "R-245ca":    "R245ca",
    "R-245fa":    "R245fa",
    "R-290":      "Propane",
    "R-600":      "Butane",
    "R-600a":     "IsoButane",
    "R-717":      "Ammonia",
    "R-718":      "Water",
    "R-744":      "CarbonDioxide",
    "R-365mfc":   "R365MFC",
    # ── HFO ────────────────────────────────────────────────────────────────
    "R-1233zd(E)": "R1233zd(E)",
    "R-1234yf":    "R1234yf",
    "R-1234ze":    "R1234ze(E)",
    "R-1234ze(E)": "R1234ze(E)",
    "R-1234ze(Z)": "R1234ze(Z)",
    "R-1243zf":    "R1243zf",
    # ── 완전 불소화 (반례) ──────────────────────────────────────────────────
    "R-14":       "R14",
    "R-116":      "R116",
    "R-218":      "R218",
    "RC318":      "RC318",
    # ── 자연 냉매 / 탄화수소 ────────────────────────────────────────────────
    "Methane":    "Methane",
    "Ethane":     "Ethane",
    "Ethylene":   "Ethylene",
    "Propane":    "Propane",
    "Propylene":  "Propylene",
    "Pentane":    "Pentane",
    "Isopentane": "Isopentane",
    "Neopentane": "Neopentane",
    "1-Butene":       "1-Butene",
    "cis-2-Butene":   "cis-2-Butene",
    "trans-2-Butene": "trans-2-Butene",
    # ── HCFC 레거시 ────────────────────────────────────────────────────────
    "R-11":    "R11",
    "R-12":    "R12",
    "R-13":    "R13",
    "R-21":    "R21",
    "R-113":   "R113",
    "R-114":   "R114",
    "R-115":   "R115",
    "R-123":   "R123",
    "R-124":   "R124",
    "R-141b":  "R141b",
    "R-142b":  "R142b",
    # ── HFC 추가 ────────────────────────────────────────────────────────────
    "R-13I1":        "R13I1",
    "R-1336mzz(E)":  "R1336mzz(E)",
    # ── 기타 소형 냉매 ──────────────────────────────────────────────────────
    "SulfurDioxide": "SulfurDioxide",
    "DimethylEther": "DimethylEther",
    "CycloPropane":  "CycloPropane",
    # ── 반례: Tc 너무 낮음 ──────────────────────────────────────────────────
    "CarbonMonoxide": "CarbonMonoxide",
    "ParaHydrogen":   "ParaHydrogen",
    # ── 반례: Tc 너무 높음 (방향족/알케인은 식별자=CoolProp명 동일) ─────────
    "EthylBenzene": "EthylBenzene",
    "o-Xylene":     "o-Xylene",
    "m-Xylene":     "m-Xylene",
    "p-Xylene":     "p-Xylene",
    "Cyclopentane": "Cyclopentane",
    "Cyclohexane":  "CycloHexane",
    # ── 반례: 실록산 대분자 ──────────────────────────────────────────────────
    "MM": "MM", "MDM": "MDM", "MD2M": "MD2M",
    "MD3M": "MD3M", "MD4M": "MD4M",
    "D4": "D4", "D5": "D5", "D6": "D6",
    # ── R-1336mzz(Z): CoolProp 미지원 ──────────────────────────────────────
    # "R-1336mzz": 물성값 직접 확인 후 입력 필요
    # ── 수소결합 알코올/산 (CoolProp 지원 항목만) ─────────────────────────
    "Methanol":   "Methanol",
    "Ethanol":    "Ethanol",
    "Acetone":    "Acetone",
    # 1-Propanol, 2-Propanol, 1-Butanol, AceticAcid: CoolProp 미지원 → NIST fallback
    # ── 추가 방향족 ──────────────────────────────────────────────────────
    "Benzene":    "Benzene",
    "Toluene":    "Toluene",
    # Styrene, Naphthalene: CoolProp 미지원 → NIST fallback
    # ── 정례2/반례2: CoolProp 지원 항목 ─────────────────────────────────────
    "NitrousOxide":    "NitrousOxide",
    "HydrogenSulfide": "HydrogenSulfide",
    "CarbonylSulfide": "CarbonylSulfide",
    "Propyne":         "Propyne",
    "IsoButene":       "IsoButene",
    "DiethylEther":    "DiethylEther",
    "DimethylCarbonate": "DimethylCarbonate",
    "Dichloroethane":  "Dichloroethane",
    # 나머지 신규 화합물: CoolProp 미지원 → NIST fallback 자동 적용
    # (R-1114, R-1132a, R-1123, R-1141, R-1113, R-13B1, R-12B1, R-22B1,
    #  Acetylene, 1-Butyne, 2-Butyne, R-10, R-20, R-30, Chloroethane,
    #  VinylideneChloride, Trichloroethylene, Bromomethane, Dibromomethane,
    #  Iodomethane, 1,3-Butadiene, Isoprene, Cyclobutane, Cyclopentene,
    #  Fluorobenzene, Chlorobenzene, Bromobenzene, Hexafluorobenzene,
    #  2-Methylpentane~2,3-Dimethylbutane, Methylcyclopentane, Methylcyclohexane,
    #  EthyleneOxide, PropyleneOxide, 1-Pentanol, EthyleneGlycol, Tridecane)
    # ── n-알케인 C6~C12 ───────────────────────────────────────────────────
    "Hexane":    "Hexane",
    "Heptane":   "Heptane",
    "Octane":    "Octane",
    "Nonane":    "Nonane",
    "Decane":    "Decane",
    "Undecane":  "Undecane",
    "Dodecane":  "Dodecane",
    # ── 희귀 기체 (Tc 매우 낮음) ─────────────────────────────────────────
    "Helium":    "Helium",
    "Neon":      "Neon",
    "Hydrogen":  "Hydrogen",
    "Deuterium": "Deuterium",
    "Nitrogen":  "Nitrogen",
    "Oxygen":    "Oxygen",
    "Argon":     "Argon",
    "Krypton":   "Krypton",
    # ── 정례3: 추가 냉매 후보 ────────────────────────────────────────────
    "SulfurHexafluoride": "SulfurHexafluoride",
    "Xenon":              "Xenon",
    "HydrogenChloride":   "HydrogenChloride",
    "R-245cb":    "R245CB",
    "R-143":      "R143",
    "R-152":      "R152",
    # ── 반례3: 추가 탄화수소 (CoolProp 지원) ────────────────────────────
    "Tetradecane":  "Tetradecane",
    "Hexadecane":   "Hexadecane",
    "1-Butene":     "1-Butene",    # 이미 있음 (harmless dup)
    "1-Pentene":    "1-Pentene",
    "Cycloheptane": "Cycloheptane",
    "Cyclooctane":  "Cyclooctane",
    # ── 반례4: 알코올 추가 (CoolProp 지원) ──────────────────────────────
    "1-Hexanol":    "1-Hexanol",
    "1-Octanol":    "1-Octanol",
    "2-Butanol":    "2-Butanol",
    "Cyclohexanol": "Cyclohexanol",
    # ── 반례4: 에스터 (CoolProp 지원) ───────────────────────────────────
    "MethylOleate":     "MethylOleate",
    "MethylPalmitate":  "MethylPalmitate",
    "MethylStearate":   "MethylStearate",
    "MethylLinoleate":  "MethylLinoleate",
    "MethylLinolenate": "MethylLinolenate",
    # ── 반례5: 케톤·알데히드 (CoolProp 지원) ────────────────────────────
    "Acetaldehyde":        "Acetaldehyde",
    "MethylEthylKetone":   "MethylEthylKetone",
    # ── 반례5: 에테르 추가 ──────────────────────────────────────────────
    "THF":   "THF",
    "Furan": "Furan",
    # ── 반례5: 기타 ─────────────────────────────────────────────────────
    "Acetonitrile": "Acetonitrile",
    "Trimethylamine": "Trimethylamine",
    "CarbonDisulfide": "CarbonDisulfide",
    "Thiophene": "Thiophene",
    "Nitromethane": "Nitromethane",
    # ── 반례6: n-알케인 연장 ──────────────────────────────────────────────
    "Pentadecane": "n-Pentadecane",
    # ── 반례6: 분지형 알케인 (CoolProp 지원) ──────────────────────────────
    "2-MethylHexane":        "2-Methylhexane",
    "3-MethylHexane":        "3-Methylhexane",
    "2,2-DimethylPentane":   "2,2-Dimethylpentane",
    "2,3-DimethylPentane":   "2,3-Dimethylpentane",
    "2,4-DimethylPentane":   "2,4-Dimethylpentane",
    "3,3-DimethylPentane":   "3,3-Dimethylpentane",
    "2-MethylHeptane":       "2-Methylheptane",
    "3-MethylHeptane":       "3-Methylheptane",
    "4-MethylHeptane":       "4-Methylheptane",
    "2,5-DimethylHexane":    "2,5-Dimethylhexane",
    "2,2,4-TrimethylPentane":"2,2,4-Trimethylpentane",
    "2,3,4-TrimethylPentane":"2,3,4-Trimethylpentane",
    "2,2,3-TrimethylButane": "2,2,3-Trimethylbutane",
}


def get_coolprop_properties(identifier: str) -> dict:
    """
    CoolProp에서 Tc, Pc, ω 조회

    Parameters
    ----------
    identifier : 냉매 이름 (COOLPROP_NAME_MAP 키 또는 CoolProp 직접 이름)

    Returns
    -------
    dict with Tc_K, Pc_MPa, omega (없으면 None)
    """
    cp_name = COOLPROP_NAME_MAP.get(identifier, identifier)

    try:
        state = CoolProp.AbstractState("HEOS", cp_name)
        tc    = CP.PropsSI("Tcrit", cp_name)
        pc    = CP.PropsSI("Pcrit", cp_name) / 1e6   # Pa → MPa
        omega = state.acentric_factor()

        logger.info(f"[{identifier}] Tc={tc:.2f} K  Pc={pc:.4f} MPa  ω={omega:.4f}")
        return {
            "Tc_K":   round(tc, 4),
            "Pc_MPa": round(pc, 6),
            "omega":  round(omega, 6),
        }

    except Exception as e:
        logger.warning(f"[{identifier}] CoolProp 조회 실패 ({cp_name}): {e}")
        return {"Tc_K": None, "Pc_MPa": None, "omega": None}
