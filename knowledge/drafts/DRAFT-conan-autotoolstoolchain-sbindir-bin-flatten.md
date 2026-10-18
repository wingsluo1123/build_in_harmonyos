# DRAFT: Conan AutotoolsToolchain 的 sbindir 静默 bin 展平——sbin_PROGRAMS 工具落 bin/，消费断言应按包内事实对齐

## 现象

libxfce4util 4.20.0 适配中：configure、编译、库链接全部通过，`make check` 与库产物
`libxfce4util.so.7` 正常；失败发生在 conan test_package 的断言上——

```
ERROR: libxfce4util/4.20.0 (test package): Error in test() method, line 60
	assert os.path.isfile(kiosk), "missing installed xfce4-kiosk-query"
AssertionError: missing installed xfce4-kiosk-query
```

而包里其实有这个工具，只是不在断言查的 `sbin/`，在 `bin/`（CI run6 日志 719-721 行）。

## 根因

Conan 2 `AutotoolsToolchain.generate()` 无条件注入全组 GNU 目录参数，其中
**bindir/sbindir/libexecdir 一律展平为 `${prefix}/bin`**。两个独立实证（同一次通过构建）：

1. 注入实录（CI run8 日志 190 行）：

```
RUN: ".../configure" --enable-shared --disable-static --prefix=/ \
  '--bindir=${prefix}/bin' '--sbindir=${prefix}/bin' '--libdir=${prefix}/lib' \
  '--includedir=${prefix}/include' '--oldincludedir=${prefix}/include' ...
```

   generators 目录的 `conanbuild.conf` 同样 grep 得出 `--sbindir=${prefix}/bin`。

2. 落盘实录（CI run8 日志 603 行）：

```
libtool: install: /system/bin/install -c .libs/xfce4-kiosk-query .../p//bin/xfce4-kiosk-query
```

上游 `xfce4-kiosk-query/Makefile.am` 声明 `sbin_PROGRAMS`，autoconf configure 认识并静默
接受全部注入参数，于是 sbindir 指向 `bin/`、libtool 照装——**构建期零告警**，缺陷潜伏到
验证期才被"按上游 sbin 语义写的消费断言"引爆。

## 与同族条目的形态区分（dedup 对照）

| 条目 | 工具链 | 注入参数命运 | 首报 phase | 失败签名 |
|------|--------|--------------|-----------|----------|
| **本条** | AutotoolsToolchain | autoconf configure 全盘接受，布局静默改变 | 验证期（test_package 断言） | `AssertionError: missing installed ...` |
| E2167 | AutotoolsToolchain | 手写 configure 白名单拒绝 | configure 期（当轮失败） | `Unknown option` |
| E545 | AutotoolsToolchain | 1994 版 configure 只认极少数选项 | configure 期（当轮失败） | `invalid option` |
| retro-gtk 1.0.2 | MesonToolchain | libexecdir=bin 归并进 machine file | 运行期（路径常量失配） | helper 不在 libexec/、RETRO_RUNNER_PATH 失配 |
| schroot 1.6.13 | CMakeToolchain | CMAKE_INSTALL_LIBEXECDIR=bin | 安装期 | bin/ 内同名可执行冲突 |

同一"conan 注入 GNU 目录参数"机理，四种工具链、三个失败 phase——诊断先看失败发生在
configure/安装/验证哪一段，再对号入座。

## 修复（rec）

按包内事实对齐配方声明面，不与工具链默认对抗：

```python
# conanfile.py package_info()
self.cpp_info.bindirs = ["bin"]          # 而非上游语义的 "sbin"

# test_package/conanfile.py test()
kiosk = os.path.join(pkg_folder, "bin", "xfce4-kiosk-query")
```

并在 notes/README 记录"上游 sbin_PROGRAMS 语义在 conan 包内被展平到 bin/"。这是 conan
生态的既定布局惯例，下游经 `cpp_info` 消费不受影响。

## 退路（fallback）

若上游代码把安装路径写死成 sbindir 派生（编译期常量、运行期定位），可显式还原布局：

```python
tc.update_configure_args({"--sbindir": "${prefix}/sbin"})
```

诚实权衡：偏离 conan 布局惯例——`cpp_info.bindirs` 必须同步改回 `["sbin"]`，且 CI 安装面
冒烟、commands.json、下游消费者"默认 bin/ 探测"的假设要逐一核对；仅在有硬约束时使用，
不做默认方案。

## 禁止（forbid）

- **打补丁改 Makefile.am 安装规则，或 package() 后 sed/mv 搬移已安装产物**。原因：改安装
  规则是对布局语义的侵入式改写（生成文件的修改还必须按 P-PATCH-001 落 .patch，只为目录
  名不划算）；事后搬动 ELF 会破坏 conan 包清单一致性，且任何 ELF 搬动/修改都必须重签
  （P-PACK-001），漏签在目标机 codesign 校验直接失败。后果：签名失效、路径常量与实际
  位置二次错位，问题换个 phase 复发。

## 自包含验证探针

conan create 之后，任何新 shell 可跑（`<b>`=build_folder，`<p>`=package_folder）：

```sh
# 1) 工具链注入实证：预期输出 --sbindir=${prefix}/bin
grep -o -- "--sbindir=[^\"' ]*" <b>/conan/conanbuild.conf | sort -u

# 2) 包内落点对照：工具在 bin/，sbin/ 不存在（第二个 ls 返回非 0）
ls <p>/bin
ls <p>/sbin
```

两步都命中即确认"注入+展平"成立。本 run 实测（conan 2.29.1，libxfce4util/4.20.0）：
探针 1 → `--sbindir=${prefix}/bin`；探针 2 → `bin/xfce4-kiosk-query` 存在、`sbin/` 不存在；
按 bin/ 对齐断言后 CI 全绿。

## 证据索引（run 内审计用，探针不依赖）

- run6 失败：`logs/ci-run6.log:719-721`（AssertionError）
- run8 注入与落点：`logs/ci-run8.log:190`（configure 全参数）、`logs/ci-run8.log:603`
  （libtool install `p//bin/`）
- libxfce4util `notes.md` 问题表 #8（libtool 落点 `p//bin/` 与对齐决策）

## 查重证据

- `references/build-chain-pitfalls.md`：grep `sbindir|sbin` → 0 命中。
- `knowledge/graph`：grep `sbindir` → 仅 E2167/E545 相邻（configure 期拒绝形态），无
  "静默展平+验证期失败"覆盖。
- `knowledge/drafts`：`retro-gtk-1.0.2-conan-meson-libexecdir-bin-merge`（MesonToolchain、
  运行期路径常量影响）、`schroot-1.6.13-libexecdir-bin-clash`（CMakeToolchain、安装冲突）
  为最近邻——工具链与失败 phase 均不同，逐项差异见上表。
- 经验仓 main：grep `sbindir` → 0 命中（且经验仓不构成 B 查重面，仅附注）。
- 本条新增价值：autotools 链路的"静默展平"形态 + 失败 phase 判位法 + rec/fallback/forbid
  完整方案空间，族内无覆盖。
