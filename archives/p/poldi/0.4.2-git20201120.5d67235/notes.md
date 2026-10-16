# poldi 0.4.2-git20201120.5d67235 适配笔记

## 0. 概览

| 项 | 值 |
|----|----|
| 软件 / 版本 | poldi / 0.4.2-git20201120.5d67235（上游 commit `5d67235`，2020-11-20） |
| 上游源码 | <https://codeload.github.com/gpg/poldi/tar.gz/5d672355f3d27dc1f7e4729be5f098cd2bc9d448> |
| sha256 | `3459ea5287aad02625cfce94be3fd7f15d0695e1e562b7a69648af8d632e7ae9` |
| 构建系统 | autotools（**git 快照：源码内无 `configure`/`Makefile.in`，需自举**） |
| 产物 | `lib/security/pam_poldi.so`（PAM 模块，dlopen 插件；无独立 API、无可执行文件） |
| 状态 | built（conan create 全绿，含上游测试与 test_package 端到端用例） |

## 1. 编译环境

- 平台：HarmonyOS PC (OpenHarmony 6.0) / aarch64 / `aarch64-unknown-linux-ohos`
- 编译器：clang 15.0.4（`/data/service/hnp/bin/clang`），profile `ci/conan/profiles/ohos-aarch64`
- 构建期工具：autoconf 2.72 / m4 1.4.20 / make 4.4.1（HNP），automake 1.18（Conan `tool_requires`）
- 编译日期：2026-10-14

## 2. 编译步骤（实际执行）

```bash
# 0) 依赖预检（W0，全部已发布）
conan download libgpg-error/1.61.1 -r=ohpcd --only-recipe   # 说明：实际按 libgcrypt 钉的 1.55 消费
conan download libgcrypt/1.12.2   -r=ohpcd --only-recipe
conan download libksba/1.8.1      -r=ohpcd --only-recipe
conan download linux-pam/1.7.2    -r=ohpcd --only-recipe

# 1) 语言预检（R47）
python3 scripts/ohc-run.py lang-preflight poldi 0.4.2-git20201120.5d67235 --src <work>
#   → task=cpp, detected=c（源文件 40 个 c:40，主体 100%）→ 兼容族，继续

# 2) 初始化 + 探索性编译（模式 B）
python3 scripts/ohc-run.py init-build poldi 0.4.2-git20201120.5d67235 --url=... --tar tar.gz
#   手工编译（见 §3 的四个平台修复），最终固化进 conanfile.py

# 3) 补丁 + 配方 + 验证
python3 scripts/ohc-run.py refresh-patch --auto poldi 0.4.2-git20201120.5d67235
python3 scripts/ohc-run.py conan-verify poldi 0.4.2-git20201120.5d67235

# 4) 真实构建（与 CI 同源）
conan create archives/p/poldi/0.4.2-git20201120.5d67235 \
  -pr:h=~/.conan2/profiles/ohos-aarch64 -pr:b=~/.conan2/profiles/ohos-aarch64
```

`conan create` 内部的实际构建序列（`conanfile.py build()`）：

```
apply_conandata_patches        # 0001 -lpam / 0002 NLS 守卫
aclocal -I m4 --force          # ← tool_requires(automake) 提供 aclocal/automake
autoheader --force
automake --gnu --add-missing --copy --force-missing
autoconf --force
config.guess 补 HarmonyOS 分支 + __OHOS__ libc 探针（E007）
config.sub aarch64-linux-ohos 断言（automake 1.18 已原生支持）
configure 去 umask 077（E114）
./configure --prefix=/ --with-libgpg-error-prefix=… --with-libgcrypt-prefix=… \
            --with-ksba-prefix=… --disable-nls MAKEINFO=true
make -j1 → make check（上游注册 0 用例）→ 实跑 tests/parse-test、tests/pam-test
make install DESTDIR=<package_folder>
```

