# DRAFT-10718：`Autotools.make(args=[...])` 传多词变量值会被拆开 —— 追加库列表要改写生成的 Makefile

> Contributor: Lee-BX | Status: Draft | Updated: 2026-10-14
> Source: slurm-wlm 25.11.4 HarmonyOS PC 适配（`archives/s/slurm-wlm/25.11.4`）
> 对应：`knowledge/drafts/DRAFT-10718-autotools-make-args-multiword-value-splitting.kv`
> 相关：DRAFT-E687（命令行钉死 CFLAGS/LIBS）、
> DRAFT-makefile-slot-injection-and-patch-token-fingerprint（不覆盖而是新增槽位变量）

## 现象

适配 slurm 时需要在 configure 算出的 `LIBS` **尾部**追加几个库：一个 musl 垫片静态库
和 `-lncursesw`（termcap 符号顺序问题）。第一版写法是：

```python
autotools.make(args=["-j1", "LIBS=%s" % libs])   # libs = "<build>/libmusl_account_shim.a -L<ncurses>/lib -lncursesw"
```

结果 make 直接打印用法退出（或把 `-lncursesw` 当选项、把库名当目标），
而错误信息完全不指向配方代码，看起来像"Makefile 坏了"。

## 根因

Conan 的 `Autotools.make()` 把 `args` **原样空格拼接**，不加任何引号：

```python
# conan/tools/gnu/autotools.py（2.29.1）
str_extra_args = " ".join(args) if args is not None else ""
command = join_arguments([make_program, str_makefile, target, str_args, str_extra_args, jobs])
self._conanfile.run(command)

# conan/tools/gnu/autotools.py
def join_arguments(args):
    return " ".join(filter(None, args))
```

于是 `args=["LIBS=-lfoo -lbar"]` 生成的是 **三个词**：

```text
make LIBS=-lfoo -lbar
```

`make` 会把 `-lbar` 当**选项**（`usage:` / `unrecognized option`），
或者把 `-lfoo` 当**目标**去构建（`No rule to make target`）。用户的本意只是
"传一个含空格的变量值"。

### 为什么"追加库列表"特别容易踩

1. configure 已经算出一长串 `LIBS`（`-lhwloc -lmunge ... -lncursesw -lc -ldl`），
   我们只想**追加**几项；
2. 用命令行变量就得把整串原值**重放**一遍 —— 脆弱，configure 结果一变就失效；
3. 而多词值又恰好过不了 `Autotools.make` 的拼接。

（补充事实：make 的命令行变量**会**通过 `MAKEFLAGS` 下传到子 make，
所以问题不在"传不下去"，而在"传进去时被拆成了多个词"。）

## 正确做法（推荐：改写生成的 Makefile 变量行）

在配方里用一个幂等的自有方法，把追加项挂到 build 目录下**所有生成的** Makefile 的
`LIBS = ` 行尾：

```python
def _patch_makefile_libs(self):
    """Append the compat tail to LIBS in every generated Makefile."""
    tail = self._shim_tail()      # "<build>/libmusl_account_shim.a -L<ncurses>/lib -lncursesw"
    patched = 0
    for base, _dirs, files in os.walk(self.build_folder):
        if "Makefile" not in files:
            continue
        path = os.path.join(base, "Makefile")
        text = io.open(path, encoding="utf-8", errors="replace").read()
        out = []
        for line in text.split("\n"):
            if line.startswith("LIBS = ") and tail not in line:
                line = line + " " + tail
                patched += 1
            out.append(line)
        io.open(path, "w", encoding="utf-8", newline="").write("\n".join(out))
    self.output.info("patched LIBS in %d generated Makefile(s)" % patched)
```

三条优点：

1. **追加**语义 —— 保留 configure 的探测结果，不重放、不失效；
2. 覆盖所有子目录 Makefile —— `make` 与 `make install` 都生效（`install` 会重新链接）；
3. **幂等** —— 带 `tail not in line` 判断，可重复执行。

这是对**构建期生成物**的后处理：上游源文件零改动，生成物只在 build 目录里被加工、不进仓库。

## 备选做法（自己拼引号）

若确实要用命令行变量，就别走 `Autotools.make(args=[...])`，而是自己拼一条带引号的命令：

```python
self.run('make -j1 LIBS="%s"' % libs, env="conanbuild", cwd=self.build_folder)
```

代价：要自己处理引号/转义，而且命令行变量是**覆盖**语义，必须把原值一起重放。

## 反例（禁止）

```python
autotools.make(args=["LIBS=-lfoo -lbar"])   # ✗ 值会被拆成多个 make 词
```

## 验证

```sh
# Conan 侧的拼接行为（可直接复现）
python3 -c "from conan.tools.gnu.autotools import join_arguments as j; print(j(['make','LIBS=-la -lb']))"
# → make LIBS=-la -lb          （没有引号）

# shell 侧对比
make LIBS="-la -lb"      # ✗ usage / -lb 当选项
make "LIBS=-la -lb"      # ✓ 单引号整体保留

# 适配侧验收
grep -m1 "^LIBS = " <build>/Makefile      # 行尾应出现追加的 tail
```

slurm 25.11.4 实测：改用改写生成 Makefile 的方式后，`make -j1` 与 `make -j1 install`
均一次通过，`libmusl_account_shim.a` 与 `-lncursesw` 出现在 230 个生成的 Makefile 的 `LIBS` 行尾。

## 通用化建议

1. 用任何"把参数列表 join 成命令行"的构建助手时，**不要把多词值放进列表**；
   含空格的变量值要么自己拼引号，要么换成"改写生成的配置文件/生成物"的路线。
2. 判断"变量有没有传进去"最直接的证据是**生成的 Makefile 里那一行**（或 make 打印的实际命令行），
   而不是配方里写了什么。
3. 需要"在构建系统算出的值后面追加"时，优先选"追加到生成物"而不是"覆盖命令行变量"：
   后者要求重放原值，天然脆弱。
