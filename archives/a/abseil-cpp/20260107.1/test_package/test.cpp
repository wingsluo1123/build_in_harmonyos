#include <absl/strings/str_cat.h>
#include <absl/strings/string_view.h>
#include <cassert>
#include <cstdio>

int main() {
    std::string s = absl::StrCat("hello", " ", "abseil", " ", "20260107.1");
    absl::string_view sv(s);
    assert(sv.size() == s.size());
    printf("abseil-cpp test: %s\n", s.c_str());
    return 0;
}
