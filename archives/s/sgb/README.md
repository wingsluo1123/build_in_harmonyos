# Stanford GraphBase

SGB 是用于组合计算的 C 图生成与图算法库，包含标准图构造、数据集生成器、最短路径、随机数和图保存恢复。

适配使用已发布的 CWEB 构建工具和原版随附的 PROTOTYPES change files，保留原始 CWEB 文件与许可。包提供静态 `libgb.a`、头文件、`sgb::sgb` CMake 目标及 `share/sgb` 数据；数据生成器沿用当前目录查找方式。运行时依赖 C 标准库和系统数学库。

官网：<https://www-cs-faculty.stanford.edu/~knuth/sgb.html>；官网指向的维护仓库：<https://github.com/ascherer/sgb>。版本对应、测试结果和环境边界见版本目录的 notes.md。
