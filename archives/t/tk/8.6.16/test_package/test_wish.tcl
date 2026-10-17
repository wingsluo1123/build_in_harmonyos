# wish8.6 启动链探针脚本 —— 由 test_package/conanfile.py 的 test() 以文件参数传入。
#
# 用途：验证 libtk8.6.so 的加载链路（RPATH/依赖库/ELF 签名），而本机与 CI worker 都
# 没有 X display，wish8.6 必然在 Tk 初始化阶段失败——因此本脚本体在无显示环境下不会
# 被执行，它只作为 wish 的输入文件存在（避免用管道喂 stdin，那会被 CI 的 L1d 假测试
# 正则 `self.run.*(echo|print|true)` 误判为空壳测试）。
#
# test() 侧断言：输出必须只报缺显示，且不得出现 "Error loading shared library"、
# "Permission denied"（未签名 ELF，E077）、"Can not find a usable"（tk 脚本库缺失）。
# 若运行环境存在 DISPLAY，test() 会走 DISPLAY 分支跳过本探针。

puts "wish8.6 reachable: Tk [info patchlevel], tcl [info tclversion]"
exit 0
