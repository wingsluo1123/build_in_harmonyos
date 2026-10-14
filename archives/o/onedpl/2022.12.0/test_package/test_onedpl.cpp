// test_onedpl.cpp -- consumer test for oneDPL 2022.12.0 (serial backend).
// Exercises the real public API (oneapi/dpl/algorithm + numeric) under both
// the seq and par execution policies and verifies every result explicitly.
// Each numbered check prints a PASS line; any mismatch prints FAIL and the
// program exits non-zero (explicit return, valid in Release/NDEBUG builds).
#include <algorithm>
#include <functional>
#include <iostream>
#include <numeric>
#include <vector>

#include <oneapi/dpl/algorithm>
#include <oneapi/dpl/execution>
#include <oneapi/dpl/numeric>

#include <oneapi/dpl/internal/version_impl.h>

namespace ex = oneapi::dpl::execution;

static int failures = 0;

static void check(int id, const char* name, bool ok) {
    if (ok) {
        std::cout << "[check " << id << "] " << name << ": PASS" << std::endl;
    } else {
        std::cout << "[check " << id << "] " << name << ": FAIL" << std::endl;
        ++failures;
    }
}

int main() {
    // Check 1: library version macros match 2022.12.0.
    check(1, "version macros",
          ONEDPL_VERSION_MAJOR == 2022 && ONEDPL_VERSION_MINOR == 12 &&
              ONEDPL_VERSION_PATCH == 0);

    // Check 2: sort with seq policy.
    {
        std::vector<int> v{5, 1, 4, 2, 3};
        oneapi::dpl::sort(ex::seq, v.begin(), v.end());
        check(2, "sort seq",
              v == std::vector<int>({1, 2, 3, 4, 5}));
    }

    // Check 3: sort with par policy and comparator.
    {
        std::vector<int> v{1, 5, 2, 4, 3};
        oneapi::dpl::sort(ex::par, v.begin(), v.end(), std::greater<int>());
        check(3, "sort par greater",
              v == std::vector<int>({5, 4, 3, 2, 1}));
    }

    // Check 4: transform with seq policy (doubling).
    {
        std::vector<int> in{1, 2, 3, 4};
        std::vector<int> out(4, 0);
        oneapi::dpl::transform(ex::seq, in.begin(), in.end(), out.begin(),
                               [](int x) { return x * 2; });
        check(4, "transform seq",
              out == std::vector<int>({2, 4, 6, 8}));
    }

    // Check 5: transform_reduce with par policy (sum 1..100 = 5050).
    {
        std::vector<int> v(100);
        std::iota(v.begin(), v.end(), 1);
        int sum = oneapi::dpl::transform_reduce(
            ex::par, v.begin(), v.end(), 0, std::plus<int>(),
            [](int x) { return x; });
        check(5, "transform_reduce par", sum == 5050);
    }

    // Check 6: exclusive_scan with seq policy (prefix sums of ones).
    {
        std::vector<int> in(5, 1);
        std::vector<int> out(5, 0);
        oneapi::dpl::exclusive_scan(ex::seq, in.begin(), in.end(), out.begin(), 0);
        check(6, "exclusive_scan seq",
              out == std::vector<int>({0, 1, 2, 3, 4}));
    }

    // Check 7: find_if with par policy (first value greater than 3).
    {
        std::vector<int> v{1, 2, 3, 4, 5};
        auto it = oneapi::dpl::find_if(ex::par, v.begin(), v.end(),
                                       [](int x) { return x > 3; });
        check(7, "find_if par", it != v.end() && *it == 4);
    }

    // Check 8: count_if with seq policy (odd numbers in 1..10).
    {
        std::vector<int> v(10);
        std::iota(v.begin(), v.end(), 1);
        auto n = oneapi::dpl::count_if(ex::seq, v.begin(), v.end(),
                                       [](int x) { return x % 2 == 1; });
        check(8, "count_if seq", n == 5);
    }

    // Check 9: merge with seq policy (two sorted ranges).
    {
        std::vector<int> a{1, 3, 5};
        std::vector<int> b{2, 4, 6};
        std::vector<int> out(6, 0);
        oneapi::dpl::merge(ex::seq, a.begin(), a.end(), b.begin(), b.end(),
                           out.begin());
        check(9, "merge seq",
              out == std::vector<int>({1, 2, 3, 4, 5, 6}));
    }

    // Check 10: for_each with par policy then reverse with seq policy.
    {
        std::vector<int> v(5, 0);
        oneapi::dpl::for_each(ex::par, v.begin(), v.end(),
                              [](int& x) { x = 7; });
        oneapi::dpl::reverse(ex::seq, v.begin(), v.end());
        check(10, "for_each par + reverse seq",
              v == std::vector<int>({7, 7, 7, 7, 7}));
    }

    if (failures == 0) {
        std::cout << "ALL 10 CHECKS PASSED" << std::endl;
        return 0;
    }
    std::cout << failures << " CHECK(S) FAILED" << std::endl;
    return 1;
}
