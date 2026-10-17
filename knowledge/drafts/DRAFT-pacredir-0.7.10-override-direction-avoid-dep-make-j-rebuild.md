# override 方向要避开「构建系统走 GNU make -j 的依赖」：下游给不了 -j1，而 OHOS 上 make -j>1 必炸

- **Status**: DRAFT
- **出处**: pacredir 0.7.10 适配 HarmonyOS PC，远程 CI **#93768**（PR #16086 第 1 轮）实测失败后修正
- **严重度**: 3（blocking：conan create 在依赖阶段即失败，目标包连 `source()` 都没轮到）
- **阶段**: compilation（依赖包构建）
- **metrics**: success 1 / fail 1 —— 反向方案已实测失败一次，正向方案的 CI 结果见本 PR 回填

## 相关既有条目（撞车判定）

查重范围：`knowledge/graph/index.tsv`（768 条）、`knowledge/doc/`、`knowledge/drafts/`（5440 文件）。

另用仓内工具做了机器相似度复核（`ohc-run.py draft-review <本草稿> --top 5`）：
质量预检 signature/root_cause/rec 三项全绿，最近邻 **E074 score 0.21**、
E146 0.14、**E538 0.12**、E525 0.12、E478 0.10，工具给出 **`create`（疑似新知，
无高相似条目）**。分数都不高正是因为机制层已被 E074/E525 占住、而本条申报的是
决策层。下面把工具点到的 E538/E146 一并列入逐条对比：

| 条目 | 它覆盖什么 | 本条增量 |
|---|---|---|
| **E538**（ohpcd 已发布二进制的 `shared` 选项不一致 ⇒ 全图无匹配 binary） | 同族最近邻：harfbuzz 的发布二进制只基于 `glib:shared=False` 构建，而 glibmm/cairomm/pango 基于 `shared=True`，于是 pangomm 全图解析时 harfbuzz 算出的 package_id 无发布 binary、被迫源码构建并**超过 300s 前台时限**。修法是等 ohpcd 发布一致版本（`published-binary-wait`）加一串 meson/PkgConfigDeps/签名修复 | 三点不同：① 失配来源——E538 是**制品仓发布不一致**（被动踩到），本条是**消费者自己 override** 主动改了传递依赖版本（可提前预判）；② 失败形态——E538 是超时（给足时间或等发布即可解），本条是 SELinux 硬限制（给多少时间都不会成功，等发布也等不到，因为冲突是版本级的）；③ 修法位点——E538 依赖 registry 侧修复，本条完全在消费者配方内闭环（选 override 方向），无需等任何人 |
| **E146**（缺库依赖 + 本地工具链限制如 bison/flex pipe） | 编译中发现缺依赖，叠加本地工具链的 pipe 类限制 | 都涉及「工具链/平台限制叠加依赖问题」，但 E146 的限制在**本地构建工具**（bison/flex 的 pipe），本条的限制在**目标平台 SELinux**（mkfifo），且 E146 不涉及 package_id / override 决策 |
| **E074**（SELinux 禁 FIFO ⇒ make jobserver 失效） | **机制**：鸿蒙 SELinux 禁止用户进程创建 FIFO，GNU make 的 jobserver 靠 FIFO 传并行令牌，`make -j>1` 卡住或报错。影响面写作「所有使用 `make -j` 的 Autotools/CMake 项目」 | 机制层面无增量，本条**直接引用**它作为前提（`caused_by`）。增量在决策层：当出错的 `make -j` 不在自己配方里时，E074 给的修法（自己统一 `-j1`）**用不上** |
| **E525**（OHOS 下 make 应统一 -j1） | 同上机制，并落到本仓实践：`archives/7/7zip/*` 的 recipe 模板仍写 `make -j$(nproc)`，新 recipe 照抄会踩坑；推荐 `force-j1`，回退 `MAKEFLAGS=... -j1` | 同上。E525 的两个方案都预设「你能改那个 `self.run`」；本条处理的正是**你改不了**的情形——`-j20` 出自依赖包 `libcurl/8.5.0` 的 `cmake.build()`，下游唯一能做的是别让它被重建 |
| **E028**（系统同名库必须静态、`--without-shared`） | 共享库与系统库冲突时用静态规避 | 本条给出一个**反向约束**：在 OHOS 上「把依赖切成静态」不是免费的——它会使已发布二进制失效并强制源码重建，若该依赖走 make 就撞 E074/E525。两条要一起读：R26 要求静态，本条要求先确认静态化不会触发依赖重建 |
| **E242**（Fortran `.mod` / `package_id_mode` / `tool_requires`） | 依赖的 package_id 与工具链匹配问题 | 同属「package_id 失配 ⇒ 被迫重建」家族，但 E242 的成因是编译器 / `package_id_mode`，本条是 **override 改了传递依赖版本**；处置也不同（E242 调 mode，本条调 override 方向） |
| **E057**（并行 worker 导致测试 flaky） | `MAKEFLAGS` / `-j` / `cpu_count` 在测试期的全局状态污染 | 都涉及 `-j`，但 E057 是**测试期**竞态、可靠重试缓解；本条是**构建期**平台能力硬限制，重试无效 |

