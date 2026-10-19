# 已知大小写碰撞的无损增量：隔离导出根与上游树

四范围查重命中 DRAFT-liboggz-1.1.1-hmdfs-patches-collision，其根因与本次相同，
不是新的碰撞发现。既有处方为 excludes 排除非必要文件，或重命名补丁目录。
本条实质增量是用标准 source_folder 布局保留所有上游成员和已冻结补丁表示，
并以实际 Conan source 证明 Windows errno13 与 Harmony errno21 的同一别名边界。
E470 改 build_folder 处理 Bazel BUILD 碰撞，阶段与命名空间也不同。

## 现象和根因

下载及 SHA256 校验成功后，source() 解包报 `IsADirectoryError: './PATCHES'`。
这不是缺依赖、编译失败或 ELF 未签名。Conan 把导出的 `patches/` 放在源码缓存根；
默认布局的下载树也在这个根。大小写不敏感文件系统把上游 `PATCHES` 文件解析为
同一个目录。仅在大小写敏感的任务私有目录跑过 conan create，不能证明该 worker
上的根命名空间没有冲突。

## 可复用解决步骤

1. 回读首个原始错误、准确解包目标和原归档成员类型，区别文件/目录冲突与权限错误。
2. 检查 recipe exports_sources 的根名字与上游根名字，按 casefold 比较，包括父路径。
3. 用 Conan 标准 `cmake_layout(self, src_folder="upstream")` 隔离上游树。
   `get()` 的官方地址、哈希和 strip_root 保持不变。CMake、许可证复制和补丁应用
   沿用 self.source_folder；补丁文件仍从 export_sources_folder 定位。
4. 保留上游文件及补丁集，先在大小写不敏感文件系统验证真实 source()，再执行干净
   Conan 构建、完整上游测试和安装包消费者，最后触发当前 HEAD 的平台构建。

Conan 官方第三方布局示例说明导出根与 source/src 的区分：
https://docs.conan.io/2/examples/conanfile/layout/third_party_libraries.html

## 本次证据

PR15756 原提交 `48e4ded0c756b37f29de5ecdc101335e61f8a176` 的 CI91435
（buildid105045、CI-010）在 source() 首先失败；官方源包含普通文件 PATCHES。
修复只改变布局，不删除文件或重组原有15个补丁。实际 Windows Conan source
旧布局失败/新布局成功2/2；新布局保留 PATCHES 文件和完整15个补丁目录。
真机 r3 shared/static 各37/37上游与消费者1/1；finish r6 RC0。正式日志SHA256
为9f10bf6b8e8444620bbf7b18cd08ea4ba24b206c0e38b8571dc76d32374e625c；
比赛当前 HEAD CI 仍需重新执行，不能拿真机 PASS 冒充平台通过。

## 安全边界

适用于外部源码与配方辅助文件的命名空间碰撞，也能指导 Autotools 等布局；
不是仅对 libdispatch 的文件重命名方案。若上游归档内部本身必须同时保留两个
大小写同名成员，子目录布局仍不能解决，必须使用能表示两者的大小写敏感文件系统。
禁止删除碰撞文件、吞掉异常、修改上游校验和或用残留树冒充干净解包。
