# 上游测试语料按 gitlink 版本化、却只有一份不可按修订取用的快照：挂进来就是 11% 假失败

对应知识草稿：`knowledge/drafts/gdcm-3.0.24-test-corpus-revision-skew.kv`
来源：gdcm 3.0.24 适配（分支 `feat/gdcm-3.0.24`），完整实测记录另见
`archives/g/gdcm/3.0.24/notes.md`。

## 命中场景

包的测试数据与代码**分两处版本化**：代码 tarball 里数据目录是空的 gitlink，
数据本体在另一个仓库/另一份快照里，而测试断言又把"数据修订"当常量用
（语料文件的静态哈希表、或"这个语料必须读得动"）。典型：GDCM/gdcmData、
ITK/ITKData、VTK/Data、OpenCV/opencv_extra。

## 症状（gdcm 3.0.24 实测，OHOS aarch64 / clang 15）

不挂语料（上游发布形态）：

```
ctest --test-dir <build> -N   →  Test file 1..199  → 199 项注册
```

把 SourceForge 唯一那份 `gdcmData.tar.gz`（sha256
`54ff2db5511f01eecc5d012f46083382ce49348b9e1ce62db87b06e5d860890f`，解开后 195 MB）
解进 `Testing/Data` 后重新 configure：

```
ctest -N                      → 232 项注册（if(GDCM_DATA_ROOT) 追加 33 项数据驱动用例）
ctest --output-on-failure     → 89% tests passed, 25 tests failed out of 232
                                Total Test time (real) = 1223.78 sec
```

失败分两类，都不是移植缺陷：

1. **静态哈希参考表对不上语料文件本身**（`TestMD5`）：

   ```
   D_CLUNIE_RG3_JPLY.dcm  期望 6867e0e4f8a1feb871a1ee8dcfac838e
                            快照 d06de3e3b941dce6c2c2c896fe42584b
   ```

   参考值写死在 `Testing/Source/Data/gdcmMD5DataImages.cxx`、
   `Testing/Source/Common/Cxx/TestMD5.cxx`，比对的是**输入文件的字节**，
   跟 CPU/OS/编译器无关——哈希差只能说明"语料修订 ≠ 代码修订"。

2. **快照里有本版本读不动的语料**（`TestCleaner4`）：

   ```
   Could not read: JPEGInvalidSecondFrag.dcm
   ```

   快照比 v3.0.24 新，含该版本还不支持的文件。

## 根因

v3.0.24 的 `Testing/Data` gitlink 固定在 `a0bba51684aa0cc929186ebc8870a27ce1930996`
（`git://git.code.sf.net/p/gdcm/gdcmdata`），但 SourceForge 只发布单一
`gdcmData.tar.gz` 快照，**不能按修订取用**。而 conan 配方的 `source()` 只能按
`URL + sha256` 取物——等于配方层面就没有正确取用语料的通道。

于是只有三种可选：

| 方案 | 结果 |
|------|------|
| 挂快照 | 注册数涨到 232，但 25 项假失败（11%），且单轮 ctest 1223.78s |
| `-DGDCM_DATA_ROOT` 指到空目录 | `if(GDCM_DATA_ROOT)` 成立、数据驱动用例注册，但文件表为空 → 用例空转，注册数虚高（**最坏：制造假覆盖**） |
| 按上游发布形态（不挂） | 199 项照常注册/编译/执行（gdcm/3.2.11 同族形态注册 200 项，版本间注册数本就不同） |

## 建议做法

选第三种：**按上游发布形态构建**，并且

- PR/manifest 的分母用 `ctest -N` 的**注册数**，把该清单打进构建日志，让声明可核对；
- 不要手动设 `GDCM_DATA_ROOT`，让上游 `find_path()` 自然判空；
- 语料实验的完整数据（199→232、+33 项、两条哈希证据、耗时）写进 `notes.md` + 本知识条目，
  而不是静默省略——review 关注的是"少报"，透明申报豁免原因可过，虚报/瞒报不能过。

若将来语料能按修订取用（例如存在 GitHub 镜像、可用 `/archive/<sha>.tar.gz` 固定
并填 sha256），可以换挂语料取全量 232 项；但要先核算时间预算：`conan create` 整体
受 `ci/config/build_timeouts.txt` 的超时约束（默认 3600s），语料 ctest 单轮就
1223.78s，叠加构建很可能越线，而该配置文件不在适配 PR 允许提交的目录里
（适配 PR 只提交 `archives/` 与 `knowledge/`）。

## 反向验证（怎么确认这是数据错配而不是移植缺陷）

同一份失败清单在 x86 Linux 上用相同源码 + 相同快照必然复现；且失败信息是
"文件哈希/文件读不动"而非 crash、符号缺失或字节序差异。

**未定论项（如实记录，不要笼统归给语料）**：失败清单里的 JPEG2000 系
`D_CLUNIE_CT1_J2KI`/`ELSCINT1_JP2vsJ2K`/`MAROTECH_CT_JP2Lossy` 三条属于
"解码后像素缓冲与代码内参考哈希不符"，这类差异**理论上**也可能来自 OHOS 侧
openjpeg 路径。我用 `gdcmraw` 下过探针核对解码缓冲长度，但探针本身不成立
（`-t` 语义用错），观察到的缓冲长度 7536/248330/204016 与代码参考所需的
524288（512×512×2 字节）不一致，无法据此判定根因。结论只能是
**"未确证：语料修订错配 vs 解码路径缺陷，二者未区分开"**；因这三条只在挂语料时
才注册，不挂语料的交付形态不受影响。若要坐实，应改为直接用
`gdcm::ImageReader` 解这三个文件并打印 `GetBufferLength()` 与逐像素比对，
而不是用 `gdcmraw -t` 猜封装。
