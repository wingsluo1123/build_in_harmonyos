// test.cpp — consumer smoke test for scim 1.4.18-git20211204
// Exercises the public libscim API exposed through the installed headers
// (scim.h / scim_utility.h): UTF-8 <-> WideString conversion plus the
// public locale helpers, proving the package links and works.
#include <scim.h>
#include <cstdio>
#include <string>

using namespace scim;

int main() {
    // Core utility API: UTF-8 multibyte <-> wide string round-trip.
    String utf8 = "SCIM Thai \xe0\xb8\xa0\xe0\xb8\xb2\xe0\xb8\xa9\xe0\xb8\xb2";
    WideString wide = utf8_mbstowcs(utf8);
    String back = utf8_wcstombs(wide);
    if (utf8 != back) {
        std::printf("UTF-8 round-trip failed\n");
        return 1;
    }

    // Public locale helpers (declared in scim_utility.h).
    String lang = scim_get_current_language();
    String enc = scim_get_locale_encoding(lang);
    if (enc.empty() && lang.empty()) {
        // OHOS has no locale set; fall back to a fixed round-trip only.
        std::printf("scim API round-trip OK (no locale)\n");
        return 0;
    }
    if (enc.empty()) {
        std::printf("scim API round-trip OK (locale=%s, no encoding)\n",
                    lang.c_str());
        return 0;
    }

    std::printf("scim API round-trip OK (locale=%s, enc=%s)\n",
                lang.c_str(), enc.c_str());
    return 0;
}