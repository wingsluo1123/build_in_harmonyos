## PR 信息

- **三方库名称**：libdbusmenu-glib
- **上游版本**：16.04.0
- **上游仓库地址**：https://launchpad.net/libdbusmenu
- **适配路径**：路径 A（基础适配） / 路径 B（贡献创新）
- **使用知识库**：E348、E480、E452、E7009及E2026101613119-draft-A139。
- 官方发布源码：760376bytes，SHA256 b9cc4a2acd74509435892823607d966d424bd9ad5d0b00938f27240a1bfa878a。沿用任务13119及现有PR14388。

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 1 | 原objects TESTS入口，内部9个子例单列 |
| 集成测试 | 7 | 原events、events-nogroup、layout、properties、proxy、simple-items、submenu |
| 其他测试 | 0 | 本GLib子包的原默认入口无额外组 |
| **合计** | **8** | 以原tests/Makefile.am TESTS登记为分母；15个编译程序不重复计入口 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 1 | 不变 | objects原9个内部子例全部通过 |
| 集成测试 | 13 | +6 | 原7组，加安装API消费者6个登记项 |
| 鸿蒙特有测试 | 1 | 新增 | 实际HarmonyOS aarch64、UID自有0700存储的菜单属性/GVariant回读 |
| **合计** | **15** | **+7** | 重复create、编译helper及子断言不累加 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

四个原始数据头test-glib-layout.h、properties.h、proxy.h、submenu.h共373处GNU旧式id:/properties:/submenu:改为等价C99指定初始化。字段名、值、结构、原程序参数与断言均不变，保留-Wall/-Werror/-DG_DISABLE_DEPRECATED；原Makefile.am字节不变。另有产品menuitem.c的child_find循环条件修复，及新的消费者回归。五项.patch均由官方refresh-patch --auto生成并完成dry-run。原8组无跳过或裁剪。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

保留原8个入口和15个编译程序，另增已安装库API消费者6项，包括child_find空链、首/次项、未命中和删除后查找；Harmony1项验证真实UID私有存储和菜单数据往返。CMake消费者实际编译、链接、签名后运行。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：8/8（100%）
- 新增测试用例通过率：7/7（100%）

libdbusmenu-glib-16.04.0-official-20261016-r1289同一不可变事务内两次实际正式create，各原8/8入口、15编译程序、消费者6/6、Harmony1/1，零失败/跳过。官方Finish35、15回执/30WAL、唯一launch、自有进程0及release/postrelease均核验。观察SHA256 7f3efb7bd15f106135d3df45659bdf574faa8e7c7bc43b7c9423999ef4ec9d3a；W3日志SHA256 ca1ea00d3a0f87985927093eead87bfd3a81c01152d264707cef0ae405d231b7。

正式CI121774/build108615在原始objects入口启动发布gtester时被系统拒绝（Operation not permitted），原始断言尚未开始。独立r1287在同一运行库闭包对照：原始发布gtester为EPERM(errno1)，私有重签副本--help RC0，发布文件字节不变。复用E452：将已声明GLib2.84.0.1的gtester及同版libglib-2.0.so.0/libintl.so.8复制到当前数字UID所有0700临时目录，使用真实SDK签名并逐一核对原provider字节未改；原Makefile生成器仅把gtester执行路径绑定为此副本。保持原8入口、15程序、9个objects断言、全部参数、严格警告与300秒预算。libdbusmenu-glib-16.04.0-official-20261016-r1289准备阶段特意不预先重签发布gtester，两次正式create均原8/8、消费者6/6、Harmony1/1，独立审计确认唯一launch、自有进程0及release/postrelease。每轮私有副本及总线根均由上下文清理。存在codesign段不等于当前执行签名有效，实际平台CI仍按新HEAD另验。

---

## 补充说明

- 关联 Issue：[!3699](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3699)
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/libdbusmenu-glib-16.04.0
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：Conan命令值编译器须拆成实际可执行文件和CMAKE_C_COMPILER_ARG1保留必需wrapper参数；结合公开GLib头/库传递及实际build_folder/bindir绝对路径，使原始多进程套件之后的CMake消费者真实编译、签名、执行。保留旧失败，新增child_find空链、两项命中、未命中及删除后查找回归。 本次原始gtester测试辅助工具复用E452私有ELF副本重新签名规则，新增原始发布字节EPERM与私有签名RC0的对照证据及不修改provider缓存的真实原套件验证，不另造通用签名知识。 平台CI和Review按新提交完整核验后提审；合并及正式制品下载另行回读。
