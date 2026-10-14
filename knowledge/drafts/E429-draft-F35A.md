# E429 — OHOS musl 不支持 IRELATIVE 重定位：代码含 ifunc（GNU indirect function）时二进制一启动就崩

## 错误特征

- 编译、链接、安装**全部正常**，失败只出现在运行时（`conan create` 的 test_package 冒烟阶段最先暴露）：
  - `Error relocating <bin>: <symbol>: symbol not found`
  - 或进程在 libc 初始化阶段直接被终止（无 backtrace，退出码 127/139）
- 关键判据（决定性证据）：`readelf -r <bin> | grep -c IRELATIVE` **> 0**
- 极易误判：症状与「运行时库找不到 / LD_LIBRARY_PATH 未设置」高度相似，容易一路排查库路径而错过重定位问题

## 触发条件

- 构建系统: cmake（nCine 引擎系；任何显式使用 ifunc 的工程同理）
- 阶段: runtime（configuration / compilation / linking / installation 均无异常）
- 平台: OHOS aarch64（musl 动态加载器 `ld-musl-aarch64.so`）
- 上游开关: nCine 默认 `DEATH_CPU_USE_IFUNC=ON`（`cmake/ncine_helpers.cmake`，用于 memcpy 等热点做 CPU 特性分发）

## 根因分析

`__attribute__((ifunc))` 把符号解析推迟到**加载期**：由动态加载器执行 resolver，再把结果地址写回 GOT。链接器为此产出 `R_AARCH64_IRELATIVE` 重定位。OHOS 的 musl 动态加载器不实现 IRELATIVE 处理路径，于是这些符号保持在未解析状态——轻则加载期报 `symbol not found`，重则进程在 libc 初始化阶段异常终止。

具误导性的地方在于：`readelf -d` 的依赖列表完全正常，静态检查（含编译期告警）无任何异常，只有真正跑起来才暴露。

## 解决方案

### 推荐方案

构建期关闭 ifunc 分发，交回编译器做静态选择：

- nCine 系：`-DDEATH_CPU_USE_IFUNC=OFF`（本仓 jazz2-native 3.6.0 即此处置，配方 `cache_variables` 固定关闭）
- 自研代码：把 ifunc 换成语义等价的运行期条件分支，或按基线指令集静态编译

### 禁止做法

- ❌ 用 `LD_PRELOAD` / wrapper 脚本 / 额外 rpath 绕过——问题发生在加载期且属于重定位语义缺失，绕过手段可能在 resolver 之前就已失败
- ❌ 只看编译链接通过就判「适配完成」（R40：图形/多媒体等深层库须验证可运行性）
- ❌ 手工伪造验证结论替代实跑（应实际执行 `<bin> --version` 之类的早退路径取退出码）

## 验证

```bash
readelf -r <bin> | grep -c IRELATIVE   # 修复前 > 0；修复后必须为 0
<bin> --version                        # 修复后应正常输出并 0 退出（headless 可跑的早退路径）
```

## 关联条目

- 相关: E211（musl 缺少 glibc pthread 扩展符号——同为「glibc 专属能力在 musl 缺失」，但 E211 在**链接期**报未定义符号，本条在**运行期**才崩，两者常在同一批 nCine 系适配中同时出现）
- 相关: E499（Conan 依赖注入与运行时库解析——排查运行期崩溃时的邻接方向，先排除库路径再定位重定位）
- 相关: E092（OHOS 下 CMAKE_SYSTEM_NAME 需显式覆盖——同属工具链语义差异类）