结论：机制已被 E074/E525 完整覆盖，本条不重复申报机制；申报的是
**「依赖图 override 方向选择」这条决策规则**，以及「下游无法给依赖注入 `-j1`」
这个约束边界。index.tsv 中检索 `override` / `package_id` / `重建` / `prebuilt`
无同类条目；机器相似度点到的最相近条目 E538 已在上表逐条区分。上述 5 条
（E028、E057、E146、E242、E538）已填入 `.kv` 的 `similar_to`，机制前提
E074/E525 填入 `caused_by`。是否纳入正式库由主编人工审核决定；本 PR 不做 promote。

## Scope（何时用本条）

三条同时成立时适用：

1. 依赖图里同一库出现两个版本，必须 `override` 才能解析
   （本例：`systemd/261.1` 钉 `zlib/1.3.1`，`libcurl/8.5.0` 钉 `zlib/1.3.1.1`）；
2. override 之后至少一个依赖的**已发布二进制失效**，CI 的 `--build=missing`
   会把它从源码重建；
3. 候选被重建者的 `build()` 最终落到 **GNU make 且 `-j>1`**
   （CMake + `Unix Makefiles` 生成器、Autotools、裸 Makefile 都算）。

**不适用**：冲突能靠换 provider / 换版本彻底消除（那就没人需要重建，见回退方案）；
或者出错的 `make -j` 就在**你自己**的配方里（那按 E525 直接 `make -j1`）。

## Symptom（CI #93768 真实日志）

```text
olibcurl/8.5.0: Main binary package '7ed998dad2cd7b6fe73eee7bc365fa0677f5cb72' missing
olibcurl/8.5.0: Checking 11 compatible configurations
olibcurl/8.5.0: No compatible configuration found
opacredir/0.7.10: Forced build from source
...
olibcurl/8.5.0: options: fPIC=True shared=False          ← 消费者强制静态所致
olibcurl/8.5.0: RUN: cmake -G "Unix Makefiles" ...
...
omake: jobserver mkfifo: /storage/Users/currentUser/.cache/tmp/GMfifo48803: Operation not permitted
omake[2]: /bin/sh: Resource temporarily unavailable
omake[2]: *** [lib/CMakeFiles/libcurl_static.dir/build.make:120: .../asyn-thread.c.obj] Error 127
omake[2]: *** Waiting for unfinished jobs....
o/bin/sh: can't fork - try again
o/bin/sh: can't fork - try again
omake[1]: *** [CMakeFiles/Makefile2:139: lib/CMakeFiles/libcurl_static.dir/all] Error 2
omake: *** [Makefile:136: all] Error 2
olibcurl/8.5.0: ERROR:
oPackage '7ed998dad2cd7b6fe73eee7bc365fa0677f5cb72' build failed
oERROR: libcurl/8.5.0: Error in build() method, line 112
o	cmake.build()
o	ConanException: Error 2 while executing
o[fail] pacredir/0.7.10 — conan create failed
helapsedTime=653.335939
```

