# SKILL: FUSE 临时目录写入被拒检测与预防（fuse-tmp-write-guard）

> 版本 1.0.0 · 适用 OHOS PC（aarch64）三方库适配流程 · Conan 2.x
> 定位：把「umask 077 + FUSE uid 映射错位 → 构建期临时目录写入被拒」从
> **几十分钟后的 configure/test 阶段硬失败**，提前成**一次廉价探测 +
> 两段可直接执行的修复命令**。一次入库、多次复用。

## 1. 一句话说明

本仓库的 FUSE（HMDFS）工作区存在复合平台陷阱（E046 的具体化变体）：
**工具链按 Unix 惯例 `umask 077` 创建的临时目录（0700/0600），创建者自己
随即就写不进去，且 chmod 补救被静默忽略**。本 SKILL 做三件事：

1. **识别**：扫构建日志的报错特征行（config.status/conf*/cmp EOF）+ 扫
   源码的 umask077×mktemp 共现 + 在目标目录实测探针；
2. **给策略**：输出两类可执行修复（umask 000 wrapper 注入 / config.status
   内部 umask 重写补丁）；
3. **可复现**：自带双向验证脚本（关 SKILL 复现原始报错 / 开 SKILL 生效）。

## 2. 问题机理（为什么 chmod 777 救不了）

| # | 因素 | 实测行为 |
|---|------|---------|
| ① | uid 映射错位 | 进程 uid 与 FUSE 显示属主不一致（目录属主显示 20001006，进程 uid 20020084）——属主权限位不生效 |
| ② | chmod 被静默忽略（E046） | `chmod 777 x` 退出码 0 但 stat 不变——事后补救无效 |
| ③ | umask 077 惯例 | autotools config.status / mktemp harness / 各类构建工具按惯例建 0700/0600 临时区 |

三者叠加：**umask 077 创建的目录 = 任何 uid 都不可写的黑洞**。唯一可靠
绕法是 umask 000（0777/0666 不依赖属主位）。

## 3. 适用范围

### 3.1 适用（任一满足）

| 场景 | 具体表现 |
|------|---------|
| configure 阶段失败 | `config.status: ... can't create ./confXXXXXX/subs1.awk: Permission denied` |
| 上游测试 harness 失败 | `cmp: EOF on /tmp/xxx after byte 0`（mktemp 输出文件写入失败 → 空文件对比） |
| 适配前风险评估（W0 阶段） | 上游源码/脚本含 `umask 077` × `mktemp XXXXXX` 共现（如 tests/ 里 mktemp harness） |
| 环境确认 | 在新工作区/新机器上确认该 FS 是否带此陷阱（`--probe-fs`） |

### 3.2 实证样例（一类问题，非单库补丁）

| 样例库 | 触发点 | 后果 |
|--------|--------|------|
| oddjob 0.34.7 | `./configure` → config.status 第 860 行段落 `umask 077 && mktemp -d ./confXXXXXX` → 写 subs1.awk | configure 硬失败，PR 无法产出（探索期手工改 umask 000 才修通） |
| oddjob 0.34.7 tests/cmdparse | `test-cmdparse.sh` 的 `mktemp $TMPDIR/cmdparseXXXXXX`（0600 输出文件） | 9 组向量 cmp 全部 EOF 误报失败 |

### 3.3 不适用

| 情形 | 原因 / 应做什么 |
|------|----------------|
| 普通磁盘（ext4 等）上的 0700 目录 | 属主权限正常生效；本 SKILL 的 `--probe-fs` 会返回 ENV_NOT_AFFECTED |
| EACCES 由 SELinux/DAC 真实拒绝（非 umask 形态） | 报错行不含 conf*/mktemp 特征——那是 E046 原条目与系统策略问题 |
| 构建产物权限问题（非临时目录） | 产物 0644 通常够用；只有 0600/0700 临时区才触发 |
| 配方内部需保留严格权限的安全场景 | umask 000 会放宽新建文件权限——该场景应改用 build_dir_migration 策略 |

## 4. 使用方法

### 4.1 检测（三通道，可单用可合用）

```bash
SKILL=skills/fuse-tmp-write-guard

# ① 扫构建日志（W3/CI 失败日志直接喂入）
python3 $SKILL/scripts/fuse_tmp_write_guard.py --log conan-create.log

# ② 扫上游源码/脚本（适配前预检：umask077×mktemp 共现）
python3 $SKILL/scripts/fuse_tmp_write_guard.py --source upstream-test.sh

# ③ FS 实测探针（建临时目录验证，自动清理）
python3 $SKILL/scripts/fuse_tmp_write_guard.py --probe-fs ~/tmp --fix

# 退出码: 0=CLEAN  1=HIT  2=参数错误   --json 供流水线消费
```

