# GNU Bash Debugger — OpenHarmony 编译档案

## 软件简介
bashdb 是 Bash 脚本调试器，提供类似 gdb 的调试功能，包括断点设置、单步执行、变量检查、调用栈跟踪等。

## 功能概述
- 断点设置与条件断点
- 单步执行（step/next）
- 变量检查与修改
- 调用栈跟踪
- 表达式求值
- 支持 `bash --debugger` 直接调试
- 支持从脚本内部通过 `source bashdb-trace` 启动调试

## OHOS 适配要点
- configure 脚本仅支持 bash 5.0/5.1/5.2，需补丁添加 5.3 支持
- 使用 `--with-bash` 选项指定 bash 5.3 可执行文件路径
- 纯 bash 脚本包，无需编译，仅运行 configure + make install
- 运行时依赖 bash/5.3

## 依赖关系
- bash/5.3（运行时依赖）

## 使用方式
```bash
# 方式一：通过 bash --debugger 调试
bash --debugger -- script.sh arg1 arg2

# 方式二：直接调用 bashdb
bashdb -- script.sh arg1 arg2

# 方式三：从脚本内部启动
source ${BASHDB_PREFIX}/bashdb-trace -L ${BASHDB_PREFIX}
_Dbg_debugger; :
```

## 参考资料
- [bashdb 官方文档](http://bashdb.sourceforge.net/bashdb-man.html)
- [SourceForge 项目页](https://sourceforge.net/projects/bashdb/)
