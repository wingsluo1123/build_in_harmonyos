# pd-vbap

Pure Data 的 **VBAP（Vector Base Amplitude Panning，矢量基幅度声像）** 外部对象集，
上游源自 Ville Pulkki 1999–2006 的 VBAP 实现（HCS 移植为 Pd 外部）。

提供三个 Pd 对象：

| 对象 | 说明 |
|------|------|
| `vbap` | 矢量基幅度声像器：按扬声器布局把单声道声源定位到任意方位/仰角 |
| `rvbap` | 不定向声源（"reverberant"/无指向）的增益分布 |
| `define_loudspeakers` | 扬声器布局定义，输出 `ls-directions` / `ls-triplets` 矩阵 |

## 版本索引

| 版本 | 状态 | 构建系统 | 补丁 | 说明 |
|------|------|----------|------|------|
| [1.2.1](1.2.1/) | published | Makefile (pd-lib-builder 0.6.0) | 0 | 首个 OHOS 适配版本 |

## 依赖

| 依赖 | 用途 |
|------|------|
| `puredata/0.54.1` | **编译期头集**（Pd 内部头 `s_stuff.h` / `m_pd.h` / `g_canvas.h` … 位于其 `include/pd`） |
| `libpd/0.16.1` | **仅 test_package**：提供 Pd 引擎作为外部对象的插件宿主 |

## OHOS 适配要点

- 上游随源码 vendored `Makefile.pdlibbuilder`（pd-lib-builder 0.6.0）。它在 OHOS 上会**在编译任何东西之前硬失败**：

  ```
  Makefile.pdlibbuilder:764: *** Command "cc -dumpmachine" did not return a target triplet
  ```

  根因是它默认 `CC = $(PLATFORM)-cc`（`Makefile.pdlibbuilder:388/392`），而 OHOS 只带
  `clang`，没有 `cc`/`gcc`。
- 配方因此**显式注入编译器**（取自 `tools.build:compiler_executables`，R33：不依赖只在
  开发者会话里存在的 `${CC}`），并把 `PDINCLUDEDIR` 指向 **`puredata` 包的 `include/pd`** ——
  `libpd` 包只装 `include/libpd`，**不含 `s_stuff.h`**，无法用于编译外部对象。
- **零补丁**：不改上游任何源文件。
- 产物 `.pd_linux` 是 Pd 运行时 `dlopen` 的插件，**不是可链接库** → `cpp_info.libs` 为空，
  插件目录经 `cpp_info.libdirs=["lib/pd-externals"]` 暴露。
- OHOS 目标机 `/tmp` 只读：clang 需显式 `TMPDIR`。

## 产物布局

```
lib/pd-externals/{vbap,rvbap,define_loudspeakers}.pd_linux   # 插件（Pd 宿主 dlopen）
share/pd-vbap/                                               # help 补丁、examples/、unittests/
licenses/LICENSE.txt
```

产物仅依赖 `libc.so`，`RUNPATH=$ORIGIN`（自包含）。

## 相关技能

本库属于 **pd-lib-builder 外部库** 一族（zexy / iemlib / cyclone / iemnet …），
通用适配方法（检测 → `CC` + `PDINCLUDEDIR` 注入 → `libpd` 消费者测试）已沉淀为：
[`knowledge/operations/pd-externals-ohos/`](../../../knowledge/operations/pd-externals-ohos/)。
