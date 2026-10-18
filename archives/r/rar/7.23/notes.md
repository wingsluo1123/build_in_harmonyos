# rar 7.23 适配笔记（RARLAB UnRAR）

## 编译环境
- 构建系统: makefile（上游手写 makefile，无 configure/cmake）
- 编译日期: 2026-10-16
- 编译器: OHOS SDK clang++ 15.0.4（aarch64-linux-ohos）
- 状态: built（本地 W3 交叉验证；远程 CI 待回填）

## 版本口径（重要）

任务版本 "7.23" = 上游显示版本 7.23 = 源码包 `unrarsrc-7.2.7.tar.gz`。
依据：源码 `version.hpp` 为 `RARVER_MAJOR=7 RARVER_MINOR=23 RARVER_BETA=0`
（2026-06-27），CLI banner 打印 `UNRAR 7.23`；rarnew.htm 版本史含
"Version 7.23" 正式版。同系列映射：unrarsrc-7.2.3=7.20 beta3、
7.2.4=7.20、7.2.5=7.21 beta1、7.2.6=7.21、7.2.7=7.23（已逐一解包核实）。

## 编译步骤

```bash
make clean
make lib  CXX=<ohos clang++> STRIP=llvm-strip AR=llvm-ar -j4   # -DRARDLL -fPIC
# 保存 libunrar.a / libunrar.so
make clean
make      CXX=<ohos clang++> STRIP=llvm-strip AR=llvm-ar -j4   # -DUNRAR → unrar CLI
```

conanfile.py 的 build() 即按此顺序；CXX/AR 取自 profile
`tools.build:compiler_executables`（R33），STRIP 走 PATH（profile buildenv）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | consio.cpp 调用 getpass() 编译报错 | OHOS musl libc 无 getpass（POSIX.1-2008 已删除；隐式声明在 C++ 下硬错误） | 0001-consio.cpp.patch：getpass 仅 `#elif defined(__GLIBC__)` 下使用，其余平台 fgets(stdin)（patch 内不含 __OHOS__，PF5 合规） |
| 2 | `make lib` 后接着 `make` 链接 unrar 失败（undefined main/mprintf/St） | lib 目标用 -DRARDLL 编译全部对象（无 main、SILENT UI），unrar 目标需 -DUNRAR 对象；makefile 不在目标间 clean | build() 中 lib→保存产物→make clean→unrar 两段式构建 |
| 3 | `make lib` 复用非 PIC 对象链接 .so 失败（R_AARCH64_ADR_PREL_PG_HI21） | 先 build unrar 再 build lib 时对象未加 -fPIC | 同上：先 clean 后 lib（PIC 对象先行），unrar 复用 PIC 对象亦可链接（本配方选择两段 clean 彻底隔离） |

## 源码修改

- `patches/0001-consio.cpp.patch`：见问题 1。glibc 保持原 getpass 行为；
  musl/OHOS/macOS/BSD 走 fgets（口令从 stdin 读取，不回显控制降级为可见输入，
  与 unrar 6.2.4 归档（archives/u/unrar/6.2.4）的处理一致，仅守卫宏换成
  __GLIBC__ 以满足 PF5 补丁平台宏禁令）。

## 依赖版本

无外部依赖（仅 libc/libc++/pthread，全部由 OHOS SDK sysroot 提供）。

## 上游测试清点（R51 三步法）

- 清点：unrarsrc-7.2.7.tar.gz 共 159 个顶层文件，无 tests/ 目录；
  makefile 目标仅 all/unrar/sfx/lib/install/uninstall/clean，
  `make -n check` → "No rule to make target 'check'"。
- 结论：上游测试数 = 0（无正式测试框架，无测试入口）。
- 适配后补全：见 test_package/（libunrar API 4 项 + CLI 功能 3 项 +
  鸿蒙特有 4 项，共 11 个独立检查项）。

## 鸿蒙特有测试（rule12，N=4）

