// Consumer probe for indi-dsi (R34): exercises the driver's public helper
// tokenize_str() from the vendored Util.cpp — upstream ships no test suite
// (R51, see notes.md for the source-tree inventory evidence).
//
// Semantics under test (from Util.cpp):
//   - consecutive delimiters are treated as a single delimiter
//   - delimiters are not included in the returned tokens
//   - leading delimiters are skipped
#include "Util.h"

#include <cstdio>
#include <string>
#include <vector>

static int failures = 0;

static void expect_tokens(const char *label, const std::vector<std::string> &got,
                          std::initializer_list<const char *> want)
{
    bool ok = got.size() == want.size();
    if (ok)
    {
        size_t i = 0;
        for (const char *w : want)
            ok = ok && (got[i++] == w);
    }
    if (ok)
    {
        std::printf("%s: PASS (%zu tokens)\n", label, got.size());
    }
    else
    {
        ++failures;
        std::printf("%s: FAIL got [", label);
        for (const auto &t : got)
            std::printf("\"%s\" ", t.c_str());
        std::printf("]\n");
    }
}

int main()
{
    // default delimiters ", \t": basic split with mixed delimiters
    expect_tokens("mixed_delims", tokenize_str("a, b\tc"), {"a", "b", "c"});
    // consecutive delimiters collapse to one
    expect_tokens("consecutive", tokenize_str("a,,b", ","), {"a", "b"});
    // leading delimiters are skipped
    expect_tokens("leading", tokenize_str(",,lead", ","), {"lead"});
    // trailing delimiter yields no empty tail token
    expect_tokens("trailing", tokenize_str("abc,", ","), {"abc"});
    // empty input -> no tokens
    expect_tokens("empty", tokenize_str(""), {});
    // custom single delimiter (e.g. exposure parameter lists)
    expect_tokens("custom_colon", tokenize_str("10:20:30", ":"), {"10", "20", "30"});

    if (failures == 0)
        std::printf("PASS: tokenize_str public helper exercised (6 assertion groups)\n");
    return failures == 0 ? 0 : 1;
}
