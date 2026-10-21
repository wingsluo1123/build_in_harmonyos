# krb5-auth-dialog

GNOME Kerberos 凭据通知小程序（GTK3 applet）：监控 Kerberos 凭据缓存，
临期弹窗提示续票。上游 https://gitlab.gnome.org/GNOME/krb5-auth-dialog 。

## OHOS 适配

- gcr-3 以 GtkEntryBuffer 替代（registry 仅 gcr-base gtk=false 变体）
- help/ 跳过（gnome.yelp 需 itstool/yelp-tools）
- --version 在 gtk_init 前处理（headless 可验证）
- pam-plugin/pkinit/etpo 关闭
- 产物 ELF 自签名（XPM exec/dlopen 要求）

## 依赖

- glib/2.84.0.1、gtk/3.24.43、krb5/1.22.1
