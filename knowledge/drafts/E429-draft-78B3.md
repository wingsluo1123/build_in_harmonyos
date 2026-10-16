# 扩展记录前缀必须由拥有真实载荷的层消费一次

状态：mrtparse 1.6 新适配 A+B 的规范知识草稿；主机与 H1-002 真实目标证据已取得。未提升正式 E 条目、未改索引，PR/审阅/有效提审仍待实际回执。

触发条件是同一格式的普通与扩展记录共用子解码器，但扩展记录在真实载荷前增加可选字段。mrtparse1.6 对Type16/17共享Bgp4Mp：合法Type16 KEEPALIVE能得到AS/IP/BGP字段，带123456微秒前缀的Type17却在Reader.val_num→chk_buf因Reader.buf=None产生TypeError。

根因有两层：Reader的数值读取没有指向实际payload；若只赋buf或给None加默认值，后续Bgp4Mp(data)仍会把微秒前缀当作peer AS等字段。正确边界是在拥有真实data的父层确认前缀完整、按大端解码4B micro_ts，并只向共享子层交data[4:]，保留完整原始record给诊断。普通记录不消费这4B。短前缀走原MrtFormatError/MRT Data Error机制，不吞异常或补零。

规范：[RFC6396 §3](https://www.rfc-editor.org/rfc/rfc6396.html#section-3)。微秒字段计入记录Length，位于payload开始；扩展记录的子类型和其余载荷仍沿用普通格式。此结论适用于具有相同前缀布局、相同子解码入口和明确缓冲所有权的解析器，不扩为所有None错误或所有协议格式。

实际修法见本项0001-mrtparse-__init__.py.patch。验证使用同语义普通/扩展载荷，对AS2/AS4、IPv4/IPv6、消息/状态同时核时间精度和下游字段，另核0–3B前缀、仅4B前缀无子头、连续扩展/普通/扩展记录的对齐及原始字节保留。5个unittest消费者方法在WSL Python3.12.3通过；12原样本与未改summary.py逐项保留原输出和Unsupported BGP4MP_ENTRY边界。H1-002 在 HarmonyOS aarch64/Python3.12.9 上实际加载 Conan 包，5方法通过、12原样本匹配（382记录中351解码、31原有不支持记录保留）；W3及真实移走lib的负向消费者验证复用。原报告及日志保全在作者本地证据，不进入PR。本次未重跑软件。

限定近邻比较直接复用领前卡的当前原件：E305为字体资源自解析，kaitai-runtime为musl iconv编码别名，minlzma为关闭CRC时的损坏判据，construct为sdist测试辅助缺失；未覆盖本项扩展前缀消费层/共享子载荷切片。领前搜索范围和页上限保留，不宣称全库原创。正式B发布前仍须按当时近邻变化复核增量；本次使用固定官方 graph add --draft 生成配对，实际原生解析和原 Type17 错误匹配保存在本地证据，不提升正式E编号/修改共享索引。

原始证据都由ENTRY定位：固定sdist/tag、未改原缺陷探针、完整v1.6 tree、当前补丁和主机原始结果。该草稿不是有效目标知识条目，不以编写文档替代目标、W4、完整AtomCode、申请关联、CI或提审。

## 规范配对与消费边界

草稿文件为 `E429-draft-78B3.kv` / `E429-draft-78B3.md`；其中 `E429` 仅为固定生成器草稿键，`draft: true`，未分配/提升正式知识号。`doc_file` 指向本草稿配对。匹配使用原未改源码探针保存的真实 Type17 traceback，字面特征 `self.mrt.micro_ts = self.val_num(4)` 与 mrtparse/val_num/chk_buf 上下文相符；未重新执行原缺陷或软件测试。隔离预览仅含本草稿，能证明本字段解析与消费，不证明全库原创或官方认可。

一级纯库 readiness 限定处置 cda35e25167245bec69ea4668f64c756d1f2cef2880db2f8c35481ce2f8797e1 接受本库已有 Conan、安装后消费者、真实负例与 W3 用于内部准入，不造 tar/暂存标记。原 finish rc1/W5 FAIL 保留；软件 README/PF9、正式 W4/full AtomCode、平台关联/CI/有效提审分别待核。
