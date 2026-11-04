import json
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from clients.check_connection import check_connection, OPERATIONS


class PreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                self.server.requests.append((self.path, dict(self.headers)))
                status = 200
                payload = {"ok": True}
                if self.path.endswith("openapi.json"):
                    payload = {"paths": {path: {"post": {}} for path in OPERATIONS}}
                    if self.server.mode == "missing":
                        payload["paths"].pop(OPERATIONS[0])
                if self.path.endswith("usage"):
                    status = 401
                    payload = {"error": {"code": "INVALID_API_KEY"}}
                if self.server.mode == "html":
                    status = 503
                if self.server.mode == "redirect":
                    status = 302
                self.send_response(status)
                if status == 302:
                    self.send_header("Location", "/redirect-target")
                self.end_headers()
                self.wfile.write(b'<html>private upstream content</html>' if status == 503 else json.dumps(payload).encode())
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.origin = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.server.mode = "ok"
        self.server.requests = []

    def test_ready_without_auth_or_products(self):
        result = check_connection(self.origin)
        self.assertTrue(result["ready_for_key_request"])
        self.assertEqual(len(self.server.requests), 3)
        for _, headers in self.server.requests:
            self.assertNotIn("X-Api-Key", headers)
            self.assertNotIn("Authorization", headers)

    def test_missing_operation_not_ready(self):
        self.server.mode = "missing"
        self.assertFalse(check_connection(self.origin)["ready_for_key_request"])

    def test_non_json_error_is_redacted(self):
        self.server.mode = "html"
        result = check_connection(self.origin)
        self.assertFalse(result["ready_for_key_request"])
        self.assertNotIn("private upstream", json.dumps(result))

    def test_redirect_not_followed(self):
        self.server.mode = "redirect"
        self.assertFalse(check_connection(self.origin)["ready_for_key_request"])
        self.assertNotIn("/redirect-target", [path for path, _ in self.server.requests])

    def test_unsafe_origins_rejected(self):
        for origin in ("http://example.com", "https://user:secret@example.com", "https://example.com?key=secret", "https://example.com/path"):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                check_connection(origin)

    def test_javascript_same_modes_and_anonymous_requests(self):
        root = Path(__file__).resolve().parents[1]
        for mode, expected in (("ok", True), ("missing", False), ("html", False), ("redirect", False)):
            with self.subTest(mode=mode):
                self.server.mode = mode
                self.server.requests = []
                result = subprocess.run(["node", "clients/check-connection.mjs", "--origin", self.origin],
                    cwd=root, text=True, capture_output=True, timeout=20)
                data = json.loads(result.stdout)
                self.assertEqual(data["ready_for_key_request"], expected)
                self.assertEqual(result.returncode, 0 if expected else 1)
                self.assertEqual(len(self.server.requests), 3)
                self.assertNotIn("private upstream", result.stdout)
                self.assertNotIn("/redirect-target", [path for path, _ in self.server.requests])
                for _, headers in self.server.requests:
                    self.assertFalse(any(key.lower() in {"authorization", "x-api-key"} for key in headers))

    def test_javascript_rejects_credential_url_without_echo(self):
        result = subprocess.run(["node", "clients/check-connection.mjs", "--origin", "https://user:secret@example.com"],
            cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("secret", result.stdout + result.stderr)
