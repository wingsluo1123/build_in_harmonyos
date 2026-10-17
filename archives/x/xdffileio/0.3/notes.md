# xdffileio 0.3 适配笔记

## 编译环境

- 构建系统: autotools (configure + make, libtool)
- 编译日期: 2026-10-10
- 编译器: clang/clang++ (HarmonyOS PC aarch64, OHOS 6.0)
- 状态: built (待真机预检 evidence 轮确认后更新为 published)

## 源码选择

- 上游: https://github.com/mmlabs-mindmaze/xdffileio, 标签 `xdffileio-0.3` (2012-05-02)
- 配方实际下载: Debian orig 包 `xdffileio_0.3.orig.tar.bz2`
  (`https://deb.debian.org/debian/pool/main/x/xdffileio/xdffileio_0.3.orig.tar.bz2`,
  sha256 `9f4615cb320963cb8855993960adb46895c4a614c700bc2e2b79c10d4a7312fb`,
  与 Launchpad/Debian dsc 多方一致)
- 选 Debian orig 而不用 GitHub 标签包的原因: 0.3 是纯 autotools 工程,
  GitHub 标签包只有 `configure.ac` + `autogen.sh`, 需 `gnulib-tool --import`
  + `autoreconf -fi` 自举 (gnulib 源缺失, 设备无 gnulib-tool, 高风险);
  Debian orig 已含生成的 `configure`/`Makefile.in`/gnulib `libgnu`,
  设备可直接 configure (同仓 iselect/ispell 先例同样用 Debian orig)。

## 编译步骤

```bash
conan create archives/x/xdffileio/0.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

配方流程: `get` 解包 → `AutotoolsDeps`/`AutotoolsToolchain` 生成
(`--enable-static --disable-shared`, 默认静态以避开 hmdfs 版本化 .so 符号链接问题)
→ `configure` → `make -j1` → `make check` (上游 6 TESTS, 解析
`tests/test-suite.log` 出 HMBS 标记) → `make install` → 去 `.la` →
持久化 `upstream_test_result.json` 进包内 `res/`。

## 依赖版本

- 无第三方运行时依赖：0.3 的 configure.ac 与全部 .c/.h/.am 源码零引用 mmlib/MM_CHECK_LIB（已对 xdffileio-0.3 标签包实测验证）；mmlib 仅现代 >=1.0 需要，故无 requires、无 vendoring
- 系统库: m, pthread (musl 并入 libc, 链接探测通过)

## 上游测试

- 口径: `tests/Makefile.am` 的 automake TESTS 共 6 个
  (`testbdf/testedf/testgdf1/testgdf2/readcheck` 无条件 + `errorcheck`
  经 `AC_CHECK_FUNC(setrlimit)` 门控; OHOS musl 含 setrlimit, 故注册 6 个),
  方法 `autotools_tests`, 读 `tests/test-suite.log` 的
  `# TOTAL/# PASS/# FAIL/# SKIP/# XFAIL/# XPASS/# ERROR` 汇总块。
- 防假阳性: `build()` 在 `make check` 前断言 4 个 ref fixture
  (`ref128-13-97-50-11-7-1.{bdf,edf,gdf1,gdf2}`) 存在且非空,
  空文件直接抛错, 杜绝空对空比对报 PASS。
- 真机结果待预检 evidence 轮回填 (通过率以预检日志为准, 本轮不猜测)。

## test_package

- `test_xdffileio_api` (15 CHECKs): 经公开 `xdfio.h` 做 BDF 一写一读
  (open/set_conf/add_channel×3/set_chconf/define_arrays/prepare_transfer/write/close/
  文件存在且>256B/重开/get_conf NCHANNEL==3)。
- `test_xdffileio_ohos` (6 CHECKs): 枚举契约 + TMPDIR 可写 + TMPDIR 下 EDF 一写一读非空。
- 合计 21 assertions; `test()` 按进程退出码计数并输出
  `HMBS_TEST_PACKAGE_RESULT`, 另从包内 `res/upstream_test_result.json`
  重发 `HMBS_UPSTREAM_TEST_RESULT` (缓存命中跳过 build 时仍有上游证据)。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Windows 检出 main 报 `invalid path 'archives/g/gama/...patch??'` | 上游某文件名含两个 CR (`0x0D`) 字符, Windows 文件系统非法 | 启用 `sparse-checkout --no-cone`, 排除 `!/archives/g/gama/`, 后用 `reset --mixed` 建索引, 仅按需 checkout 所需路径 |
| 2 | GitHub 标签包需 gnulib 自举 | 0.3 标签包无生成文件, `autogen.sh` 要 `gnulib-tool` | 改用含生成文件的 Debian orig 包, 无需自举 |
| 3 | 老 `config.guess` 可能不识 OHOS/aarch64 | 2012 年 config 脚本无 OHOS 三元组 | 首轮不打补丁, 靠 `AutotoolsToolchain` 显式 `--host/--build`; 若预检报 guess 失败再补 config 补丁 |
| 4 | libtool 版本化 .so 在 hmdfs 缺 `.so` 链接 | hmdfs 拒绝 `ln -s` | 默认静态 (`--enable-static --disable-shared`); 共享构建仍支持, 装后走 `binary-sign-tool` 重签名 |
| 5 | 真机 configure 报 config.guess 无法识别系统、cannot guess build type（2012-02-10 脚本，uname -s=HarmonyOS） | 上游 Debian 包自带 2012 年 config.guess/sub，无 HarmonyOS 分支（E007） | 复用 es-shell/0.9.2 已验证的 OHOS 版 build-aux/config.guess+config.sub（patches/build-aux/ 全文件，export_sources 拷贝 + build() 覆盖），统一传 --build/--host=aarch64-unknown-linux-ohos（相同即原生非交叉），build() 先跑 config.sub/guess 自证再 configure |

## 交付物

| 文件 | 说明 |
|------|------|
| archives/x/xdffileio/0.3/conanfile.py | 主配方 (Autotools + make check + HMBS 标记) |
| archives/x/xdffileio/0.3/conandata.yml | Debian orig URL + sha256 |
| archives/x/xdffileio/0.3/manifest.yaml | 版本 manifest (built, 待预检更新) |
| archives/x/xdffileio/0.3/test_package/ | CMake 消费者测试×2 + MANIFEST.yml |
| .hmbs/pr-body.md | PR 正文草稿 (测试数待 evidence 轮填写) |

## 注意事项

- 本轮未执行 `git commit/push`, 未创建 PR, 未调用 GitCode 写接口 (按任务守则)。
- `git rev-parse --verify HEAD` 成功、无 `index.lock`、`ci/conan/profiles/ohos-aarch64` 存在已确认。
- Windows 工作树为稀疏/部分检出 (`archives/g/gama` 排除); 属地仅新增
  `archives/x/xdffileio/0.3/`, 不含其他库改动, 满足 PR 原子性。
- 认领/PR 身份须用 `momimgya` / 队伍 `干`, 不得沿用示例身份 (HMBS 统一生成正文时使用)。
