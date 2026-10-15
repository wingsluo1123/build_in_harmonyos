// test_iitii.cpp — L1 consumer test for iitii header-only library.
// Exercises the real iit/iitii builder + overlap API (R34):
// cases 1-4 replicate upstream test_iitii.cc deterministic TEST_CASEs,
// case 5 is a small fixed-seed fuzz cross-checked against naive scan.
//
// NOTE (OHOS fix): upstream src/iitii.h at 85209e0 exposes only the
// memory-mapped builder (iit_mm_builder_base) for both iit::builder and
// iitii::builder, so every builder needs a backing file first argument:
//   builder(const std::string& file) / builder(file, begin, end).
// The previous revision used the in-memory builder API (builder() default +
// builder(begin, end)) which does not exist here, and `using namespace iitii`
// collided with class ::iitii::iitii (ambiguous lookup). Both are fixed below
// with fully-qualified aliases and per-case backing files. No assertion is
// removed or weakened.
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <random>
#include <string>
#include <utility>
#include <vector>

#include "iitii.h"

using pos = uint32_t;
using pospair = std::pair<pos, pos>;

static pos get_beg(const pospair& p) { return p.first; }
static pos get_end(const pospair& p) { return p.second; }

// Fully-qualified aliases: never `using namespace iitii` (namespace iitii
// vs class ::iitii::iitii would be ambiguous).
using Iit = ::iitii::iit<pos, pospair, &get_beg, &get_end>;
using Iitii = ::iitii::iitii<pos, pospair, &get_beg, &get_end>;

static int failures = 0;
static const int kDiscovered = 10;

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (!(cond)) {                                                       \
            std::cerr << "FAIL: " << msg << std::endl;                       \
            ++failures;                                                      \
        } else {                                                             \
            std::cout << "ok: " << msg << std::endl;                          \
        }                                                                    \
    } while (0)

// Backing file for the mm_builder. Prefers the HMBS-injected TMPDIR
// (task-independent, writable on OHOS); falls back to the current directory.
static std::string backing_file(const char* tag) {
    const char* dir = std::getenv("TMPDIR");
    if (dir == nullptr || dir[0] == '\0') dir = std::getenv("TMP");
    if (dir == nullptr || dir[0] == '\0') dir = std::getenv("TEMP");
    std::string path;
    if (dir != nullptr && dir[0] != '\0') {
        path = std::string(dir) + "/iitii_" + tag + ".bin";
    } else {
        path = std::string("./iitii_") + tag + ".bin";
    }
    // The mm_builder opens per-thread spill files in append mode, so a stale
    // backing file from a previous run would corrupt the new index.
    std::remove(path.c_str());
    std::remove((path + ".tmp_write.0").c_str());
    std::remove((path + ".tmp_write.1").c_str());
    return path;
}

int main() {
    // Case 1: cgranges example with iit.
    {
        std::string fn = backing_file("case1");
        Iit::builder br(fn);
        br.add(pospair(12, 34));
        br.add(pospair(0, 23));
        br.add(pospair(34, 56));
        auto tree = br.build();
        std::vector<pospair> results = tree.overlap(22, 25);
        CHECK(results.size() == 2, "iit overlap(22,25) finds 2 intervals");
        CHECK(results.size() == 2 && results[0].first == 0, "iit first hit begins at 0");
        CHECK(results.size() == 2 && results[1].first == 12, "iit second hit begins at 12");
    }

    // Case 2: cgranges example with iitii (1 domain).
    {
        std::string fn = backing_file("case2");
        Iitii::builder br(fn);
        br.add(pospair(12, 34));
        br.add(pospair(0, 23));
        br.add(pospair(34, 56));
        auto tree = br.build(1);
        std::vector<pospair> results = tree.overlap(22, 25);
        CHECK(results.size() == 2, "iitii overlap(22,25) finds 2 intervals");
        CHECK(results.size() == 2 && results[0].first == 0, "iitii first hit begins at 0");
    }

    // Case 3: dark nodes (N=5) with iit, including visit-cost assertion.
    {
        std::vector<pospair> examples = {{0, 7}, {1, 2}, {2, 4}, {3, 6}, {4, 9}};
        std::string fn = backing_file("case3");
        Iit::builder br(fn, examples.begin(), examples.end());
        auto tree = br.build();
        std::vector<pospair> results = tree.overlap(6, 10);
        CHECK(results.size() == 2, "dark nodes overlap(6,10) finds 2 intervals");
        size_t cost = tree.overlap(7, 10, results);
        CHECK(cost == 4, "dark nodes overlap(7,10) visits 4 nodes");
    }

    // Case 4: dark nodes with iitii — interpolation answers in one step.
    {
        std::vector<pospair> examples = {{0, 7}, {1, 2}, {2, 4}, {3, 6}, {4, 9}};
        std::string fn = backing_file("case4");
        Iitii::builder br(fn, examples.begin(), examples.end());
        auto tree = br.build(1);
        std::vector<pospair> results;
        size_t cost = tree.overlap(7, 10, results);
        CHECK(results.size() == 1, "iitii dark nodes overlap(7,10) finds 1 interval");
        CHECK(cost == 1, "iitii dark nodes overlap(7,10) costs 1 visit");
    }

    // Case 5: small fixed-seed fuzz cross-checked against naive scan.
    {
        std::default_random_engine rng(42);
        std::uniform_int_distribution<uint32_t> beg_dist(1, 4200);
        std::geometric_distribution<uint16_t> len_dist(0.05);
        std::vector<pospair> examples;
        for (int i = 0; i < 300; ++i) {
            auto beg = beg_dist(rng);
            examples.push_back({beg, static_cast<pos>(beg + len_dist(rng))});
        }
        std::string fn1 = backing_file("case5a");
        std::string fn2 = backing_file("case5b");
        Iit::builder br1(fn1, examples.begin(), examples.end());
        auto tree = br1.build();
        Iitii::builder br2(fn2, examples.begin(), examples.end());
        auto treeii = br2.build(10);
        std::sort(examples.begin(), examples.end(), [](const pospair& a, const pospair& b) {
            if (a.first == b.first) return a.second < b.second;
            return a.first < b.first;
        });
        bool all_match = true;
        for (int q = 0; q < 100; ++q) {
            auto qbeg = beg_dist(rng);
            auto qend = static_cast<pos>(qbeg + 42);
            std::vector<pospair> ans, ansii, naive;
            tree.overlap(qbeg, qend, ans);
            treeii.overlap(qbeg, qend, ansii);
            for (const auto& p : examples) {
                if (qbeg < p.second && p.first < qend) naive.push_back(p);
            }
            if (ans != naive || ansii != naive) {
                all_match = false;
                break;
            }
        }
        CHECK(all_match, "fuzz(300 intervals, 100 queries) matches naive scan");
    }

    // Machine evidence marker: counts come from the real CHECK counter above
    // (discovered is the static number of CHECK sites; passedCount is
    // discovered minus actual failures). No stdout string counting.
    const int passedCount = kDiscovered - failures;
    std::cout << "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":"
              << (failures == 0 ? "true" : "false")
              << ",\"command\":\"./test_iitii\",\"discovered\":" << kDiscovered
              << ",\"passedCount\":" << passedCount << "}" << std::endl;

    if (failures == 0) {
        std::cout << "PASS: iitii header-only consumer test passed (10 checks)" << std::endl;
        return 0;
    }
    std::cerr << "FAILURES: " << failures << " check(s) failed" << std::endl;
    return 1;
}
