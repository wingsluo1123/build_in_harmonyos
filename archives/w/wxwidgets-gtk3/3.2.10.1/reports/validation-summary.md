# wxwidgets-gtk3 3.2.10.1 真机验证

日期：2026-10-13。上游wxWidgets3.2.10，官方tar.bz2 SHA256 d66e929569947a4a5920699539089a9bda83a93e5f4917fb313a61f0c344b896。OHOS6 profile、HongMeng Kernel1.12.0、armv8、Clang15.0.4、libc++17、Release；SSH入口ohos-pc-active，设备ID3QC0124C20000792。

## 上游实测

| 原版目标 | 注册/定义组 | 通过 | 失败 | 整组跳过 | 未运行 |
|---|---:|---:|---:|---:|---:|
| test | 301 | 276 | 22 | 1 | 2 |
| test_gui | 354 | 348 | 6 | 0 | 0 |
| test_drawing | 1 | 0 | 1 | 0 | 0 |
| test_allheaders | 1 | 1 | 0 | 0 | 0 |
| failtest负向编译 | 11 | 11 | 0 | 0 | 0 |
| 合计 | 668 | 636 | 29 | 1 | 2 |

实际校验665项，636/665（95.64%）；全部声明范围636/668（95.21%），不是100%。运行Catch657组=625通过+29失败+FTP1跳过+人工2未跑；负向编译另计11/11，4源正控先编译成功，才核验具体误用诊断。绘图插件编译/加载不另造case。

默认test为271/292，test_gui为346/351。注册数分别301/354，显式隐藏用例按最终结果计数；两个目标共享8个注册名及5源文件，为上游刻意安排的console/GUI不同上下文。858是CPPUNIT方法/SECTION静态声明，不作为顶层case分母；316/304静态宏数也不混加。原输出另有13条条件跳过警告，可能发生于某组部分SECTION，详见upstream-statistics.json，不把它们当13个完整case。Catch通过不代表每个条件分支已覆盖。

## 消费者与门禁

3/3入口通过：test_wxgtk3（原API及16×16 JPEG往返）、test_wxgtk3_gui（真实显示、窗口、Cairo文字大小，Pango errors=0）、test_wx_app_state（真实exe和动态模块读取同一wxApp）。16为检查点数，不冒充独立case。

最终Verifier包的原版samples/minimal/minimal.cpp还进行了交互验证：实际显示Minimal wxWidgets App窗口，Help→About出现上游wxWidgets3.2.10与HongMeng Kernel1.12.0 aarch64信息，关闭对话框并正常关闭主窗口，退出0、stderr为空（minimal.exit/minimal-run.log）。这是补充GUI证据，不累计为更多上游注册组或消费者case。

原FinishPipeline.step35_local_ci返回0，L0/L1/L2/L4/L5逐项pass，破坏性依赖反向验证确实失败。wx-config --version、wxrc/wxrc-3.2 --help通过；wxrc无--version，commands.json使用--help。W3日志SHA256 bc187f9fa68ec1344d4709f0c0570da26af9384905a4fc6c2f88fa894526128b；.ci-result.json为原工具字节。L1自动字符串判定upstream executed不代表build内跑完整上游：recipe wxBUILD_TESTS=OFF，上游由本报告独立入口真实执行。

原ConanVerifier CLI PASS，G0/G1/G2/G3通过；G4旧缓存解析未找到PID，L2/L4/L5原报告skip。补充入口由真实conan cache path解析精确引用，配置原Verifier缓存上下文，实际调用L2/L4/L5均通过；13共享ELF均有相对SONAME，无绝对或../ NEEDED，RUNPATH为$ORIGIN及$ORIGIN/../lib。见artifact-followup.json；框架源码未改。

原legacy staging verified=1 failed=2：其只试--version，而wxrc两个入口没有该参数，实际--help通过。未把有效工具排除出Conan包。真实conan cache save归档仅留忽略的packaging/，不提交二进制。

W3 RREV f7b54e62924cd8b3446d9e5ccedecca3，PID fed32c441924cf90473bb8ea5190d75542020fc6，PREV223fbec1baaa930af6a6c114400ed1e0。Verifier @ohpcd/stable RREV64637f005b0658d0680008907e0655ce、同PID、PREVe143cd9bc264a0c8c5dd53da56af6d8d。不同RREV来自原工具临时URL回退元数据，源码SHA/功能相同；均为本地缓存，非已发布制品。

## 原版入口与资源

test.bkl的test87源、test_gui104源逐个匹配官方入口，源码和断言未改。drawing5源、allheaders4源和pluginsample源另验证，保留官方console/drawing wxUSE_GUI=0。主目标复验重用相同配置原源对象，重链接最终W3包；新增小目标、插件及负向源重新编译。

