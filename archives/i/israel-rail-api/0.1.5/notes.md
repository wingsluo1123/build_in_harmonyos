# israel-rail-api 0.1.5 — 适配笔记

## 上游测试清点(W2 申报表)

- 上游测试目录:`tests/`(2 个文件)
- 测试框架:unittest(标准库,无第三方 runner)
- 文件清点:
  - `tests/test_api.py` — 6 个用例
  - `tests/test_train_station.py` — 1 个用例(注:`failed_station_lookup` 未以 `test_` 开头,unittest 不收集,上游自身问题,未修改)
- **上游测试合计:7 个用例**

## 上游测试实际执行(W2 执行证据)

- 命令:`PYTHONPATH=<包 site-packages>:<依赖 site-packages> python3 -m unittest discover -s tests -v`
- 执行目录:sdist 解压源码目录(temp/israel-rail-analyze/israel_rail_api-0.1.5)
- 退出码:0
- 结果:**总数 7,通过 7,失败 0,跳过 0**
- 日志:`logs/israel-rail-api-upstream-test.log`
- 用例明细(全部 ok):
  1. test_api.ApiTest.test_request_args
  2. test_api.ApiTest.test_setup
  3. test_api.TrainRoutePartTest.test_departure_delay_empty_list
  4. test_api.TrainRoutePartTest.test_departure_delay_matching_station
  5. test_api.TrainRoutePartTest.test_departure_delay_missing_key
  6. test_api.TrainRoutePartTest.test_departure_delay_no_matching_station
  7. test_train_station.ApiTest.test_station_lookup
- 说明:test_package 消费测试不替代上游测试统计;上游测试为离线单测(不访问网络),与 OHOS 平台无关。

## 适配过程中的问题与修复

1. **build()/package() 自检 ModuleNotFoundError: No module named 'chardet'**
   - 首个错误:`requests/__init__.py: import chardet` 失败(exit 1)
   - 根因:conan 依赖包(纯 Python 布局)的 site-packages 不在自检 python 进程的 sys.path
   - 修复:配方新增 `_dep_site_packages()` 收集全部 host 依赖 site-packages 注入 sys.path;重新验证 EXIT=0
2. **test_package 导入 `conan.tools.build.run` ImportError**
   - 根因:conan 2.29 无此导出
   - 修复:改用 `self.run()`;EXIT=0
3. **test_package 第二次失败 ModuleNotFoundError: 'israelrailapi'/'chardet'**
   - 根因:①目标包 site-packages 未插入 sys.path;②requests 传递依赖在 test 图中被 skip 未物化
   - 修复:sp+paths 全部插入;test_package 显式 requires chardet/5.2.0、idna/3.18、urllib3/2.7.0;EXIT=0
4. **G1 门禁:export_sources() 缺失 / 补丁调用缺失 / MANIFEST.yml 缺失**
   - 修复:加空 export_sources()、source() 中 apply_conandata_patches()、补 test_package/MANIFEST.yml 与 consumer 测试文件;重跑 conan create EXIT=0、conan-verify 全部 PASS

## 版本选择说明

- conan 依赖用远端 ohpcd 实际存在的 `requests/2.22.0`、`pytz/2026.3.post1`(conan download EXIT=0),非 PyPI 最新版;requests 2.22.0 运行时用 chardet 而非 charset_normalizer,依赖树与依赖分析报告的 wheel 层拓扑不同,属 conan 配方体系差异,无阻塞。
- 运行时有一条 `RequestsDependencyWarning: urllib3 (2.7.0) or chardet (5.2.0) doesn't match a supported version!`,为 requests 2.22.0 对新版依赖的版本声明警告,功能不受影响(全部测试通过)。
