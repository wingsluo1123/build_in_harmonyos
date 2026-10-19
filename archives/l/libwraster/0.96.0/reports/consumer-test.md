# libwraster 0.96.0 —— 端到端消费者用例实测报告

面向审查项：鸿蒙特有测试不得只是断言集合，必须至少有一个**完整端到端消费者用例**
（构造输入 → 真实执行 → 产出结果 → 独立参考逐字节校验）。本报告记录该用例的实现与
实测数据。

## 1. 用例定位

- 文件：`test_package/consumer.c`（可执行文件 `libwraster_consumer`）
- 驱动：`test_package/conanfile.py` 的 `test()`（`conan create` / `conan test` 自动执行）
- 运行环境：aarch64-linux-ohos 交叉编译产物，在目标平台实际执行
- **不依赖 X server**：全流程只走 wraster 的与 X 无关的核心路径，CI（无显示器）可稳定执行

## 2. 五段式流程

| 段 | 动作 | 使用的库 API |
|----|------|--------------|
| 构造输入 | 4x4 主图标，四象限分别为红/绿/蓝/白四个规格色 | `RCreateImage` / `RClearImage` / `ROperateRectangle` |
| 真实执行 | 放大到 dock 图标尺寸 8x8 | `RScaleImage` |
| 塑形 | 打出 2x2 全透明窗口（(3,3)-(4,4)） | `ROperateRectangle` + `RClearOperation` |
| 产出结果 | 由库自身写出真实 XPM 文件，并回读全图落报告 | `RSaveImage(path, "XPM")` / `RGetPixel` / `RMessageForError` |
| 独立校验 | 独立实现的 XPM 解析器解码产物（不调用本库），与内存镜像、输入规格、二次运行逐项比对 | — |

产物：`dockapp-icon.xpm`（215 字节）+ `consumer-report.txt`（像素报告）。

## 3. 独立校验项（`test()` 内，共 7 类）

1. 内存镜像尺寸 = 8x8（`ICON_SIZE`）
2. 产物解码尺寸 = 内存镜像尺寸
3. **产物逐像素 = 内存镜像逐像素**（库的序列化结果必须与库的内存表示一致，不满足则打印首个不一致行）
4. 四象限核心块分别等于规格色（红/绿/蓝/白），验证缩放后各象限颜色未被串扰
5. 透明窗口 4 个像素 alpha 必须为 0（且 RGB 为 0）
6. 全图调色板必须 ⊆ 规格色集合 + 透明色（出现规格外颜色立即失败）
7. **确定性**：消费者重跑第二次，两份产物 sha256 必须完全相同

> 校验器不调用被测库：XPM 解析在 `test_package/conanfile.py` 内独立实现
> （`decode_xpm`），逐字节读出 `W H colors chars` 头、色表与数据行，按 chars-per-pixel
> 切分符号解码像素；参考期望值来自 `consumer.c` 的输入规格常量。

## 4. 实测结果

本地（同一 aarch64-linux-ohos 产物，`conan test test_package libwraster/0.96.0
-pr=ohos-aarch64-nv -s os.version=6.0`，退出码 0）：

```
consumer artefact: .../consumer-out-a/dockapp-icon.xpm (215 bytes,
  sha256 b1f2e5df31f88882801b7afbf4e035d3734239e3e999ebe43f08aef409884f8b)
end-to-end consumer OK: 8x8 shaped dock icon, 4 colours + transparent window,
  artefact matches the in-memory image and is byte identical across 2 runs
```

产物内容（库自身写出）：

```
/* XPM */
static char *libwraster_consumer[] = {
"8 8 5 1",
"  c None",
"0 c #ffffff",
"1 c #0000ff",
"2 c #00ff00",
"3 c #ff0000",
"33332222",
"33332222",
"33332222",
"3333  22",
"3333  22",
"11110000",
"11110000",
"11110000",
"11110000"};
```

## 5. 设计要点与踩坑

- 离线可产出格式只有 XPM：本配方关闭了 PNG/JPEG（`--disable-png --disable-jpeg`），
  且 `RSaveImage(RImage*, filename, format)` 不接收 `RContext`，XPM 写出路径
  （`wrlib/save_xpm.c`）不引用任何 Display/context，因此无 X server 也能产出真实文件。
- **透明像素只能用 `RClearOperation` 写**：`ROperateRectangle` 的快速路径分支
  （`wrlib/draw.c:334`：`color->alpha == 255 || operation == RCopyOperation`）会把
  alpha 强制为 255，传 `{0,0,0,0}` 用 `RCopyOperation` 实测回读为 `000000ff`
  （不透明黑）；改用 `RClearOperation` 后回读为 `00000000`。
- 消费者编译使用 `-Wall -Wextra -Werror`（与 `test.c` 同口径），无告警。

## 6. 与断言层（`test.c`）的分工

`test.c` 覆盖 15 条 API 断言（尺寸/像素往返/错误路径），保证单个 API 行为正确；
`consumer.c` + `test()` 覆盖"把库当成一个工具用"的完整链路并核验落盘产物。
两者都在 `conan create` 的 L1 测试阶段执行。
