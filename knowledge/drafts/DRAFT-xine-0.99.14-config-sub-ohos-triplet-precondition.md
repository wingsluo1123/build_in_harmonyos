# E566 的“显式 --build/--host”方案有前置条件：bundled `config.sub` 不认 `ohos` 时，三元组路线照样要改源码

- **草稿 ID**: DRAFT-xine-0.99.14-config-sub-ohos-triplet-precondition
- **来源**: xine-ui 0.99.14 HarmonyOS PC 适配（G0 命中 E566 → 实测 config.sub 拒绝 ohos → 走 0001/0002 补丁路线）
- **分类**: autotools / configure / cross-compile / compat
- **状态**: 本地草稿（路径 B 知识库扩展申请中）

## 问题 / 错误签名

- `configure: error: cannot guess build type; you must specify one`
- `Invalid configuration \`aarch64-unknown-linux-ohos': OS \`ohos' not recognized`（直接跑 `sh config.sub <三元组>` 时）
- `./config.guess: unable to guess system type — This script (version 2022-01-09), has failed to recognize the operating system you are using.`
- 知识图谱 G0 提示：`已知风险 E566 未在配方中处理`（E566 方案 = `explicit-build-host-triplet`）

## 根因

E566 的场景是：OHOS 上 build == host，Conan 的 `AutotoolsToolchain` 不主动下发 `--build/--host`，
configure 因此运行随源码分发的 `config.guess` 探测平台，而旧版 `config.guess` 不认 `uname -s=HarmonyOS`。
E566 的推荐做法是显式传三元组以跳过探测。

**但这条推荐有一个未被记录的前提：`config.sub` 必须已经认识 `ohos`。**

autotools 的 `AC_CANONICAL_HOST`/`AC_CANONICAL_BUILD` 对任何外部传入的别名都要经
`sh config.sub <alias>` 规范化。2024-01-01 之前的 `config.sub` 的 OS 表没有 `ohos`/`linux-ohos`，
实测（未打补丁的 tarball 基线）：

```console
$ sh ./config.sub aarch64-unknown-linux-ohos; echo "rc=$?"
Invalid configuration `aarch64-unknown-linux-ohos': OS `ohos' not recognized
rc=1
```

所以在这类包上，显式三元组方案与补丁方案**都要改 `config.sub`**，前者并不少改文件、
也不构成“零源码侵入”。两条路线的真实分界点是 `config.sub` 的版本，不是 `config.guess`。

## 最小修复方案

**先跑决策探针，再选路线**：

| `sh config.sub aarch64-unknown-linux-ohos` | 路线 |
|---|---|
| rc=0（config.sub 已支持 ohos） | 走 E566：配方 `build()` 显式 `--build/--host`，零源码改动 |
| rc=1（bundled 旧 config.sub） | 走补丁：`config.guess` + `config.sub` 双补丁，此时三元组方案并不更轻 |

补丁内容（xine-ui 0001/0002）：

```diff
# config.guess —— 放在其它 aarch64 分支之前
+    aarch64:HarmonyOS:*:*)
+	GUESS=aarch64-unknown-linux-ohos
+	;;
```

```diff
# config.sub
-    | fiwix* )
+    | fiwix* | ohos* )
-    | linux-musl* | linux-relibc* | linux-uclibc* )
+    | linux-musl* | linux-relibc* | linux-uclibc* | linux-ohos* )
```

只补 `config.guess` 不够：探测能产出三元组，下一步 `config.sub` 规范化仍 rc=1。
只补 `config.sub` 也不够：OHOS 上没人传三元组，探测阶段就失败了。

选型时另有一条工程理由：**同上游家族的兄弟包应统一路线**。本仓库
`archives/x/xine-lib/1.2.13` 已合入同款 0001/0002 补丁，xine-ui 跟着走补丁路线，
两个包的 `config.*` 处理方式不分叉，后续同家族包可直接复用。

## 验证方法

```bash
cd <src_root>
grep -n "timestamp = " config.guess config.sub      # 版本判据
sh ./config.sub aarch64-unknown-linux-ohos; echo rc=$?
sh ./config.guess
```

## 验证结果

| 环境 | 结果 |
|------|------|
| 本机 · 未打补丁基线（`.orig`） | `config.sub` → `OS \`ohos' not recognized`，rc=1；`config.guess` → `unable to guess system type` |
| 本机 · 打补丁基线（`.work`） | 两脚本均输出 `aarch64-unknown-linux-ohos`，rc=0 |
| Conan 2.29.1 + clang 15 + `ohos-aarch64` profile | `conan create` G2 PASS，`conan-create.log` 中 `checking build system type... aarch64-unknown-linux-ohos`；conan-verify G0-G4 全绿；test_package 27/27 |

## 禁止策略

- 禁止在未实测 `config.sub` 的情况下按 E566 字面执行“只加 `--build/--host`”并宣称零源码改动。
- 禁止为了让三元组通过而把 `--host` 改成 `aarch64-unknown-linux-gnu` 之类“伪装值”——configure 会进入
  真正的交叉模式并改变探测策略（参见 E553），且与 OHOS 上 build==host 的事实矛盾。
- 禁止直接给生成物（`configure` 里的 config.sub 调用逻辑）之外的生成文件打补丁代替 `config.sub` 本体（R6）。

## 相关

- 上位条目：E566（config.guess 双重失败，本条记录其方案边界，不重复其内容）
- 相似条目：E553（`--host` 触发交叉模式）、E490（autotools helper 执行位）
- 配套草稿：DRAFT-xine-0.99.14-in-tree-build-pollutes-patch-baseline（补丁路线的基线卫生）
- 归档：`archives/x/xine/0.99.14/`（notes.md 问题 1/1b，补丁 0001/0002）
