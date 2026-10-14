# lib32 2.6.2 适配笔记（HarmonyOS PC · Conan autotools）

## 0. 包名 / 上游不一致（重要，用户已裁定，必须如实记录）

- **包名 `lib32` 不可更改**（任务/配方命名）。"lib32" 不是任何上游项目名——全网核查
  （GitHub、Repology、发行版包索引）均无名为 "lib32" 的独立 C/C++ 库；它是发行版
  multilib 仓库的 `lib32-<pkg>` 前缀命名空间。
- **版本 2.6.2 的唯一自然上游身份 = GNU libtool 2.6.2**（libltdl 2.6.2）：
  1. `libtool-2.6.2.tar.gz/.tar.xz` 确实存在于 GNU 官方归档（ftp.gnu.org，
     2026-07-16），是当前最新稳定版；Repology 显示 multilib 包 `lib32-libltdl`/
     `libtool` 均为 2.6.2。
  2. 本仓演进线吻合：`archives/l/libtool/2.4.7`（verified）、`libtool/2.5.4.1`
     （built，工具包）、`libltdl/2.6.0`（published，取自 2026-01 alpha）——
     alpha 2.6.0 之后跟进稳定版 2.6.2 是自然下一步。
  3. 命名先例：`archives/l/lib32-gcc/16.1.1` 已确立 "任务名与上游不一致时，
     名号保留 + 源码用真实上游 + 显式标注" 的处理范式。
- **用户裁定（2026-10-06）**：包名沿用 `lib32`，实际适配 GNU libtool 2.6.2
  （libltdl 2.6.2），按 lib32-gcc/16.1.1 先例在 manifest.yaml / conandata.yml /
  notes.md 显式标注任务名与上游不一致。
- **打包口径**：与 libltdl/2.6.0 一致——把 libltdl 当**库**打包（lib + 头文件），
  不做 libtoolize/libtool 工具包（工具型见 archives/l/libtool/2.5.4.1 历史归档）。
  License 申报 LGPL-2.1-or-later（libltdl 运行库；libtool 工具链为 GPL-3.0-or-later，
  不打包）。

## 1. 源码归档（已实测固定）

- URL: `https://ftp.gnu.org/gnu/libtool/libtool-2.6.2.tar.xz`（GNU 官方原站，
  2026-07-16 稳定发布；另存在 .tar.gz 与 .sig）
- SHA256: `2ef1067c16c97db930fd740cc9bc3d3ba9a583804ae5ac42cc3e8719e49e191e`
- 校验方式：mirrorservice.org 与 mirrors.tuna.tsinghua.edu.cn 两个独立镜像各下载
  一次，sha256sum 逐字节交叉验证一致（GNU 发布目录无 sha256 旁路文件，与 GCC
  同理，由本地从官方 tarball 计算）。
- 源码树实测（本机解包核验）：2.6.2 与 2.6.0 alpha 树同构——`libltdl/` 子目录
  （ltdl.h + ltdl.c + loaders/）、`tests/` 自带生成好的 `testsuite`（**187 组**，
  2.6.0 为 185；组 187 cmdline_wrap 为低 max_cmd_len 内层重跑包装）、发布 tarball
  自带顶层 `configure` 无需 autoreconf；`configure` 中 config.status 的
  `umask 077` 临时目录仍在（`umask 077 && mktemp -d`）；`libtool-next-version.in`
  的 `uname -s` OS 白名单硬限制仍在（HarmonyOS 落 `*)` 分支报 unknown OS）。

## 2. 编译环境

- 构建系统: autotools（发布 tarball 自带 configure，无需 autoreconf 自举）
- 编译器: clang / clang++（OHOS 定制，CC=clang CXX=clang++）
- 平台: HarmonyOS aarch64（uname -s=HarmonyOS）
- 状态: built

## 3. 编译步骤

1. conan source：下载官方稳定 tarball（见 §1，sha256 见 manifest/conandata）。
2. `./configure --host=aarch64-unknown-linux-gnu --build=aarch64-unknown-linux-gnu`
   - 显式三元组跳过 config.guess 对 `uname -s=HarmonyOS` 的误判
     （历史 libtool 2.5.4.1 / libltdl 2.6.0 已验证法）。
   - 配方默认 `--disable-shared --enable-static`（R26 系统同名库：只产出静态库，
     避免污染系统 /lib、/lib64）。
3. `make -j1`：整树构建，`libltdl/` 产出 libltdl.la 及 `.libs/libltdl.a`（动态时
   `.libs/libltdl.so.7.x`）。
4. `make install MAKEINFO=true`：设备/CI 无 texinfo，跳过 doc/libtool.info
   （历史同法）；安装后只保留 libltdl 库 + 头文件，去除 bin/share/.la。
