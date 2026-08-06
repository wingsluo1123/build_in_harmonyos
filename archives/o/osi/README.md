# Osi

> COIN-OR Open Solver Interface.

## 简介

Osi 是 COIN-OR 项目的 Open Solver Interface，提供统一的 C++ 接口来访问不同线性规划和混合整数规划求解器。本适配只构建核心 `libOsi`，不启用 GLPK、SoPlex、CPLEX、Gurobi、Xpress 等外部可选求解器绑定。

## OHOS 适配要点

- 使用 autotools 构建系统。
- 依赖 `coinutils/2.11.13`，通过 `--with-coinutils-incdir` 和
  `--with-coinutils-lib` 分别传入 Conan 依赖包的头文件目录和链接参数。
- 默认构建静态库，避免运行时 RPATH 和可选求解器动态链接问题。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| coinutils | 2.11.13 | COIN-OR 基础容器和工具库 |

## 功能验证

```bash
conan create archives/o/osi/0.108.12 -pr:h ci/conan/profiles/ohos-aarch64 -pr:b default
```

## 参考

- [源码仓库](https://github.com/coin-or/Osi)
