"""
NIST WebBook HTML 파싱 기반 열역학 물성 수집
CoolProp에 없는 화합물의 Tc, Pc, ω 보완용

수집 순서:
  1. 화합물명으로 NIST WebBook 검색
  2. 임계 물성(Tc [K], Pc [bar→MPa]) HTML 테이블 파싱
  3. 포화 증기압 API (Tr=0.7) → ω = -log10(Psat/Pc) - 1
"""

import re
import math
import time
import logging
import requests
from typing import Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

REQUEST_DELAY = 0.5
SEARCH_URL  = "https://webbook.nist.gov/cgi/cbook.cgi"
FLUID_URL   = "https://webbook.nist.gov/cgi/fluid.cgi"

# 화합물명 → NIST 검색명 매핑 (필요한 경우만)
NIST_NAME_MAP = {
    "1-Propanol":  "1-propanol",
    "2-Propanol":  "2-propanol",
    "1-Butanol":   "1-butanol",
    "Acetone":     "acetone",
    "AceticAcid":  "acetic acid",
    "Methanol":    "methanol",
    "Ethanol":     "ethanol",
    "Styrene":     "styrene",
    "Naphthalene": "naphthalene",
    "Benzene":     "benzene",
    "Toluene":     "toluene",
    "Hexane":      "hexane",
    "Heptane":     "heptane",
    "Octane":      "octane",
    "Nonane":      "nonane",
    "Decane":      "decane",
    "Undecane":    "undecane",
    "Dodecane":    "dodecane",
    "Helium":      "helium",
    "Neon":        "neon",
    "Hydrogen":    "hydrogen",
    "Deuterium":   "deuterium",
    "Nitrogen":    "nitrogen",
    "Oxygen":      "oxygen",
    "Fluorine":    "fluorine",
    "Argon":       "argon",
    "Krypton":     "krypton",
    "Cyclopentane":"cyclopentane",
    "Cyclohexane": "cyclohexane",
    "EthylBenzene":"ethylbenzene",
    "o-Xylene":    "o-xylene",
    "m-Xylene":    "m-xylene",
    "p-Xylene":    "p-xylene",
    # ── 정례2: C2 HFO ───────────────────────────────────────────────────────
    "R-1114":  "tetrafluoroethylene",
    "R-1132a": "1,1-difluoroethylene",
    "R-1123":  "trifluoroethylene",
    "R-1141":  "vinyl fluoride",
    "R-1113":  "chlorotrifluoroethylene",
    # ── 정례2: Br+F ──────────────────────────────────────────────────────────
    "R-13B1":  "bromotrifluoromethane",
    "R-12B1":  "bromochlorodifluoromethane",
    "R-22B1":  "difluorobromomethane",
    # ── 반례2: 삼중결합 ─────────────────────────────────────────────────────
    "Acetylene": "acetylene",
    "1-Butyne":  "1-butyne",
    "2-Butyne":  "2-butyne",
    # ── 반례2: C1~C2 염소화 ─────────────────────────────────────────────────
    "R-10":           "carbon tetrachloride",
    "R-20":           "chloroform",
    "R-30":           "dichloromethane",
    "Chloroethane":   "chloroethane",
    # ── 반례2: C2 Cl 불포화 ─────────────────────────────────────────────────
    "VinylideneChloride": "1,1-dichloroethylene",
    "Trichloroethylene":  "trichloroethylene",
    # ── 반례2: Br·I ──────────────────────────────────────────────────────────
    "Bromomethane":   "bromomethane",
    "Dibromomethane": "dibromomethane",
    "Iodomethane":    "iodomethane",
    # ── 반례2: C4~C5 불포화 ─────────────────────────────────────────────────
    "1,3-Butadiene": "1,3-butadiene",
    "Isoprene":      "isoprene",
    "Cyclobutane":   "cyclobutane",
    "Cyclopentene":  "cyclopentene",
    # ── 반례2: 할로겐화 방향족 ─────────────────────────────────────────────
    "Fluorobenzene":     "fluorobenzene",
    "Chlorobenzene":     "chlorobenzene",
    "Bromobenzene":      "bromobenzene",
    "Hexafluorobenzene": "hexafluorobenzene",
    # ── 반례2: 분지형 C6 ────────────────────────────────────────────────────
    "2-Methylpentane":    "2-methylpentane",
    "3-Methylpentane":    "3-methylpentane",
    "2,2-Dimethylbutane": "2,2-dimethylbutane",
    "2,3-Dimethylbutane": "2,3-dimethylbutane",
    # ── 반례2: 알킬 고리형 ──────────────────────────────────────────────────
    "Methylcyclopentane": "methylcyclopentane",
    "Methylcyclohexane":  "methylcyclohexane",
    # ── 반례2: 에폭사이드 ───────────────────────────────────────────────────
    "EthyleneOxide":  "ethylene oxide",
    "PropyleneOxide": "propylene oxide",
    # ── 반례2: 수소결합2 ────────────────────────────────────────────────────
    "1-Pentanol":     "1-pentanol",
    "EthyleneGlycol": "ethylene glycol",
    # ── 반례2: n-알케인 연장 ────────────────────────────────────────────────
    "Tridecane":  "tridecane",
    # ── 정례3: 추가 냉매 후보 ────────────────────────────────────────────────
    "R-245cb":      "1,1,1,2,2-pentafluoropropane",
    "R-245eb":      "1,1,1,2,3-pentafluoropropane",
    "R-236cb":      "1,1,1,2,2,3-hexafluoropropane",
    "R-263fb":      "1,1-difluoropropane",
    "R-253fb":      "1,1,3,3-tetrafluoropropane",
    "R-1225ye(E)":  "1,2,3,3,3-pentafluoroprop-1-ene",
    "R-1225ye(Z)":  "1,2,3,3,3-pentafluoroprop-1-ene",
    "R-1225zc":     "1,1,3,3,3-pentafluoroprop-1-ene",
    "R-1224yd(Z)":  "1-chloro-2,3,3,3-tetrafluoroprop-1-ene",
    "R-1233zd(Z)":  "1-chloro-3,3,3-trifluoroprop-1-ene",
    "R-1336mzz(Z)": "1,1,1,4,4,4-hexafluorobut-2-ene",
    "HFE-143m":    "methyl trifluoromethyl ether",
    "HFE-125":     "difluoromethyl trifluoromethyl ether",
    "HFE-134":     "bis(difluoromethyl) ether",
    "HFE-245mc":   "methyl pentafluoroethyl ether",
    "HFE-245fa2":  "2-(difluoromethoxy)-1,1,1-trifluoroethane",
    "SulfurHexafluoride": "sulfur hexafluoride",
    "Xenon":            "xenon",
    "HydrogenChloride": "hydrogen chloride",
    "R-143":    "1,1,2,2-tetrafluoroethane",
    "R-152":    "1,2-difluoroethane",
    "R-31":     "chlorofluoromethane",
    "R-133a":   "1-chloro-2,2,2-trifluoroethane",
    "R-132b":   "1-chloro-2,2-difluoroethane",
    "R-243fa":  "1-chloro-3,3,3-trifluoropropane",
    "R-244fa":  "3-chloro-1,1,1-trifluoropropane",
    "R-123a":   "1-chloro-1,2,2,2-tetrafluoroethane",
    "R-132":    "1,2-dichloro-1,2-difluoroethane",
    "R-141":    "1,1-dichloro-2-fluoroethane",
    "R-1354myfz": "(Z)-1,1,1,4,4,4-hexafluorobut-2-ene",
    "HFE-7000":   "methyl nonafluorobutyl ether",
    "R-E143a":    "trifluoromethyl methyl ether",
    "R-1122":     "1,1-dichloro-2,2-difluoroethylene",
    "R-1112a":    "1-chloro-1,2,2-trifluoroethylene",
    "R-1130":     "trans-1,2-dichloroethylene",
    "R-1130a":    "cis-1,2-dichloroethylene",
    "R-1233xf":   "2-chloro-3,3,3-trifluoropropene",
    "R-1232xf":   "1-chloro-3,3,3-trifluoropropene",
    "R-338mccq":  "1,1,1,2,3,4-hexafluorobutane",
    "HFE-449sl":  "methyl nonafluoroisobutyl ether",
    "R-30B2":     "dibromomethane",
    "R-20B3":     "bromoform",
    "R245cb":     "1,1,1,2,2-pentafluoropropane",
    "NitrogenTrifluoride": "nitrogen trifluoride",
    "Silane":     "silane",
    # ── 반례3: n-알케인 연장 ─────────────────────────────────────────────────
    "Tetradecane":  "tetradecane",
    "Pentadecane":  "pentadecane",
    "Hexadecane":   "hexadecane",
    # ── 반례3: 분지형 C7~C8 알케인 ───────────────────────────────────────────
    "2-MethylHexane":          "2-methylhexane",
    "3-MethylHexane":          "3-methylhexane",
    "2,2-DimethylPentane":     "2,2-dimethylpentane",
    "2,3-DimethylPentane":     "2,3-dimethylpentane",
    "2,4-DimethylPentane":     "2,4-dimethylpentane",
    "3,3-DimethylPentane":     "3,3-dimethylpentane",
    "3-EthylPentane":          "3-ethylpentane",
    "2,2,3-TrimethylButane":   "2,2,3-trimethylbutane",
    "2-MethylHeptane":         "2-methylheptane",
    "3-MethylHeptane":         "3-methylheptane",
    "4-MethylHeptane":         "4-methylheptane",
    "2,5-DimethylHexane":      "2,5-dimethylhexane",
    "2,2,4-TrimethylPentane":  "2,2,4-trimethylpentane",
    "2,3,4-TrimethylPentane":  "2,3,4-trimethylpentane",
    "2,2,3-TrimethylPentane":  "2,2,3-trimethylpentane",
    "2,3-DimethylHexane":      "2,3-dimethylhexane",
    "2,4-DimethylHexane":      "2,4-dimethylhexane",
    "3,4-DimethylHexane":      "3,4-dimethylhexane",
    "3-EthylHexane":           "3-ethylhexane",
    "2,2,5-TrimethylHexane":   "2,2,5-trimethylhexane",
    "2-Methyloctane":          "2-methyloctane",
    "4-Methyloctane":          "4-methyloctane",
    "2,2-DimethylHeptane":     "2,2-dimethylheptane",
    "2,6-DimethylHeptane":     "2,6-dimethylheptane",
    "2,2,3,3-TetramethylButane": "2,2,3,3-tetramethylbutane",
    # ── 반례3: 고리형·알켄 추가 ──────────────────────────────────────────────
    "Cycloheptane":  "cycloheptane",
    "Cyclooctane":   "cyclooctane",
    "Decalin":       "decahydronaphthalene",
    "1-Pentene":     "1-pentene",
    "1-Hexene":      "1-hexene",
    "1-Heptene":     "1-heptene",
    "1-Octene":      "1-octene",
    "2-Pentene":     "2-pentene",
    "Cyclohexene":   "cyclohexene",
    "2-Hexene":      "2-hexene",
    "3-Hexene":      "3-hexene",
    "C4F10":   "perfluorobutane",
    "C5F12":   "perfluoropentane",
    "C6F14":   "perfluorohexane",
    # ── 반례4: 알코올 ────────────────────────────────────────────────────────
    "1-Hexanol":       "1-hexanol",
    "1-Heptanol":      "1-heptanol",
    "1-Octanol":       "1-octanol",
    "1-Nonanol":       "1-nonanol",
    "1-Decanol":       "1-decanol",
    "1-Dodecanol":     "1-dodecanol",
    "2-Butanol":       "2-butanol",
    "2-Hexanol":       "2-hexanol",
    "Cyclohexanol":    "cyclohexanol",
    "BenzylAlcohol":   "benzyl alcohol",
    "Phenol":          "phenol",
    "Glycerol":        "glycerol",
    "PropyleneGlycol": "1,2-propanediol",
    "DiethyleneGlycol":"diethylene glycol",
    "TriethyleneGlycol":"triethylene glycol",
    "3-Pentanol":      "3-pentanol",
    "Cyclopentanol":   "cyclopentanol",
    "3-Methyl-2-Butanol": "3-methyl-2-butanol",
    "2-Methyl-2-Butanol": "2-methyl-2-butanol",
    "2-Methyl-1-Propanol": "isobutanol",
    "2-Methyl-1-Butanol":  "2-methyl-1-butanol",
    "3-Methyl-1-Butanol":  "3-methyl-1-butanol",
    "tert-Butanol":        "tert-butanol",
    "tert-Amyl-Alcohol":   "2-methyl-2-butanol",
    # ── 반례4: 카르복실산 ────────────────────────────────────────────────────
    "PropionicAcid":       "propionic acid",
    "ButyricAcid":         "butyric acid",
    "ValericAcid":         "pentanoic acid",
    "BenzoicAcid":         "benzoic acid",
    "ForamicAcid":         "formic acid",
    "TrifluoroaceticAcid": "trifluoroacetic acid",
    "HydrofluoricAcid":    "hydrogen fluoride",
    # ── 반례4: 에스터 ────────────────────────────────────────────────────────
    "MethylAcetate":      "methyl acetate",
    "EthylAcetate":       "ethyl acetate",
    "PropylAcetate":      "propyl acetate",
    "ButylAcetate":       "butyl acetate",
    "EthylPropanoate":    "ethyl propanoate",
    "MethylButanoate":    "methyl butanoate",
    "DiethylCarbonate":   "diethyl carbonate",
    "MethylFormate":      "methyl formate",
    "EthylFormate":       "ethyl formate",
    "MethylPropanoate":   "methyl propanoate",
    "IsoPropylAcetate":   "isopropyl acetate",
    "IsoButylAcetate":    "isobutyl acetate",
    "MethylAcrylate":     "methyl acrylate",
    "EthylAcrylate":      "ethyl acrylate",
    "MethylMethacrylate": "methyl methacrylate",
    "VinylAcetate":       "vinyl acetate",
    "DimethylOxalate":    "dimethyl oxalate",
    "EthylBenzoate":      "ethyl benzoate",
    "MethylBenzoate":     "methyl benzoate",
    "EthylLactate":       "ethyl lactate",
    "DimethylPhthalate":  "dimethyl phthalate",
    "DiethylPhthalate":   "diethyl phthalate",
    "DimethylSuccinate":  "dimethyl succinate",
    # ── 반례5: 케톤 ──────────────────────────────────────────────────────────
    "MethylEthylKetone":    "2-butanone",
    "DiethylKetone":        "3-pentanone",
    "MethylIsobutylKetone": "4-methyl-2-pentanone",
    "Cyclohexanone":        "cyclohexanone",
    "Acetophenone":         "acetophenone",
    "MethylPropylKetone":   "2-pentanone",
    "2-Heptanone":          "2-heptanone",
    "4-Heptanone":          "4-heptanone",
    "Cyclopentanone":       "cyclopentanone",
    "Benzophenone":         "benzophenone",
    "Isophorone":           "isophorone",
    # ── 반례5: 알데히드 ──────────────────────────────────────────────────────
    "Acetaldehyde":    "acetaldehyde",
    "Propionaldehyde": "propanal",
    "Butyraldehyde":   "butanal",
    "Benzaldehyde":    "benzaldehyde",
    "Furfural":        "furfural",
    # ── 반례5: 니트릴 ────────────────────────────────────────────────────────
    "Acetonitrile":  "acetonitrile",
    "Propionitrile": "propionitrile",
    "Benzonitrile":  "benzonitrile",
    "Acrylonitrile": "acrylonitrile",
    # ── 반례5: 아민 ──────────────────────────────────────────────────────────
    "Trimethylamine":  "trimethylamine",
    "Triethylamine":   "triethylamine",
    "Aniline":         "aniline",
    "Pyridine":        "pyridine",
    "Morpholine":      "morpholine",
    "Piperidine":      "piperidine",
    "DimethylAmine":   "dimethylamine",
    "DiethylAmine":    "diethylamine",
    "Butylamine":      "butylamine",
    "Cyclohexylamine": "cyclohexylamine",
    "Dibutylamine":    "dibutylamine",
    "Quinoline":       "quinoline",
    "Isoquinoline":    "isoquinoline",
    # ── 반례5: 에테르 ────────────────────────────────────────────────────────
    "DipropylEther":  "dipropyl ether",
    "DibutylEther":   "dibutyl ether",
    "THF":            "tetrahydrofuran",
    "Dioxane":        "1,4-dioxane",
    "Anisole":        "anisole",
    "MTBE":           "tert-butyl methyl ether",
    "Tetrahydropyran":"tetrahydropyran",
    "1,3-Dioxolane":  "1,3-dioxolane",
    # ── 반례5: 황 화합물 ──────────────────────────────────────────────────────
    "CarbonDisulfide":   "carbon disulfide",
    "DMSO":              "dimethyl sulfoxide",
    "DimethylSulfide":   "dimethyl sulfide",
    "Thiophene":         "thiophene",
    "Methanethiol":      "methanethiol",
    "DiethylSulfide":    "diethyl sulfide",
    "Dimethyldisulfide": "dimethyl disulfide",
    # ── 반례5: 질소 화합물 ────────────────────────────────────────────────────
    "Nitromethane":         "nitromethane",
    "Nitroethane":          "nitroethane",
    "NNDimethylFormamide":  "N,N-dimethylformamide",
    "Formamide":            "formamide",
    "Acetamide":            "acetamide",
    "NDimethylAcetamide":   "N,N-dimethylacetamide",
    # ── 반례6: 방향족 추가 ────────────────────────────────────────────────────
    "Cumene":              "cumene",
    "Mesitylene":          "1,3,5-trimethylbenzene",
    "Pseudocumene":        "1,2,4-trimethylbenzene",
    "Indene":              "indene",
    "Tetralin":            "1,2,3,4-tetrahydronaphthalene",
    "Biphenyl":            "biphenyl",
    "1-MethylNaphthalene": "1-methylnaphthalene",
    "Propylbenzene":           "propylbenzene",
    "1,2,3-Trimethylbenzene":  "1,2,3-trimethylbenzene",
    "Butylbenzene":            "butylbenzene",
    "Isobutylbenzene":         "isobutylbenzene",
    # ── 반례6: 헤테로고리 ─────────────────────────────────────────────────────
    "Furan":              "furan",
    "Pyrrole":            "pyrrole",
    "Indole":             "indole",
    "Imidazole":          "imidazole",
    "NMethylPyrrolidone": "N-methyl-2-pyrrolidinone",
    "Benzofuran":         "benzofuran",
    "2-Methylfuran":      "2-methylfuran",
    # ── 반례6: C3~C5 염소화 ───────────────────────────────────────────────────
    "1-Chloropropane":       "1-chloropropane",
    "2-Chloropropane":       "2-chloropropane",
    "1-Chlorobutane":        "1-chlorobutane",
    "2-Chlorobutane":        "2-chlorobutane",
    "1-Chloropentane":       "1-chloropentane",
    "1,2-Dichloropropane":   "1,2-dichloropropane",
    "1,3-Dichloropropane":   "1,3-dichloropropane",
    "1,1,1-Trichloroethane": "1,1,1-trichloroethane",
    "1,1,2-Trichloroethane": "1,1,2-trichloroethane",
    "1-Chloro-2-Methylbutane": "1-chloro-2-methylbutane",
    "1,2-Dichloropentane":     "1,2-dichloropentane",
    # ── 반례6: Br·I C3+ ───────────────────────────────────────────────────────
    "1-Bromopropane":  "1-bromopropane",
    "2-Bromopropane":  "2-bromopropane",
    "1-Bromobutane":   "1-bromobutane",
    "Bromoethane":     "bromoethane",
    "1-Iodopropane":   "1-iodopropane",
    "1-Iodobutane":    "1-iodobutane",
    "1-Chlorohexane":  "1-chlorohexane",
    "1-Bromooctane":   "1-bromooctane",
    "1-Bromohexane":   "1-bromohexane",
    "1-Chlorooctane":  "1-chlorooctane",
    # ── 반례6: 불소화 방향족 ──────────────────────────────────────────────────
    "1,2-Difluorobenzene": "1,2-difluorobenzene",
    "1,3-Difluorobenzene": "1,3-difluorobenzene",
    "1,4-Difluorobenzene": "1,4-difluorobenzene",
    "Trifluorotoluene":    "benzotrifluoride",
    "Pentafluorobenzene":  "pentafluorobenzene",
    "2-Chlorotoluene":     "2-chlorotoluene",
    "4-Chlorotoluene":     "4-chlorotoluene",
    "4-Fluorotoluene":     "4-fluorotoluene",
    "4-Chlorofluorobenzene": "1-chloro-4-fluorobenzene",
    # ── 반례6: 방향족 Cl 추가 ─────────────────────────────────────────────────
    "1,2-Dichlorobenzene":    "1,2-dichlorobenzene",
    "1,3-Dichlorobenzene":    "1,3-dichlorobenzene",
    "1,4-Dichlorobenzene":    "1,4-dichlorobenzene",
    "1,2,4-Trichlorobenzene": "1,2,4-trichlorobenzene",
    # ── 반례6: 할로 C1C2 추가 ─────────────────────────────────────────────────
    "1,1-Dichloroethane":        "1,1-dichloroethane",
    "1,1,1,2-Tetrachloroethane": "1,1,1,2-tetrachloroethane",
    "Hexachloroethane":          "hexachloroethane",
    "1,2-Dibromoethane":         "1,2-dibromoethane",
    "Dibromochloromethane":      "dibromochloromethane",
    "Bromoform":                 "bromoform",
    "Iodoform":                  "iodoform",
    # ── 반례7: 다환 방향족 ────────────────────────────────────────────────────
    "Anthracene":   "anthracene",
    "Phenanthrene": "phenanthrene",
    "Fluorene":     "fluorene",
    # ── 반례9: 반응성 C3 불포화 ───────────────────────────────────────────────
    "Allylchloride":    "3-chloropropene",
    "Acrolein":         "acrolein",
    "PropargylAlcohol": "prop-2-yn-1-ol",
    # ── 반례10: 테르펜 ────────────────────────────────────────────────────────
    "Limonene":     "limonene",
    "aAlphaPinene": "alpha-pinene",
    "Camphene":     "camphene",
    # ── 반례10: 실란 ──────────────────────────────────────────────────────────
    "Tetramethylsilane": "tetramethylsilane",
    # ── 반례10: 글리콜 에테르 ─────────────────────────────────────────────────
    "EthyleneGlycolMonoethylEther":    "2-ethoxyethanol",
    "EthyleneGlycolMonobutylEther":    "2-butoxyethanol",
    "DiethyleneGlycolMonomethylEther": "diethylene glycol monomethyl ether",
    "1,3-Propanediol": "1,3-propanediol",
    "1,4-Butanediol":  "1,4-butanediol",
    # ── 반례11: 방향족 O ──────────────────────────────────────────────────────
    "Catechol":   "catechol",
    "Resorcinol": "resorcinol",
    "Guaiacol":   "guaiacol",
    # ── 반례: 불소화 특수 케톤 ────────────────────────────────────────────────
    "Novec1230": "1,1,1,2,2,4,5,5,5-nonafluoro-4-(trifluoromethyl)-3-pentanone",
}


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _get_nist_id(name: str) -> Optional[str]:
    """
    화합물명으로 NIST WebBook을 검색해 NIST ID (e.g. 'C67641') 반환.

    우선순위:
    1. "Phase change data" 링크의 ID
    2. 검색 결과 목록 첫 번째 항목의 ID
    3. 페이지 내 링크에서 가장 많이 등장하는 ID (최빈값)
    """
    search_name = NIST_NAME_MAP.get(name, name)
    params = {"Name": search_name, "Units": "SI"}
    try:
        resp = requests.get(SEARCH_URL, params=params, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"[NIST] 검색 실패 ({name}): {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # 1순위: "Phase change data" 링크에서 ID 추출 (가장 신뢰할 수 있음)
    for a in soup.find_all("a", href=True):
        if "phase change" in a.get_text(strip=True).lower():
            m = re.search(r"ID=(C\d+)", a["href"])
            if m:
                return m.group(1)

    # 2순위: 검색 결과 목록 <ol> 첫 번째 항목
    ol = soup.find("ol")
    if ol:
        first_link = ol.find("a", href=re.compile(r"ID=C\d+"))
        if first_link:
            m = re.search(r"ID=(C\d+)", first_link["href"])
            if m:
                return m.group(1)

    # 3순위: 페이지 내 최빈 ID (다른 화합물 링크 제외)
    from collections import Counter
    id_counts: Counter = Counter()
    for a in soup.find_all("a", href=re.compile(r"ID=C\d+")):
        m = re.search(r"ID=(C\d+)", a["href"])
        if m:
            id_counts[m.group(1)] += 1
    if id_counts:
        return id_counts.most_common(1)[0][0]

    return None


def _fetch_nist_phase_page(nist_id: str) -> Optional[BeautifulSoup]:
    """
    NIST ID로 Phase Change Data 페이지(Mask=4) 조회 → BeautifulSoup 반환
    이 페이지에 Tc [K], Pc [bar] 가 포함되어 있음
    """
    params = {"ID": nist_id, "Units": "SI", "Mask": "4"}
    try:
        resp = requests.get(SEARCH_URL, params=params, timeout=15)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        logger.warning(f"[NIST] Phase 페이지 실패 ({nist_id}): {e}")
        return None


def _parse_critical_props(soup: BeautifulSoup) -> dict:
    """
    Phase Change Data 페이지 HTML 테이블에서 Tc [K], Pc [MPa] 파싱
    NIST 테이블 형식: Quantity | Value | Units | Method | Reference | Comment
      - Quantity 셀이 'Tc' 또는 'Pc' (정확 매칭, 대소문자 무시)
      - Pc 단위는 bar → ×0.1 → MPa
    """
    result = {"Tc_K": None, "Pc_MPa": None}

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) < 3:
                continue

            quantity = cells[0].strip()
            value_str = cells[1]
            unit = cells[2].strip() if len(cells) > 2 else ""

            # 값 파싱: "508. ± 2." → 508.0  または "536.9 ± 0.8" → 536.9
            m = re.match(r"([\d.]+)", value_str.replace(",", ""))
            if not m:
                continue
            val = float(m.group(1))

            if quantity == "Tc" and result["Tc_K"] is None:
                if unit.lower() == "k":
                    result["Tc_K"] = round(val, 4)
                elif "°c" in unit.lower():
                    result["Tc_K"] = round(val + 273.15, 4)

            elif quantity == "Pc" and result["Pc_MPa"] is None:
                unit_lower = unit.lower()
                if "mpa" in unit_lower:
                    result["Pc_MPa"] = round(val, 6)
                elif unit_lower == "bar":
                    result["Pc_MPa"] = round(val * 0.1, 6)
                elif "kpa" in unit_lower:
                    result["Pc_MPa"] = round(val / 1000, 6)
                elif "atm" in unit_lower:
                    result["Pc_MPa"] = round(val * 0.101325, 6)
                elif "pa" in unit_lower:
                    result["Pc_MPa"] = round(val / 1e6, 6)

    return result


