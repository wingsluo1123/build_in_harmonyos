# pragha

## 简介
pragha 是一个基于 GTK+ 3 的轻量级音乐播放器，提供曲库管理、播放列表、
GStreamer 播放后端、媒体标签读取（taglib）与音乐数据库（sqlite3）。

## OHOS 适配
- **构建系统**: autotools（上游随附生成文件，无需 autoreconf）
- **依赖链**: glib → gtk（broadway 后端）；gstreamer（核心静态）；sqlite3、taglib（taglib_c C 绑定）
- **插件子系统**: libpeas 门控的 14 个可选插件全部禁用（OHOS 无对应依赖发布）
- **运行期验证**: 无显示环境，经 `--version` / `--help` / `--selftest`
  无头路径 + no-display fail-closed 路径验证（test_package 14 断言）

## 依赖
- glib/2.84.0.1
- gtk/3.24.43
- gstreamer/1.28.3
- sqlite3/3.53.4
- taglib/1.13.1
- zlib/1.3.1.1（glib/glib2 双图对齐）

## 功能验证
```bash
pragha --version    # 期望输出: pragha 1.3.4
pragha --selftest   # 期望输出: pragha selftest: all checks passed
```

## 参考
- 官网: https://github.com/pragha-music-player/pragha
- 源码: https://github.com/pragha-music-player/pragha/releases/tag/v1.3.4
