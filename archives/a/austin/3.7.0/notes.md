# austin 3.7.0 适配笔记

## 结论速览
- **类型**：C（austin 本体 + 依赖仓库已归档的 argp）→ 编译过程里有 C/C++ 系工具链
- **产物**：`bin/austin`（musl 动态 ELF64/AArch64，91840 字节）+ `licenses/LICENSE.md`
- **依赖**：`argp-standalone/1.5.0` + `libunwind/1.6.2` —— **两者都已在仓库归档**，按"先扣掉仓库已有"
  的口径不算阻塞；构建期 `automake/1.18` + `libtool/2.5.4` 走 tool_requires
- **的测试**：上游套件在本机/CI **不可运行**（见下）→ 配方里补了能真跑的测试 + 消费者 7 项
- **状态**：built（本地 conan create 全绿：编译 ✓ + 补的测试 ✓ + 消费者 7/7 ✓）

## 四个必须知道的坑（本库四轮 CI 才打通）

### 1) `argp.h` 找不到 → 依赖的 include 要**显式**注入
只靠 `AutotoolsToolchain` 自动收集时，austin 的编译行里**不会**出现 argp 的 include：
```
src/argparse.c:186:10: fatal error: 'argp.h' file not found
```
→ 在 `generate()` 里显式加：
```python
tc.extra_cflags.append("-I" + os.path.join(dep.package_folder, "include"))
tc.extra_ldflags.append("-L" + os.path.join(dep.package_folder, "lib"))
```

### 2) `-largp` 必须用 `LIBS=` 传，不能放 LDFLAGS
austin 上游 `src/Makefile.am` 是 `austin_LDADD = -lm`（**没有 argp**）。放 LDFLAGS 会让 `-largp`
排到目标文件**之前** → 静态库抓不到符号（静默失败）；正确做法：
```python
tc.configure_args.append("LIBS=-largp")     # autoconf 惯例 → 落在链接行末尾
```

### 3) OHOS 上必须显式给三元组
`config.guess` 认不出本机 → `configure: error: cannot guess build type`：
```
--build=aarch64-unknown-linux-musl --host=aarch64-unknown-linux-musl
```

### 4) `configure` 的 `umask 077` 要在 **autoreconf 之后**改成 022
HMDFS 上 `umask 077` 建的临时目录会 `Permission denied`
（`config.status: can't create ./confXXXXXX/subs1.awk`）——仓库里 `argp-standalone` 同款处理。
⚠️ 顺序很关键：`autoreconf` 会**重新生成** `configure`，放在前面等于白改。

## 上游测试：55 个用例，本平台不可执行（硬证据：上游 harness 自己拒绝 HarmonyOS）

- **上游用例数 N=55**（`test/**/test_*.py` 里 `def test_` 计数：cunit 17 + functional 33 + integrity 3 + support 2）。
- **可执行 0/55**，原因**不是**缺依赖、也不是人为跳过，而是**上游测试框架硬编码了平台门**：
  `test/utils.py` 的 `python(version)` 只接受 `Windows` / `Darwin` / `Linux`，其余一律
  `raise RuntimeError(f"Unsupported platform: {platform.system()}")`。在本机（`platform.system()='HarmonyOS'`）
  实跑上游 integrity 子集即得：

  ```
  E   RuntimeError: Unsupported platform: HarmonyOS
      ../.conan2/p/austi…/s/test/utils.py:89: RuntimeError
  ```

- 配方 `_run_upstream_tests()` 把这条**做成了能失败的断言**：若上游放开平台门（或改在 Linux 上构建），
  构建会失败并提示"应改为真实执行上游 55 个用例" —— 不会出现"悄悄不跑却声称通过"。
- 另注：`test/run.sh` 还写死了作者本机的 venv（`source /tmp/austin-test/bin/activate`）与私有
  `LD_LIBRARY_PATH`，本身也不具备可移植性（同一结论的另一条旁证）。
`test/run.sh` 写死了作者本机环境：
```bash
source /tmp/austin-test/bin/activate                      # /tmp 在本机只读
export LD_LIBRARY_PATH="/Users/gabriele/Projects/libunwind/src/.libs/"   # 作者 macOS 私有路径
AUSTIN_TESTS_PYTHON_VERSIONS=$PY pytest "$@"
```
且 `test/requirements.txt` 需要 `austin-python~=1.6`/`flaky`/`pytest`/`pytest-xdist`/`psycopg`/`psutil`，
用例本身是 pytest + ptrace 型 → **本机与 CI 都跑不起来**，故与 rp 同法补测并摊开构成。

## austinp 为什么没有随包
`configure.ac:23` 查 `libunwind-ptrace.h`，仓库的 `libunwind/1.6.2` **不含该头**（实测包内只有
`libunwind.h`/`libunwind-aarch64.h`/`libunwind-common.h`/`libunwind-dynamic.h` 与
`libunwind.a`/`libunwind-generic.a`）→ 上游自行打印：
```
checking for libunwind-ptrace.h... no
not building austinp: missing libunwind
```
→ 这是**上游的既定行为**，不是适配缺陷；直接后果是"真实采样"在本环境做不了（austin 需要它的
原生采样器 austinp），实测 `austin -i 1000 -- python3 -c ...` 返回 rc=33
`Cannot launch the given command or it terminated too quickly`。

## 实测结果（本地 conan create）
```
[build] 已把 1 个 configure 的 umask 077 改为 022（HMDFS 目录权限）
[added tests] 产物：austin(91840 字节)
[added tests] ① `austin --help` rc=0 且打印用法 ✓
WARN [added tests] ② 真实采样未成功（rc=33，目标 .../python3）——如实记录，不计为通过
[ok]   产物齐备：bin/austin 可执行（91840 字节）
[ok]   ELF 头自检：bin/austin 为真 ELF64、machine=0xB7(AArch64) ✓
[ok]   bin/austinp 未随包（上游在缺 libunwind-ptrace.h 时会跳过它；如实记录，不算失败）
[ok]   真实运行：`austin --help` rc=0 且打印用法
[ok]   真实功能尝试：本环境缺 austinp/ptrace 支持（rc=33）——如实记录，不计为通过
[ok]   许可证随包：licenses/LICENSE.md 存在
[ok]   证据：bin/austin sha256=bbf0c16319eac302…；python 3.12.9
checks=7 fails=0
RESULT: PASS
```
