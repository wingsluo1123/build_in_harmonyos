#!/usr/bin/env bash
set -euo pipefail

h2o -v 2>&1 | grep "2.2.6"
