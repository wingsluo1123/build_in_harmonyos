# ming (libming) 0.4.8.r68.g04aee523 适配笔记

## 编译环境
- 构建系统: autotools（**源码包不含生成好的 `configure`**，只有 `configure.ac`/`Makefile.am`，须 autoreconf 自举）
- 编译日期: 2026-10-14
- 编译器: clang 15.0.4 / clang++（`/data/service/hnp/bin/clang`）
- 平台: HarmonyOS / aarch64（HongMeng Kernel 1.12.0），原生构建（非交叉）
- 状态: built（conan create 端到端通过；等 commit 授权后重跑 finish 生成 .ci-result.json）

## 版本号来源（可复现的核对方式）
分支版本 `0.4.8.r68.g04aee523` 是 git describe 形态。核对方法：
`curl https://api.github.com/repos/libming/libming/compare/ming-0_4_8...04aee52363688426eab74f5d6180c149654a6473`
→ `total_commits: 68`，与版本号中的 `r68` 逐位吻合；tag 为 `ming-0_4_8`。

## 编译步骤

```bash
# 1. 归档骨架 + 源码（codeload 为 GitHub 官方归档主机，github.com/.../archive 在本机不可达）
python3 $SKILL_ROOT/scripts/ohc-run.py init-build ming 0.4.8.r68.g04aee523 \
  --url="https://codeload.github.com/libming/libming/tar.gz/04aee52363688426eab74f5d6180c149654a6473"

# 2. 语言预检（R47）
python3 scripts/ohc-run.py lang-preflight ming 0.4.8.r68.g04aee523 --src <源码目录> --lang c

# 3. 生成 patch（R3：只走 refresh-patch，不手写）
python3 scripts/ohc-run.py track-edit add ming 0.4.8.r68.g04aee523 util/makeswf_utils.c
python3 scripts/ohc-run.py refresh-patch --auto ming 0.4.8.r68.g04aee523

# 4. W3 本地验证（与 CI 同口径：profile 文件，不带 --user/--channel）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="ming/*"
```

## 遇到的问题与解决方案

