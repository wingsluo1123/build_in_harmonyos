# spellcast 1.0 适配笔记

## 编译环境
- 构建系统: Make (1994 年 Makefile，无 configure，无 autotools)
- 编译日期: 2026-10-15
- 编译器: clang (OHOS aarch64 交叉工具链)
- 状态: built

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 硬编码 `-I/usr/local/include -L/usr/local/lib` | 1994 年 Makefile 面向 Unix 系统固定路径 | build() 内动态替换为 conan libx11/xorgproto 的绝对 include/lib 路径 |
| 2 | `cc: inaccessible or not found` (implicit make rule) | conanbuild 环境未传播 CC | 从 conf_info 读取工具链 CC 路径，make 命令显式传 CC= |
| 3 | `'X11/Xlib.h' file not found` (main.o) | `-I/usr/local/include` 替换未生效 | 使用 `dep.package_folder + "/include"` 绝对路径而非 `cpp_info.includedirs` |
| 4 | `'X11/X.h' file not found` (Xlib.h 内部包含) | libx11 不传播 xorgproto 头文件（已知行为） | 显式添加 `xorgproto/2025.1` 依赖，并将其 include 路径注入 Makefile |
| 5 | K&R C (1993) 编译报数百个 implicit declaration/int-conversion/return-type 错误 | 1993 年代码使用隐式 int 返回、隐式函数声明、int 转指针等 | Makefile CFLAGS 追加 `-std=gnu89` + 相关 warning suppression |
| 6 | 直接执行二进制 rc=126 (Permission denied) | conan 缓存位于 FUSE 挂载，exec 位不保留 | test.sh 检测 rc=126 后 cp 到 $HOME/tmp + chmod 755 重试；loader error 时走 stage_libs 依赖闭包 fallback（同 wmgtemp 模式） |

## 消费者测试（test_package）

`test.sh` 共 10 项：

1. 二进制文件存在
2. file 输出含 ELF
3. 架构 aarch64 (HarmonyOS target)
4. PIE 动态链接 (dynamic)
5. readelf -d 含 libX11 NEEDED
6. musl 动态链接器 `/lib/ld-musl-aarch64.so.1`
7. man 页面 `share/man/man6/spellcast.6` 存在
8. `spelllist.ps` 存在
9. 二进制含符号表 (not stripped)
10. **鸿蒙特有 · 非断言运行时可行性用例**：真实执行二进制（无 DISPLAY），验证完整 NEEDED 共享库闭包（libX11.so.6 + libc.so）在 OHOS musl 加载器下原生加载与重定位。**非断言判定**：仅动态加载器错误（`Error loading shared library` / `Error relocating`）判失败，任何其他结果（usage 输出、exit 12、display 错误）均证明闭包加载成功；含 rc=126 exec 位修复重试与 stage_libs 闭包 staging fallback（wmgtemp 先例模式）

## 四维测试账本

| 维度 | 数值 | 来源 |
|---|---|---|
| 上游静态声明 N_static | 0 | Makefile 无 check 目标 |
| 构建系统注册 N_registered | 0 | 同上 |
| 实际执行 N_executed | 0 | 无上游套件 |
| 未执行分类 | 0 | — |
| 消费者测试 N_consumer | 10 | test_package/test.sh（含 1 项鸿蒙特有非断言运行时用例） |

## 源码修改

无补丁文件。Makefile 在 build() 内动态修改。

## 依赖版本

- libx11/1.8.13.1（已通过 conan download 验证可消费）
- xorgproto/2025.1（libx11 不传播，显式添加）

## 路径 B 判断

- 本包问题均为仓库已知模式（K&R C 编译、libx11 不传播 xorgproto、Makefile 路径替换）
- 无新错误签名
- 结论：纯路径 A，不申报路径 B

## 验证结果

- conan-verify: G0/G1/G2/G3/G4/L2/L4/L5 全 PASS
- W3 本地 CI 模拟: PASS (L0/L1/L4/L5 全通过)
- 消费者测试: 10/10 PASS
- 日志路径: archives/s/spellcast/1.0/reports/w3-local-ci.log

### 对话 #1 [2026-10-15]

- 问题
  - 1994 年 K&R C 源码在 OHOS clang 下数百个 implicit declaration/int-conversion 错误；Makefile 硬编码 `/usr/local` 路径与 `cc`；libx11 不传播 xorgproto 头文件；FUSE conan 缓存 exec 位不保留导致二进制 rc=126；test.sh 第 3 项在 OHOS grep 下误报架构不匹配。
- 操作
  - Makefile CFLAGS 追加 `-std=gnu89` 并压制 K&R 风格告警；build() 内将 `/usr/local` include/lib 路径动态替换为 conan 依赖包绝对路径；显式添加 xorgproto/2025.1 依赖并注入 include 路径；从 conf_info 读取工具链 CC 显式传给 make；test.sh 对 rc=126 增加 cp+chmod 重试，loader error 时走 stage_libs 闭包 staging fallback；test.sh 第 3 项 grep 由 BRE `\|` 交替（GNU 扩展，musl/busybox grep 不支持）改为 `grep -q -E "arm64|aarch64"`。
- 结果
  - conan create 成功；test_package 10/10 PASS（含 1 项鸿蒙特有非断言运行时闭包加载用例，真实执行输出 usage banner、rc=12，证明 libX11.so.6+libc.so 在 OHOS musl 加载器下原生加载重定位）；W3 本地 CI 模拟 L0/L1/L4/L5 全 PASS；finish 到达 Step 10 submit 预检通过。

---

**编译开始**: 2026-10-15
---

**编译结束**: 2026-10-15 16:06
**最终状态**: built
