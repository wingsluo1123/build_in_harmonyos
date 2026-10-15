# gif 5.2.2 测试报告

## 上游回归套件（tests/makefile，12 个 regress 目标）

| 目标 | 结果 | 说明 |
|------|------|------|
| render-regress | ✅ | gif2rgb RGB 渲染 9 张图片与基准 .rgb 逐像素 cmp |
| gif2rgb-regress | ✅ | gif2rgb→gifbuild 幂等性 diff |
| gifbuild-regress | ✅ | gifbuild -d 与基准 .ico diff |
| gifclrmp-regress | ✅ | 色彩映射行为 |
| gifecho-regress | ✅ | 拷贝行为 |
| giffilter-regress | ✅ | giffilter→gif2rgb 与基准 cmp（9 图） |
| giffix-regress | ✅ | 截断 GIF 修复后 gifbuild -d diff（补丁 0001） |
| gifinto-regress | ✅ | 短文件/非法输入行为 |
| gifsponge-regress | ✅ | 拷贝 9 图与原始 cmp |
| giftext-regress | ✅ | 文本转储 9 图 |
| giftool-regress | ✅ | 拷贝/去隔行/隔行 |
| gifwedge-regress | ✅ | 楔形图生成 |

命令：`make -C tests`（含 giffix-rebuild 前置，输出 "No output is good news"，退出码 0）。
日志：reports/conan-create.log（W3 内 conan create 执行），SHA-256
f20689fc58f565efc3052fa67cc80cf1993392b7f1adf1af58320c3d4a54db31。

## 消费者测试（test_package/test_gif）

- 公开 API：EGifOpenFileName / EGifPutScreenDesc / EGifPutImageDesc /
  EGifPutLine / EGifCloseFile / DGifOpenFileName / DGifSlurp / DGifCloseFile
- 行为：编码 3x2 GIF（2 色索引）→ 解码 → 尺寸/图像数/6 像素往返逐字节断言
- 结果：`gif consumer round-trip OK: 3x2, 1 image(s), 6 pixels verified` +
  `test_gif: PASS`，退出码 0

## 统计（双口径）

- source_declared_total: 13（12 上游回归目标 + 1 消费者）
- configured_executable_total: 13
- executed_passed_total: 13，失败 0，未运行 0
- 通过率：13/13（100%）
