# genometools 1.6.2 适配 notes

## 状态：shadow CI 全绿（r13，L0–L5 全 pass，exit 0）

- 评审修正（2026-10-12，Septest rule4 少报）：上游 `gt -test` 实测 **79 项**全过，
  此前按"1 个套件"声明属少报，manifest/PR 已改为 79/79（100%）。
- 评审修正（rule6）：知识草稿提交（ae3ff550）晚于上次 AI 检视，需触发重新检视。
- 分支：`feat/genometools-1.6.2`
- worktree：`D:\harmonyos\worktrees\genometools`（sparse 排除 `archives/g/gama/`，
  规避 origin/main Windows 非法文件名 `…gama…patch??`——见 ltrsift notes 复用知识）
- 动因：ltrsift/1.0.2 的阻塞依赖（制品仓 0 配方，PR !14618 待本包落地回填）
- 真机 run：`ohos-test-runs/codex-1.6.2-genometools-…-164700-36921`（排队 735s）

## 真机 r13 门禁结果（最终轮）

| 门禁 | 结果 |
|---|---|
| G0/KC/JC/L0 | pass |
| L1 | pass（`bin/gt -test` 上游内建单元测试于 build() 执行，0 failures；L1c 官方认证） |
| L1e | pass：Negative test confirmed（破坏产物后 test 失败，真依赖） |
| L2 | pass：gt --version OK（裸环境，$ORIGIN RUNPATH 生效） |
| L4 | pass（无补丁） |
| L5 | pass（SONAME libgenometools.so.1 + bin/ 有内容） |
| test_package | 消费者探针 7 断言 × conanrun/裸环境两轮全过 + gt -version 冒烟 |

## 迭代记录（r1→r13）

