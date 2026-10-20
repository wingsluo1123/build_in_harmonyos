# nanojsonc 1.3.0 适配笔记

## 编译环境
- 构建系统: cmake (CMakeLists.txt, cmake_minimum_required 3.26)
- 编译日期: 2026-10-19
- 编译器: clang 15.0.4 / clang++
- 状态: built（conan-verify G1-G4 全 PASS，W3 本地 CI 模拟通过）

## 编译步骤

```bash
# 探索编译（.work 源码树，独立构建目录避免覆盖源码自带 build/config.cmake）
cmake -S . -B cmake-build -DCMAKE_INSTALL_PREFIX=... -DBUILD_TESTS=ON -DCMAKE_BUILD_TYPE=Release
cmake --build cmake-build -j2
ctest --test-dir cmake-build --output-on-failure   # 上游 2/2 通过
cmake --install cmake-build --prefix $TEST_PREFIX   # staging 隔离验证

# Conan 配方验证
conan create archives/n/nanojsonc/1.3.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing --user=ohpcd --channel=stable
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游把头文件装成 include/nanojsonc/nanojsonc/parser.h（双嵌套），消费者 #include <nanojsonc/parser.h> 找不到 | CMakeLists `install(DIRECTORY include/ DESTINATION include/${PROJECT_NAME})` 在 include/ 下已有 nanojsonc/ 子目录时再套一层；与 INSTALL_INTERFACE=${CMAKE_INSTALL_INCLUDEDIR} 不一致 | patches/0001-CMakeLists.txt.patch：DESTINATION 改为 ${CMAKE_INSTALL_INCLUDEDIR}（路径 B 草稿 DRAFT-nanojsonc-1.3.0-cmake-install-directory-header-double-nest） |
| 2 | W3 本地 CI L0d 门禁报 stub_test_method | test_package test() 只调 cmake.test()，CI 要求显式 self.run() 证明测试程序被执行（等价命中 E1669） | test_package/conanfile.py test() 改为 self.run(bin_path, env="conanrun") |
| 3 | 重建时 rm -rf build 误删源码自带 build/config.cmake | configure_package_config_file 引用源码目录 build/config.cmake | 从 .orig 恢复；后续用独立 cmake-build 目录 |
| 4 | e2e 首跑挂起 | parse_array 误传对象文档导致解析器无法前进 | e2e 数组解析改传独立数组 JSON；修复后重跑退出码 0 |

## 源码修改

- `patches/0001-CMakeLists.txt.patch`：修复头文件安装路径双嵌套（见上表 #1）

## 依赖版本

- 无第三方依赖（纯 C 静态库，不 malloc）

## 验证结果

```bash
# 上游测试
ctest --test-dir cmake-build --output-on-failure   # 2/2 passed
# test_package（conan create 内执行）
test_nanojsonc   # Passed 0.03s
# 鸿蒙 consumer e2e（真实构建/运行，退出码 0）
./test_nanojsonc_e2e   # events=8 matched=6 errors=0, exit 0
# 负向可失败证明（注入空对象，观测真实非零退出码）
./test_nanojsonc_e2e_neg  # exit 1（matched=2 < 6）
# W3 本地 CI 模拟
build_and_test.sh nanojsonc/1.3.0  # RC=0
```

## 交付物

无独立打包产物（built 状态，未 upload）；归档含 conanfile.py / conandata.yml / test_package / patches / harmonyos_tests（消费者 e2e 源码随 PR 交付）。

## 注意事项

- 源码自带 `build/` 目录（含 config.cmake）不可删除，重建须用独立构建目录
- 知识判定：候选2（L0d stub_test_method）等价命中 E1669 → 路径 A 复用；候选1（头文件安装双嵌套）无等价命中且可跨库复用 → 路径 B，草稿对已创建并审计
