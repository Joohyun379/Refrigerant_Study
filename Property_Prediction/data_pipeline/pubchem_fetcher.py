"""
PubChem Data Pipeline for Refrigerant Property Prediction
분자구조(SMILES, InChI, 분자량 등) 수집 전용
열역학 물성(Tc, Pc, ω)은 coolprop_fetcher.py 에서 담당
"""

import requests
import pandas as pd
import time
import json
import logging
from typing import Optional
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
# VIEW_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view"
REQUEST_DELAY = 0.3  # PubChem rate limit: max 5 req/sec


# ---------------------------------------------------------------------------
# 냉매 번호 → PubChem 검색용 이름 매핑
# (PubChem이 냉매 번호를 직접 인식하지 못하는 경우 IUPAC명 사용)
# ---------------------------------------------------------------------------

PUBCHEM_NAME_MAP = {
    # ── 기존 냉매 ──────────────────────────────────────────────────────────
    "R-22":       "Chlorodifluoromethane",
    "R-23":       "Trifluoromethane",
    "R-32":       "Difluoromethane",
    "R-40":       "Chloromethane",
    "R-41":       "Fluoromethane",
    "R-116":      "Hexafluoroethane",
    "R-125":      "Pentafluoroethane",
    "R-134a":     "1,1,1,2-Tetrafluoroethane",
    "R-143a":     "1,1,1-Trifluoroethane",
    "R-152a":     "1,1-Difluoroethane",
    "R-161":      "Fluoroethane",
    "R-227ea":    "1,1,1,2,3,3,3-Heptafluoropropane",
    "R-236ea":    "1,1,1,2,3,3-Hexafluoropropane",
    "R-236fa":    "1,1,1,3,3,3-Hexafluoropropane",
    "R-245ca":    "1,1,2,2,3-Pentafluoropropane",
    "R-245fa":    "1,1,1,3,3-Pentafluoropropane",
    "R-290":      "Propane",
    "R-365mfc":   "1,1,1,3,3-Pentafluorobutane",
    "R-600":      "Butane",
    "R-600a":     "Isobutane",
    "R-717":      "Ammonia",
    "R-718":      "Water",
    "R-744":      "Carbon dioxide",
    # ── HFO ────────────────────────────────────────────────────────────────
    "R-1233zd(E)": "(E)-1-chloro-3,3,3-trifluoroprop-1-ene",
    "R-1234yf":    "2,3,3,3-Tetrafluoroprop-1-ene",
    "R-1234ze(E)": "1,3,3,3-Tetrafluoroprop-1-ene",
    "R-1234ze(Z)": "1,3,3,3-Tetrafluoroprop-1-ene",
    "R-1243zf":    "3,3,3-Trifluoroprop-1-ene",
    # ── 완전 불소화 ─────────────────────────────────────────────────────────
    "R-14":       "Carbon tetrafluoride",
    "R-218":      "Perfluoropropane",
    "RC318":      "Perfluorocyclobutane",
    # ── 탄화수소 / 자연 냉매 ───────────────────────────────────────────────
    "Methane":        "Methane",
    "Ethane":         "Ethane",
    "Ethylene":       "Ethylene",
    "Propane":        "Propane",
    "Propylene":      "Propylene",
    "Pentane":        "Pentane",
    "Isopentane":     "Isopentane",
    "Neopentane":     "Neopentane",
    "1-Butene":       "1-Butene",
    "cis-2-Butene":   "cis-2-Butene",
    "trans-2-Butene": "trans-2-Butene",
    # ── HCFC 레거시 ────────────────────────────────────────────────────────
    "R-11":    "Trichlorofluoromethane",
    "R-12":    "Dichlorodifluoromethane",
    "R-13":    "Chlorotrifluoromethane",
    "R-21":    "Dichlorofluoromethane",
    "R-113":   "1,1,2-Trichloro-1,2,2-trifluoroethane",
    "R-114":   "1,2-Dichloro-1,1,2,2-tetrafluoroethane",
    "R-115":   "Chloropentafluoroethane",
    "R-123":   "2,2-Dichloro-1,1,1-trifluoroethane",
    "R-124":   "2-Chloro-1,1,1,2-tetrafluoroethane",
    "R-141b":  "1,1-Dichloro-1-fluoroethane",
    "R-142b":  "1-Chloro-1,1-difluoroethane",
    # ── HFC 추가 ─────────────────────────────────────────────────────────
    "R-13I1":       "Trifluoroiodomethane",
    "R-1336mzz(E)": "(E)-1,1,1,4,4,4-hexafluorobut-2-ene",
    "R-1336mzz":    "1,1,1,4,4,4-Hexafluoro-2-butene",
    # ── 기타 소형 냉매 ────────────────────────────────────────────────────
    "SulfurDioxide": "Sulfur dioxide",
    "DimethylEther": "Dimethyl ether",
    "CycloPropane":  "Cyclopropane",
    # ── 반례: Tc 너무 낮음 ─────────────────────────────────────────────────
    "CarbonMonoxide": "Carbon monoxide",
    "ParaHydrogen":   "Hydrogen",   # PubChem은 동위체 구분 없음
    # ── 반례: Tc 너무 높음 (방향족) ──────────────────────────────────────
    "EthylBenzene": "Ethylbenzene",
    "o-Xylene":     "1,2-Dimethylbenzene",
    "m-Xylene":     "1,3-Dimethylbenzene",
    "p-Xylene":     "1,4-Dimethylbenzene",
    # ── 반례: 실록산 대분자 ────────────────────────────────────────────────
    "MM":   "Hexamethyldisiloxane",
    "MDM":  "Octamethyltrisiloxane",
    "MD2M": "Decamethyltetrasiloxane",
    "MD3M": "Dodecamethylpentasiloxane",
    "MD4M": "Tetradecamethylhexasiloxane",
    "D4":   "Octamethylcyclotetrasiloxane",
    "D5":   "Decamethylcyclopentasiloxane",
    "D6":   "Dodecamethylcyclohexasiloxane",
    # ── 정례2: C2 HFO (이중결합 불소화 에틸렌) ────────────────────────────
    "R-1114":  "Tetrafluoroethylene",
    "R-1132a": "1,1-Difluoroethylene",
    "R-1123":  "Trifluoroethylene",
    "R-1141":  "Vinyl fluoride",
    "R-1113":  "Chlorotrifluoroethylene",
    # ── 정례2: C1~C2 Br+F 할로겐화 ──────────────────────────────────────────
    "R-13B1":  "Bromotrifluoromethane",
    "R-12B1":  "Bromochlorodifluoromethane",
    "R-22B1":  "Difluorobromomethane",
    # ── 정례2: 소형 극성 무기 ────────────────────────────────────────────────
    "NitrousOxide":    "Nitrous oxide",
    "HydrogenSulfide": "Hydrogen sulfide",
    "CarbonylSulfide": "Carbonyl sulfide",
    # ── 반례2: 삼중결합 알카인 ───────────────────────────────────────────────
    "Acetylene":  "Acetylene",
    "Propyne":    "Propyne",
    "1-Butyne":   "1-Butyne",
    "2-Butyne":   "2-Butyne",
    # ── 반례2: C1~C2 완전 염소화 ────────────────────────────────────────────
    "R-10":           "Carbon tetrachloride",
    "R-20":           "Chloroform",
    "R-30":           "Dichloromethane",
    "Chloroethane":   "Chloroethane",
    "Dichloroethane": "1,2-Dichloroethane",
    # ── 반례2: C2 Cl 불포화 ─────────────────────────────────────────────────
    "VinylideneChloride": "1,1-Dichloroethylene",
    "Trichloroethylene":  "Trichloroethylene",
    # ── 반례2: C1~C2 Br·I ────────────────────────────────────────────────────
    "Bromomethane":   "Bromomethane",
    "Dibromomethane": "Dibromomethane",
    "Iodomethane":    "Iodomethane",
    # ── 반례2: C4~C5 불포화 ─────────────────────────────────────────────────
    "IsoButene":     "2-Methylpropene",
    "1,3-Butadiene": "1,3-Butadiene",
    "Isoprene":      "Isoprene",
    "Cyclobutane":   "Cyclobutane",
    "Cyclopentene":  "Cyclopentene",
    # ── 반례2: 할로겐화 방향족 ───────────────────────────────────────────────
    "Fluorobenzene":     "Fluorobenzene",
    "Chlorobenzene":     "Chlorobenzene",
    "Bromobenzene":      "Bromobenzene",
    "Hexafluorobenzene": "Hexafluorobenzene",
    # ── 반례2: 분지형 C6 알케인 ─────────────────────────────────────────────
    "2-Methylpentane":    "2-Methylpentane",
    "3-Methylpentane":    "3-Methylpentane",
    "2,2-Dimethylbutane": "2,2-Dimethylbutane",
    "2,3-Dimethylbutane": "2,3-Dimethylbutane",
    # ── 반례2: 에테르·카보네이트 ─────────────────────────────────────────────
    "DiethylEther":      "Diethyl ether",
    "DimethylCarbonate": "Dimethyl carbonate",
    # ── 반례2: 알킬 고리형 ────────────────────────────────────────────────────
    "Methylcyclopentane": "Methylcyclopentane",
    "Methylcyclohexane":  "Methylcyclohexane",
    # ── 반례2: 에폭사이드 ─────────────────────────────────────────────────────
    "EthyleneOxide":  "Ethylene oxide",
    "PropyleneOxide": "Propylene oxide",
    # ── 반례2: 수소결합2 ──────────────────────────────────────────────────────
    "1-Pentanol":     "1-Pentanol",
    "EthyleneGlycol": "Ethylene glycol",
    # ── 반례2: n-알케인 연장 ─────────────────────────────────────────────────
    "Tridecane": "Tridecane",
    # ── 반례: 수소결합 알코올/산 ────────────────────────────────────────────
    "1-Propanol": "1-propanol",
    "2-Propanol": "2-propanol",
    "1-Butanol":  "1-butanol",
    "AceticAcid": "acetic acid",
    "Acetone":    "acetone",
    # ── 반례: 추가 방향족 ───────────────────────────────────────────────────
    "Styrene":     "styrene",
    "Naphthalene": "naphthalene",
    # ── 반례: Tc 너무 낮음 (희귀 기체) ────────────────────────────────────
    "Helium":    "helium",
    "Neon":      "neon",
    "Hydrogen":  "hydrogen",
    "Deuterium": "deuterium",
    "Nitrogen":  "nitrogen",
    "Oxygen":    "oxygen",
    "Fluorine":  "fluorine",
    "Argon":     "argon",
    "Krypton":   "krypton",
    # ── 반례: Tc 너무 높음 n-알케인 ────────────────────────────────────────
    "Hexane":   "hexane",
    "Heptane":  "heptane",
    "Octane":   "octane",
    "Nonane":   "nonane",
    "Decane":   "decane",
    "Undecane": "undecane",
    "Dodecane": "dodecane",
    # ── 반례: Tc 너무 높음 고리형 ──────────────────────────────────────────
    "Cyclopentane": "cyclopentane",
    "Cyclohexane":  "cyclohexane",
    "Benzene":      "benzene",
    "Toluene":      "toluene",
    "Methanol":     "methanol",
    "Ethanol":      "ethanol",
    # ── 정례3: 추가 냉매 후보 ──────────────────────────────────────────────
    "R-245cb":      "1,1,1,2,2-Pentafluoropropane",
    "R-245eb":      "1,1,1,2,3-Pentafluoropropane",
    "R-236cb":      "1,1,1,2,2,3-Hexafluoropropane",
    "R-263fb":      "1,1-Difluoropropane",
    "R-253fb":      "1,1,3,3-Tetrafluoropropane",
    "R-1225ye(E)":  "(E)-1,2,3,3,3-Pentafluoroprop-1-ene",
    "R-1225ye(Z)":  "(Z)-1,2,3,3,3-Pentafluoroprop-1-ene",
    "R-1225zc":     "1,1,3,3,3-Pentafluoroprop-1-ene",
    "R-1224yd(Z)":  "(Z)-1-Chloro-2,3,3,3-tetrafluoroprop-1-ene",
    "R-1233zd(Z)":  "(Z)-1-Chloro-3,3,3-trifluoroprop-1-ene",
    "R-1336mzz(Z)": "(Z)-1,1,1,4,4,4-Hexafluorobut-2-ene",
    "HFE-143m":     "Methyl trifluoromethyl ether",
    "HFE-125":      "methyl 1,1,2,2-tetrafluoroethyl ether",
    "HFE-134":      "Bis(difluoromethyl) ether",
    "HFE-245mc":    "Methyl pentafluoroethyl ether",
    "HFE-245fa2":   "2-(Difluoromethoxy)-1,1,1-trifluoroethane",
    "SulfurHexafluoride": "Sulfur hexafluoride",
    "Xenon":            "Xenon",
    "HydrogenChloride": "Hydrogen chloride",
    "R-143":   "1,1,2,2-Tetrafluoroethane",
    "R-152":   "1,2-Difluoroethane",
    "R-31":    "Chlorofluoromethane",
    "R-133a":  "1-Chloro-2,2,2-trifluoroethane",
    "R-132b":  "1-Chloro-2,2-difluoroethane",
    "R-243fa": "1-Chloro-3,3,3-trifluoropropane",
    "R-244fa": "3-Chloro-1,1,1-trifluoropropane",
    "R-234ab": "1,2-Dichloro-1,2,3,3,3-pentafluoropropane",
    "R-123a":  "1,2-dichloro-1,1,2-trifluoroethane",
    "R-132":   "1,2-Dichloro-1,2-difluoroethane",
    "R-141":   "1,1-Dichloro-2-fluoroethane",
    "R-1354myfz": "1,1,1,4,4,4-hexafluorobut-2-yne",  # TODO: 구조 미확인, 재조사 필요
    "R-338mccq":  "1,1,1,2,3,4-Hexafluorobutane",
    "HFE-7000":   "Methyl nonafluorobutyl ether",
    "R-E143a":    "Trifluoromethyl methyl ether",
    "R-1122":     "1-chloro-2,2-difluoroethylene",
    "R-1112a":    "1,1-Dichloro-2,2-difluoroethylene",
    "R-1130":     "trans-1,2-Dichloroethylene",
    "R-1130a":    "cis-1,2-Dichloroethylene",
    "R-1233xf":   "2-Chloro-3,3,3-trifluoropropene",
    "R-1232xf":   "1,2-dichloro-3,3,3-trifluoroprop-1-ene",
    "NitrogenTrifluoride": "Nitrogen trifluoride",
    "Silane":    "Silane",
    "HFE-449sl": "Methyl nonafluoroisobutyl ether",
    "R-30B2":    "Dibromomethane",
    "R-20B3":    "Bromoform",
    "R245cb":    "1,1,1,2,2-Pentafluoropropane",
    # ── 반례3: n-알케인 추가 ───────────────────────────────────────────────
    "Tetradecane": "Tetradecane",
    "Pentadecane": "Pentadecane",
    "Hexadecane":  "Hexadecane",
    # ── 반례3: 분지형 C7~C9 알케인 ────────────────────────────────────────
    "2-MethylHexane":          "2-Methylhexane",
    "3-MethylHexane":          "3-Methylhexane",
    "2,2-DimethylPentane":     "2,2-Dimethylpentane",
    "2,3-DimethylPentane":     "2,3-Dimethylpentane",
    "2,4-DimethylPentane":     "2,4-Dimethylpentane",
    "3,3-DimethylPentane":     "3,3-Dimethylpentane",
    "3-EthylPentane":          "3-Ethylpentane",
    "2,2,3-TrimethylButane":   "2,2,3-Trimethylbutane",
    "2-MethylHeptane":         "2-Methylheptane",
    "3-MethylHeptane":         "3-Methylheptane",
    "4-MethylHeptane":         "4-Methylheptane",
    "2,5-DimethylHexane":      "2,5-Dimethylhexane",
    "2,2,4-TrimethylPentane":  "2,2,4-Trimethylpentane",
    "2,3,4-TrimethylPentane":  "2,3,4-Trimethylpentane",
    "2,2,3-TrimethylPentane":  "2,2,3-Trimethylpentane",
    "2,3-DimethylHexane":      "2,3-Dimethylhexane",
    "2,4-DimethylHexane":      "2,4-Dimethylhexane",
    "3,4-DimethylHexane":      "3,4-Dimethylhexane",
    "3-EthylHexane":           "3-Ethylhexane",
    "2,2,5-TrimethylHexane":   "2,2,5-Trimethylhexane",
    "2-Methyloctane":          "2-Methyloctane",
    "4-Methyloctane":          "4-Methyloctane",
    "2,2-DimethylHeptane":     "2,2-Dimethylheptane",
    "2,6-DimethylHeptane":     "2,6-Dimethylheptane",
    "2,2,3,3-TetramethylButane": "2,2,3,3-Tetramethylbutane",
    "2,9-DimethylHeptane":     "2,6-Dimethylheptane",
    # ── 반례3: 고리형·알켄 추가 ────────────────────────────────────────────
    "Cycloheptane":  "Cycloheptane",
    "Cyclooctane":   "Cyclooctane",
    "Decalin":       "Decahydronaphthalene",
    "1-Pentene":     "1-Pentene",
    "1-Hexene":      "1-Hexene",
    "1-Heptene":     "1-Heptene",
    "1-Octene":      "1-Octene",
    "2-Pentene":     "2-Pentene",
    "Cyclohexene":   "Cyclohexene",
    "2-Hexene":      "2-Hexene",
    "3-Hexene":      "3-Hexene",
    "C4F10":  "Perfluorobutane",
    "C5F12":  "Perfluoropentane",
    "C6F14":  "Perfluorohexane",
    # ── 반례4: 알코올 ──────────────────────────────────────────────────────
    "1-Hexanol":       "1-Hexanol",
    "1-Heptanol":      "1-Heptanol",
    "1-Octanol":       "1-Octanol",
    "1-Nonanol":       "1-Nonanol",
    "1-Decanol":       "1-Decanol",
    "1-Dodecanol":     "1-Dodecanol",
    "2-Butanol":       "2-Butanol",
    "2-Hexanol":       "2-Hexanol",
    "Cyclohexanol":    "Cyclohexanol",
    "BenzylAlcohol":   "Benzyl alcohol",
    "Phenol":          "Phenol",
    "Glycerol":        "Glycerol",
    "PropyleneGlycol": "1,2-Propanediol",
    "DiethyleneGlycol":"Diethylene glycol",
    "TriethyleneGlycol":"Triethylene glycol",
    "3-Pentanol":      "3-Pentanol",
    "Cyclopentanol":   "Cyclopentanol",
    "3-Methyl-2-Butanol": "3-Methyl-2-butanol",
    "2-Methyl-2-Butanol": "2-Methyl-2-butanol",
    "2-Methyl-1-Propanol": "Isobutanol",
    "2-Methyl-1-Butanol":  "2-Methyl-1-butanol",
    "3-Methyl-1-Butanol":  "3-Methyl-1-butanol",
    "tert-Butanol":        "tert-Butanol",
    "tert-Amyl-Alcohol":   "2-Methyl-2-butanol",
    # ── 반례4: 카르복실산 ──────────────────────────────────────────────────
    "PropionicAcid":       "Propionic acid",
    "ButyricAcid":         "Butyric acid",
    "ValericAcid":         "Pentanoic acid",
    "BenzoicAcid":         "Benzoic acid",
    "ForamicAcid":         "Formic acid",
    "TrifluoroaceticAcid": "Trifluoroacetic acid",
    "HydrofluoricAcid":    "Hydrogen fluoride",
    # ── 반례4: 에스터 ──────────────────────────────────────────────────────
    "MethylAcetate":      "Methyl acetate",
    "EthylAcetate":       "Ethyl acetate",
    "PropylAcetate":      "Propyl acetate",
    "ButylAcetate":       "Butyl acetate",
    "EthylPropanoate":    "Ethyl propanoate",
    "MethylButanoate":    "Methyl butanoate",
    "DiethylCarbonate":   "Diethyl carbonate",
    "MethylFormate":      "Methyl formate",
    "EthylFormate":       "Ethyl formate",
    "MethylPropanoate":   "Methyl propanoate",
    "IsoPropylAcetate":   "Isopropyl acetate",
    "IsoButylAcetate":    "Isobutyl acetate",
    "MethylAcrylate":     "Methyl acrylate",
    "EthylAcrylate":      "Ethyl acrylate",
    "MethylMethacrylate": "Methyl methacrylate",
    "VinylAcetate":       "Vinyl acetate",
    "DimethylOxalate":    "Dimethyl oxalate",
    "EthylBenzoate":      "Ethyl benzoate",
    "MethylBenzoate":     "Methyl benzoate",
    "EthylLactate":       "Ethyl lactate",
    "DimethylPhthalate":  "Dimethyl phthalate",
    "DiethylPhthalate":   "Diethyl phthalate",
    "DimethylSuccinate":  "Dimethyl succinate",
    "MethylOleate":      "Methyl oleate",
    "MethylPalmitate":   "Methyl palmitate",
    "MethylStearate":    "Methyl stearate",
    "MethylLinoleate":   "Methyl linoleate",
    "MethylLinolenate":  "Methyl linolenate",
    # ── 반례5: 케톤 ────────────────────────────────────────────────────────
    "MethylEthylKetone":    "2-Butanone",
    "DiethylKetone":        "3-Pentanone",
    "MethylIsobutylKetone": "4-Methyl-2-pentanone",
    "Cyclohexanone":        "Cyclohexanone",
    "Acetophenone":         "Acetophenone",
    "MethylPropylKetone":   "2-Pentanone",
    "2-Heptanone":          "2-Heptanone",
    "4-Heptanone":          "4-Heptanone",
    "Cyclopentanone":       "Cyclopentanone",
    "Benzophenone":         "Benzophenone",
    "Isophorone":           "Isophorone",
    # ── 반례5: 알데히드 ────────────────────────────────────────────────────
    "Acetaldehyde":    "Acetaldehyde",
    "Propionaldehyde": "Propanal",
    "Butyraldehyde":   "Butanal",
    "Benzaldehyde":    "Benzaldehyde",
    "Furfural":        "Furfural",
    # ── 반례5: 니트릴 ──────────────────────────────────────────────────────
    "Acetonitrile":  "Acetonitrile",
    "Propionitrile": "Propionitrile",
    "Benzonitrile":  "Benzonitrile",
    "Acrylonitrile": "Acrylonitrile",
    # ── 반례5: 아민 ────────────────────────────────────────────────────────
    "Trimethylamine":  "Trimethylamine",
    "Triethylamine":   "Triethylamine",
    "Aniline":         "Aniline",
    "Pyridine":        "Pyridine",
    "Morpholine":      "Morpholine",
    "Piperidine":      "Piperidine",
    "DimethylAmine":   "Dimethylamine",
    "DiethylAmine":    "Diethylamine",
    "Butylamine":      "Butylamine",
    "Cyclohexylamine": "Cyclohexylamine",
    "Dibutylamine":    "Dibutylamine",
    "Quinoline":       "Quinoline",
    "Isoquinoline":    "Isoquinoline",
    # ── 반례5: 에테르 ──────────────────────────────────────────────────────
    "DipropylEther":  "Dipropyl ether",
    "DibutylEther":   "Dibutyl ether",
    "THF":            "Tetrahydrofuran",
    "Dioxane":        "1,4-Dioxane",
    "Anisole":        "Anisole",
    "MTBE":           "tert-Butyl methyl ether",
    "Tetrahydropyran":"Tetrahydropyran",
    "1,3-Dioxolane":  "1,3-Dioxolane",
    # ── 반례5: 황 화합물 ────────────────────────────────────────────────────
    "CarbonDisulfide":   "Carbon disulfide",
    "DMSO":              "Dimethyl sulfoxide",
    "DimethylSulfide":   "Dimethyl sulfide",
    "Thiophene":         "Thiophene",
    "Methanethiol":      "Methanethiol",
    "DiethylSulfide":    "Diethyl sulfide",
    "Dimethyldisulfide": "Dimethyl disulfide",
    # ── 반례5: 질소 화합물 ──────────────────────────────────────────────────
    "Nitromethane":         "Nitromethane",
    "Nitroethane":          "Nitroethane",
    "NNDimethylFormamide":  "N,N-Dimethylformamide",
    "NDimethylFormamide":   "N,N-Dimethylformamide",
    "Formamide":            "Formamide",
    "Acetamide":            "Acetamide",
    "NDimethylAcetamide":   "N,N-Dimethylacetamide",
    "NMethylPyrrolidone":   "N-Methyl-2-pyrrolidinone",
    # ── 반례6: 방향족 추가 ──────────────────────────────────────────────────
    "Cumene":              "Cumene",
    "Mesitylene":          "1,3,5-Trimethylbenzene",
    "Pseudocumene":        "1,2,4-Trimethylbenzene",
    "Indene":              "Indene",
    "Tetralin":            "1,2,3,4-Tetrahydronaphthalene",
    "Biphenyl":            "Biphenyl",
    "1-MethylNaphthalene": "1-Methylnaphthalene",
    "Propylbenzene":           "Propylbenzene",
    "1,2,3-Trimethylbenzene":  "1,2,3-Trimethylbenzene",
    "Butylbenzene":            "Butylbenzene",
    "Isobutylbenzene":         "Isobutylbenzene",
    # ── 반례6: 헤테로고리 ────────────────────────────────────────────────────
    "Furan":              "Furan",
    "Pyrrole":            "Pyrrole",
    "Indole":             "Indole",
    "Imidazole":          "Imidazole",
    "Benzofuran":         "Benzofuran",
    "2-Methylfuran":      "2-Methylfuran",
    # ── 반례6: 염소화 C3~C5 ──────────────────────────────────────────────────
    "1-Chloropropane":       "1-Chloropropane",
    "2-Chloropropane":       "2-Chloropropane",
    "1-Chlorobutane":        "1-Chlorobutane",
    "2-Chlorobutane":        "2-Chlorobutane",
    "1-Chloropentane":       "1-Chloropentane",
    "1,2-Dichloropropane":   "1,2-Dichloropropane",
    "1,3-Dichloropropane":   "1,3-Dichloropropane",
    "1,1,1-Trichloroethane": "1,1,1-Trichloroethane",
    "1,1,2-Trichloroethane": "1,1,2-Trichloroethane",
    "1-Chloro-2-Methylbutane": "1-Chloro-2-methylbutane",
    "1,2-Dichloropentane":     "1,2-Dichloropentane",
    # ── 반례6: Br·I C3+ ──────────────────────────────────────────────────────
    "1-Bromopropane":  "1-Bromopropane",
    "2-Bromopropane":  "2-Bromopropane",
    "1-Bromobutane":   "1-Bromobutane",
    "Bromoethane":     "Bromoethane",
    "1-Iodopropane":   "1-Iodopropane",
    "1-Iodobutane":    "1-Iodobutane",
    "1-Chlorohexane":  "1-Chlorohexane",
    "1-Bromooctane":   "1-Bromooctane",
    "1-Bromohexane":   "1-Bromohexane",
    "1-Chlorooctane":  "1-Chlorooctane",
    # ── 반례6: 불소화 방향족 추가 ────────────────────────────────────────────
    "1,2-Difluorobenzene": "1,2-Difluorobenzene",
    "1,3-Difluorobenzene": "1,3-Difluorobenzene",
    "1,4-Difluorobenzene": "1,4-Difluorobenzene",
    "Trifluorotoluene":    "Benzotrifluoride",
    "Pentafluorobenzene":  "Pentafluorobenzene",
    "2-Chlorotoluene":     "2-Chlorotoluene",
    "4-Chlorotoluene":     "4-Chlorotoluene",
    "4-Fluorotoluene":     "4-Fluorotoluene",
    "4-Chlorofluorobenzene": "1-Chloro-4-fluorobenzene",
    # ── 반례6: 방향족 Cl 추가 ────────────────────────────────────────────────
    "1,2-Dichlorobenzene":    "1,2-Dichlorobenzene",
    "1,3-Dichlorobenzene":    "1,3-Dichlorobenzene",
    "1,4-Dichlorobenzene":    "1,4-Dichlorobenzene",
    "1,2,4-Trichlorobenzene": "1,2,4-Trichlorobenzene",
    # ── 반례6: 할로 C1C2 추가 ────────────────────────────────────────────────
    "1,1-Dichloroethane":        "1,1-Dichloroethane",
    "1,1,1,2-Tetrachloroethane": "1,1,1,2-Tetrachloroethane",
    "Hexachloroethane":          "Hexachloroethane",
    "1,2-Dibromoethane":         "1,2-Dibromoethane",
    "Dibromochloromethane":      "Dibromochloromethane",
    "Bromoform":                 "Bromoform",
    "Iodoform":                  "Iodoform",
    # ── 반례7: 다환 방향족 ──────────────────────────────────────────────────
    "Anthracene":   "Anthracene",
    "Phenanthrene": "Phenanthrene",
    "Fluorene":     "Fluorene",
    # ── 반례7: 분지 알코올 ────────────────────────────────────────────────────
    "2-Methyl-1-Propanol": "Isobutanol",
    "2-Methyl-1-Butanol":  "2-Methyl-1-butanol",
    "3-Methyl-1-Butanol":  "3-Methyl-1-butanol",
    "tert-Butanol":        "tert-Butanol",
    "tert-Amyl-Alcohol":   "2-Methyl-2-butanol",
    # ── 반례8: 에스터 추가 ────────────────────────────────────────────────────
    "EthylLactate":    "Ethyl lactate",
    # ── 반례9: 반응성 C3 ─────────────────────────────────────────────────────
    "Allylchloride":    "Allyl chloride",
    "Acrolein":         "Acrolein",
    "PropargylAlcohol": "Propargyl alcohol",
    # ── 반례10: 테르펜 ────────────────────────────────────────────────────────
    "Limonene":     "Limonene",
    "aAlphaPinene": "alpha-Pinene",
    "Camphene":     "Camphene",
    # ── 반례10: 실란 ──────────────────────────────────────────────────────────
    "Tetramethylsilane": "Tetramethylsilane",
    # ── 반례10: 글리콜 에테르 ─────────────────────────────────────────────────
    "EthyleneGlycolMonoethylEther":    "2-Ethoxyethanol",
    "EthyleneGlycolMonobutylEther":    "2-Butoxyethanol",
    "DiethyleneGlycolMonomethylEther": "Diethylene glycol monomethyl ether",
    "1,3-Propanediol": "1,3-Propanediol",
    "1,4-Butanediol":  "1,4-Butanediol",
    # ── 반례11: 방향족 O ──────────────────────────────────────────────────────
    "Catechol":   "Catechol",
    "Resorcinol": "Resorcinol",
    "Guaiacol":   "Guaiacol",
    # ── 반례: 불소화 특수 케톤 ────────────────────────────────────────────────
    "Novec1230": "1,1,1,2,2,4,5,5,5-Nonafluoro-4-(trifluoromethyl)-3-pentanone",
    # ── 반례9: 케톤 추가 ─────────────────────────────────────────────────────
    "Benzophenone":  "Benzophenone",
    "Isophorone":    "Isophorone",
    # ── 추가 name 매핑 ────────────────────────────────────────────────────────
    "Benzophenol":   "Benzophenone",
    "Acetophenol":   "4-Hydroxyacetophenone",
    "Allyl":         "Allyl alcohol",
    "DietylDisulfide": "Diethyl disulfide",
    "EpsilonCaprolactone": "epsilon-Caprolactone",
    "Trichloroacetic": "Trichloroacetic acid",
    "NitrogenDioxide": "Nitrogen dioxide",
    "NitricOxide":   "Nitric oxide",
    "3-EthylMethylPentane": "3-Ethyl-3-methylpentane",
    "DinitrogenTetroxide": "Dinitrogen tetroxide",
    "Perfluorodecalin": "Perfluorodecalin",
    "PerfluoroMethylDecalin": "2-(Trifluoromethyl)decahydronaphthalene",
    "1-MethylCyclopentene": "1-Methylcyclopentene",
    "1-Phenylnaphthalene": "1-Phenylnaphthalene",
    "Erythritol": "Erythritol",
    "Sorbitol": "Sorbitol",
    "Chrysene": "Chrysene",
    "Terpinolene": "Terpinolene",
    "Myrcene": "Myrcene",
    "Camphene": "Camphene",
    "TrimethylPhosphate": "Trimethyl phosphate",
    "TrimethylBorate": "Trimethyl borate",
    "TriethylPhosphate": "Triethyl phosphate",
    "TripropylPhosphate": "Tripropyl phosphate",
    "TributylPhosphate": "Tributyl phosphate",
    "Chloromethylmethylether": "Chloromethyl methyl ether",
    "Bis2chloroethylether": "Bis(2-chloroethyl) ether",
    "Methanesulfonic": "Methanesulfonic acid",
    "Perfluorobutylamine": "Perfluorobutylamine",
    "PerfluoroTripropylamine": "Perfluorotripropylamine",
    "PerfluorotributylAmine": "Perfluorotributylamine",
    "DiMethylPeroxide": "Dimethyl peroxide",
    "HydrofluoricAcid": "Hydrofluoric acid",
    "PhosphoricAcid": "Phosphoric acid",
    "PentafluoropropionicAcid": "Pentafluoropropionic acid",
    "Coronene": "Coronene",
    "CrownEther18c6": "18-Crown-6",
    "bis_HFE_7300": "Methyl 1,1,2,3,3,3-hexafluoropropyl ether",
}


