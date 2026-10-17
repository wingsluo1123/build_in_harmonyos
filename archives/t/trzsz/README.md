# trzsz（Python）

trzsz 在终端会话中传输文件，提供接收命令 `trz` 和发送命令 `tsz`。本归档对应官方 Python 项目 1.1.5，同版 metapackage、trzsz-libs 与 trzsz-svr 一起提供；可选 iTerm2 前端不在本次验证范围。

OHOS 6 / armv8 上已实际构建 Conan 包：原 unit 19/19、七组协议回归 7/7、一个包消费者通过，均无跳过；完整自动 W3 exit=0。完整 finish 仍 rc1，详见版本笔记和测试报告。尚未发布、提审、合入或计分。

## 运行与依赖

配方依赖公共 `python/3.12.9` 的固定 recipe revision。消费者加载 Conan 的 `conanrun` 环境后执行：

```sh
trz --help
tsz --help
```

`PYTHONHOME`、Python 和模块搜索路径只作用于该运行环境。启动器自行定位本包模块；包消费者已核准确公共解释器的路径、prefix、3.12.9 与真实 OHOS termios 标准库；协议回归实际执行 alarm 和 CLI 错误传播。双向传输需要支持 trzsz 协议的客户端，本次定向测试用真实协议对端覆盖文件阶段，不声称完成远端终端客户端兼容矩阵。

## 文件进度边界

在已约定正 SIZE 且文件尚未完成时，decoded 空 DATA 不能当作成功进度。发送端源文件在 SIZE 确认后被截短，或接收端收到有效空 DATA，应通过原错误协议终止该文件事务。合法 SIZE=0 空文件跳过数据循环，仍完成 MD5；通用零长控制消息不因此禁用。

知识草稿记录复现输入、双端 guard、正常空文件/多块对照和近邻差异：[`E429-draft-F6EC.md`](../../../knowledge/drafts/E429-draft-F6EC.md)。草稿未接受、合入或计分。

## 来源

- [官方 Python 源码](https://github.com/trzsz/trzsz/tree/e433a8c326dddd1b7a9fe79f3f1b766f76fe9ca8)
- [版本笔记](1.1.5/notes.md)
