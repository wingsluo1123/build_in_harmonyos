# mps 0.20.16 适配笔记

## 上游信息

- 名称：mps
- 版本：0.20.16
- 仓库：https://github.com/np1/mps
- 源码：https://files.pythonhosted.org/packages/a4/16/aaf6a3b6bd899ba963617889b59671ac176d58e555810ddcae5861049cfa/mps-0.20.16.tar.gz
- sha256：ad4b01cb4c9eafeae0573632829a4e6cb6bfcf11c974214e40480f9d8f6aaf64
- 许可证：GPL-3.0-only（PyPI 分类 GPLv3）
- 构建系统：setuptools（纯 Python，无 C 扩展）
- 内容：mps_pkg/__init__.py、mps_pkg/main.py（约 62 KB）、setup.py 入口 `mps = mps_pkg:main.main`

## 编译环境

- 平台：HarmonyOS aarch64（OHOS 6.0，原生构建）
- 工具：python3（真机 conan profile 提供）、setuptools（构建期 pip 安装）
- 状态：built（待真机 rule4 门禁验证后由 HMBS 提交）

## 编译步骤

```bash
python3 -c "import setuptools" || python3 -m pip install --break-system-packages setuptools --quiet
python3 setup.py build      # cwd=source_folder
python3 setup.py install --prefix=<package_folder>  # cwd=source_folder
```

## 上游测试审计结论

实拉 PyPI sdist 逐文件审计（14 个条目）：无 tests/test 目录、无 test_*.py、无 pytest/unittest 注册，
setup() 无 tests_require/test_suite。结论为上游确实无测试，MANIFEST 声明
`upstream_tests_exist: false`、`upstream_test_total: 0`（口径 python_def），
配方 build() 与 test_package 均输出 `status: no_tests` 证据标记。

test_package 用 6 个消费者检查覆盖真实 API：版本元数据、包导入、Config 默认值、
文件名清洗、zlib/pickle 往返、utf8 编解码。mps 二进制为交互式 CLI（无参进入
prompt），验证时只检查 `bin/mps` 文件存在，不直接执行，避免非 tty 挂起
（buku 先例）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 是否需要声明 mplayer 依赖 | 上游 README 要求 mplayer/mpv 做播放 | 播放器为外部运行时可选件，非 Python import 依赖，不进 conan requires；notes 如实记录 |
| 2 | setup.py 在 Python 3.12 下是否可用 | sdist 先 try setuptools 再回退 distutils | 先探测 import setuptools，已有则零改动；缺失时以 --break-system-packages 做构建期一次性补齐（PEP 668 合规），保证主分支可用；distutils 已移除，回退分支不依赖 |
| 3 | 真机 PEP 668 拒绝裸 pip 装 setuptools | Homebrew 系 python 报 externally-managed-environment | 同上：探测优先 + --break-system-packages，旧 pip 回退为普通 pip install |
| 4 | 真机 test_package 报 bin/mps 缺失 | `setup.py install --prefix` 在不同解释器下脚本落点不一致（bin 与 local/bin 等方案差异） | package() 后在包内全树搜索已安装的 `mps` 脚本并归位到 bin/；全树无脚本时按真实入口 `mps_pkg.main:main` 生成等效 wrapper（非桩），chmod 失败容忍（HMBS_CAP_CHMOD=0） |
| 3 | 交互式 CLI 如何验证 | mps 无参进入输入循环 | 只做文件存在 + import/函数级检查，不启动交互进程 |

## 验证结果

本地仅做源码审计与测试脚本语法检查；完整 `conan create` 与两行 HMBS
证据标记待 HMBS 后台真机预检产出，PR 正文以上游与新增标记实测为准。

## 注意事项

- package_type 为 application，需软件级 commands.json（R38）。
- 无补丁（patches: {}），POSIX 代码无 OHOS 特判需求。
- 申请人：gcw_6a3w2yXz，队伍：来都来了。
