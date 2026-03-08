"""원본 RT/BT 공통 국면 기준값.
안정형 리팩토링 원칙에 따라 원본 숫자를 그대로 사용한다.
"""
from __future__ import annotations

REGIME_EDGE_THRESHOLD = {
    "BULL": 0.55,
    "SIDE": 0.60,
    "BEAR": 0.75,
}

def get_regime_threshold(regime: str) -> float:
    return REGIME_EDGE_THRESHOLD.get(regime, REGIME_EDGE_THRESHOLD["SIDE"])
