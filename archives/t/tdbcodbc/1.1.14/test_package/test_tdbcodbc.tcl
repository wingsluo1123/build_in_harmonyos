#!/usr/bin/env tclsh
# test_tdbcodbc.tcl — tdbcodbc/1.1.14 消费者测试（Conan test_package）
#
# R34：必须实质调用被测包的 API（不是打印空壳）。
#
# 被测对象的真实调用链（决定了下面每一项断言在验证什么）：
#   tclsh → auto_path/TCLLIBPATH 发现 lib/tdbcodbc1.1.14/pkgIndex.tcl
#         → load libtdbcodbc1.1.14.so Tdbcodbc（依赖 tcl + tdbc 的 stub 表）
#         → source library/tdbcodbc.tcl（package require tdbc + TclOO 类定义）
#         → 首次 ODBC 调用时 GetHEnv() → OdbcInitStubs()
#             dlopen libodbc.so.2（按 name + .so + ABI 后缀 .2/.1/.0 逐个试）
#             dlopen libodbcinst.so.2 + Tcl_FindSymbol(SQLConfigDataSource*)
#
# 其中 4 项为鸿蒙特有断言（ohos-platform / ohos-elf-aarch64 /
# ohos-odbc-manager-mapped / ohos-odbcinst-mapped），计数口径见 MANIFEST.yml。

set pass 0
set fail 0

