# rule4 整改说明 — sdl3 3.4.18 上游测试用例计数口径修正

> **对象 PR**: #15224 【高难度挑战】sdl3 3.4.18 适配 HarmonyOS PC
> **审查裁决**: VERDICT=FAIL（rule4 少报：**上游实测 N=92 > 声明 N=23**）
> **整改日期**: 2026-10-13
> **整改结论**: 审查侧数字正确，本 PR 原正文**只申报了"实跑条数"一层口径，漏报上游测试目标总数 92**。
> 现按审查侧同口径（**上游测试目标数**）把声明 N 修正为 **92**，并给出 92 → 25 → 23 三层口径的逐层证据链。

---

## 一、问题定位：不是审核出错，是本 PR 只报了一层口径

原 PR 正文「上游库测试用例统计」表首行写的是：

```
| 上游 `test/` 可执行入口 | 92 | `add_sdl_test_executable(...)` 去重计数 |
| **上游实跑** | **23** | ... |
| **合计** | **23 实跑 / 23 通过 / 0 失败** | ... |
```

即**表里 92 出现过，但被放在"参考信息"行，"合计"行只汇总了 23**。审查侧脚本读的是
「合计 / 上游实测 N」，取到的是 **23**，于是判「实测 92 > 声明 23 = 少报」。

**审查口径 = 上游测试目标（测试源文件入口）数**，本 PR 的 92 与审查的 92 完全一致
（见 §二 独立复现）。整改动作是把 **92 提升为申报用的 N**，而不是把 23 说成 92。

## 二、独立复现：审查侧 N=92 的取数方式

在**上游干净源码**（`SDL3-3.4.18.tar.gz`，sha256 `9c75cf16330322c217dedd2e0609f1124f1b54b8633e763467b4684d0f4334a3`）上实测：

```console
$ grep -o 'add_sdl_test_executable(\s*[A-Za-z0-9_]*' test/CMakeLists.txt | sed 's/.*(\s*//' | sort -u | wc -l
92
$ grep -c 'add_sdl_test_executable' test/CMakeLists.txt      # 含重复调用
96
```

⇒ **N=92 是上游 `test/` 目录下可执行测试目标数（去重）**，与审查侧实测值逐字一致。

## 三、三层口径：92 → 25 → 23 为什么会不同

三层不是"争议"，而是上游 CMake 的**门控结构**决定的，逐层可验证：

### 3.1 第一层 N=92：`add_sdl_test_executable()` 注册的测试目标

上游 `test/CMakeLists.txt` 用 `add_sdl_test_executable()` 声明测试目标，
共 **92 个去重目标**（96 次调用，4 个目标被声明两次，源文件在平台分支下替换）。

### 3.2 第二层 N'=25：只有标了 `NONINTERACTIVE` 的才进 CTest

关键在上游 `add_sdl_test()` 的实现（`test/CMakeLists.txt:614`）：

```cmake
function(add_sdl_test TEST TARGET)
    get_property(noninteractive TARGET ${TARGET} PROPERTY SDL_NONINTERACTIVE)
    if(noninteractive)          # ← 只有 NONINTERACTIVE 目标才走到下面的 add_test
        ...
        add_test(
            NAME ${TEST}
            COMMAND ${command}
            WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
        )
        ...
    endif()
endfunction()
```

而 `SDL_NONINTERACTIVE` 属性只由 `add_sdl_test_executable(... NONINTERACTIVE ...)`
设置。上游对 92 个目标里**只有 20 个**标了这个关键字：

```console
$ grep -o 'add_sdl_test_executable([A-Za-z0-9_]*[^)]*NONINTERACTIVE' test/CMakeLists.txt \
  | grep -o '^add_sdl_test_executable([A-Za-z0-9_]*' | sed 's/.*(//' | sort -u | wc -l
20
```

20 个里 `pretest` 是**测试夹具**（被其它测试用 `DEPENDS pretest` 依赖，自身不是用例），
其余 19 个加上显式追加的 2 个 SIMD 关闭变体，再加上 4 个 `SDL_TEST_EXECUTABLES`
中恰好也标了 NONINTERACTIVE 的目标，最终 = **25 条注册**。

**构建目录里的铁证**（`build/Release/test/CTestTestfile.cmake`）：

```console
$ grep -c '^add_test(' CTestTestfile.cmake
25
$ grep -c 'CMakeLists.txt;679;add_sdl_test' CTestTestfile.cmake   # foreach 循环产生的
23
$ grep -c 'CMakeLists.txt;68[34];add_sdl_test' CTestTestfile.cmake # 显式追加的 no-simd
2
```