## 3. 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Can't locate Automake/Config.pm in @INC (… //share/automake-1.18)` | automake 1.18 包用 `--prefix=/` 安装，`.automake-real` 把 `//share/automake-1.18` 烤进 `@INC` | 该包 `package_info()` 已用 `PERL5LIB` 补上真实路径；配方所有自举命令用 `env="conanbuild"` 执行即生效（E248/automake 包约定） |
| 2 | `config.guess: unable to guess system type`（uname -s = HarmonyOS） | GNU config.guess 无 HarmonyOS 分支（E007） | 自举后给生成的 `config.guess` 插入 HarmonyOS case 与 `__OHOS__` libc 探针（与框架 `patch-autotools-ohos.pl` 等价；automake 1.18 的 config.sub 已支持 `linux-ohos`，配方断言） |
| 3 | 配置阶段报 `can't create ./confXXXXXX/subs1.awk: Permission denied`（来自 config.status） | autoconf 2.72 的 `config.status` 用 `umask 077 && mktemp -d` 建临时目录，HMDFS 上 0700 目录连创建者都不可写（E114） | 自举后把生成的 `configure` 里的 `umask 077` 去掉（模板变更时显式报错，避免静默失效） |
| 4 | `error: call to undeclared function 'dgettext'` | OHOS SDK 的 `<libintl.h>` 是空壳头（无任何函数声明），而 `src/poldi.h` 无条件 `#define _(String) dgettext(...)`；仓库以 `--disable-nls` 构建 | 补丁 0002：NLS 定义加 `ENABLE_NLS` 守卫，关闭 NLS 时 `_()` 退化为原字符串 |
| 5 | `id: command not found`（configure 打印两次） | 设备无 `id(1)`（toybox 未提供） | 仅影响 configure 的 ustar/UID 探测提示，非阻塞，不改 |
| 6 | `makeinfo: inaccessible or not found` → `doc/poldi.info Error 127` | worker 无 Texinfo（`texinfo` 未发布到 ohpcd） | `configure MAKEINFO=true`（既有先例 adplug/2.4）；automake 的 install-info 在文件不存在时跳过安装，包内不产生空 info |
| 7 | 模块被 PAM 栈拒绝：`pam_authenticate → rc=28 PAM_MODULE_UNKNOWN`（`dlopen` 报 `Error relocating … pam_get_item: symbol not found`） | **OHOS 加载器不为 `dlopen` 的模块提供宿主进程已加载库的符号作用域**（模块只在自己的 `DT_NEEDED` 闭包里解析符号；实测：宿主链接提供者无效、`RTLD_GLOBAL` 无效、`LD_PRELOAD` 或模块自带 `DT_NEEDED` 有效） | 补丁 0001：`pam_poldi.so` 显式 `-lpam`（宿主已提供符号的平台上多一个 DT_NEEDED 是无害的 no-op）；test_package 用真实 libpam 宿主端到端复现正/反例 |
| 8 | `make: jobserver mkfifo: …: Operation not permitted`（`make install -j20`） | HMDFS 不支持 FIFO | make 自动退化执行，安装成功；非阻塞 |

### 3.1 关于问题 7 的最小复现（可独立验证平台行为）

```bash
# 宿主库 libhost.so.1 导出 foo_func；插件 use.so 只声明不链接
clang -shared -fPIC -o libhost.so.1 foo.c -Wl,-soname,libhost.so.1
clang -shared -fPIC -o use.so use.c                 # extern int foo_func(void);
clang -o m m.c -L. -lhost -Wl,-rpath,$PWD           # m 调用 foo_func 并 dlopen(use.so)
./m ./use.so        # → dlopen failed: Error relocating …: foo_func: symbol not found
LD_PRELOAD=$PWD/libhost.so.1 ./m ./use.so           # → dlopen OK
```

同一现象用 libpam + PAM 模块复现（本仓 test_package 的控制/正例即此）：

```bash
# 模块未链接 libpam 时：pam_authenticate → rc=28 (Module is unknown)
# 模块链接 libpam 后：  pam_authenticate → rc=7  (Authentication failure，入口已执行)
```

## 4. 源码修改（补丁）

| 补丁 | 文件 | 内容 |
|------|------|------|
| `0001-src-pam-Makefile.am.patch` | `src/pam/Makefile.am` | `pam_poldi.so` 链接命令追加 `-lpam`（附成因注释）：dlopen 模块需要自带 DT_NEEDED libpam |
| `0002-src-poldi.h.patch` | `src/poldi.h` | NLS 段落加 `#ifdef ENABLE_NLS` 守卫，关闭 NLS 时 `_(String)` 退化为 `(String)` |

