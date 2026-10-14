cmake_minimum_required(VERSION 3.16)
project(test_gtk3 C)

find_package(gtk3 REQUIRED CONFIG)

add_executable(test_gtk3 test_gtk.c)
target_link_libraries(test_gtk3 PRIVATE gtk3::gtk3)

# V2 最小验收件：只链接 libgtk-3，做一次译文查找，不需要显示后端。
# gtk/3.24.38（gettext shim 默认可见导出）会在此永久挂起；隐藏/移除该 shim 后正常。
add_executable(gtk_gettext_probe gtkgettext_probe.c)
target_link_libraries(gtk_gettext_probe PRIVATE gtk3::gtk3)

enable_testing()

add_test(NAME test_gtk3 COMMAND test_gtk3)
set_tests_properties(test_gtk3 PROPERTIES TIMEOUT 120)

# 严格断言：探针必须 exit=0（由 sh 的 && 链保证：非 0 则不打印断言行）且输出出现
# "[gtkprobe] done"（挂死时只打印到 "after setlocale"，由 TIMEOUT 判定失败）。
add_test(NAME gtk_gettext_probe
         COMMAND sh -c "$<TARGET_FILE:gtk_gettext_probe> && echo '[gtkprobe] assert: done && exit=0'")
set_tests_properties(gtk_gettext_probe PROPERTIES
  TIMEOUT 20
  PASS_REGULAR_EXPRESSION "\\[gtkprobe\\] assert: done && exit=0")
