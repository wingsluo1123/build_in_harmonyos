# mbtserver 0.17 适配笔记

## 编译环境
- 构建系统: custom（上游 autotools，OHOS 上手动编译，见下）
- 编译日期: 2026-10-14（首轮工作树，待 HMBS 真机预检回填实测）
- 编译器: clang/clang++
- 状态: built（待真机 rule4 门禁确认；确认前不提交、不建 PR）

## 上游信息

- 上游仓库: https://github.com/LanguageMachines/mbtserver
- 上游版本: v0.17（tag commit 2d04204dc315dc6a52d6251301c0064003ad4615）
- 源码归档: `https://github.com/LanguageMachines/mbtserver/archive/refs/tags/v0.17.tar.gz`
  （308642 字节，sha256 见 conandata.yml，实拉官方归档计算）
- 许可证: GPL-3.0-only
- 内容: MBT 基于记忆的词性标注服务器（TCP/JSON 双协议），C++17，
  产物为静态库 `libmbtserver.a` + 可执行文件 `bin/mbtserver`。
- 同组织已合入配方: archives/t/timbl/6.1（W0b 历史经验来源，做法对齐）

## 编译步骤

上游是 GNU Autotools 项目，但发布归档内**没有预生成的 configure 脚本**
（仅 configure.ac + bootstrap.sh），而 OHOS 侧无 automake/autoreconf，
无法走标准 `./configure` 流程。沿用同组织 timbl/6.1 已验证的做法：

1. `conanfile.py._generate_config_h()` 手写最小 config.h。
   审计结论：全源码树唯一用到的 config.h 宏是 `VERSION`
  （`src/MbtServerBase.cxx:116` 打印版本号），无需模拟其他探测宏。
2. 从 AutotoolsToolchain 生成的 `conanbuild.conf` 读取 CXX/CXXFLAGS/
   LDFLAGS/AR（R33：不依赖裸 shell 环境变量）。
3. 以 `-std=c++17`（上游 `src/Makefile.am` 的 `AM_CXXFLAGS` 要求）直接编译
   两个库源文件（`libmbtserver_la_SOURCES`）：
   `MbtServerBase.cxx`、`MbtJSONServerBase.cxx`，
   头文件搜索路径 = 自身 `include/` + 各依赖的 `cpp_info.includedirs`。
4. `llvm-ar rcs` 打包 `libmbtserver.a`。
5. 编译 `MbtServer.cxx`（`bin_PROGRAMS` 唯一目标）并链接
   `-lmbtserver` + 依赖库（静态链接顺序：mbt → timbl → ticcutils → icu，
   与上游 configure.ac 的 LIBS 累积顺序一致）+ `-lpthread`
  （上游 `AX_PTHREAD`，R32 口径 `os in ("Linux", "OHOS")` 才加）。

依赖的聚合全部取自各依赖包的 `cpp_info`（includedirs/libdirs/libs/
system_libs/defines/cxxflags），不调用 pkg-config，不读 shell 环境。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 configure 脚本，无法走 Autotools 流程 | 发布归档仅含 configure.ac；OHOS 无 autoreconf | 手动编译（timbl/6.1 先例），config.h 仅定义 VERSION |
| 2 | 远端缺失依赖：真机预检 `ticcutils/0.38 not resolved`，timbl/7.0、mbt/3.13 同样无远端发布（仓库内仅 timbl/6.1，不满足 >= 6.4.14） | 三个依赖短期无独立适配（R36） | 配方内私有静态子构建并合包（serf/1.3.10 先例）：conandata 新增三者官方源码条目（哈希不变），source 解包到 `_vendored/`，build 自底向上（ticcutils 0.38 → timbl 7.0 → mbt 3.13）编译静态归档，package 合入 4 个 .a 与全部公共头（含 ticcutils/json.hpp），cpp_info.libs 按被依赖优先排序；远端 requires 仅保留有发布证据的 icu/76.1、libxml2/2.15.3、zlib/1.3.2、bzip2/1.0.8.2 |
| 3 | 公共头声明了未定义的 `VersionInfo(bool)` | 上游只在 `MbtServerBase.h:43` 声明，两个 .cxx 均无定义（全树 grep 确认） | 消费者测试不引用它，改用 `StartServer`/`StartJSONServer` 取址做链接验证 |
| 4 | 服务器二进制直接运行会常驻阻塞 | `StartServer` 无配置时才退出，正常启动后 `server.Run()` 常驻 | 冒烟只走代码已证明的立即退出路径：`-h/--help` 打印用法并 `exit(0)`、`-V/--version` 直接 `exit(0)`（`MbtServerBase.cxx` 的 `StartServer` 前两段分支） |
| 5 | 真机 `ticcutils/Unicode.cxx: unicode/ustream.h file not found` | icu/76.1 以 `--disable-icuio` 构建（见 archives/i/icu/76.1/conanfile.py），包内无 icu-io 头与库；ticcutils 0.38 的 configure.ac 硬要求 `icu-uc + icu-io`，`Unicode.h:41` 必含该头（`Unicode.cxx` 的 `cerr << UnicodeString` 调试输出与 `UniFilter` 流输出所用算子） | 配方内头文件垫片（非上游补丁）：`build()` 在构建目录生成 `_icuio_shim/unicode/ustream.h`，以 icuuc 公共 API（`toUTF8String`/`fromUTF8`，ticcutils 文件编码即 UTF-8）内联实现 `<<`/`>>`，`-I` 置首后参与 ticcutils 私有静态构建；无需额外链接库（`cpp_info` 仍为 icuuc/i18n/data），不改上游源码 |
| 6 | 真机 test_package `timbl/StringOps.h: unicode/unistr.h file not found`（主包已构建成功） | 合包头（vendored timbl/ticcutils）向消费者暴露了 `unicode/unistr.h` 等远端依赖头，但 `package_info` 未声明 `requires` 传递，且 CMakeDeps 不为传递依赖展开 include（dwarves/1.30 先例），test 仅 `requires(mbtserver)` 故无 ICU 包含路径 | `package_info.requires` 补 `icu::icu`/`libxml2::libxml2`/`zlib::zlib`/`bzip2::bzip2`；test_package 显式 `requires` 四个远端包并在 `CMakeLists.txt` 逐一 `find_package` + 链接（含 `LibXml2::LibXml2` 拼写与 zlib/bzip2 双拼写探测及 libxml2 嵌套 include 兜底） |
| 7 | 真机 test_package `ticcutils/Unicode.h: unicode/ustream.h file not found`（主包构建成功、unistr 已通） | 前轮 `_icuio_shim` 只写在构建目录供主包编译，未随包发布；消费者编 `test_mbtserver.cxx` 经 `TimblAPI.h→Instance.h→Unicode.h:41` 仍需该头 | `package()` 内幂等重建垫片并 `copy` 至 `include/unicode/ustream.h` 随包发布；消费者 `-I<mbtserver>/include` 解析垫片，其内嵌 `unicode/unistr.h` 仍回 icu 包解析，无需额外链接库 |

