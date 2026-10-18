# ktx 1.45 — KTX (Kombat Teams eXtreme), QuakeWorld 服务器扩展 mod

> 本文件是 **版本级** 说明。软件级目录 `archives/k/ktx/` 下同时存在另一个上游
> （KhronosGroup/KTX-Software，版本 4.3.2），两者只有名字相同，详见 ../README.md。

# ktx — KTX (Kombat Teams eXtreme), a QuakeWorld server modification

Upstream: https://github.com/QW-Group/ktx (QW-Group)

KTX 是一个 QuakeWorld 服务器扩展 mod，为 QuakeWorld 服务器（推荐 MVDSV，
FTEQW 可能可用）增加大量比赛相关功能。它**不是独立可执行程序**，而是编译成
原生共享库 `qwprogs.so`，由服务器 `dlopen()` 加载后调用 `dllEntry()` 完成握手。

- 交付形态：共享库（本仓库按库包适配，不含 `commands.json`）
- 语言：C99（仅标准 C 头 + libm）
- 构建系统：CMake ≥ 3.9
- 许可：GPL-2.0-or-later

## 版本索引

| 版本 | Conan 配方 | 状态 | 适配目标 |
|------|-----------|------|----------|
| 1.45 | `archives/k/ktx/1.45/` | 已适配 | HarmonyOS PC（OHOS aarch64，clang 15） |

## 消费方式

```python
# conanfile.py
def requirements(self):
    self.requires("ktx/1.45")

def build(self):
    # CMakeDeps 会生成 ktx::ktx 目标；注意产物没有 lib 前缀
    ...
```

产物布局：

```
lib/qwprogs.so           # 模块本体，SONAME=qwprogs.so（与文件名一致），唯一 NEEDED 是 libc.so(musl)
include/ktx/*.h          # mod ABI 头文件（dllEntry / vmMain 与 QuakeWorld 共享结构）
licenses/LICENSE.md      # GPL-2.0-or-later
```

`lib/qwprogs.so` 的导出符号面被上游 `C_VISIBILITY_PRESET hidden` 限制为
`dllEntry`、`vmMain`（外加链接器生成的 `_init`/`_fini`）。若要把它加载进
QuakeWorld 服务器，请把该 `.so` 放到服务器 mod 目录。