# garcon 4.20.0 适配笔记

## 编译环境
- 构建系统: autotools（tarball 实测无 meson.build——XFCE 上游 garcon 分支尚未切 meson，
  任务卡"meson"与实测不符，按实测走 autotools；tarball 自带预生成 configure/Makefile.in）
- 编译日期: 2026-10-15
- 编译器: clang/clang++（OHOS SDK，aarch64-linux-ohos）
- 状态: built（本机 conan create RC=0，制品未发布——等 libxfce4util #15906 merge）

## 编译步骤

1. `conan create archives/g/garcon/4.20.0 -pr:h=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64 --build=missing -c tools.build:jobs=2`
2. 前置依赖本机缓存：libxfce4util/4.20.1 先行 `conan create`（与在途 PR #15906 配方
   一致），落本机 cache 后 garcon 从 cache 解析 requires。
3. 配方层适配（patch 0001 只改 Makefile.in + configure，不跑 autoreconf）：
   - SUBDIRS 裁剪：garcon-gtk（唯一 libxfce4ui 消费者，xfconf 链未发布）、
     docs（gtk-doc）、tests（test-display-menu-gtk3 链接被裁的 garcon-gtk；三程序
     均 noinst 未接 make check）全部移出构建；核心 libgarcon 零 libxfce4ui 引用
     （garcon/ 目录逐文件审计）；
   - configure 的 LIBXFCE4UI2 pkg-config 探测用 stub libxfce4ui-2.pc 满足
     （空 flags，无消费者）；
   - configure mktemp 模板重定向到 /data/storage/el2/base/temp/：HMFS 上
     `umask 077 && mktemp -d ./confXXXXXX` 产出 setgid 目录属主不可写，
     config.status Permission denied（实测；el2 分区不受影响）；
   - `--build=aarch64-linux` 显式三元组（config.guess 认不出 HarmonyOS 内核；
     原生编译不传 --host，config.sub 不认 ohos）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 libxfce4ui-2 not found | 制品仓无 libxfce4ui（xfconf 链未适配） | patch 0001 从 SUBDIRS 裁掉 garcon-gtk + stub libxfce4ui-2.pc 过探测（核心库零依赖，审计见 MANIFEST） |
| 2 | autoreconf 路线失败 | autotools 工具链分裂在 hnp/usr-local 双前缀，本地 aclocal 对 vendored XDT 宏不展开 | 改补 tarball 预生成的 configure/Makefile.in 直用 |
| 3 | config.status 阶段 Permission denied | HMFS 上 `umask 077 && mktemp -d ./confXXXXXX` 产出 setgid 目录，属主写不进 | patch 0001 把 configure 的 mktemp 模板指到 /data/storage/el2/base/temp/ |
| 4 | 链接报 g_libintl_* undefined | OHOS sysroot libintl 空 stub + lld --no-allow-shlib-undefined | glib 家族 .pc Libs 追加 -lintl（libxfce4util 4.20.1 同款） |
| 5 | glib-2.0 探测失败 Requires.private | OHOS pkg-config 急切解析 Requires.private 而 libffi.pc 不在图里 | .pc 后处理剥 libffi（wlrctl 先例） |
| 6 | 安装副本 .so 加载失败风险 | libtool install 重写 ELF 使链接器自签 .codesign 失效 | package() 内 binary-sign-tool selfSign 重签 lib/*.so（libxfce4util/glib 先例） |
| 7 | 包内 .la 带构建机绝对路径 + '//lib' | libtool install 记录 configure 期路径 | package() 内 rm *.la（libxfce4util 4.20.0 历史教训，commit 2cc04f7c35） |

## 源码修改

patches/0001-drop-garcon-gtk-and-docs-subdirs.patch：
- Makefile.in：SUBDIRS 去掉 garcon-gtk/docs/tests
- configure：mktemp 模板重定向到 el2 分区

## 依赖版本

- glib/2.84.0.1（制品仓）
- gtk/3.24.43（制品仓；上游 XDT_CHECK_PACKAGE 硬依赖，.pc Requires 声明）
- libxfce4util/4.20.1（在途 PR #15906，本机 cache；merge 后 CI 可解析）

## 验证结果

```bash
conan create archives/g/garcon/4.20.0 \
  -pr:h=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64 \
  --build=missing -c tools.build:jobs=2
# → RC=0
# test_package 消费者冒烟 3/3：版本 extern 断言（4.x）、
# garcon_menu_new_for_path 构造+销毁、menu-item-pool 构造+销毁
# 上游测试 N=0（三程序均 noinst 未接 make check，审计见 test_package/MANIFEST.yml）
```

## 注意事项

- 本包是依赖项任务（任务卡 #15234）：制品不发布、分支不推送——等
  libxfce4util #15906 merge 后由主对话另派推送任务，届时 CI 才能从
  制品仓解析 libxfce4util/4.20.1。
- 下游（libxfce4ui 等）经 pkg-config garcon-1 消费；头文件在
  include/garcon-1/garcon/。
- 上游 4.20.0 是 autotools；XFCE 后续版本若切 meson，配方需换范式
  （libxfce4util 4.20.1 的 meson 配方可参照）。
