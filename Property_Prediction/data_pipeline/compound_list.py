"""
냉매 물성예측 모델 학습용 화합물 목록

설계 기준
----------
정례 (label=1):  C1~C3 / 적절한 불소 함량(1~5 F) / 이중결합 포함 / 높은 분자 대칭성
반례 (label=0):  C4~C5 / F 없음 또는 완전 불소화 / 이중결합 없음 / 낮은 분자 대칭성

각 그룹은 한 가지 기준에 집중하여 설계하되,
경계값(borderline) 화합물을 포함해 모델이 연속적인 구조-물성 관계를 학습할 수 있게 함.

다양성 축
----------
할로겐  : F / Cl / Br / I 함유 분자 전반
결합    : 단일(σ) / 이중(π) / 삼중(π²) / 방향족 / 고리형
탄소수  : C1 ~ C14 + 무기 (N, S, O 포함)
"""

# ──────────────────────────────────────────────────────────────────────────────
# 정례 (label=1) : 구조적으로 냉매에 유리한 방향
# ──────────────────────────────────────────────────────────────────────────────

POSITIVE = {

    # ① C1, 적절한 불소 함량, 높은 대칭성
    "C1_moderate_F": [
        "R-41",    # CH3F          — 불소 1개, 경량
        "R-32",    # CH2F2         — 불소 2개, 대칭, 대표 냉매
        "R-23",    # CHF3          — 불소 3개, 대칭
        "R-40",    # CH3Cl         — 할로겐 1개 (비불소 기준점)
    ],

    # ② C2, 이중결합 + 불소 (HFO 계열 C2)
    "C2_doublebond_F": [
        "Ethylene",  # CH2=CH2     — 불소 없으나 이중결합 기준점 (C2)
    ],

    # ③ C2, 포화 + 적절한 불소, 대칭성
    "C2_saturated_F": [
        "R-161",   # CH3CH2F       — 불소 1개
        "R-152a",  # CH3CHF2       — 불소 2개
        "R-143a",  # CF3CH3        — 불소 3개
        "R-134a",  # CF3CH2F       — 불소 4개, 대표 냉매
        "R-125",   # CF3CHF2       — 불소 5개
    ],

    # ④ C3, 이중결합 + 불소 (HFO 계열 C3) — 핵심 정례 그룹
    "C3_doublebond_F": [
        "Propylene",      # CH2=CHCH3         — 불소 없는 기준점 (C3)
        "R-1243zf",       # CF3CH=CH2         — 불소 3개
        "R-1234yf",       # CF3CF=CH2         — 불소 4개, 차세대 냉매
        "R-1234ze(E)",    # CF3CH=CHF         — 불소 4개, 대칭
        "R-1234ze(Z)",    # CF3CH=CHF (Z형)   — 불소 4개
        "R-1233zd(E)",    # CF3CH=CHCl        — 혼합 할로겐
    ],

    # ⑤ C3, 포화 + 불소 + 높은 대칭성
    "C3_saturated_symmetric_F": [
        "R-245ca",  # CH2FCF2CHF2   — 불소 4개
        "R-236ea",  # CF3CHFCHF2    — 불소 5개
        "R-236fa",  # CF3CH2CF3     — 불소 6개, 좌우 대칭 ★
        "R-227ea",  # CF3CHFCF3     — 불소 7개, 좌우 대칭 ★
    ],

    # ⑥ 소형 무기/자연 냉매 (높은 대칭성)
    "small_symmetric_inorganic": [
        "R-744",   # CO2  — 선형 대칭
        "R-717",   # NH3  — 소형
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# 반례 (label=0) : 구조적으로 냉매에 불리한 방향
# ──────────────────────────────────────────────────────────────────────────────

NEGATIVE = {

    # ① C4~C5, 불소 없음, 이중결합 없음 (포화 탄화수소)
    "C4C5_noF_saturated": [
        "R-600",    # n-Butane
        "R-600a",   # Isobutane
        "Pentane",
        "Isopentane",
        "Neopentane",
    ],

    # ② C4~C5, 이중결합 있으나 불소 없음
    "C4C5_doublebond_noF": [
        "1-Butene",
        "cis-2-Butene",
        "trans-2-Butene",
    ],

    # ③ C4, 불소 있으나 비대칭 (불소 위치 비대칭)
    "C4_asymmetric_F": [
        "R-365mfc",   # CF3CH2CF2CH3 — C4, 비대칭
    ],

    # ④ 완전 불소화 (과다 불소, 낮은 반응성)
    "fully_fluorinated": [
        "R-14",    # CF4       — C1 완전 불소화
        "R-116",   # C2F6      — C2 완전 불소화
        "R-218",   # C3F8      — C3 완전 불소화
        "RC318",   # c-C4F8    — C4 고리형 완전 불소화
    ],

    # ⑤ C1~C3, 불소 없음, 이중결합 없음 (순수 탄화수소)
    "C1C3_noF_saturated": [
        "Methane",
        "Ethane",
        "Propane",
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# 정례 확장 (label=1) : HCFC 레거시 + HFC 추가 + 기타 소형 냉매
# ──────────────────────────────────────────────────────────────────────────────

POSITIVE_EXTENDED = {

    # ① HCFC 레거시 (역사적 냉매, 임계 물성 범위 내 — 오존 파괴로 퇴출됐으나 기준점)
    "HCFC": [
        "R-11",    # CCl3F
        "R-12",    # CCl2F2         — 가장 널리 쓰인 냉매
        "R-13",    # CClF3
        "R-21",    # CHCl2F
        "R-113",   # CCl2FCClF2
        "R-114",   # CClF2CClF2     — 대칭
        "R-115",   # CClF2CF3
        "R-123",   # CHCl2CF3       — R-11 대체재
        "R-124",   # CHClFCF3       — R-114 대체재
        "R-141b",  # CH3CCl2F
        "R-142b",  # CH3CClF2
    ],

    # ② HFC 추가 (기존 목록 미포함)
    "HFC_extended2": [
        "R-22",           # CHClF2           — 가장 많이 쓰인 HCFC
        "R-245fa",        # CF3CH2CHF2       — 단열 발포제 겸용
        "R-13I1",         # CF3I             — 저GWP 소화제 겸용
        "R-1336mzz(E)",   # (E)-HFO          — Z형과 쌍
    ],

    # ③ 기타 소형 냉매 후보 (Tc 200~500 K 범위)
    "misc_small_refrigerant": [
        "SulfurDioxide",  # SO2  — 역사적 냉매 (독성으로 퇴출), Tc=430.6 K
        "DimethylEther",  # DME — Tc=400.4 K, 친환경 대안 연구 중
        "CycloPropane",   # C3H6 고리형 — 대칭, Tc=398.7 K
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# 반례 확장 (label=0) : Tc 범위 이탈 / 수소결합 / 대분자
# ──────────────────────────────────────────────────────────────────────────────

NEGATIVE_EXTENDED = {

    # ① Tc 너무 낮음 (< 210 K) — 상온 액화 불가
    "Tc_too_low": [
        "Helium",         # Tc=5.2 K
        "Neon",           # Tc=44.4 K
        "Hydrogen",       # Tc=33.1 K
        "ParaHydrogen",   # Tc=32.9 K
        "Deuterium",      # Tc=38.3 K
        "Nitrogen",       # Tc=126.2 K
        "Oxygen",         # Tc=154.6 K
        "Fluorine",       # Tc=144.4 K
        "Argon",          # Tc=150.7 K
        "CarbonMonoxide", # Tc=132.9 K
        "Krypton",        # Tc=209.5 K  (경계값)
    ],

    # ② Tc 너무 높음 — n-알케인 (C6~C12)
    "Tc_too_high_nalkane": [
        "Hexane",    # Tc=507.8 K
        "Heptane",   # Tc=541.2 K
        "Octane",    # Tc=568.7 K
        "Nonane",    # Tc=594.5 K
        "Decane",    # Tc=617.7 K
        "Undecane",  # Tc=638.8 K
        "Dodecane",  # Tc=658.1 K
    ],

    # ③ Tc 너무 높음 — 방향족
    "Tc_too_high_aromatic": [
        "Benzene",      # Tc=562.0 K
        "Toluene",      # Tc=591.7 K
        "EthylBenzene", # Tc=617.1 K
        "o-Xylene",     # Tc=630.3 K
        "m-Xylene",     # Tc=616.9 K
        "p-Xylene",     # Tc=616.2 K
    ],

    # ④ Tc 너무 높음 — 고리형 탄화수소
    "Tc_too_high_cyclic": [
        "Cyclopentane",  # Tc=511.7 K
        "Cyclohexane",   # Tc=553.6 K
        "Water",         # Tc=647.1 K  (극단적 수소결합 + 고Tc)
    ],

    # ⑤ Tc 너무 높음 + 대분자 — 실록산 (MW 150~450)
    "large_molecule_siloxane": [
        "MM",    # 헥사메틸다이실록세인,       MW=162,  Tc=518.7 K
        "MDM",   # 옥타메틸트라이실록세인,     MW=236,  Tc=565.4 K
        "MD2M",  # 데카메틸테트라실록세인,     MW=310,  Tc=599.4 K
        "MD3M",  # 도데카메틸펜타실록세인,     MW=384,  Tc=628.0 K
        "MD4M",  # 테트라데카메틸헥사실록세인, MW=458,  Tc=653.2 K
        "D4",    # 옥타메틸사이클로테트라실록세인, MW=296, Tc=586.5 K
        "D5",    # 데카메틸사이클로펜타실록세인,  MW=370, Tc=618.3 K
        "D6",    # 도데카메틸사이클로헥사실록세인, MW=444, Tc=645.8 K
    ],

    # ⑥ 수소결합 물질 (비정상적 상거동, 냉매 부적합)
    "H_bonding": [
        "Methanol",    # Tc=513.4 K, 강한 수소결합
        "Ethanol",     # Tc=514.7 K, 강한 수소결합
        "1-Propanol",  # Tc=536.9 K, 수소결합 알코올
        "2-Propanol",  # Tc=508.3 K, 수소결합 알코올
        "1-Butanol",   # Tc=563.0 K, 수소결합 알코올
        "AceticAcid",  # Tc=591.9 K, 수소결합 산
    ],

    # ⑦ 수소결합 케톤 (극성 + 비정상 상거동)
    "H_bonding_ketone": [
        "Acetone",     # Tc=508.1 K, 쌍극자 + 약한 H-bond
    ],

    # ⑧ Tc 너무 높음 — 추가 방향족
    "Tc_too_high_aromatic2": [
        "Styrene",     # Tc=635.0 K
        "Naphthalene", # Tc=748.4 K, 다환 방향족
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# 통합 리스트 생성 (identifier, label, group 포함)
# ──────────────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────
# 정례 확장2 (label=1) : 할로겐 다양성(Br/I) + C2 HFO + 극성 무기 소형
# ──────────────────────────────────────────────────────────────────────────────

POSITIVE_EXTENDED2 = {

    # ① C2 이중결합 불소화 에틸렌 계열 (C2 HFO — 현재 누락)
    #    결합 다양성: CH2=CF2 ~ CF2=CF2 (F 수 1→4), Cl+F 혼합 포함
    "C2_HFO": [
        "R-1114",   # CF2=CF2   Tc=306.4 K — C2 완전 불소화 이중결합
        "R-1132a",  # CH2=CF2   Tc=302.8 K — 비대칭 불화 에틸렌
        "R-1123",   # CHF=CF2   Tc=330.7 K — 3F 이중결합
        "R-1141",   # CH2=CHF   Tc=327.9 K — 최소 불화 에틸렌
        "R-1113",   # CClF=CF2  Tc=378.6 K — Cl+F 혼합 이중결합
    ],

    # ② C1~C2 Br+F 할로겐화 (할론 계열 — Br 원소 다양성)
    "C1C2_BrF": [
        "R-13B1",   # CBrF3     Tc=340.1 K — Br+F 대칭 C1
        "R-12B1",   # CBrClF2   Tc=426.2 K — Br+Cl+F 혼합
        "R-22B1",   # CHBrF2    Tc=412.8 K — Br+F C1 비대칭
    ],

    # ③ 소형 극성 무기 냉매 (S, N 원소 다양성)
    "small_polar_inorganic": [
        "NitrousOxide",    # N2O  Tc=309.5 K — 선형 대칭, N 포함
        "HydrogenSulfide", # H2S  Tc=373.1 K — 소형 극성, S 포함
        "CarbonylSulfide", # OCS  Tc=378.8 K — 선형, C=O+S
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# 반례 확장2 (label=0) : 삼중결합 / 순수Cl / Br·I / 불포화C4-C5 / 할로방향족 /
#                        분지형알케인 / 에테르 / 고리형 / H-결합2
# ──────────────────────────────────────────────────────────────────────────────

NEGATIVE_EXTENDED2 = {

    # ① 삼중결합 알카인 (반응성/불안정, 구조 다양성 확보)
    "triple_bond_alkyne": [
        "Acetylene",  # C2H2    Tc=308.3 K — 삼중결합 기준점, 폭발성
        "Propyne",    # C3H4    Tc=402.7 K — 메틸아세틸렌
        "1-Butyne",   # C4H6    Tc=440.0 K — 말단 삼중결합 C4
        "2-Butyne",   # C4H6    Tc=488.7 K — 내부 삼중결합 C4
    ],

    # ② C1~C2 완전/고도 염소화 (불소 없음, Tc 높음)
    "C1C2_Cl_noF": [
        "R-10",           # CCl4      Tc=556.6 K — 완전 염소화 C1
        "R-20",           # CHCl3     Tc=536.4 K — 클로로폼 C1
        "R-30",           # CH2Cl2    Tc=510.0 K — 다이클로로메탄
        "Chloroethane",   # C2H5Cl    Tc=460.3 K — R-160, 단일Cl C2
        "Dichloroethane", # C2H4Cl2   Tc=561.6 K — 1,2-이염화에탄
    ],

    # ③ C2 Cl 계열 불포화 (이중결합+Cl, 불소 없음)
    "C2_Cl_unsaturated": [
        "VinylideneChloride",  # CH2=CCl2   Tc=490.2 K — 1,1-이염화에틸렌
        # "Trichloroethylene" 제거 — R-1120과 동일 구조 (중복)
    ],

    # ④ C1~C2 Br·I 할로겐화 (무불소 무거운 할로겐)
    "C1C2_Br_I": [
        "Bromomethane",   # CH3Br   Tc=467.0 K — R-40B, 단일Br
        "Iodomethane",    # CH3I    Tc=528.0 K — 요오드화메탄
    ],

    # ⑤ C4~C5 불포화 (이중결합 있지만 C4+, 불소 없음)
    "C4C5_unsaturated_noF": [
        "IsoButene",     # C4H8   Tc=418.1 K — 이소뷰틸렌
        "1,3-Butadiene", # C4H6   Tc=425.4 K — 공액 이중결합, 반응성
        "Isoprene",      # C5H8   Tc=484.0 K — C5 공액 이중결합
        "Cyclobutane",   # C4H8   Tc=459.9 K — C4 고리형
        "Cyclopentene",  # C5H8   Tc=506.5 K — C5 고리형 불포화
    ],

    # ⑥ 할로겐화 방향족 (방향족 + 다양한 할로겐, Tc 높음)
    "halogenated_aromatic": [
        "Fluorobenzene",      # C6H5F   Tc=560.1 K — F-방향족
        "Chlorobenzene",      # C6H5Cl  Tc=632.4 K — Cl-방향족
        "Bromobenzene",       # C6H5Br  Tc=670.7 K — Br-방향족
        "Hexafluorobenzene",  # C6F6    Tc=516.7 K — 완전 F-방향족
    ],

    # ⑦ 분지형 C6 알케인 (Tc 높음 + 비대칭)
    "branched_C6_alkane": [
        "2-Methylpentane",    # C6H14  Tc=497.7 K
        "3-Methylpentane",    # C6H14  Tc=504.6 K
        "2,2-Dimethylbutane", # C6H14  Tc=489.1 K — 네오헥세인
        "2,3-Dimethylbutane", # C6H14  Tc=500.2 K
    ],

    # ⑧ 에테르·카보네이트 (산소 함유 극성, Tc 중간~높음)
    "ether_carbonate": [
        "DiethylEther",      # C4H10O  Tc=467.9 K
        "DimethylCarbonate", # C3H6O3  Tc=557.0 K
    ],

    # ⑨ Tc 너무 높음 — 알킬 고리형
    "Tc_too_high_alkyl_cyclic": [
        "Methylcyclopentane", # C6H12   Tc=532.7 K
        "Methylcyclohexane",  # C7H14   Tc=572.2 K
    ],

    # ⑩ 에폭사이드 (고리형 에테르, 반응성 높음)
    "epoxide_reactive": [
        "EthyleneOxide",  # C2H4O  Tc=469.1 K — 반응성 에폭사이드
        "PropyleneOxide", # C3H6O  Tc=482.2 K — 프로필렌옥사이드
    ],

    # ⑪ 수소결합2 — 다가 알코올 + 장쇄 알코올
    "H_bonding2": [
        "1-Pentanol",     # C5H12O  Tc=588.1 K — 장쇄 알코올
        "EthyleneGlycol", # C2H6O2  Tc=720.0 K — 다가 알코올, 극단적 H-결합
    ],

    # ⑫ Tc 너무 높음 — n-알케인 연장 (C13)
    "Tc_too_high_nalkane2": [
        "Tridecane",  # C13H28  Tc=675.8 K
    ],
}


# ──────────────────────────────────────────────────────────────────────────────
# 정례 확장3 (label=1) : 추가 HFC 이성질체 / HFO / HFE / 무기 냉매
# ──────────────────────────────────────────────────────────────────────────────

POSITIVE_EXTENDED3 = {

    # ① C3 HFC 이성질체 (더 많은 F 위치 변이)
    "C3_HFC_isomers": [
        "R-245cb",   # CF3CF2CH3   Tc=380.1 K  1,1,1,2,2-pentafluoropropane
        "R-245eb",   # CF3CHFCH2F  Tc=431.6 K  1,1,1,2,3-pentafluoropropane
        "R-236cb",   # CF3CF2CH2F  Tc=412.4 K  1,1,1,2,2,3-hexafluoropropane
        "R-263fb",   # CHF2CH2CH3  Tc=453.6 K  1,1-difluoropropane
        "R-253fb",   # CHF2CH2CHF2 Tc=448.2 K  1,1,3,3-tetrafluoropropane
    ],

    # ② C3 HFO 추가 이성질체 (F 위치·E/Z 변이)
    "C3_HFO_additional": [
        "R-1225ye(E)",  # (E)-CF3CF=CHF  Tc=416.8 K
        "R-1225ye(Z)",  # (Z)-CF3CF=CHF  Tc=394.8 K
        "R-1225zc",     # CF3CH=CF2      Tc=412.4 K  1,1,3,3,3-pentafluoroprop-1-ene
        "R-1224yd(Z)",  # (Z)-CF3CF=CHCl Tc=428.7 K  HCFO
        "R-1233zd(Z)",  # (Z)-CF3CH=CHCl Tc=439.0 K  (Z)-HCFO-1233zd
    ],

    # ③ C4 HFO 추가
    "C4_HFO_additional": [
        "R-1336mzz(Z)",   # (Z)-CF3CH=CHCF3  Tc=444.5 K
    ],

    # ④ HFE (hydrofluoroether) 소형 냉매 후보
    "HFE_small": [
        "HFE-143m",   # CH3OCF3        Tc=377.9 K  methyl trifluoromethyl ether
        "HFE-125",    # CHF2OCF3       Tc=354.5 K
        "HFE-134",    # CHF2OCHF2      Tc=420.3 K  bis(difluoromethyl) ether
        "HFE-245mc",  # CH3OCF2CF3     Tc=406.8 K  methyl pentafluoroethyl ether
        "HFE-245fa2", # CHF2OCH2CF3    Tc=444.9 K
    ],

    # ⑤ 무기·희귀기체 냉매 후보 (Tc 200~400 K, 높은 대칭성)
    "inorganic_refrigerant": [
        "SulfurHexafluoride",  # SF6  Tc=318.7 K  완전 대칭 무기 불소화합물
        "Xenon",               # Xe   Tc=289.7 K  희귀기체 냉매
        "HydrogenChloride",    # HCl  Tc=324.5 K  C1 대칭 무기
    ],

    # ⑥ C2 HFC 추가 이성질체
    "C2_HFC_additional": [
        "R-143",   # CHF2CHF2  Tc=374.2 K  1,1,2,2-tetrafluoroethane
        "R-152",   # CH2FCH2F  Tc=386.4 K  1,2-difluoroethane
    ],

    # ⑦ C1·C2 HCFC 추가
    "C1C2_HCFC_additional": [
        "R-31",    # CH2ClF    Tc=369.3 K  chlorofluoromethane
        "R-133a",  # CF3CH2Cl  Tc=480.2 K  1-chloro-2,2,2-trifluoroethane
        "R-132b",  # CH2ClCHF2 Tc=452.9 K  1-chloro-2,2-difluoroethane
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# 정례 확장4 (label=1) : 추가 혼합할로겐 / 불소화 C4 / 경계값 화합물
# ──────────────────────────────────────────────────────────────────────────────

POSITIVE_EXTENDED4 = {

    # ① C3 HCFC 추가
    "C3_HCFC_additional": [
        "R-243fa",   # CF3CHClCH3    Tc=502.5 K  1-chloro-3,3,3-trifluoropropane
        "R-244fa",   # CF3CH2CH2Cl   Tc=501.5 K  3-chloro-1,1,1-trifluoropropane
        "R-234ab",   # CHF2CHClCF3   Tc=482.5 K
    ],

    # ② C2 추가 혼합할로겐
    "C2_mixed_halogen": [
        "R-123a",    # CF3CHClF      Tc=425.0 K
        "R-132",     # CHFClCHFCl    Tc=470.0 K  1,2-dichloro-1,2-difluoroethane
        "R-141",     # CH2FCHCl2     Tc=481.0 K  1,1-dichloro-2-fluoroethane
    ],

    # ③ C4 대칭 불소화 냉매 후보
    "C4_symmetric_F": [
        "R-1354myfz",  # (Z)-CF3CH=CHCF3  C4 HFO symmetric (= HFO-1354)
        "R-338mccq",   # CF3CF2CHFCHF2    Tc=475.0 K  C4 HFC
    ],

    # ④ 불소화 에테르 추가 (C3+)
    "HFE_extended": [
        "HFE-7000",    # C3F7OCH3  Tc=437.7 K  methyl perfluoropropyl ether
        "HFE-449sl",   # 상용 혼합 전구체
    ],

    # ⑤ 기타 냉매 후보 (문헌 기록 존재)
    "misc_refrigerant_candidate": [
        "R-21",        # Already in list — skip if duplicate check fails
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# 반례 확장3 (label=0) : 추가 알케인 (분지형 C7~C8, n-알케인 C14+, 고리형)
# ──────────────────────────────────────────────────────────────────────────────

NEGATIVE_EXTENDED3 = {

    # ① n-알케인 C14~C16 (Tc 매우 높음, 대분자)
    "Tc_too_high_nalkane3": [
        "Tetradecane",   # C14H30  Tc=693.0 K
        "Pentadecane",   # C15H32  Tc=707.0 K
        "Hexadecane",    # C16H34  Tc=722.0 K
    ],

    # ② 분지형 C7 알케인 (비대칭, Tc 500~520 K)
    "branched_C7_alkane": [
        "2-MethylHexane",     # C7H16  Tc=530.4 K
        "3-MethylHexane",     # C7H16  Tc=535.2 K
        "2,2-DimethylPentane",# C7H16  Tc=520.5 K
        "2,3-DimethylPentane",# C7H16  Tc=537.4 K
        "2,4-DimethylPentane",# C7H16  Tc=519.8 K
        "3,3-DimethylPentane",# C7H16  Tc=536.4 K
        "3-EthylPentane",     # C7H16  Tc=540.6 K
        "2,2,3-TrimethylButane", # C7H16 Tc=531.2 K  triptane
    ],

    # ③ 분지형 C8 알케인 (비대칭, Tc 540~570 K)
    "branched_C8_alkane": [
        "2-MethylHeptane",       # C8H18  Tc=559.7 K
        "3-MethylHeptane",       # C8H18  Tc=563.7 K
        "4-MethylHeptane",       # C8H18  Tc=561.7 K
        "2,5-DimethylHexane",    # C8H18  Tc=550.0 K
        "2,2,4-TrimethylPentane",# C8H18  Tc=543.9 K  isooctane
        "2,3,4-TrimethylPentane",# C8H18  Tc=566.4 K
    ],

    # ④ 추가 고리형 탄화수소 (Tc 높음)
    "Tc_too_high_cyclic2": [
        "Cycloheptane",    # C7H14   Tc=604.2 K
        "Cyclooctane",     # C8H16   Tc=647.2 K
        "Decalin",         # C10H18  Tc=702.3 K  데칼린 (데카하이드로나프탈렌)
    ],

    # ⑤ 직쇄 알켄 C5~C8 (이중결합 있으나 C5+, F 없음)
    "larger_alkene_noF": [
        "1-Pentene",     # C5H10  Tc=464.8 K
        "1-Hexene",      # C6H12  Tc=504.0 K
        "1-Heptene",     # C7H14  Tc=537.3 K
        "1-Octene",      # C8H16  Tc=566.9 K
        "2-Pentene",     # C5H10  Tc=475.0 K (cis/trans 혼합)
        "Cyclohexene",   # C6H10  Tc=560.4 K  고리형 이중결합
    ],

    # ⑥ 완전 불소화 C4~C6 (PFC, 낮은 반응성·높은 GWP)
    "fully_fluorinated_C4C6": [
        "C4F10",        # C4F10  Tc=386.3 K  perfluorobutane (R-3-1-10)
        "C5F12",        # C5F12  Tc=420.6 K  perfluoropentane
        "C6F14",        # C6F14  Tc=448.8 K  perfluorohexane
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# 반례 확장4 (label=0) : 알코올 / 카르복실산 / 에스터
# ──────────────────────────────────────────────────────────────────────────────

NEGATIVE_EXTENDED4 = {

    # ① 장쇄 알코올 (강한 수소결합, Tc 매우 높음)
    "long_chain_alcohol": [
        "1-Hexanol",    # C6H14O  Tc=611.4 K
        "1-Heptanol",   # C7H16O  Tc=631.9 K
        "1-Octanol",    # C8H18O  Tc=652.3 K
        "2-Butanol",    # C4H10O  Tc=536.2 K
        "2-Hexanol",    # C6H14O  Tc=586.2 K
        "Cyclohexanol", # C6H12O  Tc=625.2 K
        "BenzylAlcohol",# C7H8O   Tc=720.2 K  방향족 알코올
        "Phenol",       # C6H6O   Tc=694.3 K  수산화벤젠
    ],

    # ② 다가 알코올 (수소결합 극단)
    "polyol": [
        "Glycerol",          # C3H8O3  Tc=850.0 K  글리세린
        "PropyleneGlycol",   # C3H8O2  Tc=626.0 K  1,2-프로판다이올
        "DiethyleneGlycol",  # C4H10O3 Tc=753.0 K
    ],

    # ③ 카르복실산 (이량체 형성, 수소결합)
    "carboxylic_acid": [
        "PropionicAcid",  # C3H6O2  Tc=600.8 K
        "ButyricAcid",    # C4H8O2  Tc=615.7 K
        "ValericAcid",    # C5H10O2 Tc=651.0 K
        "BenzoicAcid",    # C7H6O2  Tc=751.0 K  방향족 산
        "ForamicAcid",    # CH2O2   Tc=588.0 K  포름산
    ],

    # ④ 에스터 (중간 극성, Tc 높음)
    "ester": [
        "MethylAcetate",    # C3H6O2   Tc=506.6 K
        "EthylAcetate",     # C4H8O2   Tc=523.2 K
        "PropylAcetate",    # C5H10O2  Tc=549.7 K
        "ButylAcetate",     # C6H12O2  Tc=575.4 K
        "EthylPropanoate",  # C5H10O2  Tc=546.0 K
        "MethylButanoate",  # C5H10O2  Tc=554.5 K
        "DiethylCarbonate", # C5H10O3  Tc=576.0 K
    ],

    # ⑤ 지방산 메틸 에스터 (대분자, CoolProp 지원)
    "fatty_acid_ester": [
        "MethylOleate",      # C19H36O2  Tc=782.0 K  (CoolProp: MethylOleate)
        "MethylPalmitate",   # C17H34O2  Tc=755.0 K  (CoolProp: MethylPalmitate)
        "MethylStearate",    # C19H38O2  Tc=775.0 K  (CoolProp: MethylStearate)
        "MethylLinoleate",   # C19H34O2  Tc=799.0 K  (CoolProp: MethylLinoleate)
        "MethylLinolenate",  # C19H32O2  Tc=772.0 K  (CoolProp: MethylLinolenate)
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# 반례 확장5 (label=0) : 케톤 / 알데히드 / 니트릴 / 아민 / 에테르
# ──────────────────────────────────────────────────────────────────────────────

NEGATIVE_EXTENDED5 = {

    # ① 케톤 (쌍극자, 극성 비양성자성 용매)
    "ketone": [
        "MethylEthylKetone",      # C4H8O   Tc=535.5 K  2-butanone (MEK)
        "DiethylKetone",          # C5H10O  Tc=560.9 K  3-pentanone
        "MethylIsobutylKetone",   # C6H12O  Tc=571.4 K  MIBK
        "Cyclohexanone",          # C6H10O  Tc=653.0 K  고리형 케톤
        "Acetophenone",           # C8H8O   Tc=701.0 K  방향족 케톤
        "MethylPropylKetone",     # C5H10O  Tc=561.0 K  2-pentanone
    ],

    # ② 알데히드 (반응성, 산화 용이)
    "aldehyde": [
        "Acetaldehyde",      # C2H4O  Tc=466.0 K  에탄알
        "Propionaldehyde",   # C3H6O  Tc=503.6 K  프로판알
        "Butyraldehyde",     # C4H8O  Tc=537.2 K  부탄알
        "Benzaldehyde",      # C7H6O  Tc=695.0 K  방향족 알데히드
        "Furfural",          # C5H4O2 Tc=670.0 K  푸르푸랄 (헤테로고리)
    ],

    # ③ 니트릴 (극성, 반응성, 높은 Tc)
    "nitrile": [
        "Acetonitrile",    # C2H3N  Tc=545.5 K  아세토니트릴
        "Propionitrile",   # C3H5N  Tc=564.4 K
        "Benzonitrile",    # C7H5N  Tc=699.4 K
        "Acrylonitrile",   # C3H3N  Tc=535.0 K  반응성 이중결합+니트릴
    ],

    # ④ 아민 (염기성, 수소결합, 부식성)
    "amine": [
        "Trimethylamine",   # C3H9N  Tc=433.3 K
        "Triethylamine",    # C6H15N Tc=535.6 K
        "Aniline",          # C6H7N  Tc=698.8 K  방향족 아민
        "Pyridine",         # C5H5N  Tc=619.0 K  헤테로 방향족
        "Morpholine",       # C4H9NO Tc=618.4 K  환형 아민
        "Piperidine",       # C5H11N Tc=594.0 K  포화 환형 아민
        "DimethylAmine",    # C2H7N  Tc=437.2 K
        "DiethylAmine",     # C4H11N Tc=496.6 K
    ],

    # ⑤ 에테르 추가 (비교적 낮은 극성, 그러나 Tc 또는 반응성 문제)
    "ether_additional": [
        "DipropylEther",    # C6H14O  Tc=530.6 K  dipropyl ether
        "DibutylEther",     # C8H18O  Tc=584.2 K  dibutyl ether
        "THF",              # C4H8O   Tc=540.2 K  테트라하이드로퓨란
        "Dioxane",          # C4H8O2  Tc=587.0 K  1,4-다이옥세인
        "Anisole",          # C7H8O   Tc=641.7 K  메톡시벤젠
        "MTBE",             # C5H12O  Tc=497.1 K  메틸 tert-부틸 에테르
    ],

    # ⑥ 황 함유 화합물 (독성, 부식, 냉매 부적합)
    "sulfur_compound": [
        "CarbonDisulfide",  # CS2     Tc=552.0 K  이황화탄소
        "DMSO",             # C2H6OS  Tc=726.0 K  다이메틸설폭사이드
        "DimethylSulfide",  # C2H6S   Tc=503.0 K  다이메틸설파이드
        "Thiophene",        # C4H4S   Tc=579.4 K  방향족 황 헤테로고리
        "Methanethiol",     # CH4S    Tc=469.9 K  메탄싸이올 (악취)
        "DiethylSulfide",   # C4H10S  Tc=557.0 K
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# 반례 확장6 (label=0) : 추가 방향족 / 헤테로고리 / 염소화 C3~C5
# ──────────────────────────────────────────────────────────────────────────────

NEGATIVE_EXTENDED6 = {

    # ① 추가 방향족 (Tc 높음 + 독성/반응성)
    "aromatic_extended": [
        "Cumene",          # C9H12   Tc=631.1 K  이소프로필벤젠
        "Mesitylene",      # C9H12   Tc=637.3 K  1,3,5-트리메틸벤젠
        "Pseudocumene",    # C9H12   Tc=649.1 K  1,2,4-트리메틸벤젠
        "Indene",          # C9H8    Tc=687.0 K  불포화 이환 방향족
        "Tetralin",        # C10H12  Tc=720.0 K  1,2,3,4-테트라하이드로나프탈렌
        "Biphenyl",        # C12H10  Tc=789.3 K  다환 방향족
        "1-MethylNaphthalene",  # C11H10 Tc=772.0 K
    ],

    # ② 헤테로고리 (N·O 포함, 냉매 부적합)
    "heterocyclic": [
        "Furan",            # C4H4O  Tc=490.2 K  산소 헤테로고리
        "Pyrrole",          # C4H5N  Tc=639.7 K  질소 방향족
        "Indole",           # C8H7N  Tc=790.0 K  이환 N-헤테로고리
        "Imidazole",        # C3H4N2 Tc=784.0 K  질소×2 헤테로고리
        "NMethylPyrrolidone",  # C5H9NO Tc=721.7 K  NMP
    ],

    # ③ C3~C5 염소화 알케인 (Cl 함량 높음, F 없음)
    "Cl_alkane_C3C5": [
        "1-Chloropropane",     # C3H7Cl  Tc=503.1 K
        "2-Chloropropane",     # C3H7Cl  Tc=485.1 K
        "1-Chlorobutane",      # C4H9Cl  Tc=539.2 K
        "2-Chlorobutane",      # C4H9Cl  Tc=520.6 K
        "1-Chloropentane",     # C5H11Cl Tc=571.2 K
        "1,2-Dichloropropane", # C3H6Cl2 Tc=578.0 K
        "1,3-Dichloropropane", # C3H6Cl2 Tc=603.0 K
        "1,1,1-Trichloroethane", # C2H3Cl3 Tc=545.0 K  메틸클로로포름
        "1,1,2-Trichloroethane", # C2H3Cl3 Tc=602.0 K
    ],

    # ④ 브롬·요오드 C3~C4 (무거운 할로겐, 냉매 부적합)
    "Br_I_C3C4": [
        "1-Bromopropane",    # C3H7Br  Tc=536.9 K
        "2-Bromopropane",    # C3H7Br  Tc=532.4 K
        "1-Bromobutane",     # C4H9Br  Tc=563.9 K
        "Bromoethane",       # C2H5Br  Tc=503.8 K  R-160B1
        "Chloroiodomethane", # CH2ClI  Tc=572.0 K
    ],

    # ⑤ 불소화 방향족 추가
    "fluorinated_aromatic_add": [
        "1,2-Difluorobenzene",  # C6H4F2  Tc=566.0 K
        "1,3-Difluorobenzene",  # C6H4F2  Tc=558.4 K
        "1,4-Difluorobenzene",  # C6H4F2  Tc=556.0 K
        "Pentafluorobenzene",   # C6HF5   Tc=530.97 K
    ],

    # ⑥ 질소 화합물 (비냉매, 반응성 또는 독성)
    "nitrogen_compound": [
        "Nitromethane",          # CH3NO2   Tc=588.1 K  폭발성
        "Nitroethane",           # C2H5NO2  Tc=593.0 K
        "NNDimethylFormamide",   # C3H7NO   Tc=647.0 K  DMF, 강극성 용매
        "Formamide",             # CH3NO    Tc=771.0 K  수소결합
        "Acetamide",             # C2H5NO   Tc=761.0 K  수소결합
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# 반례 확장7 (label=0) : 더 다양한 유기 화합물 / 반응성 물질 / 특수 케이스
# ──────────────────────────────────────────────────────────────────────────────

NEGATIVE_EXTENDED7 = {

    # ① 더 많은 n-알케인 이성질체 C9~C11 (이미 Tc 높음으로 있지만 더 추가)
    "large_nalkane": [
        "Tridecane",  # 이미 있음—중복방지 로직에서 skip
    ],

    # ② 다환 방향족 (PAH, 발암성·고Tc)
    "polycyclic_aromatic": [
        "Anthracene",     # C14H10  Tc=869.3 K
        "Phenanthrene",   # C14H10  Tc=873.0 K
        "Fluorene",       # C13H10  Tc=826.0 K
        "Acenaphthylene", # C12H8   Tc=803.0 K
    ],

    # ③ 락톤·환형 에스터 (반응성 높음)
    "lactone_cyclic_ester": [
        "GammaButyrolactone",  # C4H6O2  Tc=731.0 K  GBL
        "EpsilonCaprolactone", # C6H10O2 Tc=806.0 K  ε-카프로락톤
    ],

    # ④ 과산화물·반응성 (냉매 부적합)
    "reactive_peroxide": [
        "DiMethylPeroxide",  # C2H6O2  Tc=... 불안정, skip if fail
    ],

    # ⑤ 인·붕소 화합물 (원소 다양성)
    "P_B_compound": [
        "TrimethylPhosphate",  # C3H9O4P  Tc=680.0 K  인산 에스터
        "TrimethylBorate",     # C3H9BO3  Tc=501.0 K  붕산 에스터
    ],

    # ⑥ 실란·실리콘 (Si 원소 다양성, 실록산 외)
    "silane": [
        "Tetramethylsilane",  # C4H12Si  Tc=448.6 K  TMS
        "Hexamethyldisilane", # C6H18Si2 Tc=540.0 K
    ],

    # ⑦ 할로겐화 에테르 (비냉매 용도)
    "halogenated_ether": [
        "Chloromethylmethylether", # C2H5ClO  Tc=490.0 K  클로로메틸메틸에테르
        "Bis2chloroethylether",    # C4H8Cl2O Tc=627.0 K
    ],

    # ⑧ 더 많은 C5 알케인 이성질체
    "C5_alkane_isomers": [
        "Cyclopentane",  # 이미 있음—중복 skip
    ],

    # ⑨ 글리콜 에테르 (고bp, 수소결합)
    "glycol_ether": [
        "EthyleneGlycolMonoethylEther",  # C4H10O2  Tc=569.0 K  셀로솔브
        "EthyleneGlycolMonobutylEther",  # C6H14O2  Tc=633.0 K
        "DiethyleneGlycolMonomethylEther", # C5H12O3 Tc=651.0 K
    ],

    # ⑩ 이황화·이불화 (S-S, F-F 결합)
    "disulfide_difluoride": [
        "DimethylDisulfide",  # C2H6S2  Tc=606.0 K
        "DietylDisulfide",    # C4H10S2 Tc=642.0 K
    ],

    # ⑪ 더 많은 C6 알켄 (불포화 C6, F 없음)
    "C6_alkene": [
        "Cyclohexene",   # 이미 있음
        "2-Hexene",      # C6H12  Tc=513.0 K
        "3-Hexene",      # C6H12  Tc=509.0 K
        "1-MethylCyclopentene",  # C6H10 Tc=542.0 K
    ],

    # ⑫ 불소화 케톤 (낮은 GWP 주장되는 화합물)
    "fluorinated_ketone": [
        "Novec1230",    # C6F12O  Tc=441.8 K  FK-5-1-12 (소화제), 완전불소화케톤
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# 반례 확장8 (label=0) : 추가 다양성 (알킬 방향족, 더 많은 이성질체)
# ──────────────────────────────────────────────────────────────────────────────

NEGATIVE_EXTENDED8 = {

    # ① n-알케인 확장 C5 이성질체 (이미 있는 것 외)
    "C5_isomers": [
        # Pentane, Isopentane, Neopentane 이미 있음
        # 추가 없음
    ],

    # ② C9~C10 알킬 방향족
    "alkyl_aromatic_C9C10": [
        "Propylbenzene",         # C9H12   Tc=638.4 K
        "1,2,3-Trimethylbenzene",# C9H12   Tc=664.5 K
        "Butylbenzene",          # C10H14  Tc=660.5 K
        "Isobutylbenzene",       # C10H14  Tc=650.1 K
        "1-Phenylnaphthalene",   # C16H12  Tc=849.0 K
    ],

    # ③ 더 많은 할로메탄·에탄 유도체
    "halo_C1C2_extended": [
        "Dibromochloromethane",   # CHBrCl2  Tc=603.0 K
        "Iodoform",               # CHI3     Tc=795.0 K  트리요오드메탄
        "1-Iodopropane",          # C3H7I    Tc=578.0 K
        "1-Iodobutane",           # C4H9I    Tc=600.0 K
    ],

    # ④ 퍼플루오로고리형 (완전불소화 고리, 냉매 아님)
    "perfluoro_cyclic": [
        "Perfluorodecalin",       # C10F18  Tc=566.0 K  혈액 대체제
        "PerfluoroMethylCyclohexane",  # C7F14 Tc=485.9 K
    ],

    # ⑤ 폴리올 추가
    "polyol_extended": [
        "1,3-Propanediol",     # C3H8O2  Tc=658.0 K
        "1,4-Butanediol",      # C4H10O2 Tc=724.0 K
        "Erythritol",          # C4H10O4 Tc=902.0 K  (skip if no data)
    ],

    # ⑥ 방향족 할로겐화 추가
    "halogenated_aromatic_add": [
        "2-Chlorotoluene",      # C7H7Cl  Tc=655.0 K
        "4-Chlorotoluene",      # C7H7Cl  Tc=660.0 K
        "Benzotrifluoride",     # C7H5F3  = Trifluorotoluene (중복)
        "1-Bromonaphthalene",   # C10H7Br Tc=824.0 K
        "4-Fluorotoluene",      # C7H7F   Tc=591.2 K
        "4-Chlorofluorobenzene",# C6H4ClF Tc=614.0 K
    ],

    # ⑦ 이소시아네이트·산무수물 (반응성 극단)
    "reactive_isocyanate": [
        "MethylIsocyanate",   # C2H3NO  Tc=503.0 K  맹독성 (보팔 사고)
        "AceticAnhydride",    # C4H6O3  Tc=606.0 K  산무수물
    ],

    # ⑧ 더 많은 에스터 (짧은 chain)
    "short_ester": [
        "MethylFormate",     # C2H4O2  Tc=487.2 K
        "EthylFormate",      # C3H6O2  Tc=508.5 K
        "MethylPropanoate",  # C4H8O2  Tc=530.6 K
        "IsoPropylAcetate",  # C5H10O2 Tc=531.0 K
        "IsoButylAcetate",   # C6H12O2 Tc=561.0 K
    ],

    # ⑨ 알코올 추가 (분지형)
    "branched_alcohol": [
        "2-Methyl-1-Propanol",  # C4H10O  Tc=547.8 K  isobutanol
        "2-Methyl-1-Butanol",   # C5H12O  Tc=565.0 K
        "3-Methyl-1-Butanol",   # C5H12O  Tc=577.2 K  isoamyl alcohol
        "tert-Butanol",         # C4H10O  Tc=506.2 K  tertiary 알코올
    ],

    # ⑩ 이산화물·할로 산화물
    "halo_oxide": [
        "PhosphorylChloride",   # Cl3OP   Tc=602.0 K  POCl3
        "ThionylChloride",      # Cl2OS   Tc=554.0 K  SOCl2
        "SulfurylChloride",     # Cl2O2S  Tc=545.0 K  SO2Cl2
    ],
}


# ──────────────────────────────────────────────────────────────────────────────
# 정례 확장5 (label=1) : 추가 불소화 냉매 후보
# ──────────────────────────────────────────────────────────────────────────────

POSITIVE_EXTENDED5 = {

    # ① C2 이중결합 불소+Cl 추가
    "C2_HFO_Cl_add": [
        "R-1122",    # CF2=CCl2  Tc=428.9 K  1,1-dichloro-2,2-difluoroethylene
        "R-1112a",   # CF2=CCl2  → same? Actually R-1112a = CFCl=CF2  Tc=450K?
        "R-1120",    # CHCl=CCl2  Tc=571K ... 이건 trichloroethylene = Trichloroethylene (이미 있음)
        "R-1130",    # CHCl=CHCl  Tc=544.0 K  1,2-dichloroethylene (trans)
        "R-1130a",   # CHCl=CHCl  Tc=535.0 K  1,2-dichloroethylene (cis)
    ],

    # ② C3 이중결합 추가 (Cl+F 혼합)
    "C3_HFO_ClF_add": [
        "R-1233xf",  # CHCl=CFCF3    Tc=...
        "R-1232xf",  # CHCl=CClCF3   Tc=...
    ],

    # ③ 추가 무기 소형 냉매 후보
    "inorganic_small_add": [
        "Fluorine",           # F2   Tc=144.4 K — 이미 있음 (skip)
        "NitrogenTrifluoride",# NF3  Tc=234.0 K  낮은 GWP 연구 냉매
        "Silane",             # SiH4 Tc=269.7 K  무기 소형
    ],

    # ④ C1 추가 이성질체
    "C1_additional": [
        "R-30B2",    # CH2Br2 = Dibromomethane — 이미 반례에 있음
        "R-20B3",    # CBr3H?
    ],

    # ⑤ CoolProp에 있는 추가 냉매 후보
    "coolprop_additional": [
        "Fluorine",  # 이미 있음
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# 반례 확장9 (label=0) : 추가 유기 화합물 군
# ──────────────────────────────────────────────────────────────────────────────

NEGATIVE_EXTENDED9 = {

    # ① 더 많은 직쇄 알코올 (C2~C12)
    "alcohol_series": [
        "1-Nonanol",     # C9H20O   Tc=671.0 K
        "1-Decanol",     # C10H22O  Tc=687.3 K
        "1-Dodecanol",   # C12H26O  Tc=719.0 K
        "2-Propanol",    # C3H8O    Tc=508.3 K — 이미 있음 (skip)
        "3-Methyl-1-Butanol",  # C5H12O Tc=577.2 K — 이미 있음
    ],

    # ② 더 많은 케톤 이성질체
    "ketone_extended": [
        "2-Heptanone",   # C7H14O  Tc=611.4 K
        "4-Heptanone",   # C7H14O  Tc=602.6 K
        "Benzophenone",  # C13H10O Tc=830.0 K  다이페닐케톤
        "Cyclopentanone",# C5H8O   Tc=624.0 K  5원 고리 케톤
        "Isophorone",    # C9H14O  Tc=715.0 K  불포화 고리 케톤
    ],

    # ③ 더 많은 에스터 (고리형 포함)
    "ester_extended": [
        "EthylLactate",       # C5H10O3  Tc=588.0 K  젖산에틸
        "Caprolactam",        # C6H11NO  Tc=806.0 K  나일론 전구체
        "DimethylPhthalate",  # C10H10O4 Tc=766.0 K
        "DiethylPhthalate",   # C12H14O4 Tc=777.0 K
        "DimethylSuccinate",  # C6H10O4  Tc=660.0 K
    ],

    # ④ 더 많은 아민 (C4+)
    "amine_extended": [
        "Butylamine",      # C4H11N  Tc=531.9 K
        "Dibutylamine",    # C8H19N  Tc=607.5 K
        "Cyclohexylamine", # C6H13N  Tc=615.5 K
        "Quinoline",       # C9H7N   Tc=782.2 K  방향족 N-헤테로고리
        "Isoquinoline",    # C9H7N   Tc=803.0 K
    ],

    # ⑤ 더 많은 방향족 산소 화합물
    "aromatic_oxygen": [
        "Catechol",        # C6H6O2  Tc=820.0 K  1,2-다이하이드록시벤젠
        "Resorcinol",      # C6H6O2  Tc=836.0 K  1,3-다이하이드록시벤젠
        "Guaiacol",        # C7H8O2  Tc=697.0 K  2-메톡시페놀
        "Acetophenol",     # C8H8O2  → p-메톡시아세토페논?
        "Benzophenol",     # C13H10O → Benzophenone (이미 위에)
    ],

    # ⑥ 더 많은 할로겐화 에탄 (C2 Cl/Br)
    "halo_ethane_extended": [
        "1,1-Dichloroethane",  # C2H4Cl2  Tc=523.0 K  vinylidene chloride 아님
        "1,1,1,2-Tetrachloroethane",  # C2H2Cl4 Tc=624.0 K
        "Hexachloroethane",    # C2Cl6    Tc=695.0 K  완전 염소화 C2
        "1,2-Dibromoethane",   # C2H4Br2  Tc=650.2 K  이브로모에탄
    ],

    # ⑦ 인산 에스터·가소제
    "phosphate_ester": [
        "TripropylPhosphate",  # C9H21O4P  Tc=750.0 K
        "TributylPhosphate",   # C12H27O4P Tc=800.0 K  TBP
        "TriethylPhosphate",   # C6H15O4P  Tc=680.0 K
    ],

    # ⑧ 글리콜·폴리올 추가
    "glycol_extended": [
        "TriethyleneGlycol",   # C6H14O4  Tc=769.5 K
        "TetraethyleneGlycol", # C8H18O5  Tc=795.0 K
        "Sorbitol",            # C6H14O6  Tc=950.0 K  (데이터 없을 수 있음)
    ],

    # ⑨ 불포화 C3 (F 없음, 반응성)
    "C3_unsaturated_noF": [
        "Allyl",           # CH2=CHCH2 (not stable)
        "Acrolein",        # CH2=CHCHO    Tc=506.0 K  아크롤레인 (반응성)
        "PropargylAlcohol",# HC≡CCH2OH    Tc=507.0 K  프로파길 알코올
    ],

    # ⑩ 더 많은 방향족 다환
    "PAH_extended": [
        "Pyrene",          # C16H10  Tc=936.0 K  피렌
        "Chrysene",        # C18H12  Tc=979.0 K  크리센 (데이터 없을 수 있음)
        "Acridine",        # C13H9N  Tc=900.0 K  N-헤테로 PAH
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# 반례 확장10 (label=0) : 추가 C5~C8 포화 이성질체, 기타 특수 분자
# ──────────────────────────────────────────────────────────────────────────────

NEGATIVE_EXTENDED11 = {

    # ① 더 많은 C7~C9 분지 알케인
    "C7C9_branched_add": [
        "2,2,3-TrimethylPentane",  # C8H18  Tc=563.5 K
        "2,2,3,3-TetramethylButane", # C8H18 Tc=567.8 K  hexamethylethane
        "3-EthylHexane",           # C8H18  Tc=565.5 K
        "2,3-DimethylHexane",      # C8H18  Tc=563.4 K
        "2,4-DimethylHexane",      # C8H18  Tc=553.5 K
        "3,4-DimethylHexane",      # C8H18  Tc=568.8 K
        "3-EthylMethylPentane",    # 2,3-dimethylpentane duplicate? skip
        "2,2,5-TrimethylHexane",   # C9H20  Tc=568.1 K
    ],

    # ② 더 많은 에스터 (포르메이트, 아크릴레이트)
    "ester_add2": [
        "MethylAcrylate",      # C4H6O2  Tc=536.0 K  아크릴산메틸 (반응성)
        "EthylAcrylate",       # C5H8O2  Tc=553.0 K
        "MethylMethacrylate",  # C5H8O2  Tc=566.0 K  MMA
        "VinylAcetate",        # C4H6O2  Tc=519.1 K  비닐아세테이트
        "DimethylOxalate",     # C4H6O4  Tc=632.0 K
        "EthylBenzoate",       # C9H10O2 Tc=700.0 K
        "MethylBenzoate",      # C8H8O2  Tc=693.0 K
    ],

    # ③ 더 많은 방향족 Cl 화합물
    "aromatic_Cl_add": [
        "1,2-Dichlorobenzene",  # C6H4Cl2  Tc=705.0 K  o-DCB
        "1,3-Dichlorobenzene",  # C6H4Cl2  Tc=683.9 K  m-DCB
        "1,4-Dichlorobenzene",  # C6H4Cl2  Tc=684.8 K  p-DCB
        "1,2,4-Trichlorobenzene",# C6H3Cl3 Tc=725.0 K
        "Chloronaphthalene",    # C10H7Cl  Tc=774.0 K
    ],

    # ④ 더 많은 헤테로고리 O 함유
    "heterocyclic_O_add": [
        "Benzofuran",          # C8H6O   Tc=726.0 K  산소 이환 방향족
        "2-Methylfuran",       # C5H6O   Tc=527.0 K
        "2-Methyltetrahydrofuran", # C5H10O Tc=537.0 K
        "Tetrahydropyran",     # C5H10O  Tc=572.2 K — 이미 있음 (skip)
        "Paraldehyde",         # C6H12O3 Tc=599.0 K  아세트알데히드 삼합체
    ],

    # ⑤ 더 많은 산 (무기산 포함)
    "acid_add": [
        "HydrofluoricAcid",    # HF      Tc=461.0 K  무기 불산 (독성)
        "PhosphoricAcid",      # H3PO4   Tc=...  (데이터 없을 수 있음)
        "TrifluoroaceticAcid", # C2HF3O2 Tc=491.3 K  강산
        "Trichloroacetic",     # C2HCl3O2 Tc=592.0 K
        "PentafluoropropionicAcid", # C3HF5O2 Tc=506.0 K
    ],

    # ⑥ 더 많은 C10+ 방향족
    "large_aromatic_add": [
        "AcenaphtHene",        # C12H10  Tc=803.0 K  아세나프텐
        "Fluoranthene",        # C16H10  Tc=905.0 K  플루오란텐
        "Coronene",            # C24H12  Tc=1116.0 K (예측값)
    ],

    # ⑦ 아미드·락탐 (강한 수소결합, 고bp)
    "amide_lactam": [
        "NDimethylAcetamide",  # C4H9NO  Tc=658.0 K  DMAc
        "NMethylPyrrolidone",  # C5H9NO  Tc=721.7 K  NMP — 이미 있음 (skip)
        "Caprolactam",         # C6H11NO Tc=806.0 K — 이미 있음 (skip)
        "Succinimide",         # C4H5NO2 Tc=...
    ],

    # ⑧ 더 많은 C5~C6 할로겐화
    "halo_C5C6_add": [
        "1,2-Dichloropentane",  # C5H10Cl2 Tc=606.0 K
        "1-Chloro-2-MethylPropane", # C4H9Cl Tc=... 이소부틸 클로라이드
        "3-Chloropropene",      # C3H5Cl  = Allylchloride (skip)
        "1-Chloro-2-Methylbutane", # C5H11Cl Tc=542.0 K
    ],
}

NEGATIVE_EXTENDED10 = {

    # ① 더 많은 C5 이성질체 알코올
    "C5_alcohol": [
        "3-Methyl-2-Butanol",   # C5H12O  Tc=549.0 K
        "2-Methyl-2-Butanol",   # C5H12O  Tc=543.7 K  tert-아밀알코올과 유사
        "Cyclopentanol",        # C5H10O  Tc=619.5 K
        "3-Pentanol",           # C5H12O  Tc=559.6 K
    ],

    # ② C6~C8 할로알케인 (F 없는 긴 사슬)
    "halo_C6C8": [
        "1-Chlorohexane",   # C6H13Cl  Tc=599.0 K
        "1-Chlorooctane",   # C8H17Cl  Tc=643.3 K
        "1-Bromohexane",    # C6H13Br  Tc=617.0 K
        "1-Bromooctane",    # C8H17Br  Tc=650.0 K
    ],

    # ③ 더 많은 에테르 (C6+)
    "ether_C6plus": [
        "DipentylEther",     # C10H22O  Tc=616.0 K
        "Dibenzofuran",      # C12H8O   Tc=824.0 K  방향족 에테르
        "Tetrahydropyran",   # C5H10O   Tc=572.2 K  THP
        "1,3-Dioxolane",     # C3H6O2   Tc=542.0 K
        "CrownEther18c6",    # C12H24O6 Tc=...  (데이터 없을 수 있음)
    ],

    # ④ 더 많은 불포화 탄화수소 (C6~C10 방향족 외)
    "misc_unsaturated": [
        "Limonene",          # C10H16  Tc=653.0 K  테르펜 (2중결합×2)
        "aAlphaPinene",      # C10H16  Tc=648.0 K  테르펜 고리형
        "Camphene",          # C10H16  Tc=638.0 K
        "Terpinolene",       # C10H16  Tc=652.0 K
        "Myrcene",           # C10H16  Tc=644.0 K  공액 테르펜
    ],

    # ⑤ 더 많은 실록산 이성질체
    "siloxane_extended": [
        "Trimethylsilane",      # C3H10Si  Tc=432.0 K  SiH(CH3)3
    ],

    # ⑥ 카바메이트·우레탄 (반응성 질소 화합물)
    "carbamate": [
        "MethylCarbamate",   # C2H5NO2  Tc=603.0 K  우레탄
        "EthylCarbamate",    # C3H7NO2  Tc=625.0 K
    ],

    # ⑦ 더 많은 PFC 화합물
    "PFC_extended": [
        "Perfluorodecane",        # C10F22  Tc=542.0 K  (데이터 없을 수 있음)
        "PerfluoroMethylDecalin", # C11F20  Tc=566.0 K
        "PerfluoroTripropylamine",# C9F21N  Tc=525.0 K  FC-43
    ],

    # ⑧ 더 많은 C9 이성질체 알케인
    "C9_alkane_isomers": [
        "2-Methyloctane",     # C9H20  Tc=582.8 K
        "4-Methyloctane",     # C9H20  Tc=587.7 K
        "2,2-Dimethylheptane",# C9H20  Tc=576.7 K
        "2,6-Dimethylheptane",# C9H20  Tc=579.5 K
    ],

    # ⑨ 추가 황 화합물
    "sulfur_extended": [
        "DiethylSulfide",     # C4H10S  Tc=557.0 K — 이미 있음
        "CarbonylSulfide",    # OCS     Tc=378.8 K — 이미 정례에 있음 (skip)
        "HydrogenSulfide",    # H2S     Tc=373.1 K — 이미 정례에 있음 (skip)
        "Methanesulfonic",    # CH4O3S  Tc=... (데이터 없을 수 있음)
    ],

    # ⑩ 이산화질소·산화물
    "nitrogen_oxide": [
        "NitrogenDioxide",    # NO2     Tc=431.0 K  (반응성)
        "NitricOxide",        # NO      Tc=180.1 K  (Tc 낮음)
        "DinitrogenTetroxide",# N2O4    Tc=431.0 K  (폭발성)
    ],

    # ⑪ 특수 불소화 화합물 (GWP 관련 연구)
    "fluorinated_special": [
        "Perfluorobutylamine",  # C4F9NH2  Tc=...
        "PerfluorotributylAmine",# C12F27N Tc=525.0 K  Fluorinert FC-43
        "bis_HFE_7300",         # C7H5F13O Tc=...
    ],
}


def get_all_compounds() -> list[dict]:
    """
    전체 화합물 목록을 반환 (중복 제거 포함)
    각 항목: {"identifier": str, "label": int, "group": str}
    """
    all_dicts = [
        (1, POSITIVE),
        (1, POSITIVE_EXTENDED),
        (1, POSITIVE_EXTENDED2),
        (1, POSITIVE_EXTENDED3),
        (1, POSITIVE_EXTENDED4),
        (1, POSITIVE_EXTENDED5),
        (0, NEGATIVE),
        (0, NEGATIVE_EXTENDED),
        (0, NEGATIVE_EXTENDED2),
        (0, NEGATIVE_EXTENDED3),
        (0, NEGATIVE_EXTENDED4),
        (0, NEGATIVE_EXTENDED5),
        (0, NEGATIVE_EXTENDED6),
        (0, NEGATIVE_EXTENDED7),
        (0, NEGATIVE_EXTENDED8),
        (0, NEGATIVE_EXTENDED9),
        (0, NEGATIVE_EXTENDED10),
        (0, NEGATIVE_EXTENDED11),
    ]
    records = []
    seen: set[str] = set()
    for label, d in all_dicts:
        for group, compounds in d.items():
            for c in compounds:
                if c not in seen:
                    seen.add(c)
                    records.append({"identifier": c, "label": label, "group": group})
    return records


if __name__ == "__main__":
    import pandas as pd
    df = pd.DataFrame(get_all_compounds())
    print(f"총 {len(df)}종  (정례={df['label'].sum()}, 반례={(df['label']==0).sum()})")
    print(df.groupby(["label","group"]).size().to_string())
