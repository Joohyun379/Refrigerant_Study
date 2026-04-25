"""
범주 5: 냉매 특화 특성 (Refrigerant-Specific Features)

냉매 물성(Tc, Pc, ω)과 직접 연관된 도메인 지식 기반 특성.

추출 특성:
  - 할로겐 개수·비율 (F, Cl, Br, I)
  - 불소화 패턴 그룹 (CF3, CF2, CHF, CClF, CCl2, 등)
  - 탄소 사슬 특성 (길이, 분지)
  - 냉매 구조 유형 (HFC / HFO / HCFC / CFC / FC / HC / inorganic)
  - 포화 여부, 고리 여부, 에테르 산소
  - 순불소화도(degree of fluorination), 할로겐 치환도
"""
from __future__ import annotations
import logging
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors
from .base import FeatureExtractor

logger = logging.getLogger(__name__)

# ── 냉매 유형 분류 SMARTS ────────────────────────────────────────────────────
_PAT = {
    # 할로겐 그룹 패턴
    "CF3":      Chem.MolFromSmarts("[CX4]([F])([F])[F]"),
    "CF2":      Chem.MolFromSmarts("[CX4]([F])[F]"),
    "CF":       Chem.MolFromSmarts("[CX4][F]"),
    "CHF":      Chem.MolFromSmarts("[CX4H][F]"),
    "CH2F":     Chem.MolFromSmarts("[CX4H2][F]"),
    "CCl2F":    Chem.MolFromSmarts("[CX4]([Cl])([Cl])[F]"),
    "CClF2":    Chem.MolFromSmarts("[CX4]([Cl])([F])[F]"),
    "CClF":     Chem.MolFromSmarts("[CX4]([Cl])[F]"),
    "CCl3":     Chem.MolFromSmarts("[CX4]([Cl])([Cl])[Cl]"),
    "CCl2":     Chem.MolFromSmarts("[CX4]([Cl])[Cl]"),
    "CBrF2":    Chem.MolFromSmarts("[CX4]([Br])([F])[F]"),
    # 불포화 할로겐 그룹
    "CF2_vinyl":Chem.MolFromSmarts("[CX3]([F])=[CX3]"),
    "CF_vinyl": Chem.MolFromSmarts("[CX3;H0][F]"),
    # 산소 함유
    "ether_O":  Chem.MolFromSmarts("[OX2H0;!a]"),
    # 환형
    "ring_any":      Chem.MolFromSmarts("[R]"),
    "ring_carbocycle": Chem.MolFromSmarts("[c,C;R]"),
    # 올레핀 (HFO 핵심)
    "C_double": Chem.MolFromSmarts("[CX3]=[CX3]"),
    "C_triple": Chem.MolFromSmarts("[CX2]#[CX2]"),
}


def _count(mol: Chem.Mol, pat_key: str) -> int:
    pat = _PAT.get(pat_key)
    if pat is None:
        return 0
    return len(mol.GetSubstructMatches(pat))


def _classify_refrigerant(
    n_F: int, n_Cl: int, n_Br: int, n_I: int,
    n_H_on_C: int, n_C: int, n_O: int,
    has_double: bool, has_triple: bool,
) -> dict[str, float]:
    """
    냉매 구조 유형 판별 (one-hot).

    유형 정의:
      FC   : 완전불소화 탄화수소 (n_H_on_C=0, no Cl/Br, only F+C)
      CFC  : Cl+F, no H
      HCFC : Cl+F+H
      HFC  : F+H, no Cl/Br
      HFO  : HFC + 이중결합
      HCFO : HCFC + 이중결합
      HC   : 탄화수소 (no halogen)
      inorganic : no C
      other: 나머지 (Br/I 포함 등)
    """
    has_hal  = (n_F + n_Cl + n_Br + n_I) > 0
    has_F    = n_F > 0
    has_Cl   = n_Cl > 0
    has_Br   = n_Br > 0
    has_H_C  = n_H_on_C > 0
    has_C    = n_C > 0
    has_O    = n_O > 0

    is_FC    = has_C and has_F and not has_Cl and not has_Br and not has_H_C and not has_O
    is_CFC   = has_C and has_F and has_Cl and not has_H_C
    is_HCFC  = has_C and has_F and has_Cl and has_H_C and not has_double
    is_HFC   = has_C and has_F and not has_Cl and not has_Br and has_H_C and not has_double
    is_HFO   = has_C and has_F and not has_Cl and not has_Br and has_H_C and has_double
    is_HCFO  = has_C and has_F and has_Cl and has_H_C and has_double
    is_HC    = has_C and not has_hal and not has_O
    is_inorg = not has_C

    return {
        "rf_type_FC":      float(is_FC),
        "rf_type_CFC":     float(is_CFC),
        "rf_type_HCFC":    float(is_HCFC),
        "rf_type_HFC":     float(is_HFC),
        "rf_type_HFO":     float(is_HFO),
        "rf_type_HCFO":    float(is_HCFO),
        "rf_type_HC":      float(is_HC),
        "rf_type_inorganic": float(is_inorg),
        "rf_type_other":   float(not any([is_FC, is_CFC, is_HCFC, is_HFC,
                                           is_HFO, is_HCFO, is_HC, is_inorg])),
    }