### 4.2 修复（两条策略，按场景二选一或组合）

**策略① umask 000 wrapper 注入**——适用于构建命令继承外层 umask 的场景
（conan create、make、cmake 等不自设 umask 的工具链）：

```bash
# 原: ./configure --prefix=... && make
# 改:
sh $SKILL/scripts/ohc_umask_wrap.sh sh -c './configure --prefix=... && make'
# 语义: 仅放宽 umask、退出码原样透传、无自身输出（日志重定向由调用方负责）
```

**策略② config.status 内部 umask 重写**——适用于脚本**内部自设 umask**
的场景（外层注入无效，oddjob 实战已验证：子 shell 会自我重置）：

```bash
# configure 生成 config.status 后、执行它之前：
sh $SKILL/scripts/ohc_fix_config_status_umask.sh ./config.status
# 行为: 原地改写 (umask 077 && mktemp → (umask 000 && mktemp，
#       备份 .umaskbak，自校验，幂等（重复运行无害），dry-run 可预览
```

**边界结论（实测）**：config.status 类脚本**必须用策略②**——策略①对
「脚本内部自设 umask」无效；两类脚本同时存在时组合使用。

### 4.3 配方内集成模式（conanfile.py）

```python
def build(self):
    old = os.umask(0o000)          # 策略①等价物：recipe 内直接注入
    try:
        self.run("./configure ...")
        self.run("make ...")
    finally:
        os.umask(old)              # 恢复，不外溢
```

## 5. 输入输出定义

| 接口 | 输入 | 输出 |
|------|------|------|
| `--log <file>`（可多次） | 构建日志 | 逐行证据 `[L1/L2/L3] file: line` |
| `--source <file>`（可多次） | 源码/脚本 | 风险点 `[S] file:line: why`（umask077×mktemp 共现才报） |
| `--probe-fs <dir>` | 工作目录 | `harness_vulnerable` bool + 机理证据（chmod 是否有效/umask000 对照） |
| `--fix` | - | 三段修复建议（umask_injection / build_dir_migration / recipe_pattern） |
| `--json` | - | 机器可读全量结果（流水线消费） |
| `ohc_umask_wrap.sh <cmd>` | 构建命令 | 透传执行（umask 000 环境），退出码原样 |
| `ohc_fix_config_status_umask.sh <path>` | config.status | 原地改写 + `.umaskbak` 备份；退出码 0/2/3/4（见脚本头） |
| `tests/repro_umask_trap.sh [dir]` | - | 双向验证：`TRAP_CONFIRMED_SKILL_EFFECTIVE` / `ENV_NOT_AFFECTED` / `UNEXPECTED` |

## 6. 自检与验证

```bash
# 单元测试（8 项：L1/L2/L3 特征行、误报排除、共现规则、退出码契约）
python3 $SKILL/tests/test_fuse_tmp_write_guard.py

# 双向验证（样例库 oddjob 同型探针；受影响环境预期
# TRAP_CONFIRMED_SKILL_EFFECTIVE，正常 FS 预期 ENV_NOT_AFFECTED）
sh $SKILL/tests/repro_umask_trap.sh
```

实测记录（2026-10-11，本仓库 FUSE 工作区）：
- Phase A（SKILL 关）：`config.status[repro]: can't create ./confpFASvk/subs1.awk: Permission denied` ✅ 复现
- Phase B（SKILL 开）：wrapper 注入后写入成功，rc=0 ✅ 生效
- 单元测试 8/8 通过

## 7. 限制与不适用声明

1. **仅覆盖 umask 形态**：uid 映射错位的其他表现（如跨属主 chown 需求）不在本 SKILL 范围；
2. **umask 000 的安全边界**：放宽的是*新建临时文件*权限，不改变既有文件；安全敏感构建（需 0700 隔离的场景）应改用构建目录迁移策略（迁到非 FUSE fs）；
3. **策略②的模式特异性**：只改 `umask 077 && mktemp` 这一种形态；上游若用其他 077 变体（如 `umask 077; mkdir`）需人工按同法扩展；
4. **E046 关联**：chmod 无效是本陷阱的放大器而非根因——E046 条目覆盖更广的 chmod 失效场景，本 SKILL 是其在「umask077×临时目录」上的专用化解法。

## 8. 样例库

- **主样例**：oddjob 0.34.7（`archives/o/oddjob/0.34.7/`）——两处独立触发点（configure 阶段 config.status + 上游测试 harness），覆盖「策略②配方内固化」与「上游 harness 阻塞如实上报」两种处置；其 conanfile 生成 config.h 的方案使配方完全不跑 configure，从结构上规避了 config.status（策略②的替代形态）。
- 复现与验证不依赖 oddjob 源码：`tests/repro_umask_trap.sh` 的探针即 config.status 关键段落的逐字复刻。
