/* SPDX-License-Identifier: GPL-3.0-only */
#include "core_cases.h"
#include <string.h>

int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    for (size_t i = 0; i < wvkbd_test_case_count; ++i) {
        if (strcmp(argv[1], wvkbd_test_cases[i].name) == 0)
            return wvkbd_test_cases[i].run();
    }
    return 2;
}
