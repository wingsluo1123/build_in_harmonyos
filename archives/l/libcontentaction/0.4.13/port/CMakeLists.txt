# =============================================================================
# libcontentaction 0.4.13 —— OHOS 移植构建（CMake）
#
# 上游为 qmake 工程（libcontentaction.pro / src.pro / tests.pro …），OHOS 交叉
# 工具链与赛事 CI 均以 CMake 为门禁口径，故提供等价 CMake 构建：
#   * 编译同一批上游源文件（src/*.cpp）与测试源文件（tests/*.cpp，零改动）；
#   * 测试夹具布局、环境变量、执行方式按上游 tests/tests.xml.in +
#     tests/lca-cita-test.in 复刻（lca-cita-test 原样生成）；
#   * 上游依赖 mlite（MDesktopEntry/MDConfItem/MRemoteAction）以兼容层实现，
#     见 port/mlite-compat/。
# =============================================================================
cmake_minimum_required(VERSION 3.20)

# -----------------------------------------------------------------------------
# HarmonyOS 原生构建（= 赛事 CI worker）平台识别兜底 —— 必须在 project() 之前
# -----------------------------------------------------------------------------
# CMake 在原生构建时执行 `uname -s`，HarmonyOS 主机返回 "HarmonyOS"，CMake 据此
# 设 CMAKE_SYSTEM_NAME=HarmonyOS，然后去加载 Modules/Platform/HarmonyOS.cmake。
# 而 CMake 官方（含 CI worker 的 cmake 4.1.2 与 brew cmake 4.4.3）**只提供
# Platform/OHOS.cmake（内容仅 `include(Platform/Linux)`），没有 HarmonyOS.cmake**，
# 于是：
#   System is unknown to cmake, create: Platform/HarmonyOS ...
#   CMake Error: Generator: build tool execution failed ...
#   Check for working CXX compiler: .../clang++ - broken
#   The C++ compiler ... is not able to compile a simple test program.
# 交叉构建（-DCMAKE_SYSTEM_NAME=OHOS，WSL/Conan profile 强制）不受影响，因此该失败
# 只在原生（CI）侧暴露，本地 WSL 交叉全绿也照样红。
#
# 处理：仅当「宿主机是 HarmonyOS 且未指定任何目标系统」（即真正的原生构建）时，
# 在 project() 之前把 CMAKE_SYSTEM_NAME 预置为 OHOS —— 与 OHOS SDK 内
# ohos.toolchain.cmake 的 `set(OHOS TRUE)` + `if(NOT CMAKE_SYSTEM_NAME) ...` 同构。
# 预置值会写入 <build>/CMakeFiles/<ver>/CMakeSystem.cmake，CMakeDetermineSystem
# 检测到已有 CMAKE_SYSTEM_NAME 时不再自行 uname/查找平台文件，于是走
# Platform/OHOS.cmake -> Platform/Linux，与 WSL 交叉构建完全同一条代码路径。
#
# 判据取 CMAKE_HOST_SYSTEM_NAME 而不是 CMAKE_SYSTEM_NAME：
#   * 宿主非 HarmonyOS（Linux/WSL 交叉）→ 条件为假，行为逐字节不变；
#   * 已知交叉（toolchain 已设 CMAKE_SYSTEM_NAME=OHOS）→ 条件为假；
#   * 宿主 HarmonyOS + 无目标系统 = 原生 → 命中。
# CMAKE_HOST_SYSTEM_NAME 要么由 -D 缓存变量给定，要么由 CMakeDetermineSystem
# 写入同一条 CMakeSystem.cmake（先赋 uname -s 结果），任一情况下在本行之前已确定。
# 只有显式传入 CMAKE_SYSTEM_NAME 的调用方才会压制本兜底（那是交叉声明，不该覆盖）。
# 不使用 CMAKE_CROSSCOMPILING：它在 project() 之后才被设置。
if(CMAKE_HOST_SYSTEM_NAME STREQUAL "HarmonyOS" AND NOT CMAKE_SYSTEM_NAME)
    set(CMAKE_SYSTEM_NAME OHOS)
endif()

