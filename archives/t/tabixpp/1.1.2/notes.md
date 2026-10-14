# tabixpp 1.1.2 适配笔记

## 编译环境
- 构建系统: makefile（仓库根 raw Makefile，唯一构建入口）
- 编译日期: 2026-09-26
- 编译器: clang/clang++
- 状态: built（待真机 rule4 门禁验证后由 HMBS 提交）

## 编译步骤

1. `get()` 拉取 `https://github.com/vcflib/tabixpp/archive/refs/tags/v1.1.2.tar.gz`（sha256 见 conandata.yml），`strip_root=True`。
2. 打补丁 `patches/0001-tabixpp-link-external-htslib.patch`（仅改 `tabix++` 链接行）。
3. `make` 时覆盖变量（Makefile 中均为 `?=`，命令行优先）：
   `make CC="<hnp clang>" CXX="<hnp clang++>" AR="<llvm-ar>" INCLUDES="-I<htslib include>" LIBPATH="-L. -L<htslib lib> -L<transitive dep libs>" HTS_HEADERS="" HTS_LIB="" -j1 all`
4. 上游测试：`./tabix++ test/vcf_file.vcf.gz > upstream_test.log 2>&1 && cat upstream_test.log`，断言输出非空且至少含 1 个数据行，再打印 `HMBS_UPSTREAM_TEST_RESULT`（discovered=1，计数来自日志行数与字节数，无字符串数数推导）。
5. 打包不用上游 `make install`（其 `install -c libtabix.a libtabix.so.1 <dir>` 多源形式被 HarmonyOS install shim 以 Error 64 拒绝），改用 conan `copy()` 直拷 `tabix++`→`bin/`、`*.hpp`→`include/`、`libtabix.a`/`libtabix.so*`→`lib/`，`LICENSE`→`licenses/`，并对包内 `bin/tabix++` 最佳努力自签。
6. test_package 用 CMake 构建 `test_tabixpp.cpp`，链接 `tabixpp::tabixpp` + `htslib::htslib`，运行时用 BGZF/tbx_index_build C API 现场制作 3 记录 VCF 夹具并驱动 Tabix API（不依赖 bgzip/tabix CLI：远端 htslib 二进制包未提供工具）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 发布 tarball 内 `htslib/` 为空目录 | htslib 是 git submodule，GitHub tag 归档不收录子模块内容 | 不用子模块，`requires htslib/1.24-r0`（transitive_headers/libs），`INCLUDES/LIBPATH` 指向 Conan 包，`HTS_HEADERS/HTS_LIB` 置空 |
| 2 | 上游链接 `-lcurl -lbz2` 在 OHOS 失败 | htslib/1.24-r0 以 `--disable-libcurl --disable-bz2` 构建，无这两家库 | 补丁改链接行为 `-lhts -lpthread -lm -lz -llzma -ldeflate`（静态 libhts.a 需要 libdeflate） |
| 3 | 上游测试只有一个 `make test` 入口 | 无 ctest/gtest 注册表 | 计数口径取 auto（单个可解析命令），总数 1，日志非空断言防“空文件比空文件”式假通过 |
| 4 | 真机 `build()` 上游测试报 Error 127 且空错误信息 | 三个叠加：① `&& cat` 使 CLI 失败时日志不打印、根因不可见；② 链接偏好共享 libhts 时运行时缺 `LD_LIBRARY_PATH`；③ OHOS 未自签名的 ELF 可能被拒执行 | `_run_upstream_test` 改为 `; rc=$?; cat; exit $rc` 常显日志、异常也落 `HMBS_UPSTREAM_TEST_RESULT`；运行前注入全部依赖 `libdirs` 到 `LD_LIBRARY_PATH`；`binary-sign-tool` 最佳努力自签（缺工具仅警告）；非零退出即使有输出也判失败 |

## 源码修改

- `patches/0001-tabixpp-link-external-htslib.patch`：`Makefile` 的 `tabix++` 链接行去掉 `-lcurl -lbz2`、增加 `-ldeflate`；不碰测试逻辑与平台宏（无新增 `__OHOS__`）。

## 依赖版本

- `htslib/1.24-r0`（及其传递依赖 `zlib/1.3.1`、`xz/5.6.2`、`libdeflate/1.25`）

## 验证结果

待 HMBS 真机预检（conan create 全量：上游 `make test` + test_package `./test_tabixpp` + 双 HMBS 标记）。本轮不猜测数字，PR 正文表格留待 evidence 轮回填。

## 注意事项

- 本机 Windows 不运行 conan（规范要求真机验证）；`build()` 内的测试分支用 `can_run` 守卫，交叉场景仅提示、不伪造通过。
- `tabix.hpp` 透出 `htslib/*.h` 头，消费者需 `htslib::htslib` 联动（recipe 已声明 transitive）。
- Windows 检出注意：仓库 `archives/l/libXext` 与 `archives/l/libxext` 大小写冲突、`archives/g/gama` 有含 CR 文件名，本机用 sparse-checkout 排除冲突项；与本 PR 无关。
