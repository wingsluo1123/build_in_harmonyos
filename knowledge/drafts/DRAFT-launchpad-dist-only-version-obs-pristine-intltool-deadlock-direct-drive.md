# DRAFT-launchpad-dist-only-version-obs-pristine-intltool-deadlock-direct-drive — Launchpad 时代版本的全网溯源锚 + intltool 死锁包的直驱编译(中型多 TU GLib 库)

> 来源:libdbusmenu-glib 16.04.0 适配(task libdbusmenu-glib/16.04.0,10 火种积分赛)
> 环境:build_in_harmonyos 配方仓库;源为 openSUSE Factory 源码包内的 pristine tarball(760KB,241 项);OH 构建环境无 perl/intltool/gettext 工具链

## 场景特征

```
源 = 2016 年前的 Canonical/Launchpad 项目最后一个正式版(如 16.04.0):
  launchpad /+download/ 端点已死(HTTP 404);
  Ubuntu/Debian 池只有 daily/重打包版,从未有裸版本号 orig tarball;
  Launchpad 产品 API 的 release 序列停在更早年代(团队改走 bzr/daily)。
源 tarball 自带生成的 configure,但 configure 硬依赖 intltool ——
  IT_PROG_INTLTOOL 展开含七处独立致命检查(perl/三脚本/gettext/
  automake/intltool 版本 grep),stub 需伪造版本输出,脆且不可审计;
  Makefile.am 又以裸 PATH 调 glib-genmarshal/xsltproc(BUILT_SOURCES
  重生成风险),config.sub(2016)不识 ohos 三元组。
库本体 = 纯 GLib/GIO 的 11 个翻译单元,全部生成物(marshal/enum-types/
  gdbus XML C 数组)已在 tarball 内,零非 GLib 系统头。
```

## 触发条件

- 任务版本号对应 Launchpad 时代(Ubuntu YY.MM 风格)的"最后一个正式版"
- 上游 autotools release tarball 自带 configure,但 configure 依赖
  OHOS worker 不存在的工具链(intltool/perl/gettext/gnome-doc-utils 等)
- 库源码零平台系统头(纯 GLib/GObject/GIO),生成物齐全在包内

## 根因分析

1. **发行版版本号 ≠ 上游发布物**:Launchpad 项目在 bzr/daily 时代不建
   产品 release,版本号只存在于发行池;池内又只有 daily 版。裸版本号的
   pristine 字节只活在"未重打包"的第三方源码包里——openSUSE Factory
   的 spec `Source0:` 钉着原始 launchpad URL,即为未重打包的字节级证明。
2. **intltool 是 2016 年 GNOME 栈的依赖放大器**:它把 perl、三个
   intltool 脚本、gettext 工具、automake 全部变成 configure 硬前置;
   这些在 CI worker 上要么缺失、要么是 target 交叉编译产物不可执行。
3. 当生成物已随包分发且库体为纯 GLib TU 时,autotools 的特性检测
   价值为零——直驱编译既绕开全部工具链死锁,又保持产物可哈希审计。

## 解决方案

### 推荐方案(双管齐下)
1. **版本锚**:conandata url 用 openSUSE OBS 公共源 API 直链
   (`https://api.opensuse.org/public/source/openSUSE:Factory/<pkg>/<file>`,
   免登录、路径稳定),sha256 锚定;notes.md 写完整证据链
   (LP 端点 404 / 池内只有 daily / LP API release 停更 / spec Source0 印证)。
2. **直驱编译**:conanfile build() 内嵌 TU 白名单,PkgConfigDeps +
   pkg-config 取依赖 flags,逐 TU 编译后自行落 libtool 版本化 SONAME
   (`-version-info C:R:A` → soname=libX.so.(C-A),file=.so.(C-A).A.R);
   pkgconfig/*.pc、include 布局按上游 pc.in 镜像。subunit 贡献式包装
   的同族先例,但更进一步——连 CMake 都不用,纯 clang 直驱。
3. 两个必需宏必须写进编译 flags:`-DGETTEXT_PACKAGE`(含
   <glib/gi18n-lib.h> 的 TU 缺宏直接 #error)、`-DG_LOG_DOMAIN`
   (源码把该宏拼进字符串字面量,缺宏编译错)。
4. test_package 为真实消费者:CMakeDeps/CMakeToolchain find_package
   链接,对象级断言(menuitem 属性/子项、server 创建/status),
   免 DBus session。
5. musl:getlib .pc 修函数补 -lintl(与平台 json-glib 配方一致)。

### 禁止做法
- ❌ 在 CI 上 stub intltool-update/perl/xgettext 伪造版本输出
  (七处 grep 各自解析版本串,任何一个变体都炸,且不可审计)
- ❌ patch 万行生成 configure(neutralize as_fn_error 七处=大补丁漂移面)
- ❌ --host=aarch64-linux-ohos(2016 config.sub 直接拒绝)
- ❌ 依赖 tarball 内文件 mtime 相等来跳过 BUILT_SOURCES 重生成
  (make 语义脆弱;直驱后此问题整体消失)

## 验证

```bash
# 提交前 WSL glibc 全链路预验证(本例实测):
#   11/11 TU 编译 + 共享/静态链接 + 消费者冒烟 5/5 PASS(glib 2.72)
conan create archives/l/libdbusmenu-glib/16.04.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 关联条目

- 相关:DRAFT-subunit-github-tag-tarball-contributed-cmake-wrapper
  (子场景:tag tarball 无 configure;本条是"有 configure 但 configure
  本身不可用"的对照场景,直驱法是二者的共同终态)
- 相关:DRAFT-doas-6.9.3-bsd-configure-yacc-pregen-musl-monolithic-libc
  (姊妹:手写 configure 可跑时走 configure+make;生成 configure 不可跑时直驱)
- 冲突:无
