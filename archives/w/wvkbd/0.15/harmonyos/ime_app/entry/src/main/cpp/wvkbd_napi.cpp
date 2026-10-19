// SPDX-License-Identifier: GPL-3.0-only
#include <napi/native_api.h>
#include <cmath>
#include <cstdint>
#include "wvkbd_core.h"

namespace {
wvkbd_core_state state = { false, false };

napi_value Fail(napi_env env, const char *message)
{
    napi_throw_error(env, nullptr, message);
    return nullptr;
}

bool Coordinates(napi_env env, napi_callback_info info, uint32_t &row, uint32_t &column)
{
    size_t count = 2;
    napi_value args[2];
    if (napi_get_cb_info(env, info, &count, args, nullptr, nullptr) != napi_ok || count != 2) {
        napi_throw_type_error(env, nullptr, "Two nonnegative integer coordinates are required");
        return false;
    }
    uint32_t *outputs[] = { &row, &column };
    for (size_t i = 0; i < 2; ++i) {
        double number;
        if (napi_get_value_double(env, args[i], &number) != napi_ok || !std::isfinite(number) ||
            number < 0 || number > UINT32_MAX || std::floor(number) != number) {
            napi_throw_range_error(env, nullptr, "Invalid key coordinate");
            return false;
        }
        *outputs[i] = static_cast<uint32_t>(number);
    }
    return true;
}

bool Number(napi_env env, napi_value object, const char *name, uint32_t value)
{
    napi_value output;
    return napi_create_uint32(env, value, &output) == napi_ok &&
        napi_set_named_property(env, object, name, output) == napi_ok;
}

bool Text(napi_env env, napi_value object, const char *name, const char *value)
{
    napi_value output;
    return napi_create_string_utf8(env, value, NAPI_AUTO_LENGTH, &output) == napi_ok &&
        napi_set_named_property(env, object, name, output) == napi_ok;
}

bool Modifiers(napi_env env, napi_value object)
{
    napi_value shift, caps;
    return napi_get_boolean(env, state.shift, &shift) == napi_ok &&
        napi_get_boolean(env, state.caps_lock, &caps) == napi_ok &&
        napi_set_named_property(env, object, "shift", shift) == napi_ok &&
        napi_set_named_property(env, object, "capsLock", caps) == napi_ok;
}

napi_value RowCount(napi_env env, napi_callback_info)
{
    napi_value output;
    if (napi_create_uint32(env, wvkbd_core_row_count(), &output) != napi_ok) return Fail(env, "rowCount failed");
    return output;
}

napi_value KeyCount(napi_env env, napi_callback_info info)
{
    size_t count = 1;
    napi_value argument, output;
    double row;
    if (napi_get_cb_info(env, info, &count, &argument, nullptr, nullptr) != napi_ok || count != 1 ||
        napi_get_value_double(env, argument, &row) != napi_ok || !std::isfinite(row) ||
        row < 0 || row > UINT32_MAX || std::floor(row) != row) {
        napi_throw_range_error(env, nullptr, "Invalid row");
        return nullptr;
    }
    if (napi_create_uint32(env, wvkbd_core_key_count(static_cast<uint32_t>(row)), &output) != napi_ok)
        return Fail(env, "keyCount failed");
    return output;
}

napi_value KeyAt(napi_env env, napi_callback_info info)
{
    uint32_t row, column;
    if (!Coordinates(env, info, row, column)) return nullptr;
    wvkbd_key_view key;
    if (wvkbd_core_key_at(&state, row, column, &key) != 0) return Fail(env, "Unknown key");
    napi_value output;
    if (napi_create_object(env, &output) != napi_ok || !Text(env, output, "label", key.label) ||
        !Number(env, output, "action", key.action) || !Modifiers(env, output)) return Fail(env, "keyAt failed");
    return output;
}

napi_value Activate(napi_env env, napi_callback_info info)
{
    uint32_t row, column;
    if (!Coordinates(env, info, row, column)) return nullptr;
    wvkbd_event event;
    if (wvkbd_core_activate(&state, row, column, &event) != 0) return Fail(env, "Unknown key");
    napi_value output;
    if (napi_create_object(env, &output) != napi_ok || !Text(env, output, "text", event.text) ||
        !Number(env, output, "action", event.action) || !Modifiers(env, output)) return Fail(env, "activate failed");
    return output;
}

napi_value SetCapsLock(napi_env env, napi_callback_info info)
{
    size_t count = 1;
    napi_value argument, output;
    bool enabled;
    if (napi_get_cb_info(env, info, &count, &argument, nullptr, nullptr) != napi_ok || count != 1 ||
        napi_get_value_bool(env, argument, &enabled) != napi_ok) {
        napi_throw_type_error(env, nullptr, "Caps Lock requires a boolean");
        return nullptr;
    }
    wvkbd_core_set_caps_lock(&state, enabled);
    napi_get_undefined(env, &output);
    return output;
}

napi_value Reset(napi_env env, napi_callback_info)
{
    wvkbd_core_state_init(&state);
    napi_value output;
    napi_get_undefined(env, &output);
    return output;
}

napi_value Init(napi_env env, napi_value exports)
{
    napi_property_descriptor properties[] = {
        { "rowCount", nullptr, RowCount, nullptr, nullptr, nullptr, napi_default, nullptr },
        { "keyCount", nullptr, KeyCount, nullptr, nullptr, nullptr, napi_default, nullptr },
        { "keyAt", nullptr, KeyAt, nullptr, nullptr, nullptr, napi_default, nullptr },
        { "activate", nullptr, Activate, nullptr, nullptr, nullptr, napi_default, nullptr },
        { "setCapsLock", nullptr, SetCapsLock, nullptr, nullptr, nullptr, napi_default, nullptr },
        { "resetSession", nullptr, Reset, nullptr, nullptr, nullptr, napi_default, nullptr },
        { "dismiss", nullptr, Reset, nullptr, nullptr, nullptr, napi_default, nullptr }
    };
    if (napi_define_properties(env, exports, sizeof(properties) / sizeof(properties[0]), properties) != napi_ok)
        return Fail(env, "Native keyboard initialization failed");
    return exports;
}

napi_module module = { 1, 0, nullptr, Init, "wvkbd_napi", nullptr, { nullptr } };
}

extern "C" __attribute__((constructor)) void RegisterWvkbdModule()
{
    napi_module_register(&module);
}
