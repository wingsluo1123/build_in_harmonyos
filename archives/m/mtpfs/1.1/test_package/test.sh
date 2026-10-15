#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke + consumer test for mtpfs 1.1
# Runs in conanrun env (PATH includes installed bin/)
# R25: shell scripts must start with set -euo pipefail
set -euo pipefail

# R34/L1e: 显式断言被测包产物真实存在——破坏性反向验证会移走 bin/，
# 必须在此明确失败（避免被 && 短路豁免或 rc 宽容集合吞掉，误判"测试通过"）
command -v mtpfs >/dev/null 2>&1 || {
    echo "FAIL mtpfs binary not found in PATH (package artifact missing?)"
    exit 1
}

echo "[test] mtpfs --help"
# 真 mtpfs（mtpfs.c main）在 --help 下先做 libmtp 设备枚举打印标题再 exit 0；
# 断言真实输出内容而非仅退出码（空壳/假包二进制无此输出）
if ! help_out=$(mtpfs --help 2>&1); then
    echo "FAIL mtpfs --help exited non-zero (binary missing/broken?)"
    exit 1
fi
echo "$help_out" | grep -q "Listing raw device(s)" || {
    echo "FAIL mtpfs --help output missing device enumeration header (not real mtpfs?)"
    exit 1
}
echo "OK --help exited 0 with real device-enumeration output"

echo "[test] mtpfs rejects mounting a nonexistent target without hanging"
# 真机无 MTP 设备/无 /dev/fuse：预期在 libmtp 设备枚举阶段退出；
# rc 0(异常成功)/1/255(libmtp 无设备) 均可接受；超时 124 = 挂死 = 失败；
# 其余 rc（126/127/139：不可执行/丢失/崩溃）一律拒绝——证明测试实质
# 依赖包产物（R34）
set +e
timeout 30 mtpfs /nonexistent-target > mtpfs_mount_out.txt 2>&1
rc=$?
set -e
case "$rc" in
    0|1|255)
        grep -q "Listing raw device(s)" mtpfs_mount_out.txt || {
            echo "FAIL missing-target run output missing device enumeration header (not real mtpfs?)"
            exit 1
        }
        ;;
    124)
        echo "FAIL mtpfs hung on missing device"
        exit 1
        ;;
    *)
        echo "FAIL mtpfs exited rc=$rc (binary broken/missing/not executable?)"
        exit 1
        ;;
esac
rm -f mtpfs_mount_out.txt
echo "OK mtpfs exited rc=$rc on missing-device path (in {0,1,255}, no hang)"
echo "ALL TESTS PASSED"
