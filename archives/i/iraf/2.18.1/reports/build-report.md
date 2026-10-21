# IRAF 2.18.1 构建报告

2026-10-17，HarmonyOS PC / AArch64，SDK 26.0.0.18 clang 15，Release，私有 CONAN_HOME。
原始 `FinishPipeline.step35_local_ci()` 完整退出 **0**，耗时 **2081 秒**。
自举 NOVOS→VOS→宿主工具重建→完整核心/NOAO→原始上游测试→安装及 test_package 均完成。

本轮基于 main `ad0c1a73eaeeb0807aebf150606a75a9ee950bd0`，源码提交 `7646521e2988cc49ae145a47569724d56f76b572`，
run_id `facfbb4c44c842209dd0479d00662fd9`，启动时间 2026-10-17T11:43:47.429836+00:00。
`setup.sh`、`build_and_test.sh`、KC、预算配置及 FinishPipeline 与该 main 的 Git blob 逐字节一致。
采用默认 **3600 秒**，没有 IRAF 超时覆盖或 OHC_W3_TIMEOUT；应用 PR 不包含框架改动。
此前 #16270 和 #16376 已按用户要求关闭，本轮不依赖它们。

源码为官方 GitHub v2.18.1 归档，SHA256
`d4e0859088459622625d27b5c025524dc70fbf334e8df5e59dd32b65630e7981`。
实际包：`iraf/2.18.1#188ac75554dd52f5a674f58331428afa:a11f76f99f4c0529e1d1120a6ce5c02a81629ab9#2f12ad2c87c67dba39ff9997a4e2f9ff`。
构建目录：`/storage/Users/currentUser/work/frj__/iraf-7507/conan/p/b/irafd9e8de2daa931/b`；安装目录：`/storage/Users/currentUser/work/frj__/iraf-7507/conan/p/b/irafd9e8de2daa931/p`。

## 能力探测与 SDK 工具

配方先验证编译器能正常链接，再按实际链接结果选择 `sigsetjmp` / `__sigsetjmp`，
探测 netdb.h 的 rcmd 与 fpu_control.h。缺失能力必须对应明确诊断；资源、信号和其他编译错误直接失败。
探测只编译和链接，不运行构建探针。实际选择公开 `sigsetjmp`、SSH 兼容实现、通用浮点初始化路径。
补丁没有新增操作系统平台宏。24 项真机专项回归独立计数，详见 host-feature-tests.json。
其中21项通过受控结果/环境注入验证判定与错误边界，3项调用真实SDK；均在真机执行，
不把24项解释为24组实际编译，也不混入上游或消费者统计。
测试源码为reports/test-host-features.py，直接导入本配方；可在已安装Conan的OHOS环境执行：
`IRAF_PROBE_COMPILER="$CC" python3 reports/test-host-features.py`，CC使用实际profile编译器。
支持IRAF_RECIPE与IRAF_PROBE_WORKSPACE覆盖，默认在当前目录下创建独立测试工作区。
实际安装 libos.a 的符号表再次确认 zsvjmp 使用 sigsetjmp、zfioks 使用 iraf_rcmd_ssh。

配方在 build-release/tools（Conan build_folder/tools）生成 SDK ar/ranlib/nm/strip 包装器，W3 和后续消费者 PATH 均移除旧任务私有别名。
包装器不会安装到生产包。其内容及摘要写入 verification.json。

## 证据绑定

启动前固定10个关键输入 SHA256，收集时与工作树、实际导出配方及实际构建补丁核对。
原始工具生成 .ci-result.json，未手写或修改。CI 暂将官方 URL 展开为固定顺序镜像列表并预下载到 file URL；
按 URL 派生缓存名、位置、顺序和归档 SHA256 核对导出缓存，其余元数据字段必须相同。
退出后保留官方 .orig 与镜像元数据，精确恢复 canonical conandata；CI result、导出缓存和启动清单不变。
本轮仅复用已校验的源码归档缓存；第二 URL 缓存键由第一归档复制，不声称第二路网络下载成功，未导入编译产物。

重定位与独立缓存验证各有唯一 run_id，子进程成功、原目录 inode 身份恢复、包和输入摘要不变后才记通过。
完整原始日志及恢复日志保存在真机与本机独立备份，仓库提交测试输出和摘要。

安装树归档 `iraf-2.18.1-ohos-armv8-2f12ad2c.tar.gz`，95486734 字节，3711 成员；
SHA256 `2a23d64bc1cf2bafb92d63aec7ec68b30a04e2c042a718a3ff7ca197ff73b681`。归档保留在真机，不作为源码提交。