补丁均由 `ohc-run.py refresh-patch --auto` 生成（`patch_generation` 字段记录 orig/work 指纹）。
平台三元组（config.guess）与 HMDFS umask 两处改动**不落补丁文件**，而是在 `build()` 内对自举产物就地修改：
这些文件在 git 快照里根本不存在，无法作为源码补丁表达（先例：htscodecs/1.6.5）。

## 5. 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| libgpg-error | 1.55 | libgcrypt/1.12.2 精确钉此版本；包内只提供 `bin/gpgrt-config`（无 `gpg-error-config`），配方导出 `GPG_ERROR_CONFIG` 指向它 |
| libgcrypt | 1.12.2 | `AM_PATH_LIBGCRYPT` 经 `bin/libgcrypt-config` |
| libksba | 1.8.1 | X.509 认证方式（缺省启用）；经 `bin/ksba-config` |
| linux-pam | 1.7.2 | PAM 头文件（编译期）+ `libpam.so.0`（模块 DT_NEEDED + 测试宿主） |
| automake（build） | 1.18 | 自举 aclocal/automake |

## 6. 上游测试（R51 三步法）

### 6.1 清点（adaptation 前）

```bash
# tests/ 目录内容
$ ls tests/
ChangeLog  Makefile.am  README  pam-test.c  parse-test.c
# 自动化注册用例数（automake TESTS / check_PROGRAMS）
$ grep -n "TESTS\|check_PROGRAMS" tests/Makefile.am
（无输出）
```

结论：上游有 **2 个测试程序**（`tests/parse-test.c`、`tests/pam-test.c`，注册为 `noinst_PROGRAMS`
—— 即 `make all` 编译但 `make check` 不执行），**automake 自动注册用例 0 个**。
`make check` 在 11 个子目录均输出 `Nothing to be done for 'check'`。

### 6.2 实际运行（conan create 内，OHOS worker 本机执行）

| 用例 | 命令 | 结果 | 日志 |
|------|------|------|------|
| make check（注册用例） | `make check` | 0 用例注册（Nothing to be done） | `reports/conan-create.log` |
| parse-test 选项向量 | `tests/parse-test -f foo.txt -b bar baz rest </dev/null` | PASS（`opt 'foo'=foo.txt`、`opt 'bar'=bar`、`Rest args: baz, rest`） | 同上 |
| parse-test 配置流 | `tests/parse-test </dev/null` | PASS（空配置流无错误） | 同上 |
| pam-test --version | `tests/pam-test --version` | PASS（`pam-test 0.2`） | 同上 |
| pam-test --help | `tests/pam-test --help` | PASS（打印用法） | 同上 |
| pam-test `<service>` 真实认证 | `tests/pam-test poldi` | **SKIP**：需要可写 PAM 配置（OHOS `/etc` 只读，无法建 `/etc/pam.d/<service>`）与 OpenPGP 卡 | — |

### 6.3 如实回填

- 上游自动化注册用例：**0**
- 上游测试程序实跑：**4/4 通过**
- 跳过：**1**（pam-test 真实认证，原因见上；该 PAM 流程由 test_package 的 libpam 宿主用例覆盖）
- 机器可读标记：`HMBS_UPSTREAM_TEST_RESULT={"discovered": 5, "executed": 4, "passed": 4, "failed": 0, "skipped": 1, ...}`

## 7. 鸿蒙特有测试（test_package，rule12：完整消费者用例）

被测产物是 dlopen 插件，没有可链接的 API 也没有可执行文件，因此采用 E345
「ABI 匹配的私有宿主」验证：`test_package/test_pam_module.c` 是**真实 libpam 消费者**，
用 `pam_start_confdir()` 指定自建 pam.d 目录、`pam_authenticate()` 触发真实加载流程。

| 用例 | 期望 | 实测 |
|------|------|------|
| 控制例：service → 不存在的模块 | 必须 `PAM_MODULE_UNKNOWN(28)`（证明检测非空转） | rc=28 ✅ |
| 正例：service → 打包的 `lib/security/pam_poldi.so` | 模块被加载、`pam_sm_authenticate` 真实执行、返回真实 PAM 结果（非模块加载失败码） | rc=7（Authentication failure）✅ |

