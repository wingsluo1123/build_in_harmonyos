# IRAF CI修复提交核验

2026-10-17；主PR #16407，C4176/B4177，任务7507已绑定，未代用户提审。
#16270（预算）和#16376（KC）按用户指令关闭，API回读确认，不作为本轮依赖。

## 当前实际结果

- main `ad0c1a73eaeeb0807aebf150606a75a9ee950bd0` 已合并；完整W3源码 `7646521e2988cc49ae145a47569724d56f76b572`，run `facfbb4c44c842209dd0479d00662fd9`。
- 原始main CI脚本/default3600秒，RC0/2081秒；无私有覆盖、IRAF预算条目或超时环境覆盖。
- 上游143调用：140 passed、2 skipped、1 xfailed、0 failed。保留所有原始测试和oracle。
- 安装、隐藏原包的副本、隐藏原构建缓存的新CONAN_HOME各16场景/33检查通过，恢复及摘要核对通过。
- 24项能力探测回归另计；权限、资源、信号及混合链接错误不可被当作能力缺失。
- 工具生成的local-ci-result.json原样保留；输入、包引用/制品摘要及唯一验证run_id在verification.json绑定。

本地原始证据备份：`iraf-repair-evidence.tar.gz`，373160字节，79文件，
SHA256 `a63128fd7ac62b35a5508b931fd5249a43bd042e5d6269fa264166a02852d655`。备份保存在提交者本机；完整编译日志及二进制保留在真机任务目录，未混入源码。

## 本轮修复

AI指出的OS宏已去除：实际链接探测选sigsetjmp/private备用入口；rcmd缺失才选择SSH实现；
浮点初始化按头文件能力。保留上下文尾跳转、ABI及C/SPP生产声明契约，不申请R8宏例外。
探针直接设置私有可写TMPDIR，SDK工具wrapper由配方自身提供，消费验证移除旧任务手工别名。
两轮中途发现问题后主动停止的重建及更早的超时/资源失败保留为历史，不计成功。
历史独立机制实验固定在06b848e36059fb160ce7c925d9ca94abe9d29b16，未改写为本轮重跑。

## 查重与边界

当前main2295正式条目，G0实际通过，KC RC0/KC_ERRORS=0、index2295=2295；graph validate RC0，
1085个既有分类警告完整输出保存在原始日志。四个精确特征词在正式graph/doc仍0命中，草稿分开列出。
longjmp已有E1279和E1904命中；本条只申报实际libc符号、前缀缓冲/尾跳转ABI及C/SPP双生产声明子族。
查重清单与门禁摘要见knowledge-recheck.json、latest-graph-validation.json。

本地源码/安装验证不等于线上CI/AI或C/B认定通过；远端结论以最终提交后的平台检查为准。

## 本地创建PR预检的现存路径误报

原始preflight仅报告PF9：把软件级README.md、commands.json、manifest.yaml当作缺版本目录。
这些是软件入口元数据，R38要求commands.json位于软件级；实际版本配方、测试和分支均正确。
R8没有命中，框架未修改；本PR已存在，本轮更新不新建PR。保留原始preflight-result.json，
不将自动预检描述成全通过，也不把该工具误报当作新源码或原始main W3失败。
