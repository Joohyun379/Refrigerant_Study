"""
Feature extractor 기반 추상 클래스
"""
from __future__ import annotations
from abc import ABC, abstractmethod
import logging
import pandas as pd
from rdkit import Chem

logger = logging.getLogger(__name__)


class FeatureExtractor(ABC):
    """
    평탄(flat) 특성 벡터 추출기 기반 클래스.
    각 범주별 extractor는 이 클래스를 상속받아 `extract()`와 `prefix`를 구현한다.
    """

    @property
    @abstractmethod
    def prefix(self) -> str:
        """특성 이름 접두사 (예: 'gc', 'gt', 'rd', ...)"""

    @abstractmethod
    def extract(self, mol: Chem.Mol) -> dict[str, float]:
        """
        RDKit Mol 객체 → 특성 dict 반환.
        키는 prefix 포함 (예: 'gc_CH3', 'gt_mw').
        실패한 특성은 float('nan')으로 채운다.
        """

    def __call__(self, smiles: str) -> dict[str, float]:
        """SMILES 문자열에서 직접 특성 추출."""
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise ValueError(f"Invalid SMILES: {smiles}")
        return self.extract(mol)

    def extract_batch(
        self,
        smiles_list: list[str],
        identifiers: list[str] | None = None,
    ) -> pd.DataFrame:
        """SMILES 리스트 → 특성 DataFrame. 실패 행은 NaN으로 채움."""
        records = []
        for i, smi in enumerate(smiles_list):
            try:
                records.append(self(smi))
            except Exception as e:
                ident = identifiers[i] if identifiers else smi
                logger.warning(f"[{self.__class__.__name__}] {ident}: {e}")
                records.append({})
        df = pd.DataFrame(records)
        if identifiers:
            df.insert(0, "identifier", identifiers)
        return df
