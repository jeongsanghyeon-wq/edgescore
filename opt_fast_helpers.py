from __future__ import annotations
import json, random
from pathlib import Path
from typing import Callable

TOPN_FILE = Path(__file__).with_name('optimizer_topn.json')


def random_search(trades: list,
                  grid: dict,
                  cfg: dict,
                  simulate_func: Callable[[list, dict], dict],
                  *,
                  samples: int = 400,
                  seed: int = 42,
                  topn: int = 20,
                  score_func: Callable[[dict], float] | None = None) -> dict:
    """Grid Search 대체용 경량 랜덤 탐색."""
    rng = random.Random(seed)
    keys = list(grid.keys())
    if score_func is None:
        def score_func(result: dict) -> float:
            mdd_penalty = max(0, abs(result.get('mdd', 0)) - 0.15)
            return (result.get('sharpe', 0) * (1 - mdd_penalty * 3) * (1 + result.get('win_rate', 0)))

    best_score = float('-inf')
    best_params: dict = {}
    best_result: dict = {}
    top_rows: list[dict] = []

    for _ in range(max(int(samples), 1)):
        params = {k: rng.choice(grid[k]) for k in keys}
        params['max_pos_ratio'] = cfg.get('MAX_POSITION_RATIO', 0.30)
        result = simulate_func(trades, params)
        score = score_func(result)
        row = {'score': score, 'params': params, 'result': result}
        top_rows.append(row)
        top_rows.sort(key=lambda x: x['score'], reverse=True)
        if len(top_rows) > topn:
            top_rows = top_rows[:topn]
        if score > best_score:
            best_score = score
            best_params = params
            best_result = result

    try:
        TOPN_FILE.write_text(json.dumps(top_rows, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass

    return {
        'params': best_params,
        'result': best_result,
        'score': best_score,
        'meta': {
            'mode': 'random_search',
            'samples': samples,
            'seed': seed,
            'topn_saved': min(len(top_rows), topn),
        }
    }
