# DRAFT-conan2-option-variant-no-fallback-publish-new-version — conan 回退不放宽 options：缺的变体只能用新版本号发布

> 草稿（待审核 promote）。来源：libfuse 3.18.2.1（PR #15754）× saunafs #14023 联合诊断。

## 症状

- 消费方（saunafs）配方显式 `"libfuse/*:shared": True`，CI **每轮** `Forced build from source` 重编 libfuse；
- 其中一轮倒在 `ninja: fatal: posix_spawn: Resource temporarily unavailable`（CI 机器高负载），表象像偶发环境失败；
- 版本级查询 `conan list "libfuse/*" -r=ohpcd` 显示 3.18.2 **有**制品——与"每轮都编"矛盾。

## 根因

| conan 选项 | package_id | ohpcd |
|---|---|---|
| `shared=False`（3.18.2 默认） | `21b17f8b2bc0e9511e276e3d57a23893067cefe5` | ✓ 有 |
| `shared=True`（saunafs 要求） | `0726937e17000c634ad5fc029642008575bda6b0` | ✗ 从未发布 |

1. package_id 由 settings + options + 依赖闭包共同决定："有制品"只是"默认变体有"。
2. conan 对不可用二进制的兼容性回退**只放宽 settings 类兼容性（如 cppstd），不构造不同 options 的替代变体** → 匹配不到就只能源码编。
3. 发布侧结论：发布缺失变体的唯一合规途径是**新版本号**（R37）。

## 方案

- 新版本 `libfuse/3.18.2.1`：源码与 4 个补丁和 3.18.2 完全相同（同一 `fuse-3.18.2.tar.gz`），**唯一差异** `default_options = {"shared": True, "fPIC": True}`；
- 本地 `conan create` 产出的 package_id 恰为 `0726937e…`——CI 报缺失的那个，证明精确补位；
- 制品发布后，消费方把 require 改指 3.18.2.1 即命中制品，免去每轮源码编译；
- **不改消费方选型**（退回静态链接）来"绕开"缺制品——那是语义变更。

## 验证

```bash
conan list "libfuse/3.18.2:*" -r=ohpcd                # package_id 级看全变体
conan graph info --requires=libfuse/3.18.2 \
  -o "libfuse/*:shared=True" -pr:h=<p> -pr:b=<p> --format=json   # 两取值对照
conan create archives/l/libfuse/3.18.2.1 …            # 产物应含 0726937e…
```

## 禁止做法

- ❌ 版本级 `conan list` 下结论（R35）："有制品/没制品"都不成立，必须 `"<ref>:*"` 按 package_id 看；
- ❌ 把每轮重编当"环境慢"、把 EAGAIN 当"偶发抖动"——变体缺制品是确定性根因；
- ❌ 在消费方 PR 里顺手建依赖包（JC6 单软件原子性）。

## 关联

- E234（exact override 需新包标识）：同族不同角度；
- 姊妹草稿 `DRAFT-ctest-upstream-tests-dependency-libdirs`（#14023 的另一半根因）。
