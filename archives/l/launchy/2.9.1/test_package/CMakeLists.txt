cmake_minimum_required(VERSION 3.15)
project(test_launchy C)

# launchy 为 application 包（package_type=application，无库目标/公开头文件），
# 消费者只能通过其运行时产物 bin/launchy 使用（R34：执行被测包二进制）。
# test.c 为真实消费者程序：验证 packaged 二进制 aarch64 ELF + DT_NEEDED 严格
# 解析，并用 QT_QPA_PLATFORM=offscreen 真实运行 packaged launchy，
# 触发 QLockFile 单实例锁（R40 路径 1）真实执行。
add_executable(test_launchy test.c)

enable_testing()
add_test(NAME test_launchy COMMAND test_launchy)