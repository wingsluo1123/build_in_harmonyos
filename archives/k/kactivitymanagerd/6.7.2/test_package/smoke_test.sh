#!/bin/sh
# Smoke test for the packaged kactivitymanagerd daemon.
#
# kactivitymanagerd is a D-Bus daemon application (no upstream test suite).
# Outcomes accepted by conanfile.py test():
#   exit 0   -> daemon started, could not register the D-Bus service on the
#               headless worker (no session bus) and exited cleanly
#   exit 124 -> daemon is up and serving (killed by the timeout guard)
set -u

daemon="$1"
timeout 60 "$daemon"
