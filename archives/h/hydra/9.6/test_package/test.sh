#!/bin/sh
set -eu

hydra -h 2>&1 | grep -q "Hydra v9.6"
pw-inspector -h 2>&1 | grep -q "PW-Inspector"
