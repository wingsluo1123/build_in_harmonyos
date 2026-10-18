# E550（草稿）HarmonyOS PC 上 `umask 077 + mktemp -d` 目录属主亦不可写

- **状态**: 草稿（待主编审核提升编号）
- **严重度**: 3
- **类别**: platform, filesystem, autotools
- **来源**: raptor2/2.0.16 适配（路径 A，2026-10-16）
- **与既有条目的关系**: 见文末「去重与新增点」

## 错误特征

```
config.guess: unable to guess system type
./build/config.guess: line 1553: /…/cgoHbPFc/dummy.c: Permission denied
configure: error: cannot guess build type; you must specify one

config.status: error: could not setup config files machinery
./config.status: line 837: ./confpcFNHK/subs1.awk: Permission denied
```

## 触发条件（最小复现）

```sh
cd "$TMPDIR"
( umask 077; mktemp -d ./mtXXXXXX )        # → drwx--S--- (2700)
ls -lad ./mt*                              # 属主 = 当前用户
touch ./mt*/f                              # → Permission denied
```

对照（同一目录、同一用户）：

```sh
mkdir d && chmod 700 d && ls -lad d         # → drwxrws--x (2771)，touch d/f 成功
mkdir -m 700 d2 && ls -lad d2               # → drwxrws--x (2771)，可写
```

## 根因

本机文件系统（HarmonyOS PC, HongMeng Kernel 1.12.0 aarch64）对目录权限做归一化：
经 `mkdir` 或任何 `chmod` 之后，目录显示为 `drwxrws--x`(2771) 且可写；而 `mktemp -d` 在
`umask 077` 下直接 `mkdir(0700)` 建出的目录保持 `drwx--S---`(2700, 带 setgid)，**对属主本人也写入失败**（EACCES）。
实测属性 owner 与目标 uid 显示一致，故不是简单的"属主不同"；判断口径以「目录是否含 group 执行位」的实测为准。

## 影响面（两面）

1. **config.guess 兜底路径**：`uname` 未识别（如 HarmonyOS 未在旧 config.guess 列表中）时，config.guess 走"编译并运行探测程序"的兜底分支，先用
   `{ tmp=$(umask 077 && mktemp -d "$TMPDIR/cgXXXXXX") … ; }` 建临时目录，随后 `cat > "$dummy.c"` 即 EACCES。
   表面症状是 `unable to guess system type`，极易被误判为"config.guess 太旧"，真实原因在临时目录权限。
2. **autoconf 生成的 configure/config.status**：两处同样使用
   `tmp=\`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null\`` 与 `(umask 077 && mkdir "$tmp")`，
   于是 config.status 无法写 `subs1.awk` → `could not setup config files machinery`。

## 解决方案

- **首选（可复现、可审计）**：把改动落入 `patches/`，由 `apply_conandata_patches()` 每次对干净源码重放：
  ```diff
  -  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
  +  tmp=`mktemp -d "./confXXXXXX" 2>/dev/null` &&
     test -d "$tmp"
   }  ||
   {
     tmp=./conf$$-$RANDOM
  -  (umask 077 && mkdir "$tmp")
  +  mkdir "$tmp" 2>/dev/null
   } || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5
  ```
  先例：`archives/a/aaphoto/0.45/patches/0003-configure.patch`（同为 autotools + 生成文件补丁）。
- **根因侧**：让 config.guess 直接用 `uname -s=HarmonyOS` 得出三元组，不再进入兜底路径（E007/E160 + `scripts/patch-autotools-ohos.pl`）。两条一起做，症状才彻底消失。
- **不要**在探索阶段就地 `sed` 改 `configure` 而不落补丁（不可复现，且 review-memory §14 要求经 `patches/` 或 `generate()` 处理生成产物）。

## 验证方法

```sh
# 1. 平台行为
cd "$TMPDIR"; ( umask 077; mktemp -d ./mtXXXXXX ); touch ./mt*/f   # 期望 Permission denied
# 2. 补丁生效
conan create archives/<letter>/<name>/<version> -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
#    configure 不再报 cannot guess build type / could not setup config files machinery
```

## 限制与反例

- 该现象与具体路径无关（`$TMPDIR`、源码树内 `./confXXXXXX` 均可复现），取决于文件系统的目录权限归一化行为。
- `umask 022/002/000` 下 `mktemp -d` 正常可写；只有 `umask 077` 触发。
- 不适用于已确定平台的场景：若 config.guess 已通过 uname 得到三元组，则不会创建该临时目录，问题不出现（这也是"两条一起做"的原因）。

## 去重与新增点

与既有条目的关系：

| 条目 | 覆盖 | 本条的**新增** |
|---|---|---|
| E011 / E129 / E206（edit-umask-in-configure / sed-replace / patch-script） | config.status 因 `umask 077` 不可写；修法是 sed `configure`/`config.status` 改 umask | 给出 `mktemp -d`(2700 不可写) 与 `mkdir`+`chmod`(归一化为 2771 可写) **可复现的对照实验**，说明为什么"去掉 umask"就够；并指出**同一根因还会打断 config.guess 的兜底路径**（既有条目只覆盖 config.status 一面），后者症状伪装成 `unable to guess system type` |
| E007 / E160（config.guess 识别 HarmonyOS） | config.guess 不识别 HarmonyOS | 说明"补 config.guess 不只是加分支，还能顺带绕开 2700 临时目录"这一因果链 |
| E114 / E175 / E060 / E112 / E136 / E118 | 同源方案的多种变体（bypass-mktemp / autoreconf / tmpfs / 改脚本） | 明确**首选补丁化**（`patches/` + `apply_conandata_patches`）而非就地 sed，并给出 aaphoto 先例 |
