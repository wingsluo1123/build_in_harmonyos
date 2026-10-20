# vkd3d

Direct3D 12 → Vulkan 翻译库（Wine 项目），内含自研的 DXBC/DXIL → SPIR-V 着色器编译器。

## 简介

vkd3d 把 Direct3D 12 的 API 调用翻译成 Vulkan 调用，使 Windows 应用（经 Wine）能在只有 Vulkan 驱动的
平台上运行 D3D12 程序。它自带一套着色器编译器，可以把 DXBC（着色器模型 4/5）与 DXIL（着色器模型 6）
字节码编译成 SPIR-V，不依赖厂商的 D3D 编译器。

## 产物

| 产物 | 说明 |
|------|------|
| `libvkd3d.so.1.19.0` | D3D12 设备/资源/命令队列翻译层 |
| `libvkd3d-shader.so.1.17.0` | 着色器编译器：DXBC/DXIL/HLSL/FX → SPIR-V / DXBC / 汇编 |
| `libvkd3d-utils.so.1.6.5` | 工具函数（纹理上传、blob、调试等） |
| `bin/vkd3d-compiler` | 着色器编译命令行工具 |
| `bin/vkd3d-dxbc` | DXBC 容器的列举/提取/汇编工具 |

## 依赖

- `vulkan-headers`（`VK_HEADER_VERSION` 需 ≥ 228）
- `spirv-headers`（提供 `spirv/unified1/spirv.h` 与 `GLSL.std.450.h`）
- 运行期：由宿主提供 Vulkan loader（`libvulkan.so.1`）；vkd3d 以 `dlopen` 方式加载，不直接链接它

可选（默认关闭）：SPIRV-Tools（额外校验）、ncurses（编译器的交互界面）、XCB/OpenGL（演示与测试后端）。

## HarmonyOS 适配

- 构建系统：autotools。源码取上游官方发行包，其中已自带 `configure` 与由上游生成的公共头，
  因此在 HarmonyOS 上不需要 Wine 的 IDL 编译器。
- 目标三元组：`aarch64-linux-ohos`（同时显式给出 host 与 build，配置阶段不做平台猜测）。
- 平台相关改动集中在版本级 `patches/` 目录，并在版本级 `notes.md` 逐条说明原因与验证方式。
- 构建期需要 Perl 核心模块 `JSON::PP`（不是 `JSON`）；配方对上游脚本做了等价的可移植性替换。
- 测试：版本级 `reports/test-report.md` 记录上游套件的真实执行读数。上游测试需要真实 Vulkan 设备，
  配方在构建期提供软件 Vulkan 实现作为测试用设备，并在该设备不可用时直接失败（不允许零执行被记成通过）。

## 目录

```
archives/v/vkd3d/
├── README.md
├── commands.json          # 命令行工具声明
└── 1.19/
    ├── conanfile.py
    ├── conandata.yml
    ├── manifest.yaml
    ├── notes.md           # 适配笔记：症状 / 根因 / 最小复现 / 已试方案 / 最终方案
    ├── patches/           # 平台相关补丁
    ├── reports/           # 测试与验证报告
    └── test_package/      # 消费者测试
```
