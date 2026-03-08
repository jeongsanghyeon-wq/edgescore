"""공통 진입 정책.
전략 판단만 담당하고 주문/체결은 포함하지 않는다.
"""
from __future__ import annotations
from dataclasses import dataclass
from .regime import get_regime_threshold

@dataclass(frozen=True)
class EntryDecision:
    allowed: bool
    reason: str
    threshold: float


def should_enter_by_edge(edge: float, regime: str, *, slip_ok: bool = True, extra_gate: bool = True) -> EntryDecision:
    threshold = float(get_regime_threshold(regime))
    edge = float(edge)
    if not slip_ok:
        return EntryDecision(False, 'slippage_blocked', threshold)
    if not extra_gate:
        return EntryDecision(False, 'extra_gate_blocked', threshold)
    if edge >= threshold:
        return EntryDecision(True, f'edge_gte_threshold({edge:.4f}>={threshold:.4f})', threshold)
    return EntryDecision(False, f'edge_below_threshold({edge:.4f}<{threshold:.4f})', threshold)
