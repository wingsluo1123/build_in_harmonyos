cmake_minimum_required(VERSION 3.16)
project(opennurbs_consumer CXX)

find_package(opennurbs CONFIG REQUIRED)

add_executable(opennurbs_consumer main.cpp)
# 链接 SHARED 目标（libOpenNURBS.so）——它是本包的主要交付物；
# 运行期需要它的目录在 LD_LIBRARY_PATH 上（见 test_package/conanfile.py）。
# 链接包级目标 opennurbs::opennurbs（CMakeDeps 未设 cmake_target_name 时生成的名字，
# 它已聚合 cpp_info.libs 里的库）——**不是** opennurbs::OpenNURBS（实测不存在）。
target_link_libraries(opennurbs_consumer PRIVATE opennurbs::opennurbs)
set_target_properties(opennurbs_consumer PROPERTIES CXX_STANDARD 17)
