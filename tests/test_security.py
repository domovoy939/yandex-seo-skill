"""Тесты на то, что проверка не делает лишнего на чужом сайте.

Запуск из корня репозитория:  python3 -m unittest discover tests
Поднимают локальные «вредные» серверы на 127.0.0.1 — в интернет не ходят.
"""
import http.server
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'skills' / 'yandex-seo' / 'scripts'))
os.environ['NO_PROXY'] = os.environ['no_proxy'] = '127.0.0.1,localhost'
import yandex_tech_check as ytc  # noqa: E402


def serve(handler):
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


class Security(unittest.TestCase):
    def setUp(self):
        ytc.TRUSTED.clear()
        ytc.DEADLINE[0] = time.monotonic() + 60

    def test_redirect_to_local_file_is_refused(self):
        secret = tempfile.NamedTemporaryFile('w', suffix='.html', delete=False)
        secret.write('<title>LOCAL-SECRET</title>')
        secret.close()

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_GET(self):
                self.send_response(301)
                self.send_header('Location', 'file://' + secret.name)
                self.end_headers()
        srv, port = serve(H)
        ytc.TRUSTED.add('127.0.0.1')
        st, _, _, body, _ = ytc.fetch(f'http://127.0.0.1:{port}/')
        srv.shutdown()
        os.unlink(secret.name)
        self.assertEqual(st, 0)
        self.assertNotIn('LOCAL-SECRET', body)

    def test_sitemap_on_internal_host_is_not_fetched(self):
        class Inner(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'<urlset><url><loc>http://internal/TOKEN-123</loc></url></urlset>')
        inner, iport = serve(Inner)

        class Site(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_GET(self):
                body = {'/robots.txt': f'User-agent: *\nSitemap: http://localhost:{iport}/s.xml\n',
                        '/': '<html><head><title>Тест</title></head><body>ok</body></html>'}.get(self.path)
                self.send_response(200 if body else 404)
                self.end_headers()
                if body:
                    self.wfile.write(body.encode())
        site, port = serve(Site)
        report, _ = ytc.check(f'http://127.0.0.1:{port}/')
        site.shutdown()
        inner.shutdown()
        self.assertNotIn('TOKEN-123', ' '.join(i['text'] for i in report.items))

    def test_cgnat_and_private_ranges_are_internal(self):
        for ip in ('100.100.100.100', '10.0.0.1', '192.168.1.1', '169.254.1.1', '::1', 'fc00::1'):
            with self.subTest(ip=ip):
                with self.assertRaises(OSError):
                    ytc._resolve(ip, 80)

    def test_terminal_escape_codes_are_stripped(self):
        r = ytc.Report()
        r.add('g', ytc.INFO, 'title: \x1b]0;PWNED\x07\x1b[31mRED')
        self.assertNotRegex(r.items[0]['text'], r'[\x00-\x1f\x7f-\x9f]')

    def test_hostile_page_is_parsed_fast(self):
        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_GET(self):
                body = {'/robots.txt': 'Sitemap:' + ' ' * 200_000 + 'x\n',
                        '/': '<html><body>' + '1 ' * 150_000 + 'a' * 150_000 + '</body></html>'}.get(self.path)
                self.send_response(200 if body else 404)
                self.end_headers()
                if body:
                    self.wfile.write(body.encode())
        srv, port = serve(H)
        t0 = time.monotonic()
        ytc.check(f'http://127.0.0.1:{port}/')
        srv.shutdown()
        self.assertLess(time.monotonic() - t0, 10)


if __name__ == '__main__':
    unittest.main()
