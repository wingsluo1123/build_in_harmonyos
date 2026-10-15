#!/bin/sh
# Build the sandbox u-boot bootstd E2E fixture images for the test_package.
#
# Reproduces the upstream pytest fixtures (test/py/tests/test_ut.py
# setup_bootflow_image / setup_fedora_image / setup_efi_image / RAUC
# DiskHelper spec) with pure dd + mkfs.vfat (standalone on Linux hosts,
# busybox applet on OHOS) + mke2fs + the pure-python ext2 builder (OHOS
# has no mke2fs -d / debugfs, and u-boot's own ext4 driver is the
# validation oracle).
#
# Env (all required):
#   U_BOOT_SANDBOX  u-boot sandbox binary
#   U_BOOT_MKIMAGE  mkimage from the package
#   U_BOOT_DTB      arch/sandbox/dts/test.dtb from the build
#   U_BOOT_TESTAPP  lib/efi_loader/testapp.efi from the build
#   HOST_FIXTURES   directory with the static fixture inputs:
#                     boot.cmd extlinux.conf initrd.bin gen-gpt-fixtures.py
#                     abootimg-hexdumps.py fixture-blobs.py
#                     (the 13 binary inputs mbr-mmc1.bin mbr-mmc4.bin
#                     mbr-scsi.bin mbr-flash1.bin mbr-mm10.bin boot.bmp
#                     inf.gz sandbox.dtb cedit.dtb tools/logos/denx.bmp
#                     tools/logos/denx-comp.bmp
#                     tools/logos/denx-16bpp.bmp.gz
#                     tools/logos/denx-24bpp.bmp.gz ship as base64 text
#                     inside fixture-blobs.py and are materialized into $F
#                     below)
#   UT_WORKDIR      scratch dir (images are created here)
F=${UT_WORKDIR:?set UT_WORKDIR}
H=${HOST_FIXTURES:?set HOST_FIXTURES}
U=${U_BOOT_SANDBOX:?set U_BOOT_SANDBOX}
MKI=${U_BOOT_MKIMAGE:?set U_BOOT_MKIMAGE}
DTB=${U_BOOT_DTB:?set U_BOOT_DTB}
TAPP=${U_BOOT_TESTAPP:?set U_BOOT_TESTAPP}
# mkfs.vfat: standalone tool on Linux hosts (CI), busybox applet on OHOS
if command -v mkfs.vfat >/dev/null 2>&1; then MKFS_VFAT=mkfs.vfat; else MKFS_VFAT="busybox mkfs.vfat"; fi
export HOME=${HOME:-/tmp}
export TMPDIR=$F/tmp
export U_BOOT_PERSISTENT_DATA_DIR=$F
mkdir -p $F/tmp
cd $F || exit 1

# seed the workdir from the (read-only) fixture inputs: everything below
# builds inside $F, so HOST_FIXTURES can be a pristine package dir
if [ "$F" != "$H" ]; then
    for f in boot.cmd extlinux.conf initrd.bin abootimg-hexdumps.py; do
        cp $H/$f $F/$f || exit 1
    done
fi
# the 13 binary inputs ship as base64 text (gitcode's .diff endpoint drops
# binary patch payloads, which would make the PR unapplyable); decode them
# byte-exactly into $F -- every payload's sha256 is pinned in the script.
# Additions: cedit.dtb (read by the cedit SDL tests as `cedit load hostfs -
# cedit.dtb`) and tools/logos/denx*.bmp(.gz) (dm video BMP tests, cwd-
# relative). cedit.dtb is prebuilt: upstream pytest generates it via
# tools/expo.py, which needs the source tree + dtc + a writable /tmp; the
# shipped file is that same upstream generator's deterministic output over
# test/boot/files/{expo_ids.h,expo_layout.dts} (two runs byte-identical,
# sha256 pinned in fixture-blobs.py).
python3 $H/fixture-blobs.py $F || exit 1

# lib_test_membuf_readline reads 'README' as sample data (upstream pytest
# runs with CWD = the source tree root, where README exists). test_uboot.sh
# seeds $F with the packaged upstream README copy first (fixtures/README,
# byte-identical to the upstream source-tree README); ONLY fall back to a
# stub when this script runs standalone, so the two runners share one data
# source and this step never clobbers the upstream copy.
[ -f $F/README ] || printf 'U-Boot test fixture: sample text for lib_test_membuf_readline.\n' > $F/README

