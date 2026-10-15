#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the sqlsmith CLI executable.
#
# sqlsmith needs a live RDBMS to generate SQL, so the only runnable consumer
# checks are --version / --help, which exit 0 without a database connection.
# Each check emits exactly one "TEST PASS:" marker that the conanfile counts.
set -eu

echo "[sqlsmith test] running: sqlsmith --version"
if version_out="$(sqlsmith --version 2>&1)"; then
  if [[ "$version_out" == *"SQLsmith"* ]]; then
    echo "TEST PASS: version reports SQLsmith"
  else
    echo "TEST FAIL: sqlsmith --version did not report 'SQLsmith': $version_out"
    exit 1
  fi
else
  echo "TEST FAIL: sqlsmith --version exited non-zero"
  exit 1
fi

echo "[sqlsmith test] running: sqlsmith --help"
if help_out="$(sqlsmith --help 2>&1)"; then
  if [[ "$help_out" == *"--version"* ]]; then
    echo "TEST PASS: help lists cli options"
  else
    echo "TEST FAIL: sqlsmith --help did not list options: $help_out"
    exit 1
  fi
else
  echo "TEST FAIL: sqlsmith --help exited non-zero"
  exit 1
fi

echo "[sqlsmith] all checks passed"