| 轮 | 报错原文（摘） | 根因 | 解法 |
|---|---|---|---|
| r1 | `EnvVars object has no attribute define`（generate()） | 设备端 conan 版本 API 差异 | 删 generate()/Environment，TMPDIR/HOME 改 make 前内联变量 |
| r2 | `encseq.c: error: -Werror,-Wunused-but-set-variable` | 上游 errorcheck 默认开 -Werror | `errorcheck=no`（同 ltrsift/E625 先例） |
| r3 | `rcr.c: 'samtools/sam.h' not found` | tarball 内 samtools/ 为符号链接头文件，HMDFS 解包后为空目录 | source() 里用真实文件镜像 samtools/*.h（幂等） |
| r4 | `ld.lld: duplicate symbol: XML_*` | expat 对象同时经目录通配与 lib/libexpat.a 进链接；GNU ld 容忍、lld 判重 | `-Wl,--allow-multiple-definition`（恢复 GNU ld 语义） |
| r5 | test_package：`annotationsketch/block_api.h not found` | genometools.h 无条件 include 该目录 | package() 补齐 annotationsketch 头（cairo 只裁实现） |
| r6 | `canvas_cairo_context_api.h: 'cairo.h' not found` | genometools.h 的 `#ifndef WITHOUT_CAIRO` 守卫需消费者提供宏 | package_info `defines=["WITHOUT_CAIRO"]`（test_package 同步 -D） |
| r7-9 | probe `Assertion (ma) failed` → SIGSEGV | 未初始化全局内存分配器 | 探针先 `gt_ma_init(false)`、结束 `gt_ma_clean()` |
| r10 | SIGSEGV in `gt_hashmap_delete` | 探针 key 用字符串字面量却注册 gt_free_func（delete 时 free 栈地址） | key 改 `gt_cstr_dup` 堆分配 |
| r11 | `L5 fail: soname_gate_failed` | 上游 .so 无版本化 SONAME | 链接期 `-Wl,-soname,libgenometools.so.1` + 打包 .so.1/symlink |
| r12 | L5 仍 fail（误判） | 门禁 readelf 不在 runner PATH，`|| true` 吞错判空 | job env.sh PATH 前置 `/data/service/hnp/bin`（job 本地配置，非基础设施改动） |

## W0 依赖结论

```text
依赖数量：0（conan requirements 为空）
已满足依赖：—（无）
缺失依赖：—（无）
是否需要拆分依赖适配：否
阻塞点：无（构建工具链也不需要：手写 Makefile，非 autotools）
下一步：已完成真机验证 → 提 PR
```

关键事实：上游以 `useshared=no` 默认把 `src/external/`（zlib 1.2.8、expat 2.0.1、
bzip2 1.0.6、lua 5.1.5、luafilesystem、lpeg、md5、samtools 0.1.18、sqlite、tre）
**内置静态编译**进 libgenometools——"依赖重"是错觉；pkg-config 探测只在
`useshared=yes` 或启用 cairo 时引入依赖，`cairo=no` 后全部绕开。

## lang-preflight 说明（mixed 误判，附交付物证据）

`ohc-run.py lang-preflight` 返回 detected=mixed（task=cpp）：触发源是
`gtpython/setup.py` —— 探测器对 setup.py 做**全树递归**匹配。交付物证据：

- 交付物是 C 库 `libgenometools.so`（顶层手写 Makefile，938 个 .c 占源码 76%）；
- `gtpython/` 是 **ctypes 纯 Python 消费者封装**（dlload.py 运行时 dlopen
  libgenometools.so，无任何编译扩展），不是构建系统，`make all` 完全不经过它；
- 参照 onnx 1.20.0 判例（DRAFT-onnx-…-lang-preflight-pyproject-priority-cpp-deliverable-misdetect）：
  绑定型双语言仓库、交付物为 C/C++ 库 → 按 cpp 适配，语言结论以平台检查为准。

## W1 构建系统分析

- 手写 GNUmakefile（1090 行），无 configure/CMake。变量契约：
  `CC/CXX`（默认 gcc/g++ → 传 clang/clang++）、`64bit=yes/no`（有显式开关）、
  `cairo=no`（关 annotationsketch + GOTAGS）、`sharedlib`（默认 yes）、
  `fpic`（默认 yes）、`useshared`（保持 no）、`errorcheck`（默认 -Werror → 关）。
- `ld -V | grep GNU` 探测决定是否用 version-script；设备 HAS_GNU_LD 路径正常。
- 产物：`lib/libgenometools.so`（无版本化 SONAME → 配方注入 .so.1）+ `.a` + `bin/gt`。
- 安装布局（配方复刻）：`include/genometools/{core,extended,ltr,annotationsketch,…}/*_api.h`
  + `src/genometools.h` + `obj/gt_config.h`；上游 install 用 `cp -a`
  （HMDFS 无 symlink，配方用 copy 重放）。
- **Windows 解包坑**：tarball 内 `src/external/samtools-0.1.18/samtools`
  （符号链接）等在 Windows 解压报 Invalid argument——仅影响 Windows 本地审计。

## 上游测试审计（真机实测）

- `bin/gt -test`：C 内建单元测试全过（run 日志 164700-36921，0 failures），
  由 build() 在构建后执行，L1c 门禁认证"上游官方测试已在构建阶段执行"。
- `testsuite/`：`testsuite.rb`（Ruby 驱动）——设备无 ruby 解释器，属缺工具
  依赖，如实登记 not_run，不计入通过数、不伪装平台限制。

## 平台预案落地情况

- ✅ `$ORIGIN/../lib` RUNPATH（L2 裸环境 gt --version 通过）
- ✅ 包内 TMPDIR/HOME（make 前内联变量）
- ✅ commands.json（R38）
- ✅ SONAME 注入 + 版本化布局（L5a）
- ✅ HMDFS 无 symlink：samtools 头镜像 + 打包 symlink 失败退化实体副本

## 遗留

- testsuite/（Ruby）未执行：如上，缺工具依赖，如实登记。
- ltrsift 回填：genometools PR 合入、制品发布后，ltrsift 重跑 shadow CI
  （r13 已证明同 job 缓存内 ltrsift 依赖解析可行，见后续联合验证记录）。
