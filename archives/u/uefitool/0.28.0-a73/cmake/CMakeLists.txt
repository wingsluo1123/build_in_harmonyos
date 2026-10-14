# cmake/CMakeLists.txt — uefitool 0.28.0-a73 的适配侧构建入口（**非上游文件**）
#
# 为什么需要它：
#   上游根 CMakeLists.txt 无条件 ADD_SUBDIRECTORY(UEFITool)，而
#   UEFITool/CMakeLists.txt 第 9 行是
#       FIND_PACKAGE(Qt6 REQUIRED COMPONENTS Widgets)
#   ⇒ 在没有 Qt6 的平台上，根工程在 configure 阶段直接 FATAL_ERROR，
#     连两个纯 CLI 目标（UEFIExtract / UEFIFind，二者都不依赖 Qt）都拿不到。
#
#   与其给上游打补丁改它的构建文件（会引入 patches_applied 计数同步、
#   R8「平台条件编译宏」等一系列额外风险），本包改为**自带一个构建入口**
#   把两个 CLI 子工程装进来 —— 上游源码一个字节都不动，补丁列表为空。
#   这是 Conan Center Index 的常规做法（自带构建入口而非改上游）。
#
#   路径语义：子工程里的 `../common/*.cpp` 是相对于**子工程自身**的源目录解析的，
#   所以这里 ADD_SUBDIRECTORY 直接指向 UEFIExtract/ 与 UEFIFind/ 即可，
#   不需要复制或重排任何源码。

cmake_minimum_required(VERSION 3.22)

# ★ project() 的第二个位置参数起必须全是 CMake 认识的关键字（LANGUAGES/VERSION/...）。
# 这里必须写 LANGUAGES，否则多出来的裸词会被 CMake **当成语言名**：
#   实测（cmake 4.3.4 最小复现）写成 `project(uefitool CLI CXX C)` 会让 CMake 去找
#   CMakeDetermineCLICompiler.cmake，报
#     "Could not find cmake module file: CMakeDetermineCLICompiler.cmake"
#     "No CMAKE_CLI_COMPILER could be found."
#     -- Configuring incomplete
#   即 configure 阶段直接失败 —— 与"两个 CLI 能不能编"无关，纯语法坑。
project(uefitool LANGUAGES CXX C)

# 两个子工程各自已声明 CMAKE_CXX_STANDARD 11 / CMAKE_CXX_EXTENSIONS OFF，
# 以及 INSTALL(TARGETS <target> RUNTIME DESTINATION bin)，无需重复声明。
# 第二个参数（binary dir）必须给：源目录在父目录之外，不能自动推导。
add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../UEFIExtract"
                 "${CMAKE_CURRENT_BINARY_DIR}/UEFIExtract")
add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../UEFIFind"
                 "${CMAKE_CURRENT_BINARY_DIR}/UEFIFind")

# 把产物名钉死。
# 上游只在 `IF(UNIX)` 分支里把 OUTPUT_NAME 改成小写（`uefiextract` / `uefifind`），
# 是否能命中取决于 CMake 的平台识别结果。本包的对外接口**就是**这两个可执行
# 文件的路径（消费者用例、commands.json、使用文档都按小写名写），
# 不能让平台识别结果左右它，故在父作用域里显式再钉一次（目标在子目录里定义，
# 但 CMake 目标是全局的，父作用域可以再次 set_target_properties）。
set_target_properties(UEFIExtract PROPERTIES OUTPUT_NAME "uefiextract")
set_target_properties(UEFIFind    PROPERTIES OUTPUT_NAME "uefifind")

# ── 构建自检（本包新增，**不是**上游测试）──────────────────────────────
# 上游全仓没有任何测试套件（无 enable_testing()、无 add_test(、meson 里
# 零处 test()，只有 fuzzing/ 下的 libFuzzer harness）⇒ 直接跑 ctest 会因
# "找不到任何测试"返回非 0，让 conan create 失败，而日志里只有一句
# "No tests were found"，既不是证据也不是失败原因。
#
# 这里注册 3 条**只依赖两个 CLI 自身退出码**的冒烟用例：确定性、无外部
# 固定装置、与机器负载无关。期望退出码全部取自上游 main() 的字面返回：
#   uefiextract -v       -> 0（uefiextract_main.cpp 的 -v/--version 分支）
#   uefifind   -v        -> 0（uefifind_main.cpp 的 -v/--version 分支）
#   uefiextract（无参数）-> 1（uefiextract_main.cpp: argc <= 1 → print_usage 后 return 1）
#
# 注意这是**构建树自检**（跑的是刚编出来的二进制），
# 安装产物的消费者级验证在 test_package/test.sh 里，两者层次不同。
enable_testing()
add_test(NAME uefitool-cli-version-extract
         COMMAND $<TARGET_FILE:UEFIExtract> -v)
add_test(NAME uefitool-cli-version-find
         COMMAND $<TARGET_FILE:UEFIFind> -v)
add_test(NAME uefitool-cli-usage-extract
         COMMAND $<TARGET_FILE:UEFIExtract>)
set_tests_properties(uefitool-cli-usage-extract PROPERTIES WILL_FAIL TRUE)
