# libinput 1.28.1 适配笔记(HarmonyOS PC / aarch64)

## 基本信息

- 构建系统: **meson**(1.28.x 选项面与 1.26.x 一致)
- 上游版本: 1.28.1(Debian 源包 `1.28.1-1` 的 orig)
- 源 URL: `https://deb.debian.org/debian/pool/main/libi/libinput/libinput_1.28.1.orig.tar.gz`
  sha256 `a13f8c9a7d93df3c85c66afd135f0296701d8d32f911991b7aa4273fdd6a42a3`(实测)
- 补丁: **1 个** — `patches/0001-ohos-musl-program-invocation-name-fallback.patch`
- 前置: 本包是 consolation 0.0.10 的依赖;依赖组合(libevdev/1.13.7、
  mtdev/1.1.7、eudev/3.2.14)沿用 main 上**已构建发布**的 1.26.2 同款,
  保证本 PR 合入前即可独立构建。

## 补丁说明(musl:program_invocation_short_name 第三级 fallback)

上游 `meson.build` 的探测链只有两级:

```meson
if not cc.has_header_symbol('errno.h', 'program_invocation_short_name', ...)
    if cc.has_header_symbol('stdlib.h', 'getprogname')
        config_h.set('program_invocation_short_name', 'getprogname()')
    endif
endif
```

musl(OHOS PC)两级皆不命中 → `program_invocation_short_name` 保持
未定义 → `tools/libinput-record.c` 与 `tools/ptraccel-debug.c`(仅有的
两个使用点,都在 usage() 输出)编译失败。补丁追加第三级:

```meson
else
    config_h.set('program_invocation_short_name', '"libinput"')
```

字面量对 usage() 输出无功能损失;glibc 与 BSD 行为不变。

与 1.26.2 补丁的口径差异(有意为之):1.26.2 在两个 tools 文件里
per-file 地 `#define program_invocation_short_name __progname`(语义
等价、保留运行时程序名);本补丁在 meson 层一处收敛,不引入逐文件
extern。两种方案均在仓内有先例,可任选;若评审倾向 `__progname`
方案,补丁可等价替换。

## 平台构建要点(承 1.26.2,全部保留)

| 要点 | 原因 |
|------|------|
| `PkgConfigDeps` 生成依赖 .pc | libinput 经 pkg-config 找 libudev/mtdev/libevdev |
| eudev 显式 `headers=True, libs=True, transitive_*` | eudev 的 `package_type=application` 使 Conan 默认丢弃其 cpp_info;且公开头 `libinput.h` 直接 `#include <libudev.h>` |
| `-Dlibwacom=false` | ohpcd 无 libwacom;上游有 no-op fallback,损失仅数位板型号识别 |
| `-Ddebug-gui=false` | 该工具需要 GTK4 |
| `-Dtests=false -Dinstall-tests=false` | litest 需 /dev/uinput 创建虚拟设备(1.26.2 实测 EACCES);如实申报未运行 |
| `-Dlibexecdir=libexec` | Conan 的 MesonToolchain 硬编码 libexecdir=bindir,主命令与子工具目录撞车 |
| `TMPDIR` / `AR`/`RANLIB` 注入 | /tmp 只读(E002);meson 回退宿主 ar |
| OHOS 下 ELF 递归重签名 | meson install 原地改写 RUNPATH 使 .codesign 失效,加载器空原因拒载 |
| shared 时补 `.so` SONAME 软链 | HMDFS 软链丢失防护 |

## 验证记录(本地,未交叉编译)

- 补丁对 Debian orig 解包树 `git apply --check` **通过**;
- 源码树做过 musl 兼容性静态检查(43/43 通过);工具链无 OHOS 交叉
  环境,实际构建由 CI `conan create` 完成;
- sha256 为下载原包实测值。

## test_package(L1 消费者测试)

与 1.26.2 相同的 `test_libinput.c`(4 项断言):path 后端建 context
(无需 udev/seat)、日志优先级设置、添加不存在设备返回 NULL(不崩溃)、
unref 引用计数契约。上游 litest 套件需 /dev/uinput,构建机不可用,
如实申报未运行。

## 交付物(与 1.26.2 同构)

| 路径 | 说明 |
|------|------|
| `lib/libinput.so.*` + SONAME/dev 软链 | 共享库 |
| `include/libinput.h` | 公开头(**含 `#include <libudev.h>`**) |
| `lib/pkgconfig/libinput.pc` | pkg-config 元数据(consolation 的依赖入口) |
| `bin/libinput`、`libexec/libinput/`、`lib/udev/` | 主命令、子工具、udev callout |
| `share/libinput/*.quirks` | 设备 quirk 数据库 |

## 2026-10-13：GUI 当前候选与历史验证边界

上文的早期交叉编译缺失、GUI关闭及未运行说明属于历史状态，不代表本次
新候选已完成。当前配方默认with_debug_gui=True，并绑定真实GTK3.24.43
及其生产者targets=broadway元数据；run=True保留安装工具运行闭包，GTK
头文件和链接接口不误透传为libinput公共API。

新鲜r1352原生构建启用debug-gui=true/tests=true，真实Broadway服务与GTK
初始化后原工具参数测试73/73通过、零跳过，含此前未覆盖的25个GUI用例。
libinput-debug-gui SHA256为7bfc1cbad5274f6f17892176805f6cecf0fe4015b646a9d5ef8bda14166f0b03。
独立XML及15回执30WAL核验见任务根libinput-original-gui-observed-oct12-r1355.json。
发行源943个C测试定义、100个quirks参数化用例、73个工具用例和8个独立
检查的粒度仍须分别说明；853个实际需要原始设备能力的定义未获验证，
不能把旧r024结果与r1352拼成一轮完整软件PASS。

源码仅扩充原显示前置以识别BROADWAY_DISPLAY与显式GDK_BACKEND=broadway，
原gtk_init_check/RC77及解析返回值断言不改。0003补丁由官方
refresh-patch --auto生成，干净源精确重放字节匹配，SHA256
a4e47494b6d25f588922d4284c3db8b7a98463dfe7ba5bdf1a936a675d3220db。
这是源码适配，不设置伪造DISPLAY/WAYLAND_DISPLAY，不证明浏览器像素、
原始输入路由或硬件注入权限。当前正式Conan/消费者/鸿蒙专项、完整可执行
原测试合同及新HEAD平台Review/CI尚需完成，旧HEAD通过不能迁移到新候选。


## Current actual delivery 2026-10-13

Original available tests are one GUI r002 run:73+55+46+100+8=282;842 original device source definitions remain unexecuted and24 registered device gates retain RC77. A separate complete official producer r007 verified the GUI-enabled recipe, actual installed CLI with generated Conan runenv, C4 and one actual OHOS signed private-inode/API loader scenario. Both full receipts/WAL and cleanup are independently verified. This is not a combined full1124 pass, platform CI, merge or provider publication.

Actual official log SHA256: 335dfacc2c83f365354d2577bde899d50b1d6b1f1329931669eecac1f81727f7
