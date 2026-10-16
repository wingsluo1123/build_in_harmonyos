#!/usr/bin/env python3
"""Minimal sendmail-compatible capture used by the consumer flow."""

import os
import sys


capture = os.environ["VACATION_CAPTURE"]
with open(capture, "wb") as stream:
    stream.write(sys.stdin.buffer.read())
with open(capture + ".args", "w", encoding="utf-8") as stream:
    stream.write("\n".join(sys.argv[1:]))
