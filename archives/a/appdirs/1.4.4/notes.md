# appdirs 1.4.4 — 适配笔记

## 概述
- 上游: https://github.com/ActiveState/appdirs (tag 1.4.4, 2020-05)
- 类型: 纯 Python 单模块库（`appdirs.py`，py_modules=["appdirs"]），无 C/C++ 代码
- 依赖: 零（仅 sys/os stdlib），PyPI requires_dist 为空
- SHA-256 (GitHub tag tarball): 6db10570b4f0176a05924c20745ff73385497e57829634fb3e756e15636ff408

## 适配要点
1. 纯 Python noarch → `package_type = "python-require"`，package() 用 shutil.copy2
   将 `appdirs.py` 拷贝到 `lib/python3.12/site-packages/`（同 python-magic/rich
   noarch 模式；pip/setuptools 构建在本环境不可用）。
2. 无需任何源码补丁：模块仅用 stdlib，Python 3.12 下无 import 障碍
   （unittest 已在 py2.7 分支处理 unittest2 回退，py3 直接用 unittest）。
3. package_info() 注入 runenv/buildenv PYTHONPATH（aiohttp 教训：只打印不够）。
4. R38: 无 console_scripts / scripts= / bin/ 产物 → 纯库包，不创建 commands.json。

## 上游测试
- 唯一测试源: `test/test_api.py`（unittest，Test_AppDir 类）
- 用例: test_metadata / test_helpers / test_dirs（3 个）
- 实测: `python3 -m unittest -v test.test_api` → 3/3 OK, rc=0
- 双口径: source_declared_total=3, configured_executable_total=3,
  executed_passed_total=3, failed=0, uninstantiated=0 → 3/3 = 100%

## 合规修正（2026-10-15，分支 fix/appdirs-1.4.4）
- 背景: recipe 已在官方仓 origin/main 树，但进仓时间早、从未被发布管线推送到
  ohpcd 制品仓；下游 lastversion/3.6.12 平台 CI 因 `Package 'appdirs/1.4.4'
  not resolved` 失败。本次 fix 基于最新 origin/main（bbb5e561f9）重建候选，
  完整通过权威 CI 后随合并发布（制品仓无此版本，first publish，R37 无占用）。
  **构建语义零改动**（单模块 copy2 + build() 内嵌 unittest 保持原样）。
- 体检与修正清单:
  1. 版本级 manifest.yaml 的 `verification.shadow_ci` / `device_test` 由
     pending 回填权威 CI 实测结果（旧记录止于 2026-09-20，无 CI 证据）。
  2. test_package/MANIFEST.yml 对齐现行批次台账格式（count 字段 + 复跑证据），
     并补登记 `test_ohos_appdirs.py`（conanfile test() 一直在运行它，台账漏
     登记）；assertion_count 修正为实数 22（test_appdirs 13 + test_ohos 9，
     其中 2 条为 XDG_CACHE_HOME 条件断言），旧值 15 为不准确的近似。
  3. conandata.yml 源 URL 规范化为小写 canonical 形式
     `https://github.com/activestate/appdirs/archive/refs/tags/1.4.4.tar.gz`；
     sha256 实算核验：本地 Windows 与设备 ohpc2 双侧下载实算均为
     6db10570…f408，与既有记录一致（未变源）。
  4. 版本级 manifest test_ledger 补 test_package 两条消费者/OHOS 专项条目；
     软件级 manifest key_points 补 OHOS 专项测试要点。
- 上游测试独立复跑（2026-10-15）: 设备隔离 venv
  （/storage/Users/currentUser/tmp/oh-device-porting-v2/testenv，Python
  3.12.9 + pytest 9.1.1）对官方 tag tarball 的 test/ 实测
  **3 passed / 0 failed（0.03s）**。上游 activestate/appdirs 已归档；套件仅
  依赖 stdlib，pytest 9.1.1 下收集/运行无弃用告警失败，无需 -W 兼容处理，
  oracle 未改动。证据: reports/dep-upstream/appdirs-upstream-rerun.log
- 权威 CI: ci/conan/build_and_test.sh（CI_PACKAGES=archives/a/appdirs/1.4.4，
  CI_BRANCH=fix/appdirs-1.4.4，profile ohos-aarch64）→ 1/1 全过，CI_EXIT=0
  （logs/ci-appdirs-120647.log）：G0/L0 全过（L0j 确认 first publish、L0k
  纯库免 commands.json、L0m/L0n 合规）、KC/JC 过、conan create 内嵌
  unittest 3/3 OK、test_package 消费者与 OHOS 专项双 PASS、L1e 破坏性
  负测过、L5 lib/ 有产物。CI 对 conandata.yml 的镜像改写已还原（E415）。

## 环境
- Python 3.12.9, Conan 2.x, profile ohos-aarch64
- /tmp 只读（E002）→ 临时目录用 $HOME/tmp

---

**编译结束**: 2026-10-15（合规修正复验）
**最终状态**: built
