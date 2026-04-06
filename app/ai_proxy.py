"""
Proxy HTTP local pour relayer les requêtes vers Ollama (local GPU ou serveur distant).
Résout les limitations CORS du HTML local. Tourne sur localhost:5050 en thread daemon.
Détecte automatiquement si Ollama local est disponible, sinon bascule sur le serveur.
"""

import json
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

LOCAL_OLLAMA  = "http://localhost:11434"
REMOTE_OLLAMA = "http://57.129.110.251:11434"
PROXY_PORT = 5050

_server_instance = None
_server_lock = threading.Lock()
_ollama_target = None  # déterminé au démarrage


def _detect_target() -> str:
    try:
        requests.get(f"{LOCAL_OLLAMA}/api/tags", timeout=2).raise_for_status()
        print("[OllamaProxy] Ollama local détecté → relais GPU local")
        return LOCAL_OLLAMA
    except Exception:
        print("[OllamaProxy] Ollama local absent → relais serveur distant")
        return REMOTE_OLLAMA


class _ProxyHandler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            resp = requests.post(
                f"{_ollama_target}{self.path}",
                data=body,
                headers={"Content-Type": "application/json"},
                timeout=180,
            )
            self.send_response(resp.status_code)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp.content)
        except Exception as exc:
            self.send_response(500)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(exc)}).encode())

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt, *args):  # silencieux
        pass


def start_proxy(port: int = PROXY_PORT) -> HTTPServer:
    """Démarre le proxy dans un thread daemon. Idempotent (ne recrée pas si déjà actif)."""
    global _server_instance, _ollama_target
    with _server_lock:
        if _server_instance is not None:
            return _server_instance
        _ollama_target = _detect_target()
        server = HTTPServer(("localhost", port), _ProxyHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True, name="OllamaProxy")
        thread.start()
        _server_instance = server
        print(f"[OllamaProxy] Proxy démarré sur http://localhost:{port} → {_ollama_target}")
        return server
