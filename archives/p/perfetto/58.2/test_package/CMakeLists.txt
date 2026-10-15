cmake_minimum_required(VERSION 3.16)
project(perfetto_consumer CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 消费者：使用 Perfetto 公共头 + 链接 libperfetto，验证 SDK 头与库可用。
find_package(perfetto CONFIG REQUIRED)

add_executable(consumer consumer.cc)
target_link_libraries(consumer PRIVATE perfetto::perfetto)

# 双保险：CMakeDeps 会通过 imported target 带出 include 路径；此处再显式补一次
# （避免某些 package_type 下 cpp_info.includedirs 未导出导致的隐性缺头）。
if(perfetto_INCLUDE_DIRS)
  target_include_directories(consumer PRIVATE ${perfetto_INCLUDE_DIRS})
endif()