echo "== sizes =="
dd if=/dev/zero of=mmc1.img bs=1M count=20 2>/dev/null
dd if=/dev/zero of=mmc4.img bs=1M count=20 2>/dev/null
dd if=/dev/zero of=scsi.img bs=1M count=2 2>/dev/null
dd if=/dev/zero of=mmc6.img bs=1M count=12 2>/dev/null
dd if=/dev/zero of=mmc9.img bs=1M count=32 2>/dev/null
dd if=/dev/zero of=spi.bin bs=1M count=2 2>/dev/null
dd if=/dev/zero of=testflash.bin bs=1M count=4 2>/dev/null
# test_ut_dm_init: testflash.bin = b'this is a test' zero-padded to 4MB
# (dm_test_usb_flash reads block 0 through the usb mass-storage emulation
# and asserts that exact string; the rest of the stick stays zero)
printf 'this is a test' | dd of=testflash.bin conv=notrunc 2>/dev/null
dd if=/dev/zero of=flash1.img bs=1M count=20 2>/dev/null
dd if=/dev/zero of=testflash2.bin bs=1M count=1 2>/dev/null
dd if=/dev/zero of=mmc10.img bs=1M count=37 2>/dev/null
dd if=/dev/zero of=image.bin bs=1M count=1 2>/dev/null
dd if=/dev/zero of=i2c.bin bs=1M count=1 2>/dev/null

echo "== MBRs =="
dd if=$F/mbr-mmc1.bin of=mmc1.img conv=notrunc 2>/dev/null
dd if=$F/mbr-mmc4.bin of=mmc4.img conv=notrunc 2>/dev/null
dd if=$F/mbr-scsi.bin of=scsi.img conv=notrunc 2>/dev/null
dd if=$F/mbr-flash1.bin of=flash1.img conv=notrunc 2>/dev/null
dd if=$F/mbr-mm10.bin of=mmc10.img conv=notrunc 2>/dev/null

echo "== mkimage outputs (before the ext2 build: boot.scr goes into it) =="
$MKI -C none -A arm -T script -d $F/boot.cmd $F/boot.scr
$MKI -f auto -d $F/inf.gz $F/vmlinuz
VM_SZ=$(stat -c%s $F/vmlinuz)
VM_HEX=$(printf '%x' $VM_SZ)
VM_SECS=$(printf '%x' $(( (VM_SZ + 511) / 512 )))
# testapp.efi 尺寸随构建而定（EFI 测试按整文件读 BOOTSBOX.EFI），
# 读扇区数与 fatwrite 长度都从真实字节数推导，杜绝硬编码漂移
TAPP_SZ=$(stat -c%s $TAPP)
TAPP_HEX=$(printf '%x' $TAPP_SZ)
TAPP_SECS=$(printf '%x' $(( (TAPP_SZ + 511) / 512 )))
EXT_SZ=$(stat -c%s $F/extlinux.conf)
EXT_HEX=$(printf '%x' $EXT_SZ)

echo "== filesystems =="
dd if=/dev/zero of=$F/mmc1p1.vfat bs=1M count=18 2>/dev/null
$MKFS_VFAT -F 32 $F/mmc1p1.vfat 2>&1 | tail -1
dd if=$F/mmc1p1.vfat of=mmc1.img bs=1M seek=1 conv=notrunc 2>/dev/null

dd if=/dev/zero of=$F/mmc1p2.ext2 bs=1M count=1 2>/dev/null
mke2fs -q $F/mmc1p2.ext2 2>&1 | tail -1 || busybox mke2fs $F/mmc1p2.ext2 2>&1 | tail -1
dd if=$F/mmc1p2.ext2 of=mmc1.img bs=1M seek=19 conv=notrunc 2>/dev/null