| # | 问题（实际报错） | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ERROR: Version conflict: zlib/1.3.2 与 zlib/1.3.1` | 配方声明 `zlib/1.3.1`，而 `libpng/1.6.58.3` 要求 `1.3.2` | 依赖版本对齐 `zlib/1.3.2`（`conan graph info` 先验证解析干净） |
| 2 | `get(): BadZipFile: File is not a zip file` | codeload URL 以提交哈希结尾、无扩展名，Conan 无法推断归档格式 | `conandata.yml` 的 `sources` 加 `filename: ming-<sha>.tar.gz`（同 abbtr/1.0.4） |
| 3 | `configure: error: cannot guess build type` | `config.guess` 不认 HarmonyOS（`uname -s = HarmonyOS`），且在本平台还因 HMDFS 限制写不了探针临时文件（`can't create .../dummy.c: Permission denied`） | 显式传 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu` 跳过 config.guess。**实测 automake 1.18 的 config.sub 只接受该形态**：`aarch64-linux`、`*-linux-ohos`、`*-linux-musl` 均被拒。build==host → autoconf 按 native 处理（`cross_compiling=no`），故不存在 E007 警告的 `AC_RUN_IFELSE` 被跳过问题；libming 本身也无 AC_RUN_IFELSE |
| 4 | `config.status: ./confXXXXXX/subs1.awk: Permission denied` → `could not setup config files machinery` | E114：生成的 `configure` 用 `(umask 077 && mktemp -d)` 建临时目录，HMDFS 上权限为 `drwx--S---`，连 owner 也写不进去（chmod 无效） | autoreconf 后 `sed -i 's/umask 077/umask 000/g' configure`（同 afuse/abiword） |
| 5 | `ld.lld: error: duplicate symbol: swf4debug/swf5debug` | `src/actioncompiler` 的 flex(`-Pswf4`/`-Pswf5`) 与 bison 各产生一份**暂定定义**；clang 11+ 默认 `-fno-common` 使其变强符号 | `tc.extra_cflags.append("-fcommon")`（`ant-phone/0.2.1` 同因同治） |
| 6 | 可选库静默探测失败：`gif_lib.h... no`、`png_read_image in -lpng... no`（而 `zlib.h... yes`） | 注入的 `-I`/`-L` **自带引号**（`f'-I"{inc}"'`），引号被当作路径字面量的一部分 → 指向不存在的目录；`-lz` 之所以"通过"是命中了 OHOS **系统自带 zlib**，掩盖了问题 | 去掉引号：`env.append("CPPFLAGS", f"-I{inc}")`。**排查要点：只看 zlib 通过会误判注入已生效** |
| 7 | `make check` 运行期 `Error loading shared library libpng16.so.16 / libgif.so.7` → `png_*/DGif* symbol not found` | 测试程序（及 `libming.so.1`）运行期找不到依赖包的 `.so`。**关键结论：本平台上 `LD_LIBRARY_PATH` 在 `make → sh → perl → libtool wrapper → 测试程序` 这条子进程链上不可靠**——同一命令在交互 shell 里 `exit=0`，经 make 链则失效（与 HMDFS 限制子进程写入同源） | 把依赖目录写进 **ELF RUNPATH**：`env.append("LDFLAGS", f"-L{lib} -Wl,-rpath,{lib}")`。**踩坑：不要用 `AutotoolsToolchain.extra_ldflags`**——在 `tc.generate(env=<自定义 env>)` 路径下它不进 LDFLAGS（实测生成脚本 `grep rpath` = 0，即"rpath 已修"其实从未注入，白跑一轮） |
| 8 | `test/actionscript` → `FAIL: ActionScriptTest`，`sh: cpp: inaccessible or not found` | `util/makeswf_utils.c` **硬编码** `#define CPP "cpp -xc++ -P -Wall"`，由 `makeswf_preprocess()` 经 `system()` 调用；本机与 CI 均无 `cpp` 可执行文件 | 1 行补丁改为 `#define CPP "clang -E -xc++ -P -Wall"`（clang 自带预处理器，参数语义等价） |
| 9 | `ERROR: package(): copy() got an unexpected keyword argument 'delete'` | **ADAPTATION_GUIDE 模板里的 `copy(..., delete=True)` 在 Conan 2.29 已不存在** | 改用 `rm(self, "*.la", os.path.join(self.package_folder, "lib"))` |
| 10 | test_package 运行期 `Error relocating test_ming: SWFShape_end: symbol not found` | 测试程序链接了 libming 但运行期找不到它及其传递依赖 | 同 #7：链接 test_package 时也加 `-Wl,-rpath,<每个依赖 lib 目录>`；**同时去掉 `-I/-L` 的引号** |
| 11 | test_package 报 `FAIL saved .swf has FWS/CWS signature`（但打印出 `signature FWS`） | **自己测试程序的 bug**：`char sig[3]` 存 `"FWS"` 无 NUL 终止符 → `strcmp` 越界比较恒不等（`printf("%.3s")` 却显示正常） | 改 `char sig[4] = {0}` |
| 12 | 安装后的 `bin/listswf` 报 `Error loading shared library libming.so.1` | 安装二进制由构建期 `--libdir=//lib` 决定 RUNPATH（构建时包目录还不存在），`env="conanrun"` 在本平台未能提供包内 `lib/` | 在命令上显式前置包 lib 目录：`LD_LIBRARY_PATH="<pkg>/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"` |

## 鸿蒙特有端到端消费者用例（test_package/test_ohos_e2e.sh）

评审要求「鸿蒙特有测试」至少一个完整端到端消费者用例（纯断言不算）。本用例只用**已安装的包产物**串起三段真实链路，并逐环节断言：

```
makeswf  test_ohos_e2e.as ──编译──▶ e2e.swf(CWS)   # 走 clang -E 预处理 + zlib 压缩
listswf  e2e.swf ──反解析──▶ 结构文本              # 含 cws2fws() 的 TMPDIR 临时文件路径
listaction e2e.swf ──反解析──▶ 动作文本            # 第二条独立解析链路
```

断言 12 项：三工具已安装、makeswf rc=0、产物存在、魔数为 FWS/CWS、listswf rc=0 且输出含 `File version` / `SWFACTION_TRACE` / **本用例写入的常量 `ming-ohos-e2e-ok`**（端到端闭环证据）、listaction rc=0 且输出含该常量。

平台特异性：工作目录取 `$TMPDIR`（本平台 `/tmp` 只读）；运行期依赖靠 ELF RUNPATH 定位；两条补丁路径（`clang -E` 预处理、`TMPDIR` 临时文件）都在本用例中被真实走到。

### 接口探测发现的真实缺陷（已修 / 已记录）

