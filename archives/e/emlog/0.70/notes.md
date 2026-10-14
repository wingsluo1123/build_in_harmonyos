# emlog 0.70 适配笔记

## 软件是什么
emlog 是一个 Linux 内核模块（字符设备驱动），提供有限容量的环形缓冲日志设备；
附带两个用户态工具：
- nbcat：非阻塞读取 emlog 设备当前内容（对普通文件/FIFO 同样适用）
- mkemlog：创建 emlog 设备节点（依赖内核模块已加载）

上游：https://github.com/nicupavel/emlog（tag emlog-0.70）

## OHOS 适配要点
1. **内核模块不可构建**：emlog.c 依赖 `<linux/*>` 内核头与 KDIR 内核构建树，
   OHOS 用户态工具链不存在，无法构建 emlog.ko。属真实平台阻塞，不尝试。
2. **用户态工具可构建**：nbcat.c 仅依赖标准 POSIX 头，直接通过；mkemlog.c
   依赖 GNU `<error.h>`（OHOS musl sysroot 缺失），补丁提供最小等价实现
   （fprintf+exit，保持原错误语义）。
3. **Makefile 目标拆分**：`make nbcat` / `make mkemlog` 单独构建，不触发
   `modules` 目标（需要内核构建树）。
4. **CLI 交付**：产出两个可执行文件 → 软件级 commands.json（R38）。

## 构建步骤（OHOS aarch64, clang 15）
```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```
配方取 Conan profile 的 `tools.build:compiler_executables:c`（R33），
`CFLAGS=-Wall -O2 -D__OHOS__`。

## 运行说明
- nbcat 可在 OHOS 上直接对普通文件运行（非阻塞读，输出当前内容）。
- mkemlog 需要 `/dev/emlog` 字符设备与已加载的内核模块，OHOS 用户态无法运行
  （保留编译产物，运行属内核模块依赖）。
---

**编译结束**: 2026-09-26 02:35
**最终状态**: built
