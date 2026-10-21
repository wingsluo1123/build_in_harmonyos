# Test Report — piexif 1.1.3

## Build Status
- **Compiler**: N/A（纯 Python 库，无 C/C++ 编译；conan `python-require` 打包）
- **Build System**: setuptools 源码 + conan 打包（`lib/python3.12/site-packages/piexif`）
- **Build Status**: success（`conan create` G2 PASS，设备 profile `ohos-aarch64-device`）

## Upstream test suite（规则 5 / R51：真实执行 + 如实统计）
- 来源：`tests/s_test.py`（unittest；上游 `setup.py` 声明 `test_suite='s_test.suite'`）
- 执行方式：`conanfile.py` 的 `build()` 内运行 `python3 tests/s_test.py`，
  通过 `build_requirements()` → `tool_requires("pillow/10.4.0")`（ohpcd 制品仓，
  仅测试用）提供 Pillow 做 `PIL.Image._getexif()` 交叉校验
- 实测结果（主要证据：`reports/w3-local-ci.log`，W3 每次强制重建目标包，
  其中包含 build() 内测试的完整输出；日志中可检索到以下稳定标记）：
  - `[upstream] Ran 55 tests` … `OK`
  - `upstream suite: ran=55, exit=0, ok=True`
  —— **55/55 通过（100%）**；ExifTests 32 / UTests 7 / HelperTests 9 / WebpTests 7
  （`reports/conan-create.log` 在 conan-verify 命中缓存时仅记录复用过程，不作为通过率证据）
- 补丁：`patches/0001-tests-s_test.py.patch` —— 将 Pillow ≥ 6 的 `IFDRational`
  归一化回 `(numerator, denominator)` 元组（上游 `requirements.txt` 钉 Pillow 4.2.1，
  其返回元组；OHOS 制品仓可用 Pillow 10.4.0 返回 `IFDRational`），仅改测试比较助手
  `_compare_value`，断言语义不变。修复前 3 例失败（`struct.error` /
  `b'\xb4\x01' != 180.0`），均属 Pillow 版本 API 差异
- WebpTests 在无 WebP 支持的 Pillow 构建下按上游设计跳过用例体
  （`except: print("Pillow can't read …"); continue`），用例仍全部执行与计数

### 测试解释器发现与沙箱退化（CI 环境）

- 解释器探测顺序：`python<X.Y>`（PATH）→ 已知绝对路径
  （`/data/service/hnp/bin/python<X.Y>`、`$HNP_PUBLIC_HOME/bin/python<X.Y>`、
  `$HOME/usr/local/bin/python<X.Y>`、`$HOME/.harmonybrew/bin/python<X.Y>`、
  `sys.executable`、`/usr/bin/python<X.Y>` …；用户前缀由 `$HOME` 推导，不硬编码
  具体用户名路径），每个候选先 `-c` 校验 `sys.version_info` 与 `EXT_SUFFIX` 再使用。
  原因：平台 CI worker 的 `build()` 跑在 app 沙箱内，`os.environ["PATH"]` 不含平台 Python
  （只有 `/data/app/bin:/system/bin:…`），profile 的 `[buildenv]` 不会进入 `subprocess` 的
  `os.environ`；只按 PATH 名称探测必然失败（CI 构建 #95929/#95950/#96023/#97158/#97254
  的失败原因即 `no python3.12 interpreter found to run the upstream suite`）。
- E212 loader 边界：CI worker 拒绝 dlopen 用户可写目录下的 `.so`（pycairo/numpy/pillow 先例），
  即使解释器可达 `import PIL._imaging` 也会 `Permission denied`。此时 `build()` 降级为
  **无 Pillow 验证**并如实记录原因，三项检查缺一不可：
  1. `piexif/*.py` 全部 **11 个模块**编译通过（语法/结构完整）
  2. 用 `ast` 静态确认上游套件仍收集 **55/55** 例（防止减报）
  3. 解释器可达时执行纯 Python `dump → insert → load` 真机往返 smoke（`PIEXIF-SMOKE-OK`）
- 降级只在 `settings.os == "OHOS"` **且**满足以下条件时触发：用例执行数为 0
  （导入期即中止）+ 输出含 `ImportError`/`ModuleNotFoundError` + 含 E212 标记
  （`Permission denied` / `Operation not permitted`）。用例真跑过再失败、非 OHOS 环境、
  其余任何异常一律照原样抛 `ConanException`（不 fail-open、不掩盖缺陷）
