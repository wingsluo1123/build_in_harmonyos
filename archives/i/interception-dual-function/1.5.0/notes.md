# interception-dual-function 1.5.0 适配笔记

## 编译环境

- 构建系统: 裸 Makefile（无 configure）
- 编译日期: 2026-10-13
- 编译器: clang 15.0.4 / clang++（/data/service/hnp/bin）
- 目标平台: OpenHarmony aarch64（aarch64-linux-ohos, musl + libc++）
- 状态: built

## 编译步骤

```bash
# 依赖（Conan 制品仓预编译包，W0 已核验）
yaml-cpp/0.8.0   -> 静态 libyaml-cpp.a
libevdev/1.13.7  -> 动态 libevdev.so.2.3.0

# 上游 Makefile 硬编码 CC=cc / CXX=c++ / INCS / LDFLAGS，全部用命令行变量覆盖
make -j1 \
  CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ \
  INCS="-I<yaml-cpp>/include -I<libevdev>/include/libevdev-1.0" \
  CFLAGS="-pedantic -Wall -Wextra -O3 -std=c99" \
  CXXFLAGS="-pedantic -Wall -Wextra -O3 -std=c++11" \
  LDFLAGS="-rdynamic -L<yaml-cpp>/lib -L<libevdev>/lib -lyaml-cpp -levdev"
```

CPPFLAGS 不覆盖，保持上游 config.mk 原样（`-D_POSIX_C_SOURCE=200809L -DVERSION=\"1.5.0\"`）；
`INCS` 用命令行覆盖即可，因为 config.mk 的 `CPPFLAGS += $(INCS) ...` 会把覆盖后的值拼进去。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 任何含 C++ 侧代码的路径运行即 SIGSEGV（rc=139），`tap`/`hold` 只输出第一个按键事件 | `build_tap()`/`build_hold()` 标量分支：`calloc(node.size(), sizeof(Mapping))`，而 yaml-cpp 对标量节点 `Node::size()` 返回 0 → 只拿到 1 字节可用堆块，随后 `tap->code = ...` 越界写（ASAN: heap-buffer-overflow WRITE of size 4） | 补丁 0001：两处标量分支改为 `calloc(1, sizeof(Mapping))` |
| 2 | `make` 用 `cc`/`c++`（OHOS 上不存在） | 上游 config.mk 硬编码 `CC = cc` / `CXX = c++` | make 命令行覆盖 `CC`/`CXX`（R33：取自 Conan profile 的 compiler_executables） |
| 3 | 编译失败 `fatal error: 'yaml-cpp/yaml.h' file not found` | 上游 `INCS` 只含 libevdev 路径 | make 命令行覆盖 `INCS`，补上 yaml-cpp 的 include 目录 |
| 4 | 上游 `-Werror` 下编译失败 | clang 15 对上游 K&R 风格函数定义（`syn_pause()`/`consume_pressed()`/`loop()`）报 `-Wstrict-prototypes` | 覆盖 CFLAGS/CXXFLAGS 时移除 `-Werror`（其余 `-pedantic -Wall -Wextra -O3 -std=` 保留） |
| 5 | `-lyaml-cpp` 链接为静态库，需 C++ 运行时 | yaml-cpp 制品仓默认 shared=False | 链接步骤由 `$(CXX)`（clang++）执行，C++ 运行时自动带入 |

## 源码修改

补丁 1 枚：

- `0001-cfg.cpp.patch`（`cfg.cpp`，2 处，+2/-2）：
  `build_tap()` / `build_hold()` 的标量（非 sequence）分支由
  `calloc(node.size(), sizeof(Mapping))` 改为 `calloc(1, sizeof(Mapping))`。
  这是上游真实缺陷，与平台宏无关（`platform_only: False`）。

## 依赖版本

| 依赖 | 版本 | 链接方式 | 来源 |
|------|------|----------|------|
| yaml-cpp | 0.8.0 | 静态 | 制品仓 prebuilt（W0 `conan download` rc=0） |
| libevdev | 1.13.7 | 动态（libevdev.so.2） | 制品仓 prebuilt（W0 `conan download` rc=0） |
| linux/input.h 等 UAPI 头 | — | 头文件 | OHOS clang 15 sysroot 自带 |

## 验证结果

上游无自动化测试（无 `tests/`、无 `make test`/`ctest`/`pytest` 入口，清点证据见
`test_package/MANIFEST.yml`）。功能验证以真实二进制 + stdin/stdout 事件流完成：

