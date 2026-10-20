# irclog2html

irclog2html 将 IRC 聊天日志转换为带颜色的 HTML 页面。

## 功能

- `irclog2html`：把单个日志文件转换为 HTML。
- `logs2html`：批量转换按日期存放的日志，并生成前后日期链接。
- `irclogsearch` 与 `irclogserver`：分别提供 CGI 搜索和 WSGI 日志展示入口；本次消费者场景未覆盖这两个服务入口。

## OpenHarmony PC 适配

Conan 配方把上游纯 Python 模块及 `irclog.css` 放入包内，并为四个命令生成 Python 启动脚本；软件级 `commands.json` 声明这些命令。源码无平台补丁。目标验证结果与已知问题见版本级适配笔记；官方 CI 结果以 PR 回执为准。

## 依赖

- 运行时：Python。上游声明支持 Python 3.7 及以上，未声明强制安装的第三方运行库。
- 构建与打包：Conan 2、Python；配方编译阶段检查模块可编译性。
- 上游测试：固定测试命令使用 pytest 及其运行依赖；上游 `setup.py` 的 `test` extra 另声明 `zope.testing`。这些均非运行包的强制依赖。

## 参考资料

- [项目主页](https://mg.pov.lt/irclog2html/)
- [上游源码](https://github.com/mgedmin/irclog2html)
