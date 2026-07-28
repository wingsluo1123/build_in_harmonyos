#!/usr/bin/env python3
"""Test source for perl-net-xmpp L1 test.

This file serves as the test source file required by CI L0c gate.
The actual test logic is in conanfile.py's test() method, which invokes
perl to load Net::XMPP and verify its version.
"""
