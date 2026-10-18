# unicon 3.0.4 适配笔记

## 编译环境
- 构建系统: custom（自制 configure 脚本 + Makefile.in，非 autoconf/cmake）
- 编译日期: 2026-10-15
- 编译器: clang/clang++（OHOS aarch64，.so 需 -fPIC）
- 源码: https://deb.debian.org/debian/pool/main/u/unicon/unicon_3.0.4+dfsg1.orig.tar.xz（Debian 权威镜像，官方 sourceforge 源本机/CI 出口不可达；R39 权威镜像口径，PF7 走官方托管例外：PR 说明 + submit 时 --no-preflight）
- SHA256: 3a7a364d4048da81f58e835e7f9fa60d239c5aa0204afb854264bdcc2c17d155
- 状态: built

## 编译步骤

```bash
./configure --prefix=$PREFIX   # 生成各子目录 Makefile
make                           # 全部产物（7 项）
make -C unicon ccedata gbdata big5data   # 数据三件套（依赖 unicon 主程序先行构建）
make install
```

产物：

| 产物 | 路径 | 说明 |
|------|------|------|
| libimm_server.so | lib/unicon/ | 服务端库（进程内形态） |
| imm_server | bin/ | TCP 守护形态（pthread + socket） |
| libimmclient.a | lib/ | 客户端静态库 |
| unicon | bin/ | 终端输入法主程序 |
| cce_hzinput.so / cce_pinyin.so / gb18030_intcode.so | lib/unicon/modules/cce/ | CCE 输入法模块 |
| cxterm_hzinput.so | lib/unicon/modules/cxterm/ | cxterm 模块 |
| TL_hzinput.so | lib/unicon/modules/turbo/ | turbo 模块 |

## 遇到的问题与解决方案

