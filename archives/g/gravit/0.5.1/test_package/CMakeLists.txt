cmake_minimum_required(VERSION 3.15)
project(gravit_consumer C)

# SDL 1.2 (windowless video surface), GLU + OSMesa (the offscreen GL stack the
# simulator renders through) and libpng (the screenshot writer).  The packaged
# application itself is validated by the Python consumer cases.
find_package(SDL CONFIG REQUIRED)
find_package(glu CONFIG REQUIRED)
find_package(mesa CONFIG REQUIRED)
find_package(libpng CONFIG REQUIRED)

# 鸿蒙特有测试（rule12）：具名端到端消费者用例 GS-1..GS-3 ——
# 构造输入（已知清屏色/四边形色 + GLU 投影）→ 真实执行（OSMesa 离屏渲染 +
# glReadPixels + 无窗口 SDL 整帧拷贝 + libpng 往返）→ 产出结果（64x64 帧、
# SDL 表面、PNG）→ 校验内容（像素与用例给定的输入常量比对）。
add_executable(test_gl_stack test_gl_stack.c)
target_link_libraries(test_gl_stack PRIVATE
    SDL::SDL
    glu::glu
    mesa::mesa
    libpng::libpng
)
