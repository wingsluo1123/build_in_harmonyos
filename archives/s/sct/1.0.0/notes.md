# 适配笔记 — sct 1.0.0

- 软件名: sct
- 版本: 1.0.0（上游 tag 1.0.0）
- 上游: https://github.com/0mp/sct（Ted Unangst 的 sct 的 FreeBSD 移植版）
- 构建系统: 手写 Makefile（无 configure、无测试目标）
- 编译日期: 2026-10-17
- 状态: built（PR 阶段尚未 upload，合并后由 release 流水线发布）

## 编译步骤

```bash
# 源码：GitHub release tarball（R39 官方源），sha256 与 FreeBSD port distinfo 一致
# 依赖：libxrandr/1.5.5.1（传递 libx11/6.4.0、libxrender/0.9.12、libxext/6.4.0、xorgproto/2025.1）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
# 配方内部：
#   AutotoolsToolchain + AutotoolsDeps 生成 conanbuild 环境
#   CFLAGS="$CFLAGS $CPPFLAGS -std=c99 -Wall" LDFLAGS="$LDFLAGS" make -j1 INCS= LIBS=
#   make install DESTDIR=<package_folder> PREFIX= MANPREFIX=/share
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接报 `undefined reference to XOpenDisplay / XRRSetCrtcGamma` | 把 CFLAGS/LDFLAGS 作为 make **命令行变量**传入，覆盖了 Makefile 里的 `LDFLAGS += -lX11 -lXrandr`（GNU make 命令行赋值优先于 `+=`） | 改为环境变量方式传入（`CFLAGS=... LDFLAGS=... make ...` + `env="conanbuild"`），保留 Makefile 追加的 `-lX11/-lXrandr`；该经验已沉淀为知识草稿 DRAFT-sct-1.0.0-make-commandline-var-suppresses-append |
| 2 | `make: *** No targets specified and no makefile found` | `basic_layout` 将 source 与 build 目录分离，conan 默认在 build 目录执行 | `cd "{self.source_folder}"` 后再 make |
| 3 | 链接/头文件命中 `/usr/local` 宿主机路径 | Makefile 默认 `X11INC=/usr/local/include`、`X11LIB=/usr/local/lib` | `make INCS= LIBS=` 置空，include/lib 由 conan 依赖（CPPFLAGS/LDFLAGS）提供（R33） |
| 4 | `conan install` 时 libxrender/0.9.12 二进制缺失 | libxrandr/1.5.5.1 固定 libxrender/0.9.12，该版本在 libx11/6.4.0 下未发布预编译包 | `--build=missing` 从源码重建（约 1.5 分钟），CI 使用同一策略 |

## 源码修改

无。上游 `sct.c` / `Makefile` 未改动，`patches/` 为空。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| libxrandr | 1.5.5.1 | 直接依赖（Xrandr.h、libXrandr.so.2） |
| libx11 | 6.4.0 | 传递依赖（Xlib.h/Xatom.h/Xproto.h、libX11.so.6） |
| libxrender | 0.9.12 | 传递依赖，二进制缺失时源码重建 |
| libxext | 6.4.0 | 传递依赖 |
| xorgproto | 2025.1 | 传递依赖（extensions/randr.h 等协议头） |

## 验证结果

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify sct 1.0.0   # G0-G4 PASS；L2/L4/L5 跳过（纯可执行包，无 cache 路径）
conan create ... --build=missing                                 # 成功，test_package 18/18 断言 PASS
readelf -h package/bin/sct   # ELF64 LSB, AArch64, DYN (PIE)
readelf -l package/bin/sct   # interpreter /lib/ld-musl-aarch64.so.1
readelf -d package/bin/sct   # NEEDED libX11.so.6, libXrandr.so.2；无 libc.so.6
readelf -S package/bin/sct   # .note.ohos.ident 存在
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（application 类型，R38） |
| conandata.yml | 源码 URL + sha256 |
| test_package/ | 消费者测试（18 条断言）+ 可选真实 X server 测试 |
| commands.json | 命令行工具声明（软件级，R38） |
| manifest.yaml | 版本级元数据 |

## 注意事项

1. **上游无测试套件**：tarball 只有 `sct.c` / `Makefile` / `sct.1` / `README.md` /
   `LICENSE`，Makefile 无 `check`/`test` 目标（`make check` 报 "No rule to make target"）。
   `test_package/MANIFEST.yml` 如实声明 `upstream_tests: []`，未虚报上游用例。
2. **真实 gamma 路径需要 X server**：本设备无可用 X server（Xvfb 依赖的共享 libpng
   在本机不可用），`test_package` 在检测不到 DISPLAY/Xvfb 时跳过真实 gamma 应用并输出
   平台限制说明；CLI 错误契约与鸿蒙 ELF 标记测试始终执行。
3. **sct 先打开 display 再解析 argv**（上游设计）：无 X server 时非法/越界温度参数
   也会先走 "Failed to open X display" 退出，因此本地无法覆盖 1000-10000K 范围钳制
   逻辑；有 X server 的 CI/设备上由 test_package 的 `sct 3000/6500` 补足。
4. **运行期依赖**：目标系统需提供 X server（X11）+ XRandR 扩展；HarmonyOS PC 默认
   无 X server，工具在无 display 时按上游契约返回 1 并打印诊断。
---

**编译结束**: 2026-10-17 15:48
**最终状态**: built
