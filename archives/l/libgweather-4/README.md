# libgweather

libgweather（GWeather）是 GNOME 的天气与世界位置信息库：提供世界位置数据库
（城市/气象站/时区，数据来自 gweather-locations 的 Locations.bin）、时区与
日出日落/月相的本地计算、METAR 报文解析，以及 MET Norway / OpenWeatherMap /
NWS / Iwin 等天气服务后端。GTK 应用通过 pkg-config 名 `gweather4` 或
GObject introspection 消费。

## 功能概述

- 世界位置数据库访问：区域→国家→州→城市→气象站的层级查询、最近城市查找、
  机场代码/气象站代码定位、序列化/反序列化
- 时区信息与地理时区推断；日出/日落/月相的本地天文计算
- METAR 报文解析与多天气服务后端（网络功能，运行期按需使用）
- GSettings 配置（org.gnome.GWeather4：温度/风速/距离单位等）

## OHOS 适配

- 交叉构建关闭 `introspection`/`gtk_doc`/`enable_vala`（构建机无
  g-ir-scanner/vapigen；gir 在交叉构建下上游也自动关闭）
- `gnome.mkenums`/`gnome.post_install` 需要构建机 glib 工具：recipe 将
  glib 包 bin 目录前置进 PATH，并把 glib_mkenums/glib_compile_schemas 等
  工具变量补丁进 glib-2.0.pc（geocode-glib 先例）
- 位置数据库来自独立数据包 gweather-locations（Locations.bin 为 GVariant
  二进制、构建机字节序）；编译期宏 GWEATHER_LOCATIONS_DB 由
  gweather-locations.pc 的 `locations_db` 变量注入（Conan 生成的 .pc 会
  丢失该变量，recipe 已回填）；运行期可用 `LIBGWEATHER_LOCATIONS_PATH`
  环境变量覆盖
- GSettings schema 随包装入 `share/glib-2.0/schemas` 并编译出
  gschemas.compiled；运行期缺失 schema 时 `g_settings_new` 会 abort，
  下游应用需保证该目录可用（或设置 `GSETTINGS_SCHEMA_DIR`）
- GLib 的 GTimeZone 需按 TZDIR 查找逐文件的 TZif；OHOS 镜像只有
  Android 式单文件 `/system/etc/zoneinfo/tzdata`（无
  /usr/share/zoneinfo）。recipe 构建期把 blob 拆成 TZif 树（并补回
  Antarctica/South_Pole、Pacific/Johnston 两个 tzdb 链接别名），
  上游测试以 TZDIR 指向该树实跑，并把树随包发布到
  `share/zoneinfo` 供下游设置 TZDIR 使用
- gettext 域为 `libgweather-4.0`（位置名翻译域 `gweather-locations` 在
  数据包内）；musl 无独立 libintl，走 glib proxy-libintl
- 交付的 .so 需 binary-sign-tool 重签（OHOS loader 要求有效 .codesign 段）
- 许可证为 GPL-2.0-or-later（注意：不是 LGPL，下游链接方式需自查）

## 依赖关系

- 编译依赖：glib(gio-2.0) >= 2.68、libsoup-3.0 >= 2.99.2、libxml-2.0 >= 2.6、
  json-glib-1.0、geocode-glib-2.0（libsoup3 flavour）、gweather-locations
  （数据包，提供 locations_db）
- 运行依赖：glib 及以上各库的 .so、Locations.bin、GSettings schema；
  天气后端的网络功能需运行期网络可达

## 参考资料

- 上游：https://gitlab.gnome.org/GNOME/libgweather
- 源码归档：https://download.gnome.org/sources/libgweather/
- 数据包：https://download.gnome.org/sources/gweather-locations/
