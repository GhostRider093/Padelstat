from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

# Origines autorisées à appeler le service local
_ALLOWED_ORIGINS = {
    "http://localhost:8012",
    "http://127.0.0.1:8012",
    "http://57.129.110.251:8012",
    "http://localhost",
    "http://127.0.0.1",
    # fichier ouvert directement dans le navigateur
    "null",
}


SERVICE_TOKEN = "005625"


class PadelRemoteControlServer:
    def __init__(self, root, app, host: str = "127.0.0.1", port: int = 8766,
                 token: str | None = None) -> None:
        self.root = root
        self.app = app
        self.host = host
        self.port = port
        self.token: str = token or SERVICE_TOKEN
        self.httpd: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.httpd is not None:
            return

        server_ref = self

        class Handler(BaseHTTPRequestHandler):
            def _origin(self) -> str:
                return self.headers.get("Origin", "").strip()

            def _cors(self) -> None:
                origin = self._origin()
                allowed = origin if origin in _ALLOWED_ORIGINS else ""
                if allowed:
                    self.send_header("Access-Control-Allow-Origin", allowed)
                    self.send_header("Vary", "Origin")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, X-PadelStat-Token")

            def _auth_ok(self) -> bool:
                return self.headers.get("X-PadelStat-Token", "") == server_ref.token

            def _send(self, status: int, payload: dict[str, Any]) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self._cors()
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: Any) -> None:
                return

            def do_OPTIONS(self) -> None:
                self.send_response(204)
                self._cors()
                self.end_headers()

            def do_GET(self) -> None:
                if self.path == "/health":
                    # Pas d'auth sur health — juste vérifier que le service tourne
                    origin = self._origin()
                    if origin and origin not in _ALLOWED_ORIGINS:
                        self._send(403, {"ok": False, "error": "Origin non autorisée"})
                        return
                    self._send(200, {"status": "ok"})
                    return
                if not self._auth_ok():
                    self._send(401, {"ok": False, "error": "Token invalide"})
                    return
                if self.path == "/state":
                    try:
                        state = server_ref.call_ui(server_ref.app.remote_get_state)
                        self._send(200, {"ok": True, "result": state})
                    except Exception as exc:
                        self._send(500, {"ok": False, "error": str(exc)})
                    return
                self._send(404, {"ok": False, "error": "Not found"})

            def do_POST(self) -> None:
                origin = self._origin()
                if origin and origin not in _ALLOWED_ORIGINS:
                    self._send(403, {"ok": False, "error": "Origin non autorisée"})
                    return
                if not self._auth_ok():
                    self._send(401, {"ok": False, "error": "Token invalide"})
                    return

                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length else b"{}"

                try:
                    payload = json.loads(raw.decode("utf-8"))
                except Exception as exc:
                    self._send(400, {"ok": False, "error": f"JSON invalide: {exc}"})
                    return

                if self.path == "/annotation":
                    try:
                        result = server_ref.dispatch_annotation(payload)
                        self._send(200, {"ok": True, "result": result})
                    except Exception as exc:
                        self._send(500, {"ok": False, "error": str(exc)})
                    return

                if self.path == "/command":
                    try:
                        command = str(payload.get("command", "")).strip()
                        params = payload.get("params", {}) or {}
                        result = server_ref.dispatch(command, params)
                        self._send(200, {"ok": True, "result": result})
                    except Exception as exc:
                        self._send(500, {"ok": False, "error": str(exc)})
                    return

                self._send(404, {"ok": False, "error": "Not found"})

        self.httpd = ThreadingHTTPServer((self.host, self.port), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, name="padel-remote-control", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.httpd is None:
            return
        try:
            self.httpd.shutdown()
            self.httpd.server_close()
        finally:
            self.httpd = None
            self.thread = None

    def call_ui(self, func, *args, **kwargs):
        done = threading.Event()
        box: dict[str, Any] = {}

        def runner() -> None:
            try:
                box["result"] = func(*args, **kwargs)
            except Exception as exc:
                box["error"] = exc
            finally:
                done.set()

        self.root.after(0, runner)
        done.wait(timeout=15)
        if not done.is_set():
            raise TimeoutError("UI call timed out")
        if "error" in box:
            raise box["error"]
        return box.get("result")

    def dispatch(self, command: str, params: dict[str, Any]) -> Any:
        mapping = {
            "open_video_dialog": lambda: self.call_ui(self.app.remote_open_video_dialog),
            "load_video": lambda: self.call_ui(self.app.remote_load_video, str(params["video_path"])),
            "play": lambda: self.call_ui(self.app.remote_play),
            "pause": lambda: self.call_ui(self.app.remote_pause),
            "toggle_play_pause": lambda: self.call_ui(self.app.remote_toggle_play_pause),
            "seek_relative": lambda: self.call_ui(self.app.remote_seek_relative, float(params["seconds"])),
            "seek_to": lambda: self.call_ui(self.app.remote_seek_to, float(params["seconds"])),
            "set_speed": lambda: self.call_ui(self.app.remote_set_speed, float(params["speed"])),
            "rotate_video": lambda: self.call_ui(self.app.remote_rotate_video),
            "generate_quick_report": lambda: self.call_ui(self.app.remote_generate_quick_report),
            "export_json": lambda: self.call_ui(self.app.remote_export_json),
            "undo_last": lambda: self.call_ui(self.app.remote_undo_last),
            "state": lambda: self.call_ui(self.app.remote_get_state),
        }
        if command not in mapping:
            raise ValueError(f"Unknown command: {command}")
        return mapping[command]()

    def dispatch_annotation(self, payload: dict[str, Any]) -> Any:
        """Reçoit une annotation du frontend et l'ajoute à l'annotation_manager."""
        ann_type  = str(payload.get("type", "")).strip()
        joueur    = str(payload.get("joueur", "")).strip()
        type_coup = str(payload.get("type_coup", "autre")).strip()
        timestamp = float(payload.get("timestamp", 0.0))
        frame     = int(payload.get("frame", 0))

        if ann_type == "point_gagnant":
            result = self.call_ui(
                self.app.annotation_manager.add_point_gagnant,
                joueur, timestamp, frame, type_coup
            )
        elif ann_type == "faute_directe":
            result = self.call_ui(
                self.app.annotation_manager.add_faute_directe,
                joueur, timestamp, frame, type_coup
            )
        elif ann_type == "faute_provoquee":
            attaquant  = str(payload.get("attaquant", joueur)).strip()
            defenseur  = str(payload.get("defenseur", "")).strip()
            result = self.call_ui(
                self.app.annotation_manager.add_faute_provoquee,
                attaquant, defenseur, timestamp, frame,
                type_coup, None
            )
        else:
            raise ValueError(f"Type d'annotation inconnu: {ann_type}")

        # Autosave JSON après chaque annotation
        self.call_ui(self.app.annotation_manager.autosave)
        return {"annotation": result}
