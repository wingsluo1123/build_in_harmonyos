# DRAFT — OHOS 上 Go 工具链自举三件事：签 SDK 全部 ELF、签名后必须 chmod 755、链接输出放非 hmdfs

> 拟提升编号：E558（最终编号由知识库主编确认）
> 来源：termsvg / termshot / termshark 三包适配（2026-10-13，鸿蒙 PC 真机）
> 参照已发布先例：`archives/a/addchain/0.4.0`（Go CLI）

## 错误特征

```
# 1) 下载的 Go 工具链无法执行
sh: /.../go-sdk/go1.26.0/go/bin/go: Permission denied

# 2) 签名之后仍然 Permission denied（执行位被重置）—— 与上面一字不差
$ ls -la .../bin/go
-rw-rw-r-- 1 ... 14226624 ... go      # 注意：没有 x 位

# 3) 链接阶段（hmdfs）
/data/.../pkg/tool/linux_arm64/link: mapping output file failed: permission denied

# 4) 上个构建残留导致
PermissionError: [Errno 13] Permission denied: '.../link-out/termsvg'
```

## 根因：四个连环坑

### 坑 1 — 未签名 ELF 无法 exec

OHOS 拒绝执行无 `.codesign` 段的 ELF。自举的 Go SDK 需要签三处：

- `bin/go`
- `bin/gofmt`
- `pkg/tool/linux_arm64/*`（asm / cgo / compile / cover / fix / link / vet …）

### 坑 2 — 签名会重置执行位（最关键，易误判）

`binary-sign-tool` 输出新文件并替换原文件后，**权限位回落为 644**，
exec 仍报 `Permission denied`——与「缺签名」的报错**完全相同**。

真机对比实验证实，可执行文件必须**同时**具备：

| 条件 | 可执行 |
|------|--------|
| 有 `.codesign` 段 | ❌ |
| 755 权限 | ❌ |
| 两者都有 | ✅ |

**极易误判**：看到 Permission denied 就以为签名没生效，反复重签。
**解法**：每个 ELF 签完立即 `chmod 755`。

### 坑 3 — 判断"是否已签名"不能用 grep

曾用 `grep -q '.codesign' <binary>` 判断是否跳过签名——正则里的 `.`
是**通配符**，会命中 Go 二进制内的普通字符串，导致 `go`、`fix`、`link`、`vet`
被误判为"已签名"而跳过，最终 `go: no such tool "vet"`。

正确做法：读真实 ELF 段。

```bash
llvm-readelf -S "$bin" 2>/dev/null | grep -q '\.codesign'
```

### 坑 4 — hmdfs 与残留产物

- **Go linker mmap 输出文件**：hmdfs 不支持 → `mapping output file failed`。
  链接目标必须放非 hmdfs 路径（`/data/storage/el2/base/haps/entry/files/...`）。
- **stale 产物**：上一个（可能他人 uid）构建留在 `link-out` 的产物，会让
  `shutil.move` / `chmod` 抛 `PermissionError [Errno 13]`——表象与签名问题
  完全无关，误导排查方向。构建前先清理。

## 解决方案

```python
def _sign_go_sdk_if_ohos(self, goroot):
    tool_dir = os.path.join(goroot, "pkg", "tool", f"linux_{self._go_host_arch()}")
    candidates = [os.path.join(goroot, "bin", "go"),
                  os.path.join(goroot, "bin", "gofmt")]
    if os.path.isdir(tool_dir):
        candidates.extend(os.path.join(tool_dir, f) for f in os.listdir(tool_dir))
    for candidate in candidates:
        if os.path.isfile(candidate) and self._is_elf(candidate):
            self._sign_elf_if_ohos(candidate)
            try:
                os.chmod(candidate, 0o755)   # ⭐ 签名重置执行位，必须补回
            except OSError:
                pass                          # 可能属其他 uid，非致命

@staticmethod
def _has_ohos_signature(path):
    # 必须读真实 ELF 段，不能 grep 文件内容（`.` 是通配符）
    proc = subprocess.run(["/data/service/hnp/bin/llvm-readelf", "-S", path],
                          capture_output=True, timeout=30)
    return b".codesign" in proc.stdout
```

构建环境要点：

```bash
CGO_ENABLED=0            # 纯静态，规避 fork/exec 权限问题
GOOS=linux GOARCH=arm64  # OHOS 映射为 linux
GOTOOLCHAIN=local         # 禁止 go 自行下载另一套未签名工具链
GOPROXY=https://goproxy.cn,direct   # GitHub 直连不稳定
```

## 验证

```bash
# 1. 签名字段与权限同时确认
llvm-readelf -S <goroot>/bin/go | grep codesign
ls -la <goroot>/bin/go          # 必须是 -rwxr-xr-x

# 2. 工具链可用
go version                       # go version go1.26.0 linux/arm64

# 3. 真机实测（termsvg）
         termsvg --version   → termsvg v0.11.0
         termsvg export 1.cast -o out.svg → 2.4MB 动效 SVG 成功
```

三包（termsvg / termshot / termshark）均以此模式构建并
`conan create` 通过，消费者测试全 PASS。

## 推广价值

覆盖所有 Go 包在 OHOS 上的适配，以及**任何需要在设备上自举并执行第三方
工具链**的场景（zig、rust 等同样需要签名 + 执行位修复）。
「报错表象相同但根因不同」这一特征（缺签名 vs 缺执行位）是最值得沉淀的
排查经验。