1. C1：unrar ELF e_machine = EM_AARCH64(183)（OHOS PC 目标架构）
2. C2：PT_INTERP = ld-musl-aarch64.so.1（OHOS musl 动态加载器）
3. C3：二进制携带 OHOS codesign 签名（未签名 ELF 在 HarmonyOS 无法 execve）
4. C4：stdin 管道喂口令解密密夹具 encrypted.rar（直接覆盖 consio.cpp
   getpass→fgets 鸿蒙适配点；口令 ohos-rar23，内容字节级比对）

## 测试夹具

- fixtures/plain_rar.b64 / fixtures/encrypted_rar.b64：官方 RAR 7.23
  （rarmacos-arm-723）生成的 RAR5 夹具，base64 文本入库（PF2/JC3 禁二进制
  压缩包入库）。plain 含 hello.txt(93B)+subdir/nested.txt(32B)；
  encrypted 为 -p 数据加密的 hello.txt。
- 期望值自洽：hello.txt sha256=329e766498eb752c9c4740064ee4cf95f6eda4a49d2ace63f6ca891c80a18207，
  内容字面量内嵌于 test_rar.py。
- 本地语义验证（macOS 本机构建同补丁源码）：stdin 口令解密 rc=0 且内容一致；
  错误口令 rc=11 且不落盘。OHOS 上走同一代码路径（同为非 __GLIBC__ 分支）。

## CI 轮次记录

- **CI #95183（红，C 类平台限制）**：L0/JC/KC 全过，conan create 构建通过，
  libunrar API 测试 A1-A4 在 OHOS 真机全过；但 test_package 执行**打包后的**
  `bin/unrar` 报 `PermissionError: [Errno 13] Permission denied`（EACCES）。
- **根因（机制已本地实锤）**：上游 makefile 链接后执行 `llvm-strip unrar`，
  而 llvm-strip 会删除 OHOS lld 链接期写入的 `.codesign` 段——本地用
  llvm-objcopy 给 OHOS ELF 添加 .codesign 段后 llvm-strip 即被剥除（复现实验），
  未签名 ELF 在 HarmonyOS 上拒绝 execve（E128 同类）。
- **修复**：make 变量 `STRIP='llvm-strip --keep-section=.codesign'`
  （保留签名段的正常 strip；无签名段时 no-op，本地实测 rc=0）；
  package() 的 binary-sign-tool 兜底签名保留并补全量日志
  （签名状态/工具路径/结果），test_rar.py 增加 EACCES 诊断输出
  （权限位+签名段标记，区分"未签名"与"HMDFS 丢执行位"）。
- **CI #95259（红，D 类基础设施）**：worker SSH bridge Connection refused，
  步骤未开始即失败，与本包无关。
- **CI #96118（红，根因升级）**：keep-section 后打包产物仍 EACCES；CI 诊断
  显示 `mode=0o100750 codesign=True`——`.codesign` 段结构性存在但已失效。
  对照知识 E452：strip/打包改写产物后，链接期签名对"当前制品"不再成立，
  装载器拒绝执行；唯一可靠形态是对**最终产物强制重签**（去旧段→旁路签名→
  校验→原子替换→复原执行位）。package() 已改为该协议并留全量日志。

## 验证结果

- 本机（macOS + OHOS SDK 交叉）：unrar / libunrar.so / libunrar.a 全部
  编译链接成功，unrar 为 ELF aarch64 PIE（interp /lib/ld-musl-aarch64.so.1）。
- 远程 HarmonyOS CI：#95183 红（上述签名问题，已修复待复验）。

## 注意事项

- OHOS 代码签名：本机 macOS SDK 链接产物无 codesign 段；OHOS worker 的 lld
  链接期通常自带签名（wagyu/rumdl 实测），配方 package() 内置
  binary-sign-tool 兜底自签（签名到旁路文件再原子替换 + chmod 755，
  遵循 tcl/db5.3 实证形态）。
- HMDFS 会丢 chmod 位（E077），签名后已复原 0o755。
---

**编译结束**: 2026-10-17 00:17
**最终状态**: built