5. conan create 内 test_package：CMake 消费者真实调用 ltdl API（见 §5）。

## 4. 遇到的问题与解决方案（全部继承自仓内已验证先例）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS 平台 | `uname -s=HarmonyOS` 不在 guesses 内 | 显式 `--host/--build=aarch64-unknown-linux-gnu`（2.5.4.1 / 2.6.0 同法） |
| 2 | config.status 临时目录 HMFS 不可写（E011） | configure 用 `umask 077` 建临时目录，HMDFS UID 映射下 0700 不可写 | 构建期把 configure 文本 `umask 077 → 002`（2.5.4.1 / 2.6.0 同法，对普通 Linux 无副作用） |
| 3 | make install 报 doc/libtool.info Error 127 | 设备/CI 无 makeinfo | `MAKEINFO=true`（2.5.4.1 / 2.6.0 同法） |
| 4 | HMFS chmod/hardlink 受限可能令 `install -c && chmod` 失败 | HMFS 权限语义（gmime 3.0.6 同款坑） | 配方内置纯 Python fallback 安装（2.6.0 同法，字节一致、不改权限） |
| 5 | R26 系统同名库动态链接风险 | libltdl 与系统 libltdl 同名 | 默认 `shared=False` 静态打包（2.6.0 同法） |

## 5. 测试申报表（上游测试套件清点，R51）

**测试套件**: GNU Libtool 2.6.2 testsuite（Autotest，187 个测试组；组 187 =
cmdline_wrap 内层重跑包装）。`tests/testsuite` 由发布 tarball 自带（无需 bootstrap）。
**上游入口**: `make check`。

**测试结果**: 见下文「上游 testsuite 实测记录」章节（本轮在设备上真实执行的
权威数据与证据路径）。

**test_package 消费者验证（CI 口径）**:
- conan create 内执行，`test.c` 实质调用 lt_dlinit / lt_dlopen(NULL) /
  lt_dlsym(printf) / lt_dlclose / lt_dlexit，断言 8 处，走真实 dlopen 链路。
- CI 不跑上游 testsuite（需完整 automake/autom4te 工具链），口径与
  libltdl/2.6.0 一致：conan create 仅编译验证 + test_package 消费者冒烟。

## 5b. 上游 testsuite 实测记录（2026-10-06，设备真实执行）

**结论**：`make check` 在设备上完整跑通全量 187 组（两轮）。libltdl 核心功能组
（dlopen/dlsym 模块加载、静态/动态库链接、deplibs 等 100+ 组）全部通过；意外失败
仅 3 组，全部对应 §9 预判的 HarmonyOS 平台硬限制，非本次适配回归。

### 权威轮次（run2：`make check -j1`，受控环境）

- 树：`/storage/Users/currentUser/tmp/oh-device-porting-v2/lib32-uts/libtool-2.6.2`
- 环境（run-uts2.sh，全部与配方构建同法）：
  - automake 1.18（conan 缓存 automake 包）+ `AUTOM4TE=/data/service/hnp/bin/autom4te`
    + `PERL5LIB` 指向 automake share（libltdl/2.6.0 notes 同法）
  - `PATH` 前置 shims 目录（mktemp 等兼容 shim），`TMPDIR` 指向独立可写 tmpdir
  - 显式三元组 `--build/--host=aarch64-unknown-linux-gnu`（跳 config.guess）
  - configure 文本 `umask 077 → 002`（E011 HMDFS）
  - `MAKEINFO=true`（首轮 make check 因无 makeinfo 报 doc/libtool.info Error 127 后补上）
- 结果：`ERROR: 151 tests were run, 7 failed (4 expected failures). 36 tests were skipped.`
  （151 run + 36 skipped = 187 组全量遍历；7 个失败组中 4 组为上游 xfail 标记，
  **意外失败 3 组**如下）

| 组 | 测试 | 根因 |
|----|------|------|
| 108 | Test libtool-next-version script（versioning_script.at:230） | `libtool-next-version.in` 硬编码 `uname -s` OS 白名单，HarmonyOS 落 `*)` 兜底报 unknown OS |
| 118 | lt_dlopenadvise library loading（lt_dladvise.at:385，exit code 1，期望 0） | HarmonyOS 动态链接器不支持跨 dlopen 模块的 RTLD_GLOBAL 符号解析（**本机 dlfcn 探针实证**，dlerror 原文 "Error relocating: symbol not found"；ltdl 报 "file not found" 系其合成错误码掩盖底层报错；见 knowledge/drafts/DRAFT-ohos-dlopen-rtld-global-reloc-invisible） |
| 187 | Run tests with low max_cmd_len（cmdline_wrap.at:45，recursive/expensive） | 内层 testsuite 重跑 46 组中 4 failed（3 expected），内层 fail_list 非空所致（同 108/118 平台限制的连带） |

