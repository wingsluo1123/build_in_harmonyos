# xastir 2.2.4：无 configure 的引导构建、Magick 0x0700 硬上限、Berkeley DB 探测名单缺 db、zlib 力导轨与 E050 链接视图

## 命中场景

(1) 官方发布物只有 configure.ac 的 autotools 项目（bootstrap 全链引导）；
(2) 带 ImageMagick/GraphicsMagick 可选集成的老牌图形应用（上游对
MagickLibVersion 有硬上限）；
(3) 用 AC_SEARCH_LIBS 探 Berkeley DB 但名单不含裸 `db` 的项目；
(4) 多依赖 force/版本轨分歧导致传递依赖落到未发布 package_id；
(5) 依赖闭包里有 E050 坏符号链接节点的链接 + 运行。

## 症状（实测，xastir 2.2.4 / OHOS aarch64 / clang 15）

1. `aclocal: couldn't open directory 'm4': No such file or directory`
2. `configure: error: cannot find install-sh`（缺 automake --add-missing）
3. magick 探测分支 `#error MagickLibVersion ... way too new`（0x712 > 0x0700）
4. `USE_MAP_CACHE` 静默为 0（db 探测名单无一命中 libdb.a）
5. 不 force zlib 时 conan 图展开两套 zlib；force 后 libxext/libxpm 的
   package_id 变 eab79208…（制品仓未发布）
6. `AC_CHECK_LIB(tiff, TIFFClose)` 失败：`cannot find -ltiff`（包内符号
   链接节点 stat() EACCES）；绕过链接后运行期
   `Error loading shared library libtiff.so.6` / `Error relocating ... libXau`

## 根因

| 层 | 问题 |
|----|------|
| 上游发布 | tarball 不带空 m4/；bootstrap 脚本对交叉工具链不友好 |
| 上游宏 | XASTIR_CHECK_IMAGEMAGICK 硬性 `#error`（API 窗口停在 IM6）；XASTIR_BERKELEY_DB_CHK_LIB 名单是发行版 db4.7~db18 命名集合 |
| 依赖图 | motif force libx11/1.8.13 + curl/libax25 各 pin 不同 zlib → 未发布轨 |
| worker | E050 符号链接节点跨任务标签不可读（本机 libtiff/libjpeg/libwebp/zstd/libxau/libxdmcp） |

## 解法（archives/x/xastir/2.2.4/）

1. `mkdir m4` + `sh <aclocal-wrapper>`（ACLOCAL_PATH=srcdir/m4）+ hnp 系统
   autoheader/autoconf 2.72 + `sh <automake-wrapper> --add-missing --copy
   --no-force`；configure 以 `sh configure` 运行并显式
   `--build=aarch64-linux-ohos --host=aarch64-linux-ohos`。
2. `--without-graphicsmagick --without-imagemagick`（确定性禁用；栅格导入
   走 GeoTIFF + shapelib 路径，功能面保持）。
3. toolchain env 预置 `LIBS += -ldb` → AC_SEARCH_LIBS 的 none-required 分支
   命中 → USE_MAP_CACHE=1。
4. 顶层 `zlib/1.3.1.1 force=True`；libxext/libxpm 未发布轨由 CI 源码重建
   （twclock 先例：同 pkgid 已在 CI 缓存命中过）。
5. `generate()` 私有链接视图：闭包 lib 目录里真实文件直接拷贝、不可读节点
   按最高版本可读兄弟文件以节点名重建；`-L<view>` 与
   `LD_LIBRARY_PATH=<view>` 都放首位（230 个上游 autotest 测试真实执行）；
   test_package 复刻同一视图保证消费端运行期可加载。

## 验证

- `conan create … -pr:h -pr:b ci/conan/profiles/ohos-aarch64 --build=missing`
  全绿（pkgid 09a58d77e0b6fe964a536f8fc71cc441ba758579）
- 上游 `make check`：`All 230 tests were successful.`（CHECK_EXIT=0）
- 消费者测试 6 组断言全过（callpass 哈希、headless、DT_NEEDED 正反向、数据树）
