# DRAFT — HarmonyOS 上 JNA 平台识别失效：显式识别 HarmonyOS 并禁用 native 路径

状态：草稿（OpenDesk 落稿，2026-10-14）；Exxx 编号由知识库主编定稿时分配。
案例库：typometer 1.0.1（pavelfatin/typometer，Java/Swing，经 JNA 4.2.0 做 native 屏幕访问）。

## 可复现症状与稳定错误签名

- 平台判定异常（观测）：在 HarmonyOS PC 上 `System.getProperty("os.name")` = `HarmonyOS`，
  `com.sun.jna.Platform.isLinux()` = `false`，`Platform.isARM()` = `false`，
  `Platform.RESOURCE_PREFIX` = `harmonyos-aarch64`。
- 误入 native 路径的崩溃（若代码按 Linux -> X11 分支）：
  `java.lang.UnsatisfiedLinkError: .../libX11.so.6: cannot open shared object file`（经 `Native.register("X11")`）。
- GUI 运行期（AWT）：`java.lang.UnsatisfiedLinkError: .../libfontmanager.so: Error loading shared library libfreetype.so.6`
  （见另一篇 Swing/AWT 草稿）。

## 根因（机理链）

1. JNA 的平台判定基于 `os.name` 的关键字（`linux`/`win`/`mac`）。HarmonyOS 的 `os.name="HarmonyOS"`
   不匹配任何已知平台关键字。
2. 结果：`Platform.isLinux()=false`、`Platform.isWindows()=false`，`RESOURCE_PREFIX` 推导为
   `harmonyos-aarch64`。
3. JNA 4.2.0 的 jar 内没有 `harmonyos-aarch64` 的 `libjnidispatch`（2015 年版本，早于 OHOS），
   且 OHOS 不提供 X11 客户端库（`libX11`）。
4. 因此任何"按 Linux 走 native X11"的分支在 OHOS 上都会失败；依赖 `Platform.isLinux()` 的判定
   本身也随 JNA 版本对 `os.name` 的处理而漂移，行为脆弱。

## 方案（显式平台分支）

在平台判定处显式识别 HarmonyOS/OHOS：

```java
static boolean isHarmonyOS() {
    String os = System.getProperty("os.name", "").toLowerCase();
    return os.contains("harmony") || os.startsWith("ohos");
}
static boolean isNativeApiSupported() {
    if (isHarmonyOS()) return false;              // OHOS 无 X11/WinAPI native 屏幕 API
    return Platform.isWindows() || Platform.isLinux();
}
static ScreenAccessor create(boolean isNative) {
    if (isNative && !isHarmonyOS()) { /* Windows/Linux native */ }
    return new AwtRobotScreenAccessor();          // 可移植回退
}
```

- 仅新增平台分支，不改变 Windows/Linux 既有行为；
- 回退后端（AWT Robot）为纯 Java，可在 OHOS 上直接加载执行。

## 影响面

适用于所有在 HarmonyOS 上运行、经 JNA 判定平台或调用 native 屏幕/输入 API 的 Java 应用。

## 验证

- `java -cp typometer-1.0.1.jar Probe2` → `os.name=HarmonyOS`、`isHarmonyOS()=true`、`isNativeApiSupported()=false`；
- test_package 含鸿蒙专用断言（`isHarmonyOS()==true` 且 `isNativeApiSupported()==false`），在 OHOS 上 9/9 通过。

## 禁则

- ❌ 依赖 `Platform.isLinux()` 判定 HarmonyOS 并调用 `libX11`（判定为 false，脆弱且会误入 native 路径）。
