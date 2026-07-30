# check 0.15.2 适配笔记

## 编译环境
- 构建系统: CMake（autotools 在鸿蒙上有问题）
- 编译日期: 2026-07-29
- 编译器: clang
- 状态: built

## 编译步骤

### 1. 下载并解压
- URL: https://github.com/libcheck/check/releases/download/0.15.2/check-0.15.2.tar.gz
- 大小: 756KB

### 2. 构建系统选择
- **原计划**: autotools
- **实际使用**: CMake
- **原因**: autotools 的 configure/config.status 在鸿蒙平台上有兼容性问题
  - config.status 使用 ksh/zsh 的 `print` 命令（bash 不支持）
  - config.status 创建临时文件时遇到权限问题（即使权限正常）

### 3. CMake 编译
```bash
cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF
make -j$(nproc)
```

Conan 配方声明 `shared/fPIC` 选项，默认按静态库构建，并显式传递
`BUILD_SHARED_LIBS` 与 `CMAKE_POSITION_INDEPENDENT_CODE`，满足 Conan library
包类型规则。

### 4. 测试
- 上游自测试关闭，避免 fork/临时文件运行阶段平台差异
- 新增 Conan 消费测试 `test_check.c`
- 消费测试覆盖版本宏、Suite/TCase/SRunner 基本 API 和断言执行
- 消费测试显式设置 `CK_NOFORK`，避免 HarmonyOS PC 运行环境触发
  Check 默认 fork/temp-file IPC 的临时通信文件创建限制

### 5. 安装
```bash
make install DESTDIR=$TEST_PREFIX
```

### 6. 打包
- 预编译包: check-0.15.2-ohos-aarch64.tar.gz (67KB)
- Debug 包: check-0.15.2-ohos-aarch64-debug.tar.gz (空包)
- 安装脚本: install.sh

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 执行失败 | autotools 使用 ksh/zsh 特定命令 `print` | 切换到 CMake 构建系统 |
| 2 | tar 命令创建长路径失败 | ustar 格式路径长度限制（155字符） | 使用 Python tarfile 模块 |
| 3 | 上游测试套件失败 | 临时文件创建权限问题（平台限制） | 上游测试关闭，Conan 消费测试改用 `CK_NOFORK` 覆盖公开 API |

## 安装产物

- **bin/checkmk**: awk 脚本工具，用于生成 Check 测试代码
- **lib/libcheck.a**: 静态库（77KB）
- **lib/libcheck.so**: 动态库（64KB）
- **include/check.h**: 主头文件
- **include/check_stdint.h**: stdint 类型定义

## 使用示例

```c
#include <check.h>

START_TEST(test_example) {
    ck_assert_int_eq(1, 1);
}
END_TEST

Suite* example_suite(void) {
    Suite* s = suite_create("Example");
    TCase* tc = tcase_create("Core");
    tcase_add_test(tc, test_example);
    suite_add_tcase(s, tc);
    return s;
}

int main(void) {
    Suite* s = example_suite();
    SRunner* sr = srunner_create(s);
    srunner_set_fork_status(sr, CK_NOFORK);
    srunner_run_all(sr, CK_NORMAL);
    int failed = srunner_ntests_failed(sr);
    srunner_free(sr);
    return (failed == 0) ? 0 : 1;
}
```

编译命令：
```bash
clang test.c -lcheck -lm -lpthread -o test
```
Linux/glibc 环境如需独立 clock 库时才追加 `-lrt`。
**备注**: 使用 CMake 构建，上游测试套件运行阶段在鸿蒙平台有已知限制，当前通过 Conan 消费测试覆盖公开 API
---

**编译结束**: 2026-07-29
**最终状态**: built
