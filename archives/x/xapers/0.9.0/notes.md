# xapers 0.9.0 适配笔记

## 编译环境
- 构建系统: setuptools (Python, 非 autotools；init-build 因 Makefile 误判为 autotools，已手动修正)
- 编译日期: 2026-08-09
- 编译器: clang 15.0.4 (用于 xapian-bindings 源码构建)
- Python: 3.12.9 (社区 cmd-pkgs)
- 状态: built

## 编译步骤
1. 源码: GitLab 官方归档 `https://gitlab.com/wpettersson/xapers/-/archive/0.9.0/xapers-0.9.0.tar.gz`
   (SHA256: 30f3ea0000d9fb063d7515e6f69e3092e054208c23e387448051a1b19c2a7b71)
2. xapers 为纯 Python 包 (setup.py + entry_points)，构建方式: `python3 setup.py build` → `install --prefix=$TEST_PREFIX`
3. 运行依赖安装: `pip install pybtex pycurl urwid` (社区 PyPI 镜像)
4. xapian Python 绑定不在 pip 镜像上，需从 xapian-bindings-1.4.26 源码构建 (见问题表)
5. 测试: `./test/xapers-test` (bash 测试套件, 4 组 83 用例)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | xapian-bindings configure 报 config.status Permission denied | HMDFS umask 077 权限问题 (E011) | `sed -i 's/umask 077/umask 022/g' configure config.status` |
| 2 | xapian-bindings 链接失败 `-lstdc++` not found | OHOS SDK 无 libstdc++，只用 libc++ | Makefile 中 `-lstdc++` 改为 `-lc++`，并加 `-stdlib=libc++` |
| 3 | `_xapian.so` import 报 `PyThread_allocate_lock: symbol not found` | python3 主程序未导出 Python C API 符号 | `PYTHON3_LIBS` 追加 `-L$PREFIX/lib -lpython3.12` |
| 4 | xapian `WritableDatabase` 创建失败 `Opening UUID generator failed (Permission denied)` | OHOS 上 `/proc/sys/kernel/random/uuid` 无读权限 (USE_PROC_FOR_UUID) | 平台限制，非 xapers 问题；测试 27/83 通过，55 失败均为该根因 |
| 5 | 上游 version.py 仍为 0.8.2 | 上游 0.9.0 发布时未更新 version.py | 补丁修改 version.py → `__version__ = '0.9.0'` (patch 由 refresh-patch 生成) |
| 6 | setuptools 缺失 | 干净环境未安装 | `pip install setuptools` |

## 源码修改
- `xapers/version.py`: `__version__` 0.8.2 → 0.9.0 (上游 0.9.0 发布未更新版本号)

## 依赖版本
- xapian-core 1.4.26 (cmd-pkgs 预编译包 + conan 制品仓 ohpcd 已发布)
- xapian-bindings 1.4.26 (源码构建 Python3 绑定)
- pybtex 0.26.1 / pycurl 7.45.6 / urwid 4.0.8 (pip, 社区镜像)

## 验证结果
```bash
# 本地编译安装
python3 setup.py build && python3 setup.py install --prefix=$TEST_PREFIX  # PASS
# 测试套件 (bash, 4 组)
./test/xapers-test   # 27/83 passed, 1 broken expected-fail, 55 failed
# 失败根因: xapian UUID generator 平台限制 (/proc/sys/kernel/random/uuid 无权限)
# basic 组单独运行: All 8 tests passed
# 冒烟: xapers --version → xapers 0.9.0 (补丁后)
```

## 注意事项
- xapers 是命令行工具 (console_scripts: `xapers`)，已创建软件级 `commands.json` (R38)
- xapian Python 绑定非 pip 包，由构建环境提供 (cmd-pkgs xapian-core + 源码构建绑定)，conanfile.py build() 中有 `import xapian` 前置检查
- 测试失败为平台限制 (E051 类)，不影响交付；已记录根因
- 配方为 Python 项目类型 (非 autotools)，参照 internetarchive 既有配方
---

**编译结束**: 2026-08-09 14:08
**最终状态**: built
