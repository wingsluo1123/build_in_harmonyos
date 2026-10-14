# E700 — 上游回归脚本"无输出即通过"、退出码恒为 0（sng_regress）

## 错误特征
- `make check` 末尾只有 `echo "No output is good news."`；脚本 `sng_regress` 在子步骤失败时仅打印
  `<file>: decompilation of the test PNG failed` 之类的一行，**不 exit**，整个脚本退出码恒为 0。
- 配方里 `self.run("bash ./sng_regress ...")` 不抛异常，W3 / CI 显示绿，但回归其实可能全红。

## 触发条件
- 构建系统: 手写 Makefile（sng 1.1.1，依赖 libpng → zlib）
- 阶段: testing（配方 `build()` 里的上游测试；`test_package` 里的二进制校验同理）

## 根因分析
`check()` 只 `echo`，脚本无汇总退出码，约定靠"无输出=通过"。实测反例：

```
$ echo notpng > bad.png; bash ./sng_regress bad.png >out 2>err; echo $?
0
$ cat out
bad.png: decompilation of the test PNG failed
bad.png: recompilation of the decompiled form failed
bad.png: generation of the canonicalized form failed
bad.png: recompilation of the canonicalized form failed
```

反向陷阱：健康输入 `test.sng` 也会让 libpng 往 **stderr** 打 `libpng warning: hIST: out of place`
（测试文件故意含 hIST/tRNS 边界用例）。把 stderr 并进判据会把健康构建误判为失败。

## 解决方案

### 推荐方案
捕获 **stdout** 并断言为空，stderr 不参与判据：

```python
out = StringIO()
self.run(f'TMPDIR="{tmpdir}" bash ./sng_regress test.sng snglogo.png',
         cwd=self.source_folder, env="conanrun", stdout=out)
if out.getvalue().strip():
    raise ConanException(f"upstream sng_regress reported failures:\n{out.getvalue()}")
```

同时按最小补丁处理 OHOS 差异：脚本硬编码 `/tmp`（OHOS 上只读）与 `diff -c`（toybox diff 无 `-c`），
改为 `${TMPDIR:-/tmp}` 与 `diff -u`。判据落地前先跑反例（损坏输入）确认它真的会红。

### 回退方案
build 机无法执行目标二进制（x86 runner + aarch64 产物）时，上游回归如实 skip（WARN，不写成通过），
由 `test_package` 完整消费者流程承担功能证据（被测二进制产出 PNG → 消费者程序用 libpng 解码校验 → 反编译/重编译往返），
并在 aarch64 原生 CI 上实跑。

### 禁止做法
- ❌ 只看 `self.run()` 是否抛错就把上游回归计为通过。
- ❌ `2>&1` 合并后断言"输出为空"（libpng warning 属正常 stderr）。
- ❌ 不跑反例就信任新写的判据。

## 验证
```bash
echo notpng > bad.png
TMPDIR=$PWD bash ./sng_regress bad.png >out.txt 2>err.txt; echo "exit=$? stdout_lines=$(wc -l <out.txt)"   # exit=0 stdout_lines=4
TMPDIR=$PWD bash ./sng_regress test.sng snglogo.png >out.txt 2>err.txt; echo "exit=$? stdout_lines=$(wc -l <out.txt)"  # exit=0 stdout_lines=0
```

## 关联条目
- 相关: E239（self.run 遇首个非零即抛 ConanException，本条是其反面：脚本永不返回非零）、E568-draft-5818（手写 Makefile 命令行注入与 `make -e` 的取舍）
