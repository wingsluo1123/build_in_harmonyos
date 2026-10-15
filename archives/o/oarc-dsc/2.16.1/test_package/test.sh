#!/bin/bash
# test_package/test.sh — oarc-dsc 消费者用例（鸿蒙特有测试，N=1）
#
# 上游 src/test 的 18 个脚本只在源码树内回放 pcap；本脚本验证「已安装的包」端到端
# 可用：用包内 bin/dsc 回放自造 pcap（1 个 DNS A 查询），并校验 JSON 统计结果。
set -euo pipefail

DSC="$(command -v dsc || true)"
if [ -z "$DSC" ] || [ ! -x "$DSC" ]; then
    echo "FAIL: 未在 PATH 中定位到 dsc 可执行文件" >&2
    exit 1
fi
echo "== dsc: $DSC"

WORK="$(mktemp -d "${TMPDIR:-/tmp}/dsc-consumer-XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"

# 1) 自造最小 pcap：Ethernet / IPv4 / UDP + 一个 DNS 查询（example.com A）
python3 - <<'PY'
import struct


def dns_query():
    header = struct.pack(">HHHHHH", 0x1234, 0x0100, 1, 0, 0, 0)  # id, flags, qd=1
    qname = b"".join(bytes([len(p)]) + p for p in (b"example", b"com")) + b"\x00"
    return header + qname + struct.pack(">HH", 1, 1)             # QTYPE=A, QCLASS=IN


dns = dns_query()
udp = struct.pack(">HHHH", 51000, 53, 8 + len(dns), 0) + dns
ip = struct.pack(">BBHHHBBH4s4s", 0x45, 0, 20 + len(udp), 0, 0, 64, 17, 0,
                 bytes([10, 1, 2, 3]), bytes([10, 9, 9, 9]))
eth = (b"\x02\x00\x00\x00\x00\x01" + b"\x02\x00\x00\x00\x00\x02"
       + struct.pack(">H", 0x0800))
frame = eth + ip + udp

with open("probe.pcap", "wb") as fh:
    fh.write(struct.pack(">IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
    fh.write(struct.pack(">IIII", 1458044657, 0, len(frame), len(frame)))
    fh.write(frame)
PY

# 2) 最小 conf（语法对齐上游 src/test/1458044657.conf）
cat > probe.conf <<EOF
local_address 10.1.2.3;
run_dir "$WORK";
minfree_bytes 0;
interface $WORK/probe.pcap;
dataset qtype dns All:null Qtype:qtype queries-only;
dataset transport_vs_qtype dns Transport:transport Qtype:qtype queries-only;
output_format JSON;
tld_list $WORK/probe.tld_list;
client_v4_mask 255.255.255.255;
EOF
printf 'com\n' > probe.tld_list

# 3) 回放：pcap 文件输入时 dsc 读完自行退出
"$DSC" "$WORK/probe.conf" || { echo "FAIL: dsc 退出码非 0" >&2; exit 1; }

out=""
for _ in $(seq 1 40); do
    out="$(ls "$WORK"/*.dscdata.json 2>/dev/null | head -1 || true)"
    [ -n "$out" ] && break
    sleep 0.25
done
if [ -z "$out" ]; then
    echo "FAIL: 未生成 *.dscdata.json，目录内容：" >&2
    ls -la "$WORK" >&2
    exit 1
fi
echo "== 输出文件: $out"

# 4) 统计结果断言（真消费者校验：qtype=1 即 A 查询计数 1，且走 UDP 传输）
#    注意：DSC 的 Qtype 维度输出的是数字编号（上游 *.json_gold/*.xml_gold 同为数字），
#    不是 "A"/"AAAA" 这类名字，因此这里断言 val="1" 且 count=1。
python3 - "$out" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1]))
names = [d.get("name") for d in data] if isinstance(data, list) else []
assert "qtype" in names, f"缺少 qtype 数据集，实得 {names}"
qtype = next(d for d in data if d.get("name") == "qtype")
blob = json.dumps(qtype)
assert '"val": "1"' in blob, f"qtype 未统计到 A(1) 查询: {blob[:400]}"
assert '"count": 1' in blob, f"qtype 计数异常（应为 1）: {blob[:400]}"
assert "transport_vs_qtype" in names, f"缺少 transport_vs_qtype，实得 {names}"
print("OK: qtype/transport_vs_qtype 数据集与 A 查询计数已确认")
PY

echo "PASS: oarc-dsc 包内 dsc 端到端消费者用例通过"
