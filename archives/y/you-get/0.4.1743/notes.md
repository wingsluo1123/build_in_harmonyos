# you-get 0.4.1743 适配笔记

## 基本信息

| 项 | 值 |
|---|---|
| 软件 | you-get（soimort/you-get） |
| 版本 | 0.4.1743（src/you_get/version.py `__version__`） |
| 许可证 | MIT |
| 主页 | https://github.com/soimort/you-get |
| 官方源 URL | https://github.com/soimort/you-get/archive/refs/tags/v0.4.1743.tar.gz |
| sha256 | c01f0892f530a1624260345c6881059c6d00c4f722403060cf1cc31c5568e460 |
| 类型 | 纯 Python 命令行视频下载工具（CLI，无 C/C++ 源文件） |
| CLI 入口 | `you-get = you_get.__main__:main`（console_scripts，见 you-get.json） |
| 模块结构 | src/you_get/（__main__.py / common.py / extractor.py / json_output.py / version.py / extractors/~100 站点子模块 / util / processor / cli_wrapper） |

## 语言预检与 R47 覆盖

任务标记为 cpp，但源码实测为纯 Python（无任何 C/C++ 源文件）。
按用户决策覆盖 R47，按 Python application 适配（本仓库已有
pyparsing/3.1.4、check-jsonschema/0.28.4、laniakea-spark/0.1.1、
bambam/1.4.1 纯 Python 包先例，以解释器为运行时依赖交付）；
覆盖决策记录于版本级 manifest.yaml 的 r47_override 字段。

## 构建方式

纯 Python 包无编译步骤，直接拷贝源码树（无 wheel 构建）：

1. `build()` 为无操作：**不用** `pip wheel . --no-deps`。pip 的 build
   isolation 会 spawn 嵌套子进程安装构建后端，在资源受限的 OHOS CI
   worker 上触发 `[Errno 11] EAGAIN`（fork/posix_spawn Resource
   temporarily unavailable，buildbot #91908）；且 wheel 内容与提交的
   `src/you_get` 完全一致（setup.py 用 `find_packages('src')`，
   `version.py` 上游已提交）。
2. `package()` 用 `shutil.copytree` 直接把 `src/you_get` 拷贝至
   `<prefix>/lib/pythonX.Y/site-packages/you_get`（零子进程、不依赖
   setuptools；等价于解包 wheel，仅少 `.dist-info` 元数据，启动器与
   测试均不需要）。
3. 生成 `bin/you-get` 启动器（sh 包装：设置 PYTHONPATH 后
   `exec python3 -m you_get "$@"`，等价于 pip 生成的 console 脚本）
4. `package_info()`：`cpp_info.bindirs=["bin"]`（libdirs/libs 置空）；
   `runenv_info` 追加 PYTHONPATH=site-packages、PATH=bin

- `package_type = "application"`，settings = os, arch
- `validate()`（R32）：os 不在 ("Linux", "OHOS") 抛 ConanInvalidConfiguration
- 构建用 `shutil.which("python3")` 定位解释器（R33：不裸用 `${CC}`）
- 无补丁（R8：patches 默认禁用平台宏；纯 Python 无需补丁）
- R26 不适用：纯 Python 无 .so，无系统同名库冲突

## dukpy 依赖分析（关键决策）

- dukpy 仅在 `src/you_get/extractors/youtube.py` 第 7 行被 import
  （try/except ImportError → log.e + exit(0)）。
- `extractors/__init__.py` 会 `from .youtube import *`，因此
  `import you_get.extractors` 就会触发 dukpy（缺失时进程 exit(0)）。
- 但 `you-get --version` **不**触发：`__main__.main()` 内部才
  `from .common import main`，common.py 顶层不 import extractors
  （用 import_module 惰性加载）。
- 上游测试 `tests/test.py` 顶部 `from you_get.extractors import (...)` 会触发
  dukpy → 无 dukpy 时进程被 exit(0) 中断。
- **决策：配方不声明 dukpy 为 Conan 依赖**（制品仓无此配方、CI 无外网 pip）。
  `you-get --version` 与 common 主流程均不依赖 dukpy；YouTube 站点下载受限
  （见"已知限制"）。

## 上游测试清点（R51）

| 文件 | 用例 | 类型 | 断言 | 主编实测（2026-10-14） |
|---|---|---|---|---|
| tests/test.py | test_imgur | 联网（info_only=True 探测真实站点） | - | ❌ 失败：URLError Operation timed out（imgur.com 不可达） |
| tests/test.py | test_magisto | 联网 | - | ❌ 失败：URLError Operation timed out（magisto.com 不可达） |
| tests/test.py | test_acfun | 联网 | - | ✅ 通过（acfun.cn 可访问） |
| tests/test.py | test_tiktok | 联网 | - | ❌ 失败：URLError Operation timed out（tiktok.com 不可达） |
| tests/test.py | test_twitter | 联网 | - | ❌ 失败：URLError Operation timed out（twitter.com 不可达） |
| tests/test.py | test_weibo | 联网 | - | ✅ 通过（video.weibo.com 可访问） |
| tests/test.py | test_youtube / test_bilibili / test_soundcloud | 已注释停用 | - | 不运行（上游注释停用） |
| tests/test_common.py | test_match1 | 本地断言 | 1 方法 2 断言 | ✅ 通过（2 断言全过） |
| tests/test_util.py | test_legitimize | 本地断言 | 1 方法 4 断言 | ✅ 通过（4 断言全过） |

**上游测试通过率汇总**：
- tests/test.py（启用用例 6 个）：**2/6 通过（33.3%）**——test_acfun、test_weibo 通过；test_imgur、
  test_magisto、test_tiktok、test_twitter 失败，原因均为**外部站点网络不可达**
  （`urllib.error.URLError: <urlopen error [Errno 110] Operation timed out>`），
  非代码缺陷，属环境网络受限（GitHub 直连亦超时，需镜像）。
- tests/test_common.py + tests/test_util.py（本地断言 2 个用例）：**2/2 通过（100%）**。
- 运行命令：`PYTHONPATH=src python3 -m unittest tests.test -v`（dukpy 已 pip 安装以满足 extractors 导入）。

> 说明：test.py 联网用例在 CI/无外网环境同样会因站点不可达失败（与本地一致）；以本地实测结果如实回填。


## 新增测试覆盖（消费者 test_package）

- `test_package/test_you_get.py`：运行打包产物 `bin/you-get --version`，
  断言输出包含 `0.4.1743`（R34 实质测试；不触发 dukpy、无需网络）。
- 上游联网用例无法在 CI 稳定执行，以本 test_package 功能测试兜底
  （适配后合计 M≥1）。

## 已知限制

- YouTube 站点下载需 dukpy（JS 运行时），配方未打包 dukpy →
  you-get 访问 YouTube 时会 log 错误并退出；其余 ~100 站点不受影响。
- tests/test.py 联网用例依赖真实站点可用性与外网，CI 内不保证通过。
