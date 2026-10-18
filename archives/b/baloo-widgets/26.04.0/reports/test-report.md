# baloo-widgets 26.04.0 本地验证报告（W3）

## 环境

| 项 | 值 |
|----|----|
| host/build profile | `ci/conan/profiles/ohos-aarch64` |
| 构建系统 | CMake + Ninja（ECM 6.26.0） |
| 目标平台 | aarch64-linux-ohos |
| conan | 2.29.x（OHOS 适配版），remote `ohpcd` |

## 编译验证

命令（与 CI 同构，强制重编本包以取得干净日志）：

```bash
conan create archives/b/baloo-widgets/26.04.0 -r=ohpcd --build=missing \
  --build=baloo-widgets/* -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

结果：**RC=0**（configure / build / package / test_package 全通过）；本轮日志
`reports/w3-local-ci.log`（`build_and_test.sh` 内 `Failed: 0`），conan-verify 报告
`reports/conan-verify-report.md`（G0-G4 全 PASS）。

产物（实测 `ls`）：`lib/libKF6BalooWidgets.so.26.04.0`（SONAME `libKF6BalooWidgets.so.6`，
另有 `.so` / `.so.6` 软链）、
`lib/plugins/kf6/propertiesdialog/baloofilepropertiesplugin.so`、
`lib/plugins/kf6/kfileitemaction/tagsfileitemaction.so`、
`include/KF6/BalooWidgets/Baloo/{filemetadatawidget,tagwidget,filemetadataconfigwidget,widgets_export}.h`、
`lib/cmake/KF6BalooWidgets/`。

### 产物 DT_NEEDED（L5b）实测结论

产物 `DT_NEEDED` 里有依赖包的构建机私有绝对路径（主库 6 条、两个插件各 4 条），
判据与处置见 notes.md 第 5 节：

- `build_and_test.sh` 的 L5b 对此打印 `[fail] ... DT_NEEDED 含绝对/相对路径`，但
  `L5_RESULT` 不进 `FAILED` 计数，最终输出 `Failed: 0`、`exit_code=0` → CI 不阻断。
- 已合入的 KF6 包（kbookmarks 6.28.0 `libKF6BookmarksWidgets.so` 3 条、kio
  `libKF6KIOFileWidgets.so` 16 条）同样如此，属整条 KF6 线的既成事实。
- 构建后改写 `.dynstr` 的方案**已实测证伪并回退**（改写后的 `.so` `dlopen` 报
  `Permission denied`，原样副本仅报缺 `LD_LIBRARY_PATH`），与 E537 禁止项一致。

## 上游测试用例（autotests，ctest，6 项全部执行）

| 用例 | 结果 | 依赖/原因 |
|------|------|-----------|
| extractortest | FAILED | 需 taglib 音频抽取器（mp3 Channels/SampleRate） |
| filemetadatadatedisplaytest | PASSED | — |
| filemetadataitemcounttest | FAILED | 需 taglib 音频抽取器（mp3 20 项属性） |
| filemetadatamergedatatest | PASSED | — |
| filemetadatawidgettest | FAILED | 需 taglib 音频抽取器（m4a artist）+ KDE shared-mime-info 文案 |
| widgetfactorytest | PASSED | — |

- 注册 6 / 执行 6 / 通过 3 / 失败 3（未跳过任何用例）
- 失败 3 项根因：已发布 `kfilemetadata/6.14.0` 不含音频抽取器
  （`lib/plugins/kf6/kfilemetadata/` 仅 document/image 抽取器），mp3/m4a 属性恒为空；
  另 `filemetadatawidgettest` 需要 KDE 版 shared-mime-info 文案（本环境无系统 KDE 文案库）。
- 门禁子集（不依赖音频抽取器，验证本包产物）：`filemetadatadatedisplaytest`、
  `filemetadatamergedatatest`、`widgetfactorytest` → **3/3 通过**（100%）。

## test_package（公开 API 消费者用例）

| 检查项 | 结果 |
|--------|------|
| FileMetaDataWidget 只读/日期格式/items/metaDataRequestFinished/配置模式往返 | PASS（10） |
| TagWidget 标签往返/只读/对齐 | PASS（4） |
| FileMetaDataConfigWidget items/sizeHint/save | PASS（3） |
| 临时目录与测试文件创建 | PASS（2） |

合计 **18 PASS / 0 FAIL**，Qt 使用 offscreen 平台。

## 结论

- 编译与打包通过，`test_package` 全绿。
- 上游 6 个用例全部执行，3 个因依赖包缺音频抽取器不可通过，已在 notes.md 与 PR 说明中
  给出具体技术原因与证据。

## 知识库扩展样例验证（knowledge/tools/kf6-relative-needed）

配方新增开关 `kb_compat_shim`（默认 `True`），用于对比"有/无兼容层"：

| 运行 | 命令 | 结果 |
|------|------|------|
| 关闭 SKILL | `reproduce.sh off`（`-o &:kb_compat_shim=False`） | ❌ conan create 失败，实测原文 `Error loading shared library ../../bin/libKF6ConfigCore.so: (needed by …/kconf7325dff05dfef/p/lib/libKF6ConfigGui.so)`；6 项 ctest 4 项 Failed |
| 开启 SKILL | `reproduce.sh on`（默认） | ✅ conan create RC=0；全量 3/6（3 项已知缺音频抽取器）、门禁子集 3/3 |

- 复现脚本无任何管道（规避 SIGPIPE），日志分别落 `reports/repro-off.log` / `reports/repro-on.log`，
  退出码即判定（off 需命中 loader 报错、on 需 RC=0）。
- 检测脚本对该 musl 措辞与 glibc 措辞均匹配（`LOG_RE` 三类分支，大小写不敏感）。
- 自测 `python3 knowledge/tools/kf6-relative-needed/test_relative_needed.py`：8/8 OK。
