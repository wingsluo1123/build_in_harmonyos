# 用固件自身 CLI 在无 mount/mkfs -d 宿主上构建块设备测试夹具：devnum/参数全 hex、载体零建逐扇区覆盖、GPT 盘脚本自足

- **草稿 ID**: DRAFT-11418-uboot-fixture-staging-hex-carrier
- **来源**: u-boot 2026.07 HarmonyOS PC 适配（OHOS 无 mount/debugfs → 以 sandbox CLI 自建 bootstd E2E 夹具，踩 hex devnum / usb read 参数 / 载体污染 / GPT 盘脚本自足四坑）
- **分类**: testing / sandbox / fixture / device-test
- **状态**: 本地草稿（路径 B 知识库扩展申请中）

## 问题 / 错误签名

- **"Partition Map" 静默缺失**：`part list mmc 10` 看似执行成功（零输出、无报错），实则打到设备 16（-ENODEV），do_part_list 返回 1 不打印。
- **目标文件系统读到全零/FAT 引导扇区字节**：mmc1:1/extlinux/extlinux.conf 经 fatload+md 回读为全零——载体介质曾被测试中途格式化（bootflow_efi 的 mkdosfs 写 0x800 引导扇区），保存副本复用了污染态。
- **复现**：bootstd 53 子测试中 bootflow_cmd_boot/cmd_info/scan_boot/bootstd_images 4 个失败，根因全是夹具数据而非代码缺陷。

## 根因

1. **上游夹具构建依赖 Linux 专用能力**：test/py/tests/test_ut.py 的 setup_bootflow_image/setup_fedora_image/setup_efi_image 用 mount 挂载、`mkfs.vfat -d` 目录注入、debugfs 写 ext2——OHOS 无 mount 权限、busybox mkfs.vfat 无 `-d` 参数、无 debugfs，必须另辟蹊径（纯 dd + busybox mkfs.vfat + mke2fs + 纯 python ext2 构造器 + 固件自身 CLI staging）。
2. **u-boot CLI 数值语义与直觉相反**：blk_get_device_by_str（disk/part.c）用 hextoul 解析设备号；usb read 的扇区号/长度也全按 hex 且不收设备号参数（maxargs=5）——十进制书写会把命令打到错误设备或错误扇区，且部分路径静默无输出。
3. **有状态介质的保存副本不可信**：测试中途会格式化载体（bootflow_efi mkdosfs 写 0x800），运行后保存的副本是污染态；把它当干净起点，等于把 FAT 引导扇区字节当夹具数据。
4. **生成序依赖**：上游 setup_bootflow_image 的 boot.scr 由 mkimage 在夹具构建期生成，ext2 构造器读取它——mkimage 段必须排在文件系统构造段之前，否则 ext2 里是旧/缺失的 boot.scr。
5. **夹具生成脚本必须全套自足**：cros/android 的 GPT 盘（mmc5.img cros kernel 分区；mmc7/mmc8 android boot/vendor_boot 分区，镜像体来自上游 test_abootimg.py 的 gzip hexdump）一度只靠设备上一次性手动运行预生成器留下的镜像——脚本自身不生成这三个盘。全新设备/全新目录上，bootflow_cros/bootstd_images/bootflow_android_v2/v4 四个子测试会静默无盘可挂；残留镜像的内容也无从自证（是哪个版本、哪次跑出来的）。修复：GPT 段并入 mkfixtures.sh，每次运行从零构造（PMBR + 主/备 GPT 头 + 128×128B 分区项 + 分区内容）。

## 最小修复方案

mkfixtures.sh 的载体与 staging 纪律（fixtures/mkfixtures.sh，随 test_package 分发）：