| # | 文件 | 问题 | 根因 | 解决方案 |
|---|------|------|------|----------|
| 1 | server/client 多文件（17 处） | pth 私有线程库不可用 | pth 为 1990s 私有库，现代环境无 | 全量移植 pth_* → pthread_* |
| 2 | 10 个源文件 | `#include <iostream.h>/<fstream.h>` 报错 | 非标准头已被现代编译器移除 | → `<iostream>/<fstream>` + `using namespace std` |
| 3 | include/ImmDefs.h 等 | u_char/u_long 等 u_* 类型未定义 | 1990s 头文件无 typedef | 守卫式 typedef |
| 4 | client 多文件 | `getline(istream&,char*)` 未声明 | OHOS libcxx 无 C 风格 getline | 手动实现逐字符读取 |
| 5 | SysConfig.cpp 等 | C++98 `gets()` | 现代编译器已移除 gets | fgets / ReadConfigLine |
| 6 | server/TLS_PthSocket.cpp | pth_read/pth_write 依赖 pth | 同 #1 | `::read`/`::write` |
| 7 | server/TLS_Debug.cpp/hpp | 重复默认参数 | 编译器严格化 | 去重 |
| 8 | server/TLS_AsciiConvertor.hpp | X11 头残留 | 上游平台残留 | 删除 → X11 依赖清零 |
| 9 | cce/inputs/tab2dat.c | void 函数 `return 1;` | 现代编译器报错 | → `return;` |
| 10 | cxterm/Makefile.in | dict 再生成引用缺失的 HZutil.c | 上游文件缺失（tit2cit 不可构建） | 摘除 all/clean/distclean 三处 dict 生成，保留 4 个预生成 .cit |
| 11 | cce/hzinput_test.c / intcode_test.c | 未初始化读（vtable 遮蔽） | 局部变量遮蔽模块全局，64 位下未初始化即读 | 去除遮蔽，直接使用模块全局 |
| 12 | cce/xl_pinyin.c LoadPinyinTable | pinyin.map 行缓冲溢出 | str[250]/strhz[241] 小于实际最长行，sscanf 无界 | 缓冲扩 512/400 + `sscanf "%6s %399s"` 有界 + 声母范围检查 |
| 13 | cce/xl_pinyin.c ×2 | 64 位下每条 UsrPhrase 少分配 4 字节 → 堆损坏段错误 | malloc 常数 6/4 硬编码 1990s 32 位结构头（4 字节指针+2）；aarch64 指针 8 字节、结构头 10 字节 | 改 `sizeof(UsrPhrase)` 基线（32/64 位均精确） |
| 14 | client/test.cpp | `<TLC_ImmClient.h>/<TLC_ImmModule.h>` 不存在 | 上游头改名 | → `<ImmClient.h>/<ImmModule.h>` |
| 15 | client/test.cpp | `IMM_KeyPressed` 不存在 | 新版 API 改名 | → `IMM_KeyFilter`（4 参形态） |
| 16 | client/test.cpp | 无输入法数据目录参数 | 数据路径 | 补 `"../dict"` |
| 17 | client/test.cpp | KeyFilter 恒返 0、显示为空 | TLS 层构造默认 `IsHanziInput=0`，未设模式则 KeyFilter 被门控 | 补 `IMM_SetInputMode(IMM_DOUBLE_BYTE_MODE)` |
| 18 | client/TLC_ImmServer.cpp ×3 | `(PSTR) buf` 强转无法绑定 `operator>>(PSTR&)` 左值引用 | clang 严格性（旧 g++ 宽松） | 去强转 |
| 19 | client/TLC_ImmServer.cpp | strlen 未声明 | 缺 include | `#include <string.h>` |
| 20 | server/TLS_TcpipMain.cpp | TCP 形态 handler 线程 Signal 11 | handler 线程 32KB 栈不足以支撑 dlopen + 1990s 深栈模块加载 | pthread 栈 32KB → 256KB |
| 21 | server/TLS_TcpipMain.cpp ×2 | IMM_CLOSE_SERVER 帧处理时崩溃 | 先 `CloseImm`（UnloadImm：`free(pImmSlib)` 且 `pImmOp=NULL`）后 `delete` → 析构访问已释放指针 | 交换顺序：先 delete（析构内做模块清理）后 CloseImm；open 错误路径同修 |
| 22 | server/TLS_TcpipMain.cpp | 服务端 KeyFilter 恒被门控（total:0） | client 发送 IMM_SET_INPUTMODE 帧但 server handler 无对应 case，被 default 分支丢弃 | 补 IMM_SET_INPUTMODE case |
| 23 | Makefile.in（顶层+各子目录 11 个） | CC 硬编码 gcc、无 -fPIC、子目录含 tools/unikey/fonts | 1990s 构建体系 | CC/CXX 环境变量化 + -fPIC + 摘除不可构建子目录 |
| 24 | conanfile.py package() | conan create 全绿但包内 `modules/cce/dict/` 为空（pinyin.map 缺失），consumer test 断言失败 | 上游根 Makefile `install` 与 `data-install` 是独立目标：`install: all` 只装库与模块 .so，cce inputs 数据（`*.tab`/`pinyin.map`/`*.def`）与 turbo gb/gbk/big5 数据只由 `data-install` 安装 | package() 在 `make install` 后补跑 `make data-install`；补跑后 G0-G4+L2/L4/L5 全过，consumer test 实证 dict 入包 |

## 上游测试清点（R51）

- 无测试框架：源码无 tests/ 目录，无 ctest/pytest 注册，Makefile 无 test/check 目标
- 上游测试入口（需手动编译运行，共 3 处）：
  1. `unicon/ImmModules/cce/hzinput_test.c` — 行内输入单位测试
  2. `unicon/ImmModules/cce/intcode_test.c` — GB18030 内码转换测试
  3. `unicon/client/test.cpp` — 交互式输入法客户端（无自动化入口）
- 适配后实测：

| 测试 | 用例数 | 通过 | 说明 |
|------|--------|------|------|
| hzinput_test | 1 | 1 | kexue → 科学（vtable 遮蔽修复后） |
| intcode_test | 2 | 2 | GBK 8140 → 嗀；GB18030 81308139 → 锗 |
| test.cpp（移植后） | 交互式 | PASS | 进程内形态 + TCP 形态均通过，kexue → 1科学 |

## 上游测试用例修改说明（R51）

| 文件 | 修改 | 原因 |
|------|------|------|
| cce/hzinput_test.c | vtable 遮蔽修复 | 64 位下未初始化局部变量遮蔽模块全局导致未初始化读 |
| cce/intcode_test.c | vtable 遮蔽修复 | 同上 |
| client/test.cpp | 4 处移植：2 个 include + KeyPressed→KeyFilter + 模块/数据路径 + 补 SetInputMode | 现代 API 移植（见问题 #14-#17） |
| cce/xl_pinyin.c | 2 处 malloc 改 sizeof 基线 | UsrPhrase 64 位下少分配 4 字节/条 → 堆损坏（见问题 #13） |

