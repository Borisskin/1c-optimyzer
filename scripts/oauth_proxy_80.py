"""Мини-proxy на порту 80 для OAuth callback (local dev only).

Yandex OAuth настроен на redirect_uri=http://localhost/success (без порта = :80).
Наш FastAPI server слушает на :8001. Этот скрипт ловит все запросы на :80
и пересылает на 127.0.0.1:8001 со всеми headers, body, cookies, и возвращает
ответ обратно БЕЗ автоматического follow-redirect (важно — иначе Set-Cookie
от 302 не попадёт в браузер).

Использует низкоуровневый http.client (urllib следует за redirect'ами по
умолчанию, что нам не подходит).

Запуск:
    python scripts/oauth_proxy_80.py

На Windows для :80 admin не нужен (если IIS/Apache не занимают). На Linux/Mac
надо sudo или setcap CAP_NET_BIND_SERVICE.

Только для dev. В проде nginx/apache делают это нативно.
"""
from __future__ import annotations

import http.client
import http.server
from socketserver import ThreadingMixIn

UPSTREAM_HOST = "127.0.0.1"
UPSTREAM_PORT = 8001
LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 80

HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-length",  # пересчитаем сами
}


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802
        self._proxy()

    def do_POST(self) -> None:  # noqa: N802
        self._proxy()

    def do_PUT(self) -> None:  # noqa: N802
        self._proxy()

    def do_DELETE(self) -> None:  # noqa: N802
        self._proxy()

    def do_PATCH(self) -> None:  # noqa: N802
        self._proxy()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._proxy()

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        print(f"[oauth-proxy] {self.command} {self.path}")

    def _proxy(self) -> None:
        body_len = int(self.headers.get("content-length", 0) or 0)
        body = self.rfile.read(body_len) if body_len else None

        # Передаём все headers кроме hop-by-hop и Host
        forward_headers = {}
        for k, v in self.headers.items():
            if k.lower() in HOP_BY_HOP or k.lower() == "host":
                continue
            forward_headers[k] = v
        forward_headers["Host"] = f"{UPSTREAM_HOST}:{UPSTREAM_PORT}"
        # X-Forwarded-* — чтобы server знал реальный host браузера.
        forward_headers["X-Forwarded-Host"] = self.headers.get("host", "localhost")
        forward_headers["X-Forwarded-Proto"] = "http"

        conn = http.client.HTTPConnection(UPSTREAM_HOST, UPSTREAM_PORT, timeout=30)
        try:
            conn.request(self.command, self.path, body=body, headers=forward_headers)
            resp = conn.getresponse()
            resp_body = resp.read()

            # КРИТИЧНО: НЕ следуем за redirect, передаём 302 + Set-Cookie в браузер.
            self.send_response_only(resp.status, resp.reason)
            for k, v in resp.getheaders():
                if k.lower() in HOP_BY_HOP:
                    continue
                self.send_header(k, v)
            self.send_header("content-length", str(len(resp_body)))
            self.end_headers()
            if resp_body:
                self.wfile.write(resp_body)
        except Exception as e:  # noqa: BLE001
            try:
                self.send_error(502, f"Bad gateway: {e}")
            except Exception:  # noqa: BLE001
                pass
        finally:
            conn.close()


class ThreadingHTTPServer(ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main() -> None:
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), ProxyHandler)
    print(f"[oauth-proxy] listening on http://{LISTEN_HOST}:{LISTEN_PORT} -> http://{UPSTREAM_HOST}:{UPSTREAM_PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[oauth-proxy] stopped")


if __name__ == "__main__":
    main()