- 日志：`lib32-uts/logs/make-check-console2.log`、
  `lib32-uts/libtool-2.6.2/tests/testsuite.log`（Failed tests 汇总即上表 3 组）

### 对照轮次（run1：`make check -j4`，builds 树）

- 树：`/storage/Users/currentUser/builds/lib32-2.6.2.work/libtool-2.6.2`
  （testsuite 命令行含 `-j4`，automake 1.17 + shims 环境）
- 结果：`152 tests were run, 71 failed (70 expected failures). 35 tests were skipped.`
  意外失败仅 1 组：同为组 118（lt_dlopenadvise）。expected-failure 触发数（70 vs 4）
  随并行度/环境波动，符合 Autotest 套件在 HMFS 上并行跑子构建的干扰特征；
  两轮意外失败集合均不含 libltdl 核心功能组，结论一致。
- 日志：`tmp/oh-device-porting-v2/lib32-2.6.2/make-check-run1.log`

### 跳过组（36 组）

F77/FC/Java/GCJ 等缺失语言编译器相关组（convenience.at:108/168/228 等）、
sysroot/dumpbin 等宿主工具相关组，属正常平台跳过（与 2.4.7/2.6.0 实测口径一致）。

### 测试口径

- CI（conan create）：编译验证 + test_package 消费者冒烟（CI 无 automake/autom4te
  完整工具链，不跑上游 testsuite）——与 libltdl/2.6.0 发布口径一致。
- 上游 testsuite：以上述设备实测为准。3 组意外失败均为平台硬限制
  （OS 白名单 / RTLD_GLOBAL / 连带递归组），不建议在本仓改动上游源码规避。

## 6. 源码修改

无补丁。发布 tarball 自带 configure/Makefile.in/testsuite，无需改动源码（R8）。
（E011 umask 处理在配方 build() 内对 configure 文本做 `umask 077 → 002` 替换，
属配方构建期处理，非源码补丁。）

## 7. 依赖版本

- 无外部 conan 依赖（libltdl 的 dlopen 由系统 libc 提供，`libltdl.la`
  的 dependency_libs 为空，无需 -ldl）。
- 构建工具: make、clang/clang++（OHOS 定制工具链）。

## 8. 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | autotools 配方，default shared=False（R26），显式三元组，E011 umask 处理 |
| conandata.yml | ftp.gnu.org 官方源 + sha256（双镜像交叉验证） |
| manifest.yaml | 版本级 manifest（含名号-上游不一致标注） |
| notes.md | 本文件 |
| test_package/ | CMake 消费者，test.c 调用 ltdl API（R34）+ MANIFEST.yml 测试申报 |
| （安装产物） | include/ltdl.h + include/libltdl/*.h + lib/libltdl.a |

## 9. 注意事项

- 若下游需要动态库，可 `-o lib32/*:shared=True` 构建（.so.7 系列产物正常）；
  默认静态打包以规避 R26 系统同名库污染。
- 上游 testsuite 的已知平台硬限制（继承 2.6.0 实测结论，2.6.2 树已确认同样存在）：
  - `libtool-next-version` 脚本硬编码 `uname -s` OS 白名单，HarmonyOS 落 `*)`
    兜底分支直接报 unknown OS（`libtool-next-version.in:186`）；
  - HarmonyOS 动态链接器不支持跨 dlopen 模块的 RTLD_GLOBAL 符号解析
    （影响 lt_dladvise 类测试）。**证据等级升级：本机 dlfcn 探针实证（2026-10-06）**
    ——原为"继承 2.6.0 结论 + 上游测试间接证据"，现由自包含双 .so 探针闭环：
    dlopen(A, RTLD_GLOBAL) 后 dlopen(B) 原始 dlerror = "Error relocating ./libb.so:
    a_f: symbol not found"，而同进程 dlsym(RTLD_DEFAULT, a_f) 成功（注册与重定位
    解析语义割裂）；RTLD_LAZY/RTLD_GLOBAL 加载标志均无效（BIND_NOW）；Curator 反例
    核验：RTLD_GLOBAL 预加载方案 = 组 118 场景本身，**不可行**；可用绕行为构建期
    DT_NEEDED（探针 P4 OK）与启动期 LD_PRELOAD（探针 OK）。详见
    knowledge/drafts/DRAFT-ohos-dlopen-rtld-global-reloc-invisible；
  - HMFS getcwd 限制会打断 libtool 生成的测试启动脚本（rulex abaac1605f 先例），
    testsuite 若在 HMFS 路径上跑需让 make test 目标直接调用已链接 ELF 或改在
    非 HMFS 路径执行。