注意两点：

1. **失败发生在依赖阶段**，目标包 `pacredir/0.7.10` 连 `source()` 都没执行；
2. **CI 机器人的分类是错的**。它把这次失败标成「网络问题 / 源码下载超时
   (`https://gh-proxy.com/...`)」，因为日志里确实有 6 行 gh-proxy 相关的
   `[fail]`——但那些全部是 `[fail] [Errno 2] No such file or directory: 'curl'`
   （**worker 上没装 curl**，预下载机制整体失效），与超时无关。真正的错误在
   日志末尾的 `jobserver mkfifo`。
   ⇒ 按 R44 先跑 `gitcode_pr.py diagnose`，再自己读完整日志，
   **不要照着 CI 的分类去修网络**。

## Root Cause

```text
同一依赖库两个版本共存（systemd 钉 zlib/1.3.1，libcurl 钉 zlib/1.3.1.1）
  → Conan 报 Version conflict，必须 override 到其中一个
  → override 改变被覆盖方的 package_id ⇒ 其已发布二进制不再匹配
  → CI 的 --build=missing 把失配的那个从源码重建
  → 若它走 CMake + Unix Makefiles，conan 默认按 nproc 传 -j（本例 -j20）
  → OHOS SELinux 禁止用户进程 mkfifo（E074/E525）
  → GNU make 的 jobserver 建不出 FIFO ⇒ /bin/sh: can't fork ⇒ Error 127
```

关键在于**「重建哪一个」不是等价选择**，而下游能用的杠杆只有一个：

| 想过的杠杆 | 为什么不行 |
|---|---|
| 给依赖注入 `-j1` / `MAKEFLAGS` | `tools.build:jobs` 与 `MAKEFLAGS` 属 profile/conf 或 `ci/` 框架层。消费者改它 = 在单库 PR 里动框架文件，违反 W2；且会把全仓构建串行化，诱发大面积超时 |
| 改依赖包自己的配方 | 他人归档目录，铁律禁止在同一 PR 里碰；要改就得给依赖开新版本走完整发布流程，不是本轮能闭环的 |
| 加大 `ci/config/build_timeouts.txt` 预算 | 根因不是超时（653s 就失败了），给多少时间都不会成功；且该文件同属框架文件 |
| **选 override 方向** | ✅ 唯一在单库 PR 内可闭环的杠杆：决定「谁被迫重建」 |

而「谁被迫重建」的判据**不是包大小**，是它的 `build()` 是否落到 GNU make：

| 候选 | 构建系统 | OHOS 上能否源码重建 |
|---|---|---|
| `libcurl/8.5.0` | CMake + `Unix Makefiles` → `make -j20` | ❌ 撞 E074/E525（本轮实测失败） |
| `systemd/261.1` | meson → `ninja libsystemd.so.0.44.0` | ✅ ninja 用 pipe 不用 FIFO；meson 不用 make jobserver。且它自己的 PR CI 就是从源码 `conan create` 成功后才发布的（commit `17debd6e99`），worker 侧工具链已被实证 |

顺带一个必须同时核对的约束：所选方向不能把**非 PIC** 静态库塞进共享库。
`zlib/1.3.1` 的 `libz.a` 是非 PIC 的，`zlib/1.3.1.1` 才是仓内为修此问题而建的
修订版（`--static` + `CFLAGS=-fPIC`）；本地实测 override 到 1.3.1 后 libcurl
从源码构建即炸
`ld.lld: error: relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol 'z_errmsg'; recompile with -fPIC`。
两个约束叠加后，**override 到 zlib/1.3.1.1 是唯一同时满足的方向**。

## Workaround / 修复

