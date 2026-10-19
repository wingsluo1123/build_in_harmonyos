# DRAFT-ohos-private-build-flow-genmakefiles-wiring

> 维护者复审候选草稿（Path B 知识扩展材料）；**不自动作为 Path B 评级或分值依据**。

## 现象（live555 2026.08.14 本机实测）

live555 用私有流程构建：`./genMakefiles <platform>` 生成各子目录 Makefile（`cat $subdir/Makefile.head config.<platform> $subdir/Makefile.tail`），
再 `make`。直接套用 autotools/cmake 的经验会连撞四类问题：

```
# ① 三元组写错 → 找不到 OHOS sysroot
fatal error: 'sys/types.h' file not found      # 因为写的是 --target=aarch64-linux（缺 -ohos）

# ② 走上游 install → 遍历未构建的子目录
make: *** No rule to make target 'install'.  Stop.

# ③ 消费者不带宏 → 打包头一 include 就失败
…/include/liveMedia/TLSState.hh:34:10: fatal error: 'openssl/ssl.h' file not found   # 消费者未带 -DNO_OPENSSL=1
```

## 处置范式（可直接复用到其它私有流程）

1. **构建期生成 `config.<platform>`**（没有任何自动探测，编译器/归档器/三元组/宏都要写死）：

```python
cc  = conf["tools.build:compiler_executables"]["c"]      # /data/service/hnp/bin/clang
cxx = conf["tools.build:compiler_executables"]["cpp"]    # …/clang++
ar  = os.path.join(os.path.dirname(cc), "llvm-ar")
COMPILE_OPTS = "-fPIC -O2 -DNO_OPENSSL=1 -DSOCKLEN_T=socklen_t -D_FILE_OFFSET_BITS=64 --target=aarch64-linux-ohos"
```

> **关键**：三元组必须是 `--target=aarch64-linux-ohos`（写 `aarch64-linux` 时 clang 不会去找 OHOS sysroot）。

2. **只驱动需要的子目录**：`liveMedia / groupsock / UsageEnvironment / BasicUsageEnvironment`；
   `testProgs / mediaServer / proxyServer / hlsProxy` 不构建（省时且避免无关失败）。

3. **不走上游 `make install`**（它遍历全部 8 个子目录，未构建者报错），由 recipe 显式收集产物：

```python
for subdir in _SUBDIRS:
    copy(self, "*.a", src=<subdir>, dst="lib", keep_path=False)                    # 静态库 → lib/
    copy(self, "*.hh", src=<subdir>/include, dst=f"include/{subdir}", keep_path=False)  # 头 → include/<subdir>/
```

4. **导出消费者必需的宏**：打包头用 `#ifndef NO_OPENSSL` 守卫 `<openssl/ssl.h>` →
   `self.cpp_info.defines = ["NO_OPENSSL=1"]`，否则任何消费者 include `liveMedia.hh` 都会失败。

5. **includedirs 兼容两种写法**：`["include", "include/liveMedia", "include/groupsock", …]`，
   同时满足 `#include <liveMedia/liveMedia.hh>`（上游布局 / MPlayer 的 `--enable-live` 探测）与非限定写法。

## 验证

```
conan create archives/l/live555/2026.08.14 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing   # rc=0
live555 basic usage environment ok
live555 liveMedia/BasicUsageEnvironment 可用性检查通过
```

（消费者测试包含 `<liveMedia/liveMedia.hh>` 等聚合头 + 构造 `BasicTaskScheduler`/`BasicUsageEnvironment`，全程离线、真实 API 调用。）

## 证据

- `archives/l/live555/2026.08.14/conanfile.py`（`_write_config()` / `build()` / `package()` / `package_info()`）
- `archives/l/live555/2026.08.14/notes.md`（换源与四类接线要点的完整记录）
- `archives/l/live555/2026.08.14/reports/pr-body.md`
