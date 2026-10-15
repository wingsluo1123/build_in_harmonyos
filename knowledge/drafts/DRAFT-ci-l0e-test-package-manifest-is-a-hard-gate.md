# draft-ci-l0e-test-package-manifest-is-a-hard-gate

## 症状

PR 的 CI 在 **L0 质量门禁**就失败，构建立刻中断（后面 L1/L2/L4/L5 全部 `skip: blocked_by_L0`）：

```
[step] L0: Quality gate checks...
[fail] L0c: No test source files in test_package/      # 变体
[fail] L0e: test_package/MANIFEST.yml missing — upstream test declaration required
```

实际案例：qtsensors/6.11.1 与 qtconnectivity/6.11.1 两个 Qt 附加模块 PR 均因此挂掉——
配方、test_package 源码、conanfile 全都对，**只差一个 `test_package/MANIFEST.yml`**。

## 根因

`ci/conan/build_and_test.sh` 的 L0 门禁里，`test_package/MANIFEST.yml` 是**硬性存在性检查**
（L0e：声明上游测试来源）。没有这个文件，无论代码多正确都过不了 L0。

## 修复：按模块类型写 MANIFEST

仓库里已有两套成熟写法，照抄即可。

### 情形 A：上游有测试、但在本平台不可运行（平台限制）

```yaml
# test_package/MANIFEST.yml
package: <name>/<version>
homepage: "<upstream homepage>"

upstream_check_command: "<ctest/make check 命令，或空>"
upstream_test_in_build: true|false
upstream_test_command: "<在 build() 里执行的命令>"

upstream_test_exemption:            # 关键字段：豁免必须给出 rule + reason
  rule: "platform_limitation"
  reason: "<为什么不可运行，例如无 HAL/后端；功能覆盖由 test_package 承担>"

upstream_tests:                     # 逐文件列出上游测试，便于复核
  - file: "tests/auto/.../tst_x.cpp"
    source: "<upstream tarball 内路径>"
    description: "<覆盖面>"
    command: "<实际命令，或“不可运行（平台限制）”>"

test_package_tests:
  - file: "test_package/test_x.cpp"
    description: "<消费者视角验证了什么>"
    command: "conan test"

assertion_count: N
```

实测例子：
- qtsensors：`_upstream_test_targets = ("tst_qsensor",)`，配方在 `build()` 里尽力构建该目标
  （失败仅告警），由于 OHOS 无传感器 HAL，设备类用例不可运行 → `platform_limitation` 豁免。
- qtconnectivity：上游蓝牙/NFC 测试全依赖真实硬件与 BlueZ/PCSCLite/neard 后端
  （三者特性均显式 OFF、Qt 用树内 dummy 后端）→ 配方不构建上游套件，同样 `platform_limitation`。

### 情形 B：上游根本没有测试套件

```yaml
upstream_check_command: ""
upstream_test_in_build: false
upstream_test_exemption:
  reason: "上游不提供测试套件（sdist 无 tests/）"
```

参考 `archives/q/qt-unixodbc/5.15.2/test_package/MANIFEST.yml`（同一字段结构）。

## 判据小结

| 现象 | 结论 |
|---|---|
| CI 输出 `L0e: test_package/MANIFEST.yml missing` | 文件不存在，与代码无关 |
| `L0c: No test source files in test_package/` | test_package 里没有真实测试源码 |
| L1/L2/L4/L5 全是 `skip: blocked_by_L0` | 都是被 L0 挡住，不必去查后面几层 |
| `upstream_test_exemption` 缺 `rule`/`reason` | 豁免声明不完整，复核时会被追问 |

**提交前自查**：`ls test_package/` 必须看到 `MANIFEST.yml`，且里面的上游测试声明与
`conanfile.py` 里实际执行的命令一致（否则属于声明与实际不符）。