proc check {name script {detail ""}} {
    global pass fail
    # 表达式在全局作用域求值（脚本里用到全局变量/内建数组）
    if {[uplevel #0 [list expr $script]]} {
        incr pass
        puts "++++ $name PASSED $detail"
    } else {
        incr fail
        puts "---- $name FAILED $detail"
    }
}

# $::errorCode 只在「发生过错误」之后才存在；前面若一路无错，直接读它会报
# can't read "::errorCode": no such variable（CI #91604 之后的第二轮实测踩到）。
proc error_code {} {
    if {[info exists ::errorCode]} {
        return $::errorCode
    }
    return {}
}

# 读取 ELF 头，返回 {magic ei_class e_machine}
proc elf_header {path} {
    set fh [open $path rb]
    set data [read $fh 20]
    close $fh
    binary scan $data H8 magic
    binary scan [string range $data 4 4] H2 ei_class
    binary scan [string range $data 18 19] H* machine_hex
    set lo [scan [string range $machine_hex 0 1] %x]
    set hi [scan [string range $machine_hex 2 3] %x]
    return [list $magic $ei_class [expr {$lo + $hi * 256}]]
}

# 在 /proc/self/maps 里查找已映射进本进程的共享库（返回 1/0；procfs 不可读返回 -1）
proc lib_mapped {regexp_pattern} {
    if {![file readable /proc/self/maps]} {
        return -1
    }
    set fh [open /proc/self/maps r]
    set maps [read $fh]
    close $fh
    return [regexp $regexp_pattern $maps]
}

# 1) 包版本：pkgIndex.tcl 被发现且 load 成功（否则 package require 直接抛错）
check "tdbcodbc-version" {[package require tdbc::odbc 1.1.14] eq "1.1.14"}

# 2) TclOO 类体系：library/tdbcodbc.tcl 的类定义挂到了 tdbc 基类上
#    （证明 tdbc 依赖解析成功，而不只是 .so 被 load）
set supers [info class superclass ::tdbc::odbc::connection]
check "tdbcodbc-superclass" {[lsearch -exact $supers ::tdbc::connection] >= 0} \
    "superclass=\{$supers\}"

# 3) 扩展共享库确实被 dlopen 加载（Tcl 的 load 会以包名注册）
set libpath ""
foreach entry [info loaded] {
    lassign $entry path pkg
    if {[string equal $pkg "Tdbcodbc"]} { set libpath $path }
}
check "tdbcodbc-solib-loaded" {[string length $libpath] > 0} "$libpath"

# 4) ODBC SQL 类型映射表来自被测包的 Tcl 脚本（不是 tdbc 基类提供的）
#    方向是「SQL 类型号 → 名称」：library/tdbcodbc.tcl 写的是
#    `dict create 1 char 2 numeric ... 12 varchar ... -5 bigint ... -11 guid`，
#    共 24 项（已对上游原文实测）。反向按名称查会报
#    key "varchar" not known in dictionary —— CI #91604 实测踩到。
check "tdbcodbc-sqltypes" {
    [dict get $::tdbc::odbc::sqltypes 12] eq "varchar" &&
    [dict get $::tdbc::odbc::sqltypes -5] eq "bigint" &&
    [dict size $::tdbc::odbc::sqltypes] == 24
} "12=[dict get $::tdbc::odbc::sqltypes 12] -5=[dict get $::tdbc::odbc::sqltypes -5] size=[dict size $::tdbc::odbc::sqltypes]"

# 5) 真实 ODBC 调用：SQLAllocHandle + SQLSetEnvAttr + SQLDriversW
#    能返回就说明 OdbcInitStubs() 成功 dlopen 了驱动管理器并解析出符号表
#    判定口径：成功且返回偶数长度字典，**或**失败但 errorCode 以 TDBC 开头
#    （TransferSQLError 所设）。两者都证明 OdbcInitStubs() 已 dlopen 驱动管理器
#    并解析出 SQL* 符号表；只有"库根本没加载起来"才会给出非 TDBC 的普通 Tcl
#    错误，那才是本项要拦的失败。（unixODBC 对空 odbcinst.ini 的具体返回随
#    版本而异，不应成为本项的判定依据。）
set drivers_rc [catch {tdbc::odbc::drivers} drivers_result]
set drivers_code [error_code]
check "odbc-drivers" {
    ($drivers_rc == 0 && ([llength $drivers_result] % 2) == 0) ||
    ($drivers_rc != 0 && [lindex $drivers_code 0] eq "TDBC")
} "rc=$drivers_rc code=\{$drivers_code\} drivers=\{$drivers_result\}"

# 6) SQLDataSourcesW 同样走驱动管理器（读 ODBCSYSINI 下的 odbc.ini）
set dsn_rc [catch {tdbc::odbc::datasources} dsn_result]
set dsn_code [error_code]
check "odbc-datasources" {
    ($dsn_rc == 0 && ([llength $dsn_result] % 2) == 0) ||
    ($dsn_rc != 0 && [lindex $dsn_code 0] eq "TDBC")
} "rc=$dsn_rc code=\{$dsn_code\} dsns=\{$dsn_result\}"

# 7) ::tdbc::odbc::datasource 只有在 libodbcinst 里 SQLConfigDataSource(W)
#    与 SQLInstallerError 都解析成功时才会被创建（上游同款 odbcinst 约束）
check "odbc-inst-command" \
    {[namespace which -command ::tdbc::odbc::datasource] ne {}}

# 8) 错误诊断链路：不存在的驱动 → TransferSQLError → errorCode 里带 SQLSTATE
#    （复刻上游 tdbc::odbc-1.3，但校验到 SQLSTATE 粒度）
set conn_rc [catch {tdbc::odbc::connection create ::nope {DRIVER={no-such-driver}}} \
                 conn_result]
set conn_code [error_code]
check "odbc-connect-failure-sqlstate" {
    $conn_rc == 1 &&
    [lindex $conn_code 0] eq "TDBC" &&
    [llength [regexp -all -inline {[0-9A-Z]{5}} $conn_code]] > 0
} "rc=$conn_rc errorCode=\{$conn_code\}"
catch {rename ::nope {}}

# 9) [鸿蒙特有] 运行平台为 HarmonyOS
#    （TEA 无 HarmonyOS 分支，本包靠 tcl_cv_sys_version=Linux-6.6 走 Linux 路径，
#      该断言锁住"确实在鸿蒙上运行"这个前提）
check "ohos-platform" {
    [string match -nocase "*harmony*" [exec uname -s]] &&
    [string match -nocase "*harmony*" $tcl_platform(os)]
} "os=$tcl_platform(os) uname=[exec uname -s]"

# 10) [鸿蒙特有] 已加载的本包共享库是 ELF64 / AArch64 产物
#     （TEA tcl.m4 缺 HarmonyOS 分支时 SHLIB_LD/SHLIB_SUFFIX 为空，
#       根本产不出共享库；此断言验证共享库分支确实生效且架构正确）
if {[string length $libpath] > 0} {
    lassign [elf_header $libpath] magic ei_class machine
    check "ohos-elf-aarch64" \
        {($magic eq "7f454c46") && ($ei_class eq "02") && ($machine == 183)} \
        "magic=$magic class=$ei_class machine=$machine (183=AArch64)"
} else {
    check "ohos-elf-aarch64" 0 "缺少已加载库路径"
}

# 11) [鸿蒙特有] 驱动管理器确实被映射进本进程
#     odbcStubInit.c 的候选名表里没有 __OHOS__ 分支，OHOS 走的是 Linux 路径：
#     "odbc32/odbc/libodbc32/libodbc/libiodbc" × (info sharedlibextension) ×
#     ABI 后缀 ".2/.1/.0"。制品仓的 unixodbc 提供 libodbc.so.2（soname），
#     因此 OHOS 上必须由 "libodbc" + ".so" + ".2" 这一组合命中。
#     /proc/self/maps 里出现该映射 = dlopen 按 soname 成功，不是文件存在性检查。
check "ohos-odbc-manager-mapped" {
    [info sharedlibextension] eq ".so" &&
    [lib_mapped {libodbc\.so\.2}] == 1
} "shlibext=[info sharedlibextension]"

# 12) [鸿蒙特有] 安装器库同样按 soname 解析成功（对应第 7 项的命令创建条件）
check "ohos-odbcinst-mapped" \
    {[lib_mapped {libodbcinst\.so\.2}] == 1}

puts "test_tdbcodbc:\tTotal\t[expr {$pass + $fail}]\tPassed\t$pass\tFailed\t$fail"
if {$fail > 0} {
    exit 1
}
exit 0
