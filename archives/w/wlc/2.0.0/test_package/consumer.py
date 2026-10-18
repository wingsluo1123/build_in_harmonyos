"""One installed-package consumer with a local three-page HTTP service."""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlsplit, urlunsplit

import wlc
from wlc import Translation, Weblate


def main():
    prefix = Path(sys.argv[1]).resolve()
    fixtures = Path(sys.argv[2]).resolve()
    imported = Path(wlc.__file__).resolve()
    assert imported.is_relative_to(prefix), (imported, prefix)
    expected = [{"page": ["1"], "q": ["hello"]}, {"page": ["2"]}, {"page": ["3"]}]
    queries = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = parse_qs(urlsplit(self.path).query)
            if len(queries) >= 3 or query != expected[len(queries)]:
                self.send_error(400, "unexpected pagination query")
                return
            queries.append(query)
            filename = "translations"
            if len(queries) > 1:
                filename += f"--GET--page={len(queries)}"
            page = json.loads((fixtures / filename).read_bytes())
            if page['next']:
                next_url = urlsplit(page['next'])
                page['next'] = urlunsplit(('http', f'127.0.0.1:{self.server.server_port}', next_url.path, next_url.query, ''))
            body = json.dumps(page).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    with HTTPServer(('127.0.0.1', 0), Handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        client = None
        try:
            client = Weblate(url=f'http://127.0.0.1:{server.server_port}/api/', timeout=5)
            client.session.trust_env = False
            params = {'page': 1, 'q': 'hello'}
            rows = list(client.list_factory('translations/', Translation, params))
            assert queries == expected, queries
            assert len(rows) == 50, len(rows)
            assert len({row.url for row in rows}) == 50
            assert params == {'page': 1, 'q': 'hello'}
            print(json.dumps({'consumer_programs':1, 'requests':len(queries), 'queries':queries, 'results':len(rows), 'unique_results':50, 'installed_module':str(imported), 'status':'PASS'}))
        finally:
            server.shutdown()
            thread.join(timeout=5)
            if client is not None:
                client.session.close()


if __name__ == '__main__':
    main()