```python
def requirements(self):
    self.requires("systemd/261.1")
    self.requires("libmicrohttpd/1.0.1")
    self.requires("libcurl/8.5.0")          # 沿用已发布的**动态**二进制
    self.requires("iniparser/4.2.6")
    # override 到 libcurl 的原生 pin，让 make-based 的 libcurl 不必重建，
    # 把源码重建推给纯 meson+ninja 的 systemd。
    self.requires("zlib/1.3.1.1", override=True)

# 不要再写这一行 —— 它会强制 libcurl 从源码重建，正中 E525：
# def configure(self):
#     self.options["libcurl"].shared = False
```

代价与收益要如实记进 PR：

- **代价**：`DT_NEEDED` 从 `{libsystemd.so.0, libc.so}` 变成
  `{libcurl.so, libsystemd.so.0, libc.so}`（多一个动态依赖；实测 `libcurl.so`
  的 SONAME 就是无版本号的 `libcurl.so`，运行期可解析）。
  `systemd/261.1` 需要在 CI 上从源码重建一次（meson configure + 单个 ninja 目标）。
- **收益**：避开了一个**已实测必然失败**的路径。`libmicrohttpd`（`libmicrohttpd.a`）、
  `iniparser`（`libiniparser.a`）、`zlib`（静态）仍被静态吸收，R26 的核心诉求
  （不往设备 `/lib` 塞系统同名 `.so`）依然满足。

## Prevention

1. **选型阶段就把「谁会被迫重建」列出来**，逐个查其 `build()` 是否落到 make：
   ```bash
   grep -nE 'CMake\(|Autotools\(|self\.run\(.*make|Unix Makefiles|Meson\(' \
        archives/<字母>/<候选依赖>/<版本>/conanfile.py
   ```
   命中 `CMake(self)` / `Autotools(self)` / 裸 `make` 且没有 `-j1` ⇒ OHOS 上不可重建。
2. **别为了 DT_NEEDED 好看就把依赖切静态**。`self.options["dep"].shared = False`
   在 OHOS 上的隐含代价是「强制该依赖源码重建」，先确认它的构建系统能承受。
3. **CI 机器人的失败分类不可信**，尤其当它报「网络问题/下载超时」时：
   worker 上没有 `curl`，预下载机制恒失效，日志里必然出现一串
   `[fail] [Errno 2] No such file or directory: 'curl'`，很容易被误判成下载失败。
   按 R44 先 `diagnose`，再自己读完整日志的**末尾**（真正的错误在那里）。
4. **优先尝试彻底消除冲突**（换 provider / 换版本 / 给冲突库出对齐版本），
   让谁都不必重建；本例查过 `curl/8.15.0`、`curl/8.15.0.1`、`curl/8.22.0`，
   分别钉 `zlib/1.3.1.1` 与 `1.3.2`，都无法与 `systemd` 的 `1.3.1` 对齐，
   才退到「选方向」。

## References

- 远程 CI #93768（PR #16086 第 1 轮），完整日志见该 PR 的「CI 校验失败」评论；
  构建看板 <https://ohpcd.atomgit.com/ci?id=93768>
- 本 PR：`archives/p/pacredir/0.7.10/conanfile.py`（模块 docstring「依赖图处置 4」
  与 `requirements()`）、`archives/p/pacredir/0.7.10/notes.md`（问题 #7）
- 机制前提：E074（SELinux 禁 FIFO ⇒ make jobserver 失效）、E525（OHOS 下 make 统一 -j1）
- 非 PIC 静态库约束：`archives/z/zlib/1.3.1.1/conanfile.py`（「静态库 + -fPIC（鸿蒙 PC）」）、
  `archives/k/kylin-ai-document-service/1.2.0.0/conanfile.py`（`--exclude-libs,ALL` 技法）
- systemd 可由 CI 从源码构建的实证：commit `17debd6e99`
  （【知识库扩展】feat(systemd): 261.1 适配 HarmonyOS PC）
- worker 自带系统 meson 的旁证：`archives/l/libseat/0.9.1`、`archives/v/vte/0.74.2`、
  `archives/l/libsoup/2.74.3` 等 published 的 meson 包均不 `tool_requires` meson
- 相关原则：P013（平台限制必须降级而非绕过）、P020（HMDFS/SELinux 不支持 FIFO，必须用替代方案）