正例链路完整跑通：消费者 → libpam → `dlopen(pam_poldi.so)` → 模块内部（simpleparse 读配置失败分支 /
libgcrypt、libgpg-error、libksba 运行时闭包）→ 返回 PAM 结果。两个用例都是**实际执行**而非静态断言，
且正是补丁 0001 的直接验证。

## 8. 验证结果

```bash
$ conan create archives/p/poldi/0.4.2-git20201120.5d67235 \
      -pr:h=~/.conan2/profiles/ohos-aarch64 -pr:b=~/.conan2/profiles/ohos-aarch64
...
poldi/0.4.2-git20201120.5d67235: Package '34bab84d4105e0b072a09c6a508abcea1a46c368' built
[case] service=missing pam_authenticate rc=28 (Module is unknown)   → [ok]
[case] service=poldi   pam_authenticate rc=7  (Authentication failure) → [ok]
HMBS_TEST_PACKAGE_RESULT={"discovered": 2, "passedCount": 2, ...}
# 退出码 0
```

包内产物：

```
lib/security/pam_poldi.so      # 125440 B，ELF64/AArch64
licenses/COPYING  licenses/AUTHORS
```

`pam_poldi.so` 的 DT_NEEDED：`libgcrypt.so.20`、`libgpg-error.so.0`、`libksba.so.8`、
`libpam.so.0`（补丁 0001）、`libc.so`。

## 9. 注意事项

- 本包**不含可执行文件**，故无 `commands.json`（R38 判定：纯 dlopen 模块包）。
- `package_type = "shared-library"`，`cpp_info` 的 libdirs/includedirs/bindirs 均为空；
  模块位置经 `runenv_info/buildenv_info` 的 `POLDI_PAM_MODULE_DIR` 暴露给消费者。
- 部署提示：模块按 `/etc/poldi/poldi.conf` 与 `localdb/` 目录读取配置，而 OHOS 的 `/etc` 只读；
  生产部署需把配置随系统镜像发布，或由调用方在受控目录准备配置后以相同路径挂载。

## 10. 对话记录

### 对话 #1（2026-10-14，适配 poldi 0.4.2-git20201120.5d67235）

- **起点**：目标库适配任务，指定上游 <https://github.com/gpg/poldi> 与版本串
  `0.4.2-git20201120.5d67235`。W0 预检：libgpg-error/libgcrypt/libksba/linux-pam 全部已发布；
  R47 语言预检：task=cpp、detected=c（40 个 .c，主体 100%）→ 兼容族，继续。
- **构建形态判定**：源码是 git 快照（无 `configure`/`Makefile.in`），必须自举 autotools；
  HNP 工具链有 autoconf 无 automake → `tool_requires("automake/1.18")`。
- **逐个平台问题的定位与修复**（详见 §3）：自举 → config.guess 识别 OHOS（E007）→
  config.status umask（E114）→ dgettext 无声明（NLS 守卫）→ makeinfo 缺失（MAKEINFO=true）→
  **模块被 libpam 判 PAM_MODULE_UNKNOWN**（dlopen 模块的符号作用域，新增知识草稿
  `knowledge/drafts/DRAFT-24651-ohos-dlopen-module-host-symbol-scope.kv`）。
- **上游测试**：清点出 2 个测试程序、0 个 automake 自动注册用例；实跑 4 项全通过，
  1 项（pam-test 真实认证）因 /etc 只读 + 无卡跳过并说明原因。
- **收尾**：`refresh-patch --auto` 生成 2 个补丁 → `conan-verify` 8 门禁通过 →
  `finish`（W2 原子性 11 文件、W3 本地 CI 含 junk_check 通过、.ci-result.json exit_code=0）→
  test_package 的 libpam 宿主端到端用例 2/2 通过。
- **已知环境注记**：本地 `origin/main`（fork 的 main）落后上游，会让 W3 的
  `git diff origin/main...HEAD` 把上游全部历史算作改动，触发 JC1/JC5/JC6 误报；
  已在本地把该跟踪 ref 对齐到 `official/main` 后再跑 W3（仅本地 ref，不影响提交内容）。
---

**编译结束**: 2026-10-14 14:02
**最终状态**: built