| 日志/输入 | SHA256 |
|---|---|
| w3-local-ci.log | 5eaf8ef6672596b439b05c25f6b7c09f53c0db946e0e343365b133199a47398f |
| conan_build.log | b2951575976fc27e5156ecd6dca8c00f9542523b087814ec096f15af4278d41e |
| upstream-test.log | 72e96b26c4d142a4688092dda9023dd0ff6925a4510b421820e47b07839df9f9 |
| relocation.log | f709e0d68c70d782232fd134c8666b32e4f762d8cece0dc207bd0fafed5951c9 |
| patch | b139a8f38933404745dbd364c7239353d5c03c4d2fdf58cee1a09c253f9f0fed |
| built_patch | b139a8f38933404745dbd364c7239353d5c03c4d2fdf58cee1a09c253f9f0fed |
| clean-consumer.log | f709e0d68c70d782232fd134c8666b32e4f762d8cece0dc207bd0fafed5951c9 |
| conanfile.py | 36ef0278d997418bb336dd3a85035e8e84170524f69edf6262b2a2915fe435fa |
| exported_conanfile.py | 36ef0278d997418bb336dd3a85035e8e84170524f69edf6262b2a2915fe435fa |
| conandata.yml | 32b64070436048198dc65e40caea81920e2405fe6f1340963f6a6a2f0f602edc |
| f77_parallel.py | 20200a3d8265f0e9b1816111d97c52c6e7eae874c83ff507311885ba085b4889 |
| built_f77_parallel.py | 20200a3d8265f0e9b1816111d97c52c6e7eae874c83ff507311885ba085b4889 |
| f2c_launcher.py | 73ab0e971af0c45053b9740db12cd3902a13b889d21c2d9d3f734e9ec9cc873e |
| built_f2c_launcher.py | 73ab0e971af0c45053b9740db12cd3902a13b889d21c2d9d3f734e9ec9cc873e |
| test_context.c | 2676548c29485ab056abf2f4179bf6df34f99afc13f7fd408cee061230561bb8 |
| test_rcmd.c | 944f9eea3f04dc7a3955f78711e98ed1a8576e7406ac63e592b59abac6b05578 |
| test_package/conanfile.py | 5afd6bb2410ad7e3e69802e7db692c583b81fc20d1431c4033f2aab077e654f4 |
| test_package/MANIFEST.yml | e6884d5d49d4339619119b8e576f4a59623cbf501b75eccb974f1dfdeaa1a0ef |
| test_iraf.sh | fd01d62939f3179d55aeaa4c11a5d1d63b6f7d5b1c176202c833e241142c9a26 |

| 包内代表制品 | 字节数 | SHA256 |
|---|---:|---|
| lib/iraf/bin.linux64/ecl.e | 5736960 | c47dbada6e58b1555e44364b8b17d6ffe8a5ea6fcd05c722eb54c2da17e27400 |
| lib/iraf/bin.linux64/cl.e | 5003776 | 886a879d11a92e0e6567a2bf7c126720e765732a7908036f757e80c80303ee89 |
| lib/iraf/bin.linux64/x_system.e | 2378240 | c3c8ca4ca0aec9c4cf0e87b841d10c47b6576c21422be2f09c1bbd81e7e05054 |
| lib/iraf/bin.linux64/x_nttools.e | 7780864 | 6c17ed137d500316e063f2f621526ec9cbdd7e7934b31fbfabb810a7307bb766 |
| lib/iraf/noao/bin.linux64/x_artdata.e | 5044736 | 1f23ca1b93117bd70a972fbafb48bba1984091d4acc365bcf051955c592ad5f6 |
| lib/iraf/noao/bin.linux64/x_quad.e | 3860992 | 0a1a5410f41edf3f5724fb1ede09d1f9727d8eb6394176bd71af7946d38b301e |
| lib/iraf/unix/bin.linux64/xc.e | 657920 | f87dd50d1db97ef5b9329c041e09f7e44e9921c0668589a5556461752f2bfca6 |
| lib/iraf/unix/bin.linux64/libos.a | 746886 | a9a13e1ab8d092b71fef6e6d3a926f64ed1c4188506f891c6296f864e786f96e |
| lib/iraf/unix/bin.linux64/libf2c.a | 1000072 | d139034945132ff7bcca521638cd545ecd10e07deb7aa79a0909d72dcca6e52a |
| lib/iraf/include/f2c.h | 4938 | ee11bea0efdd15d66c7d7aafb160dd267a016b5d1371cdc314ca9928cefeb88f |
| lib/iraf/unix/hlib/libc/iraf_setjmp.h | 478 | 1a62cdeb3db7e14ffa6a28aa1843838fe33fa00f346506bfd5e17068493efb88 |

本地状态 built。线上 CI/AI、制品仓发布及 C/B 分类以平台结果为准。
