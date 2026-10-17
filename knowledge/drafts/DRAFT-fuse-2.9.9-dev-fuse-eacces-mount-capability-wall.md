# DRAFT：OHOS 上 `/dev/fuse` EACCES ⇒ FUSE 用户态栈的运行期能力墙与验证面判据

- **草稿 id**：`DRAFT-fuse-2.9.9-dev-fuse-eacces-mount-capability-wall`
- **来源**：fuse 2.9.9（FUSE 2.x / Libfuse2 legacy ABI）适配，2026-10-16，OHOS aarch64 / clang 15.0.4
- **建议**：`create`（新增跨库复用机制）
- **适用范围**：所有 FUSE 用户态消费者（libfuse 2.x/3.x 本体 + sshfs、mtpfs、mhddfs、ifuse、bindfs、s3fs-fuse、ext4fuse、zfs-fuse、securefs、winregfs 等）

## 1. 症状与稳定签名

| 探针 | 实测读数（B 机，2026-10-16） |
|------|------------------------------|
| `ls -l /dev/fuse` | `ls: /dev/fuse: Permission denied` |
| `open("/dev/fuse", O_RDWR)` | **FAIL，`errno=13`（EACCES / Permission denied）** |
| `os.path.exists("/dev/fuse")` | **`False`** ← 假阴性（stat 被拒 ⇒ 存在性 API 报"不存在"） |
| `grep -i fuse /proc/modules` | 无命中（fuse 模块未加载） |
| `ls -ld /etc` | `/etc -> /system/etc`（符号链接） |
| 系统 `fusermount`（4 处候选路径） | 均不存在 |
| 本包 `bin/fusermount` | `mode=0o770 setuid=False` ⇒ upstream `chmod u+s` **未生效**（E046） |

稳定签名（可用于匹配）：

```
fuse: failed to open /dev/fuse: Permission denied
ls: /dev/fuse: Permission denied
errno 13 (EACCES) on open("/dev/fuse", O_RDWR)
```

## 2. 根因

1. OHOS 未向本进程开放 `/dev/fuse` 字符设备：**节点存在**（`ls` 报的是 `Permission denied` 而不是 `No such file`，`open` 报 `EACCES` 而不是 `ENOENT`），但被 SELinux/权限策略拒绝；`/proc/modules` 里也没有 fuse。
2. 次生事实 A：`os.path.exists()` / `access(F_OK)` 在 `EACCES` 场景返回 `False` —— **存在性 API 会把"存在但不可访问"误判成"不存在"**。
3. 次生事实 B：OHOS 忽略 `chmod`（E046，同族 E011/E046 权限面），所以 upstream `util/Makefile.am` 的 `install-exec-hook`（`chmod u+s fusermount`）无效果，`mknod /dev/fuse` 也被拒（上游以 `|| true` 兜底，不阻塞构建）。

## 3. 影响面

* `fuse_mount()` / `fuse_session_mount()` 必然返回 `NULL`；`fuse_loop()`/`fuse_loop_mt()` 无从执行；`fusermount` 的挂载/卸载面不可用。
* 一切依赖真实挂载的上游测试与端到端 smoke 在本平台不可执行（本包实测：`fuse_mount()` 打印 `fuse: mountpoint is not empty` 已越过挂载点检查，随后 open `/dev/fuse` 失败返回 NULL，与裸探针 `errno=13` 一致）。
* **编译期不受影响**：头文件与静态库完好，`conan create` 全通。

## 4. 最优解（推荐做法）

1. **判别用 errno，不用存在性 API**：`ENOENT=真不存在`、`EACCES=存在但不可访问`，两者都归"打不开"；同时看 `/proc/modules`。
2. **交付形态**：库面照常交付，把挂载面如实披露为能力墙（notes.md / MANIFEST / PR 正文三处同源）。
3. **测试写成"探针 + 一致性断言"，不写死失败**：
   * 先裸 `open("/dev/fuse", O_RDWR)` 取 errno；
   * 再断言 `fuse_mount()` 的成功/失败与探针**一致**（探针成功 ⇒ 断言返回非 NULL；探针失败 ⇒ 断言 NULL）。
   * 这样平台将来放开权限时，断言会自动改判成"应当成功"，不会把平台改进误判成回归。
4. **探针必须带负向对照**（否则是恒真断言）：`open("/dev/null")` 必须成功（证明探针能观察到"成功"）；`open(不存在路径)` 必须返回 `ENOENT`（证明 errno 读数是区分的）。
5. **CLI 只断言参数解析即返回的文本路径**：`--version`（rc=0 + 版本串）、`-h`（rc=1 + usage）、无参数（rc=1 + `missing mountpoint argument`）、非法选项（rc=1 + `unrecognized option`，作为负向对照）、`-z` 无 `-u`（rc=1 + 专用报错）。⛔ 不碰挂载、⛔ 不 mock 设备节点。
6. **库面离线 API 真断言**：`fuse_version()==FUSE_VERSION`、`fuse_opt_parse` 取值（换输入值结果随之改变作负向对照）、`fuse_parse_cmdline` 真解析（`-s` 翻转 multithreaded 作负向对照）、`fuse_lowlevel_new()` 离线建会话后 destroy。

## 5. 已尝试/已排除

* 用 `os.path.exists()` 判 ⇒ **假阴性**，得出相反结论，已排除。
* mock `/dev/fuse`、伪造挂载成功 ⇒ ⛔ 制造假绿，排除。
* 只跑 `fusermount --version` 就宣布"验证通过" ⇒ 断言太弱（掩盖 mount 面全不可用），排除。
* 不加 `--disable-mtab`：`/etc` 是符号链接这一差异在挂载面不可达时**不可观测**，保持与既有同源配方同参数集，如实记录待将来复议。

## 6. 与既有条目的关系（查重结论）

四范围查重 **0 命中**（`knowledge/graph/` 与 `knowledge/doc/` 全库 grep `dev/fuse` 为空；经验库无 FUSE 能力面条目；OHOS 行为探针清单无 fuse 行）。

可作对照的**不同机制**条目：

* `DRAFT-ddccontrol-1.0.3-i2c-dev-device-node-unavailable`：同为"设备节点能力面"，但那条是 `ENOENT`（真不存在）+ 内核无模块；本条是 **`EACCES`（存在但不可访问）+ 存在性 API 假阴性**，并新增"探针+一致性断言"这一可执行判据形态。
* `E046`（chmod 不生效）：本条把它作为 setuid 失效的次生事实引用。
* `E011` / `E051` / `E085`：本包**复用**的既有条目（umask 077、示例链接 pthread_cancel），不属于本条新增。

## 7. 反例与边界

* 不要写成"FUSE 在 OHOS 永久不可用"——只主张"本机实测打不开，且 `exists()` 判会得到相反结论"。
* 在放开 `/dev/fuse` 权限或加载 fuse 模块的环境复跑：一致性断言会自动改判，无需改测试代码。
* 本条不覆盖 FUSE 协议实现细节、不覆盖内核侧 fuse 行为、不覆盖 setuid 权限模型放开后的情形。