注：test.cpp 的 main 返回 1 为上游设计（pass 判据 = 输出内容 + 进程正常退出），未修改。

## 消费者用例

- 新增 `test_package/consumer_test.cpp`（模拟业务上层调用公开 API 全流程）：
  `IMM_OpenClient → IMM_OpenInput → IMM_SetInputMode → IMM_KeyFilter×n → IMM_GetSelectDisplay → IMM_ResetInput → IMM_CloseInput → IMM_CloseClient`
- 硬断言 1：kexue → 科学（GBK 字节序 BF C6 D1 A7）
- 硬断言 2：zhongguo → 中国（GBK 字节序 D6 D0 B9 FA）
- 退出码：0=通过 / 1=断言失败 / 2=环境错误
- 链接形态：`-D__DLL_SUPPORT__` → libimmclient.a + libimm_server.so（进程内，与 unicon 主程序一致）
- 实测：2/2 PASS，exit=0

## 依赖版本

- 第三方依赖：**0**（conanfile requires 为空）
  - pth → pthread（系统库）
  - X11 残留已删（TLS_AsciiConvertor.hpp）
  - newt 随 tools/unikey/fonts 子模块摘除
- 系统工具链：clang/clang++、make

## 验证结果

```bash
# 构建
make                                   # exit=0，7 产物
make -C unicon ccedata gbdata big5data # 各 exit=0

# cce 上游测试
hzinput_test   # 1/1 PASS（kexue→科学）
intcode_test   # 2/2 PASS（GBK 8140→嗀，GB18030 81308139→锗）

# 消费者用例
consumer_test  # 2/2 PASS exit=0（kexue→科学，zhongguo→中国）

# TCP 真并发（imm_server 独立进程 + test_tcp 真 socket，端口 15435）
# 完整会话：open → SetInputMode → kexue+space 按键 → close
# kexue → Selection:: 1科学 2可 3克 4科...
# server 无崩溃；client rc=1（上游 main 设计返回值，非错误）
```

## 注意事项

- 两种运行形态：
  - 进程内：链 libimmclient.a + libimm_server.so（`-D__DLL_SUPPORT__`），TLS_CServerMain 对象直传——消费者用例采用此形态
  - TCP：imm_server 守护进程（pthread handler 线程）+ socket 客户端，帧协议 = 2 字节 short 长度前缀 + payload（PSTR 以 NUL 结尾）
- 模块 .so（cce/cxterm/turbo）由 server 经 dlopen 加载；相对路径 `../ImmModules/...` 以进程 cwd 为基准，或走编译期烧入的 `UNICON_LIB` 前缀
- unicon.ini 与 sys-*.tab 为 server 运行期配置/数据（install 后位于 lib/unicon/）
- G0 干净构建验证的 make_install 步骤为已知非阻塞项：1990s 手写 install 规则不支持 harness 期望的 `DESTDIR=` staging 形态，产物落 `--prefix` 而非 staging 目录判"安装产物为空"；G0 的 configure+make（干净构建）通过，install 完整性由 conan create（G2，含 data-install）与 W3 本地 CI 模拟独立实证（CI 流水线不跑 G0）
- 本机 /tmp 只读，一切临时/测试产物使用 `$TMPDIR`
- 调试取证手段：stderr 未缓冲里程碑标记 + 256KB 栈验证；PollRead/PollWrite 的 `t<0 → continue` 在连接断开后为死循环（上游隐患，未修改——测试中由客户端先退出+服务端 kill 规避）
- 补丁管线说明：0043（client/TLC_Utils.cpp）、0044（server/TLS_AsciiConvertor.hpp）两个补丁为手工生成——refresh-patch 的 `_diff_files` 以 `utf-8 errors=replace` 读取源文件，两文件 diff 上下文含 GBK 中文注释，替换字符导致 `patch --dry-run` 上下文失配而跳过（框架脚本只读，未改）。手工补丁经全量 dry-run + 与 .work 树逐字节一致性双重验证。补丁集定稿后 `.edit-tracker.json` 的 baseline 已推进到最终状态（44 个被改文件 hash 对齐、edited/added 清空），后续 refresh-patch --auto 走"无变更记录，保留现有补丁"分支，不会重生成破坏补丁集；补丁完整性仍由 G0 干净构建与 W3 conan create（全量 conan create 从 orig+44 补丁重建）独立复核
---

**编译结束**: 2026-10-16 14:52
**最终状态**: built
