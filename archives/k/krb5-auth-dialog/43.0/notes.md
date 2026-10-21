# krb5-auth-dialog 43.0 适配笔记

## 概述
GNOME Kerberos 凭据通知小程序（GTK3 applet），meson 构建。任务卡 #12899
（calbee21 认领）。交付形态：bin/krb5-auth-dialog 可执行 + 三个运行时插件
（dummy/afs/gnomelock；pam 插件关闭）。

## 上游测试口径（rule4）
上游 meson 项目**无任何 test()/add_test 注册**（GUI 小程序，无测试套件，
src/ 下无 tests 子目录）——N=0。验证由 test_package 消费者测试承担：
产物层（AArch64 ELF/裸 soname/签名）+ CLI 合同（--version 在 gtk_init 前
处理并输出 "krb5-auth-dialog 43.0"，补丁 0003）。

## 适配要点
1. **gcr-3 替换**（0001）：registry 仅有 gcr-base/3.41.2（gtk=false 构建，
   不含 gcr-3 UI 库）→ GcrSecureEntryBuffer 换 GtkEntryBuffer（密码安全
   内存特性舍弃，功能可用），改动面：meson.build 依赖行 + ka-pwdialog.c
   头文件与 g_type_ensure + ka-pwdialog.ui 对象类。
2. **help/ 跳过**（0002）：gnome.yelp 需 itstool/yelp-tools（OHOS 无）。
   post_install.py shebang 改 /usr/bin/env python3（硬编码 /usr/bin/python3
   不存在时 install 脚本失败）；DESTDIR 模式下其 gsettings/icon-cache
   编译步骤自动跳过。
3. **headless --version**（0003）：gtk_init 之前处理 --version 并
   return 0——无显示环境的 OHOS 上 CLI 合同可验证（R34 实质验证路径）。
4. **meson 选项**：pam-plugin=disabled（pam 头不在依赖闭包）、
   pkinit=disabled（最小化 krb5 preauth 面）、etpo=disabled（上游默认，
   flex/bison 不需要）。
5. **glib 构建工具 wrapper**：glib-compile-resources / glib-compile-schemas
   为无 RPATH ELF，wrapper 注入 LD_LIBRARY_PATH=glib 包 lib（libnma-gtk4
   同款模式）。
6. **ELF 自签名**：bin/krb5-auth-dialog 与 lib/krb5-auth-dialog/plugins/*.so
   在 package() 内 binary-sign-tool selfSign（XPM 拒绝未签名 exec/dlopen）。
7. **po/i18n**：i18n.gettext preset 'glib' + .desktop merge 需要 msgfmt，
   由 gettext/0.22.5.1 tool_requires 提供（libnma-gtk4 同款）。

## 依赖
- glib/2.84.0.1（gtk/3.24.43 内部 pin 同版，avahi-ui 0.8 先例）
- gtk/3.24.43（gtk+-3.0 >= 3.14 满足）
- krb5/1.22.1（krb5.pc：libkrb5/gssapi_krb5/k5crypto/com_err 等）

## Verification
- 源码 SHA256：0ebf108f0f4bc1247e8cbbfc7c9f4a50afdf7e79ceb4183ef37aec59d4365397
  （下载实测）
- 上游测试：N=0（无注册套件）
- test_package：4 断言全过（机器 AArch64/NEEDED 裸 soname/单 .codesign/
  --version 输出 "krb5-auth-dialog 43.0"）

---

**编译结束**: 2026-10-05
**最终状态**: built
