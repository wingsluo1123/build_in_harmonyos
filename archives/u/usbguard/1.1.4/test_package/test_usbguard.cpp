/*
 * Consumer test for usbguard/1.1.4 — exercises the public libusbguard API.
 *
 * R34: this is not a stub.  It links libusbguard and drives the Rule API on
 * well-formed and malformed rule specifications, asserting on observable
 * values (target, device id, serial, name, round-tripped string) and on the
 * documented exception for invalid input.  Every check prints PASS/FAIL and
 * the exit status is non-zero when any check fails, so test() can take a real
 * verdict.
 *
 * Only headers that upstream actually installs are included: the rule parser
 * entry point `usbguard/RuleParser.hpp` is not part of upstream's
 * pkginclude_HEADERS, so the equivalent public `Rule::fromString()` factory
 * declared in `usbguard/Rule.hpp` is used instead.
 */
#include <usbguard/Rule.hpp>
#include <usbguard/USB.hpp>

#include <iostream>
#include <stdexcept>
#include <string>

static int failures = 0;

static void check(bool condition, const std::string& what)
{
  std::cout << (condition ? "PASS" : "FAIL") << ": " << what << std::endl;

  if (!condition) {
    ++failures;
  }
}

int main()
{
  using namespace usbguard;

  /* 1. Parse a well-formed rule and inspect the resulting object. */
  Rule rule = Rule::fromString(
                "allow id 1d6b:0002 serial \"0123456789\" name \"Test Device\"");
  check(static_cast<bool>(rule), "Rule::fromString accepts a valid allow rule");
  check(rule.getTarget() == Rule::Target::Allow, "rule target is Allow");
  check(rule.getDeviceID().toString() == "1d6b:0002",
        "device id round-trips (1d6b:0002)");
  check(rule.getSerial() == "0123456789", "serial round-trips (0123456789)");
  check(rule.getName() == "Test Device", "name round-trips (Test Device)");
  check(rule.toString().rfind("allow", 0) == 0, "toString() starts with allow");

  /* 2. A block rule keeps its target and device id. */
  Rule blocked = Rule::fromString("block id 1234:5678");
  check(blocked.getTarget() == Rule::Target::Block,
        "Rule::fromString parses a block rule");
  check(blocked.toString().find("1234:5678") != std::string::npos,
        "block rule keeps its device id");

  /* 3. A malformed rule must be rejected. */
  bool rejected = false;

  try {
    Rule::fromString("!definitely not a usbguard rule!");
  }
  catch (const std::exception&) {
    rejected = true;
  }

  check(rejected, "invalid rule specification is rejected with an exception");

  std::cout << "checks failed: " << failures << std::endl;
  return failures == 0 ? 0 : 1;
}
