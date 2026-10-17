# DRAFT-gammastep-2.0.9-wayland-scanner-exec-denied-static-rebuild — 制品仓构建期工具双向不可执行 ⇒ 从上游源码静态重建

- **条目主题**：`conan` 制品仓提供的**构建期 ELF 工具**在 OHOS 构建机上**没有可用执行路径** ——
  ①未签名 ⇒ 执行 `EPERM`（`Operation not permitted`，rc=126）；②`binary-sign-tool sign -selfSign 1`
  自签后越过 EPERM，却因 `DT_NEEDED` 记录的是**构建机的 Conan 缓存绝对路径**（不是 soname）而
  `dlopen` 失败、`LD_LIBRARY_PATH` 无法干预 ⇒ 唯一稳定处方 = **从上游同版本源码静态重建该工具**，
  并把工具路径写进一份 `.pc` **prepend 到 `PKG_CONFIG_PATH`**。
- **状态**：草稿（B=create 成对交付件，待知识库主编审核提升编号 Exxx）
- **Software**：gammastep 2.0.9（消费方）；被测工具 = `ohpcd` 制品仓 `wayland/1.24.0` 的
  `bin/wayland-scanner`（Wayland 协议族核心代码生成器）
- **关联 Issue**：见同 PR 正文「知识库扩展 Issue」行（同 PR 内回填号 + 绝对链接）
- **查重**：四范围检索见文末「查重与新增价值」小节 —— 机制族已有
  `DRAFT-ohos-static-tool-bypass-dlopen-limit`，那条**只记 dlopen 一种签名**；本条增量 = EPERM 段
  + `NEEDED` 绝对路径根因 + autotools 消费方的 `.pc` 接法。

## 适用场景

任何**「由制品仓提供、又必须在构建机上执行」的工具型依赖**，其消费方是交叉编译配方：

- Wayland 生态：`wayland-scanner`（本包实证；`wayland`/`wayland-protocols` 及其所有客户端/合成器都要它）；
- 其它协议/IDL 代码生成器、构建期辅助 CLI（凡 `find_program` / pkg-config 取路径、再在自定义规则里执行的都算）。

判别信号：**configure/meson 阶段一切正常**，失败点落在「生成 `xxx-protocol.c`」这类自定义规则上，
且报的是**加载器/执行**错误，而不是「command not found」。

> ⚠ 关键陷阱：工具**存在、可读、权限位正常** ⇒ `find_program`、`pkg-config`、`ls -l` 全都说"有"，
> 故障推迟到真正执行时才暴露。因此**只查存在性 = 假绿**。

## 判别方法（三步取证，缺一不可）

### ① 先排除「本机整体禁执行」

```bash
printf 'int main(void){return 0;}\n' > t.c && clang t.c -o t && ./t; echo "rc=$?"
# 期望 rc=0 ⇒ 不是 noexec / 不是整机禁执行 ELF ⇒ 矛头指向该 ELF 自身
```

### ② 取「未签名」读数

```bash
<制品仓工具> --version; echo "rc=$?"
# OHOS: bash: line N: <path>: Operation not permitted
#       rc=126
```

`EPERM` 不是 `ENOENT`、也不是 `EACCES` —— 它是**签名闸**：`chmod` 无效、换目录（含 `~/tmp`）同样无效。

### ③ 自签再试 + 关键判据

```bash
cp <制品仓工具> u && chmod +x u
binary-sign-tool sign -inFile u -outFile s -selfSign 1     # 缺 -selfSign 会报 Params '-keystoreFile' is required
./s --version
# 越过 EPERM，改为加载器报错：
#   Error loading shared library /…/.cache/conan2/p/expat<hash>/p/lib/libexpat.so: (needed by ./s)
#   Error relocating ./s: xmlNewValidCtxt: symbol not found
```

**关键判据**：把该依赖库的**真实 libdir** 加进 `LD_LIBRARY_PATH` 再跑一次。

```bash
LD_LIBRARY_PATH=<同 home 内 expat 的真实 libdir>:<libxml2 真实 libdir> ./s --version
```

- 若**仍报同一条绝对路径** ⇒ `DT_NEEDED` 里存的是**绝对路径而非 soname** ⇒ 动态加载**无处插入**、
  判死刑（本条实测正是如此）；
- 若这次能加载 ⇒ 只是缺 `LD_LIBRARY_PATH`，补 run 环境即可，**不需要**静态重建。

## 处方（rec_priority=1）：从上游源码静态重建 + `.pc` 覆盖

1. **早于 configure**（`build()` 最前面，或 meson 的 `meson.configure()` 之前）静态编译该工具：
   只编它真正需要的翻译单元（`wayland-scanner` 只需 `scanner.c` + `wayland-util.c`；上游测试用的
   libxml2 DTD 校验**不需要**），第三方依赖取**宿主 SDK** 的静态库
   （本机 `/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a`），版本头由 `*.h.in` 模板手工替换；
   产出放 `build_folder/<tool>-bin/`。
