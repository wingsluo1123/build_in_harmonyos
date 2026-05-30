# CGAL

## 简介

CGAL (Computational Geometry Algorithms Library) 是一个提供高效可靠的计算几何算法的开源 C++ 库。广泛应用于 CAD、GIS、分子生物学、医学成像等领域。

## OHOS 适配

- CGAL 5.0+ 是 **header-only** 库，无需编译库文件，仅需安装头文件和 CMake 配置
- 依赖：GMP 6.3.0, MPFR 4.2.1, Boost 1.86.0（已安装预编译包）
- 质量门禁 G1-G4 通过
- 预编译包：44MB（3659 个头文件 + CMake 配置）

### 适配要点

1. CGAL 是 header-only 库，不需要编译二进制文件
2. 需要设置 `LD_LIBRARY_PATH` 包含 OHOS SDK llvm/lib 目录（GMP/MPFR 依赖）
3. CMake 配置文件已正确设置路径

### 已知问题

- 无已知问题

## 排除与替代

- 无需排除任何组件

## 依赖

### 编译依赖
- GMP 6.3.0（GNU 多精度算术库）
- MPFR 4.2.1（多精度浮点运算库）
- Boost 1.86.0（C++ 库集合）

### 运行依赖
- GMP 6.3.0
- MPFR 4.2.1

## 功能验证

```bash
# 验证 CGAL 安装
cmake --find-package -DNAME=CGAL -DCOMPILER_ID=GNU -DLANGUAGE=CXX -DMODE=COMPILE

# 或使用 pkg-config
pkg-config --cflags --libs CGAL
```

## 参考

- 官网：https://www.cgal.org/
- 源码仓库：https://github.com/CGAL/cgal
- 文档：https://doc.cgal.org/latest/Manual/index.html