## 源码修改

无补丁。全部适配收敛在 `conanfile.py` 内（编译参数、config.h 生成、
依赖聚合），`patches_applied` 为空。

## 依赖版本

| 依赖 | 要求来源 | 本配方引用 |
|------|----------|------------|
| ticcutils | configure.ac `ticcutils >= 0.36` | 内置私有构建 0.38（官方 tag v0.38，见 conandata vendored_sources） |
| timbl | configure.ac `timbl >= 6.4.14` | 内置私有构建 7.0（官方 tag v7.0） |
| mbt | configure.ac `mbt >= 3.5` | 内置私有构建 3.13（官方 tag v3.13） |
| icu | configure.ac `icu-uc >= 50 icu-io` | icu/76.1（远端依赖，有发布证据） |
| libxml2 | ticcutils XMLtools 所需 `libxml-2.0 >= 2.6.16` | libxml2/2.15.3（远端依赖） |
| zlib/bzip2 | ticcutils zipper 所需 `zlib.h/bzlib.h` | zlib/1.3.2、bzip2/1.0.8.2（远端依赖） |

## 验证结果

首轮仅完成未提交工作树（按任务要求，真机 rule4 门禁通过前不提交、不建 PR）。
待 HMBS 真机预检回填：

```bash
conan create archives/m/mbtserver/0.17 -pr=ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# 预期：2 个库源文件编译、libmbtserver.a、mbtserver 二进制、
# test_package 3 项检查（API 链接 1 + --help 退出码与用法横幅 1 + --version 1）
```

前置条件（R36）：ticcutils 0.38、timbl 7.0、mbt 3.13 已由本配方在内部私有构建（见上表 #2），
不再等待三者独立适配发布；远端仅需 icu/76.1、libxml2/2.15.3、zlib/1.3.2、bzip2/1.0.8.2（均有合入记录）。

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libmbtserver.a | 静态库（含 MbtServerClass / MbtJSONServerClass 实现） |
| bin/mbtserver | 命令行服务器（含 --help/--version 立即退出路径） |
| include/mbtserver/MbtServerBase.h | 唯一公共头 |

## 注意事项

- 本配方 `package_type = "library"` 但同时产出 `bin/`（与 timbl/6.1 一致），
  故软件级目录配有 `commands.json`（R38，type tool）。
- 测试二进制与 mbtserver 均为全静态链接，test_package 的 `self.run` 用
  `env=""`（icu/76.1 的 E064 先例：OHOS 上 source conan 脚本包装曾致
  SIGSEGV；静态产物不需要 conanrun 的 loader 路径）。
- `mbtserver --help` 的用法横幅断言 `"usage:"` 子串（源码 `usage()` 函数
  原文 `usage:  mbtserver --config=config-file`），非空输出校验，防
  “空跑也报 PASS”类假阳性。
- 本机 Windows 仅做配方编写与源码审计；编译验证一律走 HMBS 真机预检，
  本机未运行 conan。
