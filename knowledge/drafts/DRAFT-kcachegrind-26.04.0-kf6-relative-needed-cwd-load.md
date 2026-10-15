# DRAFT：KF6 依赖库的坏 `DT_NEEDED` 导致消费包 test_package 在 CI 加载失败（本机却通过）

- **来源**：kcachegrind 26.04.0 适配，远端 CI 构建 #92573（2026-10-15，worker CI-021，26/31 断言）
- **严重度**：2（测试期完全无法运行交付物；有确定性、已被仓内先例验证的修法）
- **分类**：qt6, kf6, runtime, linking, portability

## 现象

CI 跑到 `test_package` 时报：

```
Error loading shared library ../../bin/libKF6ConfigCore.so
  : (needed by /storage/.../.cache/conan2/p/kconfa2f42dbf978cc/p/lib/libKF6ConfigGui.so)
Error loading shared library ../../bin/libKF6IconThemes.so
  : (needed by /storage/.../.cache/conan2/p/kiconab5293a5fefdc/p/lib/libKF6IconWidgets.so)
[FAIL] kcachegrind --version exit 0
== 26/31 checks passed ==
```

**同一份配方在本开发机 `conan create` 为 31/31 全过。**

## 根因

两类坏 `DT_NEEDED` 同时在 KF6 生态里存在：

1. **相对形式** `../../bin/<lib>.so`
   动态加载器对**含 `/` 的名字**不查 `DT_RPATH`/`DT_RUNPATH`/`LD_LIBRARY_PATH`，
   而是把它当成**相对进程 CWD** 的路径直接 `open(2)`。所以「把依赖 lib 目录加进
   `LD_LIBRARY_PATH`」这类修法对它**完全无效**。
2. **绝对形式** `<某机器的 conan home>/p/<pkg>/p/lib/<lib>.so`
   指向构建方的缓存布局，跨机器/跨 cache home 即失效（本仓 E537 族）。

**为什么本地掩盖了缺陷**：Conan 只按 `package_id` 索引二进制，**不校验同名
`package_id` 的字节一致性**。CI worker 的持久缓存里，`kconfigwidgets`/`kiconthemes`
等是**上游配方在该 worker 上本地重建**出来的副本（链接行使用相对路径 ⇒ intra-package
的 NEEDED 记成 `../../bin/<lib>.so`）；而开发机 `~/.cache/conan2` 恰好存在、副本来自
发布方构建（绝对路径且路径真实存在）。本机 `readelf` 对照可见同一 package_id 的两份
字节 NEEDED 完全不同。

## 修法（仓内已合并先例：kteatime / ktimer 26.04.0）

在**消费方** `test_package/conanfile.py` 里重建解析路径：

1. 从任一依赖的 `package_folder` 反推 conan cache home：
   `cache_home = dirname(dirname(dirname(dep.package_folder)))`
   （对 `~/.conan2/p/<h>/p` 与 CI 的 `~/.cache/conan2/p/<h>/p` 两种布局都成立）；
2. 把所有依赖 `lib/*.so` 复制到 `cache_home/bin`（follow symlink、落地为真实文件；
   顺手把源缓存里的 symlink `.so` 原地实体化 —— HMDFS 加载器对 symlink `.so` 不稳定）；
3. 绝对形式兜底：确保 `<dirname(dirname(cache_home))>/.conan2 -> cache_home` 软链存在；
4. 测试进程 **CWD 设为 `cache_home/recon/<pkg>`** ⇒ `../../bin/<lib>.so` 命中
   `cache_home/bin/<lib>.so`；测试脚本内部**不得**再覆盖 CWD（例如别把被测程序
   `cwd=` 到 TMPDIR，这一步最容易把修好的路径又破坏掉）；
5. 若出现的相对前缀不是 `../../bin`（历史上有 `../../../bin/`），按前缀深度在对应层级
   补一个 bin 目录即可 —— 加载器报错里的相对路径就是深度证据。

## 机制自证（无需 CI 即可复现）

```bash
R="${TMPDIR:-/data/storage/el2/base/cache}/relneeded"; mkdir -p $R/bin $R/recon/kcg $R/other
printf 'int a(void){return 1;}\n' > $R/bin/a.c
(cd $R/bin && /data/service/hnp/bin/clang -shared -fPIC -o libA.so a.c)          # 无 SONAME
printf 'extern int a(void); int b(void){return a();}\n' > $R/recon/kcg/b.c
(cd $R/recon/kcg && /data/service/hnp/bin/clang -shared -fPIC -o libB.so b.c ../../bin/libA.so)
readelf -d $R/recon/kcg/libB.so | grep NEEDED     # → [../../bin/libA.so]
cd $R/other    && python3 -c "import ctypes;ctypes.CDLL('$R/recon/kcg/libB.so')"  # FAIL：同款报错
cd $R/recon/kcg && python3 -c "import ctypes;ctypes.CDLL('$R/recon/kcg/libB.so')"  # LOADED OK
```

本机实测输出：

```
OSError: Error loading shared library ../../bin/libA.so: (needed by …/recon/kcg/libB.so)
LOADED OK
```

## 边界

- 只重建**测试期**的解析路径，**不修改被测包产物**；产物内部的坏 NEEDED 属上游生态
  问题，应另按 E537 记录（或在链接期用 `-Wl,-soname`/代理副本解决）。
- 复制 `.so` 与原地实体化 symlink 会写 conan 缓存：CI 缓存是一次性工作区可接受；
  本地运行会动到共享缓存，需知悉（多会话共享 `~/.conan2` 时注意）。
- 不要把 CWD 技巧当成「交付物可移植性」的修复 —— 它只解决测试期加载。
