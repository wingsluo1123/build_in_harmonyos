/* SPDX-License-Identifier: GPL-3.0-only */
#ifndef WVKBD_CORE_H
#define WVKBD_CORE_H

#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define WVKBD_CORE_TEXT_CAPACITY 32

typedef enum {
    WVKBD_ACTION_INSERT_TEXT,
    WVKBD_ACTION_BACKSPACE,
    WVKBD_ACTION_ENTER,
    WVKBD_ACTION_SHIFT
} wvkbd_action;

typedef struct { bool shift; bool caps_lock; } wvkbd_core_state;
typedef struct { const char *label; wvkbd_action action; } wvkbd_key_view;
typedef struct { wvkbd_action action; char text[WVKBD_CORE_TEXT_CAPACITY]; } wvkbd_event;

/* Null state pointers are ignored by these two state setters. */
void wvkbd_core_state_init(wvkbd_core_state *state);
void wvkbd_core_set_caps_lock(wvkbd_core_state *state, bool enabled);
size_t wvkbd_core_row_count(void);
/* An invalid row has zero keys. */
size_t wvkbd_core_key_count(size_t row);
/* Return 0 on success, -1 for null pointers or invalid coordinates.
 * Non-null outputs are zeroed on failure; state is unchanged on failure.
 * Labels have static lifetime and remain owned by the library. */
int wvkbd_core_key_at(const wvkbd_core_state *state, size_t row,
                      size_t column, wvkbd_key_view *out);
/* Text is emitted only for INSERT_TEXT. Any non-Shift action consumes
 * one-shot Shift; Caps remains active until explicitly changed. */
int wvkbd_core_activate(wvkbd_core_state *state, size_t row, size_t column,
                        wvkbd_event *out);

#ifdef __cplusplus
}
#endif
#endif
