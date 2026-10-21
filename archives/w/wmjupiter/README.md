# wmjupiter

WindowMaker 系的 X11 dockapp：64x64 的 pixmap 小窗，实时绘制木星四颗伽利略卫星
（Io / Europa / Ganymede / Callisto）相对木星的位置，以及木星大红斑（GRS）的过中天
时刻。设计成常驻 WindowMaker 的 dock 或 AfterStep 的 Wharf，也可在任意窗口管理器下
作为普通窗口运行。原始版本由 Thomas Kuiper 于 1998-2001 年编写（inxsoft.net），
现由 engerim42 维护，许可为 BSD-3-Clause。

## 功能面

- 卫星位置与 GRS 过中天计算（`wmJupiter.c` 内的开普勒轨道/自转周期数值算法，
  不依赖外部星历数据文件）
- 64x64 贴图绘制：木星本体与卫星用 `wmJupiter_master.xpm`（运行期由 libXpm 解码，
  实测 10 色），窗形遮罩用 `wmJupiter_mask.xbm`（经 XShape 合成 64x64 形状位图）
- X11 绘制链路：`XCreateWindow` → `XCreateGC` → `XCreatePixmap` → `XPutImage` →
  `XCopyArea` 推帧到窗口；窗口属性注册（WM_NAME / WM_CLASS / WM_COMMAND 等）
- 命令行界面：`-display <dpy>`（同 X11 标准）；无参启动即直接连默认 display。
  上游未实现 `-h`/`--version`（`xutils.c` 只解析 `-display`），故 L2 smoke 检查
  按 `L2_RESULT=skip` 处理

## OHOS adaptation

- Builds with the upstream hand-written GNU Makefile (no `configure`, no autotools);
  `make CC=... CFLAGS=...` is invoked with the Conan toolchain and a single `-j1`
  (`OBJS` share one output directory and there are only two translation units).
- Two source patches only, both about the 1998-era C dialect rather than platform
  ports: upstream puts *tentative definitions* of the globals
  (`display`, `Root`, `iconwin`, `win`, `screen`, `DisplayDepth`, `NormalGC`) in
  `xutils.h`, so both translation units emit a common-symbol definition. clang 15
  under `-fno-common` rejects the duplicate at link time, so
  `0001-xutils.c.patch` turns them into one real definition and
  `0002-xutils.h.patch` turns the header copies into `extern` declarations.
  No `#ifdef __OHOS__` and no `-D__OHOS__` injection anywhere in `patches/`.
- Links the published `libx11/6.4.0` + `libxext/6.4.0` + `libxpm/3.5.17`
  (+ `xorgproto/2025.1` headers) cmd-pkgs track, so the XPM/Shape drawing surface is
  kept intact instead of being patched out.
- Upstream ships zero automated tests (tarball has 9 entries, `Makefile` has only
  `all`/`clean`/`install`, and `grep -c 'check\|test' Makefile` = 0). The consumer
  test therefore runs the real packaged binary with 24 assertions in two groups:
  - **A (7)** — display-less real failure paths (`can't open display` plus the
    display string handed to `XDisplayName`; the number is PID-derived and sits
    in a port range disjoint from the peer's own, so a leftover listener cannot
    turn the negative case into "someone pretending to be an X server"). They
    also prove the dynamic dependency on `libXpm.so.4`/`libX11.so.6`/`libXext.so.6`.
  - **B (17)** — a full end-to-end consumer case driven by a *protocol-level
    headless X11 peer* (`test_package/x11_headless.py`, answering the setup handshake,
    `QueryExtension`/`ListExtensions`, `CreateWindow`, `ChangeProperty`,
    `CreatePixmap`, `CreateGC`, `PutImage` and `CopyArea` on `127.0.0.1`). The peer
    accumulates server-side state (windows, WM properties, decoded pixels, frame
    count) and the assertions compare that real output. It is **not** Xvfb, does
    **not** set `DISPLAY=:0` and does **not** `dlopen` a display library (E530).

## Dependencies

- `libx11/6.4.0`, `libxext/6.4.0`, `libxpm/3.5.17`, `xorgproto/2025.1`
  (all published OHOS armv8 binaries in the `ohpcd` Conan remote)

## Limitations on HarmonyOS PC

- There is no real X display on the device, so the window is driven against the
  in-process protocol peer rather than a compositor; compositing, window-manager
  placement and on-screen appearance still need a manual glance on a real X session.
  Declared as-is (R40 note), not stubbed.
- `-h`/`--version` style smoke checks are skipped (`L2_RESULT=skip`): the program has
  no such option — its no-argument behaviour is to open a display, which fails on the
  device by construction.

## References

- Upstream repository: https://github.com/engerim42/wmjupiter (tag `1.21`)
- Release tarball: https://codeload.github.com/engerim42/wmjupiter/tar.gz/refs/tags/1.21
- Original author: Thomas Kuiper (inxsoft.net), 1998-2001; maintained by engerim42
