/* SPDX-License-Identifier: GPL-3.0-only
 * Adapted from wvkbd v0.15 layout.mobintl.h, keys_full (Full/default).
 * Upstream: https://github.com/jjsullivan5196/wvkbd/tree/v0.15
 * wvkbd contributors; upstream is a fork of svkbd by the suckless community.
 * See LICENSE for the upstream GNU GPL version 3 license.
 *
 * Retains printable keys, Shift, Backspace and Enter in their original row
 * order. Omits unsupported navigation, shortcut modifiers, layout switching,
 * compose/long-press actions and spacer cells. No Linux keycodes are retained.
 * Space has a visible label and always inserts a space: the upstream shifted
 * Space/Tab shortcut is outside this public text-insertion API's scope.
 */
#include "layout_mobintl.h"

#define TEXT(normal, shifted) {normal, shifted, WVKBD_ACTION_INSERT_TEXT, false}
#define LETTER(normal, shifted) {normal, shifted, WVKBD_ACTION_INSERT_TEXT, true}
#define CONTROL(label, shifted, action) {label, shifted, action, false}
#define COUNT(array) (sizeof(array) / sizeof((array)[0]))

static const wvkbd_layout_key punctuation[] = {
    TEXT("'", "\""), TEXT("-", "_"), TEXT("/", ">")
};
static const wvkbd_layout_key numbers[] = {
    TEXT("1", "!"), TEXT("2", "@"), TEXT("3", "#"), TEXT("4", "$"),
    TEXT("5", "%"), TEXT("6", "^"), TEXT("7", "&"), TEXT("8", "*"),
    TEXT("9", "("), TEXT("0", ")")
};
static const wvkbd_layout_key top[] = {
    LETTER("q", "Q"), LETTER("w", "W"), LETTER("e", "E"), LETTER("r", "R"),
    LETTER("t", "T"), LETTER("y", "Y"), LETTER("u", "U"), LETTER("i", "I"),
    LETTER("o", "O"), LETTER("p", "P")
};
static const wvkbd_layout_key home[] = {
    LETTER("a", "A"), LETTER("s", "S"), LETTER("d", "D"), LETTER("f", "F"),
    LETTER("g", "G"), LETTER("h", "H"), LETTER("j", "J"), LETTER("k", "K"), LETTER("l", "L")
};
static const wvkbd_layout_key bottom[] = {
    CONTROL("⇧", "⇫", WVKBD_ACTION_SHIFT), LETTER("z", "Z"), LETTER("x", "X"),
    LETTER("c", "C"), LETTER("v", "V"), LETTER("b", "B"), LETTER("n", "N"),
    LETTER("m", "M"), CONTROL("⌫", "⌫", WVKBD_ACTION_BACKSPACE)
};
static const wvkbd_layout_key footer[] = {
    TEXT(",", "'"), TEXT("Space", "Space"), TEXT(".", "?"),
    CONTROL("Enter", "Enter", WVKBD_ACTION_ENTER)
};
static const struct { const wvkbd_layout_key *keys; size_t count; } rows[] = {
    {punctuation, COUNT(punctuation)}, {numbers, COUNT(numbers)},
    {top, COUNT(top)}, {home, COUNT(home)}, {bottom, COUNT(bottom)}, {footer, COUNT(footer)}
};

size_t wvkbd_layout_row_count(void) { return COUNT(rows); }
size_t wvkbd_layout_key_count(size_t row) { return row < COUNT(rows) ? rows[row].count : 0; }
const wvkbd_layout_key *wvkbd_layout_key_at(size_t row, size_t column)
{
    if (column >= wvkbd_layout_key_count(row)) return NULL;
    return &rows[row].keys[column];
}
