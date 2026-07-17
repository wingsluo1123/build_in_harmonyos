# farbfeld

## 简介
farbfeld 是一个简单的无损图像格式，使用 16 位 RGBA 像素数据。提供 `ff2pam`、`ff2ppm`、`2ff` 等转换工具。

## OHOS 适配
- 通过 make 命令行参数传递编译器(CC)和标志(CPPFLAGS/CFLAGS/LDFLAGS)，无需补丁
- 构建系统为简单 Makefile，无需 configure
- OHOS 不支持 make -j2+，必须使用 -j1

## 依赖
- libpng（png2ff/ff2png 转换工具）
- libjpeg（jpg2ff/ff2jpg 转换工具）
- ff2pam/ff2ppm 无外部依赖

## 功能验证
```bash
ff2ppm < test.ff > test.ppm
ff2pam < test.ff > test.pam
```

## 参考
- 官网: https://tools.suckless.org/farbfeld/
