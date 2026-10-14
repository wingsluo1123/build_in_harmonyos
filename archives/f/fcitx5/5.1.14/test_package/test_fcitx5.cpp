/*
 * SPDX-FileCopyrightText: 2026-2026 fcitx5 adaptation
 *
 * SPDX-License-Identifier: LGPL-2.1-or-later
 *
 * 消费者用例：模拟业务上层组件通过 fcitx5 已安装/导出的公开头文件与
 * CMake 目标使用该三方库。仅使用公开 API：
 *   - fcitx::SemanticVersion::parse（版本号解析，返回 optional）
 *   - fcitx::Key 字符串构造 + states()/isValid()/toString()
 *   - fcitx::stringutils::trim（字符串处理）
 * 并链接 Fcitx5::Core 验证核心库可链接、可运行。
 */
#include <fcitx-utils/key.h>
#include <fcitx-utils/semver.h>
#include <fcitx-utils/stringutils.h>
#include <iostream>
#include <string>

int main() {
    // 1. SemanticVersion 公开 API：解析版本号并断言各分量
    auto ver = fcitx::SemanticVersion::parse("5.1.14");
    if (!ver) {
        std::cerr << "FAIL: SemanticVersion::parse returned nullopt"
                  << std::endl;
        return 1;
    }
    if (ver->major() != 5 || ver->minor() != 1 || ver->patch() != 14) {
        std::cerr << "FAIL: Semver parse mismatch: " << ver->major() << "."
                  << ver->minor() << "." << ver->patch() << std::endl;
        return 1;
    }
    std::cout << "SemanticVersion 5.1.14 parsed: " << ver->major() << "."
              << ver->minor() << "." << ver->patch() << std::endl;

    // 2. Key 公开 API：字符串构造 + 状态断言
    fcitx::Key key("Control+Alt+E");
    if (!key.isValid()) {
        std::cerr << "FAIL: Key(const char*) produced invalid key" << std::endl;
        return 1;
    }
    auto states = key.states();
    if (!states.test(fcitx::KeyState::Ctrl) ||
        !states.test(fcitx::KeyState::Alt)) {
        std::cerr << "FAIL: key states missing Ctrl/Alt: " << key.toString()
                  << std::endl;
        return 1;
    }
    std::cout << "Key Control+Alt+E parsed: " << key.toString() << std::endl;

    // 3. stringutils::trim 公开 API：断言修剪结果
    std::string trimmed = fcitx::stringutils::trim("  fcitx5  ");
    if (trimmed != "fcitx5") {
        std::cerr << "FAIL: trim result '" << trimmed << "'" << std::endl;
        return 1;
    }
    std::cout << "trim(\"  fcitx5  \") = \"" << trimmed << "\"" << std::endl;

    std::cout << "fcitx5 consumer test PASSED" << std::endl;
    return 0;
}
