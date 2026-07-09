#!/bin/sh
# test_marked.sh — Test script for marked 18.0.5 (ESM import + version check)
# Called by test_package/conanfile.py via self.run()

MARKED_ROOT="$1"
ESM_PATH="$MARKED_ROOT/lib/node_modules/marked/lib/marked.esm.js"
PKG_JSON="$MARKED_ROOT/lib/node_modules/marked/package.json"

failures=0

# Test 1: ESM module import — parse markdown and verify HTML
node --input-type=module -e "
import { marked } from '$ESM_PATH';
const html = marked.parse('# Hello World\n\nThis is **bold**.');
if (!html.includes('<h1>Hello World</h1>')) { console.error('FAIL: h1 not found'); process.exit(1); }
if (!html.includes('<strong>bold</strong>')) { console.error('FAIL: strong not found'); process.exit(1); }
console.log('PASS: marked ESM import test');
" || failures=$((failures + 1))

# Test 2: Version check via package.json
node -e "
const pkg = require('$PKG_JSON');
if (pkg.version !== '18.0.5') { console.error('FAIL: version is ' + pkg.version); process.exit(1); }
console.log('PASS: marked version:', pkg.version);
" || failures=$((failures + 1))

if [ $failures -gt 0 ]; then
    echo "$failures test(s) FAILED"
    exit 1
fi
echo "All marked tests passed."
exit 0
