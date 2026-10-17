# DRAFT-14488-ohos-elf-codesign-integrity

> Draft（待审核 promote）｜对应: `knowledge/drafts/DRAFT-14488-ohos-elf-codesign-integrity.kv`
> 说明：该 kv 为文档式条目，本文档为其可读镜像。

---

# DRAFT-14488: OHOS ELF `.codesign` 完整性校验 —— 构建产物「能编译但不能执行」的判据与救援

- 条目主题：HarmonyOS PC 上 ELF 的 `.codesign` 自签名块是**可执行性的前置条件**；任何链接后修改（objcopy/strip）都会使其失效，表现为 `execve` 返回 EPERM（shell 报 `Operation not permitted`，退出码 126）。含平台 `ld.lld --code-sign` 在「大静态库链接」下写出不一致签名的实测证据与配方级救援方案。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联 PR：`archives/d/dynamorio/11.91.20676`（PR !14488，动态二进制插桩框架适配）

## 适用场景

OHOS 上构建出的可执行文件**编译链接全绿**，但一执行就失败：

```
$ ./bin64/drrun -version
bash: ./bin64/drrun: Operation not permitted        # 退出码 126，非 127/139
```

`file` 显示是合法 `ELF 64-bit LSB arm64`，`ldd`/`readelf -d` 正常，无缺库缺解释器。

## 判据（实测）

`.codesign` 段内偏移 `+0x10` 处 8 字节（小端）**必须等于文件大小**：

| 文件 | 文件大小 | `.codesign+0x10` | 可执行 |
|---|---|---|---|
| clang 直出的小程序 | 18752 | 18752 | ✅ |
| `drrun`（动态链接） | 6203904 | 6203904 | ✅ |
| 静态链 DR 的用例（未救援） | 9956448 | 15460992 | ❌ EPERM |

- 摘要（`.codesign+0x18` 起 32 字节）**带密钥**：sha256/sm3/sha1/sha384/sha512/sha3-256/blake2s × 8 种覆盖区间组合均无法复现 → **不可离线伪造**。
- 仅改长度字段无效（摘要不匹配）；`-Wl,--no-code-sign`（不产生签名）同样 EPERM → **签名是必需的**。

## 诊断步骤

```bash
# 1) 读判据（段偏移 → 长度字段 vs 文件大小）
readelf -SW <file> | grep codesign                     # 取段的 Off 列
python3 -c "import struct;d=open('<file>','rb').read();print(len(d),struct.unpack_from('<Q',d,<Off>+0x10)[0])"

# 2) 若不一致 → 重签（官方工具，无需私钥）
llvm-objcopy --remove-section=.codesign <file> /tmp/n.elf   # 工具拒绝已存在 .codesign 的文件
binary-sign-tool sign -selfSign 1 -inFile /tmp/n.elf -outFile /tmp/s.elf
rm -f <file> && cp /tmp/s.elf <file> && chmod 755 <file>    # 已签名文件不能原地覆盖：必须先 rm
```

## 根因

1. **链接后修改破坏签名**：DR 默认在链接后执行 `objcopy --only-keep-debug` + `--add-gnu-debuglink` + `strip` 分离调试信息 → 文件与 lld 签名时的内容不一致 → EPERM。规避：`-DSPLIT_SYMBOLS=OFF`（保持链接器输出原样）。
2. **平台 `ld.lld --code-sign` 在大静态库链接下写出不一致签名**（各包可复现）：链接 `libdynamorio_static.a` 时，记录长度**恒为 15460992**，与 app 无关。受控实验：逐项去掉 `-Xlinker --dependency-file` / `-rdynamic` / `-Wl,--as-needed` / `-Wl,-S` / `-Wl,--hash-style=both` **均无效**（建库大小 9956368~9956448 不变）。→ 疑似平台 lld 侧缺陷。

## 规避（配方级，已验证）

- 构建侧：`SPLIT_SYMBOLS=OFF`（或等价：禁止任何链接后 objcopy/strip）。
- 交付侧：**配方 `package()` 内建签名救援**（本库 `ohos_resign.py`：判据检测 → 去段 → `-selfSign 1` → 原子替换 → `chmod 755`），对包内全部 ELF 生效；非 OHOS 主机自动跳过（找不到工具即 no-op）。
- 实测批处理：`ok=751 / rescued=377 / failed=0`。

## 影响

- 仅影响**可执行性**，不影响编译/链接/静态分析；错误信息误导性强（"Operation not permitted" 易被误判为权限/沙箱问题）。
- 对 CI 的连带效应：test_package 若需运行包内工具，签名未救援则必然 126 失败。

## 已知边界

- 摘要算法/密钥不可得 → 只能「重新签名」不能「修补原签名」。
- `binary-sign-tool` 与 `llvm-objcopy` 均来自 OHOS SDK（`/data/service/hnp/bin/`）；非 OHOS 构建机的行为未定义（本方案自动跳过）。