- **`util/main.c` 硬编码 `/tmp`（已修，patch 0001）**：`cws2fws()` 把临时文件写死为 `/tmp/swftoscriptXXXXXX`，而本平台 `/tmp` 是只读文件系统（`mkstemp` 报 `Read-only file system (Errno 30)`）→ `listswf`/`swftocxx` 等处理**压缩 SWF（CWS）** 时直接失败（`Couldn't create tempfile.`）。改为优先取 `TMPDIR`、缺省回退 `/tmp`（对其它平台透明）。上游 37 个用例组未暴露该问题，因为 `dotests.pl` 用的产物是未压缩 FWS，走不到 `cws2fws()`。
- **`swfto*` 转译工具在「只有动作的 SWF」上 SIGSEGV（未修，如实记录）**：`swftophp`/`swftocxx`（共享 `util/outputscript.c`）对本用例产物输出 126/161 字节后崩溃（rc=139）。与本次平台适配**无关**：同一次运行的 `listswf` 走同一条 `cws2fws()` 临时文件路径且完全正常，问题出在代码生成路径。属上游缺陷，未纳入用例断言（断言一个会崩的工具会掩盖问题），仅在 PR「补充说明」与本节披露，供上游/后续跟进。

## 工具链/框架侧踩坑（非上游问题，已另行修复）
- `init-build` 的"嵌套源码检测"会**误判并破坏源码树**：它只认 `configure`/`CMakeLists.txt`/`Makefile`/`meson.build`，不认 autotools 源码清单 `configure.ac`+`Makefile.am`；libming 源码包不含生成的 `configure`，于是下钻命中 `c++_ext/Makefile` 并把整棵树提升成 `c++_ext`（只剩 5 个文件）。已从干净归档恢复。
- `lang_detect.py` 的 manifest 扫描**作用域不一致**（CMake/Makefile/meson/package.json 只看顶层，而 Makefile.PL/Cargo.toml/go.mod/configure.ac 做全树匹配）→ 被 `perl_ext/Makefile.PL` 劫持，把 C 库判成 perl 并触发 R47 终止。已修为"顶层优先 + 全树兜底"，并补 `tests/test_v1223.py`（15 断言）。

## 源码修改

- `patches/0001-util-makeswf_utils.c.patch`（+1/-1）：`util/makeswf_utils.c` 的预处理器命令 `cpp -xc++ -P -Wall` → `clang -E -xc++ -P -Wall`。原因：OHOS 不提供 `cpp` 可执行文件，ActionScript 用例无法预处理 `.as`。
  经 `ohc-run.py track-edit add` + `refresh-patch --auto` 生成（R3）。

## 依赖版本

| 依赖 | 版本 | 用途 |
|---|---|---|
| freetype | 2.14.3.2.1 | 上游默认开启（缺 freetype2 即 `AC_MSG_ERROR`），TTF 字体支持 |
| zlib | 1.3.2 | SWF 压缩（版本随 libpng 要求） |
| libpng | 1.6.58.3 | PNG 位图导入 |
| giflib | 5.2.2 | GIF 位图导入 |
| automake / libtool | 1.18 / 2.5.4 | tool_requires：本机/CI 缺 automake/aclocal/libtool（E178），autoreconf 自举必需 |

关闭的可选扩展（`--disable-*`）：perl / php / python / tcl（语言绑定，不属 C 库功能契约；本机无 php/phpize）。

## 验证结果

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="ming/*"
```

- 编译：通过
- 上游测试（`make check`，37 个 `dotests` 用例组 / 100 条用例行）：**37/37 PASS，0 FAIL**，`Error loading` 0 次
  `BINDINGS='"c cxx"' BUILD_OPTIONS='"GIF" "PNG" "FREETYPE"'`（可选库已启用，10 条门控用例实际执行）
- test_package：`PASSED: 0 assertion(s) failed`（15 断言）+ `ming test_package: PASS（库 API 生成 SWF + 命令行工具回读）`
- 产物：`Package 'ad6f6dfc...' created`，含 `lib/libming.{a,so,so.1.4.8}`、`include/{ming.h,mingpp.h}`、`bin/`（listswf/swfc/swfto* 等）、`lib/pkgconfig/libming.pc`

## 注意事项
- `test_package` 就地构建（`self.build_folder == 配方目录`），会产生 `test_ming`、`test_package.swf`；已加 `test_package/.gitignore` 防止误入库。
- 配方内注入依赖路径时**一律不加引号**；运行期依赖定位**一律用 RUNPATH**，不要依赖 `LD_LIBRARY_PATH` 穿透 make 子进程链。
---

**编译结束**: 2026-10-14 21:36
**最终状态**: built