def _get_psat_from_fluid_api(nist_id: str, T_ref: float) -> Optional[float]:
    """
    NIST fluid.cgi API로 Psat [MPa] 조회.
    화합물이 NIST 유체 DB에 없으면 None 반환.
    """
    url = (
        f"{FLUID_URL}?Action=Load&ID={nist_id}&Type=SatT&Digits=5"
        f"&THigh={T_ref}&TLow={T_ref}&TInc=1&RefState=DEF"
        f"&TUnit=K&PUnit=MPa&DUnit=mol%2Fl&HUnit=kJ%2Fmol"
        f"&WUnit=m%2Fs&VisUnit=uPa*s&STUnit=N%2Fm"
    )
    try:
        resp = requests.get(url, timeout=15)
        if not resp.ok:
            return None
    except Exception:
        return None

    if "query error" in resp.text.lower() or "not available" in resp.text.lower():
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])]
        p_idx = next((i for i, h in enumerate(headers) if "pressure" in h), None)
        if p_idx is None:
            continue
        for row in rows[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) <= p_idx:
                continue
            try:
                psat = float(cells[p_idx])
                if psat > 0:
                    return psat   # MPa
            except ValueError:
                continue
    return None


def _get_psat_from_antoine(phase_soup: BeautifulSoup, T_ref: float) -> Optional[float]:
    """
    Phase Change 페이지의 Antoine 계수 테이블에서 Psat [MPa] 계산
    NIST Antoine:  log10(P/bar) = A - B / (T/K + C)

    1순위: T_ref 가 온도 범위 내인 항목
    2순위: T_ref 와 T_high 거리가 가장 가까운 항목 (온도 범위 밖 허용)
    """
    candidates = []  # (dist_from_range, A, B, C)

    for table in phase_soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [td.get_text(strip=True) for td in rows[0].find_all(["td", "th"])]
        headers_lower = [h.lower() for h in headers]
        # Antoine 테이블 헤더: 'Temperature (K)' + 'A' 'B' 'C'
        if not (any("temperature" in h for h in headers_lower)
                and "A" in headers and "B" in headers and "C" in headers):
            continue

        a_idx = headers.index("A")
        b_idx = headers.index("B")
        c_idx = headers.index("C")

        for row in rows[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) <= max(a_idx, b_idx, c_idx):
                continue
            try:
                t_nums = re.findall(r"[\d.]+", cells[0])
                t_low  = float(t_nums[0]) if len(t_nums) >= 1 else None
                t_high = float(t_nums[1]) if len(t_nums) >= 2 else t_low

                A = float(cells[a_idx])
                B = float(cells[b_idx])
                C = float(cells[c_idx])

                # 범위 내 거리 (0이면 범위 내)
                if t_low is not None and t_high is not None:
                    if t_low <= T_ref <= t_high:
                        dist = 0.0
                    else:
                        dist = min(abs(T_ref - t_low), abs(T_ref - t_high))
                else:
                    dist = 999.0

                candidates.append((dist, A, B, C))
            except (ValueError, IndexError):
                continue

    # 가장 가까운 Antoine 계수 사용
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    _, A, B, C = candidates[0]
    try:
        log_p_bar = A - B / (T_ref + C)
        psat_mpa  = (10 ** log_p_bar) * 0.1
        return psat_mpa
    except (ZeroDivisionError, OverflowError):
        return None


