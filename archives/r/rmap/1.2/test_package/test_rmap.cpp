// HarmonyOS-specific consumer test for the rmap package.
// The upstream project ships no test suite, so this test_package performs the
// HarmonyOS-side verification required by R34/R51 by consuming the packaged
// binary end-to-end:
//   1. run the packaged `rmap` executable with real options to render a
//      whole-earth GIF image;
//   2. verify the output file exists and is a valid GIF (signature + screen
//      descriptor);
//   3. verify non-trivial image dimensions and non-empty payload;
//   4. verify exit status and repeated runs are deterministic (same sha256).
// This exercises the real consumer path (spawn packaged CLI -> libgd imaging
// pipeline -> file output), not just assertions on constants.
// Note: the packaged libgd build has no PNG support (no gdImagePng symbol),
// so the build uses the upstream GD_GIF branch in rmap.c -> GIF output.
#include <cstdio>
#include <cstdlib>
#include <cstring>

int main() {
    const char *rmap_bin = getenv("RMAP_BIN");
    if (!rmap_bin || !*rmap_bin) {
        std::fprintf(stderr, "FAIL: RMAP_BIN not set\n");
        return 1;
    }

    const char *out1 = "rmap-earth-1.gif";
    const char *out2 = "rmap-earth-2.gif";
    const char *resdir = getenv("RMAP_RESDIR");
    if (!resdir || !*resdir) {
        std::fprintf(stderr, "FAIL: RMAP_RESDIR not set\n");
        return 1;
    }

    // 1. real consumer run: render a 320x160 whole-earth image
    char cmd[768];
    std::snprintf(cmd, sizeof(cmd),
                  "\"%s\" --zoom=1 --width=320 --height=160 "
                  "--datafile=\"%s/earth.rez\" --colorfile=\"%s/rmap.colors\" "
                  "--outfile=\"%s\"",
                  rmap_bin, resdir, resdir, out1);
    int rc = std::system(cmd);
    if (rc != 0) {
        std::fprintf(stderr, "FAIL: rmap render exited %d\n", rc);
        return 1;
    }

    // 2. output must be a valid GIF (signature "GIF8"), the format the
    //    packaged libgd build supports (GD_GIF path in upstream rmap.c)
    FILE *f = std::fopen(out1, "rb");
    if (!f) {
        std::fprintf(stderr, "FAIL: output %s not created\n", out1);
        return 1;
    }
    unsigned char sig[6];
    if (std::fread(sig, 1, 6, f) != 6 ||
        std::memcmp(sig, "GIF8", 4) != 0) {
        std::fprintf(stderr, "FAIL: output is not a GIF file\n");
        std::fclose(f);
        return 1;
    }
    // GIF logical screen descriptor: width(2 LE) + height(2 LE)
    unsigned char lsd[4];
    if (std::fread(lsd, 1, 4, f) != 4) {
        std::fprintf(stderr, "FAIL: GIF screen descriptor missing\n");
        std::fclose(f);
        return 1;
    }
    unsigned long w = lsd[0] | (lsd[1] << 8);
    unsigned long h = lsd[2] | (lsd[3] << 8);
    std::fseek(f, 0, SEEK_END);
    long size = std::ftell(f);
    std::fclose(f);
    std::printf("INFO: rendered GIF %lux%lu, %ld bytes\n", w, h, size);

    // 3. non-trivial image: requested dimensions honored, payload substantial
    if (w != 320 || h != 160) {
        std::fprintf(stderr, "FAIL: unexpected dimensions %lux%lu\n", w, h);
        return 1;
    }
    if (size < 1024) {
        std::fprintf(stderr, "FAIL: GIF suspiciously small (%ld bytes)\n", size);
        return 1;
    }

    // 4. determinism: identical second render must produce identical bytes
    std::snprintf(cmd, sizeof(cmd),
                  "\"%s\" --zoom=1 --width=320 --height=160 "
                  "--datafile=\"%s/earth.rez\" --colorfile=\"%s/rmap.colors\" "
                  "--outfile=\"%s\"",
                  rmap_bin, resdir, resdir, out2);
    if (std::system(cmd) != 0) {
        std::fprintf(stderr, "FAIL: second render failed\n");
        return 1;
    }
    f = std::fopen(out2, "rb");
    if (!f) {
        std::fprintf(stderr, "FAIL: second output missing\n");
        return 1;
    }
    unsigned char a[4096], b[4096];
    size_t na, nb;
    int identical = 1;
    FILE *f1 = std::fopen(out1, "rb");
    if (!f1) {
        std::fprintf(stderr, "FAIL: cannot reopen %s\n", out1);
        std::fclose(f);
        return 1;
    }
    while ((na = std::fread(a, 1, sizeof(a), f1)) > 0 &&
           (nb = std::fread(b, 1, sizeof(b), f)) > 0) {
        if (na != nb || std::memcmp(a, b, na) != 0) {
            identical = 0;
            break;
        }
    }
    // tail check: any length difference (one file exhausted before the other)
    if (identical &&
        ((na > 0 && nb == 0) || (na == 0 && (nb = std::fread(b, 1, sizeof(b), f)) > 0)))
        identical = 0;
    std::fclose(f1);
    std::fclose(f);
    if (!identical) {
        std::fprintf(stderr, "FAIL: renders are not deterministic\n");
        return 1;
    }

    std::printf("PASS: rmap consumer test (render/GIF/geometry/determinism)\n");
    return 0;
}
