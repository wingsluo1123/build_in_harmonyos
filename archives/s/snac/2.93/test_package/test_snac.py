#!/usr/bin/env python3
"""Exercise the packaged snac binary from a consumer's point of view.

Usage: test_snac.py <path-to-snac>

snac is a single-binary ActivityPub server; a real instance needs a data
directory and a listening socket, which the build sandbox does not provide.
This script therefore verifies that the packaged binary runs and that
``snac init <basedir>`` can initialise a local data storage purely on the
filesystem (no network, no daemon).

``snac init`` asks five questions on stdin (address, port, host name, URL
prefix, admin email); answers come from a generated file.  Empty answers keep
the built-in defaults.  Success is asserted by checking the created layout
(server.json / user / object / queue directories).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile


def main():
    bin_path = sys.argv[1]
    assert os.path.isfile(bin_path), bin_path
    assert os.access(bin_path, os.X_OK), "snac is not executable"

    # snac insists the basedir does NOT exist yet, so pass a child path under
    # a freshly created parent.
    parent = tempfile.mkdtemp(prefix="snac-test-")
    data_dir = os.path.join(parent, "data")
    answers = os.path.join(parent, "answers.txt")
    # address / port keep defaults (empty lines), host name is required.
    with open(answers, "w") as fh:
        fh.write("\n\nlocalhost\n\n\n")
    try:
        with open(answers) as stdin_fh:
            result = subprocess.run(
                [bin_path, "init", data_dir],
                stdin=stdin_fh, capture_output=True, text=True, timeout=300)
        blob = (result.stdout or "") + (result.stderr or "")
        assert result.returncode == 0, "snac init failed: %s" % blob

        # The storage layout must actually exist on disk.
        for sub in ("user", "object", "queue"):
            assert os.path.isdir(os.path.join(data_dir, sub)), sub
        srv_json = os.path.join(data_dir, "server.json")
        assert os.path.isfile(srv_json), "server.json missing"
        with open(srv_json) as fh:
            cfg = json.load(fh)
        assert cfg.get("host") == "localhost", cfg
        print("SNAC-CONSUMER-OK")
    finally:
        shutil.rmtree(parent, ignore_errors=True)


main()
