cmake_minimum_required(VERSION 3.15)
project(test_rdma C)

# OHOS E119: sys/socket.h guards sockaddr_storage with #ifndef __MUSL__.
# test_ohos_specific.c includes the package headers together with
# <linux/netlink.h> and <sys/socket.h>, so it needs the same switch that
# the recipe passes to the upstream build.
add_compile_definitions(__MUSL__=1)

find_package(rdma REQUIRED)

# L1: consumer view of the installed public API (libibverbs + librdmacm)
add_executable(test_rdma test.c)
target_link_libraries(test_rdma PRIVATE rdma::rdma)

# HarmonyOS-specific portability test (platform behaviour, not upstream)
add_executable(test_ohos_specific test_ohos_specific.c)
target_link_libraries(test_ohos_specific PRIVATE rdma::rdma)

# Consumer use case: only public headers / public API
add_executable(test_consumer test_consumer.c)
target_link_libraries(test_consumer PRIVATE rdma::rdma)

enable_testing()
add_test(NAME test_rdma COMMAND test_rdma)
add_test(NAME test_ohos_specific COMMAND test_ohos_specific)
add_test(NAME test_consumer COMMAND test_consumer)