def _get_acentric_factor(
    nist_id: str, Tc_K: float, Pc_MPa: float,
    phase_soup: Optional[BeautifulSoup] = None
) -> Optional[float]:
    """
    Tr=0.7 에서 Psat 를 얻어 ω = -log10(Psat/Pc) - 1 계산.
    1순위: NIST fluid.cgi API
    2순위: Antoine 방정식 (phase_soup 필요)
    """
    T_ref = round(0.7 * Tc_K, 2)

    psat = _get_psat_from_fluid_api(nist_id, T_ref)

    if psat is None and phase_soup is not None:
        logger.debug(f"[NIST] fluid API 없음 → Antoine 방정식 사용 ({nist_id})")
        psat = _get_psat_from_antoine(phase_soup, T_ref)

    if psat is None or Pc_MPa <= 0:
        logger.warning(f"[NIST] Psat 계산 실패: {nist_id}")
        return None

    omega = -math.log10(psat / Pc_MPa) - 1
    return round(omega, 6)


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------

def get_nist_properties(identifier: str) -> dict:
    """
    NIST WebBook에서 Tc, Pc, ω 조회

    Parameters
    ----------
    identifier : 화합물 이름 (NIST_NAME_MAP 키 또는 직접 이름)

    Returns
    -------
    dict with Tc_K, Pc_MPa, omega (없으면 None)
    """
    base = {"Tc_K": None, "Pc_MPa": None, "omega": None}

    # 1. NIST ID 조회
    nist_id = _get_nist_id(identifier)
    if nist_id is None:
        logger.warning(f"[NIST] ID 없음: {identifier}")
        return base

    logger.info(f"[NIST] {identifier} → ID={nist_id}")
    time.sleep(REQUEST_DELAY)

    # 2. Phase Change 페이지에서 Tc, Pc 파싱
    soup = _fetch_nist_phase_page(nist_id)
    if soup is None:
        return base

    props = _parse_critical_props(soup)
    base.update(props)

    if base["Tc_K"] is None or base["Pc_MPa"] is None:
        logger.warning(f"[NIST] 임계 물성 파싱 실패: {identifier}")
        return base

    logger.info(f"[NIST] {identifier}: Tc={base['Tc_K']} K, Pc={base['Pc_MPa']} MPa")

    # 3. 포화 증기압 API로 ω 계산 (fluid API → Antoine 방정식 fallback)
    time.sleep(REQUEST_DELAY)
    omega = _get_acentric_factor(nist_id, base["Tc_K"], base["Pc_MPa"], phase_soup=soup)
    base["omega"] = omega
    if omega is not None:
        logger.info(f"[NIST] {identifier}: ω={omega:.4f}")
    else:
        logger.warning(f"[NIST] ω 계산 실패: {identifier}")

    return base
