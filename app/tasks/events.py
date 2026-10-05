import json
from typing import Any

def format_sse_event(event_type: str, data: dict[str, Any], event_id: str = "") -> str:
    lines = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event_type}")
    lines.append(f"data: {json.dumps(data)}")
    return "\n".join(lines) + "\n\n"
