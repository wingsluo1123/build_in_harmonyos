#!/usr/bin/env python3
"""Consumer-side verification for yte 1.5.4 (real API, no stub).

Imports the packaged yte module from site-packages and actually processes
templated YAML documents through yte.process_yaml.
"""
import os
import sys

site = sys.argv[1] if len(sys.argv) > 1 else ""
if site and os.path.isdir(site):
    sys.path.insert(0, site)

import yte  # noqa: E402

# 1. Real template expansion: ?for loop with ?f-string keys (upstream
#    test_for syntax, verified against yte 1.5.4)
out = yte.process_yaml(
    '?for i in range(3):\n'
    '    ?f"key{i}": 1\n',
)
assert out == {"key0": 1, "key1": 1, "key2": 1}, out

# 2. Plain YAML passthrough (use_yte absent -> untouched)
plain = yte.process_yaml("key: value\n")
assert isinstance(plain, dict) and plain.get("key") == "value", plain

print("yte process_yaml consumer assertions passed")
