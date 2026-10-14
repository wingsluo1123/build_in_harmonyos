-- Minimal snort3 configuration for the OHOS consumer E2E tests.
-- Intentionally self-contained (no includes): rules are passed inline
-- through the command line (--rule) by run_e2e.sh.

alert_fast = { file = false, packet = false, limit = 10 }

ips = { }
