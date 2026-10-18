# tofi

面向 wlroots 系 Wayland 合成器的极简、高可配置启动器（`tofi`，含 `tofi-run` /
`tofi-drun` 两个安装期符号链接与内部工具 `tofi-compgen`），dmenu 的常用替代。

- 主页: https://github.com/philj56/tofi
- 许可证: MIT
- 构建系统: meson (C2x)

## 版本

| 版本 | 状态 | 构建日期 |
|------|------|----------|
| 0.9.1 | built | 2026-10-18 |

## 依赖

字体栈：`freetype/2.14.3` · `harfbuzz/14.4.0` · `cairo/1.18.4.2` · `pango/1.58.2` · `glib/2.84.0.1`
Wayland 侧：`wayland/1.24.0` · `wayland-protocols/1.48` · `libxkbcommon/1.13.1`
其他：`musl-fts/1.2.7`（musl 无 `fts(3)`，上游用 `cc.find_library('fts')` 查找）
构建工具：`meson/1.11.0`

## 适配要点

- **musl 无 `fts(3)`**：上游 meson.build 用 `cc.find_library('fts', required: not
  cc.has_function('fts_read'))`（`src/drun.c` 扫桌面项树），OHOS 上必须由
  `musl-fts/1.2.7` 提供 `libfts`；该依赖不经 pkg-config，配方以
  `extra_cflags`/`extra_ldflags` 注入它的 `-I`/`-L`。
- **wayland-scanner 必须静态重建**：制品仓 `wayland` 包自带的 scanner `.codesign`
  已被 meson 安装期 ELF 改写作废，且 DT_NEEDED 内嵌构建机缓存绝对路径
  （libexpat.so，本机不存在）、另缺 `libxml2.so.16`。配方从 wayland 1.24.0
  源码编译一个只依赖 libc 的静态 scanner 供
  `dependency('wayland-scanner', native: true)` 使用（E2200 命中）。
- **`.pc` 修补两类**：变量改写（`prefix`/`libdir`/`includedir`）之外，还要重写
  **根相对路径**——`freetype2.pc` 直接写死 `Libs: -L//lib -lfreetype`（打包
  prefix 为 `/`），只改变量够不到；纯传递依赖被 conan 记为 Skipped binary 而不装
  `.pc`（libffi/pcre2/pixman/libpng/fontconfig/fribidi/libthai/libdatrie）⇒ 提升为
  直接 requires。
- **上游 `<string.h>` 与 `<libgen.h>` 在 C2x 下互斥**：OHOS sysroot 的
  `<string.h>` 在 `_GNU_SOURCE` 下声明 K&R 的 `char *basename();`，`-std=c2x`
  下等价 `(void)`，与 `<libgen.h>` 的 `char *basename(char *)` 冲突（两种
  include 顺序都冲突）⇒ 补丁 `0001` 令 `src/config.c` 直接声明 `dirname()`、
  `src/history.c` 移除未使用的 include（上游调用点不变）。
- **ELF 必须签名（E077）**：meson 安装期就地改写 ELF（RUNPATH 的构建机绝对路径
  → 占位符）使链接器写入的 `.codesign` 失效，`package()` 末尾用
  `binary-sign-tool sign -selfSign 1` 重新签名，否则安装后的 `bin/tofi` 执行被拒。
- **上游测试真跑**：`test/meson.build` 以 `protocol: 'tap'` 注册 `config`、`utf8`
  两个目标、共 80 条断言；配方 `build()` 内 `meson.test()`。⚠ 该套件是手写 TAP
  harness，`tap_not_ok()` 只打印 `not ok`、测试 `main()` 恒 `return EXIT_SUCCESS`
  ⇒ **退出码不能当判据**，只能由 TAP 解析器判定（见知识草稿
  `DRAFT-tofi-0.9.1-tap-exit-code-decoupled-suite`）。
- 消费者测试 12 条断言（产物 8 + 真实运行 4）全部通过。

## 构建 / 验证

```bash
conan create archives/t/tofi/0.9.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

## 使用

```bash
tofi --help                # 打印 usage
tofi-run                   # 以 $PATH 为候选的启动器
tofi-drun                  # 以 .desktop 项为候选的启动器（依赖 fts）
```

详细配方与验证记录见 `0.9.1/`。
