# E429 — sane-backends 制品把后端搜索路径固化为 /lib/sane，OHOS 上不存在 → 无法枚举任何 SANE 设备

## 错误特征

消费者（libksane / ksanecore 等）无法发现或打开任何扫描仪，日志表现：

```
No scanners were identified. If you were expecting something different,
check that the scanner is plugged in, turned on and detected by the
sane-find-scanner tool (if appropriate).
```

```
scanimage: open of device test0 failed: Invalid argument
```

即 `sane_get_devices()` 恒返回空列表，`sane_open()` 返回 `SANE_STATUS_INVAL`，
即使启用的是无需硬件的官方 `test` 虚拟后端（dll.conf 中 `test` 已启用、
`test.conf` 已提供）也一样。

## 触发条件

- 平台: OHOS (arm64)，`/lib` 是指向只读 `/system/lib` 的软链
- 依赖: 制品仓 `sane-backends/1.2.1`（shared 构建）
- 阶段: runtime / testing（任何调用 `sane_init()` + `sane_get_devices()` 的消费者）

## 根因分析

`sane-backends` 的 dll 前端（`libsane-dll.so`）在编译期把后端库搜索路径固化为
`PATH_SANE_LIB`，加载时按 `"%s/libsane-%s.so.%u"` 拼路径 `dlopen`。制品包的
`libsane-dll.so` 中该常量是 **`/lib/sane`**（configure 前缀为 `/`），而 OHOS 上
`/lib` → `/system/lib`（root 所有、只读），`/lib/sane` 不存在，因此 dll 加载器
无法加载任何后端（`lib/sane/libtiff…` 无关；后端 .so 实际位于包内
`<pkg>/lib/sane/`）。该后端搜索路径不受 `SANE_CONFIG_DIR` 影响（该变量只影响
配置文件查找），也没有 `SANE_PATH` 之类的环境变量覆盖。

## 解决方案

### 推荐方案（测试环境规避，不改任何已发布产物）

SANE 后端本身就是一个完整的 libsane 实现（同时导出 `sane_init` / `sane_open` /
`sane_read` / `sane_get_devices` …），因此在运行消费者测试时直接
`LD_PRELOAD` 官方 `test` 后端即可绕过 dll 前端：

```bash
SANE_PKG=$(conan cache path sane-backends/1.2.1)
# 准备配置目录：复制包内 test.conf，并写 dll.conf
mkdir -p "$TEST_BUILD/sane.d"
cp "$SANE_PKG/etc/sane.d/test.conf" "$TEST_BUILD/sane.d/"
printf 'test\n' > "$TEST_BUILD/sane.d/dll.conf"

LD_PRELOAD="$SANE_PKG/lib/sane/libsane-test.so.1" \
SANE_CONFIG_DIR="$TEST_BUILD/sane.d" \
  "$TEST_BUILD/test_scan_flow"
```

实测（libksane 26.04.0 `test_package/test_scan_flow.cpp`）：`openDevice("0")` 成功、
读到 27 个真实 SANE 选项、写入 `resolution=100`、完整扫描得到 **314x393** 图像
（与请求的 80×100 mm @ 100 dpi 一致：80/25.4×100 = 314.96、100/25.4×100 = 393.70）。

### 根治方案（需要单独的依赖项 PR）

为 `sane-backends` 提依赖项修复：把后端搜索路径改为包内 `lib/sane`
（或在配方中通过 `--with-sane-libdir` / post-install 修正），修复后消费者可直接
使用标准 dll 加载器路径，无需任何 preload。

### 禁止做法

- ❌ 在系统目录创建 `/lib/sane`（`/lib` → 只读 `/system/lib`，且属于机器全局污染，不可复现）
- ❌ 用 dummy 设备/伪造返回值让测试"通过"（欺骗性行为，R34/R9）
- ❌ 删除或改写 `libsane-*.so` / 修改其它包的制品来规避

## 验证

```bash
# 不 preload：无任何设备（可复现缺陷）
SANE_CONFIG_DIR="$TEST_BUILD/sane.d" "$SANE_PKG/bin/scanimage" -L     # -> No scanners were identified

# preload 官方 test 后端：两个虚拟设备，可正常扫描
LD_PRELOAD="$SANE_PKG/lib/sane/libsane-test.so.1" \
SANE_CONFIG_DIR="$TEST_BUILD/sane.d" \
  "$SANE_PKG/bin/scanimage" -d 0 --resolution 50 --format=pnm -o "$TMPDIR/t.pnm"   # -> 输出真实 PNM 图像
```

## 关联条目

- 相关: `E537`（同为"制品包编译期固化路径/元数据缺陷 → 消费者侧症状"的模式，但根因不同）
- 同类先例（测试期环境隔离手段）: libksane 26.04.0 test_package 的 link farm + `/system/lib64` libc++ 前置

## 适用边界

- **适用**：OHOS 上任何依赖 `sane-backends` 的包及其消费者测试；物理扫描仪与虚拟 `test` 后端同样受影响
- **不适用**：非 OHOS 平台（`/lib/sane` 通常存在或后端路径正确）；不依赖 SANE 的包

## 不适用/禁止

- 禁止把该规避写进发布产物或 CI 发布流水线（仅测试环境使用）
- 禁止以 `== "Linux"` 判断平台（R32：须 `in ("Linux", "OHOS")`）
