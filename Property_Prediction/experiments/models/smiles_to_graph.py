"""
SMILES → PyG Data 변환 유틸리티.

원자/결합 피처 정의는 features/cat2_local_graph.py의 to_graph_data()를 그대로 사용.
  - node_dim = 24 (원자 피처)
  - edge_dim = 9  (결합 피처)

tabular 모델의 lg_* 피처와 동일한 정의에서 파생되므로 실험 해석이 일관된다.
"""
from __future__ import annotations
from typing import List, Optional

import sys
from pathlib import Path

import numpy as np
import torch
from rdkit import Chem
from torch_geometric.data import Data

# features/ 패키지 경로 추가
_PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from features.cat2_local_graph import to_graph_data as _cat2_to_graph_data

# cat2_local_graph.py 기준 차원
ATOM_DIM = 24
BOND_DIM = 9


def mol_to_data(smiles: str, y: Optional[float] = None) -> Optional[Data]:
    """SMILES → PyG Data. 파싱 실패 시 None 반환."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    g = _cat2_to_graph_data(mol)

    x          = torch.tensor(g["x"],          dtype=torch.float)
    edge_index = torch.tensor(g["edge_index"],  dtype=torch.long)
    edge_attr  = torch.tensor(g["edge_attr"],   dtype=torch.float)

    data = Data(x=x, edge_index=edge_index, edge_attr=edge_attr)
    if y is not None:
        data.y = torch.tensor([y], dtype=torch.float)
    return data


def smiles_to_dataset(
    smiles_list: List[str],
    y_list: Optional[np.ndarray] = None,
) -> List[Data]:
    """SMILES 리스트 → PyG Data 리스트 (파싱 실패 시 제외)."""
    dataset = []
    for i, smi in enumerate(smiles_list):
        y = float(y_list[i]) if y_list is not None else None
        data = mol_to_data(smi, y)
        if data is not None:
            dataset.append(data)
    return dataset
