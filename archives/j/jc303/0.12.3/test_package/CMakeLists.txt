cmake_minimum_required(VERSION 3.15)
project(jc303_bundle_probe C)

if(NOT DEFINED JC303_PACKAGE_DIR)
    message(FATAL_ERROR "JC303_PACKAGE_DIR not provided by test_package conanfile")
endif()

set(BUNDLE_ROOT "${JC303_PACKAGE_DIR}/lib/jc303")

# ── bundle 布局断言（configure 期，缺失即 FATAL_ERROR） ──────────────────
file(GLOB VST3_SO "${BUNDLE_ROOT}/JC303.vst3/Contents/*/*.so")
file(GLOB LV2_SO  "${BUNDLE_ROOT}/JC303.lv2/*.so")
file(GLOB LV2_TTL "${BUNDLE_ROOT}/JC303.lv2/*.ttl")
# clap-juce-extensions 的 Linux CLAP 产物为目录 bundle：JC303.clap/JC303.clap
file(GLOB CLAP_BIN "${BUNDLE_ROOT}/JC303.clap/JC303.clap")

list(LENGTH VST3_SO VST3_SO_N)
list(LENGTH LV2_SO  LV2_SO_N)
list(LENGTH LV2_TTL LV2_TTL_N)

if(NOT VST3_SO_N EQUAL 1)
    message(FATAL_ERROR "expected exactly one VST3 plugin .so under "
            "${BUNDLE_ROOT}/JC303.vst3/Contents/<arch>/, found ${VST3_SO_N}")
endif()
if(NOT LV2_SO_N EQUAL 1)
    message(FATAL_ERROR "expected exactly one LV2 plugin .so under "
            "${BUNDLE_ROOT}/JC303.lv2/, found ${LV2_SO_N}")
endif()
if(LV2_TTL_N LESS 2)
    message(FATAL_ERROR "expected >=2 LV2 .ttl files (plugin + manifest) "
            "under ${BUNDLE_ROOT}/JC303.lv2/, found ${LV2_TTL_N}")
endif()
if(NOT EXISTS "${CLAP_BIN}")
    message(FATAL_ERROR "CLAP binary missing: ${CLAP_BIN}")
endif()

list(GET VST3_SO 0 VST3_SO_PATH)
list(GET LV2_SO 0 LV2_SO_PATH)

add_executable(jc303_bundle_probe clap_probe.c)
target_compile_definitions(jc303_bundle_probe PRIVATE
    JC303_VST3_SO="${VST3_SO_PATH}"
    JC303_LV2_SO="${LV2_SO_PATH}"
    JC303_CLAP_PATH="${CLAP_BIN}"
    JC303_VST3_SO_N=${VST3_SO_N}
    JC303_LV2_SO_N=${LV2_SO_N}
    JC303_TTL_N=${LV2_TTL_N})
target_link_libraries(jc303_bundle_probe PRIVATE ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME jc303_bundle_probe COMMAND jc303_bundle_probe)