```bash
$ bash test_package/test_dfk.sh <pkg>/bin      # 上游接口功能 6 断言
PASS T01_tap_synthesizes_tap_key :: expect=[('LEFTSHIFT', 1), ('LEFTSHIFT', 0), ('DELETE', 1), ('DELETE', 0)]
PASS T02_hold_keeps_hold_key
PASS T03_unmapped_key_forwarded
PASS T04_rel_event_forwarded
PASS T05_version_flag
PASS T06_missing_config_exit1
RESULT: 6/6 passed

$ bash test_package/test_ohos.sh <pkg>/bin     # 鸿蒙平台 5 断言
ok   - dual-function-keys is ELF64/AArch64
ok   - interpreter is musl (ld-musl-aarch64.so.1)
ok   - NEEDED contains libevdev.so
ok   - no Linux-only dynamic dependencies
ok   - executes on OHOS (dual-function-keys version 1.5.0)
ok   - scalar TAP/HOLD mapping survived on OHOS musl (calloc(0) regression)
```

补丁前对照（同一事件流，未打补丁的 work 树）：进程 SIGSEGV，rc=139，仅输出第一个
按键事件 —— 即 calloc(0) 越界在 musl 下的必崩表现。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/dual-function-keys | 插件可执行文件（ELF64/AArch64，已 selfSign） |
| share/man/man1/dual-function-keys.1 | man page |
| share/doc/interception-dual-function/dual-function-keys.md | 上游文档 |

## 注意事项

- 该插件是 interception-tools 生态的一环，运行期需要 udevmon 与 `/dev/input`
  设备节点（截获键盘事件流）；无可执行设备环境时以 CLI 契约与事件流回放断言覆盖。
- 上游 `Makefile` 的 `install` 目标默认 `PREFIX=/usr/local`；Conan 包按包内路径
  落 bin/share，不写系统目录。
- **归档名变更（2026-10-14）**：包名由 `interception-dual-function-keys` 改为
  `interception-dual-function`（与比赛清单条目名及平台任务分支名
  `feat/interception-dual-function-1.5.0` 对齐；CI 门禁 L0n 要求分支名去前缀后精确等于
  `归档目录名-版本`，L0m 要求 `conanfile.name` 等于目录名）。上游项目名与产物名
  （`dual-function-keys`）不变，包内路径 `share/doc/` 随之改为
  `share/doc/interception-dual-function/`（由 `self.name` 派生）。
---

### 对话 #1 — 归档名对齐平台任务分支（2026-10-14 ~ 10-16）

**请求**：平台任务（比赛清单条目 `interception-dual-function` 1.5.0）要求 PR 分支名为
`feat/interception-dual-function-1.5.0`；原归档名 `interception-dual-function-keys` 与该分支名
在 CI 门禁下互斥（L0n 要求分支名去前缀后精确等于 `归档目录名-版本`，L0m 要求
`conanfile.name` 等于目录名），故按「包名 + 分支名一起改名」处理。

**执行与验证（本地与 CI 同源脚本，`CI_BRANCH=feat/interception-dual-function-1.5.0`）**：

1. `git mv archives/i/interception-dual-function-keys archives/i/interception-dual-function`
   （上游项目名与产物名 `dual-function-keys` 保持不变）。
2. 同步 `conanfile.py`（`name` / 类名 / 注释）、`commands.json`、两级 `manifest.yaml`、
   `test_package/MANIFEST.yml`、README / notes / 测试提示文本、知识草稿引用。
3. `zsh ci/conan/setup.sh` → `SETUP_RC=0`。
4. `zsh ci/conan/build_and_test.sh archives/i/interception-dual-function/1.5.0`：
   - `L0n: [ok] branch 'feat/interception-dual-function-1.5.0' matches
     'interception-dual-function-1.5.0' exactly (prefix allowed)`
   - `L0m: directory structure valid`；`L0_RESULT=pass: all checks passed`；
     `L1_RESULT=pass: test_package executed`；`L4_RESULT=pass: patches clean`；
     `L5_RESULT=pass: bin/ has content`；`JC_RESULT=pass`；`Pass rate: 100.0% (1/1)`
5. `conan create`（包引用 `interception-dual-function/1.5.0`）→ `[ok] … conan create passed`；
   test_package：`test_dfk.py` T01–T06 全 PASS（`RESULT: 6/6 passed`）、`test_ohos.sh`
   `all interception-dual-function HarmonyOS assertions passed`。
6. `python3 scripts/ohc-run.py finish interception-dual-function 1.5.0 built`：
   conan-verify G0-G4 PASS、W3 本地 CI 通过；`.ci-result.json` `exit_code=0`
   （`integrity_hash=1e5c775337cbb40d`）。
7. 包内路径实测：`bin/dual-function-keys`、`share/man/man1/dual-function-keys.1`、
   `share/doc/interception-dual-function/dual-function-keys.md`（由 `self.name` 派生，改名后随动）。

---

**编译结束**: 2026-10-16 12:04
**最终状态**: built
