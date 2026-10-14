# DRAFT-slrn-1.0.3-build-time-target-tool-run-guard - 构建期目标端校验工具的交叉编译守卫（chkslang 模式）

> **Contributor**: songzhenyan (E7AA) | **Status**: VERIFIED DRAFT | **Updated**: 2026-10-02
> **Source event**: slrn 1.0.3 HarmonyOS PC adaptation, PR #14088

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote；是否提升及最终分类由知识库维护者和赛事评审决定。

## 相关既有条目（撞车判定）

| 条目 | 已覆盖内容 | 本草稿增量 |
|---|---|---|
| E359 | 上游自定义构建系统有 HOSTCC/HOSTLD 变量时，把 conan build 上下文编译器映射过去；工具是必须运行的代码生成器 | 本条目覆盖**纯校验类**构建期工具（无产出物、仅版本/特性 sanity check）且上游**没有** HOSTCC 挂钩的老式 autotools Makefile：正确解法是交叉时跳过运行 + 依赖版本锁定兜底，而非强行换宿主编译器（校验工具要链接目标端库，宿主编译器反而不可用） |
| E543 | configure 期 AC_TRY_RUN 探测交叉中止（cache 变量预置） | 本条目是 make 期的"编译并立即运行"目标端二进制，阶段不同、修复面不同 |

| E087 | HMDFS 上 chmod 不生效导致脚本 Permission denied，用 sh 前缀绕过 | 本条目是目标架构 ELF 的 ENOEXEC（cannot execute binary file，Error 126），与权限无关；draft-review 曾将其列为灰区近似项，人工判定不覆盖 |

检索关键词：cannot execute binary file、Error 126、chkslang、build-time tool、HOSTCC、CC_FOR_BUILD（index.tsv + knowledge/doc/ 全量 grep，无其他覆盖）。

## Scope（何时用）

老式 autotools 包的 Makefile 规则在同一 target 里先编译链接一个目标架构小工具、
随后立刻执行它做校验（典型：jedsoft 系的 `slangversion: $(OBJDIR)/chkslang` +
`$(OBJDIR)/chkslang $(EXEC) 20203`；slrn/most/jed 共用此模式）。交叉编译 OHOS 时
构建机无法执行目标 ELF。

判据：该工具**无产出物**被后续编译依赖（纯校验）。若有产出物（代码生成器），
转用 E359 的宿主编译器映射。

## Symptom（真实日志）

slrn 1.0.3 交叉构建（macOS 构建机 → aarch64-linux-ohos）：

```
cd .../src/objs && /opt/ohos-clang -c ... chkslang.c        # 编译通过
.../chkslang slrn 20203
.../src/objs/chkslang: cannot execute binary file
make[1]: *** [slangversion] Error 126
```

（本地 W3 与远程 CI 均可复现；PR #14088 修复前轮次日志）

## Root Cause

`execve()` 对非本机架构/ABI 的 ELF 返回 ENOEXEC，shell 报 "cannot execute binary
file"，make 以 Error 126 中止。工具本身编译链接完全正常——问题只在"立即运行"这一步。
chkslang 的校验内容（S-Lang 头文件版本 == 运行库版本 >= 2.2.3）在 conan 体系下已由
`requires("slang/2.3.3")` 精确锁定，头文件与库同包同源，交叉构建跳过该校验不损失
正确性保证。

## Recommended Fix / Workaround

1. 给 Makefile 规则加守卫变量（补丁无平台宏，纯 POSIX shell）：

```make
slangversion: $(OBJDIR)/chkslang
	if [ "$(SKIP_CHKSLANG)" = "1" ]; then \
	  echo "skip chkslang run: cross compiling (floor pinned by conan dep)"; \
	else \
	  $(OBJDIR)/chkslang $(EXEC) 20203; \
	fi
```

2. 配方仅在**真实交叉**时传 `SKIP_CHKSLANG=1`。注意 OHOS 本地模拟 profile
   （ohos-local：host/build 都声明 OHOS 但实际构建机是 macOS）需要额外区分——
   本仓惯例用 `user.build:flex_bison_native` conf 标记模拟构建（见 scws 配方）：

```python
def _is_native_ohos(self):
    if str(self.settings_build.os) != "OHOS":
        return False
    return not self.conf.get("user.build:flex_bison_native",
                             default=False, check_type=bool)
```

3. 原生 OHOS CI 构建不传守卫变量，chkslang 照常运行——校验能力不弱化。

## Fallback

工具必须运行时（代码生成器）：E359，HOSTCC/CC_FOR_BUILD 映射，或
tool_requires 提供 build 上下文依赖后用宿主 CC 重建该工具。

## Forbidden Approaches

- 无条件删除校验目标/改成 `true`：原生构建的版本一致性检查被一并削弱。
- 试图让构建机"模拟执行"目标二进制（无 qemu/binfmt 环境时不成立）。

## Verification

- 交叉 profile `conan create` 构建通过（本地 W3 日志，PR #14088）。
- OHOS CI 原生构建日志中 chkslang 实际运行（build==host，守卫未触发）。
- slrn 实证：修复前本地/CI 均 Error 126，修复后 CI #65955/#65958 全绿。

## Prevention

适配 jedsoft 系或同类老式 autotools 包时，先 grep Makefile.in 中
"编译产物出现在 recipe 行首"的规则（本条目 .kv 的 prescan_pattern 可自动预扫）。

## References

- 配方与补丁：`archives/s/slrn/1.0.3/conanfile.py`、`patches/0003-src-Makefile.in.patch`
- 失败/通过证据：PR #14088 CI 评论（ci?id=65943 前轮失败、65955/65958 通过）
