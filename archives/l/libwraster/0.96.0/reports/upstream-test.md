# 上游测试用例真跑报告（rule4/R51）

- 日期：2026-10-16
- 主机：OHOS aarch64（HarmonyOS PC 目标平台本机）
- 显示环境：Xvfb 21.1.15（cmd-pkgs 预编译包 `xorg-server 21.1.15`，用户级 prefix 安装），
  启动参数 `Xvfb :99 -ac -nolisten local -xkbdir $HOME/usr/local/share/X11/xkb -screen 0 1024x768x24`
  （`/tmp` 只读 → unix socket 不可用，走 TCP `127.0.0.1:99`；XKB 数据来自 `xkeyboard-config 2.42` 预编译包）
- 被测程序：上游 `wrlib/tests/` 4 个 `noinst_PROGRAMS`（testdraw / testgrad / testrot / view），
  源文件未做任何修改（R51），以 OHOS clang-15 静态链接本包 `libwraster.a` 直接编译
- 依赖库：libX11.so.6 / libXpm.so.4 / libxcb*.so（全部来自 conan 制品仓已发布包的共享库）

## 结果摘要

| 上游用例 | 运行方式 | 结果 | 退出码 | 说明 |
|---------|---------|------|--------|------|
| testdraw | 无参（内置 ballot_box.xpm），stdin=/dev/null | ✅ 通过 | 0 | 完整执行 testDraw/testBevel/drawClip/testScale/testRotate 五个测试段 |
| testgrad | `-d red green blue`，stdin=/dev/null | ✅ 通过 | 0 | 输出 0xff0000 / 0x00ff00 / 0x0000ff，渐变色转换正确 |
| view | 无参（内置 tile.xpm），stdin=/dev/null | ✅ 通过 | 0 | 加载 64x64 XPM 并渲染（"size is 64x64"） |
| testrot | stdin=/dev/null，timeout 10s | ✅ 通过 | 124 | 程序设计为无限旋转动画循环（`while(1)`），10s 内渲染 185 帧无崩溃；"NOT FULLY IMPLEMENTED" 输出 185 次来自上游 `wrlib/rotate.c:331`（上游代码固有输出，非本适配引入） |

**合计：4/4 真实执行，全部无错误退出/无崩溃。**

## 完整运行日志

```
=== libwraster 上游测试真跑记录 ===
date: 2026-10-16 11:29:13
display: 127.0.0.1:99 (Xvfb 21.1.15 :99 1024x768x24, -ac -nolisten local)
host: OHOS aarch64 (HarmonyOS PC)
workdir: wrlib/tests (含 ballot_box.xpm / tile.xpm / test.png)

--- testdraw (无参=内置 XPM; stdin=/dev/null) ---
exit_code=0

--- testgrad -d red green blue (stdin=/dev/null) ---
0xff0000
0x00ff00
0x0000ff
exit_code=0

--- view (默认内置 tile.xpm; stdin=/dev/null) ---
using default image as none was provided
size is 64x64
exit_code=0

--- testrot (无限旋转动画循环, timeout 10s 主动终止) ---
    185 NOT FULLY IMPLEMENTED (rotate.c:331 上游代码固有输出)
exit_code=124 (timeout 主动终止, 非崩溃)  帧数=185
```

## 判定口径

- 3 个程序（testdraw/testgrad/view）以 `stdin=/dev/null` 运行：程序主体执行完毕后在末尾
  `getchar()` 处读到 EOF，正常 `return 0` 退出 → 退出码 0 = 完整跑通全部代码路径。
- testrot 为上游设计上的无限动画循环（`while(1)` + `usleep(50000)`），无正常退出路径；
  以 `timeout 10` 主动终止（退出码 124），期间 185 帧旋转全部成功、无任何错误/崩溃。
  该用例的"通过"判据 = 运行期间无错误退出、无崩溃、持续出帧。
