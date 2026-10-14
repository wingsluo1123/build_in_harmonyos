# emlog

EMbedded-system 日志设备（Linux 内核模块 + 用户态工具）。

## 功能概述
- `emlog.ko`：有限容量环形缓冲字符设备驱动（内核模块，仅 Linux）
- `nbcat`：非阻塞读取日志设备当前内容，类似 `cat` 但不阻塞等待新数据
- `mkemlog`：创建 emlog 设备节点

## OHOS 适配
OHOS PC 用户态工具链无法构建内核模块（缺 `<linux/*>` 内核头与 KDIR），
本适配仅交付用户态工具 nbcat/mkemlog。mkemlog.c 依赖的 GNU `<error.h>`
在 OHOS musl sysroot 中缺失，通过补丁以 fprintf+exit 最小等价实现替代。
nbcat 可对任意普通文件/FIFO 运行；mkemlog 运行需要内核模块，OHOS 下不可运行。

## 依赖关系
无第三方依赖。

## 参考资料
- 官网：http://www.circlemud.org/~jelson/software/emlog
- 源码：https://github.com/nicupavel/emlog