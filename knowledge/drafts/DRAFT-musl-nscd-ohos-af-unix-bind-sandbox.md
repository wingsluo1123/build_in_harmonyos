# DRAFT: OHOS 仅在应用沙箱数据目录下允许 bind() AF_UNIX socket

- **状态**：草稿（待知识库主编审核，拟提升编号 Exxx）
- **关联**：musl-nscd 1.1.1 OHOS 适配（feat/musl-nscd-1.1.1）；相似条目 E024、E253
- **严重度**：2（🟡 中）——不阻断编译，但会让守护进程型库的"功能可用"验证在沙箱外必然失败

## 错误特征

```
nscd: Operation not permitted            # 守护进程启动即退出（EPERM）
PermissionError: [Errno 1] Operation not permitted   # python bind AF_UNIX
bind(...): Operation not permitted
```

## 根因

OHOS 安全策略（hmmac / SELinux）对 **AF_UNIX 文件系统 socket 的 `bind()` 做路径级管控**：
只放行应用沙箱数据目录 `/data/storage/el2/base` 及其子目录；在 `$HOME`、`$TMPDIR`
（`/storage/Users/currentUser/tmp`）、构建目录、`/dev/shm` 等沙箱外路径下一律返回 **EPERM**。

限制精确落在"文件系统 socket 的 bind()"这一点上，同环境下：

| 操作 | 结果 |
|------|------|
| `socketpair(AF_UNIX, SOCK_STREAM)` | ✅ OK |
| `socket(AF_UNIX, SOCK_STREAM)` | ✅ OK |
| `bind()` 到 `$HOME` / `$TMPDIR` / 仓库目录 / `/dev/shm` | ❌ EPERM(1) |
| `bind()` 到 `/data/storage/el2/base/...` | ✅ OK |
| 抽象命名空间 `bind("\0name")` | ✅ OK |
| `bind()` AF_INET `127.0.0.1:0` | ✅ OK |

### 定位方法（可复用）

1. 用 python 探针分别试 `socketpair` / `socket()` / `bind()` / `AF_INET bind()`，
   一次区分"被限制的是哪一步"与"是否路径相关"。
2. 用被测进程自身做判别：把 socket 路径指向**不存在的目录**——
   - 返回 `No such file or directory` ⇒ `socket()` 成功，失败点确定在 `bind()`；
   - 仍返回 `Operation not permitted` ⇒ 连 `socket()` 都未通过。
3. 逐个候选目录试 bind，找出允许的位置（本环境为 `/data/storage/el2/base`）。

## 影响范围

所有守护进程型 / IPC 型三方库在 OHOS 上的 smoke test 与运行期验证：

- nscd / syslogd 风格常驻服务；
- 自行创建 AF_UNIX 监听端的测试脚本（把 socket 放在 `$TMPDIR` 的默认写法在 OHOS 上必挂）；
- 依赖 `/var/run/*.sock`、`/tmp/*.sock` 的库（这些路径在 OHOS 上同时还有"不存在/不可写"的问题）。

## 推荐方案

**方案 1（优先）：把 bind 位置改道到应用沙箱数据目录**

```
nscd -c $CONF -s /data/storage/el2/base/${PKG}-e2e-$$/nscd.sock -p $PIDFILE
```

测试脚本按候选目录顺序探测（`$NSCD_SOCK_DIR` → `/data/storage/el2/base` → `$TMPDIR`），
探测成功才启用端到端协议测试。musl-nscd 实测在该目录下**完整跑通**：守护进程监听成功，
`GETPWBYNAME` / `GETPWBYUID` / `GETGRBYNAME` / `GETGRBYGID` 四类请求及未命中分支
均返回正确应答。

**方案 2（回退）：声明平台豁免，不伪造通过**

若所有候选目录都不可 bind：

- 把端到端组标记为 **SKIP**（**不计入 PASS**），在 `test_package/MANIFEST.yml` 的
  `platform_exemptions` 中声明，附实测命令与输出；
- 同时**仍要断言**被测进程已越过配置解析与依赖加载，仅因 `bind()` 被安全策略拒绝而退出
  （用退出码 + 错误文本判别），避免平台豁免掩盖真实的解析/加载缺陷。

## 禁止做法

❌ **为绕开限制把协议从 AF_UNIX 改成 AF_INET。**

理由：NSCD 的协议契约就是"musl libc 客户端连接 AF_UNIX socket"，改传输层会让包
"测试通过但对消费者不可用"，属伪通过。

❌ 把端到端测试删掉、只留 `--version` 冒烟——违反 R34 / L1e。

## 关键词

AF_UNIX, unix domain socket, bind, EPERM, Operation not permitted, hmmac, SELinux,
/data/storage/el2/base, 应用沙箱, daemon smoke test, nscd, socketpair, 平台豁免
