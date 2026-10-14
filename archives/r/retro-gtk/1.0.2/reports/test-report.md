# retro-gtk 1.0.2 验证报告（HarmonyOS PC / OHOS aarch64）

日期：2026-10-12　|　构建系统：Meson　|　编译器：clang 15.0.4（musl, aarch64-linux-ohos）

## 1. 真实构建

```bash
conan create archives/r/retro-gtk/1.0.2 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → Package '9d069a74340868f4bf3ae39e937763cf897f9e2f' created
```

产物（包内布局）：

| 路径 | 说明 |
|------|------|
| `lib/libretro-gtk-1.so.0`（+ `.so` 符号链接） | 公开库（SONAME `libretro-gtk-1.so.0`） |
| `libexec/retro-runner` | 核心运行进程（内部 helper） |
| `include/retro-gtk/*.h` | 22 个公开头 |
| `lib/pkgconfig/retro-gtk-1.pc` | pkg-config 元数据 |
| `licenses/COPYING` | GPL-3.0-or-later |

## 2. 上游测试（build() 内实跑，R51）

清点：`tests/meson.build` 注册 2 项 meson test。

```bash
meson test -C <builddir> --print-errorlogs
```

| 用例 | 结果 | 耗时 |
|------|------|------|
| `retro-gtk:/retro-dummy reftest` | OK | 0.30–0.33s（各批次） |
| `retro-gtk:RetroCore test` | OK | 1.57–1.78s（各批次） |
| **合计** | **Ok 2 / Fail 0 / Skipped 0** | — |

上游测试对源码的修改（如实申报）：
- `tests/retro-reftest.c` 的 `gtk_test_init()` → `g_test_init()`（补丁 0003）。
  原因：`gtk_test_init()` 需要 X/Wayland display（上游 CI 自身用 `xvfb-run` 包裹），
  而该 reftest 只比较软件渲染的 pixdata、不创建任何 widget。断言一条未删。
- 另需 `RETRO_RUNNER_PATH` 覆盖（补丁 0001）：上游测试在构建树内运行时，
  `retro-runner` 位于 `<builddir>/retro-runner/retro-runner`，而编译期常量指向安装前缀。

日志：`<builddir>/upstream-meson-test.log`（配方内保留完整输出与 meson 摘要）。

## 3. test_package（消费者视角，R34）

`test_package/` 构建两个目标并实跑：

- `libretro-test-core.so`：自写的假 Libretro 核心（完整 21 个入口，RGB565
  320x240@60fps，帧内容按 `test_pattern.h` 的确定性契约生成）；
- `retro-gtk-consumer`：链接被测库，走 `RetroCore` 公开 API
  （`retro_core_new` → `"video-output"` 信号 → `retro_core_boot` →
  `retro_core_iteration` ×3），覆盖 **被测库 → 被测包内 retro-runner 进程 →
  私有 GDBus IPC → memfd 帧缓冲 → RetroPixdata → GdkPixbuf** 全链路。

断言：API 版本、initiated、fps=60.00、帧几何 320x240、3 次 iteration 均收到
pixdata、5 个采样点逐像素比对、整帧 FNV-1a 校验和比对（frame 1/2/3）。

```
RETRO_GTK_OHOS_CONSUMER_OK frames=3 geometry=320x240 fps=60.00 frame=3 checksum=0x52f0e94d
```

## 4. 鸿蒙专项测试（test_package/test_ohos.sh，19/19）

```
ok   - libretro-gtk-1.so.0 is ELF64/AArch64
ok   - libretro-gtk-1.so.0 carries a .codesign section
ok   - retro-runner is ELF64/AArch64
ok   - retro-runner carries a .codesign section
ok   - SONAME is libretro-gtk-1.so.0 (name-based, not path-based)
ok   - no Linux-only dynamic dependencies (libpthread/librt/libutil/libdl)
ok   - exports retro_core_new / retro_core_boot / retro_core_iteration /
       retro_core_get_frames_per_second / retro_pixdata_to_pixbuf /
       retro_pixdata_get_width / retro_pixdata_get_height（7 项）
ok   - installs include/retro-gtk/{retro-gtk.h,retro-core.h,retro-pixdata.h}
ok   - installs lib/pkgconfig/retro-gtk-1.pc
ok   - consumer ran on device: … checksum=0x52f0e94d
ok   - on-device frame checksum is deterministic (0x52f0e94d)
```

## 5. 结论

- 真实构建（conan create）通过，上游 2 项测试实跑 2/2 通过；
- test_package 以真实 API 驱动被测包的 runner 进程并用逐像素契约校验视频输出；
- 鸿蒙专项 19/19 通过（ELF 身份/签名/soname/符号/元数据/设备端确定性）；
- 已知取舍：pulseaudio 音频后端因制品仓版本互斥而关闭（`-Dpulseaudio=disabled`），
  见 `notes.md` 第 7 条；GL 显示路径（`RetroCoreView`）需要真实显示环境，未在本沙箱内运行。
