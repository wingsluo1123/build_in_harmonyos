# 老 autotools 项目在 OHOS/hmdfs 上的三连坑（三元组 / config.status 临时 helper / 依赖路径）

> Draft: `DRAFT-AUTOTOOLS-ON-OHOS-HMDFS-CONFIG-STATUS-AND-DEPS-PATHS`
> Stem: `autotools-on-ohos-hmdfs-config-status-and-deps-paths` — pairs with the same-stem `.kv`

## 基本信息

- **严重度**: 2
- **类别**: build-system|autotools|ohos-platform
- **触发工具**: configure|autoconf|make|conan
- **阶段**: configuration|compilation|link

## 错误特征（任一命中即触发本条目）

- `configure: error: cannot guess build type; you must specify one`
- `config.status: error: could not setup config files machinery`
- `./config.status: line 618: ./confXXXXXX/subs1.awk: Permission denied`
- `fatal error: 'alsa/asoundlib.h' file not found`（依赖头没进路径）
- `undefined symbol: snd_mixer_*`（链接到了 sysroot 的 stub 库）

## 根因（三连，同属「老 autotools + 非 glibc 平台 + hmdfs」）

1. **`config.guess` 太老**：随包发布的它认不出本机三元组 ⇒ `configure` 直接失败；
2. **`config.status` 的临时 awk 助手无法执行**：它造临时目录并在其中生成**可执行**的
   `subs1.awk` 来展开 `.in` 文件；这份老 autoconf 用**相对路径**
   ``tmp=`(umask 077 && mktemp -d "./confXXXXXX")` ``（**与 `TMPDIR` 无关** ✗），而构建目录在
   **hmdfs** 上 —— **hmdfs 忽略 chmod** ⇒ 助手没有可执行位 ⇒
   `Permission denied` + `could not setup config files machinery`，看着像"configure 坏了"；
3. **上游只 `AC_CHECK_LIB` 不取 pkg-config**：依赖只被当成 `-lxxx`，其**头目录与库目录都不进
   搜索路径** ⇒ 编译期缺头；链接期甚至可能先命中 **sysroot 里的 stub 库** 而报一串
   `undefined symbol`（很迷惑：库"明明在"）。

## 影响面

一切随包发布 `configure` 的老 autotools 项目（多为 2010–2020 年代的 GNU/第三方工具），
尤其在 OHOS 上、构建目录位于 `/storage`（hmdfs）时；也覆盖"只 AC_CHECK_LIB 不用 pkg-config"
的依赖用法。

## 取证命令

```sh
grep -n 'mktemp -d' configure | head                 # 看临时目录是相对还是绝对
( d=$(mktemp -d); touch $d/a; chmod +x $d/a; test -x $d/a && echo chmod-works || echo chmod-ignored )
df -h . | tail -1                                   # 构建目录在哪个文件系统上
grep -nE 'AC_CHECK_LIB|PKG_CHECK_MODULES' configure.ac
```

## 处置建议（rec）

**approach**: `autotools-on-ohos-triplet-ext2-tempdir-and-explicit-dep-paths`

1. 报 `cannot guess build type` ⇒ 显式 `--build=aarch64-unknown-linux-musl`（本仓约定 musl；
   `--host` 交给交叉 toolchain）；
2. **先测构建目录还讲不讲 chmod**（上面那条 shell 探针）⇒ 不生效就把 config.status 的临时目录
   指到**能行使 chmod 的 ext2 路径**：替换 `configure` 里内嵌的那行
   `mktemp -d "./confXXXXXX"` → `mktemp -d "/data/storage/el2/base/cache/confXXXXXX"`。
   **给 `TMPDIR` 没用** ✗（老 config.status 不看它）；
3. 上游只 `AC_CHECK_LIB` 时，用 `tc.extra_cflags.append("-I<dep>/include")` +
   `tc.extra_ldflags.append("-L<dep>/lib")` 显式给路径
   （`AutotoolsToolchain` **没有** `include_paths` ✗，加了会 `AttributeError`）；
4. 缺完整 gettext 时传 `--disable-nls`（上游 `AM_GNU_GETTEXT` 常是硬前置）。

## 本条的实测落点

**xdemorse/3.6.7（PR !16429）**：上述四条按序全部命中并修好 ——
`--build=…-linux-musl` 解 `cannot guess build type`；把 `configure` 里的临时目录改到
`/data/storage/el2/base/cache` 解 `subs1.awk: Permission denied`（此前误以为 `TMPDIR` 有用，
实测无效 ✗）；显式 `-I/-L` 同时解掉编译期缺 `alsa/asoundlib.h` 与链接期
`undefined symbol: snd_mixer_*`；`--disable-nls` 收尾。最终 `conan create` **EXIT=0** ✓。
