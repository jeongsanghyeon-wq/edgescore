"""공통 청산/경보 정책.
원본 동작 보존을 위해 edge 기반 비교만 공용화한다.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ExitDecision:
    should_exit: bool
    reason: str
    threshold: float


def should_exit_by_edge(edge_now: float, sell_edge_threshold: float) -> ExitDecision:
    edge_now = float(edge_now)
    sell_edge_threshold = float(sell_edge_threshold)
    if edge_now < sell_edge_threshold:
        return ExitDecision(True, f'edge_below_sell_threshold({edge_now:.4f}<{sell_edge_threshold:.4f})', sell_edge_threshold)
    return ExitDecision(False, f'edge_ok({edge_now:.4f}>={sell_edge_threshold:.4f})', sell_edge_threshold)


def should_alert_sell_edge(edge_now: float, sell_edge_threshold: float, alerted: bool) -> bool:
    return should_exit_by_edge(edge_now, sell_edge_threshold).should_exit and (not bool(alerted))


def should_reset_sell_edge_alert(edge_now: float, sell_edge_threshold: float) -> bool:
    return not should_exit_by_edge(edge_now, sell_edge_threshold).should_exit
