/*
 * SPDX-FileCopyrightText: 2026-2026 fcitx5 adaptation
 *
 * SPDX-License-Identifier: LGPL-2.1-or-later
 *
 * test_fcitx5_ohos.cpp — fcitx5 5.1.14 鸿蒙（HarmonyOS）专项测试
 *
 * 目的：验证 OHOS 平台适配的真实行为，区别于上游通用测试：
 *  1. StandardPaths 平台路径查询（standardpaths_p_unix.cpp 的 OHOS 路径
 *     适配：XDG 环境、userDirectory/directories 顺序），断言返回非空且
 *     可观察结果。该文件正是本适配打过 OHOS libc++ 兼容补丁的组件
 *     （std::ranges/std::views → 标准算法、unordered_set<fs::path>→set）。
 *  2. environ 平台环境读写（environment 查询为 OHOS 平台行为）。
 *  3. SemanticVersion/Key/stringutils 公开 API（消费者等价调用）。
 *
 * 本机为 aarch64 HarmonyOS，可执行文件原生运行（非 cross-building）。
 */
#include <fcitx-utils/environ.h>
#include <fcitx-utils/key.h>
#include <fcitx-utils/semver.h>
#include <fcitx-utils/standardpaths.h>
#include <fcitx-utils/stringutils.h>

#include <cassert>
#include <iostream>
#include <string>

int main() {
    // 1. StandardPaths：OHOS 平台路径查询（真实可观察结果）
    const auto &standardPaths = fcitx::StandardPaths::global();
    const auto userDataDir =
        standardPaths.userDirectory(fcitx::StandardPathsType::Data);
    std::cout << "OHOS userDataDir: " << userDataDir << std::endl;
    assert(!userDataDir.empty());
    const auto dataDirs =
        standardPaths.directories(fcitx::StandardPathsType::Data);
    assert(!dataDirs.empty());
    std::cout << "OHOS dataDirs: " << dataDirs.size() << " entries"
              << std::endl;

    // 2. environ：平台环境变量读写（set/get 往返断言）
    fcitx::setEnvironment("FCITX5_OHOS_TEST", "fcitx5-ohos");
    auto got = fcitx::getEnvironmentOrEmpty("FCITX5_OHOS_TEST");
    assert(got == "fcitx5-ohos");
    std::cout << "OHOS environ roundtrip: " << got << std::endl;

    // 3. 公开 API 等价断言
    const auto semver = fcitx::SemanticVersion::parse("5.1.14");
    assert(semver.has_value());
    assert(semver->major() == 5 && semver->minor() == 1 &&
           semver->patch() == 14);
    const fcitx::Key key("Control+Alt+E");
    assert(key.isValid());
    const std::string trimmed = fcitx::stringutils::trim("  fcitx5  ");
    assert(trimmed == "fcitx5");

    std::cout << "fcitx5 OHOS-specific test PASSED" << std::endl;
    return 0;
}