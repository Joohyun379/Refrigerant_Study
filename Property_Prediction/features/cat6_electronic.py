"""
범주 6: 전자 구조 / 분자 간 힘 특성 (Electronic & Intermolecular Features)

Tc와 ω는 분자 간 인력(LJ, 쌍극자-쌍극자, 수소결합, 분산력)에서 비롯됨.
이 범주는 그 인력의 세기와 이방성을 나타내는 특성을 계산한다.

RDKit 기반 (기본):
  - Gasteiger 부분 전하 통계 (max/min/mean/std, RPCG/RNCG)
  - 분극률 근사 (원자 분극률 기여값 합산, Crippen MolMR 활용)
  - LogP (소수성, 분산력 지표)
  - 수소결합 공여/수용 수 (HBD/HBA)
  - TPSA (극성 표면적 → 분자 간 상호작용 이방성)
  - 쌍극자 모멘트 근사 (Gasteiger 전하 + 3D 좌표)

선택적 (xTB GFN2):
  - HOMO/LUMO 에너지, HOMO-LUMO gap
  - DFT 수준 쌍극자 모멘트
  - Mulliken 전하 기반 전하 기술자

의존성:
  필수: RDKit
  선택: xtb-python (pip install xtb-python) 또는 xtb CLI
"""
from __future__ import annotations
import logging
import math
import numpy as np
from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors, AllChem
from rdkit.Chem.rdPartialCharges import ComputeGasteigerCharges
from .base import FeatureExtractor

logger = logging.getLogger(__name__)

# ── 원자별 분극률 (Å³) ──────────────────────────────────────────────────────
# 출처: Miller, J. Am. Chem. Soc. 112:8533 (1990)
# Crippen MolMR와 부분적으로 일치; H는 C에 귀속
_ATOMIC_POLARIZABILITY: dict[int, float] = {
    1:  0.387,   # H
    6:  1.061,   # C
    7:  0.530,   # N
    8:  0.569,   # O
    9:  0.274,   # F   ← 매우 작음 → 불소화 → 낮은 분극률
    15: 1.840,   # P
    16: 2.219,   # S
    17: 2.315,   # Cl
    35: 3.013,   # Br
    53: 5.415,   # I
    14: 3.630,   # Si
}


def _gasteiger_charge_features(mol: Chem.Mol) -> dict[str, float]:
    """Gasteiger 부분 전하 통계."""
    mol_c = Chem.RWMol(mol)
    ComputeGasteigerCharges(mol_c)
    charges = np.array([
        a.GetDoubleProp("_GasteigerCharge")
        for a in mol_c.GetAtoms()
    ])
    # NaN·Inf 제거
    charges = charges[np.isfinite(charges)]
    if len(charges) == 0:
        return {k: float("nan") for k in
                ["el_q_max", "el_q_min", "el_q_mean", "el_q_std",
                 "el_q_pos_sum", "el_q_neg_sum", "el_RPCG", "el_RNCG"]}

    feats = {
        "el_q_max":     float(charges.max()),
        "el_q_min":     float(charges.min()),
        "el_q_mean":    float(charges.mean()),
        "el_q_std":     float(charges.std()),
        "el_q_pos_sum": float(charges[charges > 0].sum()),
        "el_q_neg_sum": float(charges[charges < 0].sum()),
    }
    # RPCG: 최대 양전하 / 총 양전하 합
    # RNCG: 최소 음전하 / 총 음전하 합
    pos = charges[charges > 0]
    neg = charges[charges < 0]
    feats["el_RPCG"] = float(pos.max() / pos.sum()) if len(pos) > 0 else 0.0
    feats["el_RNCG"] = float(neg.min() / neg.sum()) if len(neg) > 0 else 0.0
    return feats


def _dipole_from_gasteiger(mol_3d: Chem.Mol) -> float:
    """Gasteiger 전하 + 3D 좌표로 쌍극자 모멘트 근사 (단위: Debye 비례)."""
    try:
        mol_c = Chem.RWMol(mol_3d)
        ComputeGasteigerCharges(mol_c)
        conf = mol_c.GetConformer()
        dipole = np.zeros(3)
        for atom in mol_c.GetAtoms():
            q = atom.GetDoubleProp("_GasteigerCharge")
            if not math.isfinite(q):
                continue
            pos = conf.GetAtomPosition(atom.GetIdx())
            dipole += q * np.array([pos.x, pos.y, pos.z])
        return float(np.linalg.norm(dipole))   # |μ| (임의 단위)
    except Exception:
        return float("nan")


def _polarizability(mol: Chem.Mol) -> float:
    """원자 분극률 합산 (단위: Å³)."""
    total = 0.0
    mol_h = Chem.AddHs(mol)
    for atom in mol_h.GetAtoms():
        an = atom.GetAtomicNum()
        total += _ATOMIC_POLARIZABILITY.get(an, 1.0)
    return total


