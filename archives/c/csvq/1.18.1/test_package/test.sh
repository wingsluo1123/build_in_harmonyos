#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for csvq executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] csvq --version"
csvq --version && echo "[ok] --version OK" || {
    echo "[test] --version failed, trying --help..."
    csvq --help > /dev/null 2>&1 && echo "[ok] --help OK" || {
        echo "[fail] csvq failed both --version and --help"
        exit 1
    }
}

# Create test CSV file
TESTDIR="$(mktemp -d)"
cat > "$TESTDIR/people.csv" << 'EOF'
name,age,city
Alice,30,New York
Bob,25,London
Charlie,35,Tokyo
Diana,28,Paris
EOF

echo "[test] SELECT * FROM people"
csvq -r "$TESTDIR" "SELECT * FROM people" | grep -q "Alice" || {
    echo "[fail] SELECT * did not return expected results"
    exit 1
}
echo "[ok] SELECT * OK"

echo "[test] SELECT WHERE age > 28"
csvq -r "$TESTDIR" "SELECT * FROM people WHERE age > 28" | grep -q "Alice" || {
    echo "[fail] WHERE clause did not return expected results"
    exit 1
}
echo "[ok] WHERE clause OK"

echo "[test] SELECT COUNT(*) and AVG(age)"
csvq -r "$TESTDIR" "SELECT COUNT(*), AVG(age) FROM people" | grep -q "4" || {
    echo "[fail] COUNT/AVG did not return expected results"
    exit 1
}
echo "[ok] COUNT/AVG OK"

rm -rf "$TESTDIR"
echo "[ok] All csvq tests passed"
