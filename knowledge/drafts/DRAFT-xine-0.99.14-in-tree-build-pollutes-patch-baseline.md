# 就地构建污染补丁基线：`finish` Step 1 无条件重跑 `refresh-patch`，把 man 页面/打包脚本的 prefix 替换也做成补丁

- **草稿 ID**: DRAFT-xine-0.99.14-in-tree-build-pollutes-patch-baseline
- **来源**: xine-ui 0.99.14 HarmonyOS PC 适配（第一次 `finish` 补丁 5→13，`conan-verify` G2 FAIL，W3 `build_and_test.sh` RC=1）
- **分类**: patch / build-system / workflow / filesystem
- **状态**: 本地草稿（路径 B 知识库扩展申请中）

## 问题 / 错误签名

- `refresh-patch` 输出 `精准模式: 只对 22 个追踪文件生成补丁` 后得到 **13 个补丁**，而 `conandata.yml` 只列 5 个
- 补丁名里出现与适配无关的条目：`0004-doc-man-en-aaxine.1.patch`、`0006-doc-man-en-xine.1.patch`、
  `0010-misc-SlackBuild.patch`、`0011-misc-build_rpms.sh.patch`（均 `+1/-1` 或 `+42/-42`）
- 若干条目报 `dry-run 失败`（`doc-man-de-*`、`doc-man-es-*`、`doc-man-fr-*`、`doc-man-pl-*`）
- 随后 `conan-verify` G2 FAIL、W3 门禁 `build_and_test.sh` 提示 patch_file 路径/格式错误

## 根因

模式 B（探索性编译）要求“在源码目录里手工 configure && make”。对 xine-ui 这类包，这一步**会改写
tarball 自带的、外观像源文件的生成物**：

| 被改写文件 | 改写内容 |
|---|---|
| `doc/man/{de,en,es,fr,nl,pl}/{xine,xine-check,aaxine}.1` | man 页面里的 `@prefix@`/默认路径被填入探索时的 `$DEFAULT_PREFIX` |
| `misc/SlackBuild` | 42 行 `PREFIX=`/路径字面量 |
| `misc/build_rpms.sh` | 1 行路径字面量 |

`refresh-patch --auto` 按“追踪文件差异”生成补丁，它无法区分“我改的”和“构建器改的”。
`finish` 的放大效应是致命的：**Step 1 无条件重跑 `refresh-patch --auto`**
（`_SKIP_PATCH_GENERATION` 只被 Step 2 `close-archive` 读取，对 Step 1 无效）。
所以即使 AI 之前生成并核对过 5 个补丁，finish 时刻的 `.work` 是什么，补丁集就是什么。
补丁编号随之重排（伪补丁抢占了 `0004`/`0005` 号段），`conandata.yml` 的文件名引用全部失配。

本例 22 个追踪文件中 17 个被构建改写：8 个能干净反 apply → 生成伪补丁；9 个 `dry-run 失败`。

## 最小修复方案

把“基线卫生”作为 **finish 前的固定动作**：

```bash
cd $HOME/.tmp/builds
diff -rq xine-ui-0.99.14.orig xine-ui-0.99.14.work      # 枚举全部差异
# 判定哪些是构建副产物（非适配），用 .orig 反向覆盖 .work，保留时间戳/权限
for f in doc/man/de/*.1 doc/man/en/*.1 doc/man/es/*.1 doc/man/fr/*.1 \
         doc/man/nl/*.1 doc/man/pl/*.1 misc/SlackBuild misc/build_rpms.sh; do
    cp -p "xine-ui-0.99.14.orig/$f" "xine-ui-0.99.14.work/$f"
done
diff -rq xine-ui-0.99.14.orig xine-ui-0.99.14.work      # 只剩 5 个真实适配文件
python3 $SKILL_ROOT/scripts/ohc-run.py refresh-patch --auto xine 0.99.14
# 旧补丁集由工具自动移入 patches/.patch-backup-<时间戳>/；核对新集正确后删除该备份目录（勿随 PR 提交）
```

**不变量（三处必须相等）**：

```
patches/*.patch 文件数 == conandata.yml patches 条目数 == manifest.yaml patch_generation.patches_count
```

**卫生判据**：`.orig`/`.work` 的差异集合必须等于“你愿意提交给上游的可移植性修复集合”。
多出来的每一个文件都要能在 notes.md 里说清理由，说不清就恢复。

## 验证结果

| 状态 | 结果 |
|------|------|
| 污染态（finish 第 1 次） | 13 个补丁（5 真实 + 8 伪），9 个 dry-run 失败，`work hash c38a4afa020a4a8d`；G2 FAIL、W3 RC=1 |
| 恢复后（finish 第 2 次） | 恰好 5 个补丁，`work hash 461951f4e5147c7d`（`orig hash fac5e461998783bb` 不变）；G0-G4 PASS、W3 本地 CI 模拟 PASS、test_package 27/27 |

## 禁止策略

- 禁止改 `conandata.yml` 去迁就虚高的补丁集——那等于把污染固化成方案（PR 里出现与适配无关的 prefix 字面量，换环境即失效）。
- 禁止绕过 `finish` 手工交付补丁：`finish` 的重跑正是“补丁 == 基线差异”不变量的工具背书。
- 禁止用 `make distclean` 代替基线恢复：`distclean` 未必回收 man/打包脚本，且可能删掉需要保留的文件。

## 相关

- 相似条目：E490（autotools helper 执行位）、E515（git 风格 `a/ b/` strip 层级）
- 配套草稿：DRAFT-xine-0.99.14-config-sub-ohos-triplet-precondition（本包选择的补丁路线本身）
- 流程依据：SKILL.md §0.3 W3 / `scripts/ohc/finish.py` Step 1（无条件 `refresh_patch_auto`）
- 归档：`archives/x/xine/0.99.14/`（notes.md 问题 13/14、注意事项 9）
