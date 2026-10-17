# Test Report — sct 1.0.0

## 编译验证

- 编译器: clang 15（aarch64-linux-ohos，OHOS SDK / musl + libc++）
- 构建系统: 手写 Makefile（无 configure）
- 编译状态: 成功（`conan create`，OHOS aarch64 profile）
- 产物: `bin/sct` + `share/man/man1/sct.1`

## 上游测试用例

**上游 sct 1.0.0 不提供任何测试套件。**

- release tarball 仅含 `sct.c`、`Makefile`、`sct.1`、`README.md`、`LICENSE`；
- `Makefile` 没有 `check` / `test` 目标，`make check` 直接报
  `No rule to make target 'check'`；
- 仓库无 tests/ 目录、无 CI 测试配置。

因此"上游测试用例全部执行"的基数为 0 条；`test_package/MANIFEST.yml` 如实声明
`upstream_tests: []`，未虚报上游用例。适配后新增以下消费者测试与鸿蒙特有测试。

## 新增测试（test_package）

### 1. `test.c` — 消费者端到端 + 鸿蒙平台标记（18 条断言）

通过 `conanrun` PATH 定位并**真实执行**包内 `bin/sct`（R34：实质依赖被测包）。

| 组 | 断言 | 结果 |
|----|------|------|
| binary 可达 | `sct` 经 conanrun PATH 可定位 | PASS |
| 无 DISPLAY 错误契约 | `DISPLAY= sct 3000` → rc=1；stderr 含 `Failed to open X display` | PASS ×2 |
| 不可达 DISPLAY | `DISPLAY=:65535 sct` → rc=1；输出回显 display 名 `:65535` | PASS ×2 |
| 参数健壮性（不可达 DISPLAY 下） | `sct not-a-number` / `sct 1000` / `sct 10001` → rc=1 且不崩溃 | PASS ×3 |
| **鸿蒙特有：ELF 头** | `readelf -h` 成功；ELF64；小端；AArch64；DYN（PIE） | PASS ×5 |
| **鸿蒙特有：解释器** | `readelf -l` 含 `/lib/ld-musl-aarch64.so.1`（OHOS musl 加载器） | PASS |
| **鸿蒙特有：动态依赖** | NEEDED 含 `libX11.so.6`、`libXrandr.so.2`；无 `libc.so.6`（非 glibc） | PASS ×3 |
| **鸿蒙特有：OHOS 标识** | `readelf -S` 含 `.note.ohos.ident` | PASS |

合计：**18 条断言，18 PASS，0 FAIL**。

> 说明：上游 `sct.c` 先调用 `XOpenDisplay` 再解析 `argv`，因此无 X server 时
> 任何温度参数都先走 display 错误路径；1000–10000K 范围钳制只能由真实 X server
> 覆盖（见下）。

### 2. `conanfile.py` — 真实 X server 的 gamma 应用（平台条件测试）

当环境提供 `DISPLAY` 或存在 `Xvfb` 时：启动/复用 X server，执行
`sct 3000` 与 `sct 6500`，两者均须 rc=0，覆盖参数解析、白点插值与
`XRRSetCrtcGamma` 写入路径。

本机结果：**SKIP**——开发设备无可用 X server（`DISPLAY` 为空，Xvfb 依赖的
共享 libpng 不可用）。测试按平台限制跳过并输出说明，不影响上述 18 条断言。
在具备 X server 的 CI/设备上该分支会自动执行。

## Conan Verify（G0–G4）

| 门禁 | 结果 |
|------|------|
| G0 预构建风险评估 | PASS（E566 为 autotools 专用，本项目无 configure，不适用） |
| G1 配方完整性 | PASS |
| G2 clean `conan create` | PASS |
| G3 系统同名库隔离 | PASS（纯可执行包，无 lib/） |
| G4 产物完整性 | PASS |
| L2 / L4 / L5 | 跳过（无 cache 路径的纯可执行包） |

## 统计

| 项 | 数量 |
|----|------|
| 上游官方测试用例 | 0 |
| 适配新增断言 | 18 |
| 通过 | 18 |
| 失败 | 0 |
| 跳过（平台条件测试） | 1（真实 X server gamma 应用） |

## 结论

配方在 OHOS aarch64 上 clean 编译通过，18 条消费者/鸿蒙平台断言全部通过；
上游 0 条测试如实声明。真实 X server 路径在当前无 X 环境跳过，测试脚本已就绪。
