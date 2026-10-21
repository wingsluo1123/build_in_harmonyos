# karchive5 5.116.0.1 适配笔记

## 为什么是 5.116.0.1（R37 版本递增）

ohpcd 已有 karchive5/5.116.0，但其配方在 requirements() 里写了：

```python
self.requires("zlib/1.3.1.1", force=True)
```

目的只是绕过「zlib/1.3.1 的 libz.a 非 PIC，链共享库失败」这一条链接错误。
副作用是整条依赖图被 force 到 zlib/1.3.1.1，而 qt5-qtbase/5.15.2.2 的
已发布二进制 package id 是按 zlib/1.3.1 算出来的；一旦换版本，Conan 认为
qtbase 需要重建，而 ohos-aarch64 profile 没有 tools.build:compiler_executables，
源码重建直接失败（kio5 首枪实测：`qt5-qtbase/5.15.2.2:86854b… missing` →
`Invalid configuration: qt5-qtbase requires c and cpp compiler executables`）。

按 R37（配方变更必须递增版本）发出 5.116.0.1：上游源码不变，只改配方
（另加一个只影响 autotests/karchivetest.cpp 的 portability 补丁，见「源码
核验」）：

1. `self.requires("zlib/1.3.1")`（与 qt5-qtbase 的 pin 一致，不动 qtbase 的
   二进制）；
2. `generate()` 增加 `CMAKE_SHARED_LINKER_FLAGS = "-Wl,--exclude-libs,ALL"`，
   把静态归档里的符号从共享库动态符号表里隐藏，非 PIC 的 libz.a 即可正常
   链入（OHOS clang 15 本机实测，见下）。

## 源码核验

- 上游：`karchive-5.116.0.tar.xz`（5.116 已归档到 Attic）。
- 官方源 + 镜像列表（bfsu/ustc/nju + download.kde.org 兜底）见 conandata.yml。
- 本地实测 sha256：
  `1663e3c970b84063ece7f28548a87c97bc7592e79da0a0afaa4f6354f8dea30a`
  与 conandata.yml 一致；上游 `.sha256` 同值（5.116.0 历史认证）。
- 补丁：仅 0001-karchivetest-symlink-eacces.patch（portability，只影响
  autotests/karchivetest.cpp）。OHOS 应用沙箱拒绝 `symlink()`
  （EACCES/errno 13，$HOME、应用数据目录实测均如此），上游
  initTestCase() 在 symlink 失败时 `QVERIFY(false)` 会直接判整个测试程序
  失败。补丁把 symlink 可用性改为运行期探测：失败时打印告警并把
  「symlink 相关校验」（归档内 z/test3_symlink 条目、copyTo 的 readlink、
  tar/zip/7z 列表条目与计数）整体跳过；其余归档读写校验全部照常执行，
  不掩盖任何非 symlink 的行为退化。

## 依赖与 zlib 冲突

| 依赖 | 角色 | 说明 |
|---|---|---|
| qt5-qtbase/5.15.2.2 | requires | Qt5Core；已发布二进制绑定 zlib/1.3.1 |
| zlib/1.3.1 | requires | 上游 `find_package(ZLIB)`（TYPE REQUIRED），libz.a 非 PIC |
| bzip2/1.0.8 | requires | 上游 `find_package(BZip2)`（RECOMMENDED），.bz2 过滤器 |
| xz/5.6.2 | requires | 可选 LibLZMA（k7zip/kxz） |
| zstd/1.5.7 | requires | 可选 libzstd（pkg-config 探测，配方内置 .pc 重定位包装） |
| ecm/6.26.0 | tool_requires | `find_package(ECM 5.116.0 NO_MODULE)` 最小版本语义 |

非 PIC 链接墙的实证与解法（OHOS clang 15 真机）：

- 直接链：`relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against
  symbol 'z_errmsg'; recompile with -fPIC`（zlib/1.3.1 的 libz.a）；
- 加 `-Wl,--exclude-libs,ALL`：三个探针共享库 p1/p2/p3 全部链接成功，
  运行期 gzip 往返正常；
- 因此不需要重建 zlib，也不需要把 qtbase 拖入源码重建。

## 构建与测试

- `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
- BUILD_TESTING=ON；build() 末尾 `_run_upstream_tests()` 执行 ctest：
  - autotests/：karchivetest, kfiltertest, deprecatedtest,
    klimitediodevicetest, kcompressiondevicetest（Qt5Network 可用时）；
  - tests/ 下的 kartest/ktartest/krcctest/kziptest/k7ziptest 会被构建，
    但上游只用 `ecm_mark_as_test()` 标记（该宏只设置 EXCLUDE_FROM_ALL 并
    加入 buildtests 目标，不调用 add_test()），所以**不进入 CTest 清单**；
  - 因此 ctest 实际注册 5 项（已在本机真机 ctest 输出核实：
    `1/5 karchivetest … 5/5 kcompressiondevicetest`）。
- karchivetest 的 symlink 校验在 OHOS 沙箱下按上面的补丁跳过（运行期探测
  EACCES），其余用例照常执行。
- 测试期 MIME 库：设备系统 MIME 库缺 zstd 压缩 tar 条目，KTar 会按
  application/octet-stream 写出未压缩 tar，导致 karchivetest 的 .tar.zst
  行失败；配方在 build 树内生成测试专用 shared-mime-info 树并经
  XDG_DATA_DIRS 注入（karchive 6.26.0 同款先例，5.116.0 配方已内置）。
- test_package：KTar 往返 + KZip Deflate 往返 + KCompressionDevice GZip
  往返（gzip 魔数 1f 8b + 内容比对），是「非 PIC libz.a 链接正确」的运行期
  证据。

## 真机执行记录（本地预验证）

见本目录 reports/（构建日志摘要与 ctest/test_package 结果在 CI 回填后补全）。

## 交付物清单

- conanfile.py / conandata.yml / manifest.yaml / notes.md
- test_package/{conanfile.py,CMakeLists.txt,test.cpp,MANIFEST.yml}
- reports/（脱敏日志摘要）
