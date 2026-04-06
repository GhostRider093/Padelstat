from __future__ import annotations

import json
import sys
import traceback
from typing import Any

from padel_stats_mcp import SESSION


def _ok(request_id: int | None, result: Any) -> dict[str, Any]:
    return {"id": request_id, "ok": True, "result": result}


def _error(request_id: int | None, message: str) -> dict[str, Any]:
    return {"id": request_id, "ok": False, "error": message}


def _dispatch(method: str, params: dict[str, Any]) -> Any:
    if method == "status":
        return {
            "status": "ok",
            "session": SESSION.get_state(),
        }
    if method == "padel_reset_session":
        return SESSION.reset(
            data_folder=params.get("data_folder", "data"),
            match_name=params.get("match_name", "Match padel"),
        )
    if method == "padel_set_players":
        return SESSION.set_players(params.get("players", []))
    if method == "padel_set_video":
        return SESSION.set_video(params["video_path"])
    if method == "padel_set_capture_context":
        return SESSION.set_capture_context(
            timestamp=params.get("timestamp"),
            frame=params.get("frame"),
        )
    if method == "padel_parse_stat_command":
        return SESSION.parse_command(params["text"])
    if method == "padel_apply_stat_command":
        return SESSION.apply_text(
            params["text"],
            timestamp=params.get("timestamp"),
            frame=params.get("frame"),
        )
    if method == "padel_add_stat":
        parsed = {
            "action": "nouveau_point",
            "joueur": params["joueur"],
            "defenseur": params.get("defenseur"),
            "type_point": params["type_point"],
            "type_coup": params.get("type_coup"),
        }
        return SESSION.apply_parsed(
            parsed,
            timestamp=params.get("timestamp"),
            frame=params.get("frame"),
        )
    if method == "padel_remove_last_stat":
        return SESSION.apply_parsed({"action": "annuler"})
    if method == "padel_save_session":
        return SESSION.apply_parsed({"action": "sauvegarder"})
    if method == "padel_export_json":
        return SESSION.export_json(output_path=params.get("output_path"))
    if method == "padel_generate_html_report":
        return SESSION.export_html(output_path=params.get("output_path"))
    if method == "padel_get_stats":
        return {
            "ok": True,
            "stats": SESSION.manager.get_stats(),
            "point_count": len(SESSION.manager.get_all_annotations()),
        }
    if method == "padel_get_session_state":
        return SESSION.get_state()
    raise ValueError(f"Unknown method: {method}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)

    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue

        request_id: int | None = None
        try:
            payload = json.loads(line)
            request_id = payload.get("id")
            method = payload["method"]
            params = payload.get("params", {})
            response = _ok(request_id, _dispatch(method, params))
        except Exception as exc:
            sys.stderr.write(traceback.format_exc())
            response = _error(request_id, str(exc))

        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
