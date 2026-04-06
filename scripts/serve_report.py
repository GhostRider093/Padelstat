import http.server
import socketserver
import webbrowser
import os


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


def ensure_favicon(data_dir: str):
    # Crée un petit favicon pour éviter le 404 récurrent
    ico_path = os.path.join(data_dir, 'favicon.ico')
    if os.path.exists(ico_path):
        return
    try:
        with open(ico_path, 'wb') as f:
            # binaire minimal (pas un vrai ico, mais suffisant pour éviter 404)
            f.write(b'\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00\x04\x00')
    except Exception:
        pass


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(root, 'data')
    os.chdir(data_dir)

    ensure_favicon(data_dir)

    host = '127.0.0.1'
    port = 8001
    url = f'http://{host}:{port}/rapport_test_point.html'
    handler = http.server.SimpleHTTPRequestHandler

    with ThreadingTCPServer((host, port), handler) as httpd:
        try:
            webbrowser.open(url)
        except Exception:
            pass
        print(f"Serving {data_dir} at {url}")
        try:
            httpd.serve_forever(poll_interval=0.5)
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()