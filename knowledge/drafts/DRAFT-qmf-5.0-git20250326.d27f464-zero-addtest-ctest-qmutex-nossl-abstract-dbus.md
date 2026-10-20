# DRAFT-qmf-5.0-git20250326.d27f464-zero-addtest-ctest-qmutex-nossl-abstract-dbus
> 上游零add_test时配方侧注入CTest注册与无SysV无SSL鸿蒙下Qt库的IPC替换及去守卫适配
## 问题特征（真实日志片段/标记）
- ctest_upstream.log仅142字节：Test project ... No tests were found!!!，harness曾以字符串回退虚报discovered=30 executed=0 passed=0 failed=0 skipped=30
- 注册补丁后29项真实运行：6/29 Test #6 tst_qmail_listmodels SIGSYS***Exception 0.17 sec，QCRITICAL Failed to connect D-Bus，15个触库用例全SIGSYS，14个纯值用例通过
- OHOS无SSL变体编译失败：imapprotocol.cpp:592 no member named 'setMailAuthentication' in 'ImapConfigurationEditor'；tst_smtp.cpp:114 no member named 'Encrypt_SSL' in 'QMailTransport'
- 会话总线失败：dbus-daemon Failed to bind socket /tmp/dbus-xxx Read-only file system，Socket name too long，messageserver poll=1 logsize=0，tst_qmailstorageaction isMessageServerRunning FALSE
- 修复轮连续3轮未过且DRAFT-E738等既有条目判reject/adapt失败，最终靠自研组合通过门禁，证明技能库无法解决
## 根因
- 章程性零注册：tests/tst_*/CMakeLists仅add_executable加install，零add_test，顶层仅include(CTest)，BUILD_TESTING与目录假设均证伪
- 鸿蒙无SysV IPC：locks.cpp ProcessMutexPrivate继承QSystemSemaphore，经semget/semop调用内核直接SIGSYS杀进程，不可捕获，QSignalSpy计数矛盾因Exception行漏计
- 鸿蒙无SSL：qtbase-sql-dbus/6.11.1定义QT_NO_SSL，imap/pop/smtp纯键值存取与Encrypt_SSL纯整数枚举被包进守卫，调用方无条件使用即缺成员
- 只读tmp加长路径：预检home约90字符，unix tmpdir文件套接字在/tmp下RO无法bind，长路径又超sun_path 108上限，需换非文件系统轴
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. conanfile.py新增_patch_register_qmf_tests：从tests/CMakeLists解析29个无条件用例名，校验同名add_executable存在，顶层追加add_test注册已构建二进制，WORKING_DIRECTORY指向各用例源码目录，tst_crypto按条件记environment缺口，总和恒等30减通过数
2. generate()仅OHOS定义QMF_USE_QMUTEX_LOCKS，新增_patch_locks_qmutex_on_ohos将locks.cpp包进条件分支：按key共享进程内QMutex注册表，调用方每次新建实例故须共享，永不销毁，SQLite文件锁保DB完整，Linux保持SysV原路径
3. 新增_patch_qt_no_ssl_config对6个纯配置文件逐行剥离QT_NO_SSL守卫行，不动传输层QSsl代码；新增_patch_transport_encrypt_enum仅锚定替换qmailtransport.h EncryptType枚举块使Encrypt_SSL/TLS常驻，其余7处守卫保留并计数校验
4. _ensure_dbus_session生成dbus-session.conf改用unix:abstract=/tmp/qmf-dbus-唯一名，保留HOME与XDG_RUNTIME_DIR长路径，预置conan依赖lib/lib64到LD_LIBRARY_PATH并显式config-file拉起，绕过只读tmp与超限
5. MANIFEST.yml与pr-body披露纯harness接入与ohos_feature缺口；build()顺序调用上述补丁；真机执行ctest --output-on-failure --timeout 300验证29项执行与test_package编译通过
## 禁止策略
- 禁止以字符串计数回退虚构discovered=30掩盖No tests were found；零注册时如实报0
- 禁止将SIGSYS崩溃标记通过或加信号处理绕过；须替换IPC实现
- 禁止改上游测试断言凑恒等式或将缺依赖包装成豁免；网络三项如实列environment/ohos_feature证据
## 与相近条目的边界（查重）
- DRAFT-E738等QT_NO_SSL与IPC条目判reject/adapt：或只去守卫未处理Encrypt枚举，或用信号处理/文件锁替代未处理注册表共享，或用短tmp未处理RO，均未通过本任务四域叠加
- 本条目仅适用于零add_test加无SysV加QT_NO_SSL加只读tmp同时出现的Qt消息框架类库；单一ushort失败沿用原条目
## 适用判断
- ctest报No tests were found但tst_*二进制已构建，且源码仅add_executable无add_test时适用注册注入
- Qt库用QSystemSemaphore/QSharedMemory且触库用例集中SIGSYS而纯计算通过时适用QMutex注册表替换
- OHOS SSL-less下纯键值配置缺成员或Encrypt_SSL缺枚举，且无Qsock调用时适用去守卫；dbus在/tmp下RO或超108字符时适用abstract套接字
