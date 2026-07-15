# nrg2iso 0.4.1 适配笔记

## 编译环境
- 构建系统: makefile（原始 Makefile 为简单手写版，非 autotools）
- 编译日期: 2026-07-15
- 编译器: clang 15.0.4
- 状态: built
- 目标平台: OpenHarmony / aarch64 (musl libc)

## 编译步骤

1. `ohc-run.py init-build nrg2iso 0.4.1 --url=https://distfiles.macports.org/nrg2iso/nrg2iso-0.4.1.tar.gz`
2. 读取 `.build-context-nrg2iso-0.4.1` 获取环境变量
3. 发现原始 Makefile 硬编码 gcc，无 install/DESTDIR 支持 → 应用 0001-Makefile.patch
4. `cd $BUILD_SRC_DIR && make -j1 CC=clang CFLAGS="-fPIC -O2" PREFIX=$DEFAULT_PREFIX`
5. `make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX`（staging 验证）
6. 功能验证: `nrg2iso --version` / `nrg2iso --help` / NRG→ISO 转换测试
7. `ohc-run.py conan-init nrg2iso 0.4.1` → 生成 conanfile.py + conandata.yml + test_package/
8. 手动调整 conanfile.py 为 application 类型（package_type="application"）
9. `ohc-run.py conan-verify nrg2iso 0.4.1` → 验证配方
10. `ohc-run.py finish nrg2iso 0.4.1 published`
11. `ohc-run.py submit nrg2iso 0.4.1`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 原始 Makefile 硬编码 gcc，无 install/DESTDIR 目标 | 上游 Makefile 过于简陋，仅 `gcc nrg2iso.c -o nrg2iso` 一行 | 重写 Makefile，引入 CC/CFLAGS/PREFIX/DESTDIR 变量，添加 install/uninstall 目标 |
| 2 | conan-init 生成 library 类型配方 | 模板默认 library | 手动改为 application 类型，package() 复制二进制到 bin/，test_package 用 test.sh 执行 --version |
| 3 | /tmp 只读 | E002 鸿蒙平台限制 | 使用 $TMPDIR |

## 源码修改

- **0001-Makefile.patch**: 重写 Makefile（+17/-3 行）
  - 硬编码 gcc → 环境变量 CC（默认 clang）
  - 添加 CFLAGS（默认 -fPIC -O2）
  - 添加 PREFIX/DESTDIR 支持
  - 添加 install/uninstall 目标
  - 修正 clean 目标格式

## 依赖版本

无依赖。nrg2iso 是纯 C 单文件程序，仅依赖 libc（musl）。

## 验证结果

```bash
# 版本检查
$ nrg2iso --version
nrg2iso v0.4

# 帮助信息
$ nrg2iso --help
Nrg2Iso v0.4 by G. Kokanosky
released under the GNU GPL v3 or later
...

# 核心功能测试：NRG → ISO 转换
$ nrg2iso test-dummy.nrg test-dummy.iso
|=======>[100%]
test-dummy.iso written : 40960 bytes
```
---

**编译结束**: 2026-07-16 00:11
**最终状态**: built
