// test_package L1 test — real roundtrip through the misa77 public API.
// SPDX-License-Identifier: MIT
#include "misa77/misa77.h"

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>

int main()
{
    // Build a compressible input (repetitive + random tail).
    std::vector<uint8_t> src(1u << 16);
    for (size_t i = 0; i < src.size(); ++i)
        src[i] = static_cast<uint8_t>((i % 97) + (i < src.size() / 2 ? 0 : (i * 31) % 13));

    misa77::config cfg;
    const uint64_t bound = misa77::compress_bound(src.size(), cfg);
    std::vector<uint8_t> comp(bound);

    const uint64_t comp_n = misa77::compress(src.data(), src.size(), comp.data(), comp.size(), cfg);
    if (comp_n == 0 || comp_n > bound)
    {
        std::fprintf(stderr, "FAIL: compress returned %llu\n",
                     static_cast<unsigned long long>(comp_n));
        return 1;
    }

    const uint64_t dec_size = misa77::decompressed_size(comp.data());
    if (dec_size != src.size())
    {
        std::fprintf(stderr, "FAIL: decompressed_size=%llu expected=%zu\n",
                     static_cast<unsigned long long>(dec_size), src.size());
        return 1;
    }

    std::vector<uint8_t> out(misa77::decompressed_buffer_bound(dec_size));
    const uint64_t out_n = misa77::decompress(comp.data(), comp_n, out.data(), out.size());
    if (out_n != src.size() || std::memcmp(out.data(), src.data(), src.size()) != 0)
    {
        std::fprintf(stderr, "FAIL: decompress=%llu expected=%zu (byte mismatch)\n",
                     static_cast<unsigned long long>(out_n), src.size());
        return 1;
    }

    std::printf("test misa77 0.6.0: roundtrip OK (%zu -> %llu bytes)\n", src.size(),
                static_cast<unsigned long long>(comp_n));
    return 0;
}
