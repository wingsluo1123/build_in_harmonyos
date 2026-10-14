# slrn

slrn 是 John E. Davis 开发的基于 S-Lang 的全屏文本模式 Usenet 新闻阅读器，支持 NNTP/NNTP over SSL、评分（score）系统、线程视图与 S-Lang 脚本扩展。

## 功能概述

- NNTP 新闻组浏览、订阅、发帖与回复
- 文章评分与过滤（scorefile）
- S-Lang 脚本宏扩展（share/slrn/slang/*.sl）
- NNTP over SSL（OpenSSL）
- 可选 slrnpull 离线阅读后端（本包未启用 spool 支持）
- 可选 uudeview/canlock（本包未启用：依赖未发布到制品仓）

## OHOS 适配

- config.sub 增加 linux-ohos 识别（上游为 2014 版，补丁 0001）
- configure 的 config.status 临时目录 umask 077 → 022（HMDFS 目录属主映射导致 0700 不可写，知识 E011，补丁 0002）
- src/Makefile.in 的构建期工具 chkslang 交叉编译时不可执行，增加 SKIP_CHKSLANG 守卫（补丁 0003）；OHOS CI 为原生构建，仍会执行该版本检查
- va_copy/__va_copy/va_list 按值复制三个 AC_TRY_RUN 探测在交叉编译时以缓存变量预置
- 已知限制：metamail 集成（默认关闭）在 mime.c 中硬编码 /tmp；HarmonyOS PC 的 /tmp 只读（E002），如需 metamail 请先导出 TMPDIR。slrn 其余临时文件路径已遵循 TMP/TMPDIR

## 依赖关系

- 编译/运行依赖：slang/2.3.3（必须）、openssl/3.0.16（SSL 支持）
- 构建工具：autotools（预生成 configure）、make

## 参考资料

- 官网：https://www.jedsoft.org/slrn/
- 源码仓库：https://github.com/jedsoft/slrn （镜像）；官方 git：git://git.jedsoft.org/git/slrn.git
- 发布包：https://www.jedsoft.org/releases/slrn/
- 命令行工具声明：commands.json 位于软件级目录 archives/s/slrn/commands.json（CI L0k 要求）