def _longest_carbon_chain(mol: Chem.Mol) -> int:
    """최장 탄소 사슬 길이 (BFS over C-C bonds)."""
    try:
        carbon_idx = [a.GetIdx() for a in mol.GetAtoms() if a.GetAtomicNum() == 6]
        if not carbon_idx:
            return 0
        # C-C 인접 리스트
        adj: dict[int, list[int]] = {i: [] for i in carbon_idx}
        for bond in mol.GetBonds():
            i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
            if i in adj and j in adj:
                adj[i].append(j)
                adj[j].append(i)

        # 모든 노드 쌍 BFS → 최단 거리 최대값
        def bfs_max(start):
            dist = {start: 0}
            queue = [start]
            while queue:
                cur = queue.pop(0)
                for nb in adj[cur]:
                    if nb not in dist:
                        dist[nb] = dist[cur] + 1
                        queue.append(nb)
            return max(dist.values()) if dist else 0

        return max(bfs_max(c) for c in carbon_idx) + 1
    except Exception:
        return 0


class RefrigerantSpecificExtractor(FeatureExtractor):

    @property
    def prefix(self) -> str:
        return "rf"

    def extract(self, mol: Chem.Mol) -> dict[str, float]:
        feats: dict[str, float] = {}

        # ── 원소 계수 ────────────────────────────────────────────────────────
        n_F  = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() == 9)
        n_Cl = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() == 17)
        n_Br = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() == 35)
        n_I  = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() == 53)
        n_C  = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() == 6)
        n_O  = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() == 8)
        n_hal = n_F + n_Cl + n_Br + n_I

        feats["rf_n_F"]   = float(n_F)
        feats["rf_n_Cl"]  = float(n_Cl)
        feats["rf_n_Br"]  = float(n_Br)
        feats["rf_n_I"]   = float(n_I)
        feats["rf_n_hal"] = float(n_hal)
        feats["rf_n_C"]   = float(n_C)
        feats["rf_n_O"]   = float(n_O)

        # ── 할로겐 비율 ──────────────────────────────────────────────────────
        # 불소화도: F / (F + H) — H는 탄소에 결합된 것만
        mol_h = Chem.AddHs(mol)
        n_H_on_C = sum(
            1 for a in mol_h.GetAtoms()
            if a.GetAtomicNum() == 1 and
               any(nb.GetAtomicNum() == 6 for nb in a.GetNeighbors())
        )
        n_subst = n_H_on_C + n_hal
        feats["rf_n_H_on_C"] = float(n_H_on_C)
        feats["rf_fluorination_degree"] = n_F / n_subst if n_subst else 0.0
        feats["rf_halogenation_degree"] = n_hal / n_subst if n_subst else 0.0
        feats["rf_ratio_F_hal"] = n_F / n_hal if n_hal else 0.0
        feats["rf_ratio_Cl_hal"] = n_Cl / n_hal if n_hal else 0.0
        feats["rf_ratio_F_C"]   = n_F / n_C if n_C else float("nan")

        # ── 할로겐 그룹 패턴 개수 ────────────────────────────────────────────
        for pat_key in ["CF3", "CF2", "CF", "CHF", "CH2F",
                         "CCl2F", "CClF2", "CClF", "CCl3", "CCl2",
                         "CBrF2", "CF2_vinyl", "CF_vinyl"]:
            feats[f"rf_{pat_key}"] = float(_count(mol, pat_key))

        # ── 구조 플래그 ──────────────────────────────────────────────────────
        has_double = _count(mol, "C_double") > 0
        has_triple = _count(mol, "C_triple") > 0
        feats["rf_has_double_bond"] = float(has_double)
        feats["rf_has_triple_bond"] = float(has_triple)
        feats["rf_is_cyclic"]       = float(_count(mol, "ring_any") > 0)
        feats["rf_has_ether_O"]     = float(_count(mol, "ether_O") > 0)
        feats["rf_is_perfluorinated"] = float(n_C > 0 and n_H_on_C == 0
                                               and n_Cl == 0 and n_Br == 0
                                               and n_F > 0)
        feats["rf_is_saturated"]    = float(not has_double and not has_triple)

        # ── 탄소 사슬 ────────────────────────────────────────────────────────
        feats["rf_n_C_chain"]  = float(_longest_carbon_chain(mol))
        feats["rf_n_C_total"]  = float(n_C)
        feats["rf_n_rot_bonds"] = float(rdMolDescriptors.CalcNumRotatableBonds(mol))

        # ── 냉매 유형 분류 ───────────────────────────────────────────────────
        feats.update(_classify_refrigerant(
            n_F, n_Cl, n_Br, n_I, n_H_on_C, n_C, n_O,
            has_double, has_triple,
        ))

        return feats
