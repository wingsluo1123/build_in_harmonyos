# libsndfile 1.2.2 编译笔记

## 编译信息

- **编译日期**: 2026-05-29
- **编译状态**: 成功
- **构建系统**: CMake
- **依赖**: 无

## 适配说明

### 平台适配

需要修改 `build-aux/config.guess` 和 `build-aux/config.sub` 以识别 OpenHarmony 平台。

### 补丁文件

1. `0001-build-aux-config.guess.patch` - 添加 OpenHarmony 平台识别
2. `0002-build-aux-config.sub.patch` - 更新 config.sub 支持新平台

## 编译命令

```bash
mkdir build
cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local
make -j$(nproc)
make install DESTDIR=$HOME/tmp/test-install-libsndfile-1.2.2
```

## 验证结果

- 质量门禁: PASS
- 预编译包: libsndfile-1.2.2-ohos-aarch64.tar.gz (已生成)

## 产物列表

- libsndfile.a (静态库)
- sndfile-info, sndfile-play, sndfile-convert 等工具
- sndfile.h 头文件

## 注意事项

无特殊注意事项。
---

**编译结束**: 2026-06-07 14:07
**最终状态**: built