project(libcontentaction VERSION 0.4.13 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
# 固定输出目录，使测试床包装脚本可在配置期生成（含可执行权限）
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

option(LCA_BUILD_TESTS "Build and register the upstream test suite" ON)

# 查找前缀补全：qtbase 以 cmake_find_mode=none 发布（LCA_QT_PREFIX 由 Conan
# 注入），且 CMP0126(OLD) 下 set(CACHE) 会抹掉 toolchain 的 generators 前缀，
# 故这里显式把两者都加进 CMAKE_PREFIX_PATH
if(DEFINED LCA_QT_PREFIX)
    list(PREPEND CMAKE_PREFIX_PATH "${LCA_QT_PREFIX}")
endif()
if(DEFINED CMAKE_TOOLCHAIN_FILE)
    get_filename_component(_lca_conan_gen "${CMAKE_TOOLCHAIN_FILE}" DIRECTORY)
    list(PREPEND CMAKE_PREFIX_PATH "${_lca_conan_gen}")
endif()

find_package(Qt6 REQUIRED COMPONENTS Core DBus Test Xml)
find_package(GLib REQUIRED)

set(LCA_CONTENTACTION_DATADIR "/usr/share/contentaction" CACHE STRING
    "Default actions directory (upstream DEFAULT_ACTIONS)")

set(LCA_SOURCES
    src/contentaction.cpp
    src/service.cpp
    src/dbus.cpp
    src/exec.cpp
    src/mime.cpp
    src/highlighter.cpp
    src/highlight.cpp
    src/config.cpp
    src/contentinfo.cpp
    port/mlite-compat/mdesktopentry.cpp
    port/mlite-compat/mdconfitem.cpp
    port/mlite-compat/mremoteaction.cpp
)

add_library(contentaction6 SHARED ${LCA_SOURCES})
target_include_directories(contentaction6
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/port/mlite-compat>
        $<INSTALL_INTERFACE:include/contentaction6>
        $<INSTALL_INTERFACE:include>
)
target_compile_definitions(contentaction6
    PRIVATE LCA_BUILD QT_NO_KEYWORDS
    PUBLIC DEFAULT_ACTIONS="${LCA_CONTENTACTION_DATADIR}"
)
target_link_libraries(contentaction6
    PUBLIC Qt6::Core Qt6::DBus
    PRIVATE GLib::Gio GLib::GObject GLib::GModule GLib::GLib
)
set_target_properties(contentaction6 PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION 0
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib
)

add_executable(lca-tool tools/lca-tool.cpp)
target_compile_definitions(lca-tool PRIVATE QT_NO_KEYWORDS)
target_link_libraries(lca-tool PRIVATE contentaction6 Qt6::Core GLib::Gio GLib::GLib)
# RUNPATH 需含 $ORIGIN 相对条目：CMake 把同构建树内的库以相对 `lib/...` 传给
# 链接器，RUNPATH 却只记配置期的绝对构建路径；构建目录搬迁或 cwd 变化时
# （CI worker 的 conan 构建目录与配置期不同）会报
#   Error loading shared library libcontentaction6.so.0
#   Error relocating ... : symbol not found
# 补 $ORIGIN/../lib 后无论构建树在哪、cwd 为何都能命中。
set_target_properties(lca-tool PROPERTIES
    BUILD_RPATH "${CMAKE_BINARY_DIR}/lib;\$ORIGIN/../lib"
    BUILD_WITH_INSTALL_RPATH OFF
    SKIP_BUILD_RPATH OFF)

# -----------------------------------------------------------------------------
# dbus-probe：guest 侧 D-Bus 会话总线可达性探针（仅供 run_py_case.sh 作执行环境预检）
# -----------------------------------------------------------------------------
# ★不是测试用例，也不安装进包★（因此不进 install(TARGETS ...) 清单）：
# 它只回答"本执行环境里 QDBusConnection::sessionBus() 能不能连上"。
# 宿主侧 python3-dbus + dbus-daemon 齐备 ≠ guest 侧连得上：qemu-user 下
# D-Bus SASL 认证（EXTERNAL/ANONYMOUS 均实测被拒）无法完成，导致
# lca-tool 的 X-Maemo-Method 触发静默 no-op、假服务收不到调用、用例超时 FAIL。
# 让 run_py_case.sh 据此按 SKIP(77) 退出，避免"环境不满足"被误报成"用例失败"。
# 放在与 lca-tool 同一输出目录，使 run_py_case.sh 能用 $ORIGIN 相对路径找到它。
add_executable(dbus-probe port/dbus-probe.cpp)
target_link_libraries(dbus-probe PRIVATE Qt6::Core Qt6::DBus)
set_target_properties(dbus-probe PROPERTIES
    BUILD_RPATH "${CMAKE_BINARY_DIR}/lib;\$ORIGIN/../lib"
    BUILD_WITH_INSTALL_RPATH OFF
    SKIP_BUILD_RPATH OFF
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin
)

include(GNUInstallDirs)
install(TARGETS contentaction6 lca-tool
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
)
install(FILES src/contentaction.h src/contentinfo.h
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/contentaction6)

# -----------------------------------------------------------------------------
# 包数据：highlight1.xml（上游 data/data.pro 为**无条件**安装的包数据）
# -----------------------------------------------------------------------------
# 上游 data.pro 不带任何构建选项守卫地安装 highlight1.xml 到
# /usr/share/contentaction；本配方对应的安装目的地是 ${CMAKE_INSTALL_DATADIR}/contentaction。
# 该文件由 gen-regexps 生成 regex.sed 再经 sed 替换 highlight1.xml.in 得到（同上游规则）。
#
# 注意：此段必须位于 if(LCA_BUILD_TESTS) **之外**。否则当
# -o libcontentaction/*:build_tests=False 时，contentaction6 仍以
# DEFAULT_ACTIONS="${LCA_CONTENTACTION_DATADIR}" 编译，但包内不再含 highlight1.xml，
# 造成"高亮规则静默为空"的包内容回归，且只在非默认选项组合下暴露。
set(LCA_PKG_HIGHLIGHT1 ${CMAKE_CURRENT_BINARY_DIR}/pkgdata/highlight1.xml)
set(LCA_UP_DATA_PKG ${CMAKE_CURRENT_SOURCE_DIR}/data)
add_custom_command(
    OUTPUT ${LCA_PKG_HIGHLIGHT1}
    COMMAND ${CMAKE_COMMAND} -E make_directory ${CMAKE_CURRENT_BINARY_DIR}/pkgdata
    COMMAND python3 ${LCA_UP_DATA_PKG}/gen-regexps > ${CMAKE_BINARY_DIR}/regex-pkg.sed
    COMMAND sed -f ${CMAKE_BINARY_DIR}/regex-pkg.sed < ${LCA_UP_DATA_PKG}/highlight1.xml.in
            > ${LCA_PKG_HIGHLIGHT1}
    WORKING_DIRECTORY ${LCA_UP_DATA_PKG}
    DEPENDS ${LCA_UP_DATA_PKG}/gen-regexps ${LCA_UP_DATA_PKG}/highlight1.xml.in
    COMMENT "Generating highlight1.xml (upstream data.pro rule, package data)")
add_custom_target(lca-highlight1-pkgdata ALL DEPENDS ${LCA_PKG_HIGHLIGHT1})
install(FILES ${LCA_PKG_HIGHLIGHT1}
    DESTINATION ${CMAKE_INSTALL_DATADIR}/contentaction)

# -----------------------------------------------------------------------------
# 上游测试（tests.xml.in 的14 个用例；夹具布局按 lca-cita-test.in）
# -----------------------------------------------------------------------------
if(LCA_BUILD_TESTS)
    enable_testing()

    set(LCA_TESTBED ${CMAKE_BINARY_DIR}/testbed)
    # 上游 .in 夹具（lca-cita-test.in / *.desktop.in）用 @PATH@ 占位，替换为测试床路径
    set(PATH "${LCA_TESTBED}")
    set(LCA_UP_TESTS ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    set(LCA_UP_DATA ${CMAKE_CURRENT_SOURCE_DIR}/data)

    # --- 目标二进制执行器（qemu-user / 原生） ---
    # 只收集**依赖包**的 lib 目录；构建树自己的 lib/ 由 run-guest.sh 按脚本位置
    # 推导（`<build>/lib`），这样 CI worker 上构建目录与配置期不同也能找到。
    #
    # 注意：CMakeDeps 生成的 glib/dbus 等目标是 INTERFACE IMPORTED，没有 LOCATION，
    # 故再按「链接库名 → 依赖包 lib 目录」补一轮（包目录从 *_PACKAGE_FOLDER_* 变量取）。
    set(LCA_GUEST_LIB_DIRS "")
    foreach(_tgt contentaction6 Qt6::Core Qt6::DBus Qt6::Test
                 GLib::Gio GLib::GObject GLib::GModule GLib::GThread GLib::GLib
                 dbus::dbus expat::expat pcre2::pcre2 libffi::libffi ZLIB::ZLIB)
        if(TARGET ${_tgt})
            get_target_property(_imported ${_tgt} IMPORTED)
            set(_loc "")
            if(_imported)
                get_target_property(_loc ${_tgt} LOCATION)
                if(NOT _loc)
                    get_target_property(_cfgs ${_tgt} IMPORTED_CONFIGURATIONS)
                    if(_cfgs)
                        list(GET _cfgs 0 _cfg)
                        get_target_property(_loc ${_tgt} IMPORTED_LOCATION_${_cfg})
                    endif()
                endif()
            endif()
            if(_loc)
                get_filename_component(_dir "${_loc}" DIRECTORY)
                list(APPEND LCA_GUEST_LIB_DIRS "${_dir}")
            endif()
        endif()
    endforeach()
    # CMakeDeps 的 INTERFACE 目标：从 -data.cmake 变量里取各依赖包根，再取 lib/
    foreach(_pkg glib qtbase dbus expat pcre2 libffi zlib)
        string(TOUPPER "${_pkg}" _PU)
        foreach(_var "${_pkg}_PACKAGE_FOLDER_RELEASE" "${_pkg}_PACKAGE_FOLDER"
                     "${_pkg}_PACKAGE_FOLDER_DEBUG" "${_PU}_PACKAGE_FOLDER")
            if(DEFINED ${_var} AND EXISTS "${${_var}}/lib")
                list(APPEND LCA_GUEST_LIB_DIRS "${${_var}}/lib")
            endif()
        endforeach()
    endforeach()
    list(REMOVE_DUPLICATES LCA_GUEST_LIB_DIRS)
    string(REPLACE ";" ":" LCA_GUEST_LIB_DIRS_STR "${LCA_GUEST_LIB_DIRS}")
    # 该串会被 @LCA_GUEST_LIB_DIRS@ 注入 run-guest.sh.in 的双引号内
    # （export LD_LIBRARY_PATH="${GUEST_LIB_DIRS}..."），故必须做壳转义：
    # 若依赖包路径含 $ ` " \ 等字符，未转义会在 shell 求值时被展开或截断。
    string(REPLACE "\\" "\\\\" LCA_GUEST_LIB_DIRS_ESC "${LCA_GUEST_LIB_DIRS_STR}")
    string(REPLACE "\"" "\\\"" LCA_GUEST_LIB_DIRS_ESC "${LCA_GUEST_LIB_DIRS_ESC}")
    string(REPLACE "$" "\\$" LCA_GUEST_LIB_DIRS_ESC "${LCA_GUEST_LIB_DIRS_ESC}")
    string(REPLACE "`" "\\`" LCA_GUEST_LIB_DIRS_ESC "${LCA_GUEST_LIB_DIRS_ESC}")
    set(LCA_GUEST_LIB_DIRS "${LCA_GUEST_LIB_DIRS_ESC}")
    configure_file(port/run-guest.sh.in ${CMAKE_BINARY_DIR}/run-guest.sh @ONLY)
    file(CHMOD ${CMAKE_BINARY_DIR}/run-guest.sh PERMISSIONS
        OWNER_READ OWNER_WRITE OWNER_EXECUTE GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE)

    # --- 测试床目录（复刻上游 CONTENTACTION_TESTDIR 布局） ---
    file(MAKE_DIRECTORY ${LCA_TESTBED}/bin ${LCA_TESTBED}/data
         ${LCA_TESTBED}/applications ${LCA_TESTBED}/mime/packages ${LCA_TESTBED}/home)

    # 生成 lca-cita-test（上游测试入口包装，@PATH@ 替换与上游 qmake 规则一致）
    configure_file(${LCA_UP_TESTS}/lca-cita-test.in ${LCA_TESTBED}/bin/lca-cita-test @ONLY)

    # 上游测试脚本与数据（tests/testdata.pro 清单）
    set(LCA_TEST_SCRIPTS
        testlib.sh cltool.py gallery.py servicemapper.py uberprogram.py
        test-defaults.py test-mimes.py test-desktop-launching.py
        test-fixed-params.py test-schemes.sh test-special-chars.py
        test-regexps.py test-highlight.sh)
    foreach(_f ${LCA_TEST_SCRIPTS})
        # 显式存在性校验：configure_file(... COPYONLY) 对缺失源目录在部分 CMake
        # 版本下不报错，会把"脚本没部署"推迟成运行期 "No such file or directory"，
        # 在 CI 上表现为用例 FAIL 而非配置失败（难定位）。这里让它在配置期就炸。
        if(NOT EXISTS ${LCA_UP_TESTS}/${_f})
            message(FATAL_ERROR
                "upstream test script missing from source tree: ${LCA_UP_TESTS}/${_f}")
        endif()
        configure_file(${LCA_UP_TESTS}/${_f} ${LCA_TESTBED}/${_f} COPYONLY)
    endforeach()
    set(LCA_TEST_DATA
        service.map plaintext empty.pdf launchme.desktop test-image.png hlinput.txt)
    foreach(_f ${LCA_TEST_DATA})
        configure_file(${LCA_UP_TESTS}/${_f} ${LCA_TESTBED}/${_f} COPYONLY)
    endforeach()
    configure_file(${LCA_UP_DATA}/gen-regexps ${LCA_TESTBED}/gen-regexps COPYONLY)
    configure_file(${LCA_UP_DATA}/regextest2.py ${LCA_TESTBED}/regextest2.py COPYONLY)
    configure_file(${LCA_UP_DATA}/hl-examples.xml ${LCA_TESTBED}/data/hl-examples.xml COPYONLY)
    configure_file(port/run_py_case.sh ${LCA_TESTBED}/run_py_case.sh COPYONLY)
    configure_file(port/run_py_subset.py ${LCA_TESTBED}/run_py_subset.py COPYONLY)
    configure_file(port/run_qtest_case.sh ${LCA_TESTBED}/run_qtest_case.sh COPYONLY)
    # 上游脚本按 shebang/PATH 直接调用，需保留可执行位
    file(CHMOD ${LCA_TESTBED}/run_py_case.sh ${LCA_TESTBED}/run_qtest_case.sh
         ${LCA_TESTBED}/gen-regexps
         ${LCA_TESTBED}/bin/lca-cita-test PERMISSIONS
        OWNER_READ OWNER_WRITE OWNER_EXECUTE GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE)
    foreach(_f ${LCA_TEST_SCRIPTS})
        file(CHMOD ${LCA_TESTBED}/${_f} PERMISSIONS
            OWNER_READ OWNER_WRITE OWNER_EXECUTE GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE)
    endforeach()

    # .desktop 夹具（@PATH@ 处理同上游 applications.pro）
    # CONFIGURE_DEPENDS：上游新增/改名 fixture 后无需手动重新 configure 即可拾取；
    # 否则配置期求值会静默沿用旧清单，运行时报 "fixture not found"。
    file(GLOB LCA_DESKTOP_FIXTURES CONFIGURE_DEPENDS ${LCA_UP_TESTS}/applications/*)
    foreach(_f ${LCA_DESKTOP_FIXTURES})
        get_filename_component(_name ${_f} NAME)
        if(_name MATCHES "\\.in$")
            string(REGEX REPLACE "\\.in$" "" _out ${_name})
            configure_file(${_f} ${LCA_TESTBED}/applications/${_out} @ONLY)
        else()
            configure_file(${_f} ${LCA_TESTBED}/applications/${_name} COPYONLY)
        endif()
    endforeach()

    # shared-mime-info 测试用 mime 数据库（构建期生成，不提交二进制）
    #
    # 上游 test-info/test-action 依赖系统 shared-mime-info 的类型描述与内容探测
    # （"Plain text document" / "PNG image"）。OHOS 无该组件，且 GIO 只读取
    # update-mime-database 生成后的数据库（mime.cache/magic/treemagic 等），
    # 不认裸 packages/*.xml。
    #
    # 该数据库含 NUL 字节（本质是二进制；实测 mime.cache 584B/194B、magic、
    # treemagic 均含 NUL），**不能作为文本提交**：GitCode 导出的 PR diff 会把它
    # 渲染成缺 GIT binary patch 段的 "binary patch"，导致 CI 的 checkout-pr
    # 步骤 git apply 失败（error: missing binary patch data for ...）。
    # 故仓库只提交可读的 XML 源，数据库在构建期用宿主 update-mime-database 生成。
    # 落点 $XDG_DATA_HOME/mime（lca-cita-test 的 XDG_DATA_HOME=${HOME}/tests-home）。
    #
    # 注意：构建机可能没有 shared-mime-info（CI worker 实测无该工具）。
    # 此时**降级**为不生成数据库：test-info/test-action 的少数依赖类型描述/内容
    # 探测的断言会失败，但库本体与其余用例不受影响；配置阶段绝不 FATAL_ERROR，
    # 否则整包构建直接失败（CI L1 = conan create failed）。
    find_program(UPDATE_MIME_DATABASE NAMES update-mime-database)
    if(NOT UPDATE_MIME_DATABASE)
        message(WARNING
            "update-mime-database (shared-mime-info) not found on the build host; "
            "the mime test database will not be generated and the upstream cases that "
            "depend on type descriptions (test-info/test-action) will not pass")
    else()
        add_custom_command(
            OUTPUT ${LCA_TESTBED}/home/tests-home/mime/mime.cache
            COMMAND ${CMAKE_COMMAND} -E make_directory
                    ${LCA_TESTBED}/home/tests-home/mime/packages
            COMMAND ${CMAKE_COMMAND} -E copy
                    ${CMAKE_CURRENT_SOURCE_DIR}/port/mime-fixture/packages/lca-test-mime.xml
                    ${LCA_TESTBED}/home/tests-home/mime/packages/lca-test-mime.xml
            COMMAND ${UPDATE_MIME_DATABASE} ${LCA_TESTBED}/home/tests-home/mime
            DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/port/mime-fixture/packages/lca-test-mime.xml
            COMMENT "Generating shared-mime-info test database (update-mime-database)")
        add_custom_target(lca-mime-fixture ALL
            DEPENDS ${LCA_TESTBED}/home/tests-home/mime/mime.cache)
    endif()

    # highlight1.xml：上游 data.pro 构建期规则（gen-regexps 生成 regex.sed + sed 替换）
    # 两份落点：TESTBED/data（上游测试数据区，与 hl-examples.xml 并存，同上游
    # data.pro testdata）、TESTBED/share-action（等价上游 /usr/share/contentaction
    # 部署区，test-highlight.sh 与 gen-regexps test 按上游语义使用纯 highlight1.xml）。
    add_custom_command(
        OUTPUT ${LCA_TESTBED}/data/highlight1.xml
               ${LCA_TESTBED}/share-action/highlight1.xml
        COMMAND ${CMAKE_COMMAND} -E make_directory ${LCA_TESTBED}/share-action
        COMMAND python3 ${LCA_UP_DATA}/gen-regexps > ${CMAKE_BINARY_DIR}/regex.sed
        COMMAND sed -f ${CMAKE_BINARY_DIR}/regex.sed < ${LCA_UP_DATA}/highlight1.xml.in
                > ${LCA_TESTBED}/data/highlight1.xml
        COMMAND ${CMAKE_COMMAND} -E copy ${LCA_TESTBED}/data/highlight1.xml
                ${LCA_TESTBED}/share-action/highlight1.xml
        WORKING_DIRECTORY ${LCA_UP_DATA}
        DEPENDS ${LCA_UP_DATA}/gen-regexps ${LCA_UP_DATA}/highlight1.xml.in
        COMMENT "Generating highlight1.xml (upstream data.pro rule)")
    add_custom_target(lca-highlight1 ALL
        DEPENDS ${LCA_TESTBED}/data/highlight1.xml)

    # --- 目标二进制包装（PATH=TESTBED/bin，上游 lca-cita-test 机制） ---
    # 输出目录固定为 build/bin，故可在配置期生成并直接赋予可执行权限
    # （上游脚本按 PATH 直接调用 lca-tool 等目标二进制，权限位是必要条件）
    foreach(_t lca-tool test-info test-action test-mimedefaults test-findhighlights)
        set(LCA_WRAP_GUEST_NAME ${_t})
        configure_file(port/guest-wrapper.sh.in ${LCA_TESTBED}/bin/${_t} @ONLY)
    endforeach()
    foreach(_t lca-tool test-info test-action test-mimedefaults test-findhighlights)
        file(CHMOD ${LCA_TESTBED}/bin/${_t} PERMISSIONS
            OWNER_READ OWNER_WRITE OWNER_EXECUTE GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE)
    endforeach()

    # --- QTest 可执行文件（上游 tests/*.cpp 零改动） ---
    foreach(_t test-info test-action test-mimedefaults test-findhighlights)
        add_executable(${_t} ${LCA_UP_TESTS}/${_t}.cpp)
        target_include_directories(${_t} PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/src
            ${CMAKE_CURRENT_SOURCE_DIR}/port/mlite-compat)
        target_compile_definitions(${_t} PRIVATE QT_NO_KEYWORDS)
        target_link_libraries(${_t} PRIVATE contentaction6 Qt6::Core Qt6::Test GLib::Gio)
        # RUNPATH 需含 **$ORIGIN 相对条目**：CMake 把同构建树内的库以相对
        # `lib/...` 传给链接器，但 RUNPATH 里只记配置期的绝对构建路径。
        # 构建目录被搬迁 / 工作目录变化时（CI worker 的 conan 构建目录与配置期
        # 不同），绝对条目失效，加载器报
        #   Error loading shared library libcontentaction6.so.0
        #   Error relocating ... findHighlights: symbol not found
        # 加 $ORIGIN/../lib 后，无论构建树放到哪里、cwd 是什么都能命中。
        set_target_properties(${_t} PROPERTIES
            BUILD_RPATH "${CMAKE_BINARY_DIR}/lib;\$ORIGIN/../lib"
            BUILD_WITH_INSTALL_RPATH OFF
            SKIP_BUILD_RPATH OFF)
    endforeach()

    # --- ctest 注册（用例名 = 上游 tests.xml.in case 名） ---
    set(LCA_SH sh)
    # GIO 自 2.80 起经 gio-launch-desktop 助手落地 GDesktopAppInfo 启动
    # （上游触发型用例 test-desktop-launching / test-mimes 的 Exec= 依赖此路径）。
    # 发行版把该助手装在 PATH 内；Conan 的 glib 包放在 <pkg>/bin，故补入测试 PATH。
    # CMakeDeps 的 glib 目标是 INTERFACE IMPORTED（无 LOCATION），依次尝试
    # 链接库路径 / 头文件目录 / 包目录变量三种途径定位包根。
    set(_lca_glib_prefix "")
    foreach(_tgt GLib::GLib GLib::Gio glib::glib)
        if(TARGET ${_tgt} AND _lca_glib_prefix STREQUAL "")
            set(_lca_cands "")
            get_target_property(_loc ${_tgt} LOCATION)
            if(NOT _loc)
                get_target_property(_cfgs ${_tgt} IMPORTED_CONFIGURATIONS)
                if(_cfgs)
                    list(GET _cfgs 0 _cfg)
                    get_target_property(_loc ${_tgt} IMPORTED_LOCATION_${_cfg})
                endif()
            endif()
            if(_loc)
                list(APPEND _lca_cands "${_loc}")
            endif()
            get_target_property(_links ${_tgt} INTERFACE_LINK_LIBRARIES)
            if(_links)
                list(APPEND _lca_cands ${_links})
            endif()
            get_target_property(_incs ${_tgt} INTERFACE_INCLUDE_DIRECTORIES)
            if(_incs)
                list(APPEND _lca_cands ${_incs})
            endif()
            foreach(_cand ${_lca_cands})
                # <pkg>/lib/libgio-2.0.so 或 <pkg>/include/glib-2.0
                string(REGEX REPLACE "/(lib|include)/.*$" "" _p "${_cand}")
                if(EXISTS "${_p}/bin/gio-launch-desktop")
                    set(_lca_glib_prefix "${_p}")
                endif()
                # <pkg>/lib/glib-2.0/include 形式
                string(REGEX REPLACE "/lib/glib-2\\.0/include$" "" _p2 "${_cand}")
                if(EXISTS "${_p2}/bin/gio-launch-desktop")
                    set(_lca_glib_prefix "${_p2}")
                endif()
            endforeach()
        endif()
    endforeach()
    # _lca_glib_prefix 由上方 foreach(_cand ${_lca_cands}) 中"命中即赋值"的
    # EXISTS 判定写入（两者均指向含 bin/gio-launch-desktop 的包根），
    # 故此处的 STATUS 报告的正是**实际命中的候选目录**，可被证据文档引用。
    set(LCA_GLIB_BIN_PATH "")
    if(_lca_glib_prefix)
        set(LCA_GLIB_BIN_PATH "${_lca_glib_prefix}/bin:")
        message(STATUS "libcontentaction tests: glib helper dir = ${_lca_glib_prefix}/bin "
                       "(matched from ${_lca_cands})")
    else()
        message(WARNING "libcontentaction tests: gio-launch-desktop not located; "
                        "trigger-based upstream cases may fail")
    endif()
    # 上游 lca-cita-test 环境的 ctest 等价（HOME 等对所有用例统一注入）
    # LCA_DBUS_PROBE：guest 侧 D-Bus 可达性探针，供 run_py_case.sh 的 DBus
    # 分支作**执行环境预检**（不可连 -> SKIP 77，而非让用例跑到超时 FAIL）。
    set(LCA_COMMON_ENV
        "HOME=${LCA_TESTBED}/home"
        "XDG_DATA_HOME=${LCA_TESTBED}/home/tests-home"
        "XDG_DATA_DIRS=${LCA_TESTBED}:/usr/local/share:/usr/share"
        "LCA_DBUS_PROBE=${CMAKE_BINARY_DIR}/bin/dbus-probe"
        "PATH=${LCA_GLIB_BIN_PATH}${LCA_TESTBED}/bin:${LCA_TESTBED}:$ENV{PATH}")

    add_test(NAME upstream-lca-cita-test-fail
        COMMAND ${LCA_SH} ${LCA_TESTBED}/bin/lca-cita-test false)
    set_tests_properties(upstream-lca-cita-test-fail PROPERTIES
        WILL_FAIL TRUE ENVIRONMENT "${LCA_COMMON_ENV}")

    add_test(NAME upstream-test-defaults
        COMMAND ${LCA_SH} ${LCA_TESTBED}/bin/lca-cita-test
                run_py_case.sh test-defaults.py)
    add_test(NAME upstream-test-regexps
        COMMAND ${LCA_SH} ${LCA_TESTBED}/bin/lca-cita-test
                run_py_case.sh test-regexps.py)

    # test-highlight.sh / gen-regexps test：上游语义是使用部署区配置
    # （上游 test-highlight.sh 显式 export CONTENTACTION_ACTIONS=/usr/share
    # /contentaction，gen-regexps test 不经 lca-cita-test 同样落部署区）。
    # OHOS 无该系统目录，改指 TESTBED/share-action（仅含部署版 highlight1.xml），
    # 测试脚本仅补 env 兜底一行（见 patches/0001）。
    add_test(NAME upstream-test-highlight
        COMMAND ${LCA_SH} ${LCA_TESTBED}/run_py_case.sh test-highlight.sh
                sh test-highlight.sh)
    add_test(NAME upstream-generated-regex-testsuite
        COMMAND ${LCA_SH} ${LCA_TESTBED}/run_py_case.sh gen-regexps
                python3 gen-regexps test)
    set_tests_properties(upstream-test-highlight upstream-generated-regex-testsuite
        PROPERTIES
        SKIP_RETURN_CODE 77
        WORKING_DIRECTORY ${LCA_TESTBED}
        ENVIRONMENT "${LCA_COMMON_ENV};CONTENTACTION_ACTIONS=${LCA_TESTBED}/share-action")
    # 注：给这两条用例设 WORKING_DIRECTORY 曾经试过（R11），但**与缺陷无关**：
    # 上游 lca-cita-test 自己就 `cd ${TEST_DIR}`，cwd 早已是 testbed。
    # 真正的缺陷在 run_py_case.sh 末位的裸相对名 exec（HMOS 的 sh 不搜索 cwd），
    # 已在 run_py_case.sh 内修复，此处保留默认 cwd 即可。
    set_tests_properties(upstream-test-defaults upstream-test-regexps
        PROPERTIES SKIP_RETURN_CODE 77 ENVIRONMENT "${LCA_COMMON_ENV}")

    # 需要执行环境预检（python3 / /tmp / DBus 夹具）的用例：缺失即 SKIP(77)
    # 用例名与上游 tests.xml.in 的 case 名严格一致（含 test-fixedparams 的写法）
    foreach(_pair "test-mimes.py|test-mimes" "test-desktop-launching.py|test-desktop-launching"
                  "test-fixed-params.py|test-fixedparams" "test-special-chars.py|test-special-chars"
                  "test-schemes.sh|test-schemes")
        string(REPLACE "|" ";" _pl "${_pair}")
        list(GET _pl 0 _c)
        list(GET _pl 1 _n)
        add_test(NAME upstream-${_n}
            COMMAND ${LCA_SH} ${LCA_TESTBED}/bin/lca-cita-test
                    run_py_case.sh ${_c})
        set_tests_properties(upstream-${_n} PROPERTIES
            SKIP_RETURN_CODE 77 ENVIRONMENT "${LCA_COMMON_ENV}")
    endforeach()

    # test-mimes.py 的非 DBus 方法子集（上游断言零改动，按方法抽取执行）
    add_test(NAME upstream-test-mimes-subset
        COMMAND ${LCA_SH} ${LCA_TESTBED}/bin/lca-cita-test
                run_py_case.sh test-mimes.py python3 run_py_subset.py test-mimes.py
                Mimes.testActionsForPlain Mimes.testInvokeExec Mimes.testInvokeExecMulti)
    set_tests_properties(upstream-test-mimes-subset PROPERTIES
        SKIP_RETURN_CODE 77
        ENVIRONMENT "${LCA_COMMON_ENV};LCA_SKIP_DBUS_CHECK=1")

    # QTest 用例（经 lca-cita-test 设置上游同款环境）
    # test-info / test-action 依赖 shared-mime-info 数据库（构建机无
    # update-mime-database 时不可用），由 run_qtest_case.sh 预检并按
    # ctest 的 SKIP_RETURN_CODE=77 记为 SKIP，避免整包构建失败。
    foreach(_c test-info test-action test-mimedefaults test-findhighlights)
        add_test(NAME upstream-${_c}
            COMMAND ${LCA_SH} ${LCA_TESTBED}/run_qtest_case.sh ${_c}
                    ${LCA_TESTBED}/bin/lca-cita-test ${_c})
        set_tests_properties(upstream-${_c} PROPERTIES
            SKIP_RETURN_CODE 77
            ENVIRONMENT "${LCA_COMMON_ENV}")
    endforeach()

    # -------------------------------------------------------------------------
    # 用例间**共享可变状态**的隔离（并发下会假失败，必须逐个给私有 HOME）
    # -------------------------------------------------------------------------
    # ★必须放在全部 add_test 之后★（set_tests_properties 对尚未注册的用例会直接
    # CMake Error 配置失败）。
    # 上游 test-defaults.py 的 testSettingDefault / testResettingDefault 会真实写
    #   $XDG_DATA_HOME/applications/mimeapps.list
    # 并断言写入前/复位后的 action 顺序一致：
    #   (status, oldactions) = getstatusoutput("lca-tool --actionsformime text/plain")
    #   lca-tool --setmimedefault ...  /  --resetmimedefault ...
    #   self.assertTrue(newactions == oldactions)      # test-defaults.py:73
    # 本机实测（**同一产物、不改任何代码**）：
    #   * ctest -j1 串行        -> `100% tests passed, 0 tests failed out of 15`
    #                              （连跑两次一致）
    #   * ctest 默认并发(-j3)    -> upstream-test-defaults 间歇 ***Failed
    #                              （AssertionError: False is not true @:73），
    #                              该用例隔离重跑 6/6 全过；
    #                              并行跑 defaults 与 mimes-subset 时**必现**互相踩。
    # 根因：多个用例二进制共用 LCA_TESTBED/home，写同一份 mimeapps.list，
    # 彼此的 set/reset 交错使 oldactions/newactions 顺序比较失败。
    # 这是**上游用例的隔离缺陷**（断言与用例逻辑零改动），修法是给会写状态的用例
    # 一份**私有 HOME/XDG_DATA_HOME**（由 run_py_case.sh 按 LCA_PRIVATE_HOME=1 落实）。
    # 只对确知会写状态的用例生效，其余保持共享目录以免偏离上游口径。
    #
    # ★ENVIRONMENT 是**整体替换**而非追加★：这里必须把该用例原有的额外变量
    # （upstream-test-mimes-subset 的 LCA_SKIP_DBUS_CHECK=1）原样带上，
    # 否则会被本循环覆盖掉，导致该用例改走 DBus 夹具预检而被误判 SKIP
    # （实测踩到过：subset 从 Passed 变成 Skipped）。
    set(_lca_iso_tests
        upstream-test-defaults upstream-test-mimedefaults
        upstream-test-mimes-subset upstream-test-regexps)
    foreach(_t ${_lca_iso_tests})
        set(_extra "")
        if(_t STREQUAL "upstream-test-mimes-subset")
            set(_extra ";LCA_SKIP_DBUS_CHECK=1")
        endif()
        set_tests_properties(${_t} PROPERTIES
            ENVIRONMENT "${LCA_COMMON_ENV};LCA_PRIVATE_HOME=1${_extra}")
    endforeach()
endif()
