# DRAFT-slrn-1.0.3-runenv-override-prefix-root-resource-dir - conan prefix=/ 固化资源目录的上游环境变量 runenv 覆盖

> **Contributor**: songzhenyan (E7AA) | **Status**: VERIFIED DRAFT | **Updated**: 2026-10-02
> **Source event**: slrn 1.0.3 HarmonyOS PC adaptation, PR #14088

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote；是否提升及最终分类由知识库维护者和赛事评审决定。

## 相关既有条目（撞车判定）

| 条目 | 已覆盖内容 | 本草稿增量 |
|---|---|---|
| E317 | 同族根因（--prefix=/ 固化 //lib/R/share 类路径）；方案是 R 专属的 install 期 sed 范围限定修补 | 本条目覆盖**零补丁**形态：上游官方文档化的资源路径环境变量（slrn: SLRN_SLANG_DIR）经 `runenv_info.define` 接到包内目录；不改上游源码/构建系统，消费者经 VirtualRunEnv 自动继承 |
| E499 | runenv 导出**传递依赖库目录**（LD_LIBRARY_PATH 类） | 本条目是**应用自有资源目录**（脚本库/数据文件）的上游专用变量，机制不同 |

检索关键词：prefix=/、//share、hardcoded load path、runenv_info、SLRN_SLANG_DIR、
relocatable（index.tsv + knowledge/doc/ 全量 grep，无其他覆盖）。

## Scope（何时用）

autotools（或同类）应用包带 share/ 下运行时资源（解释器脚本库、模块、数据文件），
且上游文档提供了覆盖该路径的环境变量。典型信号：编译和 --version 都正常，
但进入功能初始化才报资源找不到（test_package 才会暴露）。

## Symptom（真实日志，CI #65953）

```
$ slrn -i ohos-slrn.rc --show-config        # OHOS PC 上实跑
slrn 1.0.3
Unable to locate slrn.sl on load path
Configuration error: Unable to load startup file
The hardcoded load path is set to: //share/slrn/slang
You make need to set the SLRN_SLANG_DIR environment variable.
slrn fatal error:
Error initializing S-Lang interpreter.
```

注意同一次运行中 `slrn --version` / `--help` 全部正常——它们不触发解释器初始化。

## Root Cause

conan 打包约定 `configure --prefix=/`（DESTDIR 分离打包根）。slrn 把
`-DSLRN_SLANG_DIR="${prefix}/share/slrn/slang"` 固化为编译期宏，prefix=/ 时即
`//share/slrn/slang`。包移动安装到消费机后该绝对路径不存在，S-Lang 脚本库
（slrn.sl 等，上游架构的硬依赖）加载失败，解释器初始化中止。机制链：
prefix=/ → 编译期固化 //share/... → 包移动 → 运行时查找失败。

## Recommended Fix / Workaround

上游文档（INSTALL.txt）本就提供 `SLRN_SLANG_DIR` 环境变量覆盖。配方零补丁接线：

```python
def package_info(self):
    ...
    self.runenv_info.define(
        "SLRN_SLANG_DIR",
        os.path.join(self.package_folder, "share", "slrn", "slang"))
```

test_package 用 `env="conanrun"`（VirtualRunEnv）运行即自动获得该变量——
这同时保证测试环境与真实消费者环境一致。

## Fallback

上游无环境变量覆盖时：E317 式 install 期范围限定 sed；或补丁源码支持
$ORIGIN 相对二进制的资源定位（注意 OHOS 上 $ORIGIN 解析不稳定，见仓内 Gotchas）。

## Forbidden Approaches

- 只在 test_package 里 export 变量：测试假绿，消费者机器上依然坏（本条目在
  CI #65953 暴露前的形态）。
- configure --prefix 改成猜测的绝对路径：破坏 conan 布局约定且同样错误。

## Verification

- 修复前：CI #65953 test_package 报 "Unable to locate slrn.sl"（FAIL）。
- 修复后：CI #65955 / #65958 test_package 全绿，含 --show-config 进入 S-Lang
  解释器初始化并读取 HMDFS 上 init 文件的断言（PR #14088）。

## Prevention

适配带 share/ 资源的应用包时，先查上游文档（INSTALL/man）有没有官方路径覆盖
环境变量；test_package 必须包含至少一个进入功能初始化（而非 --version 即止）
的检查项。

## References

- 配方：`archives/s/slrn/1.0.3/conanfile.py`（package_info 的 runenv_info.define）
- 证据：PR #14088 CI 评论（ci?id=65953 失败、65955/65958 通过）
- 同族：E317（R 的 //lib/R/share sed 修补）
