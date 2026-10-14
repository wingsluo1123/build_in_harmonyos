# id3lib

id3lib 是一个用于读写 MP3 文件中 ID3v1/ID3v1.1/ID3v2 标签的 C++ 库，
附带四个命令行工具（id3info / id3tag / id3convert / id3cp）。

- 官网: https://sourceforge.net/projects/id3lib/
- 许可证: LGPL-2.0-or-later
- 构建系统: autotools

## 适配版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 3.8.3 | built | aarch64 HarmonyOS PC（os=OHOS），静态库 libid3.a |

## 包内容

- `lib/libid3.a` — 静态库（4 个 CLI 与库本体）
- `include/id3.h`、`include/id3/*` — 头文件
- `bin/id3info`、`bin/id3tag`、`bin/id3convert`、`bin/id3cp` — 命令行工具

## HarmonyOS 适配要点

1. `config.guess`/`config.sub` 增加 HarmonyOS → `aarch64-unknown-linux-ohos` 支持
2. 移除 `iomanip.h` 致命头检查（现代 libc++ 不提供该头）
3. 老旧 C++ 语法修复（`main` 签名、`<iostream.h>` → `<iostream>`）
4. HMDFS 上 `config.status` 临时目录 `umask` 修复（E011）
5. 依赖制品仓静态 `zlib/1.3.1`（压缩帧支持）
6. `examples/findeng.cpp`、`examples/findstr.cpp` 混合 CRLF 行尾在构建前归一化

详细背景与证据见 `3.8.3/notes.md` 与 `3.8.3/reports/test-report.md`。
