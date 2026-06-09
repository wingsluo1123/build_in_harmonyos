#!/bin/sh
# OpenSubdiv CMake 配置参数
# 禁用所有可选组件（OpenGL, GLFW, CUDA, OpenCL, PTEX, 文档, 示例, 教程, 测试）

mkdir -p build
cd build

cmake -D CMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
      -D NO_OPENGL=ON \
      -D NO_GLFW=ON \
      -D NO_CUDA=ON \
      -D NO_OPENCL=ON \
      -D NO_CLEW=ON \
      -D NO_PTEX=ON \
      -D NO_DOC=ON \
      -D NO_EXAMPLES=ON \
      -D NO_TUTORIALS=ON \
      -D NO_REGRESSION=ON \
      ..
