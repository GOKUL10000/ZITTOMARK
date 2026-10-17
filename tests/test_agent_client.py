import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from studio_client import StudioClient


class FakeStudio(BaseHTTPRequestHandler):
    token = 'first-token'
    writes = 0
    def log_message(self, *args): pass
    def do_GET(self):
        if self.path == '/':
            self.send_response(200); self.end_headers()
            self.wfile.write(f'<meta name="studio-token" content="{self.token}">'.encode())
        elif self.path == '/api/redirect':
            self.send_response(302); self.send_header('Location', 'http://example.com/'); self.end_headers()
        else:
            self.send_response(200); self.end_headers(); self.wfile.write(b'{"status":"done"}')
    def do_POST(self):
        self.rfile.read(int(self.headers['Content-Length']))
        valid = self.headers.get('X-Studio-Token') == self.token
        if valid: type(self).writes += 1
        self.send_response(200 if valid else 403); self.end_headers()
        self.wfile.write(json.dumps({'ok': True} if valid else {'error': 'Reload the studio page to continue'}).encode())


class AgentClientTests(unittest.TestCase):
    def test_nonlocal_urls_and_ambiguous_routes_are_rejected(self):
        for url in ('https://127.0.0.1:7865', 'http://example.com:7865', 'http://localhost:7865',
                    'http://user:pass@127.0.0.1:7865', 'http://127.0.0.1:7865/path',
                    'http://127.0.0.1:7865?token=x', 'http://127.0.0.1:80', 'http://127.0.0.1'):
            with self.subTest(url=url), self.assertRaises(ValueError): StudioClient(url)
        client = StudioClient()
        for route in ('https://example.com', '//example.com', '/api/../secret', '/api/a?x=1'):
            with self.assertRaises(ValueError): client.request(route)
        with self.assertRaises(ValueError): client.job('../secret')

    def test_token_refresh_does_not_duplicate_a_successful_write_and_redirect_is_blocked(self):
        FakeStudio.token, FakeStudio.writes = 'first-token', 0
        server = ThreadingHTTPServer(('127.0.0.1', 0), FakeStudio)
        worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        try:
            client = StudioClient(f'http://127.0.0.1:{server.server_port}')
            self.assertTrue(client.request('/api/storage', {'directory':'test'})['ok'])
            FakeStudio.token = 'second-token'
            self.assertTrue(client.request('/api/storage', {'directory':'test'})['ok'])
            self.assertEqual(FakeStudio.writes, 2)
            with self.assertRaises(ValueError): client.request('/api/redirect')
        finally:
            server.shutdown(); server.server_close(); worker.join()


if __name__ == '__main__': unittest.main()