# test_ut_dm_init: FsHelper('ext2', 2, '2MB').mk_fs() — dm_test_host /
# dm_test_host_dup / dm_test_cmd_host attach this image via
# os_persistent_file() and fs_write into it (empty ext2 volume, 2MB)
dd if=/dev/zero of=$F/2MB.ext2.img bs=1M count=2 2>/dev/null
mke2fs -q -t ext2 $F/2MB.ext2.img 2>&1 | tail -1 || busybox mke2fs -t ext2 $F/2MB.ext2.img 2>&1 | tail -1
od -An -tx2 -j 1080 -N 2 $F/2MB.ext2.img | tr -d ' \n' | grep -qi ef53 || {
    echo "ERROR: 2MB.ext2.img has no ext2 superblock magic" >&2
    exit 1
}

# mmc4p1 /boot is built by the pure-python ext2 builder (no mke2fs -d /
# debugfs on OHOS; u-boot's ext4 layer has no mkdir either)
python3 $H/build-ext2.py $F $F/mmc4p1.ext2
dd if=$F/mmc4p1.ext2 of=mmc4.img bs=1M seek=1 conv=notrunc 2>/dev/null
echo "sb magic (want ef53):"
od -An -tx2 -j 1080 -N 2 $F/mmc4p1.ext2

# flash1 p1: FAT16 (upstream setup_efi_image mkfs.vfat default on 18MB)
# with /EFI/BOOT/BOOTSBOX.EFI = build's lib/efi_loader/testapp.efi; the
# app file is injected by staging run 2 below (carrier sector 0xC00)
dd if=/dev/zero of=$F/flash1p1.vfat bs=1M count=18 2>/dev/null
$MKFS_VFAT $F/flash1p1.vfat 2>&1 | tail -1
dd if=$F/flash1p1.vfat of=flash1.img bs=512 seek=2048 conv=notrunc 2>/dev/null

# mmc10: A/B RAUC layout (upstream DiskHelper spec): p1/p3 FAT32 boot
# 8MB (bootable), p2/p4 ext4 root 10MB. bootmeth_rauc only stats the
# partitions (part_get_info + fs_set_blk_dev), never reads files, so the
# filesystems stay empty.
dd if=/dev/zero of=$F/mm10p1.vfat bs=1M count=8 2>/dev/null
$MKFS_VFAT -F 32 $F/mm10p1.vfat 2>&1 | tail -1 || $MKFS_VFAT $F/mm10p1.vfat 2>&1 | tail -1
dd if=$F/mm10p1.vfat of=mmc10.img bs=512 seek=2048 conv=notrunc 2>/dev/null
dd if=/dev/zero of=$F/mm10p2.ext4 bs=1M count=10 2>/dev/null
mke2fs -q -t ext4 $F/mm10p2.ext4 2>&1 | tail -1 || busybox mke2fs $F/mm10p2.ext4 2>&1 | tail -1
dd if=$F/mm10p2.ext4 of=mmc10.img bs=512 seek=18432 conv=notrunc 2>/dev/null
dd if=$F/mm10p1.vfat of=mmc10.img bs=512 seek=38912 conv=notrunc 2>/dev/null
dd if=$F/mm10p2.ext4 of=mmc10.img bs=512 seek=55296 conv=notrunc 2>/dev/null

dd if=/dev/zero of=1MB.fat32.img bs=1M count=1 2>/dev/null
$MKFS_VFAT -F 32 1MB.fat32.img 2>&1 | tail -1
# FsHelper('fat32', 1, '1MB'): dm_test_host / _dup / _cmd_host attach and
# fs_write this volume; a broken image would only surface as a confusing
# fs-type mismatch inside the test, so verify the BPB label (pipelines
# hide mkfs's exit status, hence the explicit check)
od -An -c -j 82 -N 5 1MB.fat32.img | tr -d ' \n' | grep -q FAT32 || {
    echo "ERROR: 1MB.fat32.img is not FAT32 ($MKFS_VFAT -F 32 failed)" >&2
    exit 1
}

