"""
범주 2: 국소 그래프 특성 (Local Graph Features)

두 가지 출력 형식:
  A) GNN용 그래프 데이터  → to_graph_data(mol)
     - x         : [N_atoms, N_atom_feat] 원자 특성 행렬
     - edge_index : [2, 2*N_bonds]         양방향 엣지 인덱스
     - edge_attr  : [2*N_bonds, N_bond_feat] 엣지 특성 행렬

  B) 전통 ML용 평탄 벡터  → extract(mol)
     - 원자 특성의 분포 통계(mean/max/min/std)를 집계
     - 라플라시안 스펙트럼 통계 (위상 정보 보완)

원자 특성 (15차원):
  atomic_num (one-hot, 11종) | degree | formal_charge | num_Hs
  hybridization (one-hot, 5종) | is_aromatic | is_in_ring | chirality (one-hot, 3종)

결합 특성 (8차원):
  bond_type (one-hot, 4종) | is_in_ring | is_conjugated | stereo (one-hot, 2종)
"""
from __future__ import annotations
import logging
import numpy as np
from rdkit import Chem
from rdkit.Chem import rdmolops
from .base import FeatureExtractor

logger = logging.getLogger(__name__)

# ── 원자 one-hot 범주 정의 ─────────────────────────────────────────────────
ATOM_TYPES      = [6, 7, 8, 9, 14, 15, 16, 17, 35, 53, 0]   # 0 = other
HYBRIDIZATIONS  = [
    Chem.rdchem.HybridizationType.SP,
    Chem.rdchem.HybridizationType.SP2,
    Chem.rdchem.HybridizationType.SP3,
    Chem.rdchem.HybridizationType.SP3D,
    Chem.rdchem.HybridizationType.SP3D2,
]
CHIRALITIES     = [
    Chem.rdchem.ChiralType.CHI_UNSPECIFIED,
    Chem.rdchem.ChiralType.CHI_TETRAHEDRAL_CW,
    Chem.rdchem.ChiralType.CHI_TETRAHEDRAL_CCW,
]
BOND_TYPES      = [
    Chem.rdchem.BondType.SINGLE,
    Chem.rdchem.BondType.DOUBLE,
    Chem.rdchem.BondType.TRIPLE,
    Chem.rdchem.BondType.AROMATIC,
]
STEREO_TYPES    = [
    Chem.rdchem.BondStereo.STEREONONE,
    Chem.rdchem.BondStereo.STEREOE,
    Chem.rdchem.BondStereo.STEREOZ,
]

N_ATOM_FEAT = len(ATOM_TYPES) + 1 + 1 + 1 + len(HYBRIDIZATIONS) + 1 + 1 + len(CHIRALITIES)
# = 11 + 1 + 1 + 1 + 5 + 1 + 1 + 3 = 24
N_BOND_FEAT = len(BOND_TYPES) + 1 + 1 + len(STEREO_TYPES)
# = 4 + 1 + 1 + 3 = 9


def _one_hot(value, choices: list) -> list[float]:
    return [1.0 if value == c else 0.0 for c in choices]


def _atom_features(atom: Chem.rdchem.Atom) -> list[float]:
    an = atom.GetAtomicNum()
    an_key = an if an in ATOM_TYPES[:-1] else 0
    feats = (
        _one_hot(an_key, ATOM_TYPES)                   # 11
        + [float(atom.GetDegree())]                    # 1
        + [float(atom.GetFormalCharge())]              # 1
        + [float(atom.GetTotalNumHs())]                # 1
        + _one_hot(atom.GetHybridization(), HYBRIDIZATIONS)  # 5
        + [float(atom.GetIsAromatic())]                # 1
        + [float(atom.IsInRing())]                     # 1
        + _one_hot(atom.GetChiralTag(), CHIRALITIES)   # 3
    )
    return feats  # dim = 24


def _bond_features(bond: Chem.rdchem.Bond) -> list[float]:
    feats = (
        _one_hot(bond.GetBondType(), BOND_TYPES)       # 4
        + [float(bond.IsInRing())]                     # 1
        + [float(bond.GetIsConjugated())]              # 1
        + _one_hot(bond.GetStereo(), STEREO_TYPES)     # 3
    )
    return feats  # dim = 9


