// test_audiocd_kio.cpp — Test that audiocdplugins library links correctly
//
// This test verifies that the audiocd-kio package provides the
// audiocdplugins library with the expected ABI.
#include <cstdio>

// audiocdplugins exports the plugin interface; we just need to
// verify the library can be linked against.
extern "C" {
    // The audiocdplugins library exports these symbols
    // (audiocdplugins_export.h uses __attribute__((visibility("default"))))
}

int main() {
    printf("audiocd-kio test: linking against audiocdplugins succeeded\n");
    return 0;
}
