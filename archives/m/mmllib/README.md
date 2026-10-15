# MMLlib

MMLlib 是解析 Music Macro Language、生成播放列表及 MusicXML 的纯 Python 包。上游版本 1.4，主页 https://edugit.org/nik/mmllib，许可证 MirOS。

本次新适配 A+B 仅修复合法数字音符的 MusicXML 载荷判别，保留字母音符、休止和全部原测试。配方目录 `1.4/`；知识草稿 `knowledge/drafts/E429-draft-M414.kv` 与配对 MD。

源码与固定 setuptools 后端均记录 URL/SHA256。运行依赖为 Conan Python 3.12.9；测试是标准库 unittest。激活 Conan 运行环境后调用 `mml2musicxml file.mml`、`mmllint -q file.mml`，或 `mmllib.musicxml.convert_mml_file(path)`。

固定候选001已由唯一H1在OHOS6.0/armv8目标profile完成真实Conan构建、8方法完整suite及1安装包消费者/11断言；本地W3的L0/L1/L1e/L4/L5通过，L2帮助/版本探测skip。整体finish rc1和旧G0、W5、SUMMARY问题保留，统计与边界见 `1.4/notes.md`；原始报告为本机审核证据，按仓库策略不提交Git。本包未upload、未发布或有效提审。
