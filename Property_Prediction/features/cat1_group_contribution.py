"""
범주 1: 작용기 / Group Contribution Features

Joback & Reid (1987) 방법 기반 원자단 식별 및 기여값 계산.
출처: Joback & Reid, Chem. Eng. Commun. 57:233-243 (1987)
     Poling, Prausnitz, O'Connell, "Properties of Gases and Liquids", 5th ed., App. A

추출 특성:
  - 각 Joback 원자단 개수 (gc_<group>)
  - ΣΔTc, ΣΔPc (Joback 합산값 → physics-informed feature)
  - Joback Pc 추정값 (Tb 불필요, NA 필요)
  - Joback Tc 추정값 (Tb 필요 → Tb 미제공 시 NaN)
"""
from __future__ import annotations
import math
import logging
from rdkit import Chem
from .base import FeatureExtractor

logger = logging.getLogger(__name__)

# ── Joback 원자단 정의 ──────────────────────────────────────────────────────
# (SMARTS, ΔTc, ΔPc)
# ΔPc 단위: (bar)^-0.5  →  Pc[bar] = 1/(0.113 + 0.0032*NA - ΣΔPc)^2
# Tc 단위: 무차원  →  Tc[K] = Tb/(0.584 + 0.965*ΣΔTc - (ΣΔTc)^2)
JOBACK_GROUPS: dict[str, tuple[str, float, float]] = {
    # ── 비환형 탄소 ────────────────────────────────────────────────
    "CH3":         ("[CX4H3]",         0.0141,  -0.0012),
    "CH2":         ("[CX4H2;!R]",      0.0189,   0.0000),
    "CH":          ("[CX4H1;!R]",      0.0164,   0.0020),
    "C":           ("[CX4H0;!R]",      0.0067,   0.0043),
    "dCH2":        ("[CX3H2]",         0.0113,  -0.0028),  # =CH2
    "dCH":         ("[CX3H1;!R;!a]",  0.0129,  -0.0006),  # =CH-
    "dC":          ("[CX3H0;!R;!a]",  0.0117,   0.0011),  # =C<
    "dCd":         ("[CX2H0](=*)(=*)",0.0026,   0.0028),  # =C=
    "tCH":         ("[CX2H1]",         0.0027,  -0.0008),  # ≡CH
    "tC":          ("[CX2H0;!a]",      0.0020,   0.0016),  # ≡C-
    # ── 환형 탄소 ──────────────────────────────────────────────────
    "ring_CH2":    ("[CX4H2;R]",       0.0100,   0.0025),
    "ring_CH":     ("[CX4H1;R]",       0.0122,   0.0004),
    "ring_C":      ("[CX4H0;R]",       0.0042,   0.0061),
    "ring_dCH":    ("[CX3H1;R;!a]",   0.0082,   0.0011),
    "ring_dC":     ("[CX3H0;R;!a]",   0.0143,   0.0008),
    # ── 방향족 탄소 ────────────────────────────────────────────────
    "ar_CH":       ("[cH1]",           0.0111,  -0.0057),
    "ar_C":        ("[cH0]",           0.0105,  -0.0049),
    # ── 할로겐 ─────────────────────────────────────────────────────
    "F":           ("[F]",             0.0111,  -0.0057),
    "Cl":          ("[Cl]",            0.0105,  -0.0049),
    "Br":          ("[Br]",            0.0133,   0.0057),
    "I":           ("[I]",             0.0068,  -0.0034),
    # ── 산소 함유 ──────────────────────────────────────────────────
    "OH_alc":      ("[OX2H1;!a]",     0.0741,   0.0112),
    "OH_phen":     ("[OX2H1;a]",      0.0240,   0.0184),
    "O_ether":     ("[OX2H0;!R;!a]",  0.0168,   0.0015),
    "O_ring":      ("[OX2H0;R;!a]",   0.0098,   0.0048),
    "CO_ketone":   ("[CX3H0;!R](=[OX1])[#6]",  0.0481,   0.0152),
    "CO_ring":     ("[CX3H0;R](=[OX1])[#6]",   0.0143,  -0.0074),
    "CHO":         ("[CX3H1]=[OX1]",  0.0380,   0.0031),
    "COOH":        ("[CX3](=[OX1])[OX2H1]",    0.0791,   0.0077),
    "COO_ester":   ("[CX3](=[OX1])[OX2H0;!a]", 0.0481,   0.0152),
    "O_other":     ("[OX1H0]",         0.0143,   0.0039),
    # ── 질소 함유 ──────────────────────────────────────────────────
    "NH2":         ("[NX3H2;!a]",     0.0243,   0.0109),
    "NH_acyc":     ("[NX3H1;!R;!a]", 0.0295,   0.0077),
    "NH_ring":     ("[NX3H1;R;!a]",  0.0130,   0.0114),
    "N_acyc":      ("[NX3H0;!R;!a]", 0.0169,   0.0074),
    "N_imino":     ("[NX2H0;!R;!a]=*", 0.0255, -0.0099),
    "N_ring":      ("[nH0]",          0.0085,   0.0076),
    "CN":          ("[NX1]#[CX2]",   0.0496,  -0.0101),
    "NO2":         ("[NX3](=[OX1])[OX1]", 0.0437, 0.0064),
    # ── 황 함유 ────────────────────────────────────────────────────
    "SH":          ("[SX2H1]",        0.0390,   0.0147),
    "S_acyc":      ("[SX2H0;!R]",    0.0261,   0.0139),
    "S_ring":      ("[SX2H0;R]",     0.0169,   0.0019),
}

