# DRAFT-rarcrack-0.2-20240214-413ea3a-switch-suffix-version-cut-cci-cmake-edge
> 双远端共存下裸依赖命中CCI cmake边时切换仓内独有后缀版本切断失败边
## 问题特征（真实日志片段/标记）
- 真机`conan create`尚未进入rarcrack本体编译，在依赖构建阶段失败：`cmake/4.4.4 build() line35 KeyError: 'OHOS'`。
- 失败时依赖图拉取了`libxml2/libiconv/zlib/cmake`，与本仓`libxml2`零依赖特征矛盾，证明命中了conancenter的CCI配方边。
- 本地复现指纹：`requires`为裸`libxml2/2.15.3`，双远端共存下真机预检conancenter优先命中。
## 根因
- `conanfile.py`中`requires`裸`libxml2/2.15.3`在`conancenter`与`ohpcd`双远端共存，真机预检优先命中CCI配方。
- CCI `libxml2`经`tool_requires("cmake")`拉起需从源码构建的cmake，其`conandata`无OHOS条目，在`build()`解析系统时抛`KeyError: 'OHOS'`。
- 同指纹实证：`zurl/1.12.0 notes #26-#27`为裸版本撞CCI cmake边的同类记录；`libxml2/2.15.3.1 manifest`载明R37仓内独有、同上游v2.15.3、零`tool_requires`，可作断边目标。
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. `archives/r/rarcrack/0.2-20240214-413ea3a/conanfile.py`：将`requirements`改为`self.requires("libxml2/2.15.3.1")`，并在注释中写明CCI边依据（裸2.15.3撞conancenter优先命中，经tool_requires cmake无OHOS条目失败）。
2. 同步两级manifest：`archives/r/rarcrack/manifest.yaml`与版本`manifest.yaml`中的依赖声明更新为`libxml2/2.15.3.1`。
3. 同步`notes.md`与PR草稿依赖声明，说明切换到仓内独有后缀版本切断失败边。
4. 验证：真机`conan create`依赖图仅命中仓内`libxml2/2.15.3.1`，不再出现`libiconv/zlib`连带与`cmake KeyError OHOS`，真机门禁全部通过。
## 禁止策略
- 禁止保留`libxml2/2.15.3`裸依赖（正则`libxml2/2\.15\.3["'\)]`）：双远端下仍会优先命中CCI配方并经`tool_requires`拉起无OHOS条目cmake，导致`cmake build()`再次报`KeyError OHOS`并退回修复循环。
- Windows检出下`libXext/libxext`大小写目录碰撞改动与本PR无关，不得一并提交。
## 与相近条目的边界（查重）
- 查重零实质覆盖：现有条目仅关键词相邻，均不涉及conancenter优先命中与后缀独有版本切换。
- 本条目可抽象为双远端裸依赖撞CCI cmake边的通用断边法，有`applicableWhen`与`zurl`同指纹实证，非单库临时补丁。
- 相近：`[DRAFT-zurl-1.12.0-bare-requires-cci-cmake-collision]`仅作同指纹旁证，不覆盖本条目的后缀版本断边路径。
## 适用判断
- 适用当且仅当：`requires`的裸版本在`conancenter`与`ohpcd`双远端共存且CCI配方带`cmake tool_requires`；仓内存在同上游源码的适配后缀独有版本（如`libxml2/2.15.3.1`同上游`v2.15.3`零`tool_requires`）。
- 谨慎：若`2.15.3.1`尚未发布到制品仓仍缺二进制，以后端`conan download`实证为准，不假设本地manifest即有二进制。
