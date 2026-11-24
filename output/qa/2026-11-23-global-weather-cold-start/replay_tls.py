"""Reproduce a real 4s TLS handshake on loopback through a fresh normal Alice HTTP request."""

from contextlib import ExitStack
from datetime import UTC, datetime
import http.server
import json
from pathlib import Path
import ssl
import subprocess
import tempfile
from threading import Thread
import time
from urllib.parse import parse_qsl, urlsplit

import httpx

from desk.app import create_app
from test_global_weather import NOW, fixture_weather, login, model_data, send


class PublicReply(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        target = urlsplit(self.path)
        params = dict(parse_qsl(target.query))
        if target.path.endswith("/search"):
            data = fixture_weather("https://geocoding-api.open-meteo.com/v1/search", params)
        else:
            params["forecast_days"] = int(params["forecast_days"])
            data = model_data(params)
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class DelayedTLS(http.server.ThreadingHTTPServer):
    def process_request_thread(self, request, address):
        try:
            time.sleep(self.delay)
            secured = self.context.wrap_socket(request, server_side=True)
            super().process_request_thread(secured, address)
        except OSError:
            request.close()  # The baseline client times out during its TLS handshake.


def listener(stack, ctx, delay):
    server = DelayedTLS(("127.0.0.1", 0), PublicReply)
    server.context, server.delay = ctx, delay
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    stack.callback(server.server_close)
    stack.callback(server.shutdown)
    return server.server_port


def run():
    request_log = []
    with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
        root = Path(directory)
        key, cert = root / "key.pem", root / "ca.pem"
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-days",
                "1",
                "-subj",
                "/CN=localhost",
                "-addext",
                "subjectAltName=IP:127.0.0.1",
                "-keyout",
                str(key),
                "-out",
                str(cert),
            ],
            check=True,
            capture_output=True,
        )
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert, key)
        verify = ssl.create_default_context(cafile=str(cert))
        geocoding, forecast = listener(stack, ctx, 4.2), listener(stack, ctx, 0)

        class Transport(httpx.BaseTransport):
            def __init__(self):
                self.inner = httpx.HTTPTransport(verify=verify)

            def handle_request(self, request):
                stage = (
                    "geocoding"
                    if request.url.host == "geocoding-api.open-meteo.com"
                    else "forecast"
                )
                port = geocoding if stage == "geocoding" else forecast
                target = request.url.copy_with(host="127.0.0.1", port=port)
                scoped = httpx.Request(request.method, target, extensions=request.extensions)
                item = {"stage": stage, "connect_limit_s": request.extensions["timeout"]["connect"]}
                t0 = time.monotonic()
                try:
                    response = self.inner.handle_request(scoped)
                    item["status"] = response.status_code
                    return response
                except httpx.HTTPError as exc:
                    item["failure"] = type(exc).__name__
                    raise
                finally:
                    item["elapsed_s"] = round(time.monotonic() - t0, 2)
                    request_log.append(item)

            def close(self):
                self.inner.close()

        app = create_app(root / "desk", password="fixture", scheduler=False)
        runtime = app.state.runtime
        runtime.data.weather_provider.now = lambda: NOW
        from desk.weather import read_weather_json

        runtime.data.weather_provider.fetch = lambda url, params: read_weather_json(
            url, params, transport=Transport()
        )
        t0 = time.monotonic()
        answer, _ = send(login(app), "normal-first", "帮我查一下东京的天气")
        return {
            "captured_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "cold_geocoding_tls_delay_s": 4.2,
            "provider_data": "fixture",
            "openai_requests": 0,
            "first_request_elapsed_s": round(time.monotonic() - t0, 2),
            "first_normal_reply": answer["message"],
            "public_get_attempts": request_log,
        }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))
