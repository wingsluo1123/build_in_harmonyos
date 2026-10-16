# 平台事实核实：OHOS 有 `/usr/bin/env`，缺的是 `/usr/bin/perl`

> **草稿状态**：draft，尚未经主编审核合入。
> 关联条目：`DRAFT-netpbm-10.73.42-e037-env-shebang-correction.kv`
> 定位：**证据补充与结论更正**（供主编修订正式条目 E037），非另立新类。
> 来源：netpbm 10.73.42 适配期实测（2026-10-15，HarmonyOS PC aarch64）

## 1. 为什么要更正

正式条目 **E037** 的 `root_cause` 写：

> 「鸿蒙系统**没有 `/usr/bin/env`**，使用 `#!/usr/bin/env xxx` shebang 的脚本无法执行。」

并据此给出处理策略：

> 「若不存在（如鸿蒙），则降级为直接 shebang：`#!/bin/sh`、`#!/bin/bash`、`#!/usr/bin/perl` 等」

在 HarmonyOS PC (aarch64) 上逐项实测后，**该前提不成立**，且降级方向会把脚本改写到
**不存在**的解释器路径上，制造新的"bad interpreter"故障。

## 2. 实测平台事实

| 路径 | 实测结果（2026-10-15） |
|---|---|
| `/usr/bin/env` | **存在** —— 软链 `→ ../../bin/toybox` |
| `/usr/bin/perl` | **不存在** |
| `perl` 实际位置 | `/data/service/hnp/bin/perl`（在 `PATH` 中） |
| `/bin/bash` | **不存在**（只有 `/bin/sh`）；bash 在 `/data/service/hnp/bin/bash` |

结论：OHOS 的解释器布局是"**部分对齐 Linux**"——`/usr/bin/env` 在（toybox 提供），
而 `/usr/bin/perl` / `/bin/bash` 这类具体解释器不在，改由 hnp 目录 + `PATH` 提供。

## 3. 两种 shebang 的行为对照（决定性判据）

```sh
printf '#!/usr/bin/env perl\nprint "OK-ENV\n";\n' > a.pl
printf '#!/usr/bin/perl\nprint "OK-ABS\n";\n'     > b.pl
chmod +x a.pl b.pl
./a.pl   # → OK-ENV          （env 经 PATH 找到 /data/service/hnp/bin/perl）
./b.pl   # → No such file or directory（内核 exec 找不到 /usr/bin/perl）
```

即：`#!/usr/bin/env <interp>` **是可执行的正确方向**；E037 建议的"降级为绝对路径
`#!/usr/bin/perl`"在 OHOS 上直接失败。

## 4. 处理策略

1. **安装期把写死的 Linux 绝对路径解释器改写为 `#!/usr/bin/env <interp>`**
   （注意去掉 `-w` 等额外参数——见 `DRAFT-ohos-perl-script-package-conan-adaptation`
   中 `env perl -w` 必败的实测）。
2. **判断前先在本平台实测**，不要套用"OHOS 没有 /usr/bin/env"的旧结论：

   ```sh
   ls -l /usr/bin/env        # → ../../bin/toybox
   command -v perl           # → /data/service/hnp/bin/perl
   command -v bash           # → /data/service/hnp/bin/bash
   ```

3. 若某解释器**在 PATH 中确实不存在**，则不要改写为 env 形式，而应
   `tool_requires` 对应工具（如 `perl/5.42.2`），由 Conan 的 runenv 提供 `PATH`。

### 安装期批量改写（幂等，只改首行）

```sh
grep -rl '^#!/usr/bin/perl' <package_folder>/bin \
  | xargs -r sed -i '1s|^#!/usr/bin/perl|#!/usr/bin/env perl|'
```

## 5. 限制与反例

- ❌ **禁止**依据"鸿蒙没有 `/usr/bin/env`"做降级决策（`forbid_1_pattern`）——
  会把脚本改写到不存在的路径。
- ❌ **禁止** `#!/usr/bin/env perl -w`：内核把 shebang 首个空白后的**全部内容**当作
  单个参数传给 env，env 会去找一个名为 `perl -w` 的程序 → 必然失败。
- ⚠️ 绝对路径兜底（`#!/data/service/hnp/bin/perl`）与 hnp 目录结构绑定，换机/换版本
  可能失效，仅作最后手段。
- ⚠️ 本条目只更正**平台事实与方向**；`#!/usr/bin/env` 之外的解释器环境问题
  （perl `@INC` 损坏、核心模块缺失）见
  `DRAFT-ohos-perl-script-package-conan-adaptation`，不在此重复。

## 6. 复现脚本

```sh
#!/bin/sh
# 复现 E037 前提不成立 + 两种 shebang 行为对照
set -e
echo "env  : $(ls -l /usr/bin/env 2>&1 | head -1)"
echo "perl : $(command -v perl 2>&1)"
echo "bash : $(command -v bash 2>&1)"
echo "usrbin_perl: $(ls -l /usr/bin/perl 2>&1 | head -1)"

PROBE_DIR="${TMPDIR:-.}"   # OHOS 上 /tmp 受限只读（E002），探针写临时目录或当前目录
printf '#!/usr/bin/env perl\nprint "OK-ENV\n";\n' > "$PROBE_DIR/a.pl"
printf '#!/usr/bin/perl\nprint "OK-ABS\n";\n'     > "$PROBE_DIR/b.pl"
chmod +x "$PROBE_DIR/a.pl" "$PROBE_DIR/b.pl"
"$PROBE_DIR/a.pl" || echo "a.pl FAILED"
"$PROBE_DIR/b.pl" || echo "b.pl FAILED (expected on OHOS)"
```

## 7. 关联知识

- 正式条目 **E037**（shebang 兼容性）—— 本条更正其前提与降级方向；
- `DRAFT-ohos-perl-script-package-conan-adaptation` —— 纯 Perl 脚本包适配（env perl 改写 +
  conan perl `@INC` 陷阱）；
- `DRAFT-8207-libgctp-automake-log-compiler-no-bin-bash` —— 同类"缺 `/bin/bash`"实例。
