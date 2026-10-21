# mystiq

Qt5 GUI 音视频转码器（ffmpeg 前端），HarmonyOS PC（arm64）适配配方。

- 上游：https://github.com/swl-x/MystiQ （tag `v20.03.23`）
- 构建系统：qmake（`mystiq.pro`）
- 依赖（Conan）：`qt5-qtbase/5.15.2.2`、`qt5-qtdeclarative/5.15.2`、`qt5-qtmultimedia/5.15.2`
- 运行期外部程序：`ffmpeg` / `ffprobe`（必需，需随应用部署）；`sox`（可选，仅"音频变速"）

## 目录

```
20.03.23/
├── conanfile.py           # 配方（Qt5 合并前缀 + qmake 构建）
├── conandata.yml          # 上游源码 URL + sha256（无源码补丁）
├── ohos-tests/            # 鸿蒙特有测试（随配方分发，build() 落地到 tests/testohosplatform）
├── test_package/          # 包级冒烟（offscreen 启动 6s）
├── reports/               # conan-verify 报告 / W3 本地 CI 日志 / 测试报告
└── manifest.yaml          # 构建状态与依赖元数据
```

## 版本历史

| 版本 | 状态 | 说明 |
|---|---|---|
| 20.03.23 | built | 首次适配：qmake + Qt5 模块化栈，上游测试 4/4、鸿蒙特有测试 3/3 通过 |
