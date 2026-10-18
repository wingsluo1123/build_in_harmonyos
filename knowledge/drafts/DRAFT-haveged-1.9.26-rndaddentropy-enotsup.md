# DRAFT-haveged-1.9.26: OHOS `/dev/random` 拒绝 `RNDADDENTROPY`

## 症状和最小复现

HarmonyOS PC aarch64 上，`O_RDWR|O_NONBLOCK` 打开 `/dev/random` 后，`RNDGETENTCNT` 成功；调用零熵、零长度的 `RNDADDENTROPY` 返回 `ENOTSUP (errno 95)`。同一进程读取的熵计数前后均为 4038。最小探针只写零请求，避免向内核声明未经验证的熵：

```python
import array, fcntl, os, struct
fd = os.open('/dev/random', os.O_RDWR | os.O_NONBLOCK)
def count():
    value = array.array('i', [0])
    fcntl.ioctl(fd, 0x80045200, value, True)  # RNDGETENTCNT
    return value[0]
print('before', count())
try:
    fcntl.ioctl(fd, 0x40085203, struct.pack('ii', 0, 0))  # RNDADDENTROPY
except OSError as exc:
    print('ADD errno', exc.errno)
print('after', count())
os.close(fd)
```

实测输出：`before 4038`、`ADD errno 95`、`after 4038`。`RNDGETENTCNT` 可用不意味着 `RNDADDENTROPY` 可用；编译通过和随机字节生成通过也不能证明内核熵注入可用。

## 方案和验证

在 haveged 1.9.26 的 OHOS 构建中使用 `--disable-daemon`，只交付文件/流生成命令和 `libhavege`。上游 `make check` 的 1 个 `entest` 图像自测及 10 个 16 MiB 数据流测试通过；从 Conan 包链接库的消费者测试 1/1 通过。没有尝试把用户空间生成的字节记入内核熵池。

其他需要 `RNDADDENTROPY` 的软件先用零请求探测，再决定是否启用注入服务。若业务必须注入，需另找已文档化的设备接口或取得相应平台能力并重新实测；文件生成器不能代替内核熵池服务。本结论只覆盖本次 HarmonyOS PC 设备及当前权限。

## 查重和新增点

已检索 `knowledge/graph`、`knowledge/doc`、`knowledge/drafts` 与 `knowledge/draft` 中的 `RNDADDENTROPY`、`RNDGETENTCNT`、`ioctl`、`ENOTSUP`、`entropy`、`/dev/random` 及 `haveged`：`RNDADDENTROPY` 与 `RNDGETENTCNT` 在本条之前**零命中**。同族条目按 hit 四条件逐条核否：

- **E235（OpenSSL `--with-rand-seed=getrandom`）**：症状是 `__fd_chk` 未导出符号导致的链接失败，解法是改 OpenSSL 的 configure 熵源选择；针对的是**编译/链接期**符号可用性，不涉及运行期 ioctl 能力。症状与解法均不同，未覆盖「读可用、写 `ENOTSUP`」。
- **E014（`getrandom`/`syslog` undefined reference）**：同为链接期符号缺失，不同签名、不同解法。
- **E400（Node JITless/WASM 能力边界 + 跨 UID 包缓存消费者校验）**：同属「运行期能力边界」家族，但症状为 `Signal 5` / `Check failed.*__errno_location` / `WebAssembly.*undefined` / `exit 126`，解法是 V8 `--jitless` 与包缓存权限矩阵；探针对象是 V8 优化开关与文件权限，**不是内核设备 ioctl**，也未给出同一接口读/写能力分裂的区分法。
- **E556（ptrace 被系统策略整体禁用 → 适配前能力判定与可用子集）**：与本案**同构**（都是「先探针、再按能力面收窄交付」），但症状为 `PTRACE_ATTACH`/`PTRACE_TRACEME` = `EPERM`、`PR_SET_PTRACER` = `EINVAL`，解法是 ptrace 能力探针与「非 ptrace 子集」盘点；errno 族（`EPERM`/`EINVAL`）、探针入口（ptrace 系调用 vs `RNDADDENTROPY` ioctl）与收窄对象（工具子命令 vs 注入守护进程 + 库 API）均不同。按 hit 条件 2「解法未被既有条目覆盖 ⇒ 不算 hit，按 `create` 报」与「组合型知识不判重」，E556 只覆盖**模式**、未覆盖本条**具体机制**。
- **E523（`ENOTSUP` 关键字命中）**：实为 Go 链接器 `fallocate` 在 HMDFS 上返回 `EACCES`，与熵设备无关。签名、根因、解法全不同。

**组分清单 + 新增解题路径**：本条 = ①「运行期能力边界先探针、后收窄」模式（E400/E556 族已有的**通用模式**）+ ②**零熵零长度 `RNDADDENTROPY` 探针法**（新增：以不向内核声明任何熵的代价探明写注入可用性，避免用「编译通过」或「随机字节生成通过」冒充内核熵池可用）+ ③**同一设备接口内的读/写能力分裂判据**（新增：`RNDGETENTCNT` 成功 ≠ `RNDADDENTROPY` 可用，熵计数 4038→4038 作对照）+ ④**构建期隔离决策**（新增：`--disable-daemon`，只交付文件/流生成器与 `libhavege`，并如实声明内核注入不支持）。组合后的新增解题路径是：**对任何「用户空间向内核注册/注入资源」的设备接口，先用零副作用请求探测写方向能力面，再决定该功能是否进入交付面**——既有条目或只讲编译期符号（E235/E014），或只讲整族能力被禁后如何盘点子集（E556），没有一条给出「读写分裂」的区分法与零副作用写探针范式。
