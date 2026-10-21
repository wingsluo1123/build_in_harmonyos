# 处理策略详解：路径型 `DT_NEEDED` 的三个可选动作

> 三条策略互斥可选，也可组合（S1 兜底 + S3 根治并存）。统一判据：**消费方的工作目录未知**
> → 任何"按工作目录解析"的 `NEEDED` 都必须被消除或镜像。

## 判定输入

```bash
# 列出某依赖包内所有路径型 NEEDED（含绝对缓存路径与 ../ 相对路径）
python3 detect-relative-needed.py --pkg-root "$PKG" --json
```

输出三类，处置不同：

| 类别 | 形如 | 处置 |
|------|------|------|
| `RELATIVE` | `../../bin/libKF6ConfigCore.so` | S1（祖先 bin/ 镜像）优先 |
| `ABS-CACHE` | `/…/.conan2/p/b/kconf….cache/…/lib/libKF6ConfigGui.so` | S2（绝对路径镜像）；换机失效则 S3 |
| `ABS-OTHER` | 发布机其余绝对路径 | 先确认是否残留调试路径，再 S2 |

裸名 `libX.so`（无 `/`）**不在本策略范围** —— 那是 rpath/`LD_LIBRARY_PATH`/依赖缺失问题。

## S1 — 祖先 `bin/` 镜像（样例库采用，推荐）

原理：musl/glibc 对带 `/` 的 `NEEDED` **按进程工作目录逐字解析**。若在运行目录每一级祖先
都放一份 `bin/libKF6ConfigCore.so`，则 `../../bin/x.so` 恰好命中。

```bash
python3 apply-compat-shim.py --pkg-root "$PKG" --runtime-dir "$BUILD/autotests" --apply
```

配方内等价实现（样例库 `archives/b/baloo-widgets/26.04.0/conanfile.py::_make_compat_mirrors`）：

```python
def _make_compat_mirrors(self):
    """Mirror dependency libraries into <ancestor>/bin for relative NEEDED."""
    dep_libs = {}
    for dep in self.dependencies.values():                 # 镜像的是【依赖包】的 lib
        libdir = os.path.join(dep.package_folder or "", "lib")
        if not dep.package_folder or not os.path.isdir(libdir):
            continue
        for name in sorted(os.listdir(libdir)):
            if ".so" in name:
                dep_libs.setdefault(name, os.path.join(libdir, name))
    probe = os.path.abspath(self.build_folder)
    for _ in range(4):                                     # 与 lib/plugins 深度对齐
        probe = os.path.dirname(probe)
        compat = os.path.join(probe, "bin")
        try:
            os.makedirs(compat, exist_ok=True)
        except OSError:                                    # HMDFS 上偶发 EACCES/EEXIST
            continue
        for name, target in dep_libs.items():
            link = os.path.join(compat, name)
            if os.path.lexists(link):                      # 幂等：已存在就跳过
                continue
            try:
                os.symlink(target, link)                   # 绝对目标，不依赖 cwd
            except OSError:
                pass
```

要点：
- 镜像的是**依赖包**的 `lib/*.so*`（相对条目要找的是依赖，不是本包）；
- 开关 `kb_compat_shim` 在 `_run_tests()` 里判（`False` 时刻意不建镜像，用于复现原始报错），
  函数本身不做开关判断——复现开关与建链逻辑分离；
- 镜像建在 `build_folder` 的**各级祖先**（R49 私有目录），不触碰 `/usr/local` 等共享前缀（PF6 合规）；
- HMDFS 上 `ln -sf` 覆盖无效（R5）→ 先判 `lexists` 再建，或先 `os.remove`。

## S2 — 绝对路径镜像

当 `NEEDED` 是发布机的绝对缓存路径时，S1 无效（相对形态对不上）。做法相同，只是镜像目标
换成绝对路径本身：

```bash
python3 apply-compat-shim.py --pkg-root "$PKG" --runtime-dir "$BUILD/autotests" \
        --apply
```

限制：仅在**同一台机器**（发布机/共享缓存可用）成立；CI 干净环境或换机会直接失效 →
此时必须上 S3。因为不可移植，只作临时逃生口。

## S3 — 依赖包补 SONAME 重发布（根治）

在依赖包配方 `generate()`/工具链里补链接标志，让 `NEEDED` 只留裸名：

```python
self.conf_info.define("tools.build:cxxflags", ["-Wl,-soname,libKF6ConfigCore.so"])
# 或 cmake 工程内 set_target_properties(... PROPERTIES SONAME libKF6ConfigCore.so)
```

验证：`readelf -d libX.so | grep NEEDED` 全为裸名 → 消费方无需任何镜像即通过。

治理建议：这是**依赖包侧**的修复，需要重发（版本后缀 `X.Y.Z.N`，R37）。批量治理时按
本包 `detect-relative-needed.py` 的输出清单逐个补 SONAME，可一次性消灭整类问题
（当前语料：14 个 KF6 包 / 39 条路径型 NEEDED）。

## 反例（实测，禁止）：在适配方产物上就地改写 `.dynstr`

依赖缺 SONAME 时，链接器会把 dep 的**路径**写进消费方产物的 `DT_NEEDED`
（`/…/.conan2/p/<dep>/p/lib/libKF6WidgetsAddons.so`）。直觉解法是 `package()` 里把该字符串
改写成裸名——`readelf` 会显示干净，但产物在本平台**从此无法加载**：

```
# 同一份 .so，一份原样、一份把绝对 NEEDED 改写成裸名，各自 ctypes.CDLL：
原样 → Error loading shared library libKF6KIOCore.so: (needed by …)   # 只是缺 LD_LIBRARY_PATH
改写 → Error loading shared library …/libt.so: Permission denied      # 文件本身加载不了
```

机制与 E537 记载一致（OHOS/HMDFS 对构建后被改写的 ELF 拒绝 `mmap(PROT_EXEC)`），因此：

- ❌ 不要用 `patchelf --replace-needed`、`dd`/Python 改 `.dynstr`、`objcopy` 等构建后手段；
- ❌ 不要以「L5b 会判负」为动机做这件事——`ci/conan/build_and_test.sh` 的 L5b 只打印
  `[fail]` 并写入 ci-metadata.json，`L5_RESULT` 不进 `FAILED` 计数（致命项为 L0/KC/JC/
  conan create/L1），CI 不会因此失败；
- ✅ 正确落点：S3（依赖侧补 SONAME 重发布）或 E537 的 link-time 修法
  （给依赖目标补 `IMPORTED_SONAME`、清 `IMPORTED_NO_SONAME`，让 ld 记 `-l:libX.so`）。

## 组合建议

| 场景 | 组合 |
|------|------|
| 上游依赖短期不会重发（常见） | S1（样例库配置），并在 notes.md 登记 S3 待办 |
| 依赖可重发且团队具备发版权限 | S3 根治，S1 仅作灰度期兜底 |
| 换机后 S1 失效（绝对形态） | S2 临时恢复 + 立即推进 S3 |

## 关闭开关（用于复现对照）

样例库配方提供 `kb_compat_shim` 选项，默认 `True`；关掉即回到问题原始状态：

```bash
# 关闭：应复现 loader 报错（CI/复现脚本用）
conan create archives/b/baloo-widgets/26.04.0 -o "baloo-widgets/*:kb_compat_shim=False" \
      -pr:b=ci/conan/profiles/ohos-aarch64 -pr:h=ci/conan/profiles/ohos-aarch64
```

`reproduce.sh off|on` 已封装该对照，日志分别落到 `~/tmp/kf6-relneeded-off.log` / `-on.log`。
