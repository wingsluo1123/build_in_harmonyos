# 未执行（A−E）逐项原因

A−E 合计 = 90（UNEXECUTED_MANIFEST 90；DEFERRED_LONG_RUNNING **0** —— 3 项长耗时调用已于 2026-10-08 全部执行并 PASS）

## UNEXECUTED_MANIFEST（90）

判据：该 config **没有任何执行记录**，且其套件在生成阶段的脚本数为 0（未能产出可运行脚本）。
这些不属于「失败」，也未被计入 E/P/F。

- 生成阶段未产出脚本（scripts=0） —— 90 项
    - `pgo_profile/titan`
    - `pgo_profile/vtr`
    - `pgo_profile/vtr_odin`
    - `vtr_reg_nightly_test2/titan_other`
    - `vtr_reg_nightly_test2/titan_quick_qor`
    - `vtr_reg_nightly_test2/vpr_verify_rr_graph`
    - `vtr_reg_nightly_test2/vpr_verify_rr_graph_bidir`
    - `vtr_reg_nightly_test2/vpr_verify_rr_graph_complex_switch`
    - `vtr_reg_nightly_test2/vpr_verify_rr_graph_error_check`
    - `vtr_reg_nightly_test2/vpr_verify_rr_graph_titan`
    - `vtr_reg_nightly_test2/vtr_bidir`
    - `vtr_reg_nightly_test2/vtr_func_formal`
    - `vtr_reg_nightly_test2/vtr_reg_multiclock_mcnc`
    - `vtr_reg_nightly_test2/vtr_reg_netlist_writer`
    - `vtr_reg_nightly_test2/vtr_timing_update_diff`
    - `vtr_reg_nightly_test2/vtr_timing_update_diff_titan`
    - `vtr_reg_nightly_test2_odin/titan_other`
    - `vtr_reg_nightly_test2_odin/titan_quick_qor`
    - `vtr_reg_nightly_test2_odin/vpr_verify_rr_graph`
    - `vtr_reg_nightly_test2_odin/vpr_verify_rr_graph_bidir`
    - `vtr_reg_nightly_test2_odin/vpr_verify_rr_graph_complex_switch`
    - `vtr_reg_nightly_test2_odin/vpr_verify_rr_graph_error_check`
    - `vtr_reg_nightly_test2_odin/vpr_verify_rr_graph_titan`
    - `vtr_reg_nightly_test2_odin/vtr_bidir`
    - `vtr_reg_nightly_test2_odin/vtr_func_formal`
    - `vtr_reg_nightly_test2_odin/vtr_reg_multiclock_mcnc`
    - `vtr_reg_nightly_test2_odin/vtr_reg_netlist_writer`
    - `vtr_reg_nightly_test2_odin/vtr_timing_update_diff`
    - `vtr_reg_nightly_test2_odin/vtr_timing_update_diff_titan`
    - `vtr_reg_nightly_test4/koios_medium`
    - `vtr_reg_nightly_test4/koios_medium_multi_arch`
    - `vtr_reg_nightly_test4/koios_medium_no_hb`
    - `vtr_reg_nightly_test4/titan_s10_qor`
    - `vtr_reg_nightly_test5/vpr_ispd`
    - `vtr_reg_nightly_test5/vpr_noc_clique_topology`
    - `vtr_reg_nightly_test5/vpr_noc_nearest_neighbor_topology`
    - `vtr_reg_nightly_test5/vpr_noc_star_topology`
    - `vtr_reg_nightly_test5/vpr_tight_floorplan`
    - `vtr_reg_nightly_test5/vpr_tight_floorplan_3d`
    - `vtr_reg_nightly_test7/3d_cb_titan_other_auto_bb`
    - `vtr_reg_nightly_test7/3d_cb_titan_other_cube_bb`
    - `vtr_reg_nightly_test7/3d_sb_titan_other_auto_bb`
    - `vtr_reg_nightly_test7/3d_sb_titan_other_per_layer_bb`
    - `vtr_reg_nightly_test7/titan_other_run_flat`
    - `vtr_reg_nightly_test7/verify_rr_graph_run_flat`
    - `vtr_reg_strong/koios_test`
    - `vtr_reg_strong/strong_clock_aliases`
    - `vtr_reg_strong/strong_clock_aliases_set_delay`
    - `vtr_reg_strong/strong_clock_buf`
    - `vtr_reg_strong/strong_clock_modeling`
    - `vtr_reg_strong/strong_dedicated_clock`
    - `vtr_reg_strong/strong_flat_router`
    - `vtr_reg_strong/strong_global_routing`
    - `vtr_reg_strong/strong_multiclock`
    - `vtr_reg_strong/strong_noc`
    - `vtr_reg_strong/strong_place_effort_scaling`
    - `vtr_reg_strong/strong_routing_constraints`
    - `vtr_reg_strong/strong_sdc`
    - `vtr_reg_strong/strong_target_pin_util`
    - `vtr_reg_strong/strong_tight_floorplan`
    - `vtr_reg_strong/strong_timing`
    - `vtr_reg_strong/strong_timing_fail`
    - `vtr_reg_strong/strong_timing_no_fail`
    - `vtr_reg_strong/strong_timing_update_type`
    - `vtr_reg_strong/strong_unroute_analysis`
    - `vtr_reg_strong_odin/strong_clock_aliases`
    - `vtr_reg_strong_odin/strong_clock_aliases_set_delay`
    - `vtr_reg_strong_odin/strong_clock_buf`
    - `vtr_reg_strong_odin/strong_clock_modeling`
    - `vtr_reg_strong_odin/strong_dedicated_clock`
    - `vtr_reg_strong_odin/strong_global_routing`
    - `vtr_reg_strong_odin/strong_multiclock`
    - `vtr_reg_strong_odin/strong_place_effort_scaling`
    - `vtr_reg_strong_odin/strong_sdc`
    - `vtr_reg_strong_odin/strong_target_pin_util`
    - `vtr_reg_strong_odin/strong_tight_floorplan`
    - `vtr_reg_strong_odin/strong_timing_fail`
    - `vtr_reg_strong_odin/strong_timing_no_fail`
    - `vtr_reg_strong_odin/strong_unroute_analysis`
    - `vtr_reg_valgrind/valgrind`
    - `vtr_reg_valgrind/valgrind_odin`
    - `vtr_reg_weekly/koios_large`
    - `vtr_reg_weekly/koios_large_no_hb`
    - `vtr_reg_weekly/koios_large_no_hb_odin`
    - `vtr_reg_weekly/koios_large_odin`
    - `vtr_reg_weekly/koios_proxy`
    - `vtr_reg_weekly/koios_proxy_no_hb`
    - `vtr_reg_weekly/koios_sv`
    - `vtr_reg_weekly/koios_sv_no_hb`
    - `vtr_reg_weekly/vtr_reg_titan_he`

## 本轮已完成的长耗时调用（原 DEFERRED_LONG_RUNNING，现全部 PASS）

| config · circuit | 用时 | 硬上限 |
|---|---|---|
| koios_medium_no_hb/k6FracN10LB_mem20K_complexDSP_customSB_22nm.xml/dla_like.small.v/common |  s | 10800 s |
| koios_other/k6FracN10LB_mem20K_complexDSP_customSB_22nm.xml/dnnweaver.v/common |  s | 10800 s |
| koios_other/k6FracN10LB_mem20K_complexDSP_customSB_22nm.xml/tdarknet_like.small.v/common |  s | 23631 s |
| koios_other_no_hb/k6FracN10LB_mem20K_complexDSP_customSB_22nm.xml/dnnweaver.v/common |  s | 10800 s |
| koios_other_no_hb/k6FracN10LB_mem20K_complexDSP_customSB_22nm.xml/tdarknet_like.small.v/common |  s | 25598 s |

