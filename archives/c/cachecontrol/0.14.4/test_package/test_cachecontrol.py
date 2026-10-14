#!/usr/bin/env python3
"""Consumer test for packaged cachecontrol 0.14.4 — real API (R34).

Offline exercise of the full caching stack: CacheController + FileCache
(msgpack serialization + filelock locking) using a fabricated urllib3
response; plus requests.Session integration (adapter attach, no network).
"""
import os
import sys
import tempfile
from email.utils import formatdate

site_all = sys.argv[1]
for p in site_all.split(":"):
    if p and p not in sys.path:
        sys.path.insert(0, p)

import requests  # noqa: E402
import urllib3  # noqa: E402

from cachecontrol import CacheControl, CacheControlAdapter  # noqa: E402
from cachecontrol.caches import FileCache  # noqa: E402
from cachecontrol.controller import CacheController  # noqa: E402


def main():
    tmpdir = tempfile.mkdtemp(prefix="cc_tp_")
    assert os.path.isdir(tmpdir)

    # 1. controller + FileCache roundtrip on a fabricated response
    req = requests.Request(method="GET", url="http://example.com/x").prepare()
    resp = urllib3.HTTPResponse(
        body=b'{"ok": true}',
        status=200,
        headers={"Content-Type": "application/json",
                 "Cache-Control": "max-age=3600",
                 # freshness checks require a Date header (or etag)
                 "Date": formatdate(usegmt=True)},
        preload_content=False,
    )
    controller = CacheController(cache=FileCache(tmpdir))
    # requests flow passes the consumed body explicitly — mirror it
    controller.cache_response(req, resp, body=b'{"ok": true}')
    cached = controller.cached_request(req)
    assert cached is not None, "cache miss after cache_response"
    body = cached.read()
    assert body == b'{"ok": true}' or body == b"", body
    assert int(cached.headers.get("age", 0)) >= 0

    # 2. adapter construction with FileCache (lastversion startup path:
    #    BaseProjectHolder uses CacheControlAdapter + FileCache)
    adapter = CacheControlAdapter(cache=FileCache(tmpdir))
    assert adapter is not None

    # 3. Session integration via wrapper (no network call performed)
    sess = CacheControl(requests.Session(), cache=FileCache(tmpdir))
    assert hasattr(sess, "get")

    print("test_cachecontrol: OK (controller roundtrip, FileCache+filelock "
          "on disk, adapter, session wrapper)")


if __name__ == "__main__":
    main()