# ---------------------------------------------------------------------------
# 1. CID 조회
# ---------------------------------------------------------------------------

def get_cid_by_name(name: str) -> Optional[int]:
    """화합물 이름으로 PubChem CID 조회"""
    url = f"{BASE_URL}/compound/name/{requests.utils.quote(name)}/cids/JSON"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        cids = resp.json()["IdentifierList"]["CID"]
        return cids[0]
    except (requests.HTTPError, KeyError, IndexError):
        logger.warning(f"CID not found: {name}")
        return None


def get_cid_by_smiles(smiles: str) -> Optional[int]:
    """SMILES로 PubChem CID 조회"""
    url = f"{BASE_URL}/compound/smiles/{requests.utils.quote(smiles)}/cids/JSON"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()["IdentifierList"]["CID"][0]
    except (requests.HTTPError, KeyError, IndexError):
        logger.warning(f"CID not found for SMILES: {smiles}")
        return None


# ---------------------------------------------------------------------------
# 2. 분자구조 조회
# ---------------------------------------------------------------------------

def get_molecular_structure(cid: int) -> dict:
    """
    분자구조 정보 반환
    - CanonicalSMILES, IsomericSMILES, InChI, InChIKey
    - MolecularFormula, MolecularWeight
    """
    props = [
        "CanonicalSMILES",
        "IsomericSMILES",
        "InChI",
        "InChIKey",
        "MolecularFormula",
        "MolecularWeight",
        "IUPACName",
        "XLogP",
        "HeavyAtomCount",
    ]
    url = f"{BASE_URL}/compound/cid/{cid}/property/{','.join(props)}/JSON"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()["PropertyTable"]["Properties"][0]
    except Exception as e:
        logger.error(f"[CID {cid}] Structure fetch failed: {e}")
        return {}


