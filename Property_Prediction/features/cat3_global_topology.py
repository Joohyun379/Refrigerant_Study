"""
범주 3: 전체 분자 위상·구성 기술자 (Global Topological & Constitutional Descriptors)

구성 기술자 (Constitutional):
  분자량, 원자 수, 원소 조성 비율, 결합 수, 고리 정보, Fsp3

위상 지수 (Topological Indices):
  Wiener, Randić χ, Kier-Hall κ, Balaban J, BertzCT 등

모두 RDKit Descriptors / GraphDescriptors / rdMolDescriptors로 계산.
3D 좌표 불필요 (2D 기반).
"""
from __future__ import annotations
import logging
from rdkit import Chem
from rdkit.Chem import Descriptors, GraphDescriptors, rdMolDescriptors
from .base import FeatureExtractor

logger = logging.getLogger(__name__)

# 관심 원소 목록
_ELEMENTS = ["C", "H", "F", "Cl", "Br", "I", "O", "N", "S", "Si", "P"]


class GlobalTopologyExtractor(FeatureExtractor):

    @property
    def prefix(self) -> str:
        return "gt"

    def extract(self, mol: Chem.Mol) -> dict[str, float]:
        feats: dict[str, float] = {}

        # ── 구성 기술자 ─────────────────────────────────────────────────────
        feats["gt_mw"]          = Descriptors.MolWt(mol)
        feats["gt_exact_mw"]    = Descriptors.ExactMolWt(mol)
        feats["gt_heavy_atoms"] = mol.GetNumHeavyAtoms()
        feats["gt_num_bonds"]   = mol.GetNumBonds()

        # 원소별 원자 수
        atom_counts: dict[str, int] = {el: 0 for el in _ELEMENTS}
        for atom in mol.GetAtoms():
            sym = atom.GetSymbol()
            if sym in atom_counts:
                atom_counts[sym] += 1
            else:
                atom_counts["other"] = atom_counts.get("other", 0) + 1

        # 암묵적 H 합산
        mol_h = Chem.AddHs(mol)
        h_count = sum(1 for a in mol_h.GetAtoms() if a.GetAtomicNum() == 1)
        atom_counts["H"] = h_count

        for el, cnt in atom_counts.items():
            feats[f"gt_n_{el}"] = float(cnt)

        # 원소 비율 (C 기준)
        n_c = atom_counts.get("C", 0)
        n_h = atom_counts.get("H", 0)
        n_hal = sum(atom_counts.get(x, 0) for x in ["F", "Cl", "Br", "I"])
        total = max(mol.GetNumHeavyAtoms(), 1)

        feats["gt_ratio_H_C"]     = n_h / n_c if n_c else float("nan")
        feats["gt_ratio_hal_C"]   = n_hal / n_c if n_c else float("nan")
        feats["gt_ratio_hal_tot"] = n_hal / total

        # 결합 종류별 수
        n_single = n_double = n_triple = n_arom = 0
        for bond in mol.GetBonds():
            bt = bond.GetBondTypeAsDouble()
            if bt == 1.0:   n_single += 1
            elif bt == 2.0: n_double += 1
            elif bt == 3.0: n_triple += 1
            elif bt == 1.5: n_arom   += 1
        feats["gt_n_single"] = float(n_single)
        feats["gt_n_double"] = float(n_double)
        feats["gt_n_triple"] = float(n_triple)
        feats["gt_n_arom"]   = float(n_arom)

        # 고리 정보
        ri = mol.GetRingInfo()
        feats["gt_n_rings"]       = float(ri.NumRings())
        feats["gt_n_arom_rings"]  = float(rdMolDescriptors.CalcNumAromaticRings(mol))
        feats["gt_n_sat_rings"]   = float(rdMolDescriptors.CalcNumSaturatedRings(mol))
        feats["gt_n_arom_carbocycles"]  = float(rdMolDescriptors.CalcNumAromaticCarbocycles(mol))
        feats["gt_n_arom_heterocycles"] = float(rdMolDescriptors.CalcNumAromaticHeterocycles(mol))
        feats["gt_n_bridgehead"]  = float(rdMolDescriptors.CalcNumBridgeheadAtoms(mol))
        feats["gt_n_spiro"]       = float(rdMolDescriptors.CalcNumSpiroAtoms(mol))

        # 가장 큰 고리 크기
        ring_sizes = [len(r) for r in ri.AtomRings()]
        feats["gt_max_ring_size"] = float(max(ring_sizes)) if ring_sizes else 0.0
        feats["gt_min_ring_size"] = float(min(ring_sizes)) if ring_sizes else 0.0

        # sp3 분율, 회전 가능한 결합
        feats["gt_Fsp3"]          = rdMolDescriptors.CalcFractionCSP3(mol)
        feats["gt_n_rot_bonds"]   = float(rdMolDescriptors.CalcNumRotatableBonds(mol))
        feats["gt_n_stereocenters"] = float(rdMolDescriptors.CalcNumAtomStereoCenters(mol))

        # ── 위상 지수 ───────────────────────────────────────────────────────
        # Wiener index: 모든 원자 쌍 최단 거리 합 (분자 크기·모양 지표)
        try:
            dm = Chem.rdmolops.GetDistanceMatrix(mol)
            n = mol.GetNumHeavyAtoms()
            feats["gt_wiener"] = float(dm.sum() / 2)
        except Exception:
            feats["gt_wiener"] = float("nan")

        # Randić 연결 지수 χ₀, χ₁, χ₂
        try:
            feats["gt_chi0"]  = GraphDescriptors.Chi0(mol)
            feats["gt_chi1"]  = GraphDescriptors.Chi1(mol)
            feats["gt_chi0n"] = GraphDescriptors.Chi0n(mol)
            feats["gt_chi1n"] = GraphDescriptors.Chi1n(mol)
            feats["gt_chi2n"] = GraphDescriptors.Chi2n(mol)
            feats["gt_chi3n"] = GraphDescriptors.Chi3n(mol)
        except Exception:
            for k in ["chi0", "chi1", "chi0n", "chi1n", "chi2n", "chi3n"]:
                feats[f"gt_{k}"] = float("nan")

        # Kier-Hall κ 형태 지수 (분자 분지도)
        # 중원자 1개(NH3, H2O, HF 등)는 2-결합 경로=0 → RDKit이 음수 반환 → 0으로 처리
        try:
            n_heavy = mol.GetNumHeavyAtoms()
            feats["gt_kappa1"] = GraphDescriptors.Kappa1(mol) if n_heavy >= 2 else 0.0
            feats["gt_kappa2"] = GraphDescriptors.Kappa2(mol) if n_heavy >= 3 else 0.0
            feats["gt_kappa3"] = GraphDescriptors.Kappa3(mol) if n_heavy >= 4 else 0.0
        except Exception:
            for k in ["kappa1", "kappa2", "kappa3"]:
                feats[f"gt_{k}"] = float("nan")

        # Balaban J 지수 (분자 분지도·크기 동시 반영)
        try:
            feats["gt_balaban_j"] = GraphDescriptors.BalabanJ(mol)
        except Exception:
            feats["gt_balaban_j"] = float("nan")

        # Bertz CT 복잡도 지수
        try:
            feats["gt_bertz_ct"] = GraphDescriptors.BertzCT(mol)
        except Exception:
            feats["gt_bertz_ct"] = float("nan")

        # Ipc (분자 그래프 정보 내용)
        try:
            feats["gt_ipc"] = GraphDescriptors.Ipc(mol)
        except Exception:
            feats["gt_ipc"] = float("nan")

        return feats