class ElectronicExtractor(FeatureExtractor):
    """
    전자 구조 / 분자 간 힘 특성 추출기.

    Parameters
    ----------
    use_xtb : xTB GFN2로 HOMO/LUMO 계산 시도 여부 (느림)
    """

    def __init__(self, use_xtb: bool = False):
        self.use_xtb = use_xtb

    @property
    def prefix(self) -> str:
        return "el"

    def extract(self, mol: Chem.Mol) -> dict[str, float]:
        feats: dict[str, float] = {}

        # ── Gasteiger 전하 통계 ──────────────────────────────────────────────
        feats.update(_gasteiger_charge_features(mol))

        # ── 분극률 근사 ──────────────────────────────────────────────────────
        feats["el_polarizability"] = _polarizability(mol)
        feats["el_molMR"]          = Descriptors.MolMR(mol)  # Crippen MR (Å³)

        # ── 소수성 (LogP) ────────────────────────────────────────────────────
        feats["el_logP"] = Descriptors.MolLogP(mol)

        # ── 수소결합 ─────────────────────────────────────────────────────────
        feats["el_HBD"] = float(rdMolDescriptors.CalcNumHBD(mol))  # donor
        feats["el_HBA"] = float(rdMolDescriptors.CalcNumHBA(mol))  # acceptor

        # ── 극성 표면적 (TPSA) ───────────────────────────────────────────────
        feats["el_tpsa"] = Descriptors.TPSA(mol)

        # ── 쌍극자 모멘트 근사 (3D 필요) ─────────────────────────────────────
        try:
            mol_h = Chem.AddHs(mol)
            params = AllChem.ETKDGv3()
            params.randomSeed = 42
            params.numThreads = 0
            ret = AllChem.EmbedMolecule(mol_h, params)
            if ret == 0:
                AllChem.MMFFOptimizeMolecule(mol_h, mmffVariant="MMFF94s")
                feats["el_dipole_gasteiger"] = _dipole_from_gasteiger(mol_h)
            else:
                feats["el_dipole_gasteiger"] = float("nan")
        except Exception as e:
            logger.warning(f"[cat6] 쌍극자 계산 실패: {e}")
            feats["el_dipole_gasteiger"] = float("nan")

        # ── 전기음성도 가중 특성 ─────────────────────────────────────────────
        # Pauling 전기음성도 (F=3.98, Cl=3.16, Br=2.96, C=2.55, H=2.20, O=3.44)
        _EN: dict[int, float] = {
            1: 2.20, 6: 2.55, 7: 3.04, 8: 3.44,
            9: 3.98, 16: 2.58, 17: 3.16, 35: 2.96, 53: 2.66,
        }
        en_vals = [_EN.get(a.GetAtomicNum(), 2.0) for a in mol.GetAtoms()]
        feats["el_en_mean"]  = float(np.mean(en_vals))
        feats["el_en_max"]   = float(np.max(en_vals))
        feats["el_en_std"]   = float(np.std(en_vals))
        # 분자 평균 전기음성도 (Mulliken 근사)
        feats["el_en_weighted_sum"] = float(
            sum(_EN.get(a.GetAtomicNum(), 2.0) * a.GetTotalDegree()
                for a in mol.GetAtoms())
            / max(mol.GetNumHeavyAtoms(), 1)
        )

        # ── xTB HOMO/LUMO (선택) ─────────────────────────────────────────────
        if self.use_xtb:
            feats.update(self._xtb_features(mol))

        return feats

    def _xtb_features(self, mol: Chem.Mol) -> dict[str, float]:
        """
        xTB GFN2-xTB로 HOMO/LUMO/gap 계산.
        xtb-python 또는 xtb CLI가 설치된 경우에만 동작.

        설치:
            conda install -c conda-forge xtb-python
        또는:
            pip install xtb-python
        """
        nan_result = {
            "el_xtb_homo":    float("nan"),
            "el_xtb_lumo":    float("nan"),
            "el_xtb_gap":     float("nan"),
            "el_xtb_dipole":  float("nan"),
            "el_xtb_energy":  float("nan"),
        }
        try:
            from xtb.interface import Calculator, Param
            from xtb.libxtb import VERBOSITY_MUTED
            import numpy as np_

            # 3D 좌표 생성
            mol_h = Chem.AddHs(mol)
            params_emb = AllChem.ETKDGv3()
            params_emb.randomSeed = 42
            if AllChem.EmbedMolecule(mol_h, params_emb) != 0:
                return nan_result
            AllChem.MMFFOptimizeMolecule(mol_h, mmffVariant="MMFF94s")

            conf = mol_h.GetConformer()
            atoms = np_.array([a.GetAtomicNum() for a in mol_h.GetAtoms()])
            coords = np_.array([
                [conf.GetAtomPosition(i).x,
                 conf.GetAtomPosition(i).y,
                 conf.GetAtomPosition(i).z]
                for i in range(mol_h.GetNumAtoms())
            ]) * 1.8897259886  # Å → Bohr

            calc = Calculator(Param.GFN2xTB, atoms, coords)
            calc.set_verbosity(VERBOSITY_MUTED)
            res = calc.singlepoint()

            homo = res.get_homo_lumo()[0] * 27.2114   # Hartree → eV
            lumo = res.get_homo_lumo()[1] * 27.2114
            return {
                "el_xtb_homo":   homo,
                "el_xtb_lumo":   lumo,
                "el_xtb_gap":    lumo - homo,
                "el_xtb_dipole": float(np_.linalg.norm(res.get_dipole())),
                "el_xtb_energy": res.get_energy(),
            }
        except ImportError:
            logger.debug("[cat6] xtb-python 미설치, HOMO/LUMO 계산 건너뜀")
            return nan_result
        except Exception as e:
            logger.warning(f"[cat6] xTB 계산 실패: {e}")
            return nan_result