def get_2d_sdf(cid: int) -> Optional[str]:
    """2D SDF 파일 문자열 반환 (RDKit 등에서 활용 가능)"""
    url = f"{BASE_URL}/compound/cid/{cid}/SDF"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.error(f"[CID {cid}] SDF fetch failed: {e}")
        return None


# ---------------------------------------------------------------------------
# 3. 통합 파이프라인 (분자구조 전용)
# ---------------------------------------------------------------------------

def fetch_compound_data(identifier: str, id_type: str = "name") -> dict:
    """
    단일 화합물의 분자구조 데이터 수집 (PubChem)
    열역학 물성은 coolprop_fetcher.get_coolprop_properties() 에서 별도 수집

    Parameters
    ----------
    identifier : 화합물 이름 또는 SMILES
    id_type    : "name" | "smiles"
    """
    if id_type == "name":
        search_name = PUBCHEM_NAME_MAP.get(identifier, identifier)
        cid = get_cid_by_name(search_name)
    elif id_type == "smiles":
        cid = get_cid_by_smiles(identifier)
    else:
        raise ValueError(f"Unknown id_type: {id_type}")

    if cid is None:
        return {"identifier": identifier, "cid": None, "error": "CID not found"}

    logger.info(f"[{identifier}] CID={cid}")

    time.sleep(REQUEST_DELAY)
    structure = get_molecular_structure(cid)

    return {
        "identifier": identifier,
        "cid": cid,
        **structure,
    }


