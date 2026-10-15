# E588 — W3 用 zsh 执行 CI 脚本，其 here-document 临时文件只认 `TMPPREFIX`，`/tmp` 只读时伪装成 L0i AST 解析失败

## 错误特征

```
ci/conan/build_and_test.sh:439: can't create temp file for here document: read-only file system
...
❌ L0i: conanfile.py AST 解析失败（检查是否有语法错误 / UTF-8 BOM）
```

关键误导：报错行指向一个 **python AST 提取用的 here-document**，错误提示却让人去查
`conanfile.py` 的语法或 BOM——而配方本身完全正常。

## 触发条件

- 平台: `/tmp` 只读（HMDFS / 鸿蒙 PC worker）
- 执行方式: **zsh** 执行 `ci/conan/build_and_test.sh`（W3 本地 CI 模拟就是这样调的）
- 位置: 脚本中任何 `<<'EOF'` here-document（本包命中的是 L0i 依赖提取处）

## 根因分析

zsh 的 here-document 临时文件前缀由 `TMPPREFIX` 决定（默认 `/tmp/zsh`），
**它不看 `TMPDIR`**：

- `TMPDIR=$HOME/tmp` 重跑 → 依然失败（zsh 忽略它，仍是 `/tmp/zsh*`）；
- `TMPPREFIX=$HOME/tmp/zsh` → 立即通过；
- `bash` 反而会回退到 cwd，`env -u TMPDIR bash -c 'cat <<EOF'` 在可写 cwd 下能成功。

因此“`/tmp` 只读 → 设 `TMPDIR` 就行”的做法在 **zsh** 场景下不成立。脚本的错误归类
又把 here-doc 失败记在 L0i（依赖检查）头上，于是同一根因被反复误诊为配方语法问题。

## 解决方案

### 推荐方案

```bash
TMPPREFIX=$HOME/tmp/zsh TMPDIR=$HOME/tmp zsh ci/conan/build_and_test.sh <name>/<version>
```

先用一行命令确认杠杆：

```bash
TMPPREFIX=$HOME/tmp/zsh zsh -c 'x=$(cat <<EOF
hi
EOF
); echo $x'
```

### 禁止做法

- ❌ 改 `ci/conan/build_and_test.sh` 去掉 here-document（`ci/` 属框架文件，配方 PR 不得改，W2）
- ❌ 依据 L0i 的提示去改 `conanfile.py` 的语法/BOM（本次配方并无该问题）
- ❌ 只设 `TMPDIR` 反复重试（zsh 下必然无效）

## 验证

- 未设 `TMPPREFIX`：`build_and_test.sh:439: can't create temp file for here document: read-only file system`
- 设 `TMPPREFIX=$HOME/tmp/zsh`：同一条命令走完 L0/JC/KC/L1/L4，最终 `exit_code=0`

实测（kitchen 1.2.6，2026-10-02）：该环境变量是唯一差异，配方与补丁未变。

## 关联条目

- 相关: E011（mktemp/umask 类环境问题）、E588 所属的“环境伪失败”族
