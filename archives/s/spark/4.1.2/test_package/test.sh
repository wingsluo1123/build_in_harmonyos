#!/usr/bin/env bash
# test_package/test.sh — real Spark smoke test for packaged spark-submit.
set -eu

SPARK_SUBMIT="$1"
EXAMPLES_JAR="$2"

if ! command -v java >/dev/null 2>&1; then
  if [ -x "$HOME/bishengjdk17/bin/java" ]; then
    export JAVA_HOME="$HOME/bishengjdk17"
    export PATH="$JAVA_HOME/bin:$PATH"
  elif [ -x "$HOME/usr/local/bishengjdk17/bin/java" ]; then
    export JAVA_HOME="$HOME/usr/local/bishengjdk17"
    export PATH="$JAVA_HOME/bin:$PATH"
  else
    echo "[fail] Java 17+ not found; Spark requires bishengjdk/openjdk"
    exit 1
  fi
fi

export SPARK_USER="${SPARK_USER:-currentUser}"
export HADOOP_USER_NAME="${HADOOP_USER_NAME:-$SPARK_USER}"
export SPARK_LOCAL_IP="${SPARK_LOCAL_IP:-127.0.0.1}"
export HOME="${HOME:-/storage/Users/currentUser}"
export SPARK_SUBMIT_OPTS="-Dos.name=Linux -Duser.home=$HOME -Duser.name=$SPARK_USER ${SPARK_SUBMIT_OPTS:-}"

VERSION_LOG="spark-version.log"
PI_LOG="spark-pi.log"

echo "[test] spark-submit --version"
"$SPARK_SUBMIT" --version >"$VERSION_LOG" 2>&1
if ! grep -q "version 4.1.2" "$VERSION_LOG"; then
  cat "$VERSION_LOG"
  echo "[fail] spark-submit --version did not report version 4.1.2"
  exit 1
fi

echo "[test] SparkPi local[1]"
"$SPARK_SUBMIT" --class org.apache.spark.examples.SparkPi --master local[1] "$EXAMPLES_JAR" 2 >"$PI_LOG" 2>&1
if ! grep -q "Pi is roughly" "$PI_LOG"; then
  tail -80 "$PI_LOG"
  echo "[fail] SparkPi output missing expected result"
  exit 1
fi

grep "Pi is roughly" "$PI_LOG"
echo "[pass] Spark 4.1.2 spark-submit and SparkPi smoke tests passed"
