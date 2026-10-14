# libdmapsharing

## 简介

libdmapsharing 是用 C/GObject 实现的 DMAP 系列协议（DAAP/DPAP/DACP）库，
用于访问、共享和控制 iTunes 类媒体库；并附带音频 AirPlay 服务探测能力
（配合 PulseAudio/GStreamer 可向 AirPlay 设备推流）。基于 libsoup 与 avahi
mDNS。

## OHOS 适配

- 构建系统：autotools（release 自带生成的 configure，无需 autogen）
- 依赖（制品仓，R36）：
  - glib/2.84.0.1.1（全链共享，单 GObject 拷贝）
  - libsoup3/3.6.5-r3
  - avahi-glib/0.9_rc5（mDNS：avahi-client + avahi-glib）
  - check/0.11.0（上游单元测试框架）
- 关键适配点：
  - 单 GObject 拷贝：避免 libsoup/avahi 各自带 glib 造成“existing type”SIGABRT
  - avahi-client.pc shim：avahi-glib 合并 cpp_info 不产 avahi-client.pc，
    configure 的 PKG_CHECK_MODULE 需要它（配方 generate() 手写）
  - HMFS：configure AS_TMPDIR umask 077 运行时补丁、install 批量头 shim、
    glib-mkenums python launcher
- 上游测试：6 套 Check suite 共 45 用例（经 tests/unit-test 聚合运行）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 3.9.14 | built | autotools + libsoup3 + avahi mDNS，上游 45 用例接入 |