def to_graph_data(mol: Chem.Mol) -> dict:
    """
    GNN 입력용 그래프 데이터 딕셔너리 반환.

    Returns
    -------
    {
      "x"          : np.ndarray [N, 24],
      "edge_index" : np.ndarray [2, 2E],
      "edge_attr"  : np.ndarray [2E, 9],
    }
    PyTorch Geometric Data() 변환:
        data = Data(
            x=torch.tensor(g["x"], dtype=torch.float),
            edge_index=torch.tensor(g["edge_index"], dtype=torch.long),
            edge_attr=torch.tensor(g["edge_attr"], dtype=torch.float),
        )
    """
    atom_feats = [_atom_features(a) for a in mol.GetAtoms()]
    x = np.array(atom_feats, dtype=np.float32)  # [N, 24]

    src_list, dst_list, edge_feat_list = [], [], []
    for bond in mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        bf = _bond_features(bond)
        # 양방향
        src_list += [i, j]
        dst_list += [j, i]
        edge_feat_list += [bf, bf]

    edge_index = np.array([src_list, dst_list], dtype=np.int64)   # [2, 2E]
    edge_attr  = np.array(edge_feat_list, dtype=np.float32)        # [2E, 9]

    return {"x": x, "edge_index": edge_index, "edge_attr": edge_attr}


class LocalGraphExtractor(FeatureExtractor):
    """
    원자/결합 특성을 집계하여 평탄 특성 벡터 반환 (전통 ML용).

    집계 방식:
      - 원자 특성: 분자 내 모든 원자에 대해 mean / max / std 계산
      - 라플라시안 스펙트럼: 고유값 상위 k개의 mean/std (위상 정보)
    """

    def __init__(self, n_laplacian: int = 5):
        """
        Parameters
        ----------
        n_laplacian : 라플라시안 스펙트럼에서 사용할 고유값 수
        """
        self.n_laplacian = n_laplacian

    @property
    def prefix(self) -> str:
        return "lg"

    # ── 원자 특성 이름 ──────────────────────────────────────────────────────
    @staticmethod
    def _atom_feat_names() -> list[str]:
        names = []
        for an in ATOM_TYPES:
            names.append(f"atom_type_{an}")
        names += ["degree", "formal_charge", "num_Hs"]
        for h in ["SP", "SP2", "SP3", "SP3D", "SP3D2"]:
            names.append(f"hybr_{h}")
        names += ["is_aromatic", "is_in_ring"]
        for c in ["unspec", "CW", "CCW"]:
            names.append(f"chiral_{c}")
        return names  # 24 names

    def extract(self, mol: Chem.Mol) -> dict[str, float]:
        feats: dict[str, float] = {}
        atom_mat = np.array([_atom_features(a) for a in mol.GetAtoms()])
        # [N, 24]

        feat_names = self._atom_feat_names()
        for stat, fn in [("mean", np.mean), ("max", np.max), ("std", np.std)]:
            vals = fn(atom_mat, axis=0)
            for name, val in zip(feat_names, vals):
                feats[f"lg_{stat}_{name}"] = float(val)

        # ── 라플라시안 스펙트럼 ────────────────────────────────────────────
        try:
            adj = rdmolops.GetAdjacencyMatrix(mol).astype(float)
            deg = np.diag(adj.sum(axis=1))
            lap = deg - adj
            eigvals = np.sort(np.linalg.eigvalsh(lap))
            # 가장 작은 nonzero 고유값들 (Fiedler vector 방향)
            nonzero = eigvals[eigvals > 1e-8]
            pad = np.zeros(self.n_laplacian)
            pad[: len(nonzero[: self.n_laplacian])] = nonzero[: self.n_laplacian]
            for i, v in enumerate(pad):
                feats[f"lg_lap_eigval_{i}"] = float(v)
            feats["lg_lap_mean"]    = float(eigvals.mean())
            feats["lg_lap_max"]     = float(eigvals[-1])
            feats["lg_algebraic_connectivity"] = float(nonzero[0]) if len(nonzero) > 0 else 0.0
        except Exception as e:
            logger.warning(f"[cat2] 라플라시안 계산 실패: {e}")
            for i in range(self.n_laplacian):
                feats[f"lg_lap_eigval_{i}"] = float("nan")
            feats["lg_lap_mean"] = float("nan")
            feats["lg_lap_max"]  = float("nan")
            feats["lg_algebraic_connectivity"] = float("nan")

        return feats
