# cppzmq 4.10.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-26
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 类型: header-only C++ 库
- 状态: built

## 编译步骤

1. 安装依赖 zeromq 4.3.5（cmake 编译 + make install）
2. init-build cppzmq 4.10.0 --url=https://github.com/zeromq/cppzmq/archive/refs/tags/v4.10.0.tar.gz
3. cmake configure with `-DCPPZMQ_BUILD_TESTS=OFF`（header-only库禁用测试）
4. make install DESTDIR=$TEST_PREFIX（staging 安装）
5. make install（直接安装到 $DEFAULT_PREFIX）
6. pkg-config 验证 cppzmq 4.10.0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书下载失败 | GitHub SSL证书验证失败 | 设置 SSL_CERT_FILE=/storage/Users/currentUser/usr/local/ssl/cert.pem |
| 2 | Savannah URL 404 | cppzmq-4.10.0不在Savannah镜像 | 使用GitHub archive URL |
| 3 | libzmq 依赖缺失 | zeromq未安装到$DEFAULT_PREFIX | 手动编译安装zeromq 4.3.5 (cmake + make install) |
| 4 | cppzmq测试构建耗时过长 | catch2 FetchContent下载 | 使用 -DCPPZMQ_BUILD_TESTS=OFF 禁用测试 |

## 依赖版本

| 依赖 | 版本 |
|------|------|
| zeromq (libzmq) | 4.3.5 |

## 验证结果

```bash
pkg-config --modversion cppzmq  # 4.10.0
pkg-config --modversion libzmq   # 4.3.5
ls /storage/Users/currentUser/usr/local/include/zmq.hpp        # 存在
ls /storage/Users/currentUser/usr/local/include/zmq_addon.hpp  # 存在
```

## make check
- make check: 跳过（header-only 库无 make check 目标）
- 原因: 使用 -DCPPZMQ_BUILD_TESTS=OFF 禁用测试构建

## 上游测试（Catch2 suite）

上游 `tests/` 使用 Catch2（FetchContent 拉取 v2.13.9），共 102 个用例。本包 conan 配方为
header-only（`-DCPPZMQ_BUILD_TESTS=OFF`），故上游测试在**配方之外的独立构建**中执行，二者分开报告：

- 构建: `cmake -DCPPZMQ_BUILD_TESTS=ON ..`（FetchContent 拉取 Catch2 v2.13.9）
- 运行环境: OHOS aarch64（本机原生 clang 15.0.4，产出 aarch64/musl ELF）
- 结果: `100% tests passed, 0 tests failed out of 102`（102 passed / 0 failed / 0 skipped）
- 证据日志: `reports/upstream-ctest.log`

## 鸿蒙专用消费者测试（rule12）

`test_package/test_cppzmq_ohos.cpp` 为新增的 HarmonyOS 特有消费者用例，**非断言**（`assert()` 调用数为 0），
以显式返回值检查 + 非零退出码判定：真实执行 inproc REQ/REP 往返 + multipart 编解码闭环
（构造输入 → 调用 cppzmq/libzmq 业务 API → 产出结果 → 校验内容）。由 `test_package/CMakeLists.txt`
构建并在 `test_package/conanfile.py` 的 `test()` 中以 `./test_cppzmq_ohos` 执行。

## G0 干净构建验证
- G0 结果: ⚠️ 不适用（clean-verify 脚本仅支持 autotools 项目，cppzmq 为 cmake 项目）
- 手动验证: ✅ cmake configure + make install 成功通过
- 结论: header-only库无需从源码重新编译验证

### 对话 #1 [2026-10-11]

- 问题: 本包配方（cppzmq 4.10.0）已由上游合入，本次需要在既有包上补充 HarmonyOS 特有消费者用例，并确认不改动 conanfile.py/conandata.yml 时无需按 R37 递增版本号
- 操作: 从真实上游 official/main 重建分支；新增 test_package/test_cppzmq_ohos.cpp 并接入 CMakeLists.txt 与 test_package/conanfile.py；比对制品仓已有 recipe 的 conanfile.py/conandata.yml 逐字节一致（L0j = recipe unchanged）
- 结果: 鸿蒙消费者用例端到端通过；R37 判定无需后缀；上游 Catch2 套件 102/102 通过并留存日志

## 注意事项

- cppzmq 是 header-only 库，无二进制产物（无.so/.a）
- 头文件安装到 include/ 而非 include/cppzmq/（上游默认行为）
- 必须先安装 zeromq (libzmq) 才能使用 cppzmq
---

**编译结束**: 2026-10-11 23:27
**最终状态**: built
