# yte 1.5.4 适配笔记

## 编译环境
- 构建系统: custom（纯 Python 包，package_type=python-require，无 C/C++ 编译）
- 编译日期: 2026-10-14
- Python: 3.12.9（/storage/Users/currentUser/usr/local/bin/python3，绝对路径钉定）
- 状态: published

## 编译步骤

1. `ohc-run.py init-build yte 1.5.4`：拉取 github tag v1.5.4 源码
2. `conan-init` 生成配方骨架后改写：package_type=python-require，
   package() 把 `yte/` 模块拷入 `<pkg>/lib/python3.12/site-packages/yte/`
3. `build()` 内 pip vendoring（pypi.cnb.cool 镜像，DRAFT-10175 先例）：
   `pip install --no-input --no-deps --target <src>/_pydeps
   plac==1.4.3 dpath==2.2.0 pyyaml==6.0.2`
4. `pytest --co tests.py` 收集上游测试数（42 个测试函数）
5. `conan-verify` + `finish published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pip 报 `_posixsubprocess` ImportError / test 期 `math` 缺失 | conan buildenv 的 LD_LIBRARY_PATH 指向 hnp SDK llvm lib，劫持 CPython 扩展模块加载 | pip 与 test_package 均以 `env -u LD_LIBRARY_PATH -u PYTHONHOME -u PYTHONPATH` 前缀执行 |
| 2 | hnp python3 的 pip 对 pyyaml 6.0.2 报 versions: none | 镜像上是 cp312-ohos_aarch64 专用轮子，hnp python3 自带旧 pip 不识别 | pip 全部钉定 /storage/Users/currentUser/usr/local/bin/python3 |
| 3 | plac 1.3.5 import 失败：No module named 'asyncore' | Python 3.12 移除 asyncore，plac 1.3.5 的 plac_ext 直接 import | 换 plac 1.4.3（满足上游 poetry 约束 ^1.3.4，兼容 3.12） |
| 4 | plac/dpath 未发布制品仓 | R36 依赖缺口（resolve-deps 对 Python 级依赖误判"已就绪"） | pip --target vendoring 进包（DRAFT-10175 先例），notes/MANIFEST 披露 |

## 依赖

- 运行期（随包 vendoring）：plac 1.4.3、dpath 2.2.0、pyyaml 6.0.2（均为纯 Python wheel）
- 消费者若自带同名包，本包 site-packages 版本优先；冲突处置见 test_package/MANIFEST.yml

## 验证结果

- conan-verify：G0-G4 全绿（G2 conan create + test_package EXIT=0）
- test_package：真实 API 断言 2/2（`?for` 循环展开精确匹配 + 纯 YAML 透传）
- 上游测试：42 个 pytest 测试函数（tests.py），conan create 期 `--co` 收集

## 结束

最终状态：published（本机 W3 全绿；test_package 消费者断言 2/2 通过；
制品发布与 CI 原生测试由提 PR 后的 CI 流水线完成）。

---

**编译结束**: 2026-10-14 04:20
**最终状态**: published