Broadway提供真实显示连接，任务Fontconfig使用/system/fonts。GTK包原始4份gschema XML缺编译数据，用已发布GLib工具的任务签名副本严格编译，并设置任务GSETTINGS_SCHEMA_DIR；发布GTK包没有修改，部署其文件选择器仍须提供schema资源。XRC::LoadURL从原版xrctest.cpp提取XML常量，经仅127.0.0.1临时HTTP和可写TMPDIR验证。BST用进程GMT0BST规则，FromTag用en-US，Trace用WXTRACE=logtest，原版要求下通过。

## 保留失败

- console22：默认21涉及根目录/硬编码/tmp权限、路径/inotify行为、locale/格式和XML编码；具体表达式见upstream-console.log，不能笼统称全部环境问题。隐藏RedirectUTF8要求硬编码/bin/ls为GNU ls且fr_FR.UTF-8，设备Toybox输出不符。
- GUI6：BitmapBundle::ArtProvider预期24×24却16×16并提示hicolor未找到；ClippingBoxTestCase窗口DC尺寸不符；EventClone的wxHelpEvent查询不支持的key340；ImageTestCase无条件horse.tif而本变体TIFF关闭；wxTopLevel::Show的Dialog/Frame激活断言失败（同组）；GUI RedirectUTF8的GNU ls前提也不符。
- drawing1：原PNG参考比对不一致，sample插件官方参考BMP不在归档，不能生成自身期望图冒充验证。插件真实构建/加载，组仍失败。
- FTP原版未设置HOST/DIR/FILE，WARN返回，单列跳过。InteractiveInput/Output需要人工输入或输出检查，未用EOF/timeout冒充成功。
- TIFF、OpenGL/GLCanvas、media/sound/webview等可选功能关闭；本轮仅shared验证，未伪报新版本static通过；Broadway不代表原生桌面/所有窗口管理能力。

## 修复与交付边界

0002 geometry→screen仅限单monitor且无效；无效workarea对任意monitor回退其geometry；0003未设置DPI使用比例1，组合回归零Pango critical。0004修builtin90头却先链接系统JPEG62，jpeg-red/green.log及最终JPEG消费者为实测；不声称任意宿主加载顺序均无ELF抢占。安装后14 ELF在最终路径签名；wx-config前缀、wxrc相对链接和RUNPATH可迁移。

PR、当前HEAD远端CI、审核、合并、正式发布分别记录。知识草稿仅路径B候选，官方决定入库及10分。CodeBlocks25.03须等共享版本正式发布后重新W0并验证IDE/插件，不能用本报告替代主库完成证据。

## 本地证据位置

按 .gitcode/code-style.md §24、review-memory.md §19 和 CI JC1，原始 *.log、test-report 及运行状态仅保留本地。完整可回读副本：D:/codex/harmonypc/_work/codeblocks-w0-20261009/wx-submission-local-evidence/；本摘要中的 .log 文件名指该目录 reports/ 下的原始字节，evidence-sha256.json 提供其哈希。结构化统计和诊断结果随 PR 提交；本地路径不能作为远端已公开下载链接。

## 工具目录元数据最终复验


package_info新增真实cpp_info.bindirs=["bin"]后，原W3重新完整conan create而非复用旧回执；L0/L1/L2/L4/L5逐项pass，3消费者实际执行。
最终本地完整包引用：wxwidgets-gtk3/3.2.10.1#4d874fd4a3845560a5161365bb821d5c:fed32c441924cf90473bb8ea5190d75542020fc6#842d8d7b25c86b937be2e6cb43602db1；回执时间：2026-10-13T01:20:54.863125，W3日志SHA256：bc187f9fa68ec1344d4709f0c0570da26af9384905a4fc6c2f88fa894526128b。
上述早期W3/Verifier引用作为历史实测保留，不能当作当前RREV。此次仅工具目录元数据改变，C++实现、补丁内容、功能配置与上游测试源未变；完整668上游及minimal GUI证据来自前一相同实现构建，未冒称对新RREV重复执行全部上游。

## 分类元数据范围

0003的patch_type按code-style §12由bugfix统一portability；静态核验仅一行分类改变，源码URL/SHA、所有补丁字节及应用参数完全相同。Conan实际实现中该字段仅打印分类，不参与patchset.apply。上述最终完整W3用bugfix分类运行，原回执/日志/RREV保持不变；不声明对分类变更的新revision执行过conan create。最终HEAD远端CI仍待验证，等同性细节见classification-equivalence.json。
