"""
통합 특성 추출 파이프라인

사용법:
    from features.pipeline import FeaturePipeline
    from features.cat2_local_graph import to_graph_data
    from rdkit import Chem

    # 평탄 특성 벡터 (전통 ML용)
    pipe = FeaturePipeline()
    df = pipe.transform_batch(smiles_list, identifiers)

    # GNN용 그래프 데이터
    mol = Chem.MolFromSmiles("FC(F)=CC(F)(F)F")
    g = to_graph_data(mol)
    # → {"x": np.ndarray, "edge_index": np.ndarray, "edge_attr": np.ndarray}
"""
from __future__ import annotations
import logging
import pandas as pd
from rdkit import Chem

from .cat1_group_contribution import GroupContributionExtractor
from .cat2_local_graph        import LocalGraphExtractor
from .cat3_global_topology    import GlobalTopologyExtractor
from .cat4_geometry_3d        import Geometry3DExtractor
from .cat5_refrigerant        import RefrigerantSpecificExtractor
from .cat6_electronic         import ElectronicExtractor

logger = logging.getLogger(__name__)


class FeaturePipeline:
    """
    6개 범주 특성을 하나의 평탄 벡터로 통합하는 파이프라인.

    Parameters
    ----------
    tb_map        : {identifier: Tb_K} — Joback Tc 추정에 사용
    include_3d    : 범주 4 (3D 기하학) 포함 여부 (느림)
    include_whim  : 3D WHIM 기술자 포함 여부 (더 느림)
    use_xtb       : 범주 6 xTB HOMO/LUMO 포함 여부 (매우 느림)
    categories    : 포함할 범주 번호 리스트 (기본: 전체 [1,2,3,4,5,6])
    """

    def __init__(
        self,
        tb_map: dict[str, float] | None = None,
        include_3d:   bool = True,
        include_whim: bool = False,
        use_xtb:      bool = False,
        categories:   list[int] | None = None,
    ):
        active = set(categories) if categories else {1, 2, 3, 4, 5, 6}

        self._extractors: dict[int, object] = {}
        if 1 in active:
            self._extractors[1] = GroupContributionExtractor(tb_map=tb_map)
        if 2 in active:
            self._extractors[2] = LocalGraphExtractor()
        if 3 in active:
            self._extractors[3] = GlobalTopologyExtractor()
        if 4 in active and include_3d:
            self._extractors[4] = Geometry3DExtractor(include_whim=include_whim)
        if 5 in active:
            self._extractors[5] = RefrigerantSpecificExtractor()
        if 6 in active:
            self._extractors[6] = ElectronicExtractor(use_xtb=use_xtb)

    # ── 단일 분자 ──────────────────────────────────────────────────────────
    def transform(
        self,
        smiles: str,
        identifier: str | None = None,
    ) -> dict[str, float]:
        """
        단일 SMILES → 전체 특성 dict.
        범주 1 (GroupContribution)에 identifier를 전달하여 Tb 조회를 시원하게.
        """
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise ValueError(f"Invalid SMILES: {smiles}")

        feats: dict[str, float] = {}
        for cat_id, extractor in self._extractors.items():
            try:
                if cat_id == 1:
                    # GroupContributionExtractor는 identifier 인자를 받음
                    chunk = extractor.extract(mol, identifier=identifier)
                else:
                    chunk = extractor.extract(mol)
                feats.update(chunk)
            except Exception as e:
                logger.warning(
                    f"[pipeline] cat{cat_id} 실패 "
                    f"({identifier or smiles[:20]}): {e}"
                )
        return feats

    # ── 배치 ──────────────────────────────────────────────────────────────
    def transform_batch(
        self,
        smiles_list: list[str],
        identifiers: list[str] | None = None,
    ) -> pd.DataFrame:
        """
        SMILES 리스트 → 특성 DataFrame.
        실패한 행은 NaN으로 채움.
        """
        records = []
        ids     = identifiers or smiles_list
        for i, smi in enumerate(smiles_list):
            ident = ids[i]
            try:
                records.append(self.transform(smi, identifier=ident))
            except Exception as e:
                logger.warning(f"[pipeline] {ident}: {e}")
                records.append({})

        df = pd.DataFrame(records)
        if identifiers:
            df.insert(0, "identifier", identifiers)
        return df

    @property
    def feature_names(self) -> list[str]:
        """샘플 분자로 특성 이름 목록 추출 (CH4 기준)."""
        sample = self.transform("C")
        return [k for k in sample if k != "identifier"]

    def summary(self) -> None:
        """활성화된 범주 및 특성 수 출력."""
        names = self.feature_names
        print(f"활성 범주: {sorted(self._extractors.keys())}")
        print(f"총 특성 수: {len(names)}")
        cats: dict[str, int] = {}
        for n in names:
            prefix = n.split("_")[0]
            cats[prefix] = cats.get(prefix, 0) + 1
        for prefix, cnt in sorted(cats.items()):
            label = {
                "gc": "범주1 Group Contribution",
                "lg": "범주2 Local Graph",
                "gt": "범주3 Global Topology",
                "rd": "범주4 3D Geometry",
                "rf": "범주5 Refrigerant-Specific",
                "el": "범주6 Electronic",
            }.get(prefix, prefix)
            print(f"  {label:40s}: {cnt:4d}개")
