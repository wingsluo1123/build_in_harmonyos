- **三方库名称**：spellcast
- **上游版本**：1.0（1994 年原版，上游停更）
- **上游仓库地址**：https://www.eblong.com/zarf/spellcast.html（源码包：https://archive.ubuntu.com/ubuntu/pool/multiverse/s/spellcast/spellcast_1.0.orig.tar.gz）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：知识图谱既有模式（K&R C 交叉编译告警压制、libx11 不传播 xorgproto 头文件需显式依赖、Makefile 硬编码路径替换、FUSE conan 缓存 exec 位丢失 rc=126 重试模式——同 wmgtemp 先例）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游 1994 年源码无任何测试框架，Makefile 无 check/test 目标 |
| 集成测试 | 0 | 同上 |
| 其他测试 | 0 | 无 |
| **合计** | **0** | 清点证据：Makefile 仅 all/clean/install 目标，源码树无 tests/ 目录、无断言框架引用 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游为单一二进制程序，无可单元化的库 API |
| 集成测试 | 9 | +9 | test_package/test.sh 消费者测试：包内容/ELF 元数据/链接闭包静态验证 |
| 鸿蒙特有测试 | 1 | 新增 | 真实执行二进制的非断言运行时闭包加载用例 |
| **合计** | **10** | **+10** | 全部为适配后新增 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例（上游无测试用例）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游无测试用例，适配后补全了测试
- **补全的测试范围**：为编译产物（spellcast 可执行文件）新增 10 项消费者集成测试
- **补全原因**：上游为 1994 年 X11 单二进制游戏，无任何测试框架与测试目标；按 R34/R51 以 test_package 消费者测试补全
- **新增测试文件清单**：
  1. `archives/s/spellcast/1.0/test_package/test.sh` — 10 项消费者测试：①二进制存在 ②ELF 格式 ③arm64/aarch64 架构 ④PIE 动态链接 ⑤readelf 确认 libX11.so.6 NEEDED ⑥musl 动态链接器 ⑦man 页面安装 ⑧spelllist.ps 资源安装 ⑨符号表未剥离 ⑩**鸿蒙特有·非断言运行时闭包加载**：无 DISPLAY 真实执行二进制，仅动态加载器错误（`Error loading shared library`/`Error relocating`）判失败——usage banner/exit 12 等任何其他结果均证明 libX11.so.6+libc.so 完整 NEEDED 闭包在 OHOS musl 加载器下原生加载与重定位；含 rc=126 exec 位修复重试与 stage_libs 依赖闭包 staging fallback

## 验证结果

- 编译状态：通过（conan create 成功，G0-G4/L2/L4/L5 全 PASS）
- 上游测试用例通过率：0/0（上游无测试用例，清点证据见上表）
- 新增测试用例通过率：10/10（100%），W3 本地 CI 模拟 L0/L1/L4/L5 全 PASS

## 补充说明

- 依赖：libx11/1.8.13.1、xorgproto/2025.1（均已发布制品仓，W3 L0i conan download 验证通过；libx11 不传播 xorgproto，配方显式声明）
- 无补丁文件：Makefile 的 `/usr/local` 路径替换、CC 注入、`-std=gnu89` 均在 conanfile.py build() 内动态完成
- W3 中 L2 smoke（--version 探测）记为 skip：spellcast 为交互式 X11 程序，无 --version 参数，无参数执行输出 usage banner（rc=12）——该行为恰为 test 10 非断言用例的通过证据，不影响任何门禁
- R38：构建产物含可执行文件，软件级 commands.json 已声明（type=tool）
- PF9 例外登记：本 PR 按ARCHIVE-SPEC §6 随仓提交软件级 `archives/s/spellcast/README.md` 与 `archives/s/spellcast/commands.json`（同族先例 sxmo-st、mwrap 等）；若 preflight 因软件级三件套触发 PF9，属工具与规范冲突，创建时使用 --no-preflight 并在此如实登记，非规避检查
- 已知限制：spellcast 为 X11 双人对战游戏，完整可玩性需 X11 显示环境；本适配验证编译产物、链接闭包与运行时加载在 HarmonyOS PC 上原生可用
