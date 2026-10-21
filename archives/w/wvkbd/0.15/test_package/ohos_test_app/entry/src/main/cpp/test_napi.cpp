// SPDX-License-Identifier: GPL-3.0-only
#include <napi/native_api.h>
#include <cstddef>
extern "C" int wvkbd_test_consumer_results(int *results, size_t count);
namespace {
napi_value RunCases(napi_env env, napi_callback_info)
{
    int results[4] = {};
    if (wvkbd_test_consumer_results(results, 4) < 0) {
        napi_throw_error(env, nullptr, "Incomplete packaged core suite");
        return nullptr;
    }
    napi_value array;
    napi_create_array_with_length(env, 4, &array);
    for (uint32_t index = 0; index < 4; ++index) {
        napi_value result;
        napi_create_int32(env, results[index], &result);
        napi_set_element(env, array, index, result);
    }
    return array;
}
napi_value Init(napi_env env, napi_value exports)
{
    napi_property_descriptor property = { "runCases", nullptr, RunCases, nullptr, nullptr, nullptr, napi_default, nullptr };
    napi_define_properties(env, exports, 1, &property);
    return exports;
}
napi_module module = { 1, 0, nullptr, Init, "wvkbd_test", nullptr, { nullptr } };
}
extern "C" __attribute__((constructor)) void RegisterTestModule() { napi_module_register(&module); }
