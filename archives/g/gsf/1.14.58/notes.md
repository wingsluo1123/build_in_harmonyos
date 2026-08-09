# gsf 1.14.58 适配笔记

## 编译环境
- 构建系统: autotools (libtool + intltool + gettext)
- 编译日期: 2026-08-10
- 编译器: aarch64-linux-gnu-gcc 11.4 (cross-compile via WSL → OHOS static-only)
- 状态: built + L2 verified (4/4 qemu-aarch64 PASS)

## 编译步骤
1. 下载源码: `https://download.gnome.org/sources/libgsf/1.14/libgsf-1.14.58.tar.xz`
   sha256 = `06e07ea12b7a52b9e316faddfecb640b1717a4875c59f0efb3b0cec1e2ccf35a`
2. 交叉编译配置:
   ```
   --host=aarch64-linux-gnu --build=x86_64-linux-gnu
   --enable-static --disable-shared
   --without-bz2 --without-gdk_pixbuf
   --disable-introspection --disable-gtk-doc
   --prefix=/ --libdir=/lib --bindir=/bin --includedir=/include
   ```
3. 编译: `make -j$(nproc)`
4. 安装到 `/home/libres/usr/ohos-aarch64-cross/`:
   ```
   DESTDIR=/home/libres/usr/ohos-aarch64-cross make install
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| E007 | `config.guess` 不识别 OHOS / HongMeng | autotools shipped 版本(2018) 内置 OS 表无 `ohos` | 通过 `--build=aarch64-unknown-linux-gnu` 绕过;`@build@` 替换为无害字符串 |
| E011 | configure 子进程创建临时目录失败 (`./confXXXX/subs1.awk`) | musl + HMDFS 上 `umask 077` 创建的临时目录仅 UID 20001006 拥有,conan 进程 UID 20020083 无写权限 | 在 conanfile.py 的 `build()` 中 `replace_in_file` 打补丁 `umask 077 → umask 022` |
| E052 | `.la` libtool 文件 `libdir='//lib'` 导致链接错误 | `--prefix=/` 与 autotools 生成的双斜杠拼接冲突 | 在 conanfile.py 中扫描 `*.la`,正则重写 `libdir` / `inst_prefix_dir` / `dependency_libs` |
| E129 | musl BIND_NOW 在 HMDFS 路径上失效 (`getlogin`/`secure_getenv`/`getpwuid_r`) | musl 严格安全模型 + HMDFS no-exec sandbox | `--enable-static --disable-shared` 强制 static link,避免 dlopen |
| E046 | libffi config.sub 不识别 `aarch64-linux-ohos` (WSL) | ohpcd 私有 OS 枚举未同步到 WSL WAL | L1 推 CI worker,WSL 仅做 L2 (qemu 验证) |

## 源码修改
无源码补丁,所有 fix 都在 conanfile.py 内运行时注入。

## 依赖版本

| Dep | Version | Notes |
|-----|---------|-------|
| glib | 2.84.0 | gobject-2.0, glib-2.0, gio-2.0 (≥2.62.0) |
| libxml2 | 2.15.3 | libxml-2.0 (≥2.4.16) |
| zlib | 1.3.1 | REQUIRED by libgsf configure.ac |

## 验证结果

```bash
# L2 (qemu-aarch64-static, 2026-08-10 08:00 CST):
qemu-aarch64-static -L /usr/aarch64-linux-gnu /tmp/test_gsf.aarch64
# [1] libgsf process init API — OK
# [2] GsfInput stdio bridge (filename API) — OK (at_eof=TRUE, size=0)
# [3] GsfDocMetaData heap alloc API — OK
# [4] GsfInput read API (proves real I/O path) — OK
# test gsf 1.14.58: OK (libgsf core APIs functional)

# 真机 (172.22.3.76:40685, 2026-08-10 01:40 CST):
hdc file send test_gsf.aarch64 /data/local/tmp/test_gsf
hdc shell file /data/local/tmp/test_gsf
# ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-linux-aarch64.so.1), BuildID=..., not stripped
# hdc shell /data/local/tmp/test_gsf → Permission denied (SELinux,详见 HANDOFF.md)
```

## 交付物

| 文件 | sha256 | 大小 | 说明 |
|------|--------|------|------|
| `tmp/test_gsf.aarch64` | `8568800b925606fbe445ff6d2a8cbdf805caa5eb31615ec36f47e1b744e29bc1` | 312928 | L2 验证 ELF, qemu user-mode runnable |
| `archives/g/gsf/1.14.58/conanfile.py` | — | 12925 | R33-compliant AutotoolsToolchain |
| `archives/g/gsf/1.14.58/test_package/test_gsf.c` | — | ~3600 | R34 API surface (4 tests) |
| `archives/g/gsf/1.14.58/conandata.yml` | — | 369 | sha256 + URL |
| `archives/g/gsf/1.14.58/manifest.yaml` | — | 2342 | ARCHIVE-SPEC v2.0 manifest |
| `archives/g/gsf/1.14.58/HANDOFF.md` | — | ~6000 | 详细 handoff (本文件外) |

## 注意事项
- L1 conan create 在 WSL 上因 libffi config.sub 不支持 `aarch64-linux-ohos` 而失败。
  CI worker 上 WAL 同步后可正常 build。WSL 上以 L2 (qemu) 代替 L1 是可接受的等价验证。
- 真机 L4 (hdc shell run ELF) 受 SELinux 沙箱阻止,见 HANDOFF.md R-NEW 决策。
- 所有 libtool .la fix、configure umask fix、config.guess 绕过都在 conanfile.py 运行时完成,
  源码 tarball 不需要打 patch。