echo "== GPT images (mmc5 cros / mmc7+mmc8 android) =="
# bootflow_cros/bootstd_images (mmc5), bootflow_android_v2 (mmc7),
# bootflow_android_v4 (mmc8) need GPT-labelled sticks. The generator
# builds PMBR + primary/backup GPT with hand-built cros kernel part
# (mmc5) and android boot/vendor_boot images decoded from the gzip hex
# dumps of upstream test/py/tests/test_android/test_abootimg.py
# (abootimg-hexdumps.py ships those dumps standalone).
python3 $H/gen-gpt-fixtures.py $F/abootimg-hexdumps.py $F
for g in mmc5.img mmc7.img mmc8.img; do
    echo "$g: $(stat -c%s $F/$g) bytes"
    od -An -c -j 512 -N 8 $F/$g
done

echo "== usb staging carrier =="
# stage.img is the ONLY file the three DT flash-sticks reference (patched
# below), so the usb storage device INDEX cannot select the wrong file.
# Sandbox enumerates the sticks in an order that is NOT stable across
# runs: a mis-indexed usb read fails ("0 blocks read: ERROR") and the
# following fatwrite then silently stores stale RAM as extlinux.conf /
# vmlinuz (this was the real root cause of the 'carrier pollution' bootstd
# failures). One file behind every index makes reads index-free.
# Payload sectors live in [38912,40960): past p1 (2048+36864 sectors),
# inside the 20MB disk, invisible to the partition and fs layers.
cp flash1.img stage.img
dd if=$F/extlinux.conf of=stage.img bs=512 seek=38912 conv=notrunc 2>/dev/null  # 0x9800
dd if=$F/initrd.bin of=stage.img bs=512 seek=38914 conv=notrunc 2>/dev/null      # 0x9802
dd if=$F/sandbox.dtb of=stage.img bs=512 seek=38915 conv=notrunc 2>/dev/null     # 0x9803
dd if=$F/vmlinuz of=stage.img bs=512 seek=38917 conv=notrunc 2>/dev/null         # 0x9805
dd if=$TAPP of=stage.img bs=512 seek=38920 conv=notrunc 2>/dev/null              # 0x9808
# testflash.bin stays a plain non-partitioned stick for the ut tests
dd if=$F/extlinux.conf of=testflash.bin bs=512 seek=2048 conv=notrunc 2>/dev/null
dd if=$F/initrd.bin of=testflash.bin bs=512 seek=2176 conv=notrunc 2>/dev/null
dd if=$F/sandbox.dtb of=testflash.bin bs=512 seek=2240 conv=notrunc 2>/dev/null
dd if=$F/boot.scr of=testflash.bin bs=512 seek=2560 conv=notrunc 2>/dev/null
dd if=$F/vmlinuz of=testflash.bin bs=512 seek=2624 conv=notrunc 2>/dev/null
dd if=$TAPP of=testflash.bin bs=512 seek=3072 conv=notrunc 2>/dev/null

