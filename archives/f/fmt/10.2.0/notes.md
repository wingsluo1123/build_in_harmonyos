# fmt 10.2.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-21
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 从 Gitee 镜像下载源码（GitHub 访问超时）
2. 使用 `ohc-run.py init-build` 初始化编译环境
3. 手动配置 CMake，关键参数：
   ```bash
   cmake -DCMAKE_SYSTEM_NAME=Linux \
         -DCMAKE_CXX_COMPILER=clang++ \
         -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
         -DBUILD_SHARED_LIBS=OFF \
         -DFMT_TEST=OFF ..
   ```
4. 编译：`make -j2`
5. Staging 安装：`make install DESTDIR=$TEST_PREFIX`
6. 本地安装：`make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 网络限制 | 使用 Gitee 镜像下载源码 |
| 2 | CMake 无法识别 HarmonyOS 平台 | CMake 缺少 HarmonyOS 平台文件 | 设置 `CMAKE_SYSTEM_NAME=Linux` 绕过平台检测 |
| 3 | CMake 认为编译器 broken | 平台不识别导致 ABI 检测失败 | 设置系统名称为 Linux，编译器正常工作 |

## 源码修改

无源码修改，无需补丁。

## 依赖版本

- cmake 4.1.2
- clang 15.0.4 (aarch64-unknown-linux-ohos)
- GNU Make 4.4.1

## 验证结果

```bash
# 编译测试程序
cat > ~/tmp/test_fmt.cpp << 'EOF'
#include <fmt/format.h>
#include <iostream>
int main() {
    std::string s = fmt::format("Hello {}!", "fmt");
    std::cout << s << std::endl;
    return 0;
}
EOF

# 编译并运行
clang++ -I/storage/Users/currentUser/usr/local/include \
        ~/tmp/test_fmt.cpp \
        /storage/Users/currentUser/usr/local/lib/libfmt.a \
        -o ~/tmp/test_fmt

# 运行结果
$ ~/tmp/test_fmt
Hello fmt!
```

## 测试套件结果

```bash
# 编译测试
cmake -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_CXX_COMPILER=clang++ -DFMT_TEST=ON ..
make -j2
ctest --output-on-failure

# 结果
100% tests passed, 0 tests failed out of 20
Total Test time (real) = 1.57 sec
```

详见 [test-report.md](./reports/test-report.md)

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libfmt.a | 279KB | 静态库 |
| include/fmt/*.h | 616KB total | 头文件集合 |
| lib/cmake/fmt/*.cmake | - | CMake 配置文件 |
| lib/pkgconfig/fmt.pc | - | pkg-config 文件 |

## 注意事项

1. fmt 是静态库，编译为 header-only 可选
2. 需要设置 `CMAKE_SYSTEM_NAME=Linux` 来绕过 HarmonyOS 平台识别问题
3. 建议编译为静态库 (`BUILD_SHARED_LIBS=OFF`) 以避免 ELF 签名问题
---

**编译结束**: 2026-05-21 16:20
**最终状态**: built
