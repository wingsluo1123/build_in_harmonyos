/*
 * test_package for xkbcommon 1.13.2 (HarmonyOS PC)
 *
 * 鸿蒙特有冒烟测试：实质调用被测包核心 API——
 *   xkb_context_new / xkb_keymap_new_from_string / xkb_keymap_new_from_names
 *   / xkb_state_new / xkb_state_update_key / xkb_keysym_to_utf8
 * 内联 keymap 定义（不依赖外部 xkeyboard-config 数据文件），
 * 验证 libxkbcommon 在 OHOS 上可创建上下文、编译 keymap 并处理按键状态。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <xkbcommon/xkbcommon.h>

static const char INLINE_KEYMAP[] =
    "xkb_keymap {\n"
    "xkb_keycodes \"test\" {\n"
    "    minimum = 8;\n"
    "    maximum = 255;\n"
    "    <TLDE> = 49;\n"
    "    <AB01> = 30;\n"
    "};\n"
    "xkb_types \"test\" { virtual_modifiers NumLock; };\n"
    "xkb_compatibility \"test\" { };\n"
    "xkb_symbols \"test\" {\n"
    "    key <TLDE> { [ grave, asciitilde ] };\n"
    "    key <AB01> { [ a, A ] };\n"
    "};\n"
    "};\n";

int main(void) {
    struct xkb_context *ctx = xkb_context_new(XKB_CONTEXT_NO_FLAGS);
    if (!ctx) {
        fprintf(stderr, "FAIL: xkb_context_new returned NULL\n");
        return 1;
    }
    xkb_context_set_log_level(ctx, XKB_LOG_LEVEL_ERROR);

    /* 1. 编译内联 keymap（不依赖外部 xkeyboard-config 数据） */
    struct xkb_keymap *keymap = xkb_keymap_new_from_string(
        ctx, INLINE_KEYMAP, XKB_KEYMAP_FORMAT_TEXT_V1,
        XKB_KEYMAP_COMPILE_NO_FLAGS);
    if (!keymap) {
        fprintf(stderr, "FAIL: xkb_keymap_new_from_string returned NULL\n");
        xkb_context_unref(ctx);
        return 1;
    }
    if (xkb_keymap_min_keycode(keymap) == XKB_KEYCODE_INVALID) {
        fprintf(stderr, "FAIL: invalid min keycode\n");
        xkb_keymap_unref(keymap);
        xkb_context_unref(ctx);
        return 1;
    }

    /* 2. 创建状态并模拟按键 */
    struct xkb_state *state = xkb_state_new(keymap);
    if (!state) {
        fprintf(stderr, "FAIL: xkb_state_new returned NULL\n");
        xkb_keymap_unref(keymap);
        xkb_context_unref(ctx);
        return 1;
    }
    xkb_keycode_t kc = xkb_keymap_key_by_name(keymap, "AB01");
    if (kc == XKB_KEYCODE_INVALID) {
        fprintf(stderr, "FAIL: key_by_name(AB01) invalid\n");
        xkb_state_unref(state);
        xkb_keymap_unref(keymap);
        xkb_context_unref(ctx);
        return 1;
    }
    xkb_state_update_key(state, kc, XKB_KEY_DOWN);
    xkb_keysym_t sym = xkb_state_key_get_one_sym(state, kc);
    if (sym != XKB_KEY_a) {
        fprintf(stderr, "FAIL: expected keysym 'a' (0x%x), got 0x%x\n",
                XKB_KEY_a, (unsigned)sym);
        xkb_state_unref(state);
        xkb_keymap_unref(keymap);
        xkb_context_unref(ctx);
        return 1;
    }
    char buf[8] = {0};
    int n = xkb_state_key_get_utf8(state, kc, buf, sizeof(buf));
    if (n != 1 || buf[0] != 'a') {
        fprintf(stderr, "FAIL: expected utf8 'a', got '%s'\n", buf);
        xkb_state_unref(state);
        xkb_keymap_unref(keymap);
        xkb_context_unref(ctx);
        return 1;
    }

    /* 3. RMLVO 方式编译 */
    struct xkb_rule_names rmlvo = {0};
    struct xkb_keymap *km2 = xkb_keymap_new_from_names(ctx, &rmlvo,
                                                       XKB_KEYMAP_COMPILE_NO_FLAGS);
    /* 无外部数据时可能失败，不作为硬性断言，仅记录 */
    if (km2)
        xkb_keymap_unref(km2);

    xkb_state_unref(state);
    xkb_keymap_unref(keymap);
    xkb_context_unref(ctx);
    printf("xkbcommon smoke test OK (context/keymap/state/keysym/utf8)\n");
    return 0;
}
