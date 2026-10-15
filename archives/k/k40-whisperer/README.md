# k40-whisperer

K40 Whisperer — K40 激光雕刻机（Laser cutter）控制软件。tkinter GUI，读取 SVG/DXF
文件生成 EGV 指令，通过 USB 发送到 K40 控制器。纯 Python 实现（21 个 .py、0 个
C/C++ 源文件），GPL-3.0。

## Homepage
https://www.scorchworks.com/K40whisperer/k40_whisperer.html

## License
GPL-3.0

## Build System
无编译（纯 Python 脚本族，仿 archives/p/pyjson5/0.15.0 先例）

## Dependencies
- python/3.12.9（ohpcd 已发布）
- pillow/10.4.0（svg_reader.py / k40_whisperer.py 模块级硬 import，ohpcd 已发布）
- lxml（svg_reader.py / inkex.py 硬依赖，ohpcd 仅 built 未发布 → 未声明，见 notes.md）
- pyclipper / pyusb（上游 try/except 可选降级，未声明）
- tkinter（stdlib；OHOS python3.12 缺 _tkinter，GUI 不可运行）

## OHOS Adaptation
- 纯 Python 无编译：全部模块铺到 `lib/python3.12/site-packages/`，`import` 即可用
- 启动包装 `bin/k40-whisperer`：`--version`/`--help` 直接响应；真实启动因 OHOS
  缺 `_tkinter`（且 lxml 未发布）失败时输出明确诊断（exit 1），不静默崩溃
- GUI（tkinter）在鸿蒙不可运行（R40 如实标注）；核心算法模块
  （egv/dxf/interpolate/ecoords/convex_hull/g_code_library/LaserSpeed）纯 stdlib，
  可独立导入使用
- 上游测试 N=0（源码包无任何 test 目录/测试文件）；鸿蒙特有测试
  test_package/test_k40_ohos.py 实质调用核心 API（R34），22 断言

## Versions
- 0.71 — 2026-10-11（built；纯 Python 配方；上游 N=0，鸿蒙特有测试 22 断言全过）
