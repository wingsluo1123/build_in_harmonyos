# DRAFT-hmdfs-tarball-symlink-headers-mirror：上游 tarball 内符号链接头文件在 HMDFS 解包为空目录，源码 `#include <dir/header.h>` 面断裂——source() 内镜像为真实文件

> Source: genometools 1.6.2 适配（真机 r3；ltrsift 1.0.2 为下游受益者）
> 对应 KV: knowledge/drafts/DRAFT-hmdfs-tarball-symlink-headers-mirror.kv

## 一句话

上游源码 tarball 内部用**符号链接**组织头文件目录（如 genometools 的
`src/external/samtools-0.1.18/samtools/* → ../<header>`）。HMDFS 不支持
symlink，conan 解包后该目录**静默变空**，编译到 `#include <samtools/sam.h>`
才报 `fatal error: ... file not found`——报错点距离根因（解包丢链接）很远。

## 使用说明（可复制）

配方 `source()` 在 `get()` 之后做幂等镜像（目标目录存在且首个哨兵头已在 → 跳过）：

```python
def source(self):
    get(self, url=..., sha256=..., strip_root=True)
    st_dir = os.path.join(self.source_folder, "src", "external", "samtools-0.1.18")
    sam_dir = os.path.join(st_dir, "samtools")
    if not os.path.isfile(os.path.join(sam_dir, "sam.h")):
        os.makedirs(sam_dir, exist_ok=True)
        for name in os.listdir(st_dir):
            if name.endswith(".h"):
                shutil.copy2(os.path.join(st_dir, name), os.path.join(sam_dir, name))
```

**判定技巧**：Windows 上解包同一 tarball，如果报 `Can't create '.../<name>':
Invalid argument` 且 `<name>` 与同目录某子目录同名——那基本就是符号链接，
Linux/HMDFS 解包行为见下表。

| 解包环境 | 符号链接结果 | 症状 |
|---|---|---|
| Linux / 真机 ext4 | 正常链接 | 无 |
| 设备 HMDFS（/storage） | **创建失败、静默跳过** → 空目录 | 编译期 `file not found`（远隔千里） |
| Windows 本地审计 | `Invalid argument` 硬报错 | 误以为 tarball 损坏 |

## 适用范围

- 任何在 HMDFS（/storage）上经 conan `get()`/tar 解包的、源码树内含符号链接
  的上游 tarball（vendored 第三方目录最爱用这种手法组织头文件别名）。
- 不适用：真机 ext4 分区解包（链接正常）；包 `package()` 阶段自己造的符号
  链接（那是另一类问题，用"退化实体副本"处理，见 lrslib/E625 语境）。

## 输入 / 输出

- 输入：tarball 内符号链接目录路径 + 其链接目标集合。
- 输出：同路径下的真实文件镜像；重跑幂等。

## 实证（2026-10-04，genometools/1.6.2 真机 r3→r4）

- r3：`src/extended/rcr.c:52: fatal error: 'samtools/sam.h' file not found`；
  设备上 `ls samtools-0.1.18/samtools/` → 空目录（`drwxr-s--x 2`）。
- 镜像修复后 r4 该错误消失（进入下一类失败：lld 重复符号）。
- 同 tarball 的 `lpeg-0.10.2/lua-lpeg.h` 亦为链接文件（Windows 同报 Invalid
  argument），conan 解包在设备上落地为真实文件，未再报错——即部分链接
  conan 能落盘、部分不行，**不能假设解包器行为一致**，一律按"哨兵文件存在
  才跳过"的幂等镜像最稳。
