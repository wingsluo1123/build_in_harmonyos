/* SPDX-License-Identifier: GPL-3.0-only
 * Test-only shared behavior cases; not part of the product library API. */
#ifndef WVKBD_CORE_CASES_H
#define WVKBD_CORE_CASES_H
#include "wvkbd_core.h"

typedef struct {
    const char *id;
    const char *name;
    int (*run)(void);
} wvkbd_test_case;

extern const wvkbd_test_case wvkbd_test_cases[];
extern const size_t wvkbd_test_case_count;
#endif
