# DRAFT: setuid 投递型包在 OHOS 的安装四重墙 + 运行期不触发（dma 0.14 实证）

- 条目主题：以 `setuid`/`setgid` 方式安装助手二进制、依赖 `/var` spool 与 root 运行的上游（MTA/投递助手族）在 HarmonyOS PC 上的**安装四重墙**与**运行期不触发**，以及不改上游、不 mock 的合规处置。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联软件：dma 0.14（DragonFly Mail Agent）；同范式适用于 nullmailer / ssmtp 等投递型同族。
- 归属：本机制在知识池四范围查重 **0 命中**（详见末节），故按 create 提交；`E203`（musl 无 `getprogname`）是本包复用的**另一条**已有条目，只作 cross-ref，不占本 PR 知识位。

## 错误特征（实测读数，2026-10-08）

- `install: command not found` / `install -m 4754 …` → **`rc=127`**
- `grp.getgrnam('mail')` → **`KeyError: "getgrnam(): name not found: 'mail'"`**（`mail` 组不存在）
- `chmod u+s <file>` 返回 `ok`，随后 `stat` → **`setuid=False setgid=False`**，mode 实得 **`0o770`**
- `stat('/var')` → **`errno=2(ENOENT)`**；`write('/etc')` → **`errno=30(EROFS)`**；`write('/')`、`write('/usr')` → **`errno=13(EACCES)`**
- 运行身份 `uid=20020084`（非 root）

## 根因

上游按 **BSD/Linux `root` + `mail` 组 + setuid/setgid 特权投递**模型设计安装与运行路径
（`Makefile:53-54`：`install -m 2755 -o root -g mail dma …`、`install -m 4754 -o root -g mail dma-mbox-create …`）。
OHOS/HarmonyOS PC 是**无 root 应用沙箱 + HMDFS 文件系统**：

1. **`install` / `chgrp` 命令不存在** ⇒ 上游 `install` 目标天然不可执行（`rc=127`）；
2. **非 root** ⇒ `-o root` 不成立；
3. **`mail` 组不存在** ⇒ `-g mail` 必失败；
4. **特权位被剥离** ⇒ `chmod u+s` 成功返回但 `stat` 读回 `setuid=False`；
5. **`/var` 不存在**（父 `/` 还 `EACCES`）⇒ 上游默认 spool `${VAR}/spool/dma` 无处安放，
   `install-spool-dirs`/`permissions` 目标不可执行；
6. **运行期不触发**：`dma.c:464` 只有 `geteuid()==0 || getuid()==0` 才进入降权块
   （`dma.c:476 setuid(pw->pw_uid)`），非 root **整块不进入** ⇒ 投递助手的特权语义在本平台不存在。

## 处置（合规三件套：编译照交 / 自装 / 参数期断言）

```python
# package()：不调上游 install 目标（四重墙），从 build folder 自装
copy(self, "dma", src=self.source_folder, dst=bindir, keep_path=False)
copy(self, "dma-mbox-create", src=self.source_folder, dst=libexecdir, keep_path=False)
os.chmod(0o755)   # 特权位在 OHOS 不可用，按普通可执行文件交付
```

- **test_package 只打参数期断言**：`dma -Z` → `invalid argument` + `EX_USAGE(64)`；
  `dma -bp -q` → 队列模式互斥护栏 + `EX_USAGE(64)`；两者失败点均**早于 `dma.c:606 parse_conf`**，
  不读配置、不碰 spool、不碰真投递路径；
- **能力面逐字披露**：四重墙 + errno 表 + 运行期降权条件写入 `notes.md`、`manifest.yaml` 与 PR 补充说明；
- ⛔ **不改上游 `Makefile`、不 mock 任何环节**（`Makefile:53-54` 原文与全部读数留档）。

## 验证

dma 0.14：`conan-verify` G0–G4 全 PASS、W3 本地 CI 通过、`test_package` 2/2 断言通过；
四重墙探针读数与源码行号链（`Makefile:53-54`、`dma.c:464/476/606`）三处同源。

## 四范围查重（2026-10-08 实测）

| 范围 | 结果 |
|---|---|
| 1 `经验文档/适配经验汇总.md` | `setuid\|setgid\|suid\|chown` **0 命中** |
| 2 知识图谱 `knowledge/graph/index.tsv` + `knowledge/doc/` | word `setuid` 仅 `E453`（HMDFS mode 投影）、`setgid` 仅 `E011/E129/E533`（umask 临时目录）；`mail\|MTA\|投递` 关键词行 **0**；均非本机制 |
| 3 `经验文档/经验库/*.md` | 命中为 `setgid` + `mktemp`/HMDFS 目录树语境（`05`/`12d`），非本机制 |
| 4 `经验文档/OHOS行为探针清单.md`（43 行）+ `经验库/14-最终防错清单.md` | `setuid\|setgid\|suid\|chown\|特权` **0 命中** |

## 关联

- `E203`（OpenHarmony musl 无 `getprogname()`，用 `__progname`）—— 本包另一处适配所复用的**已有**条目，cross-ref。
- `E081`（setuid 场景降级）、`E453`（HMDFS mode 投影含 setuid 位）—— 关键词相邻但机制不同。
