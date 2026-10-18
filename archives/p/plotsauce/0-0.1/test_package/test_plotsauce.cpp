// L1 consumer test for plotsauce/0-0.1 (R34: exercises the packaged binary).
//
// Steps driven by test_package/conanfile.py:
//   1. test_sample3d writes a deterministic, valid Survex .3d v8 input file.
//   2. The packaged `plotsauce` binary converts it to (gzip-compressed) XML.
//   3. This validator gunzips the output and asserts the expected document
//      structure produced by psXMLWriter for the known input contents.
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include <zlib.h>

static int expect(bool cond, const char *what) {
    printf("[%s] %s\n", cond ? "PASS" : "FAIL", what);
    return cond ? 0 : 1;
}

static bool read_gzip(const char *path, std::string &out) {
    gzFile g = gzopen(path, "rb");
    if (!g) return false;
    char buf[4096];
    int n;
    while ((n = gzread(g, buf, sizeof(buf))) > 0) out.append(buf, (size_t)n);
    gzclose(g);
    return n == 0;
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <converted.xml.gz>\n", argv[0]);
        return 2;
    }
    std::string xml;
    if (!read_gzip(argv[1], xml)) {
        printf("[FAIL] cannot gunzip converted output\n");
        return 1;
    }
    int fails = 0;
    fails += expect(!xml.empty(), "XML output is not empty");
    fails += expect(xml.find("<PlotSauceDocument") != std::string::npos,
                    "root element <PlotSauceDocument> present");
    fails += expect(xml.find("<Stations") != std::string::npos,
                    "stations section present");
    fails += expect(xml.find("<Station>") != std::string::npos,
                    "station element present");
    fails += expect(xml.find("entrance") != std::string::npos,
                    "label \"entrance\" present in output");
    fails += expect(xml.find("<Lines") != std::string::npos,
                    "lines section present");
    printf("%s: %d failures\n", fails == 0 ? "OK" : "FAILED", fails);
    return fails == 0 ? 0 : 1;
}
