// test_package consumer test — mm_file 1.0.0
// Exercises the real mm_file API (file_sink write / file_source read /
// advice / iterator) and verifies round-trip data integrity. Uses a temp
// file under the current working directory so it runs in the OHOS/Linux
// sandbox.
//
// NOTE: reads back with the SAME element type (uint32_t) that was written,
// so round-trip identity is checked directly (uint16 re-read of uint32
// data is byte-interleaved, which the upstream test intentionally prints).
#include <cstdint>
#include <cstdio>
#include <string>

#include <mm_file/mm_file.hpp>

int main() {
    std::string filename("./mm_file_tmp.bin");
    static const size_t n = 16;

    // write n uint32_t integers
    {
        mm::file_sink<uint32_t> fout(filename, n);
        if (!fout.is_open()) {
            std::fprintf(stderr, "FAIL: file_sink did not open\n");
            return 1;
        }
        auto* data = fout.data();
        for (uint32_t i = 0; i != fout.size(); ++i) {
            data[i] = i;  // deterministic pattern
        }
        fout.close();
    }

    // read back as uint32_t and verify identity
    {
        int advice = mm::advice::sequential;
        mm::file_source<uint32_t> fin(filename, advice);
        if (!fin.is_open()) {
            std::fprintf(stderr, "FAIL: file_source did not open\n");
            return 1;
        }
        auto const* data = fin.data();
        if (fin.size() != n) {
            std::fprintf(stderr, "FAIL: unexpected element count\n");
            return 1;
        }
        for (uint32_t i = 0; i != fin.size(); ++i) {
            if (data[i] != i) {
                std::fprintf(stderr, "FAIL: data mismatch at %u\n", i);
                return 1;
            }
        }
        fin.close();
    }

    // iterator round-trip
    {
        mm::file_source<uint32_t> fin;
        fin.open(filename, mm::advice::random);
        size_t count = 0;
        for (auto x : fin) {
            if (x != count) {
                std::fprintf(stderr, "FAIL: iterator mismatch at %zu\n", count);
                return 1;
            }
            ++count;
        }
        fin.close();
        if (count != n) {
            std::fprintf(stderr, "FAIL: iterator count mismatch\n");
            return 1;
        }
    }

    std::remove(filename.c_str());
    std::printf("mm_file test OK: %zu elements round-tripped\n", n);
    return 0;
}
