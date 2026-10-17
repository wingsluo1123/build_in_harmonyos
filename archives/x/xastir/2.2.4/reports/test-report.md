# xastir 2.2.4 测试报告

## 构建验证
- **conan create**: 通过（OHOS aarch64 worker 原生，`ci/conan/profiles/ohos-aarch64` 双上下文，`--build=missing`）
- **conan-verify**: 通过（G0/G1/G2/G3/G4 + L2/L4/L5 全绿，报告见 `reports/conan-verify-report.md`）
- **W3 本地 CI 模拟**: 通过（`ci/conan/build_and_test.sh xastir/2.2.4`，需 `TMPDIR`+`TMPPREFIX` 指向可写目录——zsh 的 heredoc 临时文件默认 /tmp 只读）
- **产物**: bin/xastir (aarch64 ELF), bin/callpass, share/xastir/{config,symbols,help,scripts}, share/man/man1/{xastir,callpass,xastir_udp_client,testdbfawk}.1, licenses/COPYING
- **package_id**: 09a58d77e0b6fe964a536f8fc71cc441ba758579

## 上游测试清点（R51）
- xastir 2.2.4 自带真实测试套件：
  - 7 个 check_PROGRAMS（tests/Makefile.am）：test_interface_helpers、test_db、test_object_utils、test_output_my_aprs_data、test_util、test_objects + test_nominatim（HAVE_NOMINATIM，本配方启用 Nominatim 故构建；链接真实 src/*.c 对象）
  - autotest testsuite（AC_CONFIG_TESTDIR）：db 30 + interface_helpers 1 + nominatim 12 + object_utils 118 + objects 42 + output_my_aprs_data 23 + util 16 = 242 项
- build() 内 `( unset DISPLAY; timeout 900 make check ) 2>&1` 原样执行
- **实测：`All 242 tests were successful.`（CHECK_EXIT=0，无跳过）**，原始输出逐字进构建日志（[upstream-test] 行）
- 测试二进制在 OHOS worker 上真实执行（DT_NEEDED 由配方 E050 链接视图 + LD_LIBRARY_PATH 满足）

## 消费者测试（test_package/test_xastir.sh）
- 断言组: 6
- 通过: 6
- 失败: 0
- 覆盖:
  1. callpass 功能哈希：4 呼号（W1AW/WA0EIR/N0CALL/X1ABC-9）输出与独立 Python 复算的 APRS passcode（0x73e2 种子成对 XOR）逐一相等
  2. callpass 无参 usage 横幅
  3. headless xastir：60s 不挂起、不静默成功、**零动态加载器诊断**（OHOS libc 预先重定位——进入 X 层即证明整个 DT_NEEDED 闭包装载完成）；接受显示错误文本或信号死亡（后者为本机 libXt/1.3.1 无显示错误路径的平台缺陷）
  4. DT_NEEDED 直接 soname 集：libXm.so.4/libXt.so.6/libX11.so.6/libXext.so.6/libXpm.so.4/libSM.so.6/libICE.so.6/libcurl.so/libproj.so.25/libtiff.so.6/libgeotiff.so.5
  5. 反向断言：不含 worker 前缀的 libcurl.so.4 / libpcre2-8.so.0（链接的是图内 curl/8.15.0 + 静态 pcre2/10.48）
  6. 打包运行数据树（share/xastir/{config,symbols,help}）

## 平台限制（详见 notes.md）
- ImageMagick/GraphicsMagick 集成禁用（上游拒绝 MagickLibVersion>0x0700；registry 只有 7.1.2.29=0x712）——栅格地图导入走 GeoTIFF/shapelib 路径
- 线程取消为能力探测降级（非平台宏）：`AC_CHECK_FUNCS` 探出 HAVE_PTHREAD_CANCEL/HAVE_PTHREAD_TESTCANCEL，取消检查点降级为 no-op、3 处取消调用点被守卫（不伪造取消成功）；net_connect/read/write 线程均自行 detach 且从不被 join，关闭接口时经正常循环条件退出（取消提前退出路径不可用）
- libXt/1.3.1 无显示错误路径 SIGSEGV（最小 XtOpenDisplay 程序可独立复现）——影响所有 Xt 应用的 headless 测试形态，非 xastir 特有
- Festival/GPSMan 集成禁用（worker 无对应运行时）；Nominatim 地理编码已启用（cjson/1.7.19 已发布）