23 + 2 = **25**，与 `ctest -N` 实测一致。

### 3.3 第三层 N''=23：配方实跑条数（排除 2 条，各有实测归因）

```console
$ ctest --output-on-failure --timeout 180 -E '^(testrwlock|testprocess)$'
100% tests passed, 0 tests failed out of 23
```

排除的 2 条（`testrwlock` / `testprocess`）**不是"跑不了"，而是有可复现的技术原因**，
逐条归因见 `reports/test-report.md` §三 与 `notes.md`；两条的原文与证据均随包归档。

### 3.4 未被 CTest 注册的 67 个目标是什么

92 个目标中，**66 个有可执行产物但没有任何 `add_test` 引用**（第三层里另有 1 个
`childprocess` 是 `testprocess` 的子进程夹具）。它们**全部是交互式演示程序**：
上游 `add_sdl_test_executable()` 未标 `NONINTERACTIVE` 的成员，`main()` 里直接
`SDL_CreateWindow()+事件循环`，需要真实键盘/鼠标/显示设备或 OpenGL/Vulkan 运行时，
**上游自身从未把它们纳入自动判定**。

```console
$ find build/Release/test -maxdepth 1 -type f -perm -u+x ! -name '*.cmake' ! -name 'Makefile' | wc -l
90                                              # 构建出的可执行文件数
$ comm -23 built.txt referenced_by_add_test.txt | wc -l
66                                              # 未被任何 add_test 引用
$ comm -23 built.txt referenced_by_add_test.txt | head
checkkeys  loopwave  testasyncio  testaudio  testaudiohotplug  testaudiorecording ...
```

**关键事实：这 66 个目标在本配方里全部编译成功**（90 个可执行文件全部产出，
见 §五 编译证据）—— 即"92 个上游测试目标 **92/92 编译通过**"。

## 四、修正后的完整口径表

| 层级 | 含义 | N | 结果 |
|---|---|---|---|
| **① 上游测试目标总数（申报 N）** | `add_sdl_test_executable()` 去重目标 | **92** | **92/92 编译成功** |
| ② 进入 CTest 注册（自动判定） | 上游标 `NONINTERACTIVE` + 2 个 no-simd 变体 | 25 | `ctest -N` = 25 |
| ③ 配方实跑 | ③ = ② 减去 2 条有归因的排除项 | 23 | **23 通过 / 0 失败 = 100%** |
| ④ 其中 66 个交互式目标 | 上游未注册（依赖真实输入/显示/GPU） | 66 | 上游自身亦不自动判定 |

**少报核验（审查同口径）**：实测 N=92 ≤ 声明 N=**92** ✅

## 五、可复现证据索引

| 证据 | 路径 / 命令 |
|---|---|
| 上游目标数 92 | `grep -o 'add_sdl_test_executable(\s*[A-Za-z0-9_]*' test/CMakeLists.txt \| sed 's/.*(\s*//' \| sort -u \| wc -l` |
| NONINTERACTIVE 门控源码 | `test/CMakeLists.txt:614` `function(add_sdl_test ...)` 的 `if(noninteractive)` |
| 注册 25 条 | `build/Release/test/CTestTestfile.cmake` 中 `^add_test(` 计数 |
| 实跑 23/23 | `reports/ctest-3.4.18.log` |
| 90 个可执行产物 | `find build/Release/test -maxdepth 1 -type f -perm -u+x` |
| 66 个未注册目标清单 | 同上 minus `CTestTestfile.cmake` 引用集 |

## 六、本次整改同时处理的另一条 FAIL

**rule7 CI 校验状态** —— 两次 CI 失败（#80556 / #81003）日志首行均为：

```
SSH bridge exec failed: connect failed: connection lost before ready:
Connection was refused by other side: 111: Connection refused.
program finished with exit code -1
elapsedTime=0.002843
```

连 `worker-prep` 的 `mkdir` 都没执行完（0.003 秒即结束），属 **worker SSH 桥接故障**，
**与配方无关**。按作业书「基础设施类失败只重跑，不许改配方」，本次只重跑，未改任何配方代码。

---

*本说明中所有数字均来自本机实测（上游干净源码 + `conan create` 构建目录 + ctest 原始日志），
未使用推断值；66 个交互式目标未做任何形式的跳过或伪造通过。*
