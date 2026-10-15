# 静态产物校验必须钉住产物数量：否则 L1e 反向验证在「少装一个产物」上空转

> 草稿 ID：`DRAFT-static-artifact-count-pinning`
> 来源任务：scikit-learn 1.6.1 HarmonyOS PC（OHOS aarch64）适配，`archives/s/scikit-learn/1.6.1/test_package/`
> 来源 PR：`feat/scikit-learn-1.6.1`
> 归档证据：`test_package/test_ohos_platform.py::EXPECTED_EXTENSIONS`、`notes.md`「破坏性反向验证（L1e）」表 D1–D5、`reports/test-report.md` §3.5

## 适用场景

E212（hmmac 安全标签拒绝 dlopen 用户路径 `.so`）或运行期依赖在 worker 上不可得时，`test_package` 只能退回
**静态校验通道**：不导入扩展，而是逐个解析 ELF（`EM_AARCH64`、`.codesign` 段、`DT_NEEDED` 含 `libpython3.12.so*`、
只链 musl `libc.so`、ABI tag == 本机 `EXT_SUFFIX`）并校验 site-packages 布局。

这类通道几乎都是「枚举产物 + 逐文件断言」的写法。本条讲的不是「要不要有静态通道」（`DRAFT-rapt-ble-0.1.2-native-wheel-closure-e212-probe-fallback`
已经给出结论：要有），而是**这个通道自身怎么变成假绿**。同样的形状也出现在安装后布局校验、插件打包校验、
批量签名校验，以及任何用 `glob` 结果当分母算通过率的脚本里。

## 现象与原因

scikit-learn 1.6.1 的 6 项静态检查最初这样写：`_extensions()` 用 `os.walk` 收集 `sklearn/**/*.so`，
然后对每个 `.so` 断言 5 个 ELF 性质 + 1 个布局性质。做 L1e 破坏性反向验证时，按预期「移走一个扩展就该失败」，
实测结果却是：

| 注入的缺陷 | 期望 | 初版实际 |
|---|---|---|
| D5：只移走 1 个扩展（`cluster/_k_means_lloyd…so`） | 至少 1 项失败 | **6 项静态全绿**，日志写 `67/67 全绿` |

根因是量词齐全但没有计数：所有断言都是**全称量词**（每个产物都满足性质），没有任何**下界断言**（产物总数等于
已知值）。集合由被测对象现场枚举出来，装少了只是让循环少跑一轮——分母跟着缩，通过率反而仍是 100%。
CI 侧的门禁（`conan create` 退出码、L0/L1 日志痕迹、L5 产物非空）同样只看「有没有」「日志好不好」，
不区分「68 个全在」和「68 个缺 1 个」。

最坏的后果不是漏报一个包，而是**反向验证失去判别力**：评审最想确认的缺陷形态恰是产物缺失/漏装/漏签名，
而注入它不产生任何失败信号。

## 处理方法

1. **权威数量来自构建系统，不来自当前安装结果**。meson 对本项目声明 `Build targets in project: 111`，
   其中展开为 68 个扩展模块（`ninja [251/251]` 与产物树里 68 个 `.so` 对齐）。把它写成测试脚本的模块常量：

   ```python
   EXPECTED_EXTENSIONS = 68
   ```

2. **断言放进发现函数内部**，而不是某一条检查里——这样所有依赖枚举的检查天然继承同一临界条件，
   不存在「只有一条会失败」的漏洞：

   ```python
   def _extensions(site_dir):
       sos = [...os.walk(site_dir/sklearn, *.so)...]
       assert len(sos) == EXPECTED_EXTENSIONS, (
           "expected %d compiled extensions under %s, found %d — a partial install "
           "(or a dropped artifact) must fail here, not pass at a lower count")
       return sos
   ```

3. **让计数进证据链并与配方对账**：脚本 `--json` 输出 `discovered/passed/failed` 与实际枚举数；
   `test_package/conanfile.py` 按通道校验 `discovered == expected`（live 12+9、静态 6），并把
   `extensionsVerified` 写进 `HMBS_TEST_PACKAGE_RESULT=` marker，不符即 `ConanException`。
4. **让文档读同一个常量**：MANIFEST/测试报告生成器用正则取脚本里的 `EXPECTED_EXTENSIONS`，再与真实
   `glob` 结果 `assert` 相等，归档数字就不可能与产物漂移。
5. **用它反证自己**（两条都要跑）：完整包复跑全绿（本例静态 6/6、`--runtime` 9/9），注入缺陷必失败
   （移走 1 个 → 6 项静态全部 `failed=6`，并点名数量）。

## 验证与边界

- 2026-10-14 真机（HarmonyOS PC aarch64、CPython 3.12.9 musl）实跑，在包产物副本上注入 D1–D5：
  钉数量之前只有 D1–D4 能失败（删除签名段/改 ABI tag/删 `__init__.py`/移走全部扩展），D5 假绿；
  加入 `EXPECTED_EXTENSIONS` 后 **D5 使 6 项静态全部失败**，完整包复跑仍为静态 6/6、运行期 9/9，
  `conan create` 与 `conan-verify`（G1–G4）均退出码 0。
- 反例（本条要防的两种偷懒写法）：
  - 分母用现场枚举：`f"{ok}/{len(sos)} all good"` —— 产物越少分母越小，通过率越高。
  - 期望值取自实测：`EXPECTED = len(glob(...))` —— 变成恒等式，看起来钉了数，实际什么都没钉。
- 边界：钉住的必须是**该版本该平台**的真实产物数。跨平台/跨版本产物集合可能不同（可选扩展、平台专属模块），
  此时应按平台分支给出期望数，或改用「完整清单集合相等」的回退方案；不要用「至少 N 个」这类下界，
  它对「多装」和「装错」同样无感。
- 计数只是下界的一半：本例每条检查仍逐个解析 ELF 的真实字段，`EXPECTED_EXTENSIONS` 负责让「少了」暴露，
  逐文件断言负责让「错了」暴露，两者缺一都会留下假绿面。

## 关系

- 相关草稿：`DRAFT-rapt-ble-0.1.2-native-wheel-closure-e212-probe-fallback`（何时该退回静态通道）、
  `DRAFT-tool-fork-external-false-green-verification`（fork 外部程序型假绿，机制不同但同为「判据不覆盖失效面」）、
  `DRAFT-box2d-2.4.1-ctest-empty-suite-false-pass`（空套件返回成功）。
- 适用组件：Conan `test_package` 静态校验通道、安装后布局/签名批量校验、以及上游测试计数聚合
  （`collected == passed + failures + errors + skipped + xfailed` 的可核对恒等式）。
- 验证记录：以 OHPCD scikit-learn 1.6.1 对应 PR 的最新机器人 CI 与 `test_package` marker 为准。
