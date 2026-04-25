"""
문헌 값 직접 입력 (Manual Literature Values)

사용 조건:
  - CoolProp 미지원
  - NIST WebBook HTML 파싱으로도 Tc/Pc/ω 가 하나 이상 누락인 경우

주요 출처:
  [1] Poling, Prausnitz, O'Connell, "The Properties of Gases and Liquids", 5th ed.
  [2] ASHRAE Handbook – Fundamentals (2017), Refrigerant Property Tables
  [3] CRC Handbook of Chemistry and Physics, 103rd ed.
  [4] NIST WebBook supplementary data (manually extracted)
"""

# 화합물명 → {Tc_K, Pc_MPa, omega}
# None: 해당 물성이 문헌에 없거나 불확실
MANUAL_PROPS: dict[str, dict] = {

    # ── C2 HFO (정례: 불소화 올레핀) ─────────────────────────────────────────
    # R-1114  CF2=CF2  Tetrafluoroethylene   [2][4]
    "R-1114":  {"Tc_K": 307.4,   "Pc_MPa": 3.941,   "omega": 0.224},
    # R-1132a CH2=CF2  Vinylidene fluoride   [2][4] NIST Tc/Pc 이미 있음
    "R-1132a": {"Tc_K": 302.74,  "Pc_MPa": 4.4333,  "omega": 0.204},
    # R-1123  CHF=CF2  Trifluoroethylene     [2]
    "R-1123":  {"Tc_K": 379.9,   "Pc_MPa": 4.803,   "omega": 0.182},
    # R-1141  CH2=CHF  Vinyl fluoride        [2][4]
    "R-1141":  {"Tc_K": 327.9,   "Pc_MPa": 5.243,   "omega": 0.121},
    # R-1113  CF2=CFCl Chlorotrifluoroethyl. [2]
    "R-1113":  {"Tc_K": 425.0,   "Pc_MPa": 4.074,   "omega": 0.178},

    # ── Br+F 냉매 (정례) ──────────────────────────────────────────────────────
    # R-12B1  CBrClF2  Halon-1211            [2][3]
    "R-12B1":  {"Tc_K": 428.15,  "Pc_MPa": 4.015,   "omega": 0.183},
    # R-22B1  CHBrF2   Bromodifluoromethane  [2][4] NIST Tc/Pc 이미 있음
    "R-22B1":  {"Tc_K": 411.98,  "Pc_MPa": 5.132,   "omega": 0.145},

    # ── 삼중결합 알카인 (반례) ─────────────────────────────────────────────────
    # 2-Butyne  CH3-C≡C-CH3                  [1]
    "2-Butyne": {"Tc_K": 488.7,  "Pc_MPa": 4.57,    "omega": 0.251},

    # ── C2 불포화 Cl (반례) ──────────────────────────────────────────────────
    # VinylideneChloride  CH2=CCl2           [1]
    "VinylideneChloride": {"Tc_K": 484.0, "Pc_MPa": 5.10, "omega": 0.204},
    # Trichloroethylene   CHCl=CCl2          [1][4] NIST Tc 이미 있음
    "Trichloroethylene":  {"Tc_K": 571.0,  "Pc_MPa": 5.02, "omega": 0.218},

    # ── Br·I 할로메테인 (반례) ────────────────────────────────────────────────
    # Bromomethane  CH3Br                    [1][3]
    "Bromomethane":   {"Tc_K": 467.0,  "Pc_MPa": 6.01,  "omega": 0.179},
    # Dibromomethane CH2Br2                  [1][3]
    "Dibromomethane": {"Tc_K": 611.0,  "Pc_MPa": 7.16,  "omega": 0.280},
    # Iodomethane   CH3I                     [1][3]
    "Iodomethane":    {"Tc_K": 528.0,  "Pc_MPa": 5.36,  "omega": 0.209},

    # ── C4~C5 불포화 (반례) ──────────────────────────────────────────────────
    # Isoprene  C5H8 (2-methyl-1,3-butadiene) [1]
    "Isoprene":    {"Tc_K": 484.0,  "Pc_MPa": 3.83,  "omega": 0.181},
    # Cyclobutane C4H8                       [1]
    "Cyclobutane": {"Tc_K": 460.0,  "Pc_MPa": 4.98,  "omega": 0.192},
    # Cyclopentene C5H8                      [1][4] NIST Tc/Pc 이미 있음
    "Cyclopentene": {"Tc_K": 506.5, "Pc_MPa": 4.80,  "omega": 0.196},

    # ── 할로겐화 방향족 (반례) ───────────────────────────────────────────────
    # Bromobenzene C6H5Br                    [1][3]
    "Bromobenzene": {"Tc_K": 670.15, "Pc_MPa": 4.52, "omega": 0.251},

    # ── 알킬 고리형 (반례) ───────────────────────────────────────────────────
    # Methylcyclohexane C7H14                [1][4] NIST Tc/Pc 이미 있음
    "Methylcyclohexane": {"Tc_K": 572.2, "Pc_MPa": 3.471, "omega": 0.235},

    # ── 방향족 (반례: Tc 너무 높음) ─────────────────────────────────────────
    # Styrene C8H8                           [1][3]
    "Styrene": {"Tc_K": 636.0, "Pc_MPa": 3.80, "omega": 0.297},

    # ── 정례3: 추가 냉매 후보 [1][2][5] ─────────────────────────────────────
    # [5] ASHRAE Handbook – Fundamentals (2022)
    "R-245cb":  {"Tc_K": 380.1,  "Pc_MPa": 3.138, "omega": 0.278},
    "R-245eb":  {"Tc_K": 431.0,  "Pc_MPa": 3.342, "omega": 0.297},
    "R-236cb":  {"Tc_K": 412.4,  "Pc_MPa": 3.177, "omega": 0.276},
    "R-263fb":  {"Tc_K": 453.0,  "Pc_MPa": 4.130, "omega": 0.264},
    "R-253fb":  {"Tc_K": 448.2,  "Pc_MPa": 3.550, "omega": 0.302},
    "R-1225ye(E)": {"Tc_K": 380.5, "Pc_MPa": 3.251, "omega": 0.193},
    "R-1225ye(Z)": {"Tc_K": 394.8, "Pc_MPa": 4.440, "omega": 0.192},
    "R-1225zc":    {"Tc_K": 412.4, "Pc_MPa": 3.640, "omega": 0.195},
    "R-1224yd(Z)": {"Tc_K": 428.7, "Pc_MPa": 2.930, "omega": 0.209},
    "R-1233zd(Z)": {"Tc_K": 423.3, "Pc_MPa": 3.620, "omega": 0.220},
    "R-1336mzz(Z)": {"Tc_K": 444.0, "Pc_MPa": 2.900, "omega": 0.273},
    "HFE-143m":   {"Tc_K": 377.9, "Pc_MPa": 3.261, "omega": 0.289},
    "HFE-125":    {"Tc_K": 354.5, "Pc_MPa": 3.350, "omega": 0.221},
    "HFE-134":    {"Tc_K": 420.3, "Pc_MPa": 4.647, "omega": 0.270},
    "HFE-245mc":  {"Tc_K": 406.8, "Pc_MPa": 2.879, "omega": 0.296},
    "HFE-245fa2": {"Tc_K": 444.9, "Pc_MPa": 3.433, "omega": 0.323},
    "HFE-7000":   {"Tc_K": 437.7, "Pc_MPa": 2.550, "omega": 0.385},
    "R-E143a":    {"Tc_K": 377.9, "Pc_MPa": 3.261, "omega": 0.289},
    "NitrogenTrifluoride": {"Tc_K": 234.0, "Pc_MPa": 4.460, "omega": 0.126},
    "Silane":              {"Tc_K": 269.7, "Pc_MPa": 4.840, "omega": 0.094},
    "R-143":   {"Tc_K": 374.2, "Pc_MPa": 4.610, "omega": 0.259},
    "R-152":   {"Tc_K": 386.4, "Pc_MPa": 4.430, "omega": 0.289},
    "R-31":    {"Tc_K": 369.3, "Pc_MPa": 5.710, "omega": 0.209},
    "R-133a":  {"Tc_K": 480.2, "Pc_MPa": 3.672, "omega": 0.272},
    "R-132b":  {"Tc_K": 452.0, "Pc_MPa": 4.245, "omega": 0.261},
    "R-243fa": {"Tc_K": 502.5, "Pc_MPa": 3.330, "omega": 0.358},
    "R-244fa": {"Tc_K": 501.5, "Pc_MPa": 3.240, "omega": 0.359},
    "R-234ab": {"Tc_K": 482.5, "Pc_MPa": 2.900, "omega": 0.320},
    "R-123a":  {"Tc_K": 424.0, "Pc_MPa": 3.670, "omega": 0.248},
    "R-132":   {"Tc_K": 470.0, "Pc_MPa": 4.060, "omega": 0.269},
    "R-141":   {"Tc_K": 481.0, "Pc_MPa": 4.060, "omega": 0.267},
    "R-1122":   {"Tc_K": 490.0, "Pc_MPa": 4.150, "omega": 0.247},
    "R-1112a":  {"Tc_K": 451.5, "Pc_MPa": 4.040, "omega": 0.218},
    "R-1130":   {"Tc_K": 516.0, "Pc_MPa": 5.510, "omega": 0.256},
    "R-1130a":  {"Tc_K": 535.0, "Pc_MPa": 5.320, "omega": 0.260},
    "R-1233xf": {"Tc_K": 440.7, "Pc_MPa": 3.520, "omega": 0.243},
    # ── 반례: 추가 유기화합물 (NIST 파싱 실패 대비) ────────────────────────
    "C4F10":   {"Tc_K": 386.3,  "Pc_MPa": 2.323, "omega": 0.371},
    "C5F12":   {"Tc_K": 420.6,  "Pc_MPa": 2.045, "omega": 0.423},
    "C6F14":   {"Tc_K": 448.8,  "Pc_MPa": 1.872, "omega": 0.490},
    "1,2-Dichlorobenzene": {"Tc_K": 705.0, "Pc_MPa": 4.070, "omega": 0.270},
    "1,3-Dichlorobenzene": {"Tc_K": 683.9, "Pc_MPa": 3.980, "omega": 0.267},
    "1,4-Dichlorobenzene": {"Tc_K": 684.8, "Pc_MPa": 4.070, "omega": 0.259},
    "1,1-Dichloroethane":        {"Tc_K": 523.0, "Pc_MPa": 5.070, "omega": 0.236},
    "1,2-Dibromoethane":         {"Tc_K": 650.2, "Pc_MPa": 5.420, "omega": 0.327},
    "1,1,1,2-Tetrachloroethane": {"Tc_K": 624.0, "Pc_MPa": 3.750, "omega": 0.281},
    "Hexachloroethane":          {"Tc_K": 695.0, "Pc_MPa": 3.340, "omega": 0.453},
    "Dibromochloromethane":      {"Tc_K": 603.0, "Pc_MPa": 5.020, "omega": 0.323},
    "Bromoform":                 {"Tc_K": 696.0, "Pc_MPa": 5.470, "omega": 0.388},
    "Anthracene":   {"Tc_K": 873.0, "Pc_MPa": 2.900, "omega": 0.530},
    "Phenanthrene": {"Tc_K": 869.3, "Pc_MPa": 2.900, "omega": 0.469},
    "Fluorene":     {"Tc_K": 826.0, "Pc_MPa": 2.900, "omega": 0.446},
    "Biphenyl":     {"Tc_K": 789.3, "Pc_MPa": 3.380, "omega": 0.365},
    "Pentafluorobenzene":  {"Tc_K": 530.97, "Pc_MPa": 3.531, "omega": 0.377},
    "Trifluorotoluene":    {"Tc_K": 565.0,  "Pc_MPa": 3.730, "omega": 0.350},
    "1,2-Difluorobenzene": {"Tc_K": 566.0,  "Pc_MPa": 4.300, "omega": 0.286},
    "1,3-Difluorobenzene": {"Tc_K": 558.4,  "Pc_MPa": 4.250, "omega": 0.289},
    "1,4-Difluorobenzene": {"Tc_K": 556.0,  "Pc_MPa": 4.220, "omega": 0.289},
    "Novec1230": {"Tc_K": 441.8, "Pc_MPa": 1.872, "omega": 0.471},

    # ── 양성 화합물 식별자 별칭 / 누락 ──────────────────────────────────────
    # R-1120 = CHCl=CCl2 = Trichloroethylene  [1]
    "R-1120":    {"Tc_K": 571.0,  "Pc_MPa": 5.020,  "omega": 0.218},
    # R-1232xf = (E)-1-chloro-3,3,3-trifluoropropene   [2][4]
    "R-1232xf":  {"Tc_K": 456.0,  "Pc_MPa": 3.560,  "omega": 0.244},
    # R-1354myfz = (Z)-1,1,1,4,4,4-hexafluorobut-2-ene [2]
    "R-1354myfz":{"Tc_K": 453.0,  "Pc_MPa": 2.720,  "omega": 0.336},
    # R-338mccq = 1,1,1,2,3,4-hexafluorobutane         [2]
    "R-338mccq": {"Tc_K": 475.0,  "Pc_MPa": 3.120,  "omega": 0.350},
    # HFE-449sl = methyl nonafluoroisobutyl ether (Novec 449)  [2]
    "HFE-449sl": {"Tc_K": 439.0,  "Pc_MPa": 1.920,  "omega": 0.415},
    # R-30B2 = CH2Br2 = Dibromomethane        [1][3]
    "R-30B2":    {"Tc_K": 611.0,  "Pc_MPa": 7.160,  "omega": 0.280},
    # R-20B3 = CHBr3 = Bromoform              [1][3]
    "R-20B3":    {"Tc_K": 696.0,  "Pc_MPa": 5.470,  "omega": 0.388},
    # R245cb (no-dash CoolProp alias for R-245cb)
    "R245cb":    {"Tc_K": 380.1,  "Pc_MPa": 3.138,  "omega": 0.278},

    # ── 반례: 부분 물성 보완 (omega 누락 → 보완) ────────────────────────────
    # Poling et al. Table A.1, CRC Handbook 103rd ed.
    # Note: None 값은 NIST 결과를 유지, 실수값만 보완
    "Decalin":           {"Tc_K": None,  "Pc_MPa": None,  "omega": 0.303},
    "DiethyleneGlycol":  {"Tc_K": None,  "Pc_MPa": None,  "omega": 0.910},
    "Cyclohexanone":     {"Tc_K": None,  "Pc_MPa": None,  "omega": 0.444},
    "Propionaldehyde":   {"Tc_K": 504.4, "Pc_MPa": 5.140, "omega": 0.289},  # NIST wrong (600K)
    "MTBE":              {"Tc_K": None,  "Pc_MPa": None,  "omega": 0.267},
    "NMethylPyrrolidone":{"Tc_K": None,  "Pc_MPa": None,  "omega": 0.432},
    "EthylFormate":      {"Tc_K": None,  "Pc_MPa": None,  "omega": 0.282},
    "3-Methyl-1-Butanol":{"Tc_K": None,  "Pc_MPa": None,  "omega": 0.585},
    "Butylamine":        {"Tc_K": 531.9, "Pc_MPa": 4.260,  "omega": 0.334},
    "Dibutylamine":      {"Tc_K": None,  "Pc_MPa": None,  "omega": 0.485},
    "Cyclohexylamine":   {"Tc_K": None,  "Pc_MPa": 3.600,  "omega": 0.318},
    "3-Methyl-2-Butanol":{"Tc_K": None,  "Pc_MPa": None,  "omega": 0.502},
    "Cyclopentanol":     {"Tc_K": None,  "Pc_MPa": None,  "omega": 0.546},
    "Dibenzofuran":      {"Tc_K": None,  "Pc_MPa": None,  "omega": 0.476},
    "Tetrahydropyran":   {"Tc_K": None,  "Pc_MPa": None,  "omega": 0.269},
    "2-Methyloctane":    {"Tc_K": None,  "Pc_MPa": None,  "omega": 0.448},
    "2,2-Dimethylheptane":   {"Tc_K": None, "Pc_MPa": None, "omega": 0.419},
    "2,2,3-TrimethylPentane":{"Tc_K": None, "Pc_MPa": None, "omega": 0.381},
    "3-Hexene":          {"Tc_K": None,  "Pc_MPa": None,  "omega": 0.267},
    "1,4-Butanediol":    {"Tc_K": None,  "Pc_MPa": None,  "omega": 0.898},
    "2-Methyltetrahydrofuran": {"Tc_K": None, "Pc_MPa": None, "omega": 0.289},
    "2-Methylfuran":     {"Tc_K": None,  "Pc_MPa": None,  "omega": 0.266},
    "Paraldehyde":       {"Tc_K": None,  "Pc_MPa": 3.130,  "omega": 0.378},
    "Cyclohexene":       {"Tc_K": None,  "Pc_MPa": 4.350,  "omega": 0.213},
    "ForamicAcid":       {"Tc_K": 588.0, "Pc_MPa": 5.810,  "omega": 0.474},  # formic acid
    "Acetaldehyde":      {"Tc_K": None,  "Pc_MPa": 5.550,  "omega": 0.291},
    "Triethylamine":     {"Tc_K": None,  "Pc_MPa": 3.030,  "omega": 0.316},
    "CarbonDisulfide":   {"Tc_K": None,  "Pc_MPa": 7.900,  "omega": 0.106},
    "1-Chlorobutane":    {"Tc_K": None,  "Pc_MPa": 3.970,  "omega": 0.217},
    "2-Chlorobutane":    {"Tc_K": None,  "Pc_MPa": 3.950,  "omega": 0.230},
    "1-Chloropentane":   {"Tc_K": None,  "Pc_MPa": 3.350,  "omega": 0.253},
    "1,1,1-Trichloroethane": {"Tc_K": None, "Pc_MPa": 4.300, "omega": 0.214},
    "1,1,2-Trichloroethane": {"Tc_K": None, "Pc_MPa": 4.480, "omega": 0.277},
    "2-Bromopropane":    {"Tc_K": None,  "Pc_MPa": 4.360,  "omega": 0.215},
    "1-Bromobutane":     {"Tc_K": None,  "Pc_MPa": 4.050,  "omega": 0.271},
    "NNDimethylFormamide":{"Tc_K": None, "Pc_MPa": 5.110,  "omega": 0.399},
    "DimethylDisulfide": {"Tc_K": None,  "Pc_MPa": 5.360,  "omega": 0.278},
    "Dimethyldisulfide": {"Tc_K": None,  "Pc_MPa": 5.360,  "omega": 0.278},
    "4-Chlorotoluene":   {"Tc_K": None,  "Pc_MPa": 4.050,  "omega": 0.279},
    "Benzotrifluoride":  {"Tc_K": None,  "Pc_MPa": 3.730,  "omega": 0.350},
    "4-Fluorotoluene":   {"Tc_K": None,  "Pc_MPa": 3.830,  "omega": 0.282},
    "4-Heptanone":       {"Tc_K": None,  "Pc_MPa": 3.220,  "omega": 0.445},
    "Isoquinoline":      {"Tc_K": None,  "Pc_MPa": 5.070,  "omega": 0.338},
    "3-Pentanol":        {"Tc_K": None,  "Pc_MPa": 4.060,  "omega": 0.537},
    "1-Chlorohexane":    {"Tc_K": None,  "Pc_MPa": 3.360,  "omega": 0.249},
    "Perfluorodecane":   {"Tc_K": None,  "Pc_MPa": 1.750,  "omega": 0.469},
    "2,2,5-TrimethylHexane": {"Tc_K": None, "Pc_MPa": 2.480, "omega": 0.395},
    "2,2,3,3-TetramethylButane": {"Tc_K": None, "Pc_MPa": 2.740, "omega": 0.378},
    "4-Methyloctane":    {"Tc_K": 587.0, "Pc_MPa": 2.310,  "omega": 0.451},
    "2,6-Dimethylheptane":   {"Tc_K": 579.0, "Pc_MPa": 2.410, "omega": 0.416},
    "3-EthylMethylPentane":  {"Tc_K": 567.0, "Pc_MPa": 2.740, "omega": 0.368},

    # ── 반례: 전체 물성 누락 (common compounds, Poling et al. / CRC / DIPPR) ─
    "2-Pentene":         {"Tc_K": 507.8,  "Pc_MPa": 4.000,  "omega": 0.239},
    "BenzylAlcohol":     {"Tc_K": 720.2,  "Pc_MPa": 4.400,  "omega": 0.621},
    "PropyleneGlycol":   {"Tc_K": 626.4,  "Pc_MPa": 6.100,  "omega": 0.704},
    "BenzoicAcid":       {"Tc_K": 751.0,  "Pc_MPa": 4.470,  "omega": 0.620},
    "DiethylCarbonate":  {"Tc_K": 561.5,  "Pc_MPa": 3.300,  "omega": 0.535},
    "Morpholine":        {"Tc_K": 619.0,  "Pc_MPa": 5.530,  "omega": 0.368},
    "DMSO":              {"Tc_K": 729.0,  "Pc_MPa": 5.650,  "omega": 0.480},
    "Indene":            {"Tc_K": 587.6,  "Pc_MPa": 3.950,  "omega": 0.320},
    "Indole":            {"Tc_K": 790.0,  "Pc_MPa": 4.800,  "omega": 0.497},
    "Imidazole":         {"Tc_K": 741.0,  "Pc_MPa": 6.950,  "omega": 0.429},
    "2-Chloropropane":   {"Tc_K": 514.9,  "Pc_MPa": 4.750,  "omega": 0.207},
    "1,3-Dichloropropane":{"Tc_K": 612.0, "Pc_MPa": 4.600,  "omega": 0.291},
    "Nitroethane":       {"Tc_K": 593.0,  "Pc_MPa": 5.170,  "omega": 0.376},
    "Formamide":         {"Tc_K": 771.0,  "Pc_MPa": 7.750,  "omega": 0.401},
    "Acetamide":         {"Tc_K": 761.0,  "Pc_MPa": 6.510,  "omega": 0.523},
    "GammaButyrolactone":{"Tc_K": 739.0,  "Pc_MPa": 4.500,  "omega": 0.468},
    "EpsilonCaprolactone":{"Tc_K": 806.0, "Pc_MPa": 3.800,  "omega": 0.599},
    "2-Hexene":          {"Tc_K": 516.5,  "Pc_MPa": 3.160,  "omega": 0.279},
    "1,3-Dioxolane":     {"Tc_K": 542.0,  "Pc_MPa": 5.110,  "omega": 0.300},
    "MethylAcrylate":    {"Tc_K": 536.0,  "Pc_MPa": 4.260,  "omega": 0.324},
    "EthylAcrylate":     {"Tc_K": 553.0,  "Pc_MPa": 3.770,  "omega": 0.372},
    "MethylMethacrylate":{"Tc_K": 566.0,  "Pc_MPa": 3.680,  "omega": 0.322},
    "EthylBenzoate":     {"Tc_K": 698.0,  "Pc_MPa": 3.040,  "omega": 0.479},
    "MethylBenzoate":    {"Tc_K": 693.0,  "Pc_MPa": 3.590,  "omega": 0.424},
    "1,2,4-Trichlorobenzene": {"Tc_K": 705.0, "Pc_MPa": 3.870, "omega": 0.336},
    "Chloronaphthalene": {"Tc_K": 764.0,  "Pc_MPa": 4.050,  "omega": 0.389},
    "Benzofuran":        {"Tc_K": 621.4,  "Pc_MPa": 4.640,  "omega": 0.354},
    "Guaiacol":          {"Tc_K": 696.0,  "Pc_MPa": 4.440,  "omega": 0.564},
    "Catechol":          {"Tc_K": 720.0,  "Pc_MPa": 5.280,  "omega": 0.683},
    "Resorcinol":        {"Tc_K": 725.0,  "Pc_MPa": 5.280,  "omega": 0.579},
    "Isophorone":        {"Tc_K": 715.0,  "Pc_MPa": 3.770,  "omega": 0.491},
    "Caprolactam":       {"Tc_K": 806.0,  "Pc_MPa": 4.590,  "omega": 0.611},
    "DimethylPhthalate": {"Tc_K": 766.0,  "Pc_MPa": 2.780,  "omega": 0.620},
    "DiethylPhthalate":  {"Tc_K": 776.0,  "Pc_MPa": 2.550,  "omega": 0.731},
    "DimethylSuccinate": {"Tc_K": 662.0,  "Pc_MPa": 3.240,  "omega": 0.497},
    "Pyrene":            {"Tc_K": 936.0,  "Pc_MPa": 2.630,  "omega": 0.528},
    "Fluoranthene":      {"Tc_K": 905.0,  "Pc_MPa": 2.570,  "omega": 0.526},
    "Acridine":          {"Tc_K": 899.0,  "Pc_MPa": 3.310,  "omega": 0.600},
    "Acenaphthylene":    {"Tc_K": 803.0,  "Pc_MPa": 3.630,  "omega": 0.451},
    "AcenaphtHene":      {"Tc_K": 803.0,  "Pc_MPa": 3.630,  "omega": 0.451},
    "Allylchloride":     {"Tc_K": 514.1,  "Pc_MPa": 4.730,  "omega": 0.174},
    "3-Chloropropene":   {"Tc_K": 514.1,  "Pc_MPa": 4.730,  "omega": 0.174},
    "Allyl":             {"Tc_K": 545.0,  "Pc_MPa": 5.670,  "omega": 0.508},  # allyl alcohol
    "Acrolein":          {"Tc_K": 506.5,  "Pc_MPa": 5.160,  "omega": 0.328},
    "PropargylAlcohol":  {"Tc_K": 587.0,  "Pc_MPa": 5.670,  "omega": 0.497},
    "1-Bromonaphthalene":{"Tc_K": 824.0,  "Pc_MPa": 3.920,  "omega": 0.391},
    "2-Chlorotoluene":   {"Tc_K": 615.9,  "Pc_MPa": 4.050,  "omega": 0.264},
    "4-Chlorofluorobenzene":{"Tc_K": 620.0, "Pc_MPa": 4.240, "omega": 0.265},
    "TrifluoroaceticAcid":   {"Tc_K": 491.3, "Pc_MPa": 3.260, "omega": 0.661},
    "Trichloroacetic":   {"Tc_K": 604.0,  "Pc_MPa": 4.250,  "omega": 0.571},
    "1,2-Dichloropentane":       {"Tc_K": 638.0,  "Pc_MPa": 3.700,  "omega": 0.330},
    "1-Chloro-2-MethylPropane":  {"Tc_K": 538.0,  "Pc_MPa": 4.100,  "omega": 0.261},
    "1-Chloro-2-Methylbutane":   {"Tc_K": 558.0,  "Pc_MPa": 3.670,  "omega": 0.272},
    "NDimethylAcetamide":{"Tc_K": 694.0,  "Pc_MPa": 4.000,  "omega": 0.416},
    "NDimethylFormamide":{"Tc_K": 649.6,  "Pc_MPa": 5.110,  "omega": 0.399},
    "Succinimide":       {"Tc_K": 820.0,  "Pc_MPa": 4.600,  "omega": 0.540},
    "Chloroiodomethane": {"Tc_K": 549.0,  "Pc_MPa": 5.670,  "omega": 0.243},
    "Iodoform":          {"Tc_K": 839.0,  "Pc_MPa": 4.900,  "omega": 0.368},
    "1-Iodopropane":     {"Tc_K": 613.0,  "Pc_MPa": 4.140,  "omega": 0.278},
    "1-Iodobutane":      {"Tc_K": 644.0,  "Pc_MPa": 3.860,  "omega": 0.326},
    "NitrogenDioxide":   {"Tc_K": 431.4,  "Pc_MPa": 10.13,  "omega": 0.825},
    "NitricOxide":       {"Tc_K": 180.2,  "Pc_MPa": 6.480,  "omega": 0.582},
    "MethylCarbamate":   {"Tc_K": 646.0,  "Pc_MPa": 5.920,  "omega": 0.521},
    "EthylCarbamate":    {"Tc_K": 685.0,  "Pc_MPa": 5.130,  "omega": 0.562},
    "MethylIsocyanate":  {"Tc_K": 503.0,  "Pc_MPa": 5.420,  "omega": 0.268},
    "ThionylChloride":   {"Tc_K": 523.0,  "Pc_MPa": 6.910,  "omega": 0.314},
    "SulfurylChloride":  {"Tc_K": 502.0,  "Pc_MPa": 5.170,  "omega": 0.281},
    "Hexamethyldisilane":{"Tc_K": 586.0,  "Pc_MPa": 2.650,  "omega": 0.328},
    "Trimethylsilane":   {"Tc_K": 432.0,  "Pc_MPa": 3.430,  "omega": 0.213},
    "1-Chlorooctane":    {"Tc_K": 643.0,  "Pc_MPa": 3.070,  "omega": 0.289},
    "1-Bromohexane":     {"Tc_K": 650.0,  "Pc_MPa": 3.160,  "omega": 0.355},
    "1-Bromooctane":     {"Tc_K": 698.0,  "Pc_MPa": 2.850,  "omega": 0.403},
    "DipentylEther":     {"Tc_K": 640.0,  "Pc_MPa": 2.090,  "omega": 0.597},
    "Limonene":          {"Tc_K": 657.0,  "Pc_MPa": 2.800,  "omega": 0.449},
    "aAlphaPinene":      {"Tc_K": 644.0,  "Pc_MPa": 2.760,  "omega": 0.411},
    "DietylDisulfide":   {"Tc_K": 642.0,  "Pc_MPa": 4.260,  "omega": 0.376},
    "EthylLactate":      {"Tc_K": 588.0,  "Pc_MPa": 3.800,  "omega": 0.573},
    "Acetophenol":       {"Tc_K": 751.0,  "Pc_MPa": 4.300,  "omega": 0.613},  # 4-hydroxyacetophenone est
    "2-MethylHexane":    {"Tc_K": None,   "Pc_MPa": None,   "omega": 0.331},  # CoolProp has, patch omega
    "3-MethylHexane":    {"Tc_K": None,   "Pc_MPa": None,   "omega": 0.323},
    "Benzophenol":       {"Tc_K": 830.0,  "Pc_MPa": 3.350,  "omega": 0.490},  # = Benzophenone [1][3]
    "2,2,3,3-TetramethylButane": {"Tc_K": 568.0, "Pc_MPa": 2.740, "omega": 0.378},

    # ── 반례: 아직 thermo 누락 (Poling/CRC/DIPPR 추정) ──────────────────────
    "TrimethylPhosphate":{"Tc_K": 512.0,  "Pc_MPa": 2.670,  "omega": 0.531},
    "TrimethylBorate":   {"Tc_K": 501.0,  "Pc_MPa": 3.090,  "omega": 0.434},
    "Chloromethylmethylether": {"Tc_K": 535.0, "Pc_MPa": 4.000, "omega": 0.305},
    "EthyleneGlycolMonoethylEther": {"Tc_K": 569.0, "Pc_MPa": 4.140, "omega": 0.543},
    "1-MethylCyclopentene": {"Tc_K": 542.0, "Pc_MPa": 3.720, "omega": 0.246},
    "1-Phenylnaphthalene": {"Tc_K": 849.0, "Pc_MPa": 2.580, "omega": 0.485},
    "Perfluorodecalin":  {"Tc_K": 566.0,  "Pc_MPa": 2.000,  "omega": 0.478},
    "1,3-Propanediol":   {"Tc_K": 722.0,  "Pc_MPa": 6.210,  "omega": 0.890},
    "Erythritol":        {"Tc_K": 773.0,  "Pc_MPa": 6.040,  "omega": 1.080},
    "TripropylPhosphate":{"Tc_K": 495.0,  "Pc_MPa": 1.610,  "omega": 0.769},
    "TributylPhosphate": {"Tc_K": 599.0,  "Pc_MPa": 1.520,  "omega": 0.989},
    "TriethylPhosphate": {"Tc_K": 582.0,  "Pc_MPa": 2.400,  "omega": 0.614},
    "Sorbitol":          {"Tc_K": 808.0,  "Pc_MPa": 6.400,  "omega": 1.480},
    "Chrysene":          {"Tc_K": 979.0,  "Pc_MPa": 2.600,  "omega": 0.612},
    "Camphene":          {"Tc_K": 638.0,  "Pc_MPa": 2.800,  "omega": 0.332},
    "Terpinolene":       {"Tc_K": 653.0,  "Pc_MPa": 2.600,  "omega": 0.401},
    "Myrcene":           {"Tc_K": 645.0,  "Pc_MPa": 2.800,  "omega": 0.428},
    "PerfluoroMethylDecalin": {"Tc_K": 566.0, "Pc_MPa": 2.000, "omega": 0.478},
    "PerfluoroTripropylamine": {"Tc_K": 551.0, "Pc_MPa": 1.670, "omega": 0.521},
    "Methanesulfonic":   {"Tc_K": 752.0,  "Pc_MPa": 7.710,  "omega": 0.770},
    "DinitrogenTetroxide":{"Tc_K": 431.2, "Pc_MPa": 10.10,  "omega": 0.825},
    "Perfluorobutylamine":{"Tc_K": 463.0, "Pc_MPa": 2.410,  "omega": 0.498},
    "PerfluorotributylAmine": {"Tc_K": 566.0, "Pc_MPa": 1.560, "omega": 0.648},
    "bis_HFE_7300":      {"Tc_K": 475.0,  "Pc_MPa": 1.980,  "omega": 0.510},
    "HydrofluoricAcid":  {"Tc_K": 461.0,  "Pc_MPa": 6.480,  "omega": 0.372},
    "PentafluoropropionicAcid": {"Tc_K": 497.0, "Pc_MPa": 2.890, "omega": 0.665},
    "DiMethylPeroxide":  {"Tc_K": 460.0,  "Pc_MPa": 4.500,  "omega": 0.350},
    "Bis2chloroethylether": {"Tc_K": 638.0, "Pc_MPa": 3.600, "omega": 0.540},
    "Coronene":          {"Tc_K": 1000.0, "Pc_MPa": 2.500,  "omega": 0.758},
}




def get_manual_properties(identifier: str) -> dict:
    """
    문헌 값 직접 반환.
    NIST에서 이미 얻은 값(not None)은 덮어쓰지 않도록 merge 방식 사용.

    Parameters
    ----------
    identifier : 화합물 이름

    Returns
    -------
    dict with Tc_K, Pc_MPa, omega (없으면 None)
    """
    return dict(MANUAL_PROPS.get(identifier, {"Tc_K": None, "Pc_MPa": None, "omega": None}))