echo "== u-boot staging run (mmc1 files + flash1 EFI app + partition peeks) =="
# sandbox SDRAM is 0..0x10000000; 0x1000000 buffer is well clear of
# u-boot's own relocation image at the top. usb read parses ALL args as
# hex and takes no device number (maxargs=5); fatwrite sizes are hex.
# blk devnums are hex too (hextoul): mmc device 10 is addressed as "mmc a"
# ("mmc 10" resolves to device 16, -ENODEV, do_part_list prints nothing).
# mmc4/mmc10 are status=disabled in test.dtb (bootstd ut tests bind them
# themselves); staging addresses them via a patched dtb with both on and
# the three usb sticks all pointing at stage.img.
python3 $H/patch-dtb.py $DTB $F/test-stage.dtb mmc4 mmc10 --stick-name stage.img
A=0x1000000
$U -d $F/test-stage.dtb -c "usb start; usb dev 0; usb read $A 0x9800 2; fatmkdir mmc 1:1 extlinux; fatwrite mmc 1:1 $A extlinux/extlinux.conf 0x$EXT_HEX; usb read $A 0x9802 1; fatwrite mmc 1:1 $A initramfs-5.3.7-301.fc31.armv7hl.img 0x7; usb read $A 0x9803 1; fatmkdir mmc 1:1 dtb-5.3.7-301.fc31.armv7hl; fatwrite mmc 1:1 $A dtb-5.3.7-301.fc31.armv7hl/sandbox.dtb 0x48; usb read $A 0x9805 0x$VM_SECS; fatwrite mmc 1:1 $A vmlinuz-5.3.7-301.fc31.armv7hl 0x$VM_HEX; usb read $A 0x9808 0x$TAPP_SECS; part list usb 0; fatmkdir usb 0:1 EFI; fatmkdir usb 0:1 EFI/BOOT; fatwrite usb 0:1 $A EFI/BOOT/BOOTSBOX.EFI 0x$TAPP_HEX; fatls usb 0:1 EFI/BOOT; fatls mmc 1:1; fatls mmc 1:1 extlinux; part list mmc a; fatls mmc a:1; ext4ls mmc 4:1 boot; ext4size mmc 4:1 boot/boot.cmd; ext4size mmc 4:1 boot/boot.bmp; ext4size mmc 4:1 boot/boot.scr; exit" < /dev/null > $F/stage-run.log 2>&1
echo "staging RC=$?"
# grep can race u-boot's buffered output landing in the log file; retry briefly
grepr() { i=0; while [ $i -lt 40 ]; do grep -aq -e "$1" "$2" && return 0; i=$((i + 1)); sleep 0.5; done; return 1; }
grepr 'Partition Map' $F/stage-run.log || true
grep -a -e 'blocks read' -e written -e ext4size -e 'file(s), ' -e 'Partition Map' $F/stage-run.log | head -30
NREAD=$(grep -ac 'blocks read: OK' $F/stage-run.log)
NERR=$(grep -ac 'blocks read: ERROR' $F/stage-run.log)
echo "staging: usb reads OK=$NREAD ERROR=$NERR"
if [ "$NREAD" -lt 5 ] || [ "$NERR" != "0" ]; then
    echo "ERROR: staging transport did not read all 5 payloads" >&2
    exit 1
fi

echo "== copy the written p1 region into the clean flash1.img =="
dd if=stage.img of=flash1.img bs=512 skip=2048 seek=2048 count=36864 conv=notrunc 2>/dev/null

echo "== staging verification (payload in RAM vs what u-boot reads back) =="
$U -d $F/test-stage.dtb -c "usb start; usb dev 0; usb read $A 0x9800 2; fatload mmc 1:1 0x1100000 extlinux/extlinux.conf; cmp.b $A 0x1100000 0x$EXT_HEX; usb read $A 0x9808 0x$TAPP_SECS; fatload usb 0:1 0x1100000 EFI/BOOT/BOOTSBOX.EFI; cmp.b $A 0x1100000 0x$TAPP_HEX; usb read $A 0x9805 0x$VM_SECS; fatload mmc 1:1 0x1100000 vmlinuz-5.3.7-301.fc31.armv7hl; cmp.b $A 0x1100000 0x$VM_HEX; exit" < /dev/null > $F/stage-verify.log 2>&1
echo "verify1 RC=$?"
# every payload must round-trip byte-identical (cmp.b prints the count of
# bytes found equal; a mismatch prints a lower count). Hard-fail otherwise,
# so a broken transport can never silently ship a corrupt image again.
for want in $EXT_SZ $TAPP_SZ $VM_SZ; do
    grepr "Total of $want byte(s) were the same" $F/stage-verify.log || {
        echo "ERROR: cmp.b never reported $want identical bytes" >&2
        exit 1
    }
done
grep -a 'were the same' $F/stage-verify.log

echo "== verify the shipped flash1.img itself (sticks -> flash1.img) =="
rm -f stage.img
python3 $H/patch-dtb.py $DTB $F/test-stage.dtb mmc4 mmc10 --stick-name flash1.img
$U -d $F/test-stage.dtb -c "usb start; usb dev 0; part list usb 0; fatls usb 0:1 EFI/BOOT; fatload usb 0:1 $A EFI/BOOT/BOOTSBOX.EFI; exit" < /dev/null >> $F/stage-verify.log 2>&1
echo "verify2 RC=$?"
grepr 'BOOTSBOX' $F/stage-verify.log || {
    echo "ERROR: BOOTSBOX.EFI not found on the shipped flash1.img" >&2
    exit 1
}
grep -a -e 'BOOTSBOX' -e 'Partition Map' $F/stage-verify.log | tail -4
echo "mkfixtures complete (staging + round-trip verification passed)"
