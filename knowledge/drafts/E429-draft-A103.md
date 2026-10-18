# POA共识测试的最小路径长度

heaviest_bundle.c在path_length < 10时停止生成共识；相同8残基序列能比对，
但不能产生共识。测试应使用12残基ACGTACGTACGT，保留严格内容/长度/图断言，
不改上游算法。实际OHOS7 Beta QEMU：CLI17/17、库API8/8通过。

验证：`python3 scripts/ohc-run.py conan-verify poa 2.0-20060928 --profile qemu-ohos7`。
不得删除共识断言或以退出码代替。官方框架将OHC_AGENT_ID=A1038截为A103；
实际认领账号为A1038。原始失败日志本地保留。
