"""
SIGMA - JSON Export Module
Exports complete SignalResult data model to formatted JSON.
"""

import json
from typing import Dict, Any, Union
try:
    from models.signal_result import SignalResult
except ImportError:
    from ..models.signal_result import SignalResult


def export_to_json(result: Union[SignalResult, Dict[str, Any]], filepath: str, indent: int = 2) -> str:
    """Exports signal result dictionary or model to JSON file."""
    if isinstance(result, SignalResult):
        data = result.to_dict()
    else:
        data = dict(result)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent)

    return filepath
