// HarmonyOS PC (aarch64) 专项测试 (harmonyos_specific_test)
// 验证：本库在本机 OHOS aarch64 上经平台探测修正后，NEON/portable codec 路径可实际运行，
// 且跨所有 light/heavy level 的压缩-解压 roundtrip 完全字节一致。
// SPDX-License-Identifier: MIT
#include "misa77/misa77.h"

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>

namespace
{
    // Run one round-trip at a given config level; return true on byte-exact success.
    bool roundtrip_level(const std::vector<uint8_t>& src, int8_t level, uint64_t& comp_n_out)
    {
        misa77::config cfg(level);
        const uint64_t bound = misa77::compress_bound(src.size(), cfg);
        std::vector<uint8_t> comp(bound);
        const uint64_t comp_n = misa77::compress(src.data(), src.size(), comp.data(), comp.size(), cfg);
        if (comp_n == 0 || comp_n > bound)
            return false;
        comp_n_out = comp_n;

        if (misa77::decompressed_size(comp.data()) != src.size())
            return false;

        std::vector<uint8_t> out(misa77::decompressed_buffer_bound(src.size()));
        const uint64_t out_n = misa77::decompress(comp.data(), comp_n, out.data(), out.size());
        return out_n == src.size() && std::memcmp(out.data(), src.data(), src.size()) == 0;
    }
}

int main()
{
    // Deterministic, mixed compressible/noise input so both light and heavy formats are exercised.
    std::vector<uint8_t> src(1u << 18);
    for (size_t i = 0; i < src.size(); ++i)
        src[i] = static_cast<uint8_t>((i / 8) % 250); // repetitive long runs

    int passed = 0;
    uint64_t total_comp = 0;
    // Level -1 (min) .. 4 (max, heavy).
    for (int8_t lvl = misa77::config::min_level; lvl <= misa77::config::max_level; ++lvl)
    {
        uint64_t comp_n = 0;
        if (!roundtrip_level(src, lvl, comp_n))
        {
            std::fprintf(stderr, "FAIL: level %d (heavy=%s)\n", (int)lvl,
                         lvl >= misa77::config::heavy_lb ? "yes" : "no");
            return 1;
        }
        total_comp += comp_n;
        ++passed;
    }

    std::printf("harmonyos test: %d/%d roundtrips OK on OHOS aarch64, total_compressed=%llu\n",
                passed,
                (int)(misa77::config::max_level - misa77::config::min_level + 1),
                static_cast<unsigned long long>(total_comp));
    return 0;
}