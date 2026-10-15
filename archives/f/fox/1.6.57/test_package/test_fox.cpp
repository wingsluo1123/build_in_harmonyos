// Consumer-side smoke test for the FOX toolkit (OHOS aarch64).
//
// It exercises the display-free part of the public API that every downstream
// FOX application links against, so a broken header/ABI/installation layout
// fails here instead of inside the application that depends on the package.

#include <fx.h>

#include <cstdio>

static int failures = 0;

static void check(bool ok, const char* what) {
  std::printf("%s: %s\n", ok ? "PASS" : "FAIL", what);
  if (!ok) {
    failures++;
  }
}

int main() {
  // fxversion is the toolkit's build-time version record (fxdefs.h).  The
  // consumer contract is that it matches the packaged release.
  check(fxversion[0] == 1 && fxversion[1] == 6 && fxversion[2] == 57,
        "fxversion reports 1.6.57");

  // FXString is the toolkit's string class; this walks construction, grow,
  // index access and comparison without needing an X display.
  FXString text("fox");
  text.append("-toolkit");
  check(text.length() == 11, "FXString::append() grows the string");
  check(text[0] == 'f' && text[3] == '-', "FXString::operator[] reads a byte");
  check(text == "fox-toolkit", "FXString compares equal to its content");

  FXString suffix(".so");
  text.append(suffix);
  check(text.length() == 14, "FXString copies from another FXString");
  check(text != "fox-toolkit", "appended FXString content is visible");

  // A second, independent instance must not share storage with the first.
  FXString other("fox");
  other.append("GUI");
  check(other == "foxGUI" && text != other,
        "distinct FXString instances stay independent");

  if (failures != 0) {
    std::printf("FAILED: %d check(s)\n", failures);
    return 1;
  }
  std::printf("All FOX consumer checks passed\n");
  return 0;
}
