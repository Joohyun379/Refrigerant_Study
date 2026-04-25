"""
features 패키지 — 냉매 물성 예측용 분자 특성 추출기

범주:
  1. GroupContributionExtractor  (cat1_group_contribution)  — Joback 원자단
  2. LocalGraphExtractor         (cat2_local_graph)          — GNN 노드/엣지 특성
  3. GlobalTopologyExtractor     (cat3_global_topology)      — 위상·구성 기술자
  4. Geometry3DExtractor         (cat4_geometry_3d)          — 3D 형태 기술자
  5. RefrigerantSpecificExtractor(cat5_refrigerant)          — 냉매 특화
  6. ElectronicExtractor         (cat6_electronic)           — 전자 구조

GNN 그래프 데이터:
  from features.cat2_local_graph import to_graph_data
"""
from .pipeline                import FeaturePipeline
from .cat1_group_contribution import GroupContributionExtractor
from .cat2_local_graph        import LocalGraphExtractor, to_graph_data
from .cat3_global_topology    import GlobalTopologyExtractor
from .cat4_geometry_3d        import Geometry3DExtractor
from .cat5_refrigerant        import RefrigerantSpecificExtractor
from .cat6_electronic         import ElectronicExtractor

__all__ = [
    "FeaturePipeline",
    "GroupContributionExtractor",
    "LocalGraphExtractor",
    "to_graph_data",
    "GlobalTopologyExtractor",
    "Geometry3DExtractor",
    "RefrigerantSpecificExtractor",
    "ElectronicExtractor",
]
