# ═══ Draft knowledge entry — launchy 2.9.1 OHOS Qt5 适配（QLockFile / QT5_INCLUDE_DIRS / X11 宏污染） ═══
# 来源：launchy 2.9.1 适配 run（patches 0001-0013；conan create PASS + ctest 100% + 消费者 DT_NEEDED 解析）
# Status: DRAFT — 随 launchy feat/launchy-2.9.1 分支交付，待主编/AI 审核提升为 E 条目

# 四范围多轴查重（2026-10-02，见 knowledge-ledger.md 完整版）：
#   检索范围: knowledge/graph/index.tsv（766 条）+ knowledge/drafts/ + knowledge/doc/
#   检索词: QSharedMemory、QLockFile、sharedmemory、CMakeDeps、QT5_INCLUDE_DIRS、
#           X11、AUTOMOC、mocs_compilation、macro pollution、qt5、override
#   近邻条目逐项差异（七轴详见 ledger）:
#     E216  CMakeDeps 组件 INTERFACE_INCLUDE_DIRECTORIES 不传播（glib/libxml2）→
#           本条同类现象但触发不同（override 聚合配置降级），方案不同
#           （依赖修正+toolchain 注入 vs 消费侧 GLOB 兜底）
#     E429  Qt6 POSIX shm/sem 命名空间冲突（runtime 层）→ 本条 Qt5 编译层特性禁用
#     E456  Qt5 host tools 分离（host/target 工具）→ 本条不涉及工具分离
#     其他  X11 宏污染 AUTOMOC 合并 TU 无既有条目（未命中）

# 七轴：
#   exact_duplicate: false
#   causal_duplicate: false
#   trigger_overlap: true（E216 同 CMakeDeps 组件行为；同 Qt5 体系）
#   solution_overlap: false
#   combination_novelty: true（Qt5 特性裁剪 × CMakeDeps 聚合降级 × X11 宏污染 组合无既有条目）
#   boundary_novelty: true
#   test_migration_novelty: false