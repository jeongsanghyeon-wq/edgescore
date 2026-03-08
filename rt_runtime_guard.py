from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime

RUNTIME_STATE = Path(__file__).with_name('runtime_state.json')
RUNTIME_AUDIT = Path(__file__).with_name('runtime_audit.jsonl')


def _load_state() -> dict:
    if not RUNTIME_STATE.exists():
        return {}
    try:
        return json.loads(RUNTIME_STATE.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    try:
        RUNTIME_STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass


def append_runtime_audit(event: str, **payload) -> None:
    try:
        row = {'ts': datetime.now().isoformat(timespec='seconds'), 'event': event, **payload}
        with RUNTIME_AUDIT.open('a', encoding='utf-8') as f:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    except Exception:
        pass


def save_runtime_snapshot(*, monitor=None, mode: str = '', emergency_stop: bool | None = None) -> None:
    state = _load_state()
    state['runtime_snapshot'] = {
        'ts': datetime.now().isoformat(timespec='seconds'),
        'mode': mode,
        'positions': len(getattr(monitor, 'positions', {}) or {}),
        'universe': len(getattr(monitor, 'universe', {}) or {}),
        'regime': getattr(monitor, 'regime', ''),
        'emergency_stop': emergency_stop,
    }
    _save_state(state)


def build_runtime_health_report(*, monitor=None, mode: str = '', emergency_stop: bool = False) -> str:
    pos = len(getattr(monitor, 'positions', {}) or {})
    uni = len(getattr(monitor, 'universe', {}) or {})
    reg = getattr(monitor, 'regime', '-')
    mode_str = mode or 'unknown'
    return f"mode={mode_str} | regime={reg} | positions={pos} | universe={uni} | emergency_stop={emergency_stop}"
