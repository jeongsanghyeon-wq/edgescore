"""공통 score/edge 엔진 이관을 위한 안전형 어댑터.
이번 단계에서는 원본 계산식을 바꾸지 않고 edge 스냅샷 인터페이스만 제공한다.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class EdgeSnapshot:
    edge: float
    source: str = 'adapter'
    note: str = ''


def snapshot(edge: float, source: str = 'adapter', note: str = '') -> EdgeSnapshot:
    return EdgeSnapshot(edge=float(edge), source=source, note=note)


def to_edge_int(edge: float) -> int:
    return round(float(edge) * 100)
