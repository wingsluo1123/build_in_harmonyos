# E2296 — 依赖包相对 `DT_NEEDED` 使消费方按 cwd 解析失败

## 现象

musl（OHOS 实测原文）：

```
Error loading shared library ../../bin/libKF6ConfigCore.so:
  (needed by /…/.conan2/p/kconf7325dff05dfef/p/lib/libKF6ConfigGui.so)
```

glibc 措辞：

```
error while loading shared libraries: ../../bin/libKF6ConfigCore.so:
  cannot open shared object file: No such file or directory
```

```
Cannot load library .../lib/kf6/kfilemetadata_taglibextractor.so:
  (libKF6ConfigGui.so: cannot open shared object file: No such file or directory)
```

判别要点：报错的库名**带目录分隔符**。裸名 `libfoo.so` 找不到属 rpath/依赖缺失，不是本条。

## 根因

依赖包的共享库链接时**没有写 SONAME**（或链接时直接给的是路径），链接器就把当时的路径字符串写进了
`DT_NEEDED`：

- 相对形态：`../../bin/libKF6ConfigCore.so`
- 绝对形态：`/…/.cache/conan2/p/<pkg-id>/p/lib/libKF6CoreAddons.so`

OHOS 的 musl loader 对**含 `/` 的 `DT_NEEDED` 按进程工作目录逐字解析**，既不查
`LD_LIBRARY_PATH`，也不走 rpath。于是同一份二进制：在构建目录跑报错、换个目录跑也报错，
只有把软链铺到"相对路径恰好指向的位置"才能加载。

## 适用范围

| 情况 | 适用性 |
|---|---|
| 依赖包 `DT_NEEDED` 含 `../` | 适用，镜像相对路径 |
| 依赖包 `DT_NEEDED` 含绝对路径 | 适用，镜像绝对路径（要求可写） |
| 自身产物缺 SONAME | 同机制，见 E1174 |
| 裸名库找不到 | 不适用（rpath/依赖缺失） |

实测（2026-10-18，ohpcd 制品仓 KF6 6.14 段 14 个包）：39 条路径型 `DT_NEEDED`，
34 条绝对缓存路径 + 5 条 `../../bin/` 相对路径；仓库内 162 个配方各自手写同一份兼容层。

## 处理策略

1. **祖先 `bin/` 镜像（推荐）**：`knowledge/tools/kf6-relative-needed/apply-compat-shim.py`
   —— 扫描依赖包 → 计算"运行目录 + NEEDED"解析出的目标路径 → 在各级祖先生成软链。
   配方内实现见 `archives/b/baloo-widgets/26.04.0/conanfile.py::_make_compat_mirrors()`
   （`kb_compat_shim=False` 可关闭，用于复现原始报错）。
2. **依赖包补 SONAME 重新发布（根治）**：`-Wl,-soname,libX.so`，属上游包动作。
   镜像层只是运行时补丁，依赖包下次发布不修则问题仍在。

两种策略都不改源码，也不需要 `__OHOS__` 平台宏。

**禁止项（实测反证）**：不要用任何构建后手段改写产物 `.dynstr`（`patchelf --replace-needed`、
`dd`、Python 就地改）把路径换成裸名。`readelf` 看着干净，但文件在本平台**无法再被加载**：
同一份 `.so` 原样 `dlopen` 只报缺 `LD_LIBRARY_PATH`，改写后直接 `Permission denied`
（OHOS/HMDFS 拒绝为构建后被改写的 ELF 做 `mmap(PROT_EXEC)`，见 E537）。
动机「CI L5b 会判负」也不成立：`build_and_test.sh` 的 L5b 只打印 `[fail]` 并写入
ci-metadata.json，`L5_RESULT` 不进 `FAILED` 计数（致命项是 L0/KC/JC/conan create/L1），
已合入的 KF6 包（kbookmarks 6.28.0 等）同样带绝对 `DT_NEEDED`。

## 验证

```bash
# 识别
python3 knowledge/tools/kf6-relative-needed/detect-relative-needed.py \
    --pkg-root "$PKG" --runtime-dir "$BUILD/autotests"

# 处理
python3 knowledge/tools/kf6-relative-needed/apply-compat-shim.py \
    --pkg-root "$PKG" --runtime-dir "$BUILD/autotests" --apply

# 样例库端到端（关闭/开启 SKILL 对比，无管道、日志落盘）
knowledge/tools/kf6-relative-needed/reproduce.sh off
knowledge/tools/kf6-relative-needed/reproduce.sh on
```

## 关联

- E1174 — OHOS 工具链默认不写 SONAME（自身产物侧，同一机制）
- E1820 — libjpeg-turbo 斜杠相对 NEEDED 用父目录软链解决（同一手法早期实践）
- E2080 — KF6 `ki18n_install(po)` 安装期约束（同属 KF6 基线能力缺口，不同问题）
