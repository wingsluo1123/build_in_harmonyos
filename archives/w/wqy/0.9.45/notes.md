# wqy 0.9.45 适配记录

- **上游来源**：WenQuanYi Zen Hei 0.9.45（Fighting-state RC1），官方 SourceForge 归档 `wqy-zenhei-0.9.45.tar.gz`；归档 SHA-256：`e4b7e306475bf9427d1757578f0e4528930c84c44eaa3f167d4c42f110ee75d6`。归档 45 个条目，TTC 16,791,251 字节，SHA-256：`79c18ebe7b811951e8311bad7103ebeae8c337ed9988ea69e8a78a66cfe029b9`。
- **上游测试清点**：N=0。归档无 `test/`、`tests/` 目录和测试源码；Makefile 只定义 `deb`、`rpm`、`i18n`、`clean`，没有 `check`/`test`。仓库 census 脚本确认无上游测试文件；其 `make -n check` 探测因 Windows Git Bash 环境没有 GNU make 未执行，这一环境限制不计为测试失败，也没有伪造上游测试。
- **资源交付**：Conan 包不声明依赖、不编译、不安装到系统字体目录，也不注册全局 fontconfig。上游 `wqy-zenhei.ttc` 原样放在 `res/fonts/`；`COPYING` 放在 `licenses/`，`README` 和 `AUTHORS` 放在 `res/share/doc/wqy/`。README 包含 GPL v2 字体嵌入例外和第三方字形署名，文件保持原样。
- **字体面**：TTC 头记录 3 个 face：`WenQuanYi Zen Hei`、`WenQuanYi Zen Hei Mono`、`WenQuanYi Zen Hei Sharp`。README 描述了前两个 family；解析器从实际 TTC name 表读取并验证第三个 Sharp face，三个 face 的 `中文字体测试` 均为 6/6，glyph ID 均在有效范围内。
- **应用消费契约**：应用将 TTC 随 HAP 打包，在需要文件路径的 API 场景下复制到应用私有目录，再由应用自身加载/注册。该资源包不隐式提供设备级安装或全局字体可见性。配方使用 Conan 2.29.1 支持的 `package_type = "unknown"`（该版本没有 `none` 类型），并清空 package ID；其内容与消费契约仍是纯资源包。
- **Conan 消费者**：`test_package/consumer_ttc.py` 直接解析 Conan package 中的 TTC，核验 collection/table 范围、三个 family 名称、`maxp` glyph count、Unicode cmap 和六个中文码点；不依赖 fontTools 或其他运行库。`test_package/conanfile.py` 通过 `self.run()` 先执行五个标准库单元测试，再消费真实依赖包中的字体。
- **当前验证**：实际 HarmonyOS PC（HAD-W24，6.1.0.117 / API 23，aarch64）上运行 `finish wqy 0.9.45 built`。Conan 2.29.1 `conan create`、G1-G3 与嵌入的 W3 `setup.sh` + `build_and_test.sh` 均通过；消费者 5 个单元测试全过，解析真实 Conan 包内 TTC 的 3 个 face 均覆盖中文样本 6/6。设备侧 `OH_Drawing` 专项测试结果见下文与 `reports/test-report.md`。

## 发现与知识积累

- ✅ 无构建步骤的字体数据包可使用无 Conan 依赖的 `package_type = "unknown"`；保留官方 TTC 和原始许可/署名材料即可交付，应用自行加载，不安装设备级字体。(ref: manifest.yaml)
- ✅ Windows Conan 启动器不可用时，HarmonyOS PC aarch64 上的 Conan 2.29.1 可原生执行 `conan create`，并在同一设备上完成仓库规定的 W3 本地 CI。(ref: reports/conan-verify-report.md、reports/w3-local-ci.log)
- ✅ HarmonyOS 6.1 的 `OH_Drawing_TypefaceCreateFromFile` 可按 face index 0..2 加载该 TTC；通过 `OH_Drawing_CanvasDrawTextBlob` 实际绘制中文并检查 bitmap 非背景像素，可证明字体实际参与渲染。(ref: reports/test-report.md)

## HarmonyOS 真机验证

- **Conan / W3**：设备本机 `conan create`、Conan consumer 测试和 OHC `finish` 中的 W3 全部通过；Conan profile 为 `ohos-aarch64`。原始验证日志与脚本生成的 `.ci-result.json` 保存在 `reports/`。
- **OH_Drawing 实测**：使用 `test_package/harmony_tests/native_drawing_probe.cpp`，在 HarmonyOS 6.1.0.117 aarch64 上用本机 API 26 NDK 编译并直接运行。对 face 0/1/2 分别测得 6 个 UTF-8 字形、文本宽度 288，并各自产生 4,446 个非背景像素；进程退出码为 0。运行时未将 NDK stub 目录加入 RPATH，调用设备系统 `libnative_drawing.so`。
- **HAP 应用集成实测**：临时 HarmonyOS 工程将 `default` 产品绑定到本机已有 `default` 签名配置，Hvigor 构建成功，HarmonyOS SDK `hap-sign-tool verify-app` 校验签名通过。通过无线 HDC `10.54.246.164:8710` 在 OpenHarmony 6.1.0.115 aarch64 真机安装并启动 `org.openharmony.wqyfontprobe/EntryAbility`；应用将 TTC 复制到私有目录并用 OH_Drawing 绘制三个 face，各 face 检出 6 个中文字形和 288 个非背景像素，设备返回 `WQY_HARMONY_TEST_PASS=1/1`。测试后已卸载临时应用。
- **finish 收尾状态**：设备端 Conan、W3 与 G1-G3 通过；`finish` 仍因知识库全局完整性检查发现既有条目 E219/E253/E305 缺字段、临时验证快照没有 `origin/main` 基线导致 W2 将生成的 `SUMMARY.md` 视作框架变更，以及 submit 就绪预检缺少发布打包材料而报告 partial。未修改这些仓库基础设施或其他归档；这些问题不影响本包的 Conan/W3 和 OH_Drawing 实测结果。
