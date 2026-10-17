# DRAFT-24661: Conan 的 header-only/data 传递依赖不进消费方依赖遍历与编译路径，消费方必须显式 require

- **来源**：xfractint 20.4.10 适配（2026-10-16）；同根因第二实例 xworld 2.0 适配
- **领域**：Conan 依赖图语义 × 编译期头文件路径（依赖闭包）
- **邻近条目与轴差**：
  - **E480**（X11 客户端库头文件级依赖用 `transitive_headers=True` 消费）——**生产方轴**：被移植库自身在 requirements 里声明 `transitive_headers=True`，让头文件依赖透传给*它的*消费方（configure/PKG_CHECK_MODULES 场景）。本条是**消费方轴**：应用配方对"生产配方已声明但不出现在自己遍历里的 header-only 传递包"显式 require。两轴互补非覆盖；E480 的 forbid_2（头文件级依赖不得进 cpp_info 链接级 requires）属 cpp_info 轴，与本条的 recipe requirements 轴无实质冲突。
  - E307/E308/E309——xorgproto **作为被移植对象**的条目（test_package 形态 / L0c 模板 / 打包清单），无一条覆盖"消费方须显式 require"。
  - E468——pkg-config 名映射 fallback，探测名对齐轴。
  - E499——shared 包运行期显式传递 libdirs，链接轴非编译期头包 require 轴。

## 现象

```
In file included from unixscr.c:22:
<prefix>/include/X11/Xlib.h:44:10: fatal error: 'X11/X.h' file not found
```

- 消费方配方只 require 了 `libx11/1.8.13.1`；
- 但 libX11 自己的头 `Xlib.h` 第 44 行 `#include <X11/X.h>`；
- `X11/X.h` **归属 xorgproto 包**，libx11 包内并没有这个文件；
- 且 libx11 配方确实 `self.requires("xorgproto/2025.1")`——传递依赖
  真实存在，却不出现在消费方的任何 `-I` 路径里。

## 机理（带 header-only 限定，防止过宽表述被本 run 自身证伪）

Conan 2 图语义下，消费方 `build()` 里 `self.dependencies.host` 遍历：

- **链接轴**传递依赖**会**浮现：本 run PASS 构建的 `-I` 序列含
  libx11 + libxcb + libxau + libxdmcp——四个都是 libx11 的传递依赖；
- **header-only/data 轴**传递依赖**不会**浮现：同图的 xorgproto、
  xtrans、xcb-proto 均不在 `-I` 序列。

因此正确表述是"**header-only/data 轴的传递包不浮现到消费方遍历/
编译路径**"；不带限定的"传递依赖不进遍历"会被本 run 自身的 PASS
构建证伪。

## 修复

消费方配方显式声明：

```python
def requirements(self):
    self.requires("libx11/1.8.13.1")
    self.requires("xorgproto/2025.1")  # header-only 传递依赖显式声明
```

版本与生产配方（libx11）实际 require 的版本保持图内一致；
`-I/-L` 闭包仍由 `self.dependencies.host` 遍历动态拼接，不硬编码路径。

## 证据链

> **日志留存说明**：r2 失败日志位于 `worktree/.ci_logs/conan_build_xfractint_20.4.10.log`
> 路径，已被最终 PASS 轮覆盖（原始失败日志不留存）；失败过程以
> builder 报告轮次表 + 下述可复跑核验命令留证。

1. **本 run 实例**：去 require → `fatal error: 'X11/X.h' file not found`
   （修复轮 conan create 失败）；显式 `requires("xorgproto/2025.1")`
   → CI 全绿（PASS 轮日志构建命令含 xorgproto `-I`，实际生效）。
2. **传递依赖真实性**：`archives/l/libx11/1.8.13.1/conanfile.py`
   requirements 实含 `xorgproto/2025.1`。
3. **头文件归属**：libx11 包内无 `X11/X.h`；xorgproto 包
   `include/X11/X.h` 存在（find 实测，命令见 kv `verification_cmd`）。
4. **同根因第二实例（xworld 2.0）**：`archives/x/xworld/README.md`
   （"Xatom.h lives in xorgproto, not libx11 — must require xorgproto
   explicitly"）与 `archives/x/xworld/manifest.yaml` ohos_adaptation
   同义条目。错误类 signature 同为 `fatal error: X11/*.h`（xworld 缺
   `Xatom.h`、本 run 缺 `X11/X.h`——头文件名不同、根因相同）。
5. **graph 检索记录**：
   - `grep -ri 'xorgproto' knowledge/graph/` → E307/E308/E309/E468
     （逐项核为"被移植对象/名映射"轴，无消费方 require 轴覆盖）；
   - `grep -rli 'transitive_headers' knowledge/graph/` → E480（Curator
     首轮查重漏检的词族，Auditor 补检命中；生产方 transitive_headers
     直接消费轴，裁决为互补轴，见上文"轴差"）与 E348（配方同用
     transitive_headers=True 声明，条目主轴为 meson PkgConfigDeps
     .pc 转发，非本轴）；宽词族 `grep -rliE 'transitive|传递依赖'`
     另命中 E307/E358/E363/E420/E447/E449/E498/E499/E522/E541 共
     10 个其他轴条目，逐一裁决均不覆盖消费方 require 轴。

## 方案空间

| 层 | 处置 | 定位 |
|----|------|------|
| **rec** | requirements() 显式 require 头文件级传递依赖 | 主方案；图语义正确表达 |
| **fallback** | 收紧 libx11 版本区间 + notes.md 记录"对传递闭包的赌注" | 诚实定位为过渡性赌注：上游 libx11 配方重构即碎，仅临时兼容 |
| **forbid_1** | 硬编码 conan 缓存绝对路径拼 `-I` | 缓存包目录迁移/重建即失效，构建不可复现，依赖审计失真 |

## 验证路径

- **机理级（自包含，本 run 已实测）**：kv `verification_cmd` 的四段
  核验命令（图检索去重 / 近邻排查 / 传递依赖真实性 / 头文件归属）。
- **标准路径（双轮 create 循环）**：去 require → `conan create` 复现
  `fatal error: 'X11/X.h' file not found`；恢复 require → `conan create`
  PASS。任何持有 X11 客户端配方者可独立执行。

## 适用范围

- 全部 X11 客户端应用/库配方（libx11 → xorgproto 传递头链）；
- 任何以协议头/SDK 数据包为传递依赖的 Conan 消费配方。

## 原则挂钩

- **P014**（环境变量与构建系统语义冲突陷阱——图/遍历语义族）：依赖
  可见性应走构建系统原生机制（配方 requirements / 依赖遍历），不走
  环境变量或硬编码路径旁路。
