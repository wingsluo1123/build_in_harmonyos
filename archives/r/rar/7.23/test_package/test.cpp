// libunrar consumer test for rar 7.23.
// Driven by test_rar.py: argv[1] = path to plain fixture .rar,
// argv[2] = expected hello.txt size (bytes).
#define _UNIX
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "dll.hpp"

static int g_fail = 0;
#define CHECK(name, cond) do { \
    if (cond) { printf("[ok] %s\n", name); } \
    else { printf("[fail] %s\n", name); g_fail++; } \
} while (0)

int main(int argc, char **argv) {
    if (argc < 3) {
        printf("usage: test_rar <plain.rar> <hello_size>\n");
        return 2;
    }
    const char *fixture = argv[1];
    long hello_size = atol(argv[2]);

    // A1: DLL ABI version matches the header it was compiled against.
    int version = RARGetDllVersion();
    CHECK("A1 RARGetDllVersion matches RAR_DLL_VERSION",
          version == RAR_DLL_VERSION);

    // A2: opening a nonexistent archive fails gracefully.
    struct RAROpenArchiveDataEx open_bad;
    memset(&open_bad, 0, sizeof(open_bad));
    open_bad.ArcName = (char *)"definitely_missing_archive.rar";
    open_bad.OpenMode = RAR_OM_EXTRACT;
    HANDLE hbad = RAROpenArchiveEx(&open_bad);
    CHECK("A2 nonexistent archive returns NULL with error OpenResult",
          hbad == NULL && open_bad.OpenResult != ERAR_SUCCESS);
    if (hbad) RARCloseArchive(hbad);

    // A3/A4: open the real fixture, locate hello.txt, test-extract it.
    struct RAROpenArchiveDataEx open_data;
    memset(&open_data, 0, sizeof(open_data));
    open_data.ArcName = (char *)fixture;
    open_data.OpenMode = RAR_OM_EXTRACT;
    HANDLE h = RAROpenArchiveEx(&open_data);
    if (!h) {
        printf("[fail] A3/A4 fixture open failed (OpenResult=%d)\n",
               open_data.OpenResult);
        return 1;
    }

    int found = 0, listed = 0, tested = 0;
    long found_size = -1;
    struct RARHeaderDataEx header;
    while (1) {
        // RARReadHeaderEx dereferences optional *Ex pointers when non-NULL,
        // so the header struct must be zeroed before every call.
        memset(&header, 0, sizeof(header));
        if (RARReadHeaderEx(h, &header) != ERAR_SUCCESS)
            break;
        listed++;
        if (strcmp(header.FileName, "hello.txt") == 0) {
            found = 1;
            found_size = (long)header.UnpSize;
            // A4: RAR_TEST verifies stored CRC/BLAKE2 during decompression.
            tested = (RARProcessFile(h, RAR_TEST, NULL, NULL) == ERAR_SUCCESS);
        } else {
            RARProcessFile(h, RAR_SKIP, NULL, NULL);
        }
    }
    RARCloseArchive(h);

    CHECK("A3 fixture lists hello.txt with expected unpacked size",
          found && listed >= 2 && found_size == hello_size);
    CHECK("A4 libunrar test-extract of hello.txt passes integrity check",
          tested == 1);

    printf("SUMMARY libconsumer: %s\n", g_fail == 0 ? "PASS" : "FAIL");
    return g_fail ? 1 : 0;
}
