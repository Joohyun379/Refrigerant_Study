"""
범주 4: 3D 구조 특성 (3D Structural Features)

ETKDG 알고리즘으로 3D 형상을 생성한 뒤
분자 형태(shape), 크기(size) 관련 기술자를 계산한다.

추출 특성:
  - 관성 모멘트 주축비 (NPR1, NPR2) → 형태 삼각도 위치
  - 구형도(spherocity), 이방성(asphericity), 이심률(eccentricity)
  - 관성 형태 인자, 선형도 지수
  - 회전 반경 (Rg)
  - van der Waals 부피 · 표면적 (근사)
  - TPSA (Topological Polar Surface Area)
  - WHIM 기술자 (선택, slow)

의존성: RDKit (필수), MMFF94 최적화 (실패 시 ETKDG 좌표 그대로 사용)
"""
from __future__ import annotations
import logging
import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, rdMolDescriptors
from rdkit.Chem.rdMolDescriptors import (
    CalcPMI1, CalcPMI2, CalcPMI3,
    CalcNPR1, CalcNPR2,
    CalcRadiusOfGyration,
    CalcAsphericity,
    CalcEccentricity,
    CalcSpherocityIndex,
    CalcInertialShapeFactor,
)
from .base import FeatureExtractor

logger = logging.getLogger(__name__)


def _embed_mol(mol: Chem.Mol, n_attempts: int = 10) -> Chem.Mol | None:
    """ETKDG 3D 형상 생성 + MMFF94 최적화. 실패 시 None."""
    mol_h = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.numThreads = 0
    params.randomSeed = 42
    ret = AllChem.EmbedMolecule(mol_h, params)
    if ret == -1:
        logger.warning("[cat4] ETKDG 형상 생성 실패")
        return None
    # MMFF94 최적화 (실패해도 ETKDG 좌표 사용)
    try:
        AllChem.MMFFOptimizeMolecule(mol_h, mmffVariant="MMFF94s")
    except Exception:
        pass
    return mol_h


class Geometry3DExtractor(FeatureExtractor):
    """
    3D 구조 기반 특성 추출기.

    Parameters
    ----------
    include_whim : WHIM 기술자 포함 여부 (느림, 114차원 추가)
    """

    def __init__(self, include_whim: bool = False):
        self.include_whim = include_whim

    @property
    def prefix(self) -> str:
        return "rd"

    def extract(self, mol: Chem.Mol) -> dict[str, float]:
        feats: dict[str, float] = {}

        # ── TPSA (2D 기반이므로 3D 불필요) ────────────────────────────────
        feats["rd_tpsa"] = Descriptors.TPSA(mol)

        # ── 3D 형상 생성 ────────────────────────────────────────────────────
        mol_3d = _embed_mol(mol)
        if mol_3d is None:
            nan_keys = [
                "pmi1", "pmi2", "pmi3",
                "npr1", "npr2",
                "rg",
                "asphericity", "eccentricity", "spherocity",
                "inertial_shape",
                "rod_like", "disk_like", "sphere_like",
                "vdw_volume", "vdw_sa",
            ]
            for k in nan_keys:
                feats[f"rd_{k}"] = float("nan")
            if self.include_whim:
                for i in range(114):
                    feats[f"rd_whim_{i}"] = float("nan")
            return feats

        # ── 관성 주모멘트 (PMI) ──────────────────────────────────────────────
        # I1 ≤ I2 ≤ I3, 단위: amu·Å²
        pmi1 = CalcPMI1(mol_3d)
        pmi2 = CalcPMI2(mol_3d)
        pmi3 = CalcPMI3(mol_3d)
        feats["rd_pmi1"] = pmi1
        feats["rd_pmi2"] = pmi2
        feats["rd_pmi3"] = pmi3

        # ── 정규화 PMI 비율 (NPR) → 형태 삼각도 ─────────────────────────────
        # npr1 = I1/I3 ∈ [0, 0.5] : 0=선형, 0.5=원반·구형
        # npr2 = I2/I3 ∈ [0.5, 1] : 0.5=원반, 1=구형
        feats["rd_npr1"] = CalcNPR1(mol_3d)
        feats["rd_npr2"] = CalcNPR2(mol_3d)

        # ── 파생 형태 지수 ───────────────────────────────────────────────────
        # rod-like  : npr1 ≈ 0, npr2 ≈ 0.5
        # disk-like : npr1 ≈ 0.5, npr2 ≈ 0.5
        # sphere    : npr1 ≈ 0.5, npr2 ≈ 1.0
        npr1 = feats["rd_npr1"]
        npr2 = feats["rd_npr2"]
        feats["rd_rod_like"]    = max(0.0, 1.0 - 2 * npr1)        # ~ 선형성
        feats["rd_disk_like"]   = max(0.0, 2 * npr1 + 2 * npr2 - 2) # ~ 원반성 (근사)
        feats["rd_sphere_like"] = max(0.0, 2 * npr1 + 2 * npr2 - 2 * max(0, 1 - npr2))

        # ── 회전 반경, 형태 기술자 ──────────────────────────────────────────
        feats["rd_rg"]              = CalcRadiusOfGyration(mol_3d)
        feats["rd_asphericity"]     = CalcAsphericity(mol_3d)
        feats["rd_eccentricity"]    = CalcEccentricity(mol_3d)
        feats["rd_spherocity"]      = CalcSpherocityIndex(mol_3d)
        feats["rd_inertial_shape"]  = CalcInertialShapeFactor(mol_3d)

        # ── van der Waals 부피·표면적 (근사, AllChem) ────────────────────────
        try:
            vdw_vol = AllChem.ComputeMolVolume(mol_3d)
            feats["rd_vdw_volume"] = vdw_vol
        except Exception:
            feats["rd_vdw_volume"] = float("nan")

        try:
            from rdkit.Chem import rdFreeSASA
            radii = rdFreeSASA.classifyAtoms(mol_3d)
            feats["rd_vdw_sa"] = rdFreeSASA.CalcSASA(mol_3d, radii)
        except Exception:
            feats["rd_vdw_sa"] = float("nan")

        # ── WHIM 기술자 (선택) ──────────────────────────────────────────────
        if self.include_whim:
            try:
                whim = rdMolDescriptors.CalcWHIM(mol_3d)
                for i, v in enumerate(whim):
                    feats[f"rd_whim_{i}"] = float(v)
            except Exception as e:
                logger.warning(f"[cat4] WHIM 계산 실패: {e}")
                for i in range(114):
                    feats[f"rd_whim_{i}"] = float("nan")

        return feats
