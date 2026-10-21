# Star Traders（trader）

**基于 ncurses 的星际贸易终端游戏**

Star Traders 是一个简单的星际贸易游戏：玩家创建公司、买卖股票、借贷还款，
目标是成为最富有的玩家。终端界面由宽字符 Curses（NcursesW）渲染。

## 功能特性
- 1-8 名玩家（共享同一键盘与屏幕）
- 回合制股票交易、公司创建、借贷机制
- 内置详尽游戏说明
- 命令行选项：`--max-turn`、`--no-color`、`--version`、`--help`
- GNU gettext 多语言支持（当前以 `--disable-nls` 基础适配，英文为主）

## 编译版本
- **7.21**（为 OpenHarmony aarch64 编译）

## 依赖
- ncurses 6.6（NcursesW 宽字符 + colour，静态链接）

## 构建系统
Autotools（configure + make），tarball 自带 configure；适配时以
`--disable-nls --with-ncurses` 配置，规避外部 gettext 依赖并启用 NcursesW。

## OHOS 适配要点
- OHOS libc（musl 系）缺 POSIX `strfmon()`，补丁提供 `!__GLIBC__` 守卫的
  自包含实现，避免 `undefined symbol: strfmon`。
- autoconf 的 `umask 077` 临时目录在 setgid 的 HMDFS 上不可写，构建时就地
  改为 `umask 022`。
- 官方源码站 `ftp.zap.org.au` 在构建网络下连接超时；使用与官方归档位级相同
  （同一 sha256）的 Debian 源码仓库镜像回退。

## 使用方法
```bash
trader           # 开始新游戏（提示输入玩家人数 1-8）
trader -V        # 版本信息
trader -h        # 帮助页面
trader --max-turn=NUM   # 设定回合数
trader --no-color       # 不使用彩色显示
```

## 说明
- 适配路径：路径 A（基础适配）
- 上游无自动化测试套件（见版本目录 test_package/MANIFEST.yml 审计）
