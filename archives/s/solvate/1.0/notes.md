# solvate 1.0 适配与 checkpoint EOF 验证

任务10798，账号orrkri，分支feat/solvate-1.0。状态built指真实Conan构建/包验证已完成，未upload；不表示官方CI、PR、提审、合入、知识接受或积分。

## 固定来源和许可

原始上游来自Debian官方solvate_1.0.orig.tar.gz，SHA256 562201246040b6fc66c1240e437737349ef01d062aa3eb72b6b86f5e1510768f。包装版本1.0，原程序banner1.0.1（1996–2010），保留差异，不伪造Git tag/commit。原no_fee许可完整保留于docu_html/node8.html，包内原文为licenses/solvate-license.html；Debian将其归入non-free，没有改标MIT/BSD或宣称OSI许可。修改的C源显著注明orrkri与2026-10-16。

无第三方运行依赖，libm为系统数学库。Conan归档内CMake适配器构建原单C源，-O2/-lm；包内四个PDB/PSF输入及完整许可与原归档逐字节一致。

## 最小修改与补丁

官方refresh-patch真实生成0001-solvate.c.patch，9,164B/SHA256 c73fce8acd3b419e62bfc720ac2f9f423b1f01cc2fa38e382b8f75dbcb6bbda7，目标检查和应用均成功；原C SHA256 f8f268bcaf2eb9d46a27dd1922dc782bd61d93e458592de8a0e8fbff33031145，补后d9c1ad8e3f27be126ac9bc5c620279d102826bf825a383349c151128aedfcf4b。

只在skip_line的首次读取及找LF循环检测EOF/读错，沿原terminate非0退出；保留fscanf后先跨遗留LF再跳下一header的合同。两个checkpoint reader的42 float/2 int转换必须成功1字段，避免缺值沿用旧fdummy。没有改物理算法、完整数值语法或数据结构，不声称全格式损坏恢复。

配方layout明确src/solvate_1.0，get(destination="..",strip_root=False)保留原归档根；补丁默认源根和CMake变量相同。消费者每次在build_folder内分配独立临时父目录，使用其尚不存在的results子目录；保留旧结果及验证脚本的目录不存在条件，全部断言未改。

## 实际目标结果

OHOS6/armv8/clang15/Release。原版真实-ug/-ub空文件和截断header共4场景均2秒超时，作为缺陷FAIL保全，不加入修后成功率。正式G2已成功构建真实包并通过完整消费者；后续只复验受影响W3，没有再跑原4或宿主软件测试。

最新W3由未修改FinishPipeline.step35_local_ci单次调用，自然RC0，setup/build_and_test均0。G0/L0/L1/L4/L5 PASS；L2实际为skip: version/help failed。自动.ci-result.json与完整日志原件保留，log_sha256=411f86f19b29bf22e643441fed3e5faffadb306bd84900fdab2d5e2a42f0377b，未手写/改该记录。W3本次准备230.793秒、软件84.728秒、总315.520秒，未超本次预算，PID/group自然释放。

| 目标唯一场景 | 通过 | 失败 | 跳过 |
|---|---:|---:|---:|
| 原发行方业务命令 | 2 | 0 | 0 |
| 新增checkpoint回归 | 10 | 0 | 0 |
| 合计 | 12 | 0 | 0 |

一份消费者程序执行12场景/12次CLI/60断言。原发行命令不变：solvate -r 20.91 -s -v bpti test1；solvate -n 2 -r 40.33 -t 2 -bulk -psf -ion globh test2。上游原包没有test/check目标；这两条来自原Debian autopkgtest，迁移私有cwd，不能冒称上游原生unit或原Debian拷贝/gunzip外壳已在OHOS执行。新增10是两个正常生成checkpoint去末LF后恢复，以及两入口各空/首header截断/后续header截断/缺末数值四负例，保留所有原断言。

L2说明：原CLI不支持--version/--help；bad_input()打印用法后exit1，未知以“-”开头的参数也走该出口。官方W3将该通用冒烟标为非阻断skip，保持skip；实际包的两原业务流程和两个正常resume等12场景提供功能验证，不把L2改写PASS，也不为它新增CLI功能。

W3实际fullref：solvate/1.0#5daf260e29c6fef438da37cb7729cd86:6b129b068851896169fae42d399fa922d239ce8a#7db9527ca8ef78a8c00a689aa075cca9。旧G2是solvate/1.0@ohpcd/stable#0c495b77fc3e3ce68443cd9d1b0ff216:6b129b068851896169fae42d399fa922d239ce8a#7db9527ca8ef78a8c00a689aa075cca9，不混称同一RREV。当前原包ELF64 little-endian、machine183，binary SHA256 804636f4952bfa6b7bf3df55e28fa7640a6be8f52d5237bfbea65114ddb1703e；包内数据和完整许可已核原字节。

## 保留的失败与边界

原配方源根层级错误导致G2补丁找不到C源，已作两行修正；原固定输出目录导致W3第二消费者FileExistsError，已作独立输出隔离。旧完整finish自然RC1及旧W3失败仍保留；当前W3成功不是把旧finish改成成功。旧clean-verify的configure RC127、早期subset无.git/curl ENOENT、diff序列化guard及超时历史单列，不包装为C源码新缺陷。早期collector引用未命中返回0份不表示未构建，真实包和消费者已证明并于004回收ELF/数据/许可。

原默认R46生命周期输出副作用不盲目恢复，后续已用支持的私有OHC_RESULT_OUT，本次默认文件未变。Windows历史构建环境失败、原4缺陷FAIL及准备超时均保留在原作者ENTRY/原件。未通过编造旧packaging/staging标记或修改框架规避门禁。

## 知识与本次对话结束记录

E429-draft-1306记录“必需checkpoint结构EOF失败传播与fscanf/header消费合同”；最近kevlar char吞EOF、skewer负返回值丢尾批和arena-allocator编译尾换行不同，不称OHOS专属或全球原创。KV/MD仍为草稿，未正式接受/计分。

二级回交004真实W3终态后，原作者只消费原件、说明L2边界、更新事实文字与绑定提交；没有重跑host/G2/W3/原4/R3。软件输入保持004受测字节；独立W4/真实AtomCode与发布关系按实际回执完成，当前不冒称已审阅、已发布或有效提审。
