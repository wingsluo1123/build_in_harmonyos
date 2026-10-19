/* SPDX-License-Identifier: GPL-3.0-only */
#ifndef WVKBD_LAYOUT_MOBINTL_H
#define WVKBD_LAYOUT_MOBINTL_H
#include "wvkbd_core.h"

typedef struct {
    const char *normal;
    const char *shifted;
    wvkbd_action action;
    bool letter;
} wvkbd_layout_key;

size_t wvkbd_layout_row_count(void);
size_t wvkbd_layout_key_count(size_t row);
const wvkbd_layout_key *wvkbd_layout_key_at(size_t row, size_t column);
#endif
