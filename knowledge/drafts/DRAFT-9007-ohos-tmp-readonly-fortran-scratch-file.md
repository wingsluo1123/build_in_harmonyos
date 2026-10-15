# DRAFT-9007-ohos-tmp-readonly-fortran-scratch-file

> Draft（待审核 promote）｜对应: `knowledge/drafts/DRAFT-9007-ohos-tmp-readonly-fortran-scratch-file.kv`
> 说明：该 kv 为文档式条目，本文档为其可读镜像。

---

# DRAFT-9007: HarmonyOS /tmp 只读导致 Fortran `Status='SCRATCH'` 与 musl `tmpfile()` 失效 —— 改用 $TMPDIR 具名工作文件

- 条目主题：鸿蒙 PC 的 `/tmp` 只读，Fortran 未限定名的 `Open(Status='SCRATCH')` 与依赖
  `P_tmpdir` 的 `tmpfile()` 一律失败；通用处置是把临时文件落到 `$TMPDIR` 具名文件，
  并同步修掉测试脚本里的 `/tmp` 硬编码。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxxx）
- 关联 PR：feat/pftools-3.2.12

## 现象

```console
$ touch /tmp/x
touch: '/tmp/x': Read-only file system

# 程序里
 Error: Unable to create temporary file.
# 或 Fortran 运行时直接崩
fatal Fortran runtime error(...)            Signal 6 (core dumped)
```

- Fortran：`Open(N,Status='SCRATCH',Err=901)` 落到 `901` 分支；
- C：`tmpfile()` 失败（musl 的 `P_tmpdir` 固定 `/tmp`，**设 `TMPDIR` 无效**，实测仍 EACCES）；
- 测试脚本：`mkdir -p /tmp/xxx` → `Read-only file system`。

## 处置

### 1) Fortran：`SCRATCH` → `$TMPDIR` 具名文件（固定格式注意 72 列）

```fortran
* OHOS: /tmp is read-only -> Status='SCRATCH' is unusable.
      TMPNAM=' '
      Call Get_environment_variable('TMPDIR',TMPNAM)
      LTMP=LEN_TRIM(TMPNAM)
      If (LTMP.GT.0) TMPNAM=TMPNAM(1:LTMP)//'/pftools_psa2msa.scr'
      If (LTMP.LE.0) TMPNAM='pftools_psa2msa.scr'
 1    Open(NSEQ,File=TMPNAM,Status='UNKNOWN',Err=901)
```

声明区加 `Character*256 TMPNAM` + `Integer LTMP`。不要试图 `mkdir /tmp`、
`chmod 777 /tmp` 或 remount（全部无权限）。

### 2) C：`$TMPDIR` + `mkstemp` 替代 `tmpfile()`

```c
const char *dir = getenv("TMPDIR");
if (!dir || !*dir) dir = ".";
char tpl[PATH_MAX];
snprintf(tpl, sizeof tpl, "%s/<prog>.XXXXXX", dir);
int fd = mkstemp(tpl);
unlink(tpl);
```

### 3) 测试脚本：`/tmp` → `${TMPDIR:-/tmp}`

```sh
-TMPDIR=/tmp/test_V3
+TMPDIR=${TMPDIR:-/tmp}/test_V3
```

### 4) shell here-document 的临时文件（最隐蔽的一类）

即使脚本已经改用 `$TMPDIR`，**shell 自己**在展开 here-document 时仍可能创建临时文件，
并且把它放在 `/tmp`（与脚本内的 `TMPDIR` 变量无关）：

```console
$ sh -ve ./test_V3.sh
cat > $TMPDIR/ACGTAACGT.seq << EOI
test_V3.sh[236]: can't create temporary file /tmp/shwoi9bl.tmp: Read-only file system
```

特征：**同一条用例时通时不通**（本次实测：连续多次 ctest 中随机 6/6 与 2/6 交替），
排查时极易误判为"浮点/SIMD 不稳定"。

处置：把 here-document 改写成不依赖临时文件的写法，内容逐字节等价：

```sh
-cat > $TMPDIR/x.seq << EOI
->ACGTAACGT weight=10
-ACGTAACGT
-EOI
+printf '%s\n' '>ACGTAACGT weight=10' 'ACGTAACGT' > $TMPDIR/x.seq
```

其他等价写法：`echo` 多行、`{ echo ...; echo ...; } > f`。
修完后连跑 5 次脚本 + 2 次 `ctest` 全绿，且输出与上游参考仍逐字节一致。

## 证据（真实执行）

pftools 3.2.12：

- `psa2msa`/`regpr`/`pfw` 的 `SCRATCH` → "Error: Unable to create temporary file."，
  `test_V2.sh`/`test_V3.sh` 失败；
- `tmpfile()` 微验证 → `tmpfile: Permission denied`（带/不带 `TMPDIR` 均失败）；
- 改为 `$TMPDIR` 具名文件 + 测试脚本 `${TMPDIR:-/tmp}` 后：上游 CTest **6/6 通过**。

## 推广价值

- 所有含 Fortran `STATUS='SCRATCH'`、`tmpfile()`/`tempnam()`、或硬编码 `/tmp` 的上游包；
- 与既有 Gotcha「/tmp 只读（E002）」互补：给出可落地的三类替代写法与"为什么设 TMPDIR 无效"的机理。

## 查重关键词

/tmp 只读、Read-only file system、Status='SCRATCH'、Unable to create temporary file、
tmpfile Permission denied、musl P_tmpdir、TMPDIR 无效、Get_environment_variable、
Fortran 固定格式 72 列、测试脚本 /tmp 硬编码、here-document 临时文件、can't create temporary file、时通时不通