def build_dataset(
    compounds: list[str],
    id_type: str = "name",
    output_path: Optional[str] = None,
    save_sdf: bool = False,
    sdf_dir: Optional[str] = None,
) -> pd.DataFrame:
    """
    여러 화합물에 대해 데이터 수집 → DataFrame 반환 및 CSV 저장

    Parameters
    ----------
    compounds   : 화합물 이름 또는 SMILES 리스트
    id_type     : "name" | "smiles"
    output_path : CSV 저장 경로 (None이면 저장 안 함)
    save_sdf    : SDF 파일 저장 여부
    sdf_dir     : SDF 저장 디렉토리
    """
    records = []

    for i, comp in enumerate(compounds):
        logger.info(f"[{i+1}/{len(compounds)}] Fetching: {comp}")
        record = fetch_compound_data(comp, id_type=id_type)
        records.append(record)

        # SDF 저장
        if save_sdf and record.get("cid"):
            time.sleep(REQUEST_DELAY)
            sdf_text = get_2d_sdf(record["cid"])
            if sdf_text and sdf_dir:
                sdf_path = Path(sdf_dir) / f"{record['cid']}.sdf"
                sdf_path.parent.mkdir(parents=True, exist_ok=True)
                sdf_path.write_text(sdf_text)
                logger.info(f"  SDF saved: {sdf_path}")

        time.sleep(REQUEST_DELAY)

    df = pd.DataFrame(records)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info(f"Dataset saved: {output_path} ({len(df)} rows)")

    return df


