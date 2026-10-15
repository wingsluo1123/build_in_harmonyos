# 老 libtool 在 OHOS 交叉下共享库探测失败 → 只产静态库（草稿）

- **软件**：yamcha 0.33（http://chasen.org/~taku/software/yamcha/，官方下载失效，源码取自 macports 镜像）
- **构建系统**：上游自带 2005 年前后 autoconf/automake/libtool 生成物（configure + Makefile.in + libtool 脚本），不跑 autoreconf
- **平台**：HarmonyOS PC / aarch64（aarch64-unknown-linux-ohos），OHOS SDK clang 15，conan 2.29.1
- **状态**：DRAFT（`DRAFT-yamcha-0.33-legacy-libtool-shared-probe-no.{kv,md}` 成对）
- **路径**：路径 B（知识库扩展）

## 相关既有条目（撞车判定）

| 条目 | 已覆盖内容 | 本草稿增量 |
|---|---|---|
| E236 | Libtool `.la` 文件优先级、静态依赖被重定位后 libdir 失效、llvm-ar 嵌套归档 | 消费侧问题；本条是**产出侧**：老 libtool 自身在 OHOS 下探测 shared=no，只生成 `.a` |
| E457 | 静态依赖包被嵌入 shared consumer 导致重复拷贝 | 同样是消费/链接侧；不解释"为什么老 libtool 在 OHOS 下不出 .so" |
| cdcd E688 草稿 | 同代 autotools 老包的 config.sub/探测名失配族 | 未覆盖 libtool 共享库能力探测这条路径（cdcd 是 make 期失配，本条是 configure 期 ld 探测失配） |
| E205 / E268 | config.guess/config.sub 的 OHOS 三元组识别 | 不同层：那两条管平台识别，本条管 libtool 链接能力探测 |

结论：无既有条目完整覆盖"老 libtool 共享库能力探测在 OHOS 交叉下确定性失败"这一机制，新建。

## Scope

- 触发面：随包携带 2000s 时代 libtool（`AC_PROG_LIBTOOL` 生成期）的 C/C++ 库在 OHOS 交叉构建下的 conan 配方；
- 同源同代先例：tinysvm/0.09 完全一致（同为 static-library 定型）；
- 不受影响：libtool 2.4+（三元组感知）项目。

## Symptom（真实日志，config.log）

```
configure:6939: checking whether the /Users/metyierzhen/ohos-toolchain/clang linker (/usr/bin/ld) supports shared libraries
configure:7787: result: no
configure:9297: checking if libtool supports shared libraries
configure:9299: result: no
configure:9302: checking whether to build shared libraries
configure:9360: result: no
configure:9363: checking whether to build static libraries
configure:9367: result: yes
```

产物验证：`lib/libyamcha.a`（`current ar archive`），无 `.so`；C 与 C++ 编译器两路 ld 探测（config.log 第 6939 与 10148/11481 行）均 `result: no`。

## Root Cause

老 libtool（1.5 系）的共享库能力判定机制：configure 期让 C 编译器执行一次「link 探测」——解析编译器对应的 linker 路径（本例 `/usr/bin/ld`）并尝试共享链接。OHOS 交叉工具链（clang wrapper 注入 `--target=aarch64-linux-ohos --sysroot=...`）下，该宿主 `/usr/bin/ld` 无法链接 OHOS 目标，探测编译/链接失败即回落 `shared=no`。**老 libtool 的 ld 探测不感知交叉编译**：它信任编译器二进制名解析出的宿主链接器，而不会去解析 wrapper 的真实目标环境。这是工具链与构建系统的能力失配，不是配置错误，`--enable-shared` 救不回（libtool 脚本整体按 static 生成）。

## Recommended Fix / Workaround

conan 配方直接定型静态库，把"static-only 是确定性结果"写进 manifest/notes：

```python
package_type = "static-library"        # 删 options shared 与 --disable-shared 分支
def package_info(self):
    self.cpp_info.libs = ["yamcha"]
```

test_package 按静态消费验证（`find_package(yamcha CONFIG)` 链接 `libyamcha.a`）。

## Fallback

确需 `.so`：升级随包 `config.guess/config.sub` 与 libtool 到三元组感知的现代版本（libtool 2.4+），使 ld 探测正确解析 OHOS 交叉环境；升级不可行则接受 static-only。

## Forbidden Approaches

- `--enable-shared` 期望产出 `.so`：libtool 判定后连脚本都按 static 生成，产物缺失；
- 篡改 libtool 脚本内 linker 路径 / 伪造 `.la` 符号表：环境级 hack、不可复算，test_package 假绿，CI 消费链接时暴露。

## Verification

```
grep -E "checking whether to build (shared|static) libraries" <build>/config.log
# → shared: no / static: yes
file <pkg>/lib/libyamcha.a   # current ar archive
conan create <ver_dir> --profile:build=... --profile:host=...   # rc=0
```

## Prevention

适配 2000s 老 autotools C/C++ 库前先查 config.log 的 shared 探测结论，一次定型 static-library，不要试图抢救 `.so`；评估工具链升级收益后再决定是否换 modern libtool。

## References

- 证据现场：`~/.conan2/p/b/yamch*/b/config.log`（create 迭代日志 `/tmp/yamcha_conan_create8.log`）
- 归档：`archives/y/yamcha/0.33/`（tinysvm/0.09 同型先例 `archives/t/tinysvm/0.09/`）
- 相关条目：E236、E457、cdcd E688 草稿、E205、E268