```sh
# 1) 载体零建 + 逐扇区显式覆盖（永不 cp 保存副本）
dd if=/dev/zero of=testflash.bin bs=1M count=4
dd if=$H/extlinux.conf of=testflash.bin bs=512 seek=2048 conv=notrunc   # 0x800
dd if=$H/boot.scr     of=testflash.bin bs=512 seek=2560 conv=notrunc   # 0xa00
# ...initrd 0x880 / dtb 0x8c0 / vmlinuz 0xa40 / testapp.efi 0xc00

# 2) mkimage 段先于文件系统段（boot.scr 被 ext2 构造器消费）
$MKI -C none -A arm -T script -d $H/boot.cmd $H/boot.scr

# 3) staging：设备号/数值全 hex（设备 10 = "mmc a"）
$U -d test-mmc4.dtb -c "usb start; usb read 0x1000000 0x800 4; \
  fatmkdir mmc 1:1 extlinux; fatwrite mmc 1:1 0x1000000 extlinux/extlinux.conf 0x253; \
  ...; part list mmc a; fatls mmc a:1; ext4ls mmc a:2; exit"

# 4) 回读闭环：每个 fatwrite 后 fatload + md.b 与源文件逐字节比对

# 5) GPT 盘每跑从零生成（mmc5 cros / mmc7 mmc8 android），不依赖任何预置镜像
python3 $H/gen-gpt-fixtures.py $H/abootimg-hexdumps.py $F   # 纯标准库 GPT 构造器
```

要点：

- **载体与目标介质分离**：mmc1.img/mmc4.img/flash1.img 是测试真正的夹具（测试期被格式化是预期行为）；usb 载体只是 staging 传输层，测试从不读它的裸扇区（grep test/boot/*.c 零 usb read/write 直读实证）——因此载体可以零建+覆盖，且每次运行重建。
- **hex 书写纪律**：所有 devnum/扇区/长度参数按 hex 书写；设备 10 写作 `mmc a`。
- **回读闭环**：staging 后 fatload+md 与源逐字节比对，杜绝"命令静默打到错设备"。
- **脚本自足**：全部夹具（含 mmc5/7/8 GPT 盘）必须由脚本自身每次从零生成——预置镜像/手动产物=全新环境静默缺件 + 内容不可自证；GPT 构造用纯标准库 python（OHOS 无 sgdisk/parted），android 镜像体从上游 hexdump 解码，保持与上游字节一致。

## 验证结果

| 环境 | 结果 |
|------|------|
| OHOS PC aarch64 真机 | 夹具重建后 bootstd 53 子测试从 19 失败收敛至 4 失败（含 hex devnum 修复后的 part list mmc a 正常出 Partition Map）；载体零建 + GPT 段合并修复待设备复验 |
| 排障佐证 | 隔离运行实证 "mmc 10" 静默解析为设备 16；dd 侧 0x800 良好但 usb-read 侧读到 flash1.img 的 mkdosfs 签名 → 定位载体污染；GPT 盘缺段经"移除预置镜像后四个子测试失败"路径定位 |
| 本地生成验证 | gen-gpt-fixtures.py 对 abootimg-hexdumps.py 独立运行：mmc5/7/8.img 各 20,971,520 字节，LBA1 处 EFI PART 签名齐（cros 分区体 22,528B / android boot 12,288B / vendor_boot 20,480B 与上游 hexdump 解码尺寸一致） |

## 禁止策略

- 禁止复用保存过的载体副本（cp stage-testflash2.bin 之类）——测试中途格式化的副本是污染态，症状与代码缺陷不可区分，排障走错方向。
- 禁止设备号按十进制书写——"mmc 10" 静默打到设备 16 且零报错，夹具校验形同虚设。
- 禁止夹具脚本依赖脚本外一次性预生成的镜像（预置 .img / 手动跑过才存在）——全新环境静默缺夹具，且预置内容无法自证版本。

## 相关

- 相似条目：DRAFT-box2d-2.4.1-ctest-empty-suite-false-pass（同属"成功返回 ≠ 行为发生"的测试机制陷阱）
- 引用原则：upstream-precedent（夹具脚本随 test_package 分发，不改动上游任何测试源码）、real-evidence-over-assumption、test-surface-preservation