2. **写一份 `.pc` 覆盖**：内容含工具变量（`wayland_scanner=${bindir}/<tool>`），落到
   `generators_folder/fixed_pkgconfig/`，并在 `AutotoolsToolchain` 的 env 里
   `prepend_path("PKG_CONFIG_PATH", 该目录)`。
   - autotools 消费方：`configure.ac` 的 `PKG_CHECK_VAR(WAYLAND_SCANNER, wayland-scanner, wayland_scanner)`
     即解析到自编译工具；`src/Makefile.am` 的 `$(WAYLAND_SCANNER) private-code` 规则随即可用；
   - meson 消费方：`dependency('wayland-scanner', native: true).get_variable(pkgconfig: 'wayland_scanner')`
     同款可用（`archives/l/lavalauncher/2.1.1` 先例）。
3. ⛔ **不 stub、不 LD_PRELOAD 假库、不改制品仓包** —— 生成出来的协议代码必须与上游一致。

## 实测证据（gammastep 2.0.9，B 机一手，2026-10-16）

完整逐条读数与命令见本包 `notes.md` 的「构建期工具 wayland-scanner 不可执行（B 证据）」节。摘录：

```
[1] file(1):  ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
[2] 未签名执行: Operation not permitted                                    rc=126
[3] 复制到 ~/tmp 再跑: Operation not permitted                              rc=126
[4] 对照 clang 现场编译二进制                                              rc=0
[5] binary-sign-tool -selfSign 1 自签: INFO add codesign section success / write code sign data success
    然后: Error loading shared library /storage/Users/currentUser/.cache/conan2/p/expat9fb72708ad085/p/lib/libexpat.so
          Error relocating ./ws.signed: xmlNewValidCtxt: symbol not found
[6] 加 LD_LIBRARY_PATH=<同 home 内 expat/libxml2 真实 libdir> 后:
          Error loading shared library /…/.cache/conan2/p/expat9fb72708ad085/p/lib/libexpat.so   ← 仍是绝对路径
          Error relocating ./ws.signed: XML_ParserCreate: symbol not found
[7] ls -d /storage/Users/currentUser/.cache/conan2 → No such file or directory
[8] 同 home 内 expat 包 libdir 确实有 libexpat.so ⇒ 不是"库没下载"，而是 NEEDED 写死了别的绝对路径
```

同族先行证据（lavalauncher/2.1.1，2026-08）：同款工具在同机不可用，处方同为源码静态重建；
该次记录的签名是「dlopen 失败」一种 —— 本条第一次把「未签名 ⇒ EPERM」与「NEEDED 绝对路径」
补全为完整的两段链。

## 查重与新增价值

| 既有条目 | 收录状态 | 问题面 | 本条增量 |
|---|---|---|---|
| `DRAFT-ohos-static-tool-bypass-dlopen-limit` | 草稿池 | 制品仓工具在构建机上**执行失败**（记 dlopen 一种签名），处方 = 源码静态重建 | ①补 `未签名 ⇒ EPERM` 这一段签名；②补根因 `DT_NEEDED 绝对路径 ⇒ LD_LIBRARY_PATH 无效`（该草稿未记）；③补 autotools 消费方的 `.pc` 变量接法（该草稿以 meson 为例） |
| `E527` | 图谱 | GTK 的构建期 **Python** 工具（`glib-mkenums`/`glib-genmarshal`）要在 build machine 执行，改 shebang 指向宿主解释器 | 那层是**脚本 + 解释器**，改 shebang 即可；本条是**编译型 ELF 被签名闸 + NEEDED 绝对路径**双重挡住，处置与根因都不同 |
| `E463` / `E472` | 图谱 | 制品仓取出的编译工具在 HarmonyOS 上**需要自签**才能执行 | 那两条停在「签了就可用」；本条实测证明**签了仍不可用**（第二道闸），并给出绕过第二道闸的处方 |
| `E443` | 图谱 | autotools native 工具闭包与可重定位 | 那条讲工具闭包收集与路径重定位，不讲「工具根本执行不了」 |

其余检索：`knowledge/graph`（`index.tsv` + `E*.kv`）对 `wayland-scanner` / `drm` / `gamma` **0 命中**；
`经验文档/经验库/` 全量对 `wayland-scanner` / `静态编译` / `静态重建` **0 命中**；
`经验文档/OHOS行为探针清单.md` 未覆盖本条（其 EPERM 两条分别属 AF_UNIX 路径 socket 与
`initgroups`，与本条不同面）。同域先例 `archives/x/xgamma/1.0.8`（X11 gamma CLI）覆盖的是
**运行期**无 X server 的能力面，与本条的**构建期工具执行**是两件事 —— 本包两者都有，分开披露。

## 边界与反例

- 只适用于**纯计算型**构建期工具；工具若依赖设备节点/网络/宿主服务，静态链接不解决。
- 重建用的第三方静态库取宿主 SDK 属**构建机库**、不进目标包，不构成目标侧 ABI 混装。
- **反例**：把 Wayland 后端设为可选并因工具跑不了而静默关掉 ⇒ 编过了但少一个后端，
  是「假绿」而不是修复。本包用 `--enable-wayland` 强制开启，缺依赖即 configure 硬失败。
