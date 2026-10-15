# OpenZFS 2.4.3 用户态栈在 OHOS 的内核/用户态边界适配（--with-config=user 可行性全链实证）

## 背景

OpenZFS 2.4.3 是"内核文件系统 + 用户态工具链"混合体：深度依赖 Linux 内核接口（SPL 层/内核模块/udev/libudev），任务卡 #12370 判定为路径 C 高难度挑战件（"私有系统接口"正中靶心）。可行性先研的三个问题全部得出确定性答案：

1. **libzfs 用户态库+libnv 是否可无内核模块构建**——可以。上游官方 `./configure --with-config=user` 路径（config/zfs-build.m4 的 ZFS_CONFIG case）只走 ZFS_AC_CONFIG_USER，完全不触碰内核态；OHOS aarch64 宿主上 configure RC=0、make 全量 RC=0 实证。
2. **ZED/驱动等内核态组件裁剪面**——上游条件编译天然裁剪：module/（内核模块）在 user 配置下不进 SUBDIRS；zed_disk_event.c 有完整 `#ifdef HAVE_LIBUDEV` 守卫（user_libudev=no 时整文件空化）；mount helper 的内核 ioctl 路径运行时失败（诚实降级）。无需改源码即可裁掉全部内核态。
3. **替代方案（libnv/libuutil 子集）不需要**——全量用户态可行，未走子集退路。

## 内核/用户态边界的三层处理

- **构建期边界**：`--with-config=user` 是上游官方的边界开关；fatal 依赖仅 5 个（zlib/libuuid/libblkid/libcrypto/libtirpc，ohpcd 仓全有），可降级依赖（libudev/libaio/libunwind/pam/libfetch）全部走 check 路径自动禁用。
- **链接期边界**：musl 与 glibc 的差异用"弱符号 no-op"处理 pthread_cancel 族/addmntent——这些符号只在内核交互 teardown 路径被引用，OHOS 无 ZFS 内核模块时天然不可达，弱定义保证可链接且运行时强定义（如存在）优先。
- **运行期边界**：libzfs_init()/libzfs_core_init() 在无 /dev/zfs 时诚实返回 NULL/非零（上游行为）；zfs/zpool CLI 打印上游 "cannot be auto-loaded" 消息非零退出——不伪装成功。

## 用户态测试的保真度分层（无内核环境下的上游测试真跑）

- **最高保真**：ztest——libzpool 在用户态实现完整池层（SPA/metaslab/DMU/ZAP/ARC），ztest -T 60 -s 64M 完整跑通（RC=0），覆盖 spa_create/事务/checkpoint/freeze/zdb 校验全流程。
- **次级**：tests/zfs-tests/cmd 下的单元测试二进制（sha2/edonr/skein/blake3 算法正确性向量、btree 数据结构 600 万插删压力）——均 RC=0。
- **不可跑**：ZTS 全量 1553 注册用例（common.run 164 sections/1372 例 + linux.run 45 sections/181 例），每例需 root+losetup/dmsetup 回环盘+ZFS 内核模块 ioctl——环境限制，逐项豁免。

## 验证

- OHOS aarch64 宿主（本机即目标环境）全量构建 RC=0：6 库（.so+.a 双形态，上游 soname 保留）+ 15 个 CLI
- make install DESTDIR staging RC=0
- 上游测试真跑：ztest RC=0 + 单元测试 122 向量 OK + btree 4 子测试 OK
- 消费者测试（test_package）：libnvpair 编解码往返/libuutil 列表/libzfs 句柄边界 13 断言全过