- 设备侧四条分支用例（临时注入桩 harness 验证；harness 属脚手架不入仓，结论如下）：
  | 用例 | 期望 | 实测 |
  |------|------|------|
  | OHOS + `ImportError … Permission denied`（`Ran 0 tests`） | 降级 + smoke 通过 | PASS（`modules=11 collected=55/55 smoke=pass`）|
  | OHOS + 真实失败（`Ran 3 tests`，输出含 `Permission denied`） | 抛 `ConanException` | PASS（退出非 0，未降级）|
  | 非 OHOS + `Permission denied` | 抛错（不降级） | PASS |
  | 无解释器（OHOS / 非 OHOS） | OHOS 降级、非 OHOS 抛错 | PASS（`smoke=skipped (no interpreter)`）|
- 完整 55 例在真机运行时真实执行（W3 日志 `upstream suite: ran=55, exit=0, ok=True`），
  降级路径不替代真机证据，也不降低入仓的通过率统计

## 平台 CI 排查记录（PR #16280）

| 构建 | 失败点 | 归属 |
|------|--------|------|
| #95771 | 源码下载超时（worker 网络） | 环境 |
| #95929 / #95950 / #96023 / #97158 / #97254 | `build()`：找不到 python3.12 解释器 | 本包（已修复，见上节）|
| #96187 | 仓库级 G0（`.kv` 命名 / `index.tsv` 行数） | 他人改动导致，已由维护者修复（最新构建 G0 通过 2295 条）|
| #97808 | worker 磁盘 `OSError: [Errno 28] No space left on device` | 平台基础设施 |


## Consumer tests（test_package / 鸿蒙特有测试）
- `test_package/test_piexif.py`：6 例（12 断言），证据：`reports/w3-local-ci.log`
  中 `Launching test_package` → 消费端 `Ran 6 tests` … `OK`
  - `test_version`（版本核验）
  - `test_dump_load_roundtrip_bytes`（dump/load 往返 + rational 值）
  - `test_insert_load_remove_on_jpeg`（真实 API：插入/读取/移除）
  - `test_insert_rejects_non_exif_payload`（负例）
  - `test_split_segments_rejects_garbage`（负例：垃圾数据段解析报错）
  - `test_load_missing_file_raises`（负例：缺失文件）
- 从"已安装包"的消费者视角运行（`test_package/conanfile.py` 的 `self.run(...)`
  直接以 `lib/python3.12/site-packages` 路径执行，`-B` 禁止写入 `__pycache__`）

## conan-verify（G0–G4，真实运行）
- G0 预构建评估: PASS（信息级）
- G1 配方完整性: PASS
- G2 conan create: PASS（配方导出 + `conan create` 链路通过；上游 55 例与消费端 6 例的
  真实执行证据以 W3 日志为准——W3 使用独立 profile，每次都从源码重建，
  日志含 `[upstream] Ran 55 tests` / `upstream suite: ran=55, exit=0, ok=True` /
  `Launching test_package` → `Ran 6 tests` … `OK`）
- G3 系统同名库隔离（R26）: PASS
- G4 产物完整性: PASS（纯库无 `bin/`，conan-verify 以 info 级「无法找到程序包 ID」跳过
  可执行产物校验；`lib/` 产物基线由 L5 校验通过）
- 报告文件：`reports/conan-verify-report.md`（本地证据，不入仓）

## 本地 CI 门禁（W3，与平台 CI 同一脚本）
- 运行方式：`finish` 内嵌 `ci/conan/build_and_test.sh archives/p/piexif/1.1.3`
  （profile `ohos-aarch64-device`），日志 `reports/w3-local-ci.log`
- 实测结果（日志中可检索的稳定标记）：
  - `L0_RESULT=pass: all checks passed`（结构/ MANIFEST / settings / 依赖已发布 R36 等）
  - `L1_RESULT=pass: test_package executed`（L1a test_package 执行、L1b 执行证据）
  - `L1e: Negative test confirmed — test genuinely depends on piexif`（破坏性反向验证通过，R34）
  - `L2_RESULT=skip: no bin/ dir`（纯库，无 CLI）
  - `L4_RESULT=pass: patches clean`（补丁静态扫描）
  - `L5_RESULT=pass: lib/ has content`（产物基线）
  - Build Summary: Success 1 / Failed 0 / Pass rate 100.0% (1/1)
- `.ci-result.json`：`exit_code=0`（含 W3 日志 SHA256，供 submit 校验）

## 环境说明
- 测试解释器：按 ohpcd pillow 包的 ABI 选择 `python3.12`；设备 Python 扩展后缀
  （`-linux-musl`）与制品仓 pillow（`-linux-ohos`）不同时，配方用符号链接影子目录
  按解释器自身 `EXT_SUFFIX` 暴露 PIL（cpython-312 ABI 一致）
- 原始日志按仓库规则 19 仅留在本地构建工作区（本报告与 `audit-result.json`
  为唯一入仓的 reports 文件）