# 미리 SMARTS 컴파일
_COMPILED: dict[str, Chem.Mol] = {}


def _get_pattern(group: str, smarts: str) -> Chem.Mol | None:
    if group not in _COMPILED:
        pat = Chem.MolFromSmarts(smarts)
        _COMPILED[group] = pat
        if pat is None:
            logger.warning(f"[cat1] SMARTS 컴파일 실패: {group} = {smarts}")
    return _COMPILED[group]


class GroupContributionExtractor(FeatureExtractor):
    """
    Joback 원자단 카운트 + Joback Pc/Tc 추정값을 특성으로 반환.

    Parameters
    ----------
    tb_map : 화합물명 → Tb[K] dict (Tc 추정에 필요, 없으면 gc_joback_Tc=NaN)
    """

    def __init__(self, tb_map: dict[str, float] | None = None):
        self._tb_map = tb_map or {}

    @property
    def prefix(self) -> str:
        return "gc"

    def extract(self, mol: Chem.Mol, identifier: str | None = None) -> dict[str, float]:
        feats: dict[str, float] = {}
        sum_dtc = 0.0
        sum_dpc = 0.0

        for group, (smarts, dtc, dpc) in JOBACK_GROUPS.items():
            pat = _get_pattern(group, smarts)
            if pat is None:
                feats[f"gc_{group}"] = float("nan")
                continue
            count = len(mol.GetSubstructMatches(pat))
            feats[f"gc_{group}"] = float(count)
            sum_dtc += dtc * count
            sum_dpc += dpc * count

        feats["gc_sum_dTc"] = sum_dtc
        feats["gc_sum_dPc"] = sum_dpc

        # ── Joback Pc 추정 (Tb 불필요) ──────────────────────────────────────
        n_atoms = mol.GetNumHeavyAtoms()
        denom = 0.113 + 0.0032 * n_atoms - sum_dpc
        if denom != 0:
            feats["gc_joback_Pc_bar"] = 1.0 / (denom ** 2)
        else:
            feats["gc_joback_Pc_bar"] = float("nan")

        # ── Joback Tc 추정 (Tb 필요) ────────────────────────────────────────
        tb = self._tb_map.get(identifier) if identifier else None
        if tb is not None:
            inner = 0.584 + 0.965 * sum_dtc - sum_dtc ** 2
            feats["gc_joback_Tc_K"] = tb / inner if inner != 0 else float("nan")
        else:
            feats["gc_joback_Tc_K"] = float("nan")

        return feats
