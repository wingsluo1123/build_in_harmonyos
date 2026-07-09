# zangband 2.7.5.1

## 软件描述
ZAngband (Zelazny Angband) 是基于 Angband 的 Roguelike 角色扮演游戏。
玩家在地下城中探险、战斗、收集装备，目标是击败最终 Boss。

## 版本信息
- **版本**: 2.7.5.1 (内部版本号 2.7.5pre1)
- **来源**: SourceForge release tarball
- **URL**: https://sourceforge.net/projects/zangband/files/zangband-src/2.7.5%20preview%20I/zangband-2.7.5pre1.tar.gz/download
- **SHA256**: 86871739825a292b9def28ec0dea698fb0d34949c7fab071901c231274be4c44

## 构建信息
- **构建系统**: autotools (autoconf 2.59)
- **编译器**: clang 15.0.4
- **目标平台**: OpenHarmony aarch64 (musl libc)
- **依赖**: ncurses, zlib, X11

## 补丁
1. **0001-configure.patch**: E011 修复 — umask 077→022 (HMDFS 权限兼容)
2. **0002-makefile.patch**: 生成文件变更 (CC_AUX, CFLAGS 等环境适配)

## 预编译包
- `packaging/zangband-2.7.5.1-ohos-aarch64.tar.gz` (6.8MB)
- 包含: bin/zangband + share/games/zangband/ (游戏数据)

## 安装
```bash
# 解压预编译包
tar xzf zangband-2.7.5.1-ohos-aarch64.tar.gz -C /
# 运行
zangband
```

## 质量门禁
- G1 二进制完整性: ✅ PASS
- G2 Conan 干净构建: ✅ PASS
- G4 产物完整性: ✅ PASS
- L4 安全扫描: ✅ PASS
- L5 基线对比: ✅ PASS

## 许可证
MIT
