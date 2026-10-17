# DRAFT — 字节等值测试对 JPEG 编解码器选择的敏感性（libjpeg vs libjpeg-turbo）

- **软件**：libpillowfight 0.2.4
- **任务**：`libpillowfight-0.2.4-r04-upstream-pytest-full-pass-env-alignment-pc1-35-20261015T093500Z`
- **状态**：DRAFT（配对 `DRAFT-libpillowfight-0.2.4-jpeg-codec-byte-equality.kv`）
- **编号**：`DRAFT-libpillowfight-0.2.4-jpeg-codec-byte-equality`（待人工审核后分配正式 E 编号）

## 1. 现象

上游图像测试的经典断言模式是"算法输出经 JPEG 保存→重开→`tobytes()` 与参考 JPEG
字节等值"（上游测试自带注释 *beware of JPG compression*）。设备端跑出大量
`AssertionError: ... != ...`，差异看起来是 ±1~2 像素漂移，但换编解码器后显著变化。

## 2. 根因

参考 JPEG 由维护者环境（pip wheel 内置 libjpeg-turbo）编码生成；设备端 Pillow 经
pip 源码构建时默认链接系统 libjpeg（非 turbo）。同一像素在不同编码器下的量化与解码
产生不同字节。实测（同一 RGB 像素，libjpeg/10 vs libjpeg-turbo 3.2.0）：

| 项 | 值 |
|---|---|
| 编码器差异 | 129956 像素（max 通道和 6，共 6,559,040 像素） |
| 同一参考 jpg 两解码器 | tobytes() 不同（exp_sha 不等） |

字节等值断言下，这些差异直接导致测试失败——与算法浮点无关（实验 2/3 已证伪
ffp-contract 与 libm）。

## 3. 设备可执行复现

```sh
python3 /storage/Users/currentUser/runnerljs002/r04-ab-jpeg.py
# 输出：encoder_delta_pixels 129956 / encoder_delta_max_channel_sum 6 / exp_sha_equal False
```

## 4. 处置（libpillowfight R04 实测有效：纯滤波器 TEST_DIFF -95%）

从制品仓获取 libjpeg-turbo（conan libjpeg-turbo/3.x），CPPFLAGS/LDFLAGS 指向其
include/lib 重建 Pillow（`pip install --force-reinstall --no-deps Pillow`），运行测试时
`LD_LIBRARY_PATH` 指向 turbo lib。效果：blackfilter 118k→7k、blurfilter 121k→5k、
border 44k→2k、grayfilter 244k→12k、masks 44k→2k、noisefilter 114k→5k（像素数）。

## 5. 边界与反例

- **与 E100/E157/E331 的区别**：均为构建期问题（jsimd 检测/版本探测/符号链接）；
  本条是测试期字节等值断言对编解码器选择的敏感性。
- **反例**：测试不比对 JPEG 字节（用无损中间态/结构断言）时不需要对齐编解码器。
- **限制**：若参考环境编码器版本/质量参数不可达，边界翻转无法逐字节复原，残余需裁决；
  禁止把参考 JPEG 重新编码生成"匹配"的期望图。

## 6. 复用提示

凡图像库测试用"JPEG 保存-重开-字节等值"比对参考产物，且设备端 Pillow 为非 turbo
libjpeg：先做同像素编码器 A/B 量化（证明差异存在），再对齐 libjpeg-turbo 重建 Pillow，
量化收敛后残余交分析端裁决。

## 7. 复现证据（本任务）

| 项 | 值 |
|---|---|
| A/B 日志 | `exp4-jpeg-ab.log`：encoder_delta_pixels=129956、max=6、exp_sha_equal=False |
| 对齐重建 | `exp4-pillow-turbo-system.log`（系统 Pillow 换 turbo，PIL 12.3.0 解码 OK） |
| 效果 | 纯滤波器 TEST_DIFF 44k~244k → 2k~12k（-95%） |
