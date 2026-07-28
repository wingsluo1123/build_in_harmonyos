/* Generated automatically by the program `genattrtab'
   from the machine description file `md'.  */

#define IN_TARGET_CODE 1
#include "config.h"
#include "system.h"
#include "coretypes.h"
#include "backend.h"
#include "predict.h"
#include "tree.h"
#include "rtl.h"
#include "alias.h"
#include "options.h"
#include "varasm.h"
#include "stor-layout.h"
#include "calls.h"
#include "insn-attr.h"
#include "memmodel.h"
#include "tm_p.h"
#include "insn-config.h"
#include "recog.h"
#include "regs.h"
#include "real.h"
#include "output.h"
#include "toplev.h"
#include "flags.h"
#include "emit-rtl.h"

#define operands recog_data.operand

int
insn_default_latency (rtx_insn *insn ATTRIBUTE_UNUSED)
{
  enum attr_type cached_type ATTRIBUTE_UNUSED;
  enum attr_mul32 cached_mul32 ATTRIBUTE_UNUSED;
  enum attr_widen_mul64 cached_widen_mul64 ATTRIBUTE_UNUSED;
  enum attr_cortex_a53_advsimd_type cached_cortex_a53_advsimd_type ATTRIBUTE_UNUSED;
  enum attr_cortex_a57_neon_type cached_cortex_a57_neon_type ATTRIBUTE_UNUSED;
  enum attr_predicated cached_predicated ATTRIBUTE_UNUSED;
  enum attr_exynos_m1_neon_type cached_exynos_m1_neon_type ATTRIBUTE_UNUSED;
  enum attr_tsv110_neon_type cached_tsv110_neon_type ATTRIBUTE_UNUSED;

  switch (recog_memoized (insn))
    {
    case 3638:  /* aarch64_st1_x4_v2df */
    case 3637:  /* aarch64_st1_x4_v4sf */
    case 3635:  /* aarch64_st1_x4_v8hf */
    case 3633:  /* aarch64_st1_x4_v2di */
    case 3632:  /* aarch64_st1_x4_v8bf */
    case 3630:  /* aarch64_st1_x4_v4si */
    case 3628:  /* aarch64_st1_x4_v8hi */
    case 3626:  /* aarch64_st1_x4_v16qi */
      if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) || (((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))))
        {
	  return 0;
        }
      else if (((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1))))
        {
	  return 4;
        }
      else
        {
	  return 0;
        }

    case 3622:  /* aarch64_st1_x3_v2df */
    case 3621:  /* aarch64_st1_x3_v4sf */
    case 3619:  /* aarch64_st1_x3_v8hf */
    case 3617:  /* aarch64_st1_x3_v2di */
    case 3616:  /* aarch64_st1_x3_v8bf */
    case 3614:  /* aarch64_st1_x3_v4si */
    case 3612:  /* aarch64_st1_x3_v8hi */
    case 3610:  /* aarch64_st1_x3_v16qi */
      if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) || (((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))))
        {
	  return 0;
        }
      else if (((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1))))
        {
	  return 3;
        }
      else
        {
	  return 0;
        }

    case 4019:  /* aarch64_bfdot_laneqv4sf */
    case 4018:  /* aarch64_bfdot_lanev4sf */
    case 4017:  /* aarch64_bfdot_laneqv2sf */
    case 4016:  /* aarch64_bfdot_lanev2sf */
    case 4015:  /* aarch64_bfdotv4sf */
    case 4014:  /* aarch64_bfdotv2sf */
    case 1530:  /* aarch64_sudot_laneqv16qi */
    case 1529:  /* aarch64_usdot_laneqv16qi */
    case 1528:  /* aarch64_sudot_laneqv8qi */
    case 1527:  /* aarch64_usdot_laneqv8qi */
    case 1526:  /* aarch64_sudot_lanev16qi */
    case 1525:  /* aarch64_usdot_lanev16qi */
    case 1524:  /* aarch64_sudot_lanev8qi */
    case 1523:  /* aarch64_usdot_lanev8qi */
    case 1522:  /* aarch64_udot_laneqv16qi */
    case 1521:  /* aarch64_sdot_laneqv16qi */
    case 1520:  /* aarch64_udot_laneqv8qi */
    case 1519:  /* aarch64_sdot_laneqv8qi */
    case 1518:  /* aarch64_udot_lanev16qi */
    case 1517:  /* aarch64_sdot_lanev16qi */
    case 1516:  /* aarch64_udot_lanev8qi */
    case 1515:  /* aarch64_sdot_lanev8qi */
    case 1514:  /* aarch64_usdotv16qi */
    case 1513:  /* aarch64_usdotv8qi */
    case 1512:  /* aarch64_udotv16qi */
    case 1511:  /* aarch64_sdotv16qi */
    case 1510:  /* aarch64_udotv8qi */
    case 1509:  /* aarch64_sdotv8qi */
      if (((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57))))
        {
	  return 4;
        }
      else
        {
	  return 0;
        }

    case 10027:  /* aarch64_sve2_sm4ekey */
    case 10026:  /* aarch64_sve2_sm4e */
    case 10025:  /* aarch64_sve2_rax1 */
    case 4356:  /* aarch64_update_ffrt */
    case 4349:  /* aarch64_copy_ffr_to_ffrt */
    case 4348:  /* aarch64_update_ffr_for_load */
    case 3972:  /* aarch64_sm4ekeyqv4si */
    case 3971:  /* aarch64_sm4eqv4si */
    case 3970:  /* aarch64_sm3partw2qv4si */
    case 3969:  /* aarch64_sm3partw1qv4si */
    case 3968:  /* aarch64_sm3tt2bqv4si */
    case 3967:  /* aarch64_sm3tt2aqv4si */
    case 3966:  /* aarch64_sm3tt1bqv4si */
    case 3965:  /* aarch64_sm3tt1aqv4si */
    case 3964:  /* aarch64_sm3ss1qv4si */
    case 3963:  /* bcaxqv2di4 */
    case 3962:  /* bcaxqv4si4 */
    case 3961:  /* bcaxqv8hi4 */
    case 3960:  /* bcaxqv16qi4 */
    case 3959:  /* aarch64_xarqv2di */
    case 3958:  /* aarch64_rax1qv2di */
    case 3957:  /* eor3qv2di4 */
    case 3956:  /* eor3qv4si4 */
    case 3955:  /* eor3qv8hi4 */
    case 3954:  /* eor3qv16qi4 */
    case 3953:  /* aarch64_crypto_sha512su1qv2di */
    case 3952:  /* aarch64_crypto_sha512su0qv2di */
    case 3951:  /* aarch64_crypto_sha512h2qv2di */
    case 3950:  /* aarch64_crypto_sha512hqv2di */
    case 1508:  /* aarch64_fcmlaq_lane270v4sf */
    case 1507:  /* aarch64_fcmlaq_lane180v4sf */
    case 1506:  /* aarch64_fcmlaq_lane90v4sf */
    case 1505:  /* aarch64_fcmlaq_lane0v4sf */
    case 1504:  /* aarch64_fcmlaq_lane270v8hf */
    case 1503:  /* aarch64_fcmlaq_lane180v8hf */
    case 1502:  /* aarch64_fcmlaq_lane90v8hf */
    case 1501:  /* aarch64_fcmlaq_lane0v8hf */
    case 1500:  /* aarch64_fcmla_laneq270v4hf */
    case 1499:  /* aarch64_fcmla_laneq180v4hf */
    case 1498:  /* aarch64_fcmla_laneq90v4hf */
    case 1497:  /* aarch64_fcmla_laneq0v4hf */
    case 1496:  /* aarch64_fcmla_lane270v2df */
    case 1495:  /* aarch64_fcmla_lane180v2df */
    case 1494:  /* aarch64_fcmla_lane90v2df */
    case 1493:  /* aarch64_fcmla_lane0v2df */
    case 1492:  /* aarch64_fcmla_lane270v4sf */
    case 1491:  /* aarch64_fcmla_lane180v4sf */
    case 1490:  /* aarch64_fcmla_lane90v4sf */
    case 1489:  /* aarch64_fcmla_lane0v4sf */
    case 1488:  /* aarch64_fcmla_lane270v2sf */
    case 1487:  /* aarch64_fcmla_lane180v2sf */
    case 1486:  /* aarch64_fcmla_lane90v2sf */
    case 1485:  /* aarch64_fcmla_lane0v2sf */
    case 1484:  /* aarch64_fcmla_lane270v8hf */
    case 1483:  /* aarch64_fcmla_lane180v8hf */
    case 1482:  /* aarch64_fcmla_lane90v8hf */
    case 1481:  /* aarch64_fcmla_lane0v8hf */
    case 1480:  /* aarch64_fcmla_lane270v4hf */
    case 1479:  /* aarch64_fcmla_lane180v4hf */
    case 1478:  /* aarch64_fcmla_lane90v4hf */
    case 1477:  /* aarch64_fcmla_lane0v4hf */
    case 1476:  /* aarch64_fcmla270v2df */
    case 1475:  /* aarch64_fcmla180v2df */
    case 1474:  /* aarch64_fcmla90v2df */
    case 1473:  /* aarch64_fcmla0v2df */
    case 1472:  /* aarch64_fcmla270v4sf */
    case 1471:  /* aarch64_fcmla180v4sf */
    case 1470:  /* aarch64_fcmla90v4sf */
    case 1469:  /* aarch64_fcmla0v4sf */
    case 1468:  /* aarch64_fcmla270v2sf */
    case 1467:  /* aarch64_fcmla180v2sf */
    case 1466:  /* aarch64_fcmla90v2sf */
    case 1465:  /* aarch64_fcmla0v2sf */
    case 1464:  /* aarch64_fcmla270v8hf */
    case 1463:  /* aarch64_fcmla180v8hf */
    case 1462:  /* aarch64_fcmla90v8hf */
    case 1461:  /* aarch64_fcmla0v8hf */
    case 1460:  /* aarch64_fcmla270v4hf */
    case 1459:  /* aarch64_fcmla180v4hf */
    case 1458:  /* aarch64_fcmla90v4hf */
    case 1457:  /* aarch64_fcmla0v4hf */
    case 1456:  /* aarch64_fcadd270v2df */
    case 1455:  /* aarch64_fcadd90v2df */
    case 1454:  /* aarch64_fcadd270v4sf */
    case 1453:  /* aarch64_fcadd90v4sf */
    case 1452:  /* aarch64_fcadd270v2sf */
    case 1451:  /* aarch64_fcadd90v2sf */
    case 1450:  /* aarch64_fcadd270v8hf */
    case 1449:  /* aarch64_fcadd90v8hf */
    case 1448:  /* aarch64_fcadd270v4hf */
    case 1447:  /* aarch64_fcadd90v4hf */
    case 1126:  /* stg */
    case 1125:  /* ldg */
    case 1124:  /* subp */
    case 1123:  /* addg */
    case 1122:  /* gmi */
    case 1121:  /* irg */
    case 1118:  /* tcancel */
    case 1117:  /* tcommit */
    case 1116:  /* ttest */
    case 1115:  /* tstart */
    case 1083:  /* bti_jc */
    case 1082:  /* bti_j */
    case 1081:  /* bti_c */
    case 1080:  /* bti_noarg */
    case 25:  /* nop */
      return 0;

    case -1:
      if (GET_CODE (PATTERN (insn)) != ASM_INPUT
          && asm_noperands (PATTERN (insn)) < 0)
        fatal_insn_not_found (insn);
      /* FALLTHRU */
    case 1:  /* indirect_jump */
    case 2:  /* jump */
    case 3:  /* ccmpccsi */
    case 4:  /* ccmpccdi */
    case 5:  /* ccmpccfpsf */
    case 6:  /* ccmpccfpdf */
    case 7:  /* ccmpccfpesf */
    case 8:  /* ccmpccfpedf */
    case 9:  /* ccmpccsi_rev */
    case 10:  /* ccmpccdi_rev */
    case 11:  /* ccmpccfpsf_rev */
    case 12:  /* ccmpccfpdf_rev */
    case 13:  /* ccmpccfpesf_rev */
    case 14:  /* ccmpccfpedf_rev */
    case 15:  /* condjump */
    case 24:  /* *casesi_dispatch */
    case 26:  /* prefetch */
    case 27:  /* trap */
    case 28:  /* *do_return */
    case 29:  /* simple_return */
    case 30:  /* *cbeqsi1 */
    case 31:  /* *cbnesi1 */
    case 32:  /* *cbeqdi1 */
    case 33:  /* *cbnedi1 */
    case 34:  /* *tbeqsi1 */
    case 35:  /* *tbnesi1 */
    case 36:  /* *tbeqdi1 */
    case 37:  /* *tbnedi1 */
    case 38:  /* *cbltqi1 */
    case 39:  /* *cbgeqi1 */
    case 40:  /* *cblthi1 */
    case 41:  /* *cbgehi1 */
    case 42:  /* *cbltsi1 */
    case 43:  /* *cbgesi1 */
    case 44:  /* *cbltdi1 */
    case 45:  /* *cbgedi1 */
    case 46:  /* *call_insn */
    case 47:  /* *call_value_insn */
    case 48:  /* *sibcall_insn */
    case 49:  /* *sibcall_value_insn */
    case 50:  /* *movqi_aarch64 */
    case 51:  /* *movhi_aarch64 */
    case 52:  /* *movsi_aarch64 */
    case 53:  /* *movdi_aarch64 */
    case 54:  /* insv_immsi */
    case 55:  /* insv_immdi */
    case 56:  /* aarch64_movksi */
    case 57:  /* aarch64_movkdi */
    case 58:  /* *movti_aarch64 */
    case 59:  /* *movhf_aarch64 */
    case 60:  /* *movbf_aarch64 */
    case 61:  /* *movsf_aarch64 */
    case 62:  /* *movdf_aarch64 */
    case 63:  /* *movtf_aarch64 */
    case 64:  /* load_pair_sw_sisi */
    case 65:  /* load_pair_sw_sfsi */
    case 66:  /* load_pair_sw_sisf */
    case 67:  /* load_pair_sw_sfsf */
    case 68:  /* load_pair_dw_didi */
    case 69:  /* load_pair_dw_didf */
    case 70:  /* load_pair_dw_dfdi */
    case 71:  /* load_pair_dw_dfdf */
    case 72:  /* load_pair_dw_tftf */
    case 73:  /* store_pair_sw_sisi */
    case 74:  /* store_pair_sw_sfsi */
    case 75:  /* store_pair_sw_sisf */
    case 76:  /* store_pair_sw_sfsf */
    case 77:  /* store_pair_dw_didi */
    case 78:  /* store_pair_dw_didf */
    case 79:  /* store_pair_dw_dfdi */
    case 80:  /* store_pair_dw_dfdf */
    case 81:  /* store_pair_dw_tftf */
    case 82:  /* loadwb_pairsi_si */
    case 83:  /* loadwb_pairsi_di */
    case 84:  /* loadwb_pairdi_si */
    case 85:  /* loadwb_pairdi_di */
    case 86:  /* loadwb_pairsf_si */
    case 87:  /* loadwb_pairdf_si */
    case 88:  /* loadwb_pairsf_di */
    case 89:  /* loadwb_pairdf_di */
    case 90:  /* loadwb_pairti_si */
    case 91:  /* loadwb_pairti_di */
    case 92:  /* loadwb_pairtf_si */
    case 93:  /* loadwb_pairtf_di */
    case 94:  /* loadwb_pairv16qi_si */
    case 95:  /* loadwb_pairv16qi_di */
    case 96:  /* storewb_pairsi_si */
    case 97:  /* storewb_pairsi_di */
    case 98:  /* storewb_pairdi_si */
    case 99:  /* storewb_pairdi_di */
    case 100:  /* storewb_pairsf_si */
    case 101:  /* storewb_pairdf_si */
    case 102:  /* storewb_pairsf_di */
    case 103:  /* storewb_pairdf_di */
    case 104:  /* storewb_pairti_si */
    case 105:  /* storewb_pairti_di */
    case 106:  /* storewb_pairtf_si */
    case 107:  /* storewb_pairtf_di */
    case 108:  /* storewb_pairv16qi_si */
    case 109:  /* storewb_pairv16qi_di */
    case 110:  /* *extendsidi2_aarch64 */
    case 111:  /* *load_pair_extendsidi2_aarch64 */
    case 112:  /* *zero_extendsidi2_aarch64 */
    case 113:  /* *load_pair_zero_extendsidi2_aarch64 */
    case 114:  /* *extendqisi2_aarch64 */
    case 115:  /* *extendhisi2_aarch64 */
    case 116:  /* *extendqidi2_aarch64 */
    case 117:  /* *extendhidi2_aarch64 */
    case 118:  /* *zero_extendqisi2_aarch64 */
    case 119:  /* *zero_extendhisi2_aarch64 */
    case 120:  /* *zero_extendqidi2_aarch64 */
    case 121:  /* *zero_extendhidi2_aarch64 */
    case 122:  /* *extendqihi2_aarch64 */
    case 123:  /* *zero_extendqihi2_aarch64 */
    case 124:  /* *addsi3_aarch64 */
    case 125:  /* *adddi3_aarch64 */
    case 126:  /* *addsi3_aarch64_uxtw */
    case 127:  /* *addsi3_poly_1 */
    case 128:  /* *adddi3_poly_1 */
    case 129:  /* addsi3_compare0 */
    case 130:  /* adddi3_compare0 */
    case 131:  /* *addsi3_compare0_uxtw */
    case 132:  /* *addsi3_compareC_cconly */
    case 133:  /* *adddi3_compareC_cconly */
    case 134:  /* addsi3_compareC */
    case 135:  /* adddi3_compareC */
    case 136:  /* *addsi3_compareV_cconly_imm */
    case 137:  /* *adddi3_compareV_cconly_imm */
    case 138:  /* *addsi3_compareV_cconly */
    case 139:  /* *adddi3_compareV_cconly */
    case 140:  /* addsi3_compareV_imm */
    case 141:  /* adddi3_compareV_imm */
    case 142:  /* addsi3_compareV */
    case 143:  /* adddi3_compareV */
    case 144:  /* *adds_shift_imm_si */
    case 145:  /* *adds_shift_imm_si */
    case 146:  /* *adds_shift_imm_si */
    case 147:  /* *adds_shift_imm_di */
    case 148:  /* *adds_shift_imm_di */
    case 149:  /* *adds_shift_imm_di */
    case 150:  /* *subs_shift_imm_si */
    case 151:  /* *subs_shift_imm_si */
    case 152:  /* *subs_shift_imm_si */
    case 153:  /* *subs_shift_imm_di */
    case 154:  /* *subs_shift_imm_di */
    case 155:  /* *subs_shift_imm_di */
    case 156:  /* *adds_extendqi_si */
    case 157:  /* *adds_zero_extendqi_si */
    case 158:  /* *adds_extendqi_di */
    case 159:  /* *adds_zero_extendqi_di */
    case 160:  /* *adds_extendhi_si */
    case 161:  /* *adds_zero_extendhi_si */
    case 162:  /* *adds_extendhi_di */
    case 163:  /* *adds_zero_extendhi_di */
    case 164:  /* *adds_extendsi_si */
    case 165:  /* *adds_zero_extendsi_si */
    case 166:  /* *adds_extendsi_di */
    case 167:  /* *adds_zero_extendsi_di */
    case 168:  /* *subs_extendqi_si */
    case 169:  /* *subs_zero_extendqi_si */
    case 170:  /* *subs_extendqi_di */
    case 171:  /* *subs_zero_extendqi_di */
    case 172:  /* *subs_extendhi_si */
    case 173:  /* *subs_zero_extendhi_si */
    case 174:  /* *subs_extendhi_di */
    case 175:  /* *subs_zero_extendhi_di */
    case 176:  /* *subs_extendsi_si */
    case 177:  /* *subs_zero_extendsi_si */
    case 178:  /* *subs_extendsi_di */
    case 179:  /* *subs_zero_extendsi_di */
    case 180:  /* *adds_extendqi_shift_si */
    case 181:  /* *adds_zero_extendqi_shift_si */
    case 182:  /* *adds_extendqi_shift_di */
    case 183:  /* *adds_zero_extendqi_shift_di */
    case 184:  /* *adds_extendhi_shift_si */
    case 185:  /* *adds_zero_extendhi_shift_si */
    case 186:  /* *adds_extendhi_shift_di */
    case 187:  /* *adds_zero_extendhi_shift_di */
    case 188:  /* *adds_extendsi_shift_si */
    case 189:  /* *adds_zero_extendsi_shift_si */
    case 190:  /* *adds_extendsi_shift_di */
    case 191:  /* *adds_zero_extendsi_shift_di */
    case 192:  /* *subs_extendqi_shift_si */
    case 193:  /* *subs_zero_extendqi_shift_si */
    case 194:  /* *subs_extendqi_shift_di */
    case 195:  /* *subs_zero_extendqi_shift_di */
    case 196:  /* *subs_extendhi_shift_si */
    case 197:  /* *subs_zero_extendhi_shift_si */
    case 198:  /* *subs_extendhi_shift_di */
    case 199:  /* *subs_zero_extendhi_shift_di */
    case 200:  /* *subs_extendsi_shift_si */
    case 201:  /* *subs_zero_extendsi_shift_si */
    case 202:  /* *subs_extendsi_shift_di */
    case 203:  /* *subs_zero_extendsi_shift_di */
    case 204:  /* *addsi3nr_compare0 */
    case 205:  /* *adddi3nr_compare0 */
    case 206:  /* aarch64_subsi_compare0 */
    case 207:  /* aarch64_subdi_compare0 */
    case 208:  /* *compare_negsi */
    case 209:  /* *compare_negdi */
    case 210:  /* *add_lsl_si */
    case 211:  /* *add_asr_si */
    case 212:  /* *add_lsr_si */
    case 213:  /* *add_lsl_di */
    case 214:  /* *add_asr_di */
    case 215:  /* *add_lsr_di */
    case 216:  /* *add_lsl_si_uxtw */
    case 217:  /* *add_asr_si_uxtw */
    case 218:  /* *add_lsr_si_uxtw */
    case 219:  /* *add_extendqi_si */
    case 220:  /* *add_zero_extendqi_si */
    case 221:  /* *add_extendqi_di */
    case 222:  /* *add_zero_extendqi_di */
    case 223:  /* *add_extendhi_si */
    case 224:  /* *add_zero_extendhi_si */
    case 225:  /* *add_extendhi_di */
    case 226:  /* *add_zero_extendhi_di */
    case 227:  /* *add_extendsi_si */
    case 228:  /* *add_zero_extendsi_si */
    case 229:  /* *add_extendsi_di */
    case 230:  /* *add_zero_extendsi_di */
    case 231:  /* *add_extendqi_si_uxtw */
    case 232:  /* *add_zero_extendqi_si_uxtw */
    case 233:  /* *add_extendhi_si_uxtw */
    case 234:  /* *add_zero_extendhi_si_uxtw */
    case 235:  /* *add_extendqi_si_uxtw */
    case 236:  /* *add_zero_extendqi_si_uxtw */
    case 237:  /* *add_extendhi_si_uxtw */
    case 238:  /* *add_zero_extendhi_si_uxtw */
    case 239:  /* *add_extendqi_shft_si */
    case 240:  /* *add_zero_extendqi_shft_si */
    case 241:  /* *add_extendqi_shft_di */
    case 242:  /* *add_zero_extendqi_shft_di */
    case 243:  /* *add_extendhi_shft_si */
    case 244:  /* *add_zero_extendhi_shft_si */
    case 245:  /* *add_extendhi_shft_di */
    case 246:  /* *add_zero_extendhi_shft_di */
    case 247:  /* *add_extendsi_shft_si */
    case 248:  /* *add_zero_extendsi_shft_si */
    case 249:  /* *add_extendsi_shft_di */
    case 250:  /* *add_zero_extendsi_shft_di */
    case 251:  /* *add_extendqi_shft_si_uxtw */
    case 252:  /* *add_zero_extendqi_shft_si_uxtw */
    case 253:  /* *add_extendhi_shft_si_uxtw */
    case 254:  /* *add_zero_extendhi_shft_si_uxtw */
    case 255:  /* *addsi3_carryin */
    case 256:  /* *adddi3_carryin */
    case 257:  /* *addsi3_carryin_uxtw */
    case 258:  /* *addsi3_carryinC_zero */
    case 259:  /* *adddi3_carryinC_zero */
    case 260:  /* *addsi3_carryinC */
    case 261:  /* *adddi3_carryinC */
    case 262:  /* *addsi3_carryinV_zero */
    case 263:  /* *adddi3_carryinV_zero */
    case 264:  /* *addsi3_carryinV */
    case 265:  /* *adddi3_carryinV */
    case 266:  /* *add_uxtsi_shift2 */
    case 267:  /* *add_uxtdi_shift2 */
    case 268:  /* *add_uxtsi_shift2_uxtw */
    case 269:  /* subsi3 */
    case 270:  /* *subsi3_uxtw */
    case 271:  /* subdi3 */
    case 272:  /* subvsi_insn */
    case 273:  /* subvdi_insn */
    case 274:  /* subvsi_imm */
    case 275:  /* subvdi_imm */
    case 276:  /* negvsi_insn */
    case 277:  /* negvdi_insn */
    case 278:  /* negvsi_cmp_only */
    case 279:  /* negvdi_cmp_only */
    case 280:  /* *cmpvsi_insn */
    case 281:  /* *cmpvdi_insn */
    case 282:  /* negdi_carryout */
    case 283:  /* negvdi_carryinV */
    case 284:  /* *subsi3_compare0 */
    case 285:  /* *subdi3_compare0 */
    case 286:  /* *subsi3_compare0_uxtw */
    case 287:  /* subsi3_compare1_imm */
    case 288:  /* subdi3_compare1_imm */
    case 289:  /* subsi3_compare1 */
    case 290:  /* subdi3_compare1 */
    case 291:  /* *sub_lsl_si */
    case 292:  /* *sub_asr_si */
    case 293:  /* *sub_lsr_si */
    case 294:  /* *sub_lsl_di */
    case 295:  /* *sub_asr_di */
    case 296:  /* *sub_lsr_di */
    case 297:  /* *sub_lsl_si_uxtw */
    case 298:  /* *sub_asr_si_uxtw */
    case 299:  /* *sub_lsr_si_uxtw */
    case 300:  /* *sub_extendqi_si */
    case 301:  /* *sub_zero_extendqi_si */
    case 302:  /* *sub_extendqi_di */
    case 303:  /* *sub_zero_extendqi_di */
    case 304:  /* *sub_extendhi_si */
    case 305:  /* *sub_zero_extendhi_si */
    case 306:  /* *sub_extendhi_di */
    case 307:  /* *sub_zero_extendhi_di */
    case 308:  /* *sub_extendsi_si */
    case 309:  /* *sub_zero_extendsi_si */
    case 310:  /* *sub_extendsi_di */
    case 311:  /* *sub_zero_extendsi_di */
    case 312:  /* *sub_extendqi_si_uxtw */
    case 313:  /* *sub_zero_extendqi_si_uxtw */
    case 314:  /* *sub_extendhi_si_uxtw */
    case 315:  /* *sub_zero_extendhi_si_uxtw */
    case 316:  /* *sub_extendqi_shft_si */
    case 317:  /* *sub_zero_extendqi_shft_si */
    case 318:  /* *sub_extendqi_shft_di */
    case 319:  /* *sub_zero_extendqi_shft_di */
    case 320:  /* *sub_extendhi_shft_si */
    case 321:  /* *sub_zero_extendhi_shft_si */
    case 322:  /* *sub_extendhi_shft_di */
    case 323:  /* *sub_zero_extendhi_shft_di */
    case 324:  /* *sub_extendsi_shft_si */
    case 325:  /* *sub_zero_extendsi_shft_si */
    case 326:  /* *sub_extendsi_shft_di */
    case 327:  /* *sub_zero_extendsi_shft_di */
    case 328:  /* *sub_extendqi_shft_si_uxtw */
    case 329:  /* *sub_zero_extendqi_shft_si_uxtw */
    case 330:  /* *sub_extendhi_shft_si_uxtw */
    case 331:  /* *sub_zero_extendhi_shft_si_uxtw */
    case 332:  /* *subsi3_carryin0 */
    case 333:  /* *subdi3_carryin0 */
    case 334:  /* *subsi3_carryin_uxtw */
    case 335:  /* *subsi3_carryin */
    case 336:  /* *subdi3_carryin */
    case 337:  /* *subsi3_carryin_uxtw */
    case 338:  /* *subsi3_carryin_alt */
    case 339:  /* *subdi3_carryin_alt */
    case 340:  /* *subsi3_carryin_alt_uxtw */
    case 341:  /* *usubsi3_carryinC_z1 */
    case 342:  /* *usubdi3_carryinC_z1 */
    case 343:  /* *usubsi3_carryinC_z2 */
    case 344:  /* *usubdi3_carryinC_z2 */
    case 345:  /* *usubsi3_carryinC */
    case 346:  /* *usubdi3_carryinC */
    case 347:  /* *subsi3_carryinV_z2 */
    case 348:  /* *subdi3_carryinV_z2 */
    case 349:  /* *subsi3_carryinV */
    case 350:  /* *subdi3_carryinV */
    case 351:  /* *sub_uxtsi_shift2 */
    case 352:  /* *sub_uxtdi_shift2 */
    case 353:  /* *sub_uxtsi_shift2_uxtw */
    case 354:  /* negsi2 */
    case 355:  /* negdi2 */
    case 356:  /* *negsi2_uxtw */
    case 357:  /* *ngcsi */
    case 358:  /* *ngcdi */
    case 359:  /* *ngcsi_uxtw */
    case 360:  /* negsi2_compare0 */
    case 361:  /* negdi2_compare0 */
    case 362:  /* *negsi2_compare0_uxtw */
    case 363:  /* *neg_lslsi3_compare0 */
    case 364:  /* *neg_asrsi3_compare0 */
    case 365:  /* *neg_lsrsi3_compare0 */
    case 366:  /* *neg_lsldi3_compare0 */
    case 367:  /* *neg_asrdi3_compare0 */
    case 368:  /* *neg_lsrdi3_compare0 */
    case 369:  /* *neg_lsl_si2 */
    case 370:  /* *neg_asr_si2 */
    case 371:  /* *neg_lsr_si2 */
    case 372:  /* *neg_lsl_di2 */
    case 373:  /* *neg_asr_di2 */
    case 374:  /* *neg_lsr_di2 */
    case 375:  /* *neg_lsl_si2_uxtw */
    case 376:  /* *neg_asr_si2_uxtw */
    case 377:  /* *neg_lsr_si2_uxtw */
    case 378:  /* *neg_asr_si2_extr */
    case 379:  /* mulsi3 */
    case 380:  /* muldi3 */
    case 381:  /* *mulsi3_uxtw */
    case 382:  /* maddsi */
    case 383:  /* madddi */
    case 384:  /* *maddsi_uxtw */
    case 385:  /* *msubsi */
    case 386:  /* *msubdi */
    case 387:  /* *msubsi_uxtw */
    case 388:  /* *mulsi_neg */
    case 389:  /* *muldi_neg */
    case 390:  /* *mulsi_neg_uxtw */
    case 391:  /* mulsidi3 */
    case 392:  /* umulsidi3 */
    case 393:  /* maddsidi4 */
    case 394:  /* umaddsidi4 */
    case 395:  /* msubsidi4 */
    case 396:  /* umsubsidi4 */
    case 397:  /* *mulsidi_neg */
    case 398:  /* *umulsidi_neg */
    case 399:  /* smuldi3_highpart */
    case 400:  /* umuldi3_highpart */
    case 401:  /* divsi3 */
    case 402:  /* udivsi3 */
    case 403:  /* divdi3 */
    case 404:  /* udivdi3 */
    case 405:  /* *divsi3_uxtw */
    case 406:  /* *udivsi3_uxtw */
    case 407:  /* cmpsi */
    case 408:  /* cmpdi */
    case 409:  /* fcmpsf */
    case 410:  /* fcmpdf */
    case 411:  /* fcmpesf */
    case 412:  /* fcmpedf */
    case 413:  /* *cmp_swp_lsl_regsi */
    case 414:  /* *cmp_swp_asr_regsi */
    case 415:  /* *cmp_swp_lsr_regsi */
    case 416:  /* *cmp_swp_lsl_regdi */
    case 417:  /* *cmp_swp_asr_regdi */
    case 418:  /* *cmp_swp_lsr_regdi */
    case 419:  /* *cmp_swp_extendqi_regsi */
    case 420:  /* *cmp_swp_zero_extendqi_regsi */
    case 421:  /* *cmp_swp_extendqi_regdi */
    case 422:  /* *cmp_swp_zero_extendqi_regdi */
    case 423:  /* *cmp_swp_extendhi_regsi */
    case 424:  /* *cmp_swp_zero_extendhi_regsi */
    case 425:  /* *cmp_swp_extendhi_regdi */
    case 426:  /* *cmp_swp_zero_extendhi_regdi */
    case 427:  /* *cmp_swp_extendsi_regsi */
    case 428:  /* *cmp_swp_zero_extendsi_regsi */
    case 429:  /* *cmp_swp_extendsi_regdi */
    case 430:  /* *cmp_swp_zero_extendsi_regdi */
    case 431:  /* *cmp_swp_extendqi_shft_si */
    case 432:  /* *cmp_swp_zero_extendqi_shft_si */
    case 433:  /* *cmp_swp_extendqi_shft_di */
    case 434:  /* *cmp_swp_zero_extendqi_shft_di */
    case 435:  /* *cmp_swp_extendhi_shft_si */
    case 436:  /* *cmp_swp_zero_extendhi_shft_si */
    case 437:  /* *cmp_swp_extendhi_shft_di */
    case 438:  /* *cmp_swp_zero_extendhi_shft_di */
    case 439:  /* *cmp_swp_extendsi_shft_si */
    case 440:  /* *cmp_swp_zero_extendsi_shft_si */
    case 441:  /* *cmp_swp_extendsi_shft_di */
    case 442:  /* *cmp_swp_zero_extendsi_shft_di */
    case 443:  /* aarch64_cstoreqi */
    case 444:  /* aarch64_cstorehi */
    case 445:  /* aarch64_cstoresi */
    case 446:  /* aarch64_cstoredi */
    case 447:  /* *compare_cstoresi_insn */
    case 448:  /* *compare_cstoresi_insn */
    case 449:  /* *compare_cstoredi_insn */
    case 450:  /* *compare_cstoredi_insn */
    case 451:  /* *cstoresi_insn_uxtw */
    case 452:  /* cstoreqi_neg */
    case 453:  /* cstorehi_neg */
    case 454:  /* cstoresi_neg */
    case 455:  /* cstoredi_neg */
    case 456:  /* *cstoresi_neg_uxtw */
    case 457:  /* *cmovqi_insn */
    case 458:  /* *cmovhi_insn */
    case 459:  /* *cmovsi_insn */
    case 460:  /* *cmovdi_insn */
    case 461:  /* *cmovsi_insn_uxtw */
    case 462:  /* *cmovdi_insn_uxtw */
    case 463:  /* *cmovsf_insn */
    case 464:  /* *cmovdf_insn */
    case 465:  /* aarch64_crc32b */
    case 466:  /* aarch64_crc32h */
    case 467:  /* aarch64_crc32w */
    case 468:  /* aarch64_crc32x */
    case 469:  /* aarch64_crc32cb */
    case 470:  /* aarch64_crc32ch */
    case 471:  /* aarch64_crc32cw */
    case 472:  /* aarch64_crc32cx */
    case 473:  /* *csinc2si_insn */
    case 474:  /* *csinc2di_insn */
    case 475:  /* csinc3si_insn */
    case 476:  /* csinc3di_insn */
    case 477:  /* *csinv3si_insn */
    case 478:  /* *csinv3di_insn */
    case 479:  /* csneg3_uxtw_insn */
    case 480:  /* csneg3si_insn */
    case 481:  /* csneg3di_insn */
    case 482:  /* *csinv3_uxtw_insn1 */
    case 483:  /* *csinv3_uxtw_insn1 */
    case 484:  /* *csinv3_uxtw_insn2 */
    case 485:  /* *csinv3_uxtw_insn2 */
    case 486:  /* *csinv3_uxtw_insn3 */
    case 487:  /* *csinv3_uxtw_insn3 */
    case 492:  /* andsi3 */
    case 493:  /* iorsi3 */
    case 494:  /* xorsi3 */
    case 495:  /* anddi3 */
    case 496:  /* iordi3 */
    case 497:  /* xordi3 */
    case 498:  /* *andsi3_uxtw */
    case 499:  /* *iorsi3_uxtw */
    case 500:  /* *xorsi3_uxtw */
    case 501:  /* *andsi3_compare0 */
    case 502:  /* *anddi3_compare0 */
    case 503:  /* *andsi3_compare0_uxtw */
    case 504:  /* *and_ashlsi3_compare0 */
    case 505:  /* *and_ashrsi3_compare0 */
    case 506:  /* *and_lshrsi3_compare0 */
    case 507:  /* *and_rotrsi3_compare0 */
    case 508:  /* *and_ashldi3_compare0 */
    case 509:  /* *and_ashrdi3_compare0 */
    case 510:  /* *and_lshrdi3_compare0 */
    case 511:  /* *and_rotrdi3_compare0 */
    case 512:  /* *and_ashlsi3_compare0_uxtw */
    case 513:  /* *and_ashrsi3_compare0_uxtw */
    case 514:  /* *and_lshrsi3_compare0_uxtw */
    case 515:  /* *and_rotrsi3_compare0_uxtw */
    case 516:  /* *and_ashlsi3 */
    case 517:  /* *ior_ashlsi3 */
    case 518:  /* *xor_ashlsi3 */
    case 519:  /* *and_ashrsi3 */
    case 520:  /* *ior_ashrsi3 */
    case 521:  /* *xor_ashrsi3 */
    case 522:  /* *and_lshrsi3 */
    case 523:  /* *ior_lshrsi3 */
    case 524:  /* *xor_lshrsi3 */
    case 525:  /* *and_rotrsi3 */
    case 526:  /* *ior_rotrsi3 */
    case 527:  /* *xor_rotrsi3 */
    case 528:  /* *and_ashldi3 */
    case 529:  /* *ior_ashldi3 */
    case 530:  /* *xor_ashldi3 */
    case 531:  /* *and_ashrdi3 */
    case 532:  /* *ior_ashrdi3 */
    case 533:  /* *xor_ashrdi3 */
    case 534:  /* *and_lshrdi3 */
    case 535:  /* *ior_lshrdi3 */
    case 536:  /* *xor_lshrdi3 */
    case 537:  /* *and_rotrdi3 */
    case 538:  /* *ior_rotrdi3 */
    case 539:  /* *xor_rotrdi3 */
    case 540:  /* *and_rolsi3 */
    case 541:  /* *ior_rolsi3 */
    case 542:  /* *xor_rolsi3 */
    case 543:  /* *and_roldi3 */
    case 544:  /* *ior_roldi3 */
    case 545:  /* *xor_roldi3 */
    case 546:  /* *and_ashlsi3_uxtw */
    case 547:  /* *ior_ashlsi3_uxtw */
    case 548:  /* *xor_ashlsi3_uxtw */
    case 549:  /* *and_ashrsi3_uxtw */
    case 550:  /* *ior_ashrsi3_uxtw */
    case 551:  /* *xor_ashrsi3_uxtw */
    case 552:  /* *and_lshrsi3_uxtw */
    case 553:  /* *ior_lshrsi3_uxtw */
    case 554:  /* *xor_lshrsi3_uxtw */
    case 555:  /* *and_rotrsi3_uxtw */
    case 556:  /* *ior_rotrsi3_uxtw */
    case 557:  /* *xor_rotrsi3_uxtw */
    case 558:  /* *and_rolsi3_uxtw */
    case 559:  /* *ior_rolsi3_uxtw */
    case 560:  /* *xor_rolsi3_uxtw */
    case 561:  /* one_cmplsi2 */
    case 562:  /* one_cmpldi2 */
    case 563:  /* *one_cmpl_zero_extend */
    case 564:  /* *one_cmpl_ashlsi2 */
    case 565:  /* *one_cmpl_ashrsi2 */
    case 566:  /* *one_cmpl_lshrsi2 */
    case 567:  /* *one_cmpl_rotrsi2 */
    case 568:  /* *one_cmpl_ashldi2 */
    case 569:  /* *one_cmpl_ashrdi2 */
    case 570:  /* *one_cmpl_lshrdi2 */
    case 571:  /* *one_cmpl_rotrdi2 */
    case 572:  /* *and_one_cmplsi3 */
    case 573:  /* *ior_one_cmplsi3 */
    case 574:  /* *and_one_cmpldi3 */
    case 575:  /* *ior_one_cmpldi3 */
    case 576:  /* *and_one_cmplsidi3_ze */
    case 577:  /* *ior_one_cmplsidi3_ze */
    case 578:  /* *xor_one_cmplsidi3_ze */
    case 579:  /* *xor_one_cmplsi3 */
    case 580:  /* *xor_one_cmpldi3 */
    case 581:  /* *and_one_cmplsi3_compare0 */
    case 582:  /* *and_one_cmpldi3_compare0 */
    case 583:  /* *and_one_cmplsi3_compare0_uxtw */
    case 584:  /* *and_one_cmplsi3_compare0_no_reuse */
    case 585:  /* *and_one_cmpldi3_compare0_no_reuse */
    case 586:  /* and_one_cmpl_ashlsi3 */
    case 587:  /* ior_one_cmpl_ashlsi3 */
    case 588:  /* xor_one_cmpl_ashlsi3 */
    case 589:  /* and_one_cmpl_ashrsi3 */
    case 590:  /* ior_one_cmpl_ashrsi3 */
    case 591:  /* xor_one_cmpl_ashrsi3 */
    case 592:  /* and_one_cmpl_lshrsi3 */
    case 593:  /* ior_one_cmpl_lshrsi3 */
    case 594:  /* xor_one_cmpl_lshrsi3 */
    case 595:  /* and_one_cmpl_rotrsi3 */
    case 596:  /* ior_one_cmpl_rotrsi3 */
    case 597:  /* xor_one_cmpl_rotrsi3 */
    case 598:  /* and_one_cmpl_ashldi3 */
    case 599:  /* ior_one_cmpl_ashldi3 */
    case 600:  /* xor_one_cmpl_ashldi3 */
    case 601:  /* and_one_cmpl_ashrdi3 */
    case 602:  /* ior_one_cmpl_ashrdi3 */
    case 603:  /* xor_one_cmpl_ashrdi3 */
    case 604:  /* and_one_cmpl_lshrdi3 */
    case 605:  /* ior_one_cmpl_lshrdi3 */
    case 606:  /* xor_one_cmpl_lshrdi3 */
    case 607:  /* and_one_cmpl_rotrdi3 */
    case 608:  /* ior_one_cmpl_rotrdi3 */
    case 609:  /* xor_one_cmpl_rotrdi3 */
    case 610:  /* *eor_one_cmpl_ashlsi3_alt */
    case 611:  /* *eor_one_cmpl_ashrsi3_alt */
    case 612:  /* *eor_one_cmpl_lshrsi3_alt */
    case 613:  /* *eor_one_cmpl_rotrsi3_alt */
    case 614:  /* *eor_one_cmpl_ashldi3_alt */
    case 615:  /* *eor_one_cmpl_ashrdi3_alt */
    case 616:  /* *eor_one_cmpl_lshrdi3_alt */
    case 617:  /* *eor_one_cmpl_rotrdi3_alt */
    case 618:  /* *eor_one_cmpl_ashlsidi3_alt_ze */
    case 619:  /* *eor_one_cmpl_ashrsidi3_alt_ze */
    case 620:  /* *eor_one_cmpl_lshrsidi3_alt_ze */
    case 621:  /* *eor_one_cmpl_rotrsidi3_alt_ze */
    case 622:  /* *and_one_cmpl_ashlsi3_compare0 */
    case 623:  /* *and_one_cmpl_ashrsi3_compare0 */
    case 624:  /* *and_one_cmpl_lshrsi3_compare0 */
    case 625:  /* *and_one_cmpl_rotrsi3_compare0 */
    case 626:  /* *and_one_cmpl_ashldi3_compare0 */
    case 627:  /* *and_one_cmpl_ashrdi3_compare0 */
    case 628:  /* *and_one_cmpl_lshrdi3_compare0 */
    case 629:  /* *and_one_cmpl_rotrdi3_compare0 */
    case 630:  /* *and_one_cmpl_ashlsi3_compare0_uxtw */
    case 631:  /* *and_one_cmpl_ashrsi3_compare0_uxtw */
    case 632:  /* *and_one_cmpl_lshrsi3_compare0_uxtw */
    case 633:  /* *and_one_cmpl_rotrsi3_compare0_uxtw */
    case 634:  /* *and_one_cmpl_ashlsi3_compare0_no_reuse */
    case 635:  /* *and_one_cmpl_ashrsi3_compare0_no_reuse */
    case 636:  /* *and_one_cmpl_lshrsi3_compare0_no_reuse */
    case 637:  /* *and_one_cmpl_rotrsi3_compare0_no_reuse */
    case 638:  /* *and_one_cmpl_ashldi3_compare0_no_reuse */
    case 639:  /* *and_one_cmpl_ashrdi3_compare0_no_reuse */
    case 640:  /* *and_one_cmpl_lshrdi3_compare0_no_reuse */
    case 641:  /* *and_one_cmpl_rotrdi3_compare0_no_reuse */
    case 642:  /* clzsi2 */
    case 643:  /* clzdi2 */
    case 644:  /* clrsbsi2 */
    case 645:  /* clrsbdi2 */
    case 646:  /* aarch64_rbitsi */
    case 647:  /* aarch64_rbitdi */
    case 650:  /* *andqi_compare0 */
    case 651:  /* *andhi_compare0 */
    case 652:  /* *andssi_compare0 */
    case 653:  /* *andssi_compare0 */
    case 654:  /* *andsdi_compare0 */
    case 655:  /* *andsdi_compare0 */
    case 656:  /* *andsi3nr_compare0 */
    case 657:  /* *anddi3nr_compare0 */
    case 658:  /* *andsi3nr_compare0_zextract */
    case 659:  /* *anddi3nr_compare0_zextract */
    case 660:  /* *and_ashlsi3nr_compare0 */
    case 661:  /* *and_ashrsi3nr_compare0 */
    case 662:  /* *and_lshrsi3nr_compare0 */
    case 663:  /* *and_rotrsi3nr_compare0 */
    case 664:  /* *and_ashldi3nr_compare0 */
    case 665:  /* *and_ashrdi3nr_compare0 */
    case 666:  /* *and_lshrdi3nr_compare0 */
    case 667:  /* *and_rotrdi3nr_compare0 */
    case 668:  /* *aarch64_ashl_reg_si3_mask1 */
    case 669:  /* *aarch64_ashr_reg_si3_mask1 */
    case 670:  /* *aarch64_lshr_reg_si3_mask1 */
    case 671:  /* *aarch64_rotr_reg_si3_mask1 */
    case 672:  /* *aarch64_ashl_reg_di3_mask1 */
    case 673:  /* *aarch64_ashr_reg_di3_mask1 */
    case 674:  /* *aarch64_lshr_reg_di3_mask1 */
    case 675:  /* *aarch64_rotr_reg_di3_mask1 */
    case 686:  /* *aarch64_ashl_reg_di3_mask2 */
    case 687:  /* *aarch64_ashr_reg_di3_mask2 */
    case 688:  /* *aarch64_lshr_reg_di3_mask2 */
    case 689:  /* *aarch64_rotr_reg_di3_mask2 */
    case 696:  /* *aarch64_ashl_sisd_or_int_si3 */
    case 697:  /* *aarch64_ashl_sisd_or_int_di3 */
    case 698:  /* *aarch64_lshr_sisd_or_int_si3 */
    case 699:  /* *aarch64_lshr_sisd_or_int_di3 */
    case 700:  /* *aarch64_ashr_sisd_or_int_si3 */
    case 701:  /* *aarch64_ashr_sisd_or_int_di3 */
    case 702:  /* *aarch64_sisd_ushl */
    case 703:  /* *aarch64_ushl_2s */
    case 704:  /* *aarch64_sisd_sshl */
    case 705:  /* *aarch64_sshl_2s */
    case 706:  /* *aarch64_sisd_neg_qi */
    case 707:  /* *rorsi3_insn */
    case 708:  /* *rordi3_insn */
    case 709:  /* *ashlsi3_insn_uxtw */
    case 710:  /* *ashrsi3_insn_uxtw */
    case 711:  /* *lshrsi3_insn_uxtw */
    case 712:  /* *rotrsi3_insn_uxtw */
    case 713:  /* *ashlqi3_insn */
    case 714:  /* *ashrqi3_insn */
    case 715:  /* *lshrqi3_insn */
    case 716:  /* *ashlhi3_insn */
    case 717:  /* *ashrhi3_insn */
    case 718:  /* *lshrhi3_insn */
    case 719:  /* *extrsi5_insn */
    case 720:  /* *extrdi5_insn */
    case 721:  /* *extrsi5_insn_alt */
    case 722:  /* *extrdi5_insn_alt */
    case 723:  /* *extrsi5_insn_uxtw */
    case 724:  /* *extrsi5_insn_uxtw_alt */
    case 725:  /* *extrsi5_insn_di */
    case 726:  /* *rorsi3_insn */
    case 727:  /* *rordi3_insn */
    case 728:  /* *rorsi3_insn_uxtw */
    case 729:  /* *extendsi_ashlqi */
    case 730:  /* *zero_extendsi_ashlqi */
    case 731:  /* *extendsi_ashlhi */
    case 732:  /* *zero_extendsi_ashlhi */
    case 733:  /* *extenddi_ashlqi */
    case 734:  /* *zero_extenddi_ashlqi */
    case 735:  /* *extenddi_ashlhi */
    case 736:  /* *zero_extenddi_ashlhi */
    case 737:  /* *zero_extendsi_lshrqi */
    case 738:  /* *zero_extendsi_lshrhi */
    case 739:  /* *zero_extenddi_lshrqi */
    case 740:  /* *zero_extenddi_lshrhi */
    case 741:  /* *extendsi_ashrqi */
    case 742:  /* *extendsi_ashrhi */
    case 743:  /* *extenddi_ashrqi */
    case 744:  /* *extenddi_ashrhi */
    case 745:  /* *extvsi */
    case 746:  /* *extzvsi */
    case 747:  /* *extvdi */
    case 748:  /* *extzvdi */
    case 749:  /* *insv_regsi */
    case 750:  /* *insv_regdi */
    case 751:  /* *aarch64_bfisiqi4 */
    case 752:  /* *aarch64_bfidiqi4 */
    case 753:  /* *aarch64_bfisihi4 */
    case 754:  /* *aarch64_bfidihi4 */
    case 755:  /* *aarch64_bfisisi4 */
    case 756:  /* *aarch64_bfidisi4 */
    case 757:  /* *aarch64_bfisi5_shift */
    case 758:  /* *aarch64_bfidi5_shift */
    case 759:  /* *aarch64_bfisi5_shift_alt */
    case 760:  /* *aarch64_bfidi5_shift_alt */
    case 761:  /* *aarch64_bfisi4_noand */
    case 762:  /* *aarch64_bfidi4_noand */
    case 763:  /* *aarch64_bfisi4_noand_alt */
    case 764:  /* *aarch64_bfidi4_noand_alt */
    case 765:  /* *aarch64_bfisi4_noshift */
    case 766:  /* *aarch64_bfidi4_noshift */
    case 767:  /* *aarch64_bfisi4_noshift_alt */
    case 768:  /* *aarch64_bfidi4_noshift_alt */
    case 769:  /* *aarch64_bfxilsi_extr */
    case 770:  /* *aarch64_bfxildi_extr */
    case 771:  /* *aarch64_bfxilsi_extrdi */
    case 772:  /* *extr_insv_lower_regsi */
    case 773:  /* *extr_insv_lower_regdi */
    case 774:  /* *extendqi_shft_si */
    case 775:  /* *zero_extendqi_shft_si */
    case 776:  /* *extendqi_shft_di */
    case 777:  /* *zero_extendqi_shft_di */
    case 778:  /* *extendhi_shft_si */
    case 779:  /* *zero_extendhi_shft_si */
    case 780:  /* *extendhi_shft_di */
    case 781:  /* *zero_extendhi_shft_di */
    case 782:  /* *extendsi_shft_si */
    case 783:  /* *zero_extendsi_shft_si */
    case 784:  /* *extendsi_shft_di */
    case 785:  /* *zero_extendsi_shft_di */
    case 786:  /* *andim_ashiftsi_bfiz */
    case 787:  /* *andim_ashiftdi_bfiz */
    case 788:  /* *ashiftsi_extv_bfiz */
    case 789:  /* *ashiftdi_extv_bfiz */
    case 790:  /* *ashiftsi_extvdi_bfiz */
    case 791:  /* bswapsi2 */
    case 792:  /* bswapdi2 */
    case 793:  /* bswaphi2 */
    case 794:  /* aarch64_rev16si */
    case 795:  /* aarch64_rev16di */
    case 796:  /* *aarch64_bfxilsi */
    case 797:  /* *aarch64_bfxildi */
    case 798:  /* *aarch64_bfxilsi_uxtw */
    case 799:  /* rev16si2 */
    case 800:  /* rev16di2 */
    case 801:  /* rev16si2_alt */
    case 802:  /* rev16di2_alt */
    case 803:  /* *bswapsi2_uxtw */
    case 804:  /* btrunchf2 */
    case 805:  /* ceilhf2 */
    case 806:  /* floorhf2 */
    case 807:  /* frintnhf2 */
    case 808:  /* nearbyinthf2 */
    case 809:  /* rinthf2 */
    case 810:  /* roundhf2 */
    case 811:  /* btruncsf2 */
    case 812:  /* ceilsf2 */
    case 813:  /* floorsf2 */
    case 814:  /* frintnsf2 */
    case 815:  /* nearbyintsf2 */
    case 816:  /* rintsf2 */
    case 817:  /* roundsf2 */
    case 818:  /* btruncdf2 */
    case 819:  /* ceildf2 */
    case 820:  /* floordf2 */
    case 821:  /* frintndf2 */
    case 822:  /* nearbyintdf2 */
    case 823:  /* rintdf2 */
    case 824:  /* rounddf2 */
    case 825:  /* lbtrunchfsi2 */
    case 826:  /* lceilhfsi2 */
    case 827:  /* lfloorhfsi2 */
    case 828:  /* lroundhfsi2 */
    case 829:  /* lfrintnhfsi2 */
    case 830:  /* lbtruncuhfsi2 */
    case 831:  /* lceiluhfsi2 */
    case 832:  /* lflooruhfsi2 */
    case 833:  /* lrounduhfsi2 */
    case 834:  /* lfrintnuhfsi2 */
    case 835:  /* lbtruncsfsi2 */
    case 836:  /* lceilsfsi2 */
    case 837:  /* lfloorsfsi2 */
    case 838:  /* lroundsfsi2 */
    case 839:  /* lfrintnsfsi2 */
    case 840:  /* lbtruncusfsi2 */
    case 841:  /* lceilusfsi2 */
    case 842:  /* lfloorusfsi2 */
    case 843:  /* lroundusfsi2 */
    case 844:  /* lfrintnusfsi2 */
    case 845:  /* lbtruncdfsi2 */
    case 846:  /* lceildfsi2 */
    case 847:  /* lfloordfsi2 */
    case 848:  /* lrounddfsi2 */
    case 849:  /* lfrintndfsi2 */
    case 850:  /* lbtruncudfsi2 */
    case 851:  /* lceiludfsi2 */
    case 852:  /* lfloorudfsi2 */
    case 853:  /* lroundudfsi2 */
    case 854:  /* lfrintnudfsi2 */
    case 855:  /* lbtrunchfdi2 */
    case 856:  /* lceilhfdi2 */
    case 857:  /* lfloorhfdi2 */
    case 858:  /* lroundhfdi2 */
    case 859:  /* lfrintnhfdi2 */
    case 860:  /* lbtruncuhfdi2 */
    case 861:  /* lceiluhfdi2 */
    case 862:  /* lflooruhfdi2 */
    case 863:  /* lrounduhfdi2 */
    case 864:  /* lfrintnuhfdi2 */
    case 865:  /* lbtruncsfdi2 */
    case 866:  /* lceilsfdi2 */
    case 867:  /* lfloorsfdi2 */
    case 868:  /* lroundsfdi2 */
    case 869:  /* lfrintnsfdi2 */
    case 870:  /* lbtruncusfdi2 */
    case 871:  /* lceilusfdi2 */
    case 872:  /* lfloorusfdi2 */
    case 873:  /* lroundusfdi2 */
    case 874:  /* lfrintnusfdi2 */
    case 875:  /* lbtruncdfdi2 */
    case 876:  /* lceildfdi2 */
    case 877:  /* lfloordfdi2 */
    case 878:  /* lrounddfdi2 */
    case 879:  /* lfrintndfdi2 */
    case 880:  /* lbtruncudfdi2 */
    case 881:  /* lceiludfdi2 */
    case 882:  /* lfloorudfdi2 */
    case 883:  /* lroundudfdi2 */
    case 884:  /* lfrintnudfdi2 */
    case 885:  /* *aarch64_fcvtsfsi2_mult */
    case 886:  /* *aarch64_fcvtusfsi2_mult */
    case 887:  /* *aarch64_fcvtdfsi2_mult */
    case 888:  /* *aarch64_fcvtudfsi2_mult */
    case 889:  /* *aarch64_fcvtsfdi2_mult */
    case 890:  /* *aarch64_fcvtusfdi2_mult */
    case 891:  /* *aarch64_fcvtdfdi2_mult */
    case 892:  /* *aarch64_fcvtudfdi2_mult */
    case 893:  /* *aarch64_fmahf4 */
    case 894:  /* *aarch64_fmasf4 */
    case 895:  /* *aarch64_fmadf4 */
    case 896:  /* *aarch64_fnmahf4 */
    case 897:  /* *aarch64_fnmasf4 */
    case 898:  /* *aarch64_fnmadf4 */
    case 899:  /* *aarch64_fmssf4 */
    case 900:  /* *aarch64_fmsdf4 */
    case 901:  /* *aarch64_fnmssf4 */
    case 902:  /* *aarch64_fnmsdf4 */
    case 903:  /* *aarch64_fnmaddsf4 */
    case 904:  /* *aarch64_fnmadddf4 */
    case 905:  /* extendsfdf2 */
    case 906:  /* extendhfsf2 */
    case 907:  /* extendhfdf2 */
    case 908:  /* truncdfsf2 */
    case 909:  /* truncsfhf2 */
    case 910:  /* truncdfhf2 */
    case 911:  /* fix_truncsfsi2 */
    case 912:  /* fixuns_truncsfsi2 */
    case 913:  /* fix_truncdfdi2 */
    case 914:  /* fixuns_truncdfdi2 */
    case 915:  /* fix_trunchfsi2 */
    case 916:  /* fixuns_trunchfsi2 */
    case 917:  /* fix_trunchfdi2 */
    case 918:  /* fixuns_trunchfdi2 */
    case 919:  /* fix_truncdfsi2 */
    case 920:  /* fixuns_truncdfsi2 */
    case 921:  /* fix_truncsfdi2 */
    case 922:  /* fixuns_truncsfdi2 */
    case 923:  /* *fix_to_zero_extendsfdi2 */
    case 924:  /* *fix_to_zero_extenddfdi2 */
    case 925:  /* *aarch64_scvtfsisf2_mult */
    case 926:  /* *aarch64_ucvtfsisf2_mult */
    case 927:  /* *aarch64_scvtfdidf2_mult */
    case 928:  /* *aarch64_ucvtfdidf2_mult */
    case 929:  /* *aarch64_scvtfdisf2_mult */
    case 930:  /* *aarch64_ucvtfdisf2_mult */
    case 931:  /* *aarch64_scvtfsidf2_mult */
    case 932:  /* *aarch64_ucvtfsidf2_mult */
    case 933:  /* floatsisf2 */
    case 934:  /* floatunssisf2 */
    case 935:  /* floatdidf2 */
    case 936:  /* floatunsdidf2 */
    case 937:  /* floatdisf2 */
    case 938:  /* floatunsdisf2 */
    case 939:  /* floatsidf2 */
    case 940:  /* floatunssidf2 */
    case 941:  /* aarch64_fp16_floatsihf2 */
    case 942:  /* aarch64_fp16_floatunssihf2 */
    case 943:  /* aarch64_fp16_floatdihf2 */
    case 944:  /* aarch64_fp16_floatunsdihf2 */
    case 945:  /* fcvtzssf3 */
    case 946:  /* fcvtzusf3 */
    case 947:  /* fcvtzsdf3 */
    case 948:  /* fcvtzudf3 */
    case 949:  /* scvtfsi3 */
    case 950:  /* ucvtfsi3 */
    case 951:  /* scvtfdi3 */
    case 952:  /* ucvtfdi3 */
    case 953:  /* fcvtzshfsi3 */
    case 954:  /* fcvtzuhfsi3 */
    case 955:  /* fcvtzshfdi3 */
    case 956:  /* fcvtzuhfdi3 */
    case 957:  /* scvtfsihf3 */
    case 958:  /* ucvtfsihf3 */
    case 959:  /* scvtfdihf3 */
    case 960:  /* ucvtfdihf3 */
    case 961:  /* fcvtzshf3 */
    case 962:  /* fcvtzuhf3 */
    case 963:  /* scvtfhi3 */
    case 964:  /* ucvtfhi3 */
    case 965:  /* addhf3 */
    case 966:  /* addsf3 */
    case 967:  /* adddf3 */
    case 968:  /* subhf3 */
    case 969:  /* subsf3 */
    case 970:  /* subdf3 */
    case 971:  /* mulhf3 */
    case 972:  /* mulsf3 */
    case 973:  /* muldf3 */
    case 974:  /* *fnmulsf3 */
    case 975:  /* *fnmuldf3 */
    case 976:  /* *fnmulsf3 */
    case 977:  /* *fnmuldf3 */
    case 978:  /* *divhf3 */
    case 979:  /* *divsf3 */
    case 980:  /* *divdf3 */
    case 981:  /* neghf2 */
    case 982:  /* negsf2 */
    case 983:  /* negdf2 */
    case 984:  /* *sqrthf2 */
    case 985:  /* *sqrtsf2 */
    case 986:  /* *sqrtdf2 */
    case 987:  /* abshf2 */
    case 988:  /* abssf2 */
    case 989:  /* absdf2 */
    case 990:  /* smaxsf3 */
    case 991:  /* smaxdf3 */
    case 992:  /* sminsf3 */
    case 993:  /* smindf3 */
    case 994:  /* smax_nanhf3 */
    case 995:  /* smin_nanhf3 */
    case 996:  /* fmaxhf3 */
    case 997:  /* fminhf3 */
    case 998:  /* smax_nansf3 */
    case 999:  /* smin_nansf3 */
    case 1000:  /* fmaxsf3 */
    case 1001:  /* fminsf3 */
    case 1002:  /* smax_nandf3 */
    case 1003:  /* smin_nandf3 */
    case 1004:  /* fmaxdf3 */
    case 1005:  /* fmindf3 */
    case 1006:  /* copysignsf3_insn */
    case 1007:  /* copysigndf3_insn */
    case 1008:  /* aarch64_movdi_tilow */
    case 1009:  /* aarch64_movdi_tflow */
    case 1010:  /* aarch64_movdi_tihigh */
    case 1011:  /* aarch64_movdi_tfhigh */
    case 1012:  /* aarch64_movtihigh_di */
    case 1013:  /* aarch64_movtfhigh_di */
    case 1014:  /* aarch64_movtilow_di */
    case 1015:  /* aarch64_movtflow_di */
    case 1016:  /* aarch64_movtilow_tilow */
    case 1017:  /* add_losym_si */
    case 1018:  /* add_losym_di */
    case 1019:  /* ldr_got_small_si */
    case 1020:  /* ldr_got_small_di */
    case 1021:  /* ldr_got_small_sidi */
    case 1022:  /* ldr_got_small_28k_si */
    case 1023:  /* ldr_got_small_28k_di */
    case 1024:  /* ldr_got_small_28k_sidi */
    case 1025:  /* ldr_got_tiny_si */
    case 1026:  /* ldr_got_tiny_di */
    case 1027:  /* ldr_got_tiny_sidi */
    case 1028:  /* aarch64_load_tp_hard */
    case 1029:  /* *tlsgd_small_si */
    case 1030:  /* *tlsgd_small_di */
    case 1031:  /* tlsie_small_si */
    case 1032:  /* tlsie_small_di */
    case 1033:  /* tlsie_small_sidi */
    case 1034:  /* tlsie_tiny_si */
    case 1035:  /* tlsie_tiny_di */
    case 1036:  /* tlsie_tiny_sidi */
    case 1037:  /* tlsle12_si */
    case 1038:  /* tlsle12_di */
    case 1039:  /* tlsle24_si */
    case 1040:  /* tlsle24_di */
    case 1041:  /* tlsle32_si */
    case 1042:  /* tlsle32_di */
    case 1043:  /* tlsle48_si */
    case 1044:  /* tlsle48_di */
    case 1045:  /* tlsdesc_small_advsimd_si */
    case 1046:  /* tlsdesc_small_advsimd_di */
    case 1047:  /* tlsdesc_small_sve_si */
    case 1048:  /* tlsdesc_small_sve_di */
    case 1050:  /* aarch64_fjcvtzs */
    case 1060:  /* blockage */
    case 1064:  /* reg_stack_protect_address_si */
    case 1065:  /* reg_stack_protect_address_di */
    case 1066:  /* stack_protect_set_si */
    case 1067:  /* stack_protect_set_di */
    case 1068:  /* stack_protect_test_si */
    case 1069:  /* stack_protect_test_di */
    case 1070:  /* aarch64_set_fpsrsi */
    case 1071:  /* aarch64_set_fpcrsi */
    case 1072:  /* aarch64_set_fpsrdi */
    case 1073:  /* aarch64_set_fpcrdi */
    case 1074:  /* aarch64_get_fpsrsi */
    case 1075:  /* aarch64_get_fpcrsi */
    case 1076:  /* aarch64_get_fpsrdi */
    case 1077:  /* aarch64_get_fpcrdi */
    case 1078:  /* speculation_tracker */
    case 1079:  /* speculation_tracker_rev */
    case 1084:  /* speculation_barrier */
    case 1085:  /* *despeculate_copyqi_insn */
    case 1086:  /* *despeculate_copyhi_insn */
    case 1087:  /* *despeculate_copysi_insn */
    case 1088:  /* *despeculate_copydi_insn */
    case 1089:  /* *despeculate_copyti_insn */
    case 1090:  /* despeculate_simpleqi */
    case 1091:  /* despeculate_simplehi */
    case 1092:  /* despeculate_simplesi */
    case 1093:  /* despeculate_simpledi */
    case 1094:  /* despeculate_simpleti */
    case 1095:  /* aarch64_frint32zv2sf */
    case 1096:  /* aarch64_frint32xv2sf */
    case 1097:  /* aarch64_frint64zv2sf */
    case 1098:  /* aarch64_frint64xv2sf */
    case 1099:  /* aarch64_frint32zv4sf */
    case 1100:  /* aarch64_frint32xv4sf */
    case 1101:  /* aarch64_frint64zv4sf */
    case 1102:  /* aarch64_frint64xv4sf */
    case 1103:  /* aarch64_frint32zv2df */
    case 1104:  /* aarch64_frint32xv2df */
    case 1105:  /* aarch64_frint64zv2df */
    case 1106:  /* aarch64_frint64xv2df */
    case 1107:  /* aarch64_frint32zdf */
    case 1108:  /* aarch64_frint32xdf */
    case 1109:  /* aarch64_frint64zdf */
    case 1110:  /* aarch64_frint64xdf */
    case 1111:  /* aarch64_frint32zsf */
    case 1112:  /* aarch64_frint32xsf */
    case 1113:  /* aarch64_frint64zsf */
    case 1114:  /* aarch64_frint64xsf */
    case 1119:  /* aarch64_rndr */
    case 1120:  /* aarch64_rndrrs */
    case 1128:  /* aarch64_simd_dupv8qi */
    case 1129:  /* aarch64_simd_dupv16qi */
    case 1130:  /* aarch64_simd_dupv4hi */
    case 1131:  /* aarch64_simd_dupv8hi */
    case 1132:  /* aarch64_simd_dupv2si */
    case 1133:  /* aarch64_simd_dupv4si */
    case 1134:  /* aarch64_simd_dupv2di */
    case 1135:  /* aarch64_simd_dupv4hf */
    case 1136:  /* aarch64_simd_dupv8hf */
    case 1137:  /* aarch64_simd_dupv2sf */
    case 1138:  /* aarch64_simd_dupv4sf */
    case 1139:  /* aarch64_simd_dupv2df */
    case 1140:  /* aarch64_simd_dupv4bf */
    case 1141:  /* aarch64_simd_dupv8bf */
    case 1142:  /* aarch64_dup_lanev8qi */
    case 1143:  /* aarch64_dup_lanev16qi */
    case 1144:  /* aarch64_dup_lanev4hi */
    case 1145:  /* aarch64_dup_lanev8hi */
    case 1146:  /* aarch64_dup_lanev2si */
    case 1147:  /* aarch64_dup_lanev4si */
    case 1148:  /* aarch64_dup_lanev2di */
    case 1149:  /* aarch64_dup_lanev4hf */
    case 1150:  /* aarch64_dup_lanev8hf */
    case 1151:  /* aarch64_dup_lanev4bf */
    case 1152:  /* aarch64_dup_lanev8bf */
    case 1153:  /* aarch64_dup_lanev2sf */
    case 1154:  /* aarch64_dup_lanev4sf */
    case 1155:  /* aarch64_dup_lanev2df */
    case 1156:  /* aarch64_dup_lane_to_128v8qi */
    case 1157:  /* aarch64_dup_lane_to_64v16qi */
    case 1158:  /* aarch64_dup_lane_to_128v4hi */
    case 1159:  /* aarch64_dup_lane_to_64v8hi */
    case 1160:  /* aarch64_dup_lane_to_128v2si */
    case 1161:  /* aarch64_dup_lane_to_64v4si */
    case 1162:  /* aarch64_dup_lane_to_128v4hf */
    case 1163:  /* aarch64_dup_lane_to_64v8hf */
    case 1164:  /* aarch64_dup_lane_to_128v2sf */
    case 1165:  /* aarch64_dup_lane_to_64v4sf */
    case 1166:  /* *aarch64_simd_movv8qi */
    case 1167:  /* *aarch64_simd_movv4hi */
    case 1168:  /* *aarch64_simd_movv4hf */
    case 1169:  /* *aarch64_simd_movv4bf */
    case 1170:  /* *aarch64_simd_movv2si */
    case 1171:  /* *aarch64_simd_movv2sf */
    case 1172:  /* *aarch64_simd_movv16qi */
    case 1173:  /* *aarch64_simd_movv8hi */
    case 1174:  /* *aarch64_simd_movv4si */
    case 1175:  /* *aarch64_simd_movv2di */
    case 1176:  /* *aarch64_simd_movv8hf */
    case 1177:  /* *aarch64_simd_movv8bf */
    case 1178:  /* *aarch64_simd_movv4sf */
    case 1179:  /* *aarch64_simd_movv2df */
    case 1180:  /* aarch64_store_lane0v8qi */
    case 1181:  /* aarch64_store_lane0v16qi */
    case 1182:  /* aarch64_store_lane0v4hi */
    case 1183:  /* aarch64_store_lane0v8hi */
    case 1184:  /* aarch64_store_lane0v2si */
    case 1185:  /* aarch64_store_lane0v4si */
    case 1186:  /* aarch64_store_lane0v2di */
    case 1187:  /* aarch64_store_lane0v4hf */
    case 1188:  /* aarch64_store_lane0v8hf */
    case 1189:  /* aarch64_store_lane0v4bf */
    case 1190:  /* aarch64_store_lane0v8bf */
    case 1191:  /* aarch64_store_lane0v2sf */
    case 1192:  /* aarch64_store_lane0v4sf */
    case 1193:  /* aarch64_store_lane0v2df */
    case 1194:  /* load_pairv8qiv8qi */
    case 1195:  /* load_pairv4hiv8qi */
    case 1196:  /* load_pairv4hfv8qi */
    case 1197:  /* load_pairv2siv8qi */
    case 1198:  /* load_pairv2sfv8qi */
    case 1199:  /* load_pairdfv8qi */
    case 1200:  /* load_pairv8qiv4hi */
    case 1201:  /* load_pairv4hiv4hi */
    case 1202:  /* load_pairv4hfv4hi */
    case 1203:  /* load_pairv2siv4hi */
    case 1204:  /* load_pairv2sfv4hi */
    case 1205:  /* load_pairdfv4hi */
    case 1206:  /* load_pairv8qiv4hf */
    case 1207:  /* load_pairv4hiv4hf */
    case 1208:  /* load_pairv4hfv4hf */
    case 1209:  /* load_pairv2siv4hf */
    case 1210:  /* load_pairv2sfv4hf */
    case 1211:  /* load_pairdfv4hf */
    case 1212:  /* load_pairv8qiv2si */
    case 1213:  /* load_pairv4hiv2si */
    case 1214:  /* load_pairv4hfv2si */
    case 1215:  /* load_pairv2siv2si */
    case 1216:  /* load_pairv2sfv2si */
    case 1217:  /* load_pairdfv2si */
    case 1218:  /* load_pairv8qiv2sf */
    case 1219:  /* load_pairv4hiv2sf */
    case 1220:  /* load_pairv4hfv2sf */
    case 1221:  /* load_pairv2siv2sf */
    case 1222:  /* load_pairv2sfv2sf */
    case 1223:  /* load_pairdfv2sf */
    case 1224:  /* load_pairv8qidf */
    case 1225:  /* load_pairv4hidf */
    case 1226:  /* load_pairv4hfdf */
    case 1227:  /* load_pairv2sidf */
    case 1228:  /* load_pairv2sfdf */
    case 1229:  /* load_pairdfdf */
    case 1230:  /* vec_store_pairv8qiv8qi */
    case 1231:  /* vec_store_pairv4hiv8qi */
    case 1232:  /* vec_store_pairv4hfv8qi */
    case 1233:  /* vec_store_pairv2siv8qi */
    case 1234:  /* vec_store_pairv2sfv8qi */
    case 1235:  /* vec_store_pairdfv8qi */
    case 1236:  /* vec_store_pairv8qiv4hi */
    case 1237:  /* vec_store_pairv4hiv4hi */
    case 1238:  /* vec_store_pairv4hfv4hi */
    case 1239:  /* vec_store_pairv2siv4hi */
    case 1240:  /* vec_store_pairv2sfv4hi */
    case 1241:  /* vec_store_pairdfv4hi */
    case 1242:  /* vec_store_pairv8qiv4hf */
    case 1243:  /* vec_store_pairv4hiv4hf */
    case 1244:  /* vec_store_pairv4hfv4hf */
    case 1245:  /* vec_store_pairv2siv4hf */
    case 1246:  /* vec_store_pairv2sfv4hf */
    case 1247:  /* vec_store_pairdfv4hf */
    case 1248:  /* vec_store_pairv8qiv2si */
    case 1249:  /* vec_store_pairv4hiv2si */
    case 1250:  /* vec_store_pairv4hfv2si */
    case 1251:  /* vec_store_pairv2siv2si */
    case 1252:  /* vec_store_pairv2sfv2si */
    case 1253:  /* vec_store_pairdfv2si */
    case 1254:  /* vec_store_pairv8qiv2sf */
    case 1255:  /* vec_store_pairv4hiv2sf */
    case 1256:  /* vec_store_pairv4hfv2sf */
    case 1257:  /* vec_store_pairv2siv2sf */
    case 1258:  /* vec_store_pairv2sfv2sf */
    case 1259:  /* vec_store_pairdfv2sf */
    case 1260:  /* vec_store_pairv8qidf */
    case 1261:  /* vec_store_pairv4hidf */
    case 1262:  /* vec_store_pairv4hfdf */
    case 1263:  /* vec_store_pairv2sidf */
    case 1264:  /* vec_store_pairv2sfdf */
    case 1265:  /* vec_store_pairdfdf */
    case 1266:  /* load_pairv16qiv16qi */
    case 1267:  /* load_pairv16qiv8hi */
    case 1268:  /* load_pairv16qiv4si */
    case 1269:  /* load_pairv16qiv2di */
    case 1270:  /* load_pairv16qiv8hf */
    case 1271:  /* load_pairv16qiv8bf */
    case 1272:  /* load_pairv16qiv4sf */
    case 1273:  /* load_pairv16qiv2df */
    case 1274:  /* load_pairv8hiv16qi */
    case 1275:  /* load_pairv8hiv8hi */
    case 1276:  /* load_pairv8hiv4si */
    case 1277:  /* load_pairv8hiv2di */
    case 1278:  /* load_pairv8hiv8hf */
    case 1279:  /* load_pairv8hiv8bf */
    case 1280:  /* load_pairv8hiv4sf */
    case 1281:  /* load_pairv8hiv2df */
    case 1282:  /* load_pairv4siv16qi */
    case 1283:  /* load_pairv4siv8hi */
    case 1284:  /* load_pairv4siv4si */
    case 1285:  /* load_pairv4siv2di */
    case 1286:  /* load_pairv4siv8hf */
    case 1287:  /* load_pairv4siv8bf */
    case 1288:  /* load_pairv4siv4sf */
    case 1289:  /* load_pairv4siv2df */
    case 1290:  /* load_pairv2div16qi */
    case 1291:  /* load_pairv2div8hi */
    case 1292:  /* load_pairv2div4si */
    case 1293:  /* load_pairv2div2di */
    case 1294:  /* load_pairv2div8hf */
    case 1295:  /* load_pairv2div8bf */
    case 1296:  /* load_pairv2div4sf */
    case 1297:  /* load_pairv2div2df */
    case 1298:  /* load_pairv8hfv16qi */
    case 1299:  /* load_pairv8hfv8hi */
    case 1300:  /* load_pairv8hfv4si */
    case 1301:  /* load_pairv8hfv2di */
    case 1302:  /* load_pairv8hfv8hf */
    case 1303:  /* load_pairv8hfv8bf */
    case 1304:  /* load_pairv8hfv4sf */
    case 1305:  /* load_pairv8hfv2df */
    case 1306:  /* load_pairv4sfv16qi */
    case 1307:  /* load_pairv4sfv8hi */
    case 1308:  /* load_pairv4sfv4si */
    case 1309:  /* load_pairv4sfv2di */
    case 1310:  /* load_pairv4sfv8hf */
    case 1311:  /* load_pairv4sfv8bf */
    case 1312:  /* load_pairv4sfv4sf */
    case 1313:  /* load_pairv4sfv2df */
    case 1314:  /* load_pairv2dfv16qi */
    case 1315:  /* load_pairv2dfv8hi */
    case 1316:  /* load_pairv2dfv4si */
    case 1317:  /* load_pairv2dfv2di */
    case 1318:  /* load_pairv2dfv8hf */
    case 1319:  /* load_pairv2dfv8bf */
    case 1320:  /* load_pairv2dfv4sf */
    case 1321:  /* load_pairv2dfv2df */
    case 1322:  /* load_pairv8bfv16qi */
    case 1323:  /* load_pairv8bfv8hi */
    case 1324:  /* load_pairv8bfv4si */
    case 1325:  /* load_pairv8bfv2di */
    case 1326:  /* load_pairv8bfv8hf */
    case 1327:  /* load_pairv8bfv8bf */
    case 1328:  /* load_pairv8bfv4sf */
    case 1329:  /* load_pairv8bfv2df */
    case 1330:  /* vec_store_pairv16qiv16qi */
    case 1331:  /* vec_store_pairv16qiv8hi */
    case 1332:  /* vec_store_pairv16qiv4si */
    case 1333:  /* vec_store_pairv16qiv2di */
    case 1334:  /* vec_store_pairv16qiv8hf */
    case 1335:  /* vec_store_pairv16qiv8bf */
    case 1336:  /* vec_store_pairv16qiv4sf */
    case 1337:  /* vec_store_pairv16qiv2df */
    case 1338:  /* vec_store_pairv8hiv16qi */
    case 1339:  /* vec_store_pairv8hiv8hi */
    case 1340:  /* vec_store_pairv8hiv4si */
    case 1341:  /* vec_store_pairv8hiv2di */
    case 1342:  /* vec_store_pairv8hiv8hf */
    case 1343:  /* vec_store_pairv8hiv8bf */
    case 1344:  /* vec_store_pairv8hiv4sf */
    case 1345:  /* vec_store_pairv8hiv2df */
    case 1346:  /* vec_store_pairv4siv16qi */
    case 1347:  /* vec_store_pairv4siv8hi */
    case 1348:  /* vec_store_pairv4siv4si */
    case 1349:  /* vec_store_pairv4siv2di */
    case 1350:  /* vec_store_pairv4siv8hf */
    case 1351:  /* vec_store_pairv4siv8bf */
    case 1352:  /* vec_store_pairv4siv4sf */
    case 1353:  /* vec_store_pairv4siv2df */
    case 1354:  /* vec_store_pairv2div16qi */
    case 1355:  /* vec_store_pairv2div8hi */
    case 1356:  /* vec_store_pairv2div4si */
    case 1357:  /* vec_store_pairv2div2di */
    case 1358:  /* vec_store_pairv2div8hf */
    case 1359:  /* vec_store_pairv2div8bf */
    case 1360:  /* vec_store_pairv2div4sf */
    case 1361:  /* vec_store_pairv2div2df */
    case 1362:  /* vec_store_pairv8hfv16qi */
    case 1363:  /* vec_store_pairv8hfv8hi */
    case 1364:  /* vec_store_pairv8hfv4si */
    case 1365:  /* vec_store_pairv8hfv2di */
    case 1366:  /* vec_store_pairv8hfv8hf */
    case 1367:  /* vec_store_pairv8hfv8bf */
    case 1368:  /* vec_store_pairv8hfv4sf */
    case 1369:  /* vec_store_pairv8hfv2df */
    case 1370:  /* vec_store_pairv4sfv16qi */
    case 1371:  /* vec_store_pairv4sfv8hi */
    case 1372:  /* vec_store_pairv4sfv4si */
    case 1373:  /* vec_store_pairv4sfv2di */
    case 1374:  /* vec_store_pairv4sfv8hf */
    case 1375:  /* vec_store_pairv4sfv8bf */
    case 1376:  /* vec_store_pairv4sfv4sf */
    case 1377:  /* vec_store_pairv4sfv2df */
    case 1378:  /* vec_store_pairv2dfv16qi */
    case 1379:  /* vec_store_pairv2dfv8hi */
    case 1380:  /* vec_store_pairv2dfv4si */
    case 1381:  /* vec_store_pairv2dfv2di */
    case 1382:  /* vec_store_pairv2dfv8hf */
    case 1383:  /* vec_store_pairv2dfv8bf */
    case 1384:  /* vec_store_pairv2dfv4sf */
    case 1385:  /* vec_store_pairv2dfv2df */
    case 1386:  /* vec_store_pairv8bfv16qi */
    case 1387:  /* vec_store_pairv8bfv8hi */
    case 1388:  /* vec_store_pairv8bfv4si */
    case 1389:  /* vec_store_pairv8bfv2di */
    case 1390:  /* vec_store_pairv8bfv8hf */
    case 1391:  /* vec_store_pairv8bfv8bf */
    case 1392:  /* vec_store_pairv8bfv4sf */
    case 1393:  /* vec_store_pairv8bfv2df */
    case 1394:  /* aarch64_simd_mov_from_v16qilow */
    case 1395:  /* aarch64_simd_mov_from_v8hilow */
    case 1396:  /* aarch64_simd_mov_from_v4silow */
    case 1397:  /* aarch64_simd_mov_from_v8hflow */
    case 1398:  /* aarch64_simd_mov_from_v8bflow */
    case 1399:  /* aarch64_simd_mov_from_v4sflow */
    case 1400:  /* aarch64_simd_mov_from_v16qihigh */
    case 1401:  /* aarch64_simd_mov_from_v8hihigh */
    case 1402:  /* aarch64_simd_mov_from_v4sihigh */
    case 1403:  /* aarch64_simd_mov_from_v8hfhigh */
    case 1404:  /* aarch64_simd_mov_from_v8bfhigh */
    case 1405:  /* aarch64_simd_mov_from_v4sfhigh */
    case 1406:  /* ornv8qi3 */
    case 1407:  /* ornv16qi3 */
    case 1408:  /* ornv4hi3 */
    case 1409:  /* ornv8hi3 */
    case 1410:  /* ornv2si3 */
    case 1411:  /* ornv4si3 */
    case 1412:  /* ornv2di3 */
    case 1413:  /* bicv8qi3 */
    case 1414:  /* bicv16qi3 */
    case 1415:  /* bicv4hi3 */
    case 1416:  /* bicv8hi3 */
    case 1417:  /* bicv2si3 */
    case 1418:  /* bicv4si3 */
    case 1419:  /* bicv2di3 */
    case 1420:  /* addv8qi3 */
    case 1421:  /* addv16qi3 */
    case 1422:  /* addv4hi3 */
    case 1423:  /* addv8hi3 */
    case 1424:  /* addv2si3 */
    case 1425:  /* addv4si3 */
    case 1426:  /* addv2di3 */
    case 1427:  /* subv8qi3 */
    case 1428:  /* subv16qi3 */
    case 1429:  /* subv4hi3 */
    case 1430:  /* subv8hi3 */
    case 1431:  /* subv2si3 */
    case 1432:  /* subv4si3 */
    case 1433:  /* subv2di3 */
    case 1434:  /* mulv8qi3 */
    case 1435:  /* mulv16qi3 */
    case 1436:  /* mulv4hi3 */
    case 1437:  /* mulv8hi3 */
    case 1438:  /* mulv2si3 */
    case 1439:  /* mulv4si3 */
    case 1440:  /* bswapv4hi2 */
    case 1441:  /* bswapv8hi2 */
    case 1442:  /* bswapv2si2 */
    case 1443:  /* bswapv4si2 */
    case 1444:  /* bswapv2di2 */
    case 1445:  /* aarch64_rbitv8qi */
    case 1446:  /* aarch64_rbitv16qi */
    case 1531:  /* *aarch64_mul3_eltv4hi */
    case 1532:  /* *aarch64_mul3_eltv8hi */
    case 1533:  /* *aarch64_mul3_eltv2si */
    case 1534:  /* *aarch64_mul3_eltv4si */
    case 1535:  /* *aarch64_mul3_eltv4hf */
    case 1536:  /* *aarch64_mul3_eltv8hf */
    case 1537:  /* *aarch64_mul3_eltv2sf */
    case 1538:  /* *aarch64_mul3_eltv4sf */
    case 1539:  /* *aarch64_mul3_eltv2df */
    case 1540:  /* *aarch64_mul3_elt_to_128v4hi */
    case 1541:  /* *aarch64_mul3_elt_to_64v8hi */
    case 1542:  /* *aarch64_mul3_elt_to_128v2si */
    case 1543:  /* *aarch64_mul3_elt_to_64v4si */
    case 1544:  /* *aarch64_mul3_elt_to_128v2sf */
    case 1545:  /* *aarch64_mul3_elt_to_64v4sf */
    case 1546:  /* *aarch64_mul3_elt_from_dupv4hi */
    case 1547:  /* *aarch64_mul3_elt_from_dupv8hi */
    case 1548:  /* *aarch64_mul3_elt_from_dupv2si */
    case 1549:  /* *aarch64_mul3_elt_from_dupv4si */
    case 1550:  /* *aarch64_mul3_elt_from_dupv4hf */
    case 1551:  /* *aarch64_mul3_elt_from_dupv8hf */
    case 1552:  /* *aarch64_mul3_elt_from_dupv2sf */
    case 1553:  /* *aarch64_mul3_elt_from_dupv4sf */
    case 1554:  /* *aarch64_mul3_elt_from_dupv2df */
    case 1555:  /* aarch64_rsqrtev4hf */
    case 1556:  /* aarch64_rsqrtev8hf */
    case 1557:  /* aarch64_rsqrtev2sf */
    case 1558:  /* aarch64_rsqrtev4sf */
    case 1559:  /* aarch64_rsqrtev2df */
    case 1560:  /* aarch64_rsqrtehf */
    case 1561:  /* aarch64_rsqrtesf */
    case 1562:  /* aarch64_rsqrtedf */
    case 1563:  /* aarch64_rsqrtsv4hf */
    case 1564:  /* aarch64_rsqrtsv8hf */
    case 1565:  /* aarch64_rsqrtsv2sf */
    case 1566:  /* aarch64_rsqrtsv4sf */
    case 1567:  /* aarch64_rsqrtsv2df */
    case 1568:  /* aarch64_rsqrtshf */
    case 1569:  /* aarch64_rsqrtssf */
    case 1570:  /* aarch64_rsqrtsdf */
    case 1571:  /* aarch64_ursqrtev2si */
    case 1572:  /* aarch64_ursqrtev4si */
    case 1573:  /* *aarch64_mul3_elt_to_64v2df */
    case 1574:  /* negv8qi2 */
    case 1575:  /* negv16qi2 */
    case 1576:  /* negv4hi2 */
    case 1577:  /* negv8hi2 */
    case 1578:  /* negv2si2 */
    case 1579:  /* negv4si2 */
    case 1580:  /* negv2di2 */
    case 1581:  /* absv8qi2 */
    case 1582:  /* absv16qi2 */
    case 1583:  /* absv4hi2 */
    case 1584:  /* absv8hi2 */
    case 1585:  /* absv2si2 */
    case 1586:  /* absv4si2 */
    case 1587:  /* absv2di2 */
    case 1588:  /* aarch64_absv8qi */
    case 1589:  /* aarch64_absv16qi */
    case 1590:  /* aarch64_absv4hi */
    case 1591:  /* aarch64_absv8hi */
    case 1592:  /* aarch64_absv2si */
    case 1593:  /* aarch64_absv4si */
    case 1594:  /* aarch64_absv2di */
    case 1595:  /* aarch64_absdi */
    case 1596:  /* aarch64_sabdv8qi */
    case 1597:  /* aarch64_uabdv8qi */
    case 1598:  /* aarch64_sabdv16qi */
    case 1599:  /* aarch64_uabdv16qi */
    case 1600:  /* aarch64_sabdv4hi */
    case 1601:  /* aarch64_uabdv4hi */
    case 1602:  /* aarch64_sabdv8hi */
    case 1603:  /* aarch64_uabdv8hi */
    case 1604:  /* aarch64_sabdv2si */
    case 1605:  /* aarch64_uabdv2si */
    case 1606:  /* aarch64_sabdv4si */
    case 1607:  /* aarch64_uabdv4si */
    case 1608:  /* aarch64_sabdlv8qi */
    case 1609:  /* aarch64_uabdlv8qi */
    case 1610:  /* aarch64_sabdlv4hi */
    case 1611:  /* aarch64_uabdlv4hi */
    case 1612:  /* aarch64_sabdlv2si */
    case 1613:  /* aarch64_uabdlv2si */
    case 1614:  /* aarch64_sabdl2v16qi */
    case 1615:  /* aarch64_uabdl2v16qi */
    case 1616:  /* aarch64_sabdl2v8hi */
    case 1617:  /* aarch64_uabdl2v8hi */
    case 1618:  /* aarch64_sabdl2v4si */
    case 1619:  /* aarch64_uabdl2v4si */
    case 1620:  /* aarch64_sabalv8qi */
    case 1621:  /* aarch64_uabalv8qi */
    case 1622:  /* aarch64_sabalv4hi */
    case 1623:  /* aarch64_uabalv4hi */
    case 1624:  /* aarch64_sabalv2si */
    case 1625:  /* aarch64_uabalv2si */
    case 1626:  /* aarch64_sabal2v16qi */
    case 1627:  /* aarch64_uabal2v16qi */
    case 1628:  /* aarch64_sabal2v8hi */
    case 1629:  /* aarch64_uabal2v8hi */
    case 1630:  /* aarch64_sabal2v4si */
    case 1631:  /* aarch64_uabal2v4si */
    case 1632:  /* aarch64_sadalpv8qi */
    case 1633:  /* aarch64_uadalpv8qi */
    case 1634:  /* aarch64_sadalpv16qi */
    case 1635:  /* aarch64_uadalpv16qi */
    case 1636:  /* aarch64_sadalpv4hi */
    case 1637:  /* aarch64_uadalpv4hi */
    case 1638:  /* aarch64_sadalpv8hi */
    case 1639:  /* aarch64_uadalpv8hi */
    case 1640:  /* aarch64_sadalpv4si */
    case 1641:  /* aarch64_uadalpv4si */
    case 1642:  /* aarch64_sabav8qi */
    case 1643:  /* aarch64_uabav8qi */
    case 1644:  /* aarch64_sabav16qi */
    case 1645:  /* aarch64_uabav16qi */
    case 1646:  /* aarch64_sabav4hi */
    case 1647:  /* aarch64_uabav4hi */
    case 1648:  /* aarch64_sabav8hi */
    case 1649:  /* aarch64_uabav8hi */
    case 1650:  /* aarch64_sabav2si */
    case 1651:  /* aarch64_uabav2si */
    case 1652:  /* aarch64_sabav4si */
    case 1653:  /* aarch64_uabav4si */
    case 1654:  /* fabdv4hf3 */
    case 1655:  /* fabdv8hf3 */
    case 1656:  /* fabdv2sf3 */
    case 1657:  /* fabdv4sf3 */
    case 1658:  /* fabdv2df3 */
    case 1659:  /* fabdhf3 */
    case 1660:  /* fabdsf3 */
    case 1661:  /* fabddf3 */
    case 1662:  /* andv8qi3 */
    case 1663:  /* andv16qi3 */
    case 1664:  /* andv4hi3 */
    case 1665:  /* andv8hi3 */
    case 1666:  /* andv2si3 */
    case 1667:  /* andv4si3 */
    case 1668:  /* andv2di3 */
    case 1669:  /* iorv8qi3 */
    case 1670:  /* iorv16qi3 */
    case 1671:  /* iorv4hi3 */
    case 1672:  /* iorv8hi3 */
    case 1673:  /* iorv2si3 */
    case 1674:  /* iorv4si3 */
    case 1675:  /* iorv2di3 */
    case 1676:  /* xorv8qi3 */
    case 1677:  /* xorv16qi3 */
    case 1678:  /* xorv4hi3 */
    case 1679:  /* xorv8hi3 */
    case 1680:  /* xorv2si3 */
    case 1681:  /* xorv4si3 */
    case 1682:  /* xorv2di3 */
    case 1683:  /* one_cmplv8qi2 */
    case 1684:  /* one_cmplv16qi2 */
    case 1685:  /* one_cmplv4hi2 */
    case 1686:  /* one_cmplv8hi2 */
    case 1687:  /* one_cmplv2si2 */
    case 1688:  /* one_cmplv4si2 */
    case 1689:  /* one_cmplv2di2 */
    case 1690:  /* aarch64_simd_vec_setv8qi */
    case 1691:  /* aarch64_simd_vec_setv16qi */
    case 1692:  /* aarch64_simd_vec_setv4hi */
    case 1693:  /* aarch64_simd_vec_setv8hi */
    case 1694:  /* aarch64_simd_vec_setv2si */
    case 1695:  /* aarch64_simd_vec_setv4si */
    case 1696:  /* aarch64_simd_vec_setv2di */
    case 1697:  /* aarch64_simd_vec_setv4hf */
    case 1698:  /* aarch64_simd_vec_setv8hf */
    case 1699:  /* aarch64_simd_vec_setv4bf */
    case 1700:  /* aarch64_simd_vec_setv8bf */
    case 1701:  /* aarch64_simd_vec_setv2sf */
    case 1702:  /* aarch64_simd_vec_setv4sf */
    case 1703:  /* aarch64_simd_vec_setv2df */
    case 1704:  /* aarch64_simd_vec_copy_lanev8qi */
    case 1705:  /* aarch64_simd_vec_copy_lanev16qi */
    case 1706:  /* aarch64_simd_vec_copy_lanev4hi */
    case 1707:  /* aarch64_simd_vec_copy_lanev8hi */
    case 1708:  /* aarch64_simd_vec_copy_lanev2si */
    case 1709:  /* aarch64_simd_vec_copy_lanev4si */
    case 1710:  /* aarch64_simd_vec_copy_lanev2di */
    case 1711:  /* aarch64_simd_vec_copy_lanev4hf */
    case 1712:  /* aarch64_simd_vec_copy_lanev8hf */
    case 1713:  /* aarch64_simd_vec_copy_lanev4bf */
    case 1714:  /* aarch64_simd_vec_copy_lanev8bf */
    case 1715:  /* aarch64_simd_vec_copy_lanev2sf */
    case 1716:  /* aarch64_simd_vec_copy_lanev4sf */
    case 1717:  /* aarch64_simd_vec_copy_lanev2df */
    case 1718:  /* *aarch64_simd_vec_copy_lane_to_128v8qi */
    case 1719:  /* *aarch64_simd_vec_copy_lane_to_64v16qi */
    case 1720:  /* *aarch64_simd_vec_copy_lane_to_128v4hi */
    case 1721:  /* *aarch64_simd_vec_copy_lane_to_64v8hi */
    case 1722:  /* *aarch64_simd_vec_copy_lane_to_128v2si */
    case 1723:  /* *aarch64_simd_vec_copy_lane_to_64v4si */
    case 1724:  /* *aarch64_simd_vec_copy_lane_to_128v4hf */
    case 1725:  /* *aarch64_simd_vec_copy_lane_to_64v8hf */
    case 1726:  /* *aarch64_simd_vec_copy_lane_to_128v2sf */
    case 1727:  /* *aarch64_simd_vec_copy_lane_to_64v4sf */
    case 1728:  /* aarch64_simd_lshrv8qi */
    case 1729:  /* aarch64_simd_lshrv16qi */
    case 1730:  /* aarch64_simd_lshrv4hi */
    case 1731:  /* aarch64_simd_lshrv8hi */
    case 1732:  /* aarch64_simd_lshrv2si */
    case 1733:  /* aarch64_simd_lshrv4si */
    case 1734:  /* aarch64_simd_lshrv2di */
    case 1735:  /* aarch64_simd_ashrv8qi */
    case 1736:  /* aarch64_simd_ashrv16qi */
    case 1737:  /* aarch64_simd_ashrv4hi */
    case 1738:  /* aarch64_simd_ashrv8hi */
    case 1739:  /* aarch64_simd_ashrv2si */
    case 1740:  /* aarch64_simd_ashrv4si */
    case 1741:  /* aarch64_simd_ashrv2di */
    case 1742:  /* *aarch64_simd_srav8qi */
    case 1743:  /* *aarch64_simd_srav8qi */
    case 1744:  /* *aarch64_simd_srav16qi */
    case 1745:  /* *aarch64_simd_srav16qi */
    case 1746:  /* *aarch64_simd_srav4hi */
    case 1747:  /* *aarch64_simd_srav4hi */
    case 1748:  /* *aarch64_simd_srav8hi */
    case 1749:  /* *aarch64_simd_srav8hi */
    case 1750:  /* *aarch64_simd_srav2si */
    case 1751:  /* *aarch64_simd_srav2si */
    case 1752:  /* *aarch64_simd_srav4si */
    case 1753:  /* *aarch64_simd_srav4si */
    case 1754:  /* *aarch64_simd_srav2di */
    case 1755:  /* *aarch64_simd_srav2di */
    case 1756:  /* aarch64_simd_imm_shlv8qi */
    case 1757:  /* aarch64_simd_imm_shlv16qi */
    case 1758:  /* aarch64_simd_imm_shlv4hi */
    case 1759:  /* aarch64_simd_imm_shlv8hi */
    case 1760:  /* aarch64_simd_imm_shlv2si */
    case 1761:  /* aarch64_simd_imm_shlv4si */
    case 1762:  /* aarch64_simd_imm_shlv2di */
    case 1763:  /* aarch64_simd_reg_sshlv8qi */
    case 1764:  /* aarch64_simd_reg_sshlv16qi */
    case 1765:  /* aarch64_simd_reg_sshlv4hi */
    case 1766:  /* aarch64_simd_reg_sshlv8hi */
    case 1767:  /* aarch64_simd_reg_sshlv2si */
    case 1768:  /* aarch64_simd_reg_sshlv4si */
    case 1769:  /* aarch64_simd_reg_sshlv2di */
    case 1770:  /* aarch64_simd_reg_shlv8qi_unsigned */
    case 1771:  /* aarch64_simd_reg_shlv16qi_unsigned */
    case 1772:  /* aarch64_simd_reg_shlv4hi_unsigned */
    case 1773:  /* aarch64_simd_reg_shlv8hi_unsigned */
    case 1774:  /* aarch64_simd_reg_shlv2si_unsigned */
    case 1775:  /* aarch64_simd_reg_shlv4si_unsigned */
    case 1776:  /* aarch64_simd_reg_shlv2di_unsigned */
    case 1777:  /* aarch64_simd_reg_shlv8qi_signed */
    case 1778:  /* aarch64_simd_reg_shlv16qi_signed */
    case 1779:  /* aarch64_simd_reg_shlv4hi_signed */
    case 1780:  /* aarch64_simd_reg_shlv8hi_signed */
    case 1781:  /* aarch64_simd_reg_shlv2si_signed */
    case 1782:  /* aarch64_simd_reg_shlv4si_signed */
    case 1783:  /* aarch64_simd_reg_shlv2di_signed */
    case 1784:  /* vec_shr_v8qi */
    case 1785:  /* vec_shr_v4hi */
    case 1786:  /* vec_shr_v4hf */
    case 1787:  /* vec_shr_v2si */
    case 1788:  /* vec_shr_v2sf */
    case 1789:  /* vec_shr_v4bf */
    case 1790:  /* aarch64_mlav8qi */
    case 1791:  /* aarch64_mlav16qi */
    case 1792:  /* aarch64_mlav4hi */
    case 1793:  /* aarch64_mlav8hi */
    case 1794:  /* aarch64_mlav2si */
    case 1795:  /* aarch64_mlav4si */
    case 1796:  /* *aarch64_mla_eltv4hi */
    case 1797:  /* *aarch64_mla_eltv8hi */
    case 1798:  /* *aarch64_mla_eltv2si */
    case 1799:  /* *aarch64_mla_eltv4si */
    case 1800:  /* *aarch64_mla_elt_to_128v4hi */
    case 1801:  /* *aarch64_mla_elt_to_64v8hi */
    case 1802:  /* *aarch64_mla_elt_to_128v2si */
    case 1803:  /* *aarch64_mla_elt_to_64v4si */
    case 1804:  /* aarch64_mla_nv4hi */
    case 1805:  /* aarch64_mla_nv8hi */
    case 1806:  /* aarch64_mla_nv2si */
    case 1807:  /* aarch64_mla_nv4si */
    case 1808:  /* aarch64_mlsv8qi */
    case 1809:  /* aarch64_mlsv16qi */
    case 1810:  /* aarch64_mlsv4hi */
    case 1811:  /* aarch64_mlsv8hi */
    case 1812:  /* aarch64_mlsv2si */
    case 1813:  /* aarch64_mlsv4si */
    case 1814:  /* *aarch64_mls_eltv4hi */
    case 1815:  /* *aarch64_mls_eltv8hi */
    case 1816:  /* *aarch64_mls_eltv2si */
    case 1817:  /* *aarch64_mls_eltv4si */
    case 1818:  /* *aarch64_mls_elt_to_128v4hi */
    case 1819:  /* *aarch64_mls_elt_to_64v8hi */
    case 1820:  /* *aarch64_mls_elt_to_128v2si */
    case 1821:  /* *aarch64_mls_elt_to_64v4si */
    case 1822:  /* aarch64_mls_nv4hi */
    case 1823:  /* aarch64_mls_nv8hi */
    case 1824:  /* aarch64_mls_nv2si */
    case 1825:  /* aarch64_mls_nv4si */
    case 1826:  /* smaxv8qi3 */
    case 1827:  /* sminv8qi3 */
    case 1828:  /* umaxv8qi3 */
    case 1829:  /* uminv8qi3 */
    case 1830:  /* smaxv16qi3 */
    case 1831:  /* sminv16qi3 */
    case 1832:  /* umaxv16qi3 */
    case 1833:  /* uminv16qi3 */
    case 1834:  /* smaxv4hi3 */
    case 1835:  /* sminv4hi3 */
    case 1836:  /* umaxv4hi3 */
    case 1837:  /* uminv4hi3 */
    case 1838:  /* smaxv8hi3 */
    case 1839:  /* sminv8hi3 */
    case 1840:  /* umaxv8hi3 */
    case 1841:  /* uminv8hi3 */
    case 1842:  /* smaxv2si3 */
    case 1843:  /* sminv2si3 */
    case 1844:  /* umaxv2si3 */
    case 1845:  /* uminv2si3 */
    case 1846:  /* smaxv4si3 */
    case 1847:  /* sminv4si3 */
    case 1848:  /* umaxv4si3 */
    case 1849:  /* uminv4si3 */
    case 1850:  /* aarch64_umaxpv8qi */
    case 1851:  /* aarch64_uminpv8qi */
    case 1852:  /* aarch64_smaxpv8qi */
    case 1853:  /* aarch64_sminpv8qi */
    case 1854:  /* aarch64_umaxpv16qi */
    case 1855:  /* aarch64_uminpv16qi */
    case 1856:  /* aarch64_smaxpv16qi */
    case 1857:  /* aarch64_sminpv16qi */
    case 1858:  /* aarch64_umaxpv4hi */
    case 1859:  /* aarch64_uminpv4hi */
    case 1860:  /* aarch64_smaxpv4hi */
    case 1861:  /* aarch64_sminpv4hi */
    case 1862:  /* aarch64_umaxpv8hi */
    case 1863:  /* aarch64_uminpv8hi */
    case 1864:  /* aarch64_smaxpv8hi */
    case 1865:  /* aarch64_sminpv8hi */
    case 1866:  /* aarch64_umaxpv2si */
    case 1867:  /* aarch64_uminpv2si */
    case 1868:  /* aarch64_smaxpv2si */
    case 1869:  /* aarch64_sminpv2si */
    case 1870:  /* aarch64_umaxpv4si */
    case 1871:  /* aarch64_uminpv4si */
    case 1872:  /* aarch64_smaxpv4si */
    case 1873:  /* aarch64_sminpv4si */
    case 1874:  /* aarch64_smax_nanpv4hf */
    case 1875:  /* aarch64_smin_nanpv4hf */
    case 1876:  /* aarch64_smaxpv4hf */
    case 1877:  /* aarch64_sminpv4hf */
    case 1878:  /* aarch64_smax_nanpv8hf */
    case 1879:  /* aarch64_smin_nanpv8hf */
    case 1880:  /* aarch64_smaxpv8hf */
    case 1881:  /* aarch64_sminpv8hf */
    case 1882:  /* aarch64_smax_nanpv2sf */
    case 1883:  /* aarch64_smin_nanpv2sf */
    case 1884:  /* aarch64_smaxpv2sf */
    case 1885:  /* aarch64_sminpv2sf */
    case 1886:  /* aarch64_smax_nanpv4sf */
    case 1887:  /* aarch64_smin_nanpv4sf */
    case 1888:  /* aarch64_smaxpv4sf */
    case 1889:  /* aarch64_sminpv4sf */
    case 1890:  /* aarch64_smax_nanpv2df */
    case 1891:  /* aarch64_smin_nanpv2df */
    case 1892:  /* aarch64_smaxpv2df */
    case 1893:  /* aarch64_sminpv2df */
    case 1894:  /* move_lo_quad_internal_v16qi */
    case 1895:  /* move_lo_quad_internal_v8hi */
    case 1896:  /* move_lo_quad_internal_v4si */
    case 1897:  /* move_lo_quad_internal_v2di */
    case 1898:  /* move_lo_quad_internal_v8hf */
    case 1899:  /* move_lo_quad_internal_v8bf */
    case 1900:  /* move_lo_quad_internal_v4sf */
    case 1901:  /* move_lo_quad_internal_v2df */
    case 1902:  /* move_lo_quad_internal_be_v16qi */
    case 1903:  /* move_lo_quad_internal_be_v8hi */
    case 1904:  /* move_lo_quad_internal_be_v4si */
    case 1905:  /* move_lo_quad_internal_be_v2di */
    case 1906:  /* move_lo_quad_internal_be_v8hf */
    case 1907:  /* move_lo_quad_internal_be_v8bf */
    case 1908:  /* move_lo_quad_internal_be_v4sf */
    case 1909:  /* move_lo_quad_internal_be_v2df */
    case 1910:  /* aarch64_simd_move_hi_quad_v16qi */
    case 1911:  /* aarch64_simd_move_hi_quad_v8hi */
    case 1912:  /* aarch64_simd_move_hi_quad_v4si */
    case 1913:  /* aarch64_simd_move_hi_quad_v2di */
    case 1914:  /* aarch64_simd_move_hi_quad_v8hf */
    case 1915:  /* aarch64_simd_move_hi_quad_v8bf */
    case 1916:  /* aarch64_simd_move_hi_quad_v4sf */
    case 1917:  /* aarch64_simd_move_hi_quad_v2df */
    case 1918:  /* aarch64_simd_move_hi_quad_be_v16qi */
    case 1919:  /* aarch64_simd_move_hi_quad_be_v8hi */
    case 1920:  /* aarch64_simd_move_hi_quad_be_v4si */
    case 1921:  /* aarch64_simd_move_hi_quad_be_v2di */
    case 1922:  /* aarch64_simd_move_hi_quad_be_v8hf */
    case 1923:  /* aarch64_simd_move_hi_quad_be_v8bf */
    case 1924:  /* aarch64_simd_move_hi_quad_be_v4sf */
    case 1925:  /* aarch64_simd_move_hi_quad_be_v2df */
    case 1926:  /* aarch64_simd_vec_pack_trunc_v8hi */
    case 1927:  /* aarch64_simd_vec_pack_trunc_v4si */
    case 1928:  /* aarch64_simd_vec_pack_trunc_v2di */
    case 1929:  /* aarch64_shrnv8hi_insn_le */
    case 1930:  /* aarch64_shrnv4si_insn_le */
    case 1931:  /* aarch64_shrnv2di_insn_le */
    case 1932:  /* aarch64_shrnv8hi_insn_be */
    case 1933:  /* aarch64_shrnv4si_insn_be */
    case 1934:  /* aarch64_shrnv2di_insn_be */
    case 1935:  /* aarch64_rshrnv8hi_insn_le */
    case 1936:  /* aarch64_rshrnv4si_insn_le */
    case 1937:  /* aarch64_rshrnv2di_insn_le */
    case 1938:  /* aarch64_rshrnv8hi_insn_be */
    case 1939:  /* aarch64_rshrnv4si_insn_be */
    case 1940:  /* aarch64_rshrnv2di_insn_be */
    case 1941:  /* aarch64_shrn2v8hi_insn_le */
    case 1942:  /* aarch64_shrn2v4si_insn_le */
    case 1943:  /* aarch64_shrn2v2di_insn_le */
    case 1944:  /* aarch64_shrn2v8hi_insn_be */
    case 1945:  /* aarch64_shrn2v4si_insn_be */
    case 1946:  /* aarch64_shrn2v2di_insn_be */
    case 1947:  /* aarch64_rshrn2v8hi_insn_le */
    case 1948:  /* aarch64_rshrn2v4si_insn_le */
    case 1949:  /* aarch64_rshrn2v2di_insn_le */
    case 1950:  /* aarch64_rshrn2v8hi_insn_be */
    case 1951:  /* aarch64_rshrn2v4si_insn_be */
    case 1952:  /* aarch64_rshrn2v2di_insn_be */
    case 1953:  /* vec_pack_trunc_v8hi */
    case 1954:  /* vec_pack_trunc_v4si */
    case 1955:  /* vec_pack_trunc_v2di */
    case 1956:  /* aarch64_simd_vec_unpacks_lo_v16qi */
    case 1957:  /* aarch64_simd_vec_unpacku_lo_v16qi */
    case 1958:  /* aarch64_simd_vec_unpacks_lo_v8hi */
    case 1959:  /* aarch64_simd_vec_unpacku_lo_v8hi */
    case 1960:  /* aarch64_simd_vec_unpacks_lo_v4si */
    case 1961:  /* aarch64_simd_vec_unpacku_lo_v4si */
    case 1962:  /* aarch64_simd_vec_unpacks_hi_v16qi */
    case 1963:  /* aarch64_simd_vec_unpacku_hi_v16qi */
    case 1964:  /* aarch64_simd_vec_unpacks_hi_v8hi */
    case 1965:  /* aarch64_simd_vec_unpacku_hi_v8hi */
    case 1966:  /* aarch64_simd_vec_unpacks_hi_v4si */
    case 1967:  /* aarch64_simd_vec_unpacku_hi_v4si */
    case 1968:  /* *aarch64_smlal_lov16qi */
    case 1969:  /* *aarch64_umlal_lov16qi */
    case 1970:  /* *aarch64_smlal_lov8hi */
    case 1971:  /* *aarch64_umlal_lov8hi */
    case 1972:  /* *aarch64_smlal_lov4si */
    case 1973:  /* *aarch64_umlal_lov4si */
    case 1974:  /* aarch64_smlal_hiv16qi_insn */
    case 1975:  /* aarch64_umlal_hiv16qi_insn */
    case 1976:  /* aarch64_smlal_hiv8hi_insn */
    case 1977:  /* aarch64_umlal_hiv8hi_insn */
    case 1978:  /* aarch64_smlal_hiv4si_insn */
    case 1979:  /* aarch64_umlal_hiv4si_insn */
    case 1980:  /* aarch64_smlal_hi_nv8hi_insn */
    case 1981:  /* aarch64_umlal_hi_nv8hi_insn */
    case 1982:  /* aarch64_smlal_hi_nv4si_insn */
    case 1983:  /* aarch64_umlal_hi_nv4si_insn */
    case 1984:  /* *aarch64_smlsl_lov16qi */
    case 1985:  /* *aarch64_umlsl_lov16qi */
    case 1986:  /* *aarch64_smlsl_lov8hi */
    case 1987:  /* *aarch64_umlsl_lov8hi */
    case 1988:  /* *aarch64_smlsl_lov4si */
    case 1989:  /* *aarch64_umlsl_lov4si */
    case 1990:  /* aarch64_smlsl_hiv16qi_insn */
    case 1991:  /* aarch64_umlsl_hiv16qi_insn */
    case 1992:  /* aarch64_smlsl_hiv8hi_insn */
    case 1993:  /* aarch64_umlsl_hiv8hi_insn */
    case 1994:  /* aarch64_smlsl_hiv4si_insn */
    case 1995:  /* aarch64_umlsl_hiv4si_insn */
    case 1996:  /* aarch64_smlsl_hi_nv8hi_insn */
    case 1997:  /* aarch64_umlsl_hi_nv8hi_insn */
    case 1998:  /* aarch64_smlsl_hi_nv4si_insn */
    case 1999:  /* aarch64_umlsl_hi_nv4si_insn */
    case 2000:  /* aarch64_smlalv8qi */
    case 2001:  /* aarch64_umlalv8qi */
    case 2002:  /* aarch64_smlalv4hi */
    case 2003:  /* aarch64_umlalv4hi */
    case 2004:  /* aarch64_smlalv2si */
    case 2005:  /* aarch64_umlalv2si */
    case 2006:  /* aarch64_smlal_nv4hi */
    case 2007:  /* aarch64_umlal_nv4hi */
    case 2008:  /* aarch64_smlal_nv2si */
    case 2009:  /* aarch64_umlal_nv2si */
    case 2010:  /* aarch64_smlslv8qi */
    case 2011:  /* aarch64_umlslv8qi */
    case 2012:  /* aarch64_smlslv4hi */
    case 2013:  /* aarch64_umlslv4hi */
    case 2014:  /* aarch64_smlslv2si */
    case 2015:  /* aarch64_umlslv2si */
    case 2016:  /* aarch64_smlsl_nv4hi */
    case 2017:  /* aarch64_umlsl_nv4hi */
    case 2018:  /* aarch64_smlsl_nv2si */
    case 2019:  /* aarch64_umlsl_nv2si */
    case 2020:  /* aarch64_simd_vec_smult_lo_v16qi */
    case 2021:  /* aarch64_simd_vec_umult_lo_v16qi */
    case 2022:  /* aarch64_simd_vec_smult_lo_v8hi */
    case 2023:  /* aarch64_simd_vec_umult_lo_v8hi */
    case 2024:  /* aarch64_simd_vec_smult_lo_v4si */
    case 2025:  /* aarch64_simd_vec_umult_lo_v4si */
    case 2026:  /* aarch64_intrinsic_vec_smult_lo_v8qi */
    case 2027:  /* aarch64_intrinsic_vec_umult_lo_v8qi */
    case 2028:  /* aarch64_intrinsic_vec_smult_lo_v4hi */
    case 2029:  /* aarch64_intrinsic_vec_umult_lo_v4hi */
    case 2030:  /* aarch64_intrinsic_vec_smult_lo_v2si */
    case 2031:  /* aarch64_intrinsic_vec_umult_lo_v2si */
    case 2032:  /* aarch64_simd_vec_smult_hi_v16qi */
    case 2033:  /* aarch64_simd_vec_umult_hi_v16qi */
    case 2034:  /* aarch64_simd_vec_smult_hi_v8hi */
    case 2035:  /* aarch64_simd_vec_umult_hi_v8hi */
    case 2036:  /* aarch64_simd_vec_smult_hi_v4si */
    case 2037:  /* aarch64_simd_vec_umult_hi_v4si */
    case 2038:  /* aarch64_vec_smult_lane_v4hi */
    case 2039:  /* aarch64_vec_umult_lane_v4hi */
    case 2040:  /* aarch64_vec_smult_laneq_v4hi */
    case 2041:  /* aarch64_vec_umult_laneq_v4hi */
    case 2042:  /* aarch64_vec_smult_lane_v2si */
    case 2043:  /* aarch64_vec_umult_lane_v2si */
    case 2044:  /* aarch64_vec_smult_laneq_v2si */
    case 2045:  /* aarch64_vec_umult_laneq_v2si */
    case 2046:  /* aarch64_smull_hi_lanev8hi_insn */
    case 2047:  /* aarch64_umull_hi_lanev8hi_insn */
    case 2048:  /* aarch64_smull_hi_lanev4si_insn */
    case 2049:  /* aarch64_umull_hi_lanev4si_insn */
    case 2050:  /* aarch64_smull_hi_laneqv8hi_insn */
    case 2051:  /* aarch64_umull_hi_laneqv8hi_insn */
    case 2052:  /* aarch64_smull_hi_laneqv4si_insn */
    case 2053:  /* aarch64_umull_hi_laneqv4si_insn */
    case 2054:  /* aarch64_smull_nv4hi */
    case 2055:  /* aarch64_umull_nv4hi */
    case 2056:  /* aarch64_smull_nv2si */
    case 2057:  /* aarch64_umull_nv2si */
    case 2058:  /* aarch64_smull_hi_nv8hi_insn */
    case 2059:  /* aarch64_umull_hi_nv8hi_insn */
    case 2060:  /* aarch64_smull_hi_nv4si_insn */
    case 2061:  /* aarch64_umull_hi_nv4si_insn */
    case 2062:  /* aarch64_vec_smlal_lane_v4hi */
    case 2063:  /* aarch64_vec_umlal_lane_v4hi */
    case 2064:  /* aarch64_vec_smlal_laneq_v4hi */
    case 2065:  /* aarch64_vec_umlal_laneq_v4hi */
    case 2066:  /* aarch64_vec_smlal_lane_v2si */
    case 2067:  /* aarch64_vec_umlal_lane_v2si */
    case 2068:  /* aarch64_vec_smlal_laneq_v2si */
    case 2069:  /* aarch64_vec_umlal_laneq_v2si */
    case 2070:  /* aarch64_smlal_hi_lanev8hi_insn */
    case 2071:  /* aarch64_umlal_hi_lanev8hi_insn */
    case 2072:  /* aarch64_smlal_hi_lanev4si_insn */
    case 2073:  /* aarch64_umlal_hi_lanev4si_insn */
    case 2074:  /* aarch64_smlal_hi_laneqv8hi_insn */
    case 2075:  /* aarch64_umlal_hi_laneqv8hi_insn */
    case 2076:  /* aarch64_smlal_hi_laneqv4si_insn */
    case 2077:  /* aarch64_umlal_hi_laneqv4si_insn */
    case 2078:  /* aarch64_vec_smlsl_lane_v4hi */
    case 2079:  /* aarch64_vec_umlsl_lane_v4hi */
    case 2080:  /* aarch64_vec_smlsl_laneq_v4hi */
    case 2081:  /* aarch64_vec_umlsl_laneq_v4hi */
    case 2082:  /* aarch64_vec_smlsl_lane_v2si */
    case 2083:  /* aarch64_vec_umlsl_lane_v2si */
    case 2084:  /* aarch64_vec_smlsl_laneq_v2si */
    case 2085:  /* aarch64_vec_umlsl_laneq_v2si */
    case 2086:  /* aarch64_smlsl_hi_lanev8hi_insn */
    case 2087:  /* aarch64_umlsl_hi_lanev8hi_insn */
    case 2088:  /* aarch64_smlsl_hi_lanev4si_insn */
    case 2089:  /* aarch64_umlsl_hi_lanev4si_insn */
    case 2090:  /* aarch64_smlsl_hi_laneqv8hi_insn */
    case 2091:  /* aarch64_umlsl_hi_laneqv8hi_insn */
    case 2092:  /* aarch64_smlsl_hi_laneqv4si_insn */
    case 2093:  /* aarch64_umlsl_hi_laneqv4si_insn */
    case 2094:  /* addv4hf3 */
    case 2095:  /* addv8hf3 */
    case 2096:  /* addv2sf3 */
    case 2097:  /* addv4sf3 */
    case 2098:  /* addv2df3 */
    case 2099:  /* subv4hf3 */
    case 2100:  /* subv8hf3 */
    case 2101:  /* subv2sf3 */
    case 2102:  /* subv4sf3 */
    case 2103:  /* subv2df3 */
    case 2104:  /* mulv4hf3 */
    case 2105:  /* mulv8hf3 */
    case 2106:  /* mulv2sf3 */
    case 2107:  /* mulv4sf3 */
    case 2108:  /* mulv2df3 */
    case 2109:  /* *divv4hf3 */
    case 2110:  /* *divv8hf3 */
    case 2111:  /* *divv2sf3 */
    case 2112:  /* *divv4sf3 */
    case 2113:  /* *divv2df3 */
    case 2114:  /* negv4hf2 */
    case 2115:  /* negv8hf2 */
    case 2116:  /* negv2sf2 */
    case 2117:  /* negv4sf2 */
    case 2118:  /* negv2df2 */
    case 2119:  /* absv4hf2 */
    case 2120:  /* absv8hf2 */
    case 2121:  /* absv2sf2 */
    case 2122:  /* absv4sf2 */
    case 2123:  /* absv2df2 */
    case 2124:  /* fmav4hf4 */
    case 2125:  /* fmav8hf4 */
    case 2126:  /* fmav2sf4 */
    case 2127:  /* fmav4sf4 */
    case 2128:  /* fmav2df4 */
    case 2129:  /* *aarch64_fma4_eltv2sf */
    case 2130:  /* *aarch64_fma4_eltv4sf */
    case 2131:  /* *aarch64_fma4_eltv2df */
    case 2132:  /* *aarch64_fma4_elt_to_128v2sf */
    case 2133:  /* *aarch64_fma4_elt_to_64v4sf */
    case 2134:  /* *aarch64_fma4_elt_from_dupv4hi */
    case 2135:  /* *aarch64_fma4_elt_from_dupv8hi */
    case 2136:  /* *aarch64_fma4_elt_from_dupv2si */
    case 2137:  /* *aarch64_fma4_elt_from_dupv4si */
    case 2138:  /* *aarch64_fma4_elt_from_dupv4hf */
    case 2139:  /* *aarch64_fma4_elt_from_dupv8hf */
    case 2140:  /* *aarch64_fma4_elt_from_dupv2sf */
    case 2141:  /* *aarch64_fma4_elt_from_dupv4sf */
    case 2142:  /* *aarch64_fma4_elt_from_dupv2df */
    case 2143:  /* *aarch64_fma4_elt_to_64v2df */
    case 2144:  /* fnmav4hf4 */
    case 2145:  /* fnmav8hf4 */
    case 2146:  /* fnmav2sf4 */
    case 2147:  /* fnmav4sf4 */
    case 2148:  /* fnmav2df4 */
    case 2149:  /* *aarch64_fnma4_eltv2sf */
    case 2150:  /* *aarch64_fnma4_eltv4sf */
    case 2151:  /* *aarch64_fnma4_eltv2df */
    case 2152:  /* *aarch64_fnma4_elt_to_128v2sf */
    case 2153:  /* *aarch64_fnma4_elt_to_64v4sf */
    case 2154:  /* *aarch64_fnma4_elt_from_dupv4hi */
    case 2155:  /* *aarch64_fnma4_elt_from_dupv8hi */
    case 2156:  /* *aarch64_fnma4_elt_from_dupv2si */
    case 2157:  /* *aarch64_fnma4_elt_from_dupv4si */
    case 2158:  /* *aarch64_fnma4_elt_from_dupv4hf */
    case 2159:  /* *aarch64_fnma4_elt_from_dupv8hf */
    case 2160:  /* *aarch64_fnma4_elt_from_dupv2sf */
    case 2161:  /* *aarch64_fnma4_elt_from_dupv4sf */
    case 2162:  /* *aarch64_fnma4_elt_from_dupv2df */
    case 2163:  /* *aarch64_fnma4_elt_to_64v2df */
    case 2164:  /* btruncv4hf2 */
    case 2165:  /* ceilv4hf2 */
    case 2166:  /* floorv4hf2 */
    case 2167:  /* frintnv4hf2 */
    case 2168:  /* nearbyintv4hf2 */
    case 2169:  /* rintv4hf2 */
    case 2170:  /* roundv4hf2 */
    case 2171:  /* btruncv8hf2 */
    case 2172:  /* ceilv8hf2 */
    case 2173:  /* floorv8hf2 */
    case 2174:  /* frintnv8hf2 */
    case 2175:  /* nearbyintv8hf2 */
    case 2176:  /* rintv8hf2 */
    case 2177:  /* roundv8hf2 */
    case 2178:  /* btruncv2sf2 */
    case 2179:  /* ceilv2sf2 */
    case 2180:  /* floorv2sf2 */
    case 2181:  /* frintnv2sf2 */
    case 2182:  /* nearbyintv2sf2 */
    case 2183:  /* rintv2sf2 */
    case 2184:  /* roundv2sf2 */
    case 2185:  /* btruncv4sf2 */
    case 2186:  /* ceilv4sf2 */
    case 2187:  /* floorv4sf2 */
    case 2188:  /* frintnv4sf2 */
    case 2189:  /* nearbyintv4sf2 */
    case 2190:  /* rintv4sf2 */
    case 2191:  /* roundv4sf2 */
    case 2192:  /* btruncv2df2 */
    case 2193:  /* ceilv2df2 */
    case 2194:  /* floorv2df2 */
    case 2195:  /* frintnv2df2 */
    case 2196:  /* nearbyintv2df2 */
    case 2197:  /* rintv2df2 */
    case 2198:  /* roundv2df2 */
    case 2199:  /* lbtruncv4hfv4hi2 */
    case 2200:  /* lceilv4hfv4hi2 */
    case 2201:  /* lfloorv4hfv4hi2 */
    case 2202:  /* lroundv4hfv4hi2 */
    case 2203:  /* lfrintnv4hfv4hi2 */
    case 2204:  /* lbtruncuv4hfv4hi2 */
    case 2205:  /* lceiluv4hfv4hi2 */
    case 2206:  /* lflooruv4hfv4hi2 */
    case 2207:  /* lrounduv4hfv4hi2 */
    case 2208:  /* lfrintnuv4hfv4hi2 */
    case 2209:  /* lbtruncv8hfv8hi2 */
    case 2210:  /* lceilv8hfv8hi2 */
    case 2211:  /* lfloorv8hfv8hi2 */
    case 2212:  /* lroundv8hfv8hi2 */
    case 2213:  /* lfrintnv8hfv8hi2 */
    case 2214:  /* lbtruncuv8hfv8hi2 */
    case 2215:  /* lceiluv8hfv8hi2 */
    case 2216:  /* lflooruv8hfv8hi2 */
    case 2217:  /* lrounduv8hfv8hi2 */
    case 2218:  /* lfrintnuv8hfv8hi2 */
    case 2219:  /* lbtruncv2sfv2si2 */
    case 2220:  /* lceilv2sfv2si2 */
    case 2221:  /* lfloorv2sfv2si2 */
    case 2222:  /* lroundv2sfv2si2 */
    case 2223:  /* lfrintnv2sfv2si2 */
    case 2224:  /* lbtruncuv2sfv2si2 */
    case 2225:  /* lceiluv2sfv2si2 */
    case 2226:  /* lflooruv2sfv2si2 */
    case 2227:  /* lrounduv2sfv2si2 */
    case 2228:  /* lfrintnuv2sfv2si2 */
    case 2229:  /* lbtruncv4sfv4si2 */
    case 2230:  /* lceilv4sfv4si2 */
    case 2231:  /* lfloorv4sfv4si2 */
    case 2232:  /* lroundv4sfv4si2 */
    case 2233:  /* lfrintnv4sfv4si2 */
    case 2234:  /* lbtruncuv4sfv4si2 */
    case 2235:  /* lceiluv4sfv4si2 */
    case 2236:  /* lflooruv4sfv4si2 */
    case 2237:  /* lrounduv4sfv4si2 */
    case 2238:  /* lfrintnuv4sfv4si2 */
    case 2239:  /* lbtruncv2dfv2di2 */
    case 2240:  /* lceilv2dfv2di2 */
    case 2241:  /* lfloorv2dfv2di2 */
    case 2242:  /* lroundv2dfv2di2 */
    case 2243:  /* lfrintnv2dfv2di2 */
    case 2244:  /* lbtruncuv2dfv2di2 */
    case 2245:  /* lceiluv2dfv2di2 */
    case 2246:  /* lflooruv2dfv2di2 */
    case 2247:  /* lrounduv2dfv2di2 */
    case 2248:  /* lfrintnuv2dfv2di2 */
    case 2249:  /* lbtrunchfhi2 */
    case 2250:  /* lceilhfhi2 */
    case 2251:  /* lfloorhfhi2 */
    case 2252:  /* lroundhfhi2 */
    case 2253:  /* lfrintnhfhi2 */
    case 2254:  /* lbtruncuhfhi2 */
    case 2255:  /* lceiluhfhi2 */
    case 2256:  /* lflooruhfhi2 */
    case 2257:  /* lrounduhfhi2 */
    case 2258:  /* lfrintnuhfhi2 */
    case 2259:  /* fix_trunchfhi2 */
    case 2260:  /* fixuns_trunchfhi2 */
    case 2261:  /* floathihf2 */
    case 2262:  /* floatunshihf2 */
    case 2263:  /* *aarch64_fcvtv2sfv2si2_mult */
    case 2264:  /* *aarch64_fcvtuv2sfv2si2_mult */
    case 2265:  /* *aarch64_fcvtv4sfv4si2_mult */
    case 2266:  /* *aarch64_fcvtuv4sfv4si2_mult */
    case 2267:  /* *aarch64_fcvtv2dfv2di2_mult */
    case 2268:  /* *aarch64_fcvtuv2dfv2di2_mult */
    case 2269:  /* floatv4hiv4hf2 */
    case 2270:  /* floatunsv4hiv4hf2 */
    case 2271:  /* floatv8hiv8hf2 */
    case 2272:  /* floatunsv8hiv8hf2 */
    case 2273:  /* floatv2siv2sf2 */
    case 2274:  /* floatunsv2siv2sf2 */
    case 2275:  /* floatv4siv4sf2 */
    case 2276:  /* floatunsv4siv4sf2 */
    case 2277:  /* floatv2div2df2 */
    case 2278:  /* floatunsv2div2df2 */
    case 2279:  /* aarch64_simd_vec_unpacks_lo_v8hf */
    case 2280:  /* aarch64_simd_vec_unpacks_lo_v4sf */
    case 2281:  /* fcvtzsv4hf3 */
    case 2282:  /* fcvtzuv4hf3 */
    case 2283:  /* fcvtzsv8hf3 */
    case 2284:  /* fcvtzuv8hf3 */
    case 2285:  /* fcvtzsv2sf3 */
    case 2286:  /* fcvtzuv2sf3 */
    case 2287:  /* fcvtzsv4sf3 */
    case 2288:  /* fcvtzuv4sf3 */
    case 2289:  /* fcvtzsv2df3 */
    case 2290:  /* fcvtzuv2df3 */
    case 2291:  /* scvtfv4hi3 */
    case 2292:  /* ucvtfv4hi3 */
    case 2293:  /* scvtfv8hi3 */
    case 2294:  /* ucvtfv8hi3 */
    case 2295:  /* scvtfv2si3 */
    case 2296:  /* ucvtfv2si3 */
    case 2297:  /* scvtfv4si3 */
    case 2298:  /* ucvtfv4si3 */
    case 2299:  /* scvtfv2di3 */
    case 2300:  /* ucvtfv2di3 */
    case 2301:  /* aarch64_simd_vec_unpacks_hi_v8hf */
    case 2302:  /* aarch64_simd_vec_unpacks_hi_v4sf */
    case 2303:  /* aarch64_float_extend_lo_v2df */
    case 2304:  /* aarch64_float_extend_lo_v4sf */
    case 2305:  /* aarch64_float_truncate_lo_v2sf */
    case 2306:  /* aarch64_float_truncate_lo_v4hf */
    case 2307:  /* aarch64_float_truncate_hi_v4sf_le */
    case 2308:  /* aarch64_float_truncate_hi_v8hf_le */
    case 2309:  /* aarch64_float_truncate_hi_v4sf_be */
    case 2310:  /* aarch64_float_truncate_hi_v8hf_be */
    case 2311:  /* smaxv4hf3 */
    case 2312:  /* sminv4hf3 */
    case 2313:  /* smaxv8hf3 */
    case 2314:  /* sminv8hf3 */
    case 2315:  /* smaxv2sf3 */
    case 2316:  /* sminv2sf3 */
    case 2317:  /* smaxv4sf3 */
    case 2318:  /* sminv4sf3 */
    case 2319:  /* smaxv2df3 */
    case 2320:  /* sminv2df3 */
    case 2321:  /* smax_nanv4hf3 */
    case 2322:  /* smin_nanv4hf3 */
    case 2323:  /* fmaxv4hf3 */
    case 2324:  /* fminv4hf3 */
    case 2325:  /* smax_nanv8hf3 */
    case 2326:  /* smin_nanv8hf3 */
    case 2327:  /* fmaxv8hf3 */
    case 2328:  /* fminv8hf3 */
    case 2329:  /* smax_nanv2sf3 */
    case 2330:  /* smin_nanv2sf3 */
    case 2331:  /* fmaxv2sf3 */
    case 2332:  /* fminv2sf3 */
    case 2333:  /* smax_nanv4sf3 */
    case 2334:  /* smin_nanv4sf3 */
    case 2335:  /* fmaxv4sf3 */
    case 2336:  /* fminv4sf3 */
    case 2337:  /* smax_nanv2df3 */
    case 2338:  /* smin_nanv2df3 */
    case 2339:  /* fmaxv2df3 */
    case 2340:  /* fminv2df3 */
    case 2341:  /* aarch64_faddpv4hf */
    case 2342:  /* aarch64_faddpv8hf */
    case 2343:  /* aarch64_faddpv2sf */
    case 2344:  /* aarch64_faddpv4sf */
    case 2345:  /* aarch64_faddpv2df */
    case 2346:  /* aarch64_reduc_plus_internalv8qi */
    case 2347:  /* aarch64_reduc_plus_internalv16qi */
    case 2348:  /* aarch64_reduc_plus_internalv4hi */
    case 2349:  /* aarch64_reduc_plus_internalv8hi */
    case 2350:  /* aarch64_reduc_plus_internalv4si */
    case 2351:  /* aarch64_reduc_plus_internalv2di */
    case 2352:  /* aarch64_saddlvv8qi */
    case 2353:  /* aarch64_uaddlvv8qi */
    case 2354:  /* aarch64_saddlvv16qi */
    case 2355:  /* aarch64_uaddlvv16qi */
    case 2356:  /* aarch64_saddlvv4hi */
    case 2357:  /* aarch64_uaddlvv4hi */
    case 2358:  /* aarch64_saddlvv8hi */
    case 2359:  /* aarch64_uaddlvv8hi */
    case 2360:  /* aarch64_saddlvv4si */
    case 2361:  /* aarch64_uaddlvv4si */
    case 2362:  /* aarch64_saddlvv2si */
    case 2363:  /* aarch64_uaddlvv2si */
    case 2364:  /* aarch64_zero_extendsi_reduc_plus_v8qi */
    case 2365:  /* aarch64_zero_extenddi_reduc_plus_v8qi */
    case 2366:  /* aarch64_zero_extendsi_reduc_plus_v16qi */
    case 2367:  /* aarch64_zero_extenddi_reduc_plus_v16qi */
    case 2368:  /* aarch64_zero_extendsi_reduc_plus_v4hi */
    case 2369:  /* aarch64_zero_extenddi_reduc_plus_v4hi */
    case 2370:  /* aarch64_zero_extendsi_reduc_plus_v8hi */
    case 2371:  /* aarch64_zero_extenddi_reduc_plus_v8hi */
    case 2372:  /* aarch64_reduc_plus_internalv2si */
    case 2373:  /* reduc_plus_scal_v2sf */
    case 2374:  /* reduc_plus_scal_v2df */
    case 2375:  /* clrsbv8qi2 */
    case 2376:  /* clrsbv16qi2 */
    case 2377:  /* clrsbv4hi2 */
    case 2378:  /* clrsbv8hi2 */
    case 2379:  /* clrsbv2si2 */
    case 2380:  /* clrsbv4si2 */
    case 2381:  /* clzv8qi2 */
    case 2382:  /* clzv16qi2 */
    case 2383:  /* clzv4hi2 */
    case 2384:  /* clzv8hi2 */
    case 2385:  /* clzv2si2 */
    case 2386:  /* clzv4si2 */
    case 2387:  /* popcountv8qi2 */
    case 2388:  /* popcountv16qi2 */
    case 2389:  /* aarch64_reduc_umax_internalv8qi */
    case 2390:  /* aarch64_reduc_umin_internalv8qi */
    case 2391:  /* aarch64_reduc_smax_internalv8qi */
    case 2392:  /* aarch64_reduc_smin_internalv8qi */
    case 2393:  /* aarch64_reduc_umax_internalv16qi */
    case 2394:  /* aarch64_reduc_umin_internalv16qi */
    case 2395:  /* aarch64_reduc_smax_internalv16qi */
    case 2396:  /* aarch64_reduc_smin_internalv16qi */
    case 2397:  /* aarch64_reduc_umax_internalv4hi */
    case 2398:  /* aarch64_reduc_umin_internalv4hi */
    case 2399:  /* aarch64_reduc_smax_internalv4hi */
    case 2400:  /* aarch64_reduc_smin_internalv4hi */
    case 2401:  /* aarch64_reduc_umax_internalv8hi */
    case 2402:  /* aarch64_reduc_umin_internalv8hi */
    case 2403:  /* aarch64_reduc_smax_internalv8hi */
    case 2404:  /* aarch64_reduc_smin_internalv8hi */
    case 2405:  /* aarch64_reduc_umax_internalv4si */
    case 2406:  /* aarch64_reduc_umin_internalv4si */
    case 2407:  /* aarch64_reduc_smax_internalv4si */
    case 2408:  /* aarch64_reduc_smin_internalv4si */
    case 2409:  /* aarch64_reduc_umax_internalv2si */
    case 2410:  /* aarch64_reduc_umin_internalv2si */
    case 2411:  /* aarch64_reduc_smax_internalv2si */
    case 2412:  /* aarch64_reduc_smin_internalv2si */
    case 2413:  /* aarch64_reduc_smax_nan_internalv4hf */
    case 2414:  /* aarch64_reduc_smin_nan_internalv4hf */
    case 2415:  /* aarch64_reduc_smax_internalv4hf */
    case 2416:  /* aarch64_reduc_smin_internalv4hf */
    case 2417:  /* aarch64_reduc_smax_nan_internalv8hf */
    case 2418:  /* aarch64_reduc_smin_nan_internalv8hf */
    case 2419:  /* aarch64_reduc_smax_internalv8hf */
    case 2420:  /* aarch64_reduc_smin_internalv8hf */
    case 2421:  /* aarch64_reduc_smax_nan_internalv2sf */
    case 2422:  /* aarch64_reduc_smin_nan_internalv2sf */
    case 2423:  /* aarch64_reduc_smax_internalv2sf */
    case 2424:  /* aarch64_reduc_smin_internalv2sf */
    case 2425:  /* aarch64_reduc_smax_nan_internalv4sf */
    case 2426:  /* aarch64_reduc_smin_nan_internalv4sf */
    case 2427:  /* aarch64_reduc_smax_internalv4sf */
    case 2428:  /* aarch64_reduc_smin_internalv4sf */
    case 2429:  /* aarch64_reduc_smax_nan_internalv2df */
    case 2430:  /* aarch64_reduc_smin_nan_internalv2df */
    case 2431:  /* aarch64_reduc_smax_internalv2df */
    case 2432:  /* aarch64_reduc_smin_internalv2df */
    case 2433:  /* aarch64_simd_bslv8qi_internal */
    case 2434:  /* aarch64_simd_bslv16qi_internal */
    case 2435:  /* aarch64_simd_bslv4hi_internal */
    case 2436:  /* aarch64_simd_bslv8hi_internal */
    case 2437:  /* aarch64_simd_bslv2si_internal */
    case 2438:  /* aarch64_simd_bslv4si_internal */
    case 2439:  /* aarch64_simd_bslv2di_internal */
    case 2440:  /* *aarch64_simd_bslv8qi_alt */
    case 2441:  /* *aarch64_simd_bslv16qi_alt */
    case 2442:  /* *aarch64_simd_bslv4hi_alt */
    case 2443:  /* *aarch64_simd_bslv8hi_alt */
    case 2444:  /* *aarch64_simd_bslv2si_alt */
    case 2445:  /* *aarch64_simd_bslv4si_alt */
    case 2446:  /* *aarch64_simd_bslv2di_alt */
    case 2447:  /* aarch64_simd_bsldi_internal */
    case 2448:  /* aarch64_simd_bsldi_alt */
    case 2449:  /* *aarch64_get_lane_extendsiv8qi */
    case 2450:  /* *aarch64_get_lane_extenddiv8qi */
    case 2451:  /* *aarch64_get_lane_extendsiv16qi */
    case 2452:  /* *aarch64_get_lane_extenddiv16qi */
    case 2453:  /* *aarch64_get_lane_extendsiv4hi */
    case 2454:  /* *aarch64_get_lane_extenddiv4hi */
    case 2455:  /* *aarch64_get_lane_extendsiv8hi */
    case 2456:  /* *aarch64_get_lane_extenddiv8hi */
    case 2457:  /* *aarch64_get_lane_zero_extendsiv8qi */
    case 2458:  /* *aarch64_get_lane_zero_extenddiv8qi */
    case 2459:  /* *aarch64_get_lane_zero_extendsiv16qi */
    case 2460:  /* *aarch64_get_lane_zero_extenddiv16qi */
    case 2461:  /* *aarch64_get_lane_zero_extendsiv4hi */
    case 2462:  /* *aarch64_get_lane_zero_extenddiv4hi */
    case 2463:  /* *aarch64_get_lane_zero_extendsiv8hi */
    case 2464:  /* *aarch64_get_lane_zero_extenddiv8hi */
    case 2465:  /* aarch64_get_lanev8qi */
    case 2466:  /* aarch64_get_lanev16qi */
    case 2467:  /* aarch64_get_lanev4hi */
    case 2468:  /* aarch64_get_lanev8hi */
    case 2469:  /* aarch64_get_lanev2si */
    case 2470:  /* aarch64_get_lanev4si */
    case 2471:  /* aarch64_get_lanev2di */
    case 2472:  /* aarch64_get_lanev4hf */
    case 2473:  /* aarch64_get_lanev8hf */
    case 2474:  /* aarch64_get_lanev4bf */
    case 2475:  /* aarch64_get_lanev8bf */
    case 2476:  /* aarch64_get_lanev2sf */
    case 2477:  /* aarch64_get_lanev4sf */
    case 2478:  /* aarch64_get_lanev2df */
    case 2479:  /* load_pair_lanesv8qi */
    case 2480:  /* load_pair_lanesv4hi */
    case 2481:  /* load_pair_lanesv4bf */
    case 2482:  /* load_pair_lanesv4hf */
    case 2483:  /* load_pair_lanesv2si */
    case 2484:  /* load_pair_lanesv2sf */
    case 2485:  /* load_pair_lanesdi */
    case 2486:  /* load_pair_lanesdf */
    case 2487:  /* store_pair_lanesv8qi */
    case 2488:  /* store_pair_lanesv4hi */
    case 2489:  /* store_pair_lanesv4bf */
    case 2490:  /* store_pair_lanesv4hf */
    case 2491:  /* store_pair_lanesv2si */
    case 2492:  /* store_pair_lanesv2sf */
    case 2493:  /* store_pair_lanesdi */
    case 2494:  /* store_pair_lanesdf */
    case 2495:  /* aarch64_combinezv8qi */
    case 2496:  /* aarch64_combinezv4hi */
    case 2497:  /* aarch64_combinezv4bf */
    case 2498:  /* aarch64_combinezv4hf */
    case 2499:  /* aarch64_combinezv2si */
    case 2500:  /* aarch64_combinezv2sf */
    case 2501:  /* aarch64_combinezdi */
    case 2502:  /* aarch64_combinezdf */
    case 2503:  /* aarch64_combinez_bev8qi */
    case 2504:  /* aarch64_combinez_bev4hi */
    case 2505:  /* aarch64_combinez_bev4bf */
    case 2506:  /* aarch64_combinez_bev4hf */
    case 2507:  /* aarch64_combinez_bev2si */
    case 2508:  /* aarch64_combinez_bev2sf */
    case 2509:  /* aarch64_combinez_bedi */
    case 2510:  /* aarch64_combinez_bedf */
    case 2511:  /* aarch64_saddlv16qi_hi_internal */
    case 2512:  /* aarch64_ssublv16qi_hi_internal */
    case 2513:  /* aarch64_uaddlv16qi_hi_internal */
    case 2514:  /* aarch64_usublv16qi_hi_internal */
    case 2515:  /* aarch64_saddlv8hi_hi_internal */
    case 2516:  /* aarch64_ssublv8hi_hi_internal */
    case 2517:  /* aarch64_uaddlv8hi_hi_internal */
    case 2518:  /* aarch64_usublv8hi_hi_internal */
    case 2519:  /* aarch64_saddlv4si_hi_internal */
    case 2520:  /* aarch64_ssublv4si_hi_internal */
    case 2521:  /* aarch64_uaddlv4si_hi_internal */
    case 2522:  /* aarch64_usublv4si_hi_internal */
    case 2523:  /* aarch64_saddlv16qi_lo_internal */
    case 2524:  /* aarch64_ssublv16qi_lo_internal */
    case 2525:  /* aarch64_uaddlv16qi_lo_internal */
    case 2526:  /* aarch64_usublv16qi_lo_internal */
    case 2527:  /* aarch64_saddlv8hi_lo_internal */
    case 2528:  /* aarch64_ssublv8hi_lo_internal */
    case 2529:  /* aarch64_uaddlv8hi_lo_internal */
    case 2530:  /* aarch64_usublv8hi_lo_internal */
    case 2531:  /* aarch64_saddlv4si_lo_internal */
    case 2532:  /* aarch64_ssublv4si_lo_internal */
    case 2533:  /* aarch64_uaddlv4si_lo_internal */
    case 2534:  /* aarch64_usublv4si_lo_internal */
    case 2535:  /* aarch64_saddlv8qi */
    case 2536:  /* aarch64_ssublv8qi */
    case 2537:  /* aarch64_uaddlv8qi */
    case 2538:  /* aarch64_usublv8qi */
    case 2539:  /* aarch64_saddlv4hi */
    case 2540:  /* aarch64_ssublv4hi */
    case 2541:  /* aarch64_uaddlv4hi */
    case 2542:  /* aarch64_usublv4hi */
    case 2543:  /* aarch64_saddlv2si */
    case 2544:  /* aarch64_ssublv2si */
    case 2545:  /* aarch64_uaddlv2si */
    case 2546:  /* aarch64_usublv2si */
    case 2547:  /* aarch64_ssubwv8qi */
    case 2548:  /* aarch64_usubwv8qi */
    case 2549:  /* aarch64_ssubwv4hi */
    case 2550:  /* aarch64_usubwv4hi */
    case 2551:  /* aarch64_ssubwv2si */
    case 2552:  /* aarch64_usubwv2si */
    case 2553:  /* aarch64_ssubwv16qi_internal */
    case 2554:  /* aarch64_usubwv16qi_internal */
    case 2555:  /* aarch64_ssubwv8hi_internal */
    case 2556:  /* aarch64_usubwv8hi_internal */
    case 2557:  /* aarch64_ssubwv4si_internal */
    case 2558:  /* aarch64_usubwv4si_internal */
    case 2559:  /* aarch64_ssubw2v16qi_internal */
    case 2560:  /* aarch64_usubw2v16qi_internal */
    case 2561:  /* aarch64_ssubw2v8hi_internal */
    case 2562:  /* aarch64_usubw2v8hi_internal */
    case 2563:  /* aarch64_ssubw2v4si_internal */
    case 2564:  /* aarch64_usubw2v4si_internal */
    case 2565:  /* aarch64_saddwv8qi */
    case 2566:  /* aarch64_uaddwv8qi */
    case 2567:  /* aarch64_saddwv4hi */
    case 2568:  /* aarch64_uaddwv4hi */
    case 2569:  /* aarch64_saddwv2si */
    case 2570:  /* aarch64_uaddwv2si */
    case 2571:  /* aarch64_saddwv16qi_internal */
    case 2572:  /* aarch64_uaddwv16qi_internal */
    case 2573:  /* aarch64_saddwv8hi_internal */
    case 2574:  /* aarch64_uaddwv8hi_internal */
    case 2575:  /* aarch64_saddwv4si_internal */
    case 2576:  /* aarch64_uaddwv4si_internal */
    case 2577:  /* aarch64_saddw2v16qi_internal */
    case 2578:  /* aarch64_uaddw2v16qi_internal */
    case 2579:  /* aarch64_saddw2v8hi_internal */
    case 2580:  /* aarch64_uaddw2v8hi_internal */
    case 2581:  /* aarch64_saddw2v4si_internal */
    case 2582:  /* aarch64_uaddw2v4si_internal */
    case 2583:  /* aarch64_shaddv8qi */
    case 2584:  /* aarch64_uhaddv8qi */
    case 2585:  /* aarch64_srhaddv8qi */
    case 2586:  /* aarch64_urhaddv8qi */
    case 2587:  /* aarch64_shsubv8qi */
    case 2588:  /* aarch64_uhsubv8qi */
    case 2589:  /* aarch64_shaddv16qi */
    case 2590:  /* aarch64_uhaddv16qi */
    case 2591:  /* aarch64_srhaddv16qi */
    case 2592:  /* aarch64_urhaddv16qi */
    case 2593:  /* aarch64_shsubv16qi */
    case 2594:  /* aarch64_uhsubv16qi */
    case 2595:  /* aarch64_shaddv4hi */
    case 2596:  /* aarch64_uhaddv4hi */
    case 2597:  /* aarch64_srhaddv4hi */
    case 2598:  /* aarch64_urhaddv4hi */
    case 2599:  /* aarch64_shsubv4hi */
    case 2600:  /* aarch64_uhsubv4hi */
    case 2601:  /* aarch64_shaddv8hi */
    case 2602:  /* aarch64_uhaddv8hi */
    case 2603:  /* aarch64_srhaddv8hi */
    case 2604:  /* aarch64_urhaddv8hi */
    case 2605:  /* aarch64_shsubv8hi */
    case 2606:  /* aarch64_uhsubv8hi */
    case 2607:  /* aarch64_shaddv2si */
    case 2608:  /* aarch64_uhaddv2si */
    case 2609:  /* aarch64_srhaddv2si */
    case 2610:  /* aarch64_urhaddv2si */
    case 2611:  /* aarch64_shsubv2si */
    case 2612:  /* aarch64_uhsubv2si */
    case 2613:  /* aarch64_shaddv4si */
    case 2614:  /* aarch64_uhaddv4si */
    case 2615:  /* aarch64_srhaddv4si */
    case 2616:  /* aarch64_urhaddv4si */
    case 2617:  /* aarch64_shsubv4si */
    case 2618:  /* aarch64_uhsubv4si */
    case 2619:  /* aarch64_addhnv8hi */
    case 2620:  /* aarch64_raddhnv8hi */
    case 2621:  /* aarch64_subhnv8hi */
    case 2622:  /* aarch64_rsubhnv8hi */
    case 2623:  /* aarch64_addhnv4si */
    case 2624:  /* aarch64_raddhnv4si */
    case 2625:  /* aarch64_subhnv4si */
    case 2626:  /* aarch64_rsubhnv4si */
    case 2627:  /* aarch64_addhnv2di */
    case 2628:  /* aarch64_raddhnv2di */
    case 2629:  /* aarch64_subhnv2di */
    case 2630:  /* aarch64_rsubhnv2di */
    case 2631:  /* aarch64_addhn2v8hi */
    case 2632:  /* aarch64_raddhn2v8hi */
    case 2633:  /* aarch64_subhn2v8hi */
    case 2634:  /* aarch64_rsubhn2v8hi */
    case 2635:  /* aarch64_addhn2v4si */
    case 2636:  /* aarch64_raddhn2v4si */
    case 2637:  /* aarch64_subhn2v4si */
    case 2638:  /* aarch64_rsubhn2v4si */
    case 2639:  /* aarch64_addhn2v2di */
    case 2640:  /* aarch64_raddhn2v2di */
    case 2641:  /* aarch64_subhn2v2di */
    case 2642:  /* aarch64_rsubhn2v2di */
    case 2643:  /* aarch64_pmulv8qi */
    case 2644:  /* aarch64_pmulv16qi */
    case 2645:  /* aarch64_fmulxv4hf */
    case 2646:  /* aarch64_fmulxv8hf */
    case 2647:  /* aarch64_fmulxv2sf */
    case 2648:  /* aarch64_fmulxv4sf */
    case 2649:  /* aarch64_fmulxv2df */
    case 2650:  /* aarch64_fmulxhf */
    case 2651:  /* aarch64_fmulxsf */
    case 2652:  /* aarch64_fmulxdf */
    case 2653:  /* *aarch64_mulx_elt_to_128v2sf */
    case 2654:  /* *aarch64_mulx_elt_to_64v4sf */
    case 2655:  /* *aarch64_mulx_eltv2sf */
    case 2656:  /* *aarch64_mulx_eltv4sf */
    case 2657:  /* *aarch64_mulx_eltv2df */
    case 2658:  /* *aarch64_mulx_elt_from_dupv4hf */
    case 2659:  /* *aarch64_mulx_elt_from_dupv8hf */
    case 2660:  /* *aarch64_mulx_elt_from_dupv2sf */
    case 2661:  /* *aarch64_mulx_elt_from_dupv4sf */
    case 2662:  /* *aarch64_mulx_elt_from_dupv2df */
    case 2663:  /* *aarch64_vgetfmulxv2sf */
    case 2664:  /* *aarch64_vgetfmulxv4sf */
    case 2665:  /* *aarch64_vgetfmulxv2df */
    case 2666:  /* aarch64_sqaddv8qi */
    case 2667:  /* aarch64_uqaddv8qi */
    case 2668:  /* aarch64_sqsubv8qi */
    case 2669:  /* aarch64_uqsubv8qi */
    case 2670:  /* aarch64_sqaddv16qi */
    case 2671:  /* aarch64_uqaddv16qi */
    case 2672:  /* aarch64_sqsubv16qi */
    case 2673:  /* aarch64_uqsubv16qi */
    case 2674:  /* aarch64_sqaddv4hi */
    case 2675:  /* aarch64_uqaddv4hi */
    case 2676:  /* aarch64_sqsubv4hi */
    case 2677:  /* aarch64_uqsubv4hi */
    case 2678:  /* aarch64_sqaddv8hi */
    case 2679:  /* aarch64_uqaddv8hi */
    case 2680:  /* aarch64_sqsubv8hi */
    case 2681:  /* aarch64_uqsubv8hi */
    case 2682:  /* aarch64_sqaddv2si */
    case 2683:  /* aarch64_uqaddv2si */
    case 2684:  /* aarch64_sqsubv2si */
    case 2685:  /* aarch64_uqsubv2si */
    case 2686:  /* aarch64_sqaddv4si */
    case 2687:  /* aarch64_uqaddv4si */
    case 2688:  /* aarch64_sqsubv4si */
    case 2689:  /* aarch64_uqsubv4si */
    case 2690:  /* aarch64_sqaddv2di */
    case 2691:  /* aarch64_uqaddv2di */
    case 2692:  /* aarch64_sqsubv2di */
    case 2693:  /* aarch64_uqsubv2di */
    case 2694:  /* aarch64_sqaddqi */
    case 2695:  /* aarch64_uqaddqi */
    case 2696:  /* aarch64_sqsubqi */
    case 2697:  /* aarch64_uqsubqi */
    case 2698:  /* aarch64_sqaddhi */
    case 2699:  /* aarch64_uqaddhi */
    case 2700:  /* aarch64_sqsubhi */
    case 2701:  /* aarch64_uqsubhi */
    case 2702:  /* aarch64_sqaddsi */
    case 2703:  /* aarch64_uqaddsi */
    case 2704:  /* aarch64_sqsubsi */
    case 2705:  /* aarch64_uqsubsi */
    case 2706:  /* aarch64_sqadddi */
    case 2707:  /* aarch64_uqadddi */
    case 2708:  /* aarch64_sqsubdi */
    case 2709:  /* aarch64_uqsubdi */
    case 2710:  /* aarch64_suqaddv8qi */
    case 2711:  /* aarch64_usqaddv8qi */
    case 2712:  /* aarch64_suqaddv16qi */
    case 2713:  /* aarch64_usqaddv16qi */
    case 2714:  /* aarch64_suqaddv4hi */
    case 2715:  /* aarch64_usqaddv4hi */
    case 2716:  /* aarch64_suqaddv8hi */
    case 2717:  /* aarch64_usqaddv8hi */
    case 2718:  /* aarch64_suqaddv2si */
    case 2719:  /* aarch64_usqaddv2si */
    case 2720:  /* aarch64_suqaddv4si */
    case 2721:  /* aarch64_usqaddv4si */
    case 2722:  /* aarch64_suqaddv2di */
    case 2723:  /* aarch64_usqaddv2di */
    case 2724:  /* aarch64_suqaddqi */
    case 2725:  /* aarch64_usqaddqi */
    case 2726:  /* aarch64_suqaddhi */
    case 2727:  /* aarch64_usqaddhi */
    case 2728:  /* aarch64_suqaddsi */
    case 2729:  /* aarch64_usqaddsi */
    case 2730:  /* aarch64_suqadddi */
    case 2731:  /* aarch64_usqadddi */
    case 2732:  /* aarch64_sqmovunv8hi */
    case 2733:  /* aarch64_sqmovunv4si */
    case 2734:  /* aarch64_sqmovunv2di */
    case 2735:  /* aarch64_sqmovunhi */
    case 2736:  /* aarch64_sqmovunsi */
    case 2737:  /* aarch64_sqmovundi */
    case 2738:  /* aarch64_sqmovnv8hi */
    case 2739:  /* aarch64_uqmovnv8hi */
    case 2740:  /* aarch64_sqmovnv4si */
    case 2741:  /* aarch64_uqmovnv4si */
    case 2742:  /* aarch64_sqmovnv2di */
    case 2743:  /* aarch64_uqmovnv2di */
    case 2744:  /* aarch64_sqmovnhi */
    case 2745:  /* aarch64_uqmovnhi */
    case 2746:  /* aarch64_sqmovnsi */
    case 2747:  /* aarch64_uqmovnsi */
    case 2748:  /* aarch64_sqmovndi */
    case 2749:  /* aarch64_uqmovndi */
    case 2750:  /* aarch64_sqxtn2v8hi_le */
    case 2751:  /* aarch64_uqxtn2v8hi_le */
    case 2752:  /* aarch64_sqxtn2v4si_le */
    case 2753:  /* aarch64_uqxtn2v4si_le */
    case 2754:  /* aarch64_sqxtn2v2di_le */
    case 2755:  /* aarch64_uqxtn2v2di_le */
    case 2756:  /* aarch64_sqxtn2v8hi_be */
    case 2757:  /* aarch64_uqxtn2v8hi_be */
    case 2758:  /* aarch64_sqxtn2v4si_be */
    case 2759:  /* aarch64_uqxtn2v4si_be */
    case 2760:  /* aarch64_sqxtn2v2di_be */
    case 2761:  /* aarch64_uqxtn2v2di_be */
    case 2762:  /* aarch64_sqxtun2v8hi_le */
    case 2763:  /* aarch64_sqxtun2v4si_le */
    case 2764:  /* aarch64_sqxtun2v2di_le */
    case 2765:  /* aarch64_sqxtun2v8hi_be */
    case 2766:  /* aarch64_sqxtun2v4si_be */
    case 2767:  /* aarch64_sqxtun2v2di_be */
    case 2768:  /* aarch64_sqnegv8qi */
    case 2769:  /* aarch64_sqabsv8qi */
    case 2770:  /* aarch64_sqnegv16qi */
    case 2771:  /* aarch64_sqabsv16qi */
    case 2772:  /* aarch64_sqnegv4hi */
    case 2773:  /* aarch64_sqabsv4hi */
    case 2774:  /* aarch64_sqnegv8hi */
    case 2775:  /* aarch64_sqabsv8hi */
    case 2776:  /* aarch64_sqnegv2si */
    case 2777:  /* aarch64_sqabsv2si */
    case 2778:  /* aarch64_sqnegv4si */
    case 2779:  /* aarch64_sqabsv4si */
    case 2780:  /* aarch64_sqnegv2di */
    case 2781:  /* aarch64_sqabsv2di */
    case 2782:  /* aarch64_sqnegqi */
    case 2783:  /* aarch64_sqabsqi */
    case 2784:  /* aarch64_sqneghi */
    case 2785:  /* aarch64_sqabshi */
    case 2786:  /* aarch64_sqnegsi */
    case 2787:  /* aarch64_sqabssi */
    case 2788:  /* aarch64_sqnegdi */
    case 2789:  /* aarch64_sqabsdi */
    case 2790:  /* aarch64_sqdmulhv4hi */
    case 2791:  /* aarch64_sqrdmulhv4hi */
    case 2792:  /* aarch64_sqdmulhv8hi */
    case 2793:  /* aarch64_sqrdmulhv8hi */
    case 2794:  /* aarch64_sqdmulhv2si */
    case 2795:  /* aarch64_sqrdmulhv2si */
    case 2796:  /* aarch64_sqdmulhv4si */
    case 2797:  /* aarch64_sqrdmulhv4si */
    case 2798:  /* aarch64_sqdmulhhi */
    case 2799:  /* aarch64_sqrdmulhhi */
    case 2800:  /* aarch64_sqdmulhsi */
    case 2801:  /* aarch64_sqrdmulhsi */
    case 2802:  /* aarch64_sqdmulh_lanev4hi */
    case 2803:  /* aarch64_sqrdmulh_lanev4hi */
    case 2804:  /* aarch64_sqdmulh_lanev8hi */
    case 2805:  /* aarch64_sqrdmulh_lanev8hi */
    case 2806:  /* aarch64_sqdmulh_lanev2si */
    case 2807:  /* aarch64_sqrdmulh_lanev2si */
    case 2808:  /* aarch64_sqdmulh_lanev4si */
    case 2809:  /* aarch64_sqrdmulh_lanev4si */
    case 2810:  /* aarch64_sqdmulh_laneqv4hi */
    case 2811:  /* aarch64_sqrdmulh_laneqv4hi */
    case 2812:  /* aarch64_sqdmulh_laneqv8hi */
    case 2813:  /* aarch64_sqrdmulh_laneqv8hi */
    case 2814:  /* aarch64_sqdmulh_laneqv2si */
    case 2815:  /* aarch64_sqrdmulh_laneqv2si */
    case 2816:  /* aarch64_sqdmulh_laneqv4si */
    case 2817:  /* aarch64_sqrdmulh_laneqv4si */
    case 2818:  /* aarch64_sqdmulh_lanehi */
    case 2819:  /* aarch64_sqrdmulh_lanehi */
    case 2820:  /* aarch64_sqdmulh_lanesi */
    case 2821:  /* aarch64_sqrdmulh_lanesi */
    case 2822:  /* aarch64_sqdmulh_laneqhi */
    case 2823:  /* aarch64_sqrdmulh_laneqhi */
    case 2824:  /* aarch64_sqdmulh_laneqsi */
    case 2825:  /* aarch64_sqrdmulh_laneqsi */
    case 2826:  /* aarch64_sqrdmlahv4hi */
    case 2827:  /* aarch64_sqrdmlshv4hi */
    case 2828:  /* aarch64_sqrdmlahv8hi */
    case 2829:  /* aarch64_sqrdmlshv8hi */
    case 2830:  /* aarch64_sqrdmlahv2si */
    case 2831:  /* aarch64_sqrdmlshv2si */
    case 2832:  /* aarch64_sqrdmlahv4si */
    case 2833:  /* aarch64_sqrdmlshv4si */
    case 2834:  /* aarch64_sqrdmlahhi */
    case 2835:  /* aarch64_sqrdmlshhi */
    case 2836:  /* aarch64_sqrdmlahsi */
    case 2837:  /* aarch64_sqrdmlshsi */
    case 2838:  /* aarch64_sqrdmlah_lanev4hi */
    case 2839:  /* aarch64_sqrdmlsh_lanev4hi */
    case 2840:  /* aarch64_sqrdmlah_lanev8hi */
    case 2841:  /* aarch64_sqrdmlsh_lanev8hi */
    case 2842:  /* aarch64_sqrdmlah_lanev2si */
    case 2843:  /* aarch64_sqrdmlsh_lanev2si */
    case 2844:  /* aarch64_sqrdmlah_lanev4si */
    case 2845:  /* aarch64_sqrdmlsh_lanev4si */
    case 2846:  /* aarch64_sqrdmlah_lanehi */
    case 2847:  /* aarch64_sqrdmlsh_lanehi */
    case 2848:  /* aarch64_sqrdmlah_lanesi */
    case 2849:  /* aarch64_sqrdmlsh_lanesi */
    case 2850:  /* aarch64_sqrdmlah_laneqv4hi */
    case 2851:  /* aarch64_sqrdmlsh_laneqv4hi */
    case 2852:  /* aarch64_sqrdmlah_laneqv8hi */
    case 2853:  /* aarch64_sqrdmlsh_laneqv8hi */
    case 2854:  /* aarch64_sqrdmlah_laneqv2si */
    case 2855:  /* aarch64_sqrdmlsh_laneqv2si */
    case 2856:  /* aarch64_sqrdmlah_laneqv4si */
    case 2857:  /* aarch64_sqrdmlsh_laneqv4si */
    case 2858:  /* aarch64_sqrdmlah_laneqhi */
    case 2859:  /* aarch64_sqrdmlsh_laneqhi */
    case 2860:  /* aarch64_sqrdmlah_laneqsi */
    case 2861:  /* aarch64_sqrdmlsh_laneqsi */
    case 2862:  /* aarch64_sqdmlalv4hi */
    case 2863:  /* aarch64_sqdmlalv2si */
    case 2864:  /* aarch64_sqdmlalhi */
    case 2865:  /* aarch64_sqdmlalsi */
    case 2866:  /* aarch64_sqdmlslv4hi */
    case 2867:  /* aarch64_sqdmlslv2si */
    case 2868:  /* aarch64_sqdmlslhi */
    case 2869:  /* aarch64_sqdmlslsi */
    case 2870:  /* aarch64_sqdmlal_lanev4hi */
    case 2871:  /* aarch64_sqdmlal_lanev2si */
    case 2872:  /* aarch64_sqdmlsl_lanev4hi */
    case 2873:  /* aarch64_sqdmlsl_lanev2si */
    case 2874:  /* aarch64_sqdmlsl_laneqv4hi */
    case 2875:  /* aarch64_sqdmlsl_laneqv2si */
    case 2876:  /* aarch64_sqdmlal_laneqv4hi */
    case 2877:  /* aarch64_sqdmlal_laneqv2si */
    case 2878:  /* aarch64_sqdmlal_lanehi */
    case 2879:  /* aarch64_sqdmlal_lanesi */
    case 2880:  /* aarch64_sqdmlsl_lanehi */
    case 2881:  /* aarch64_sqdmlsl_lanesi */
    case 2882:  /* aarch64_sqdmlal_laneqhi */
    case 2883:  /* aarch64_sqdmlal_laneqsi */
    case 2884:  /* aarch64_sqdmlsl_laneqhi */
    case 2885:  /* aarch64_sqdmlsl_laneqsi */
    case 2886:  /* aarch64_sqdmlsl_nv4hi */
    case 2887:  /* aarch64_sqdmlsl_nv2si */
    case 2888:  /* aarch64_sqdmlal_nv4hi */
    case 2889:  /* aarch64_sqdmlal_nv2si */
    case 2890:  /* aarch64_sqdmlal2v8hi_internal */
    case 2891:  /* aarch64_sqdmlal2v4si_internal */
    case 2892:  /* aarch64_sqdmlsl2v8hi_internal */
    case 2893:  /* aarch64_sqdmlsl2v4si_internal */
    case 2894:  /* aarch64_sqdmlal2_lanev8hi_internal */
    case 2895:  /* aarch64_sqdmlsl2_lanev8hi_internal */
    case 2896:  /* aarch64_sqdmlal2_lanev4si_internal */
    case 2897:  /* aarch64_sqdmlsl2_lanev4si_internal */
    case 2898:  /* aarch64_sqdmlal2_laneqv8hi_internal */
    case 2899:  /* aarch64_sqdmlsl2_laneqv8hi_internal */
    case 2900:  /* aarch64_sqdmlal2_laneqv4si_internal */
    case 2901:  /* aarch64_sqdmlsl2_laneqv4si_internal */
    case 2902:  /* aarch64_sqdmlal2_nv8hi_internal */
    case 2903:  /* aarch64_sqdmlsl2_nv8hi_internal */
    case 2904:  /* aarch64_sqdmlal2_nv4si_internal */
    case 2905:  /* aarch64_sqdmlsl2_nv4si_internal */
    case 2906:  /* aarch64_sqdmullv4hi */
    case 2907:  /* aarch64_sqdmullv2si */
    case 2908:  /* aarch64_sqdmullhi */
    case 2909:  /* aarch64_sqdmullsi */
    case 2910:  /* aarch64_sqdmull_lanev4hi */
    case 2911:  /* aarch64_sqdmull_lanev2si */
    case 2912:  /* aarch64_sqdmull_laneqv4hi */
    case 2913:  /* aarch64_sqdmull_laneqv2si */
    case 2914:  /* aarch64_sqdmull_lanehi */
    case 2915:  /* aarch64_sqdmull_lanesi */
    case 2916:  /* aarch64_sqdmull_laneqhi */
    case 2917:  /* aarch64_sqdmull_laneqsi */
    case 2918:  /* aarch64_sqdmull_nv4hi */
    case 2919:  /* aarch64_sqdmull_nv2si */
    case 2920:  /* aarch64_sqdmull2v8hi_internal */
    case 2921:  /* aarch64_sqdmull2v4si_internal */
    case 2922:  /* aarch64_sqdmull2_lanev8hi_internal */
    case 2923:  /* aarch64_sqdmull2_lanev4si_internal */
    case 2924:  /* aarch64_sqdmull2_laneqv8hi_internal */
    case 2925:  /* aarch64_sqdmull2_laneqv4si_internal */
    case 2926:  /* aarch64_sqdmull2_nv8hi_internal */
    case 2927:  /* aarch64_sqdmull2_nv4si_internal */
    case 2928:  /* aarch64_sshlv8qi */
    case 2929:  /* aarch64_ushlv8qi */
    case 2930:  /* aarch64_srshlv8qi */
    case 2931:  /* aarch64_urshlv8qi */
    case 2932:  /* aarch64_sshlv16qi */
    case 2933:  /* aarch64_ushlv16qi */
    case 2934:  /* aarch64_srshlv16qi */
    case 2935:  /* aarch64_urshlv16qi */
    case 2936:  /* aarch64_sshlv4hi */
    case 2937:  /* aarch64_ushlv4hi */
    case 2938:  /* aarch64_srshlv4hi */
    case 2939:  /* aarch64_urshlv4hi */
    case 2940:  /* aarch64_sshlv8hi */
    case 2941:  /* aarch64_ushlv8hi */
    case 2942:  /* aarch64_srshlv8hi */
    case 2943:  /* aarch64_urshlv8hi */
    case 2944:  /* aarch64_sshlv2si */
    case 2945:  /* aarch64_ushlv2si */
    case 2946:  /* aarch64_srshlv2si */
    case 2947:  /* aarch64_urshlv2si */
    case 2948:  /* aarch64_sshlv4si */
    case 2949:  /* aarch64_ushlv4si */
    case 2950:  /* aarch64_srshlv4si */
    case 2951:  /* aarch64_urshlv4si */
    case 2952:  /* aarch64_sshlv2di */
    case 2953:  /* aarch64_ushlv2di */
    case 2954:  /* aarch64_srshlv2di */
    case 2955:  /* aarch64_urshlv2di */
    case 2956:  /* aarch64_sshldi */
    case 2957:  /* aarch64_ushldi */
    case 2958:  /* aarch64_srshldi */
    case 2959:  /* aarch64_urshldi */
    case 2960:  /* aarch64_sqshlv8qi */
    case 2961:  /* aarch64_uqshlv8qi */
    case 2962:  /* aarch64_sqrshlv8qi */
    case 2963:  /* aarch64_uqrshlv8qi */
    case 2964:  /* aarch64_sqshlv16qi */
    case 2965:  /* aarch64_uqshlv16qi */
    case 2966:  /* aarch64_sqrshlv16qi */
    case 2967:  /* aarch64_uqrshlv16qi */
    case 2968:  /* aarch64_sqshlv4hi */
    case 2969:  /* aarch64_uqshlv4hi */
    case 2970:  /* aarch64_sqrshlv4hi */
    case 2971:  /* aarch64_uqrshlv4hi */
    case 2972:  /* aarch64_sqshlv8hi */
    case 2973:  /* aarch64_uqshlv8hi */
    case 2974:  /* aarch64_sqrshlv8hi */
    case 2975:  /* aarch64_uqrshlv8hi */
    case 2976:  /* aarch64_sqshlv2si */
    case 2977:  /* aarch64_uqshlv2si */
    case 2978:  /* aarch64_sqrshlv2si */
    case 2979:  /* aarch64_uqrshlv2si */
    case 2980:  /* aarch64_sqshlv4si */
    case 2981:  /* aarch64_uqshlv4si */
    case 2982:  /* aarch64_sqrshlv4si */
    case 2983:  /* aarch64_uqrshlv4si */
    case 2984:  /* aarch64_sqshlv2di */
    case 2985:  /* aarch64_uqshlv2di */
    case 2986:  /* aarch64_sqrshlv2di */
    case 2987:  /* aarch64_uqrshlv2di */
    case 2988:  /* aarch64_sqshlqi */
    case 2989:  /* aarch64_uqshlqi */
    case 2990:  /* aarch64_sqrshlqi */
    case 2991:  /* aarch64_uqrshlqi */
    case 2992:  /* aarch64_sqshlhi */
    case 2993:  /* aarch64_uqshlhi */
    case 2994:  /* aarch64_sqrshlhi */
    case 2995:  /* aarch64_uqrshlhi */
    case 2996:  /* aarch64_sqshlsi */
    case 2997:  /* aarch64_uqshlsi */
    case 2998:  /* aarch64_sqrshlsi */
    case 2999:  /* aarch64_uqrshlsi */
    case 3000:  /* aarch64_sqshldi */
    case 3001:  /* aarch64_uqshldi */
    case 3002:  /* aarch64_sqrshldi */
    case 3003:  /* aarch64_uqrshldi */
    case 3004:  /* aarch64_sshllv16qi_internal */
    case 3005:  /* aarch64_ushllv16qi_internal */
    case 3006:  /* aarch64_sshllv8hi_internal */
    case 3007:  /* aarch64_ushllv8hi_internal */
    case 3008:  /* aarch64_sshllv4si_internal */
    case 3009:  /* aarch64_ushllv4si_internal */
    case 3010:  /* aarch64_sshll2v16qi_internal */
    case 3011:  /* aarch64_ushll2v16qi_internal */
    case 3012:  /* aarch64_sshll2v8hi_internal */
    case 3013:  /* aarch64_ushll2v8hi_internal */
    case 3014:  /* aarch64_sshll2v4si_internal */
    case 3015:  /* aarch64_ushll2v4si_internal */
    case 3016:  /* aarch64_sshll_nv8qi */
    case 3017:  /* aarch64_ushll_nv8qi */
    case 3018:  /* aarch64_sshll_nv4hi */
    case 3019:  /* aarch64_ushll_nv4hi */
    case 3020:  /* aarch64_sshll_nv2si */
    case 3021:  /* aarch64_ushll_nv2si */
    case 3022:  /* aarch64_sshll2_nv16qi */
    case 3023:  /* aarch64_ushll2_nv16qi */
    case 3024:  /* aarch64_sshll2_nv8hi */
    case 3025:  /* aarch64_ushll2_nv8hi */
    case 3026:  /* aarch64_sshll2_nv4si */
    case 3027:  /* aarch64_ushll2_nv4si */
    case 3028:  /* aarch64_srshr_nv8qi */
    case 3029:  /* aarch64_urshr_nv8qi */
    case 3030:  /* aarch64_srshr_nv16qi */
    case 3031:  /* aarch64_urshr_nv16qi */
    case 3032:  /* aarch64_srshr_nv4hi */
    case 3033:  /* aarch64_urshr_nv4hi */
    case 3034:  /* aarch64_srshr_nv8hi */
    case 3035:  /* aarch64_urshr_nv8hi */
    case 3036:  /* aarch64_srshr_nv2si */
    case 3037:  /* aarch64_urshr_nv2si */
    case 3038:  /* aarch64_srshr_nv4si */
    case 3039:  /* aarch64_urshr_nv4si */
    case 3040:  /* aarch64_srshr_nv2di */
    case 3041:  /* aarch64_urshr_nv2di */
    case 3042:  /* aarch64_srshr_ndi */
    case 3043:  /* aarch64_urshr_ndi */
    case 3044:  /* aarch64_ssra_nv8qi */
    case 3045:  /* aarch64_usra_nv8qi */
    case 3046:  /* aarch64_srsra_nv8qi */
    case 3047:  /* aarch64_ursra_nv8qi */
    case 3048:  /* aarch64_ssra_nv16qi */
    case 3049:  /* aarch64_usra_nv16qi */
    case 3050:  /* aarch64_srsra_nv16qi */
    case 3051:  /* aarch64_ursra_nv16qi */
    case 3052:  /* aarch64_ssra_nv4hi */
    case 3053:  /* aarch64_usra_nv4hi */
    case 3054:  /* aarch64_srsra_nv4hi */
    case 3055:  /* aarch64_ursra_nv4hi */
    case 3056:  /* aarch64_ssra_nv8hi */
    case 3057:  /* aarch64_usra_nv8hi */
    case 3058:  /* aarch64_srsra_nv8hi */
    case 3059:  /* aarch64_ursra_nv8hi */
    case 3060:  /* aarch64_ssra_nv2si */
    case 3061:  /* aarch64_usra_nv2si */
    case 3062:  /* aarch64_srsra_nv2si */
    case 3063:  /* aarch64_ursra_nv2si */
    case 3064:  /* aarch64_ssra_nv4si */
    case 3065:  /* aarch64_usra_nv4si */
    case 3066:  /* aarch64_srsra_nv4si */
    case 3067:  /* aarch64_ursra_nv4si */
    case 3068:  /* aarch64_ssra_nv2di */
    case 3069:  /* aarch64_usra_nv2di */
    case 3070:  /* aarch64_srsra_nv2di */
    case 3071:  /* aarch64_ursra_nv2di */
    case 3072:  /* aarch64_ssra_ndi */
    case 3073:  /* aarch64_usra_ndi */
    case 3074:  /* aarch64_srsra_ndi */
    case 3075:  /* aarch64_ursra_ndi */
    case 3076:  /* aarch64_ssli_nv8qi */
    case 3077:  /* aarch64_usli_nv8qi */
    case 3078:  /* aarch64_ssri_nv8qi */
    case 3079:  /* aarch64_usri_nv8qi */
    case 3080:  /* aarch64_ssli_nv16qi */
    case 3081:  /* aarch64_usli_nv16qi */
    case 3082:  /* aarch64_ssri_nv16qi */
    case 3083:  /* aarch64_usri_nv16qi */
    case 3084:  /* aarch64_ssli_nv4hi */
    case 3085:  /* aarch64_usli_nv4hi */
    case 3086:  /* aarch64_ssri_nv4hi */
    case 3087:  /* aarch64_usri_nv4hi */
    case 3088:  /* aarch64_ssli_nv8hi */
    case 3089:  /* aarch64_usli_nv8hi */
    case 3090:  /* aarch64_ssri_nv8hi */
    case 3091:  /* aarch64_usri_nv8hi */
    case 3092:  /* aarch64_ssli_nv2si */
    case 3093:  /* aarch64_usli_nv2si */
    case 3094:  /* aarch64_ssri_nv2si */
    case 3095:  /* aarch64_usri_nv2si */
    case 3096:  /* aarch64_ssli_nv4si */
    case 3097:  /* aarch64_usli_nv4si */
    case 3098:  /* aarch64_ssri_nv4si */
    case 3099:  /* aarch64_usri_nv4si */
    case 3100:  /* aarch64_ssli_nv2di */
    case 3101:  /* aarch64_usli_nv2di */
    case 3102:  /* aarch64_ssri_nv2di */
    case 3103:  /* aarch64_usri_nv2di */
    case 3104:  /* aarch64_ssli_ndi */
    case 3105:  /* aarch64_usli_ndi */
    case 3106:  /* aarch64_ssri_ndi */
    case 3107:  /* aarch64_usri_ndi */
    case 3108:  /* aarch64_sqshlu_nv8qi */
    case 3109:  /* aarch64_sqshl_nv8qi */
    case 3110:  /* aarch64_uqshl_nv8qi */
    case 3111:  /* aarch64_sqshlu_nv16qi */
    case 3112:  /* aarch64_sqshl_nv16qi */
    case 3113:  /* aarch64_uqshl_nv16qi */
    case 3114:  /* aarch64_sqshlu_nv4hi */
    case 3115:  /* aarch64_sqshl_nv4hi */
    case 3116:  /* aarch64_uqshl_nv4hi */
    case 3117:  /* aarch64_sqshlu_nv8hi */
    case 3118:  /* aarch64_sqshl_nv8hi */
    case 3119:  /* aarch64_uqshl_nv8hi */
    case 3120:  /* aarch64_sqshlu_nv2si */
    case 3121:  /* aarch64_sqshl_nv2si */
    case 3122:  /* aarch64_uqshl_nv2si */
    case 3123:  /* aarch64_sqshlu_nv4si */
    case 3124:  /* aarch64_sqshl_nv4si */
    case 3125:  /* aarch64_uqshl_nv4si */
    case 3126:  /* aarch64_sqshlu_nv2di */
    case 3127:  /* aarch64_sqshl_nv2di */
    case 3128:  /* aarch64_uqshl_nv2di */
    case 3129:  /* aarch64_sqshlu_nqi */
    case 3130:  /* aarch64_sqshl_nqi */
    case 3131:  /* aarch64_uqshl_nqi */
    case 3132:  /* aarch64_sqshlu_nhi */
    case 3133:  /* aarch64_sqshl_nhi */
    case 3134:  /* aarch64_uqshl_nhi */
    case 3135:  /* aarch64_sqshlu_nsi */
    case 3136:  /* aarch64_sqshl_nsi */
    case 3137:  /* aarch64_uqshl_nsi */
    case 3138:  /* aarch64_sqshlu_ndi */
    case 3139:  /* aarch64_sqshl_ndi */
    case 3140:  /* aarch64_uqshl_ndi */
    case 3141:  /* aarch64_sqshrun_nv8hi */
    case 3142:  /* aarch64_sqrshrun_nv8hi */
    case 3143:  /* aarch64_sqshrn_nv8hi */
    case 3144:  /* aarch64_uqshrn_nv8hi */
    case 3145:  /* aarch64_sqrshrn_nv8hi */
    case 3146:  /* aarch64_uqrshrn_nv8hi */
    case 3147:  /* aarch64_sqshrun_nv4si */
    case 3148:  /* aarch64_sqrshrun_nv4si */
    case 3149:  /* aarch64_sqshrn_nv4si */
    case 3150:  /* aarch64_uqshrn_nv4si */
    case 3151:  /* aarch64_sqrshrn_nv4si */
    case 3152:  /* aarch64_uqrshrn_nv4si */
    case 3153:  /* aarch64_sqshrun_nv2di */
    case 3154:  /* aarch64_sqrshrun_nv2di */
    case 3155:  /* aarch64_sqshrn_nv2di */
    case 3156:  /* aarch64_uqshrn_nv2di */
    case 3157:  /* aarch64_sqrshrn_nv2di */
    case 3158:  /* aarch64_uqrshrn_nv2di */
    case 3159:  /* aarch64_sqshrun_nhi */
    case 3160:  /* aarch64_sqrshrun_nhi */
    case 3161:  /* aarch64_sqshrn_nhi */
    case 3162:  /* aarch64_uqshrn_nhi */
    case 3163:  /* aarch64_sqrshrn_nhi */
    case 3164:  /* aarch64_uqrshrn_nhi */
    case 3165:  /* aarch64_sqshrun_nsi */
    case 3166:  /* aarch64_sqrshrun_nsi */
    case 3167:  /* aarch64_sqshrn_nsi */
    case 3168:  /* aarch64_uqshrn_nsi */
    case 3169:  /* aarch64_sqrshrn_nsi */
    case 3170:  /* aarch64_uqrshrn_nsi */
    case 3171:  /* aarch64_sqshrun_ndi */
    case 3172:  /* aarch64_sqrshrun_ndi */
    case 3173:  /* aarch64_sqshrn_ndi */
    case 3174:  /* aarch64_uqshrn_ndi */
    case 3175:  /* aarch64_sqrshrn_ndi */
    case 3176:  /* aarch64_uqrshrn_ndi */
    case 3177:  /* aarch64_sqshrun2_nv8hi */
    case 3178:  /* aarch64_sqrshrun2_nv8hi */
    case 3179:  /* aarch64_sqshrn2_nv8hi */
    case 3180:  /* aarch64_uqshrn2_nv8hi */
    case 3181:  /* aarch64_sqrshrn2_nv8hi */
    case 3182:  /* aarch64_uqrshrn2_nv8hi */
    case 3183:  /* aarch64_sqshrun2_nv4si */
    case 3184:  /* aarch64_sqrshrun2_nv4si */
    case 3185:  /* aarch64_sqshrn2_nv4si */
    case 3186:  /* aarch64_uqshrn2_nv4si */
    case 3187:  /* aarch64_sqrshrn2_nv4si */
    case 3188:  /* aarch64_uqrshrn2_nv4si */
    case 3189:  /* aarch64_sqshrun2_nv2di */
    case 3190:  /* aarch64_sqrshrun2_nv2di */
    case 3191:  /* aarch64_sqshrn2_nv2di */
    case 3192:  /* aarch64_uqshrn2_nv2di */
    case 3193:  /* aarch64_sqrshrn2_nv2di */
    case 3194:  /* aarch64_uqrshrn2_nv2di */
    case 3195:  /* aarch64_cmltv8qi */
    case 3196:  /* aarch64_cmlev8qi */
    case 3197:  /* aarch64_cmeqv8qi */
    case 3198:  /* aarch64_cmgev8qi */
    case 3199:  /* aarch64_cmgtv8qi */
    case 3200:  /* aarch64_cmltv16qi */
    case 3201:  /* aarch64_cmlev16qi */
    case 3202:  /* aarch64_cmeqv16qi */
    case 3203:  /* aarch64_cmgev16qi */
    case 3204:  /* aarch64_cmgtv16qi */
    case 3205:  /* aarch64_cmltv4hi */
    case 3206:  /* aarch64_cmlev4hi */
    case 3207:  /* aarch64_cmeqv4hi */
    case 3208:  /* aarch64_cmgev4hi */
    case 3209:  /* aarch64_cmgtv4hi */
    case 3210:  /* aarch64_cmltv8hi */
    case 3211:  /* aarch64_cmlev8hi */
    case 3212:  /* aarch64_cmeqv8hi */
    case 3213:  /* aarch64_cmgev8hi */
    case 3214:  /* aarch64_cmgtv8hi */
    case 3215:  /* aarch64_cmltv2si */
    case 3216:  /* aarch64_cmlev2si */
    case 3217:  /* aarch64_cmeqv2si */
    case 3218:  /* aarch64_cmgev2si */
    case 3219:  /* aarch64_cmgtv2si */
    case 3220:  /* aarch64_cmltv4si */
    case 3221:  /* aarch64_cmlev4si */
    case 3222:  /* aarch64_cmeqv4si */
    case 3223:  /* aarch64_cmgev4si */
    case 3224:  /* aarch64_cmgtv4si */
    case 3225:  /* aarch64_cmltv2di */
    case 3226:  /* aarch64_cmlev2di */
    case 3227:  /* aarch64_cmeqv2di */
    case 3228:  /* aarch64_cmgev2di */
    case 3229:  /* aarch64_cmgtv2di */
    case 3230:  /* aarch64_cmltdi */
    case 3231:  /* aarch64_cmledi */
    case 3232:  /* aarch64_cmeqdi */
    case 3233:  /* aarch64_cmgedi */
    case 3234:  /* aarch64_cmgtdi */
    case 3235:  /* *aarch64_cmltdi */
    case 3236:  /* *aarch64_cmledi */
    case 3237:  /* *aarch64_cmeqdi */
    case 3238:  /* *aarch64_cmgedi */
    case 3239:  /* *aarch64_cmgtdi */
    case 3240:  /* aarch64_cmltuv8qi */
    case 3241:  /* aarch64_cmleuv8qi */
    case 3242:  /* aarch64_cmgeuv8qi */
    case 3243:  /* aarch64_cmgtuv8qi */
    case 3244:  /* aarch64_cmltuv16qi */
    case 3245:  /* aarch64_cmleuv16qi */
    case 3246:  /* aarch64_cmgeuv16qi */
    case 3247:  /* aarch64_cmgtuv16qi */
    case 3248:  /* aarch64_cmltuv4hi */
    case 3249:  /* aarch64_cmleuv4hi */
    case 3250:  /* aarch64_cmgeuv4hi */
    case 3251:  /* aarch64_cmgtuv4hi */
    case 3252:  /* aarch64_cmltuv8hi */
    case 3253:  /* aarch64_cmleuv8hi */
    case 3254:  /* aarch64_cmgeuv8hi */
    case 3255:  /* aarch64_cmgtuv8hi */
    case 3256:  /* aarch64_cmltuv2si */
    case 3257:  /* aarch64_cmleuv2si */
    case 3258:  /* aarch64_cmgeuv2si */
    case 3259:  /* aarch64_cmgtuv2si */
    case 3260:  /* aarch64_cmltuv4si */
    case 3261:  /* aarch64_cmleuv4si */
    case 3262:  /* aarch64_cmgeuv4si */
    case 3263:  /* aarch64_cmgtuv4si */
    case 3264:  /* aarch64_cmltuv2di */
    case 3265:  /* aarch64_cmleuv2di */
    case 3266:  /* aarch64_cmgeuv2di */
    case 3267:  /* aarch64_cmgtuv2di */
    case 3268:  /* aarch64_cmltudi */
    case 3269:  /* aarch64_cmleudi */
    case 3270:  /* aarch64_cmgeudi */
    case 3271:  /* aarch64_cmgtudi */
    case 3272:  /* *aarch64_cmltudi */
    case 3273:  /* *aarch64_cmleudi */
    case 3274:  /* *aarch64_cmgeudi */
    case 3275:  /* *aarch64_cmgtudi */
    case 3276:  /* aarch64_cmtstv8qi */
    case 3277:  /* aarch64_cmtstv16qi */
    case 3278:  /* aarch64_cmtstv4hi */
    case 3279:  /* aarch64_cmtstv8hi */
    case 3280:  /* aarch64_cmtstv2si */
    case 3281:  /* aarch64_cmtstv4si */
    case 3282:  /* aarch64_cmtstv2di */
    case 3283:  /* aarch64_cmtstdi */
    case 3284:  /* *aarch64_cmtstdi */
    case 3285:  /* aarch64_cmltv4hf */
    case 3286:  /* aarch64_cmlev4hf */
    case 3287:  /* aarch64_cmeqv4hf */
    case 3288:  /* aarch64_cmgev4hf */
    case 3289:  /* aarch64_cmgtv4hf */
    case 3290:  /* aarch64_cmltv8hf */
    case 3291:  /* aarch64_cmlev8hf */
    case 3292:  /* aarch64_cmeqv8hf */
    case 3293:  /* aarch64_cmgev8hf */
    case 3294:  /* aarch64_cmgtv8hf */
    case 3295:  /* aarch64_cmltv2sf */
    case 3296:  /* aarch64_cmlev2sf */
    case 3297:  /* aarch64_cmeqv2sf */
    case 3298:  /* aarch64_cmgev2sf */
    case 3299:  /* aarch64_cmgtv2sf */
    case 3300:  /* aarch64_cmltv4sf */
    case 3301:  /* aarch64_cmlev4sf */
    case 3302:  /* aarch64_cmeqv4sf */
    case 3303:  /* aarch64_cmgev4sf */
    case 3304:  /* aarch64_cmgtv4sf */
    case 3305:  /* aarch64_cmltv2df */
    case 3306:  /* aarch64_cmlev2df */
    case 3307:  /* aarch64_cmeqv2df */
    case 3308:  /* aarch64_cmgev2df */
    case 3309:  /* aarch64_cmgtv2df */
    case 3310:  /* aarch64_cmlthf */
    case 3311:  /* aarch64_cmlehf */
    case 3312:  /* aarch64_cmeqhf */
    case 3313:  /* aarch64_cmgehf */
    case 3314:  /* aarch64_cmgthf */
    case 3315:  /* aarch64_cmltsf */
    case 3316:  /* aarch64_cmlesf */
    case 3317:  /* aarch64_cmeqsf */
    case 3318:  /* aarch64_cmgesf */
    case 3319:  /* aarch64_cmgtsf */
    case 3320:  /* aarch64_cmltdf */
    case 3321:  /* aarch64_cmledf */
    case 3322:  /* aarch64_cmeqdf */
    case 3323:  /* aarch64_cmgedf */
    case 3324:  /* aarch64_cmgtdf */
    case 3325:  /* aarch64_facltv4hf */
    case 3326:  /* aarch64_faclev4hf */
    case 3327:  /* aarch64_facgev4hf */
    case 3328:  /* aarch64_facgtv4hf */
    case 3329:  /* aarch64_facltv8hf */
    case 3330:  /* aarch64_faclev8hf */
    case 3331:  /* aarch64_facgev8hf */
    case 3332:  /* aarch64_facgtv8hf */
    case 3333:  /* aarch64_facltv2sf */
    case 3334:  /* aarch64_faclev2sf */
    case 3335:  /* aarch64_facgev2sf */
    case 3336:  /* aarch64_facgtv2sf */
    case 3337:  /* aarch64_facltv4sf */
    case 3338:  /* aarch64_faclev4sf */
    case 3339:  /* aarch64_facgev4sf */
    case 3340:  /* aarch64_facgtv4sf */
    case 3341:  /* aarch64_facltv2df */
    case 3342:  /* aarch64_faclev2df */
    case 3343:  /* aarch64_facgev2df */
    case 3344:  /* aarch64_facgtv2df */
    case 3345:  /* aarch64_faclthf */
    case 3346:  /* aarch64_faclehf */
    case 3347:  /* aarch64_facgehf */
    case 3348:  /* aarch64_facgthf */
    case 3349:  /* aarch64_facltsf */
    case 3350:  /* aarch64_faclesf */
    case 3351:  /* aarch64_facgesf */
    case 3352:  /* aarch64_facgtsf */
    case 3353:  /* aarch64_facltdf */
    case 3354:  /* aarch64_facledf */
    case 3355:  /* aarch64_facgedf */
    case 3356:  /* aarch64_facgtdf */
    case 3357:  /* aarch64_addpv8qi */
    case 3358:  /* aarch64_addpv4hi */
    case 3359:  /* aarch64_addpv2si */
    case 3360:  /* aarch64_addpdi */
    case 3361:  /* *sqrtv4hf2 */
    case 3362:  /* *sqrtv8hf2 */
    case 3363:  /* *sqrtv2sf2 */
    case 3364:  /* *sqrtv4sf2 */
    case 3365:  /* *sqrtv2df2 */
    case 3366:  /* aarch64_simd_ld2v16qi */
    case 3367:  /* aarch64_simd_ld2v8hi */
    case 3368:  /* aarch64_simd_ld2v4si */
    case 3369:  /* aarch64_simd_ld2v2di */
    case 3370:  /* aarch64_simd_ld2v8hf */
    case 3371:  /* aarch64_simd_ld2v4sf */
    case 3372:  /* aarch64_simd_ld2v2df */
    case 3373:  /* aarch64_simd_ld2v8bf */
    case 3374:  /* aarch64_simd_ld2rv8qi */
    case 3375:  /* aarch64_simd_ld2rv16qi */
    case 3376:  /* aarch64_simd_ld2rv4hi */
    case 3377:  /* aarch64_simd_ld2rv8hi */
    case 3378:  /* aarch64_simd_ld2rv2si */
    case 3379:  /* aarch64_simd_ld2rv4si */
    case 3380:  /* aarch64_simd_ld2rv4bf */
    case 3381:  /* aarch64_simd_ld2rv8bf */
    case 3382:  /* aarch64_simd_ld2rv2di */
    case 3383:  /* aarch64_simd_ld2rv4hf */
    case 3384:  /* aarch64_simd_ld2rv8hf */
    case 3385:  /* aarch64_simd_ld2rv2sf */
    case 3386:  /* aarch64_simd_ld2rv4sf */
    case 3387:  /* aarch64_simd_ld2rv2df */
    case 3388:  /* aarch64_simd_ld2rdi */
    case 3389:  /* aarch64_simd_ld2rdf */
    case 3390:  /* aarch64_vec_load_lanesoi_lanev8qi */
    case 3391:  /* aarch64_vec_load_lanesoi_lanev16qi */
    case 3392:  /* aarch64_vec_load_lanesoi_lanev4hi */
    case 3393:  /* aarch64_vec_load_lanesoi_lanev8hi */
    case 3394:  /* aarch64_vec_load_lanesoi_lanev2si */
    case 3395:  /* aarch64_vec_load_lanesoi_lanev4si */
    case 3396:  /* aarch64_vec_load_lanesoi_lanev4bf */
    case 3397:  /* aarch64_vec_load_lanesoi_lanev8bf */
    case 3398:  /* aarch64_vec_load_lanesoi_lanev2di */
    case 3399:  /* aarch64_vec_load_lanesoi_lanev4hf */
    case 3400:  /* aarch64_vec_load_lanesoi_lanev8hf */
    case 3401:  /* aarch64_vec_load_lanesoi_lanev2sf */
    case 3402:  /* aarch64_vec_load_lanesoi_lanev4sf */
    case 3403:  /* aarch64_vec_load_lanesoi_lanev2df */
    case 3404:  /* aarch64_vec_load_lanesoi_lanedi */
    case 3405:  /* aarch64_vec_load_lanesoi_lanedf */
    case 3406:  /* aarch64_simd_st2v16qi */
    case 3407:  /* aarch64_simd_st2v8hi */
    case 3408:  /* aarch64_simd_st2v4si */
    case 3409:  /* aarch64_simd_st2v2di */
    case 3410:  /* aarch64_simd_st2v8hf */
    case 3411:  /* aarch64_simd_st2v4sf */
    case 3412:  /* aarch64_simd_st2v2df */
    case 3413:  /* aarch64_simd_st2v8bf */
    case 3414:  /* aarch64_vec_store_lanesoi_lanev8qi */
    case 3415:  /* aarch64_vec_store_lanesoi_lanev16qi */
    case 3416:  /* aarch64_vec_store_lanesoi_lanev4hi */
    case 3417:  /* aarch64_vec_store_lanesoi_lanev8hi */
    case 3418:  /* aarch64_vec_store_lanesoi_lanev2si */
    case 3419:  /* aarch64_vec_store_lanesoi_lanev4si */
    case 3420:  /* aarch64_vec_store_lanesoi_lanev4bf */
    case 3421:  /* aarch64_vec_store_lanesoi_lanev8bf */
    case 3422:  /* aarch64_vec_store_lanesoi_lanev2di */
    case 3423:  /* aarch64_vec_store_lanesoi_lanev4hf */
    case 3424:  /* aarch64_vec_store_lanesoi_lanev8hf */
    case 3425:  /* aarch64_vec_store_lanesoi_lanev2sf */
    case 3426:  /* aarch64_vec_store_lanesoi_lanev4sf */
    case 3427:  /* aarch64_vec_store_lanesoi_lanev2df */
    case 3428:  /* aarch64_vec_store_lanesoi_lanedi */
    case 3429:  /* aarch64_vec_store_lanesoi_lanedf */
    case 3430:  /* aarch64_simd_ld3v16qi */
    case 3431:  /* aarch64_simd_ld3v8hi */
    case 3432:  /* aarch64_simd_ld3v4si */
    case 3433:  /* aarch64_simd_ld3v2di */
    case 3434:  /* aarch64_simd_ld3v8hf */
    case 3435:  /* aarch64_simd_ld3v4sf */
    case 3436:  /* aarch64_simd_ld3v2df */
    case 3437:  /* aarch64_simd_ld3v8bf */
    case 3438:  /* aarch64_simd_ld3rv8qi */
    case 3439:  /* aarch64_simd_ld3rv16qi */
    case 3440:  /* aarch64_simd_ld3rv4hi */
    case 3441:  /* aarch64_simd_ld3rv8hi */
    case 3442:  /* aarch64_simd_ld3rv2si */
    case 3443:  /* aarch64_simd_ld3rv4si */
    case 3444:  /* aarch64_simd_ld3rv4bf */
    case 3445:  /* aarch64_simd_ld3rv8bf */
    case 3446:  /* aarch64_simd_ld3rv2di */
    case 3447:  /* aarch64_simd_ld3rv4hf */
    case 3448:  /* aarch64_simd_ld3rv8hf */
    case 3449:  /* aarch64_simd_ld3rv2sf */
    case 3450:  /* aarch64_simd_ld3rv4sf */
    case 3451:  /* aarch64_simd_ld3rv2df */
    case 3452:  /* aarch64_simd_ld3rdi */
    case 3453:  /* aarch64_simd_ld3rdf */
    case 3454:  /* aarch64_vec_load_lanesci_lanev8qi */
    case 3455:  /* aarch64_vec_load_lanesci_lanev16qi */
    case 3456:  /* aarch64_vec_load_lanesci_lanev4hi */
    case 3457:  /* aarch64_vec_load_lanesci_lanev8hi */
    case 3458:  /* aarch64_vec_load_lanesci_lanev2si */
    case 3459:  /* aarch64_vec_load_lanesci_lanev4si */
    case 3460:  /* aarch64_vec_load_lanesci_lanev4bf */
    case 3461:  /* aarch64_vec_load_lanesci_lanev8bf */
    case 3462:  /* aarch64_vec_load_lanesci_lanev2di */
    case 3463:  /* aarch64_vec_load_lanesci_lanev4hf */
    case 3464:  /* aarch64_vec_load_lanesci_lanev8hf */
    case 3465:  /* aarch64_vec_load_lanesci_lanev2sf */
    case 3466:  /* aarch64_vec_load_lanesci_lanev4sf */
    case 3467:  /* aarch64_vec_load_lanesci_lanev2df */
    case 3468:  /* aarch64_vec_load_lanesci_lanedi */
    case 3469:  /* aarch64_vec_load_lanesci_lanedf */
    case 3470:  /* aarch64_simd_st3v16qi */
    case 3471:  /* aarch64_simd_st3v8hi */
    case 3472:  /* aarch64_simd_st3v4si */
    case 3473:  /* aarch64_simd_st3v2di */
    case 3474:  /* aarch64_simd_st3v8hf */
    case 3475:  /* aarch64_simd_st3v4sf */
    case 3476:  /* aarch64_simd_st3v2df */
    case 3477:  /* aarch64_simd_st3v8bf */
    case 3478:  /* aarch64_vec_store_lanesci_lanev8qi */
    case 3479:  /* aarch64_vec_store_lanesci_lanev16qi */
    case 3480:  /* aarch64_vec_store_lanesci_lanev4hi */
    case 3481:  /* aarch64_vec_store_lanesci_lanev8hi */
    case 3482:  /* aarch64_vec_store_lanesci_lanev2si */
    case 3483:  /* aarch64_vec_store_lanesci_lanev4si */
    case 3484:  /* aarch64_vec_store_lanesci_lanev4bf */
    case 3485:  /* aarch64_vec_store_lanesci_lanev8bf */
    case 3486:  /* aarch64_vec_store_lanesci_lanev2di */
    case 3487:  /* aarch64_vec_store_lanesci_lanev4hf */
    case 3488:  /* aarch64_vec_store_lanesci_lanev8hf */
    case 3489:  /* aarch64_vec_store_lanesci_lanev2sf */
    case 3490:  /* aarch64_vec_store_lanesci_lanev4sf */
    case 3491:  /* aarch64_vec_store_lanesci_lanev2df */
    case 3492:  /* aarch64_vec_store_lanesci_lanedi */
    case 3493:  /* aarch64_vec_store_lanesci_lanedf */
    case 3494:  /* aarch64_simd_ld4v16qi */
    case 3495:  /* aarch64_simd_ld4v8hi */
    case 3496:  /* aarch64_simd_ld4v4si */
    case 3497:  /* aarch64_simd_ld4v2di */
    case 3498:  /* aarch64_simd_ld4v8hf */
    case 3499:  /* aarch64_simd_ld4v4sf */
    case 3500:  /* aarch64_simd_ld4v2df */
    case 3501:  /* aarch64_simd_ld4v8bf */
    case 3502:  /* aarch64_simd_ld4rv8qi */
    case 3503:  /* aarch64_simd_ld4rv16qi */
    case 3504:  /* aarch64_simd_ld4rv4hi */
    case 3505:  /* aarch64_simd_ld4rv8hi */
    case 3506:  /* aarch64_simd_ld4rv2si */
    case 3507:  /* aarch64_simd_ld4rv4si */
    case 3508:  /* aarch64_simd_ld4rv4bf */
    case 3509:  /* aarch64_simd_ld4rv8bf */
    case 3510:  /* aarch64_simd_ld4rv2di */
    case 3511:  /* aarch64_simd_ld4rv4hf */
    case 3512:  /* aarch64_simd_ld4rv8hf */
    case 3513:  /* aarch64_simd_ld4rv2sf */
    case 3514:  /* aarch64_simd_ld4rv4sf */
    case 3515:  /* aarch64_simd_ld4rv2df */
    case 3516:  /* aarch64_simd_ld4rdi */
    case 3517:  /* aarch64_simd_ld4rdf */
    case 3518:  /* aarch64_vec_load_lanesxi_lanev8qi */
    case 3519:  /* aarch64_vec_load_lanesxi_lanev16qi */
    case 3520:  /* aarch64_vec_load_lanesxi_lanev4hi */
    case 3521:  /* aarch64_vec_load_lanesxi_lanev8hi */
    case 3522:  /* aarch64_vec_load_lanesxi_lanev2si */
    case 3523:  /* aarch64_vec_load_lanesxi_lanev4si */
    case 3524:  /* aarch64_vec_load_lanesxi_lanev4bf */
    case 3525:  /* aarch64_vec_load_lanesxi_lanev8bf */
    case 3526:  /* aarch64_vec_load_lanesxi_lanev2di */
    case 3527:  /* aarch64_vec_load_lanesxi_lanev4hf */
    case 3528:  /* aarch64_vec_load_lanesxi_lanev8hf */
    case 3529:  /* aarch64_vec_load_lanesxi_lanev2sf */
    case 3530:  /* aarch64_vec_load_lanesxi_lanev4sf */
    case 3531:  /* aarch64_vec_load_lanesxi_lanev2df */
    case 3532:  /* aarch64_vec_load_lanesxi_lanedi */
    case 3533:  /* aarch64_vec_load_lanesxi_lanedf */
    case 3534:  /* aarch64_simd_st4v16qi */
    case 3535:  /* aarch64_simd_st4v8hi */
    case 3536:  /* aarch64_simd_st4v4si */
    case 3537:  /* aarch64_simd_st4v2di */
    case 3538:  /* aarch64_simd_st4v8hf */
    case 3539:  /* aarch64_simd_st4v4sf */
    case 3540:  /* aarch64_simd_st4v2df */
    case 3541:  /* aarch64_simd_st4v8bf */
    case 3542:  /* aarch64_vec_store_lanesxi_lanev8qi */
    case 3543:  /* aarch64_vec_store_lanesxi_lanev16qi */
    case 3544:  /* aarch64_vec_store_lanesxi_lanev4hi */
    case 3545:  /* aarch64_vec_store_lanesxi_lanev8hi */
    case 3546:  /* aarch64_vec_store_lanesxi_lanev2si */
    case 3547:  /* aarch64_vec_store_lanesxi_lanev4si */
    case 3548:  /* aarch64_vec_store_lanesxi_lanev4bf */
    case 3549:  /* aarch64_vec_store_lanesxi_lanev8bf */
    case 3550:  /* aarch64_vec_store_lanesxi_lanev2di */
    case 3551:  /* aarch64_vec_store_lanesxi_lanev4hf */
    case 3552:  /* aarch64_vec_store_lanesxi_lanev8hf */
    case 3553:  /* aarch64_vec_store_lanesxi_lanev2sf */
    case 3554:  /* aarch64_vec_store_lanesxi_lanev4sf */
    case 3555:  /* aarch64_vec_store_lanesxi_lanev2df */
    case 3556:  /* aarch64_vec_store_lanesxi_lanedi */
    case 3557:  /* aarch64_vec_store_lanesxi_lanedf */
    case 3558:  /* aarch64_rev_reglistoi */
    case 3559:  /* aarch64_rev_reglistci */
    case 3560:  /* aarch64_rev_reglistxi */
    case 3561:  /* aarch64_ld1_x3_v8qi */
    case 3562:  /* aarch64_ld1_x3_v16qi */
    case 3563:  /* aarch64_ld1_x3_v4hi */
    case 3564:  /* aarch64_ld1_x3_v8hi */
    case 3565:  /* aarch64_ld1_x3_v2si */
    case 3566:  /* aarch64_ld1_x3_v4si */
    case 3567:  /* aarch64_ld1_x3_v4bf */
    case 3568:  /* aarch64_ld1_x3_v8bf */
    case 3569:  /* aarch64_ld1_x3_v2di */
    case 3570:  /* aarch64_ld1_x3_v4hf */
    case 3571:  /* aarch64_ld1_x3_v8hf */
    case 3572:  /* aarch64_ld1_x3_v2sf */
    case 3573:  /* aarch64_ld1_x3_v4sf */
    case 3574:  /* aarch64_ld1_x3_v2df */
    case 3575:  /* aarch64_ld1_x3_di */
    case 3576:  /* aarch64_ld1_x3_df */
    case 3577:  /* aarch64_ld1_x4_v8qi */
    case 3578:  /* aarch64_ld1_x4_v16qi */
    case 3579:  /* aarch64_ld1_x4_v4hi */
    case 3580:  /* aarch64_ld1_x4_v8hi */
    case 3581:  /* aarch64_ld1_x4_v2si */
    case 3582:  /* aarch64_ld1_x4_v4si */
    case 3583:  /* aarch64_ld1_x4_v4bf */
    case 3584:  /* aarch64_ld1_x4_v8bf */
    case 3585:  /* aarch64_ld1_x4_v2di */
    case 3586:  /* aarch64_ld1_x4_v4hf */
    case 3587:  /* aarch64_ld1_x4_v8hf */
    case 3588:  /* aarch64_ld1_x4_v2sf */
    case 3589:  /* aarch64_ld1_x4_v4sf */
    case 3590:  /* aarch64_ld1_x4_v2df */
    case 3591:  /* aarch64_ld1_x4_di */
    case 3592:  /* aarch64_ld1_x4_df */
    case 3593:  /* aarch64_st1_x2_v8qi */
    case 3594:  /* aarch64_st1_x2_v16qi */
    case 3595:  /* aarch64_st1_x2_v4hi */
    case 3596:  /* aarch64_st1_x2_v8hi */
    case 3597:  /* aarch64_st1_x2_v2si */
    case 3598:  /* aarch64_st1_x2_v4si */
    case 3599:  /* aarch64_st1_x2_v4bf */
    case 3600:  /* aarch64_st1_x2_v8bf */
    case 3601:  /* aarch64_st1_x2_v2di */
    case 3602:  /* aarch64_st1_x2_v4hf */
    case 3603:  /* aarch64_st1_x2_v8hf */
    case 3604:  /* aarch64_st1_x2_v2sf */
    case 3605:  /* aarch64_st1_x2_v4sf */
    case 3606:  /* aarch64_st1_x2_v2df */
    case 3607:  /* aarch64_st1_x2_di */
    case 3608:  /* aarch64_st1_x2_df */
    case 3609:  /* aarch64_st1_x3_v8qi */
    case 3611:  /* aarch64_st1_x3_v4hi */
    case 3613:  /* aarch64_st1_x3_v2si */
    case 3615:  /* aarch64_st1_x3_v4bf */
    case 3618:  /* aarch64_st1_x3_v4hf */
    case 3620:  /* aarch64_st1_x3_v2sf */
    case 3623:  /* aarch64_st1_x3_di */
    case 3624:  /* aarch64_st1_x3_df */
    case 3625:  /* aarch64_st1_x4_v8qi */
    case 3627:  /* aarch64_st1_x4_v4hi */
    case 3629:  /* aarch64_st1_x4_v2si */
    case 3631:  /* aarch64_st1_x4_v4bf */
    case 3634:  /* aarch64_st1_x4_v4hf */
    case 3636:  /* aarch64_st1_x4_v2sf */
    case 3639:  /* aarch64_st1_x4_di */
    case 3640:  /* aarch64_st1_x4_df */
    case 3641:  /* *aarch64_movoi */
    case 3642:  /* *aarch64_movci */
    case 3643:  /* *aarch64_movxi */
    case 3644:  /* aarch64_be_ld1v8qi */
    case 3645:  /* aarch64_be_ld1v16qi */
    case 3646:  /* aarch64_be_ld1v4hi */
    case 3647:  /* aarch64_be_ld1v8hi */
    case 3648:  /* aarch64_be_ld1v2si */
    case 3649:  /* aarch64_be_ld1v4si */
    case 3650:  /* aarch64_be_ld1v2di */
    case 3651:  /* aarch64_be_ld1v4hf */
    case 3652:  /* aarch64_be_ld1v8hf */
    case 3653:  /* aarch64_be_ld1v4bf */
    case 3654:  /* aarch64_be_ld1v8bf */
    case 3655:  /* aarch64_be_ld1v2sf */
    case 3656:  /* aarch64_be_ld1v4sf */
    case 3657:  /* aarch64_be_ld1v2df */
    case 3658:  /* aarch64_be_ld1di */
    case 3659:  /* aarch64_be_st1v8qi */
    case 3660:  /* aarch64_be_st1v16qi */
    case 3661:  /* aarch64_be_st1v4hi */
    case 3662:  /* aarch64_be_st1v8hi */
    case 3663:  /* aarch64_be_st1v2si */
    case 3664:  /* aarch64_be_st1v4si */
    case 3665:  /* aarch64_be_st1v2di */
    case 3666:  /* aarch64_be_st1v4hf */
    case 3667:  /* aarch64_be_st1v8hf */
    case 3668:  /* aarch64_be_st1v4bf */
    case 3669:  /* aarch64_be_st1v8bf */
    case 3670:  /* aarch64_be_st1v2sf */
    case 3671:  /* aarch64_be_st1v4sf */
    case 3672:  /* aarch64_be_st1v2df */
    case 3673:  /* aarch64_be_st1di */
    case 3674:  /* *aarch64_be_movoi */
    case 3675:  /* *aarch64_be_movci */
    case 3676:  /* *aarch64_be_movxi */
    case 3677:  /* aarch64_ld2v8qi_dreg */
    case 3678:  /* aarch64_ld2v4hi_dreg */
    case 3679:  /* aarch64_ld2v4hf_dreg */
    case 3680:  /* aarch64_ld2v2si_dreg */
    case 3681:  /* aarch64_ld2v2sf_dreg */
    case 3682:  /* aarch64_ld2v4bf_dreg */
    case 3683:  /* aarch64_ld2di_dreg */
    case 3684:  /* aarch64_ld2df_dreg */
    case 3685:  /* aarch64_ld3v8qi_dreg */
    case 3686:  /* aarch64_ld3v4hi_dreg */
    case 3687:  /* aarch64_ld3v4hf_dreg */
    case 3688:  /* aarch64_ld3v2si_dreg */
    case 3689:  /* aarch64_ld3v2sf_dreg */
    case 3690:  /* aarch64_ld3v4bf_dreg */
    case 3691:  /* aarch64_ld3di_dreg */
    case 3692:  /* aarch64_ld3df_dreg */
    case 3693:  /* aarch64_ld4v8qi_dreg */
    case 3694:  /* aarch64_ld4v4hi_dreg */
    case 3695:  /* aarch64_ld4v4hf_dreg */
    case 3696:  /* aarch64_ld4v2si_dreg */
    case 3697:  /* aarch64_ld4v2sf_dreg */
    case 3698:  /* aarch64_ld4v4bf_dreg */
    case 3699:  /* aarch64_ld4di_dreg */
    case 3700:  /* aarch64_ld4df_dreg */
    case 3701:  /* aarch64_tbl1v8qi */
    case 3702:  /* aarch64_tbl1v16qi */
    case 3703:  /* aarch64_tbl2v16qi */
    case 3704:  /* aarch64_tbl3v8qi */
    case 3705:  /* aarch64_tbl3v16qi */
    case 3706:  /* aarch64_tbx4v8qi */
    case 3707:  /* aarch64_tbx4v16qi */
    case 3708:  /* aarch64_qtbl3v8qi */
    case 3709:  /* aarch64_qtbl3v16qi */
    case 3710:  /* aarch64_qtbx3v8qi */
    case 3711:  /* aarch64_qtbx3v16qi */
    case 3712:  /* aarch64_qtbl4v8qi */
    case 3713:  /* aarch64_qtbl4v16qi */
    case 3714:  /* aarch64_qtbx4v8qi */
    case 3715:  /* aarch64_qtbx4v16qi */
    case 3716:  /* aarch64_combinev16qi */
    case 3717:  /* aarch64_zip1v8qi */
    case 3718:  /* aarch64_zip2v8qi */
    case 3719:  /* aarch64_trn1v8qi */
    case 3720:  /* aarch64_trn2v8qi */
    case 3721:  /* aarch64_uzp1v8qi */
    case 3722:  /* aarch64_uzp2v8qi */
    case 3723:  /* aarch64_zip1v16qi */
    case 3724:  /* aarch64_zip2v16qi */
    case 3725:  /* aarch64_trn1v16qi */
    case 3726:  /* aarch64_trn2v16qi */
    case 3727:  /* aarch64_uzp1v16qi */
    case 3728:  /* aarch64_uzp2v16qi */
    case 3729:  /* aarch64_zip1v4hi */
    case 3730:  /* aarch64_zip2v4hi */
    case 3731:  /* aarch64_trn1v4hi */
    case 3732:  /* aarch64_trn2v4hi */
    case 3733:  /* aarch64_uzp1v4hi */
    case 3734:  /* aarch64_uzp2v4hi */
    case 3735:  /* aarch64_zip1v8hi */
    case 3736:  /* aarch64_zip2v8hi */
    case 3737:  /* aarch64_trn1v8hi */
    case 3738:  /* aarch64_trn2v8hi */
    case 3739:  /* aarch64_uzp1v8hi */
    case 3740:  /* aarch64_uzp2v8hi */
    case 3741:  /* aarch64_zip1v2si */
    case 3742:  /* aarch64_zip2v2si */
    case 3743:  /* aarch64_trn1v2si */
    case 3744:  /* aarch64_trn2v2si */
    case 3745:  /* aarch64_uzp1v2si */
    case 3746:  /* aarch64_uzp2v2si */
    case 3747:  /* aarch64_zip1v4si */
    case 3748:  /* aarch64_zip2v4si */
    case 3749:  /* aarch64_trn1v4si */
    case 3750:  /* aarch64_trn2v4si */
    case 3751:  /* aarch64_uzp1v4si */
    case 3752:  /* aarch64_uzp2v4si */
    case 3753:  /* aarch64_zip1v2di */
    case 3754:  /* aarch64_zip2v2di */
    case 3755:  /* aarch64_trn1v2di */
    case 3756:  /* aarch64_trn2v2di */
    case 3757:  /* aarch64_uzp1v2di */
    case 3758:  /* aarch64_uzp2v2di */
    case 3759:  /* aarch64_zip1v4hf */
    case 3760:  /* aarch64_zip2v4hf */
    case 3761:  /* aarch64_trn1v4hf */
    case 3762:  /* aarch64_trn2v4hf */
    case 3763:  /* aarch64_uzp1v4hf */
    case 3764:  /* aarch64_uzp2v4hf */
    case 3765:  /* aarch64_zip1v8hf */
    case 3766:  /* aarch64_zip2v8hf */
    case 3767:  /* aarch64_trn1v8hf */
    case 3768:  /* aarch64_trn2v8hf */
    case 3769:  /* aarch64_uzp1v8hf */
    case 3770:  /* aarch64_uzp2v8hf */
    case 3771:  /* aarch64_zip1v4bf */
    case 3772:  /* aarch64_zip2v4bf */
    case 3773:  /* aarch64_trn1v4bf */
    case 3774:  /* aarch64_trn2v4bf */
    case 3775:  /* aarch64_uzp1v4bf */
    case 3776:  /* aarch64_uzp2v4bf */
    case 3777:  /* aarch64_zip1v8bf */
    case 3778:  /* aarch64_zip2v8bf */
    case 3779:  /* aarch64_trn1v8bf */
    case 3780:  /* aarch64_trn2v8bf */
    case 3781:  /* aarch64_uzp1v8bf */
    case 3782:  /* aarch64_uzp2v8bf */
    case 3783:  /* aarch64_zip1v2sf */
    case 3784:  /* aarch64_zip2v2sf */
    case 3785:  /* aarch64_trn1v2sf */
    case 3786:  /* aarch64_trn2v2sf */
    case 3787:  /* aarch64_uzp1v2sf */
    case 3788:  /* aarch64_uzp2v2sf */
    case 3789:  /* aarch64_zip1v4sf */
    case 3790:  /* aarch64_zip2v4sf */
    case 3791:  /* aarch64_trn1v4sf */
    case 3792:  /* aarch64_trn2v4sf */
    case 3793:  /* aarch64_uzp1v4sf */
    case 3794:  /* aarch64_uzp2v4sf */
    case 3795:  /* aarch64_zip1v2df */
    case 3796:  /* aarch64_zip2v2df */
    case 3797:  /* aarch64_trn1v2df */
    case 3798:  /* aarch64_trn2v2df */
    case 3799:  /* aarch64_uzp1v2df */
    case 3800:  /* aarch64_uzp2v2df */
    case 3801:  /* aarch64_extv8qi */
    case 3802:  /* aarch64_extv16qi */
    case 3803:  /* aarch64_extv4hi */
    case 3804:  /* aarch64_extv8hi */
    case 3805:  /* aarch64_extv2si */
    case 3806:  /* aarch64_extv4si */
    case 3807:  /* aarch64_extv2di */
    case 3808:  /* aarch64_extv4hf */
    case 3809:  /* aarch64_extv8hf */
    case 3810:  /* aarch64_extv4bf */
    case 3811:  /* aarch64_extv8bf */
    case 3812:  /* aarch64_extv2sf */
    case 3813:  /* aarch64_extv4sf */
    case 3814:  /* aarch64_extv2df */
    case 3815:  /* aarch64_rev64v8qi */
    case 3816:  /* aarch64_rev32v8qi */
    case 3817:  /* aarch64_rev16v8qi */
    case 3818:  /* aarch64_rev64v16qi */
    case 3819:  /* aarch64_rev32v16qi */
    case 3820:  /* aarch64_rev16v16qi */
    case 3821:  /* aarch64_rev64v4hi */
    case 3822:  /* aarch64_rev32v4hi */
    case 3823:  /* aarch64_rev16v4hi */
    case 3824:  /* aarch64_rev64v8hi */
    case 3825:  /* aarch64_rev32v8hi */
    case 3826:  /* aarch64_rev16v8hi */
    case 3827:  /* aarch64_rev64v2si */
    case 3828:  /* aarch64_rev32v2si */
    case 3829:  /* aarch64_rev16v2si */
    case 3830:  /* aarch64_rev64v4si */
    case 3831:  /* aarch64_rev32v4si */
    case 3832:  /* aarch64_rev16v4si */
    case 3833:  /* aarch64_rev64v2di */
    case 3834:  /* aarch64_rev32v2di */
    case 3835:  /* aarch64_rev16v2di */
    case 3836:  /* aarch64_rev64v4hf */
    case 3837:  /* aarch64_rev32v4hf */
    case 3838:  /* aarch64_rev16v4hf */
    case 3839:  /* aarch64_rev64v8hf */
    case 3840:  /* aarch64_rev32v8hf */
    case 3841:  /* aarch64_rev16v8hf */
    case 3842:  /* aarch64_rev64v4bf */
    case 3843:  /* aarch64_rev32v4bf */
    case 3844:  /* aarch64_rev16v4bf */
    case 3845:  /* aarch64_rev64v8bf */
    case 3846:  /* aarch64_rev32v8bf */
    case 3847:  /* aarch64_rev16v8bf */
    case 3848:  /* aarch64_rev64v2sf */
    case 3849:  /* aarch64_rev32v2sf */
    case 3850:  /* aarch64_rev16v2sf */
    case 3851:  /* aarch64_rev64v4sf */
    case 3852:  /* aarch64_rev32v4sf */
    case 3853:  /* aarch64_rev16v4sf */
    case 3854:  /* aarch64_rev64v2df */
    case 3855:  /* aarch64_rev32v2df */
    case 3856:  /* aarch64_rev16v2df */
    case 3857:  /* aarch64_st2v8qi_dreg */
    case 3858:  /* aarch64_st2v4hi_dreg */
    case 3859:  /* aarch64_st2v4hf_dreg */
    case 3860:  /* aarch64_st2v2si_dreg */
    case 3861:  /* aarch64_st2v2sf_dreg */
    case 3862:  /* aarch64_st2v4bf_dreg */
    case 3863:  /* aarch64_st2di_dreg */
    case 3864:  /* aarch64_st2df_dreg */
    case 3865:  /* aarch64_st3v8qi_dreg */
    case 3866:  /* aarch64_st3v4hi_dreg */
    case 3867:  /* aarch64_st3v4hf_dreg */
    case 3868:  /* aarch64_st3v2si_dreg */
    case 3869:  /* aarch64_st3v2sf_dreg */
    case 3870:  /* aarch64_st3v4bf_dreg */
    case 3871:  /* aarch64_st3di_dreg */
    case 3872:  /* aarch64_st3df_dreg */
    case 3873:  /* aarch64_st4v8qi_dreg */
    case 3874:  /* aarch64_st4v4hi_dreg */
    case 3875:  /* aarch64_st4v4hf_dreg */
    case 3876:  /* aarch64_st4v2si_dreg */
    case 3877:  /* aarch64_st4v2sf_dreg */
    case 3878:  /* aarch64_st4v4bf_dreg */
    case 3879:  /* aarch64_st4di_dreg */
    case 3880:  /* aarch64_st4df_dreg */
    case 3881:  /* *aarch64_simd_ld1rv8qi */
    case 3882:  /* *aarch64_simd_ld1rv16qi */
    case 3883:  /* *aarch64_simd_ld1rv4hi */
    case 3884:  /* *aarch64_simd_ld1rv8hi */
    case 3885:  /* *aarch64_simd_ld1rv2si */
    case 3886:  /* *aarch64_simd_ld1rv4si */
    case 3887:  /* *aarch64_simd_ld1rv2di */
    case 3888:  /* *aarch64_simd_ld1rv4hf */
    case 3889:  /* *aarch64_simd_ld1rv8hf */
    case 3890:  /* *aarch64_simd_ld1rv4bf */
    case 3891:  /* *aarch64_simd_ld1rv8bf */
    case 3892:  /* *aarch64_simd_ld1rv2sf */
    case 3893:  /* *aarch64_simd_ld1rv4sf */
    case 3894:  /* *aarch64_simd_ld1rv2df */
    case 3895:  /* aarch64_simd_ld1v16qi_x2 */
    case 3896:  /* aarch64_simd_ld1v8hi_x2 */
    case 3897:  /* aarch64_simd_ld1v4si_x2 */
    case 3898:  /* aarch64_simd_ld1v2di_x2 */
    case 3899:  /* aarch64_simd_ld1v8hf_x2 */
    case 3900:  /* aarch64_simd_ld1v4sf_x2 */
    case 3901:  /* aarch64_simd_ld1v2df_x2 */
    case 3902:  /* aarch64_simd_ld1v8bf_x2 */
    case 3903:  /* aarch64_simd_ld1v8qi_x2 */
    case 3904:  /* aarch64_simd_ld1v4hi_x2 */
    case 3905:  /* aarch64_simd_ld1v4bf_x2 */
    case 3906:  /* aarch64_simd_ld1v4hf_x2 */
    case 3907:  /* aarch64_simd_ld1v2si_x2 */
    case 3908:  /* aarch64_simd_ld1v2sf_x2 */
    case 3909:  /* aarch64_simd_ld1di_x2 */
    case 3910:  /* aarch64_simd_ld1df_x2 */
    case 3911:  /* aarch64_frecpev4hf */
    case 3912:  /* aarch64_frecpev8hf */
    case 3913:  /* aarch64_frecpev2sf */
    case 3914:  /* aarch64_frecpev4sf */
    case 3915:  /* aarch64_frecpev2df */
    case 3916:  /* aarch64_frecpehf */
    case 3917:  /* aarch64_frecpesf */
    case 3918:  /* aarch64_frecpedf */
    case 3919:  /* aarch64_frecpxhf */
    case 3920:  /* aarch64_frecpxsf */
    case 3921:  /* aarch64_frecpxdf */
    case 3922:  /* aarch64_frecpsv4hf */
    case 3923:  /* aarch64_frecpsv8hf */
    case 3924:  /* aarch64_frecpsv2sf */
    case 3925:  /* aarch64_frecpsv4sf */
    case 3926:  /* aarch64_frecpsv2df */
    case 3927:  /* aarch64_frecpshf */
    case 3928:  /* aarch64_frecpssf */
    case 3929:  /* aarch64_frecpsdf */
    case 3930:  /* aarch64_urecpev2si */
    case 3931:  /* aarch64_urecpev4si */
    case 3932:  /* aarch64_crypto_aesev16qi */
    case 3933:  /* aarch64_crypto_aesdv16qi */
    case 3934:  /* aarch64_crypto_aesmcv16qi */
    case 3935:  /* aarch64_crypto_aesimcv16qi */
    case 3936:  /* *aarch64_crypto_aese_fused */
    case 3937:  /* *aarch64_crypto_aesd_fused */
    case 3938:  /* aarch64_crypto_sha1hsi */
    case 3939:  /* aarch64_crypto_sha1hv4si */
    case 3940:  /* aarch64_be_crypto_sha1hv4si */
    case 3941:  /* aarch64_crypto_sha1su1v4si */
    case 3942:  /* aarch64_crypto_sha1cv4si */
    case 3943:  /* aarch64_crypto_sha1mv4si */
    case 3944:  /* aarch64_crypto_sha1pv4si */
    case 3945:  /* aarch64_crypto_sha1su0v4si */
    case 3946:  /* aarch64_crypto_sha256hv4si */
    case 3947:  /* aarch64_crypto_sha256h2v4si */
    case 3948:  /* aarch64_crypto_sha256su0v4si */
    case 3949:  /* aarch64_crypto_sha256su1v4si */
    case 3973:  /* aarch64_simd_fmlal_lowv2sf */
    case 3974:  /* aarch64_simd_fmlalq_lowv4sf */
    case 3975:  /* aarch64_simd_fmlsl_lowv2sf */
    case 3976:  /* aarch64_simd_fmlslq_lowv4sf */
    case 3977:  /* aarch64_simd_fmlal_highv2sf */
    case 3978:  /* aarch64_simd_fmlalq_highv4sf */
    case 3979:  /* aarch64_simd_fmlsl_highv2sf */
    case 3980:  /* aarch64_simd_fmlslq_highv4sf */
    case 3981:  /* aarch64_simd_fmlal_lane_lowv2sf */
    case 3982:  /* aarch64_simd_fmlsl_lane_lowv2sf */
    case 3983:  /* aarch64_simd_fmlal_lane_highv2sf */
    case 3984:  /* aarch64_simd_fmlsl_lane_highv2sf */
    case 3985:  /* aarch64_simd_fmlalq_laneq_lowv4sf */
    case 3986:  /* aarch64_simd_fmlslq_laneq_lowv4sf */
    case 3987:  /* aarch64_simd_fmlalq_laneq_highv4sf */
    case 3988:  /* aarch64_simd_fmlslq_laneq_highv4sf */
    case 3989:  /* aarch64_simd_fmlal_laneq_lowv2sf */
    case 3990:  /* aarch64_simd_fmlsl_laneq_lowv2sf */
    case 3991:  /* aarch64_simd_fmlal_laneq_highv2sf */
    case 3992:  /* aarch64_simd_fmlsl_laneq_highv2sf */
    case 3993:  /* aarch64_simd_fmlalq_lane_lowv4sf */
    case 3994:  /* aarch64_simd_fmlslq_lane_lowv4sf */
    case 3995:  /* aarch64_simd_fmlalq_lane_highv4sf */
    case 3996:  /* aarch64_simd_fmlslq_lane_highv4sf */
    case 3997:  /* aarch64_crypto_pmulldi */
    case 3998:  /* aarch64_crypto_pmullv2di */
    case 3999:  /* extendv8qiv8hi2 */
    case 4000:  /* zero_extendv8qiv8hi2 */
    case 4001:  /* extendv4hiv4si2 */
    case 4002:  /* zero_extendv4hiv4si2 */
    case 4003:  /* extendv2siv2di2 */
    case 4004:  /* zero_extendv2siv2di2 */
    case 4005:  /* truncv8hiv8qi2 */
    case 4006:  /* truncv4siv4hi2 */
    case 4007:  /* truncv2div2si2 */
    case 4008:  /* aarch64_xtn2v8hi_le */
    case 4009:  /* aarch64_xtn2v4si_le */
    case 4010:  /* aarch64_xtn2v2di_le */
    case 4011:  /* aarch64_xtn2v8hi_be */
    case 4012:  /* aarch64_xtn2v4si_be */
    case 4013:  /* aarch64_xtn2v2di_be */
    case 4020:  /* aarch64_bfmmlaqv4sf */
    case 4021:  /* aarch64_bfmlalbv4sf */
    case 4022:  /* aarch64_bfmlaltv4sf */
    case 4023:  /* aarch64_bfmlalb_lanev4sf */
    case 4024:  /* aarch64_bfmlalt_lanev4sf */
    case 4025:  /* aarch64_bfmlalb_lane_qv4sf */
    case 4026:  /* aarch64_bfmlalt_lane_qv4sf */
    case 4027:  /* aarch64_simd_smmlav16qi */
    case 4028:  /* aarch64_simd_ummlav16qi */
    case 4029:  /* aarch64_simd_usmmlav16qi */
    case 4030:  /* aarch64_bfcvtnv4bf */
    case 4031:  /* aarch64_bfcvtn_qv8bf */
    case 4032:  /* aarch64_bfcvtn2v8bf */
    case 4033:  /* aarch64_bfcvtbf */
    case 4034:  /* aarch64_vbfcvtv4bf */
    case 4035:  /* aarch64_vbfcvtv8bf */
    case 4036:  /* aarch64_vbfcvt_highv8bf */
    case 4037:  /* aarch64_bfcvtsf */
    case 5046:  /* *vec_extractvnx16qiqi_0 */
    case 5047:  /* *vec_extractvnx8hihi_0 */
    case 5048:  /* *vec_extractvnx4sisi_0 */
    case 5049:  /* *vec_extractvnx2didi_0 */
    case 5050:  /* *vec_extractvnx8bfbf_0 */
    case 5051:  /* *vec_extractvnx8hfhf_0 */
    case 5052:  /* *vec_extractvnx4sfsf_0 */
    case 5053:  /* *vec_extractvnx2dfdf_0 */
    case 5054:  /* *vec_extractvnx16qiqi_v128 */
    case 5055:  /* *vec_extractvnx8hihi_v128 */
    case 5056:  /* *vec_extractvnx4sisi_v128 */
    case 5057:  /* *vec_extractvnx2didi_v128 */
    case 5058:  /* *vec_extractvnx8bfbf_v128 */
    case 5059:  /* *vec_extractvnx8hfhf_v128 */
    case 5060:  /* *vec_extractvnx4sfsf_v128 */
    case 5061:  /* *vec_extractvnx2dfdf_v128 */
    case 10019:  /* aarch64_sve2_aese */
    case 10020:  /* aarch64_sve2_aesd */
    case 10021:  /* aarch64_sve2_aesmc */
    case 10022:  /* aarch64_sve2_aesimc */
    case 10023:  /* *aarch64_sve2_aese_fused */
    case 10024:  /* *aarch64_sve2_aesd_fused */
      if ((cached_type = get_attr_type (insn)) == TYPE_NO_INSN)
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_type == TYPE_ADR) || (cached_type == TYPE_SHIFT_IMM) || (cached_type == TYPE_MOV_IMM) || (cached_type == TYPE_MVN_IMM) || (cached_type == TYPE_MOV_SHIFT)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_type == TYPE_SHIFT_REG) || (cached_type == TYPE_MOV_SHIFT_REG)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_type == TYPE_ALU_IMM) || (cached_type == TYPE_ALUS_IMM) || (cached_type == TYPE_LOGIC_IMM) || (cached_type == TYPE_LOGICS_IMM) || (cached_type == TYPE_ALU_SREG) || (cached_type == TYPE_ALUS_SREG) || (cached_type == TYPE_LOGIC_REG) || (cached_type == TYPE_LOGICS_REG) || (cached_type == TYPE_ADC_IMM) || (cached_type == TYPE_ADCS_IMM) || (cached_type == TYPE_ADC_REG) || (cached_type == TYPE_ADCS_REG) || (cached_type == TYPE_CSEL) || (cached_type == TYPE_CLZ) || (cached_type == TYPE_RBIT) || (cached_type == TYPE_REV) || (cached_type == TYPE_ALU_DSP_REG) || (cached_type == TYPE_MOV_REG) || (cached_type == TYPE_MVN_REG) || (cached_type == TYPE_MRS) || (cached_type == TYPE_MULTIPLE)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_type == TYPE_ALU_SHIFT_IMM_LSL_1TO4) || (cached_type == TYPE_ALU_SHIFT_IMM_OTHER) || (cached_type == TYPE_ALUS_SHIFT_IMM) || (cached_type == TYPE_CRC) || (cached_type == TYPE_LOGIC_SHIFT_IMM) || (cached_type == TYPE_LOGICS_SHIFT_IMM) || (cached_type == TYPE_ALU_EXT) || (cached_type == TYPE_ALUS_EXT) || (cached_type == TYPE_BFM) || (cached_type == TYPE_BFX) || (cached_type == TYPE_EXTEND) || (cached_type == TYPE_MVN_SHIFT)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_type == TYPE_ALU_SHIFT_REG) || (cached_type == TYPE_ALUS_SHIFT_REG) || (cached_type == TYPE_LOGIC_SHIFT_REG) || (cached_type == TYPE_LOGICS_SHIFT_REG) || (cached_type == TYPE_MVN_SHIFT_REG)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && (cached_type == TYPE_ROTATE_IMM))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && (((cached_mul32 = get_attr_mul32 (insn)) == MUL32_YES) || ((cached_widen_mul64 = get_attr_widen_mul64 (insn)) == WIDEN_MUL64_YES)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_type == TYPE_UDIV) || (cached_type == TYPE_SDIV)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_type == TYPE_LOAD_BYTE) || (cached_type == TYPE_LOAD_4) || (cached_type == TYPE_LOAD_ACQ)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_type == TYPE_STORE_4) || (cached_type == TYPE_STORE_REL)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && (cached_type == TYPE_LOAD_8))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && (cached_type == TYPE_STORE_8))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_type == TYPE_LOAD_12) || (cached_type == TYPE_LOAD_16)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_type == TYPE_STORE_12) || (cached_type == TYPE_STORE_16)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_type == TYPE_BRANCH) || (cached_type == TYPE_CALL)))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_type == TYPE_FFARITHS) || (cached_type == TYPE_FADDS) || (cached_type == TYPE_FFARITHD) || (cached_type == TYPE_FADDD) || (cached_type == TYPE_FMOV) || (cached_type == TYPE_F_CVT) || (cached_type == TYPE_FCMPS) || (cached_type == TYPE_FCMPD) || (cached_type == TYPE_FCCMPS) || (cached_type == TYPE_FCCMPD) || (cached_type == TYPE_FCSEL) || (cached_type == TYPE_F_RINTS) || (cached_type == TYPE_F_RINTD) || (cached_type == TYPE_F_MINMAXS) || (cached_type == TYPE_F_MINMAXD)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_type == TYPE_FCONSTS) || (cached_type == TYPE_FCONSTD)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_type == TYPE_FMULS) || (cached_type == TYPE_FMULD)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_type == TYPE_FMACS) || (cached_type == TYPE_FMACD) || (cached_type == TYPE_FFMAS) || (cached_type == TYPE_FFMAD)))
        {
	  return 8;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_type == TYPE_F_MCR) || (cached_type == TYPE_F_MCRR)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_type == TYPE_F_MRC) || (cached_type == TYPE_F_MRRC)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_type == TYPE_F_CVTI2F) || (cached_type == TYPE_NEON_FROM_GP) || (cached_type == TYPE_NEON_FROM_GP_Q)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_type == TYPE_F_CVTF2I) || (cached_type == TYPE_NEON_TO_GP) || (cached_type == TYPE_NEON_TO_GP_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && (cached_type == TYPE_F_FLAG))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && (((cached_type == TYPE_F_LOADS) || (cached_type == TYPE_F_LOADD)) || ((cached_cortex_a53_advsimd_type = get_attr_cortex_a53_advsimd_type (insn)) == CORTEX_A53_ADVSIMD_TYPE_ADVSIMD_LOAD_64)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && (((cached_cortex_a53_advsimd_type = get_attr_cortex_a53_advsimd_type (insn)) == CORTEX_A53_ADVSIMD_TYPE_ADVSIMD_LOAD_128) || (cached_cortex_a53_advsimd_type == CORTEX_A53_ADVSIMD_TYPE_ADVSIMD_LOAD_LOTS)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && (((cached_type == TYPE_F_STORES) || (cached_type == TYPE_F_STORED)) || ((cached_cortex_a53_advsimd_type = get_attr_cortex_a53_advsimd_type (insn)) == CORTEX_A53_ADVSIMD_TYPE_ADVSIMD_STORE_64)))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && (((cached_cortex_a53_advsimd_type = get_attr_cortex_a53_advsimd_type (insn)) == CORTEX_A53_ADVSIMD_TYPE_ADVSIMD_STORE_128) || (cached_cortex_a53_advsimd_type == CORTEX_A53_ADVSIMD_TYPE_ADVSIMD_STORE_LOTS)))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_cortex_a53_advsimd_type = get_attr_cortex_a53_advsimd_type (insn)) == CORTEX_A53_ADVSIMD_TYPE_ADVSIMD_ALU))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_cortex_a53_advsimd_type = get_attr_cortex_a53_advsimd_type (insn)) == CORTEX_A53_ADVSIMD_TYPE_ADVSIMD_ALU_Q))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_cortex_a53_advsimd_type = get_attr_cortex_a53_advsimd_type (insn)) == CORTEX_A53_ADVSIMD_TYPE_ADVSIMD_MUL))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_cortex_a53_advsimd_type = get_attr_cortex_a53_advsimd_type (insn)) == CORTEX_A53_ADVSIMD_TYPE_ADVSIMD_MUL_Q))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && (((cached_type == TYPE_FDIVS) || (cached_type == TYPE_FSQRTS)) || ((cached_cortex_a53_advsimd_type = get_attr_cortex_a53_advsimd_type (insn)) == CORTEX_A53_ADVSIMD_TYPE_ADVSIMD_DIV_S)))
        {
	  return 14 /* 0xe */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && (((cached_type == TYPE_FDIVD) || (cached_type == TYPE_FSQRTD)) || ((cached_cortex_a53_advsimd_type = get_attr_cortex_a53_advsimd_type (insn)) == CORTEX_A53_ADVSIMD_TYPE_ADVSIMD_DIV_D)))
        {
	  return 29 /* 0x1d */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_cortex_a53_advsimd_type = get_attr_cortex_a53_advsimd_type (insn)) == CORTEX_A53_ADVSIMD_TYPE_ADVSIMD_DIV_S_Q))
        {
	  return 14 /* 0xe */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_cortex_a53_advsimd_type = get_attr_cortex_a53_advsimd_type (insn)) == CORTEX_A53_ADVSIMD_TYPE_ADVSIMD_DIV_D_Q))
        {
	  return 29 /* 0x1d */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && (cached_type == TYPE_CRYPTO_AESE))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && (cached_type == TYPE_CRYPTO_AESMC))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && (cached_type == TYPE_CRYPTO_SHA1_FAST))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && (cached_type == TYPE_CRYPTO_SHA256_FAST))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && (cached_type == TYPE_CRYPTO_SHA1_XOR))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA53)))) && ((cached_type == TYPE_CRYPTO_SHA1_SLOW) || (cached_type == TYPE_CRYPTO_SHA256_SLOW)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_type == TYPE_ALU_IMM) || (cached_type == TYPE_ALUS_IMM) || (cached_type == TYPE_LOGIC_IMM) || (cached_type == TYPE_LOGICS_IMM) || (cached_type == TYPE_ALU_SREG) || (cached_type == TYPE_ALUS_SREG) || (cached_type == TYPE_LOGIC_REG) || (cached_type == TYPE_LOGICS_REG) || (cached_type == TYPE_ADC_IMM) || (cached_type == TYPE_ADCS_IMM) || (cached_type == TYPE_ADC_REG) || (cached_type == TYPE_ADCS_REG) || (cached_type == TYPE_ADR) || (cached_type == TYPE_BFX) || (cached_type == TYPE_EXTEND) || (cached_type == TYPE_CLZ) || (cached_type == TYPE_RBIT) || (cached_type == TYPE_REV) || (cached_type == TYPE_ALU_DSP_REG) || (cached_type == TYPE_ROTATE_IMM) || (cached_type == TYPE_SHIFT_IMM) || (cached_type == TYPE_SHIFT_REG) || (cached_type == TYPE_MOV_IMM) || (cached_type == TYPE_MOV_REG) || (cached_type == TYPE_MVN_IMM) || (cached_type == TYPE_MVN_REG) || (cached_type == TYPE_MRS) || (cached_type == TYPE_MULTIPLE)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_type == TYPE_BFM) || (cached_type == TYPE_ALU_SHIFT_IMM_LSL_1TO4) || (cached_type == TYPE_ALU_SHIFT_IMM_OTHER) || (cached_type == TYPE_ALUS_SHIFT_IMM) || (cached_type == TYPE_CRC) || (cached_type == TYPE_LOGIC_SHIFT_IMM) || (cached_type == TYPE_LOGICS_SHIFT_IMM) || (cached_type == TYPE_MOV_SHIFT) || (cached_type == TYPE_MVN_SHIFT)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_type == TYPE_ALU_SHIFT_REG) || (cached_type == TYPE_ALUS_SHIFT_REG) || (cached_type == TYPE_LOGIC_SHIFT_REG) || (cached_type == TYPE_LOGICS_SHIFT_REG) || (cached_type == TYPE_MOV_SHIFT_REG) || (cached_type == TYPE_MVN_SHIFT_REG)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && (((cached_mul32 = get_attr_mul32 (insn)) == MUL32_YES) || ((cached_widen_mul64 = get_attr_widen_mul64 (insn)) == WIDEN_MUL64_YES)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_type == TYPE_UDIV) || (cached_type == TYPE_SDIV)))
        {
	  return 10 /* 0xa */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && (cached_type == TYPE_BLOCK))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && (cached_type == TYPE_BRANCH))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_type == TYPE_LOAD_BYTE) || (cached_type == TYPE_LOAD_4) || (cached_type == TYPE_LOAD_8)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_type == TYPE_LOAD_12) || (cached_type == TYPE_LOAD_16)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_type == TYPE_STORE_4) || (cached_type == TYPE_STORE_8)))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_type == TYPE_STORE_12) || (cached_type == TYPE_STORE_16)))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_ABD))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_ABD_Q))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_ARITH_ACC))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_ARITH_ACC_Q))
        {
	  return 8;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_ARITH_BASIC))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_ARITH_COMPLEX))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_MULTIPLY))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_MULTIPLY_Q))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_MLA))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_MLA_Q))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_SAT_MLA_LONG))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_SHIFT_ACC))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_SHIFT_IMM_BASIC))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_SHIFT_IMM_COMPLEX))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_SHIFT_REG_BASIC))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_SHIFT_REG_BASIC_Q))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_SHIFT_REG_COMPLEX))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_SHIFT_REG_COMPLEX_Q))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_FP_NEGABS))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_FP_ARITH))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_FP_ARITH_Q))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_FP_REDUCTIONS_Q))
        {
	  return 10 /* 0xa */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_FP_CVT_INT))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_FP_CVT_INT_Q))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_FP_CVT16))
        {
	  return 10 /* 0xa */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_FP_MUL))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_FP_MUL_Q))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_FP_MLA))
        {
	  return 9;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_FP_MLA_Q))
        {
	  return 9;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_FP_RECPE_RSQRTE))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_FP_RECPE_RSQRTE_Q))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_FP_RECPS_RSQRTS))
        {
	  return 10 /* 0xa */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_FP_RECPS_RSQRTS_Q))
        {
	  return 10 /* 0xa */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_BITOPS))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_BITOPS_Q))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_FROM_GP))
        {
	  return 9;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_FROM_GP_Q))
        {
	  return 9;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_TBL3_TBL4))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_ZIP_Q))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_TO_GP))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_LOAD_A))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_LOAD_B))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_LOAD_C))
        {
	  return 9;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_LOAD_D))
        {
	  return 11 /* 0xb */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_LOAD_E))
        {
	  return 9;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_LOAD_F))
        {
	  return 11 /* 0xb */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_STORE_A))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_STORE_B))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_cortex_a57_neon_type = get_attr_cortex_a57_neon_type (insn)) == CORTEX_A57_NEON_TYPE_NEON_STORE_COMPLEX))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_type == TYPE_FCONSTS) || (cached_type == TYPE_FCONSTD)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_type == TYPE_FADDS) || (cached_type == TYPE_FADDD)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_type == TYPE_FMULS) || (cached_type == TYPE_FMULD)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_type == TYPE_FMACS) || (cached_type == TYPE_FFMAS) || (cached_type == TYPE_FMACD) || (cached_type == TYPE_FFMAD)))
        {
	  return 10 /* 0xa */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_type == TYPE_F_CVT) || (cached_type == TYPE_F_CVTF2I) || (cached_type == TYPE_F_CVTI2F)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_type == TYPE_FCMPS) || (cached_type == TYPE_FCMPD) || (cached_type == TYPE_FCCMPS) || (cached_type == TYPE_FCCMPD)))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_type == TYPE_FFARITHS) || (cached_type == TYPE_FFARITHD)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_type == TYPE_FMOV) || (cached_type == TYPE_FCSEL)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_type == TYPE_FDIVS) || (cached_type == TYPE_FSQRTS) || (cached_type == TYPE_NEON_FP_DIV_S) || (cached_type == TYPE_NEON_FP_SQRT_S)))
        {
	  return 12 /* 0xc */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_type == TYPE_FDIVD) || (cached_type == TYPE_FSQRTD) || (cached_type == TYPE_NEON_FP_DIV_D) || (cached_type == TYPE_NEON_FP_SQRT_D)))
        {
	  return 16 /* 0x10 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_type == TYPE_FDIVD) || (cached_type == TYPE_FSQRTD) || (cached_type == TYPE_NEON_FP_DIV_S_Q) || (cached_type == TYPE_NEON_FP_DIV_D_Q) || (cached_type == TYPE_NEON_FP_SQRT_S_Q) || (cached_type == TYPE_NEON_FP_SQRT_D_Q)))
        {
	  return 20 /* 0x14 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_type == TYPE_CRYPTO_AESE) || (cached_type == TYPE_CRYPTO_AESMC) || (cached_type == TYPE_CRYPTO_SHA1_FAST) || (cached_type == TYPE_CRYPTO_SHA256_FAST)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && ((cached_type == TYPE_CRYPTO_SHA1_SLOW) || (cached_type == TYPE_CRYPTO_SHA256_SLOW)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && (cached_type == TYPE_CRYPTO_SHA1_XOR))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_CORTEXA57)))) && (cached_type == TYPE_CALL))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && (cached_type == TYPE_BRANCH))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && (cached_type == TYPE_CALL))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && (! ((cached_predicated = get_attr_predicated (insn)) == PREDICATED_YES)) && ((cached_type == TYPE_ALU_IMM) || (cached_type == TYPE_ALUS_IMM) || (cached_type == TYPE_LOGIC_IMM) || (cached_type == TYPE_LOGICS_IMM) || (cached_type == TYPE_ALU_SREG) || (cached_type == TYPE_ALUS_SREG) || (cached_type == TYPE_LOGIC_REG) || (cached_type == TYPE_LOGICS_REG) || (cached_type == TYPE_ADC_IMM) || (cached_type == TYPE_ADCS_IMM) || (cached_type == TYPE_ADC_REG) || (cached_type == TYPE_ADCS_REG) || (cached_type == TYPE_ADR) || (cached_type == TYPE_BFM) || (cached_type == TYPE_BFX) || (cached_type == TYPE_CLZ) || (cached_type == TYPE_RBIT) || (cached_type == TYPE_REV) || (cached_type == TYPE_CSEL) || (cached_type == TYPE_ALU_DSP_REG) || (cached_type == TYPE_SHIFT_IMM) || (cached_type == TYPE_SHIFT_REG) || (cached_type == TYPE_ROTATE_IMM) || (cached_type == TYPE_EXTEND) || (cached_type == TYPE_MOV_IMM) || (cached_type == TYPE_MOV_REG) || (cached_type == TYPE_MVN_IMM) || (cached_type == TYPE_MVN_REG) || (cached_type == TYPE_MRS) || (cached_type == TYPE_MULTIPLE)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_predicated = get_attr_predicated (insn)) == PREDICATED_YES) && ((cached_type == TYPE_ALU_IMM) || (cached_type == TYPE_ALUS_IMM) || (cached_type == TYPE_LOGIC_IMM) || (cached_type == TYPE_LOGICS_IMM) || (cached_type == TYPE_ALU_SREG) || (cached_type == TYPE_ALUS_SREG) || (cached_type == TYPE_LOGIC_REG) || (cached_type == TYPE_LOGICS_REG) || (cached_type == TYPE_ADC_IMM) || (cached_type == TYPE_ADCS_IMM) || (cached_type == TYPE_ADC_REG) || (cached_type == TYPE_ADCS_REG) || (cached_type == TYPE_ADR) || (cached_type == TYPE_BFM) || (cached_type == TYPE_BFX) || (cached_type == TYPE_CLZ) || (cached_type == TYPE_RBIT) || (cached_type == TYPE_REV) || (cached_type == TYPE_ALU_DSP_REG) || (cached_type == TYPE_SHIFT_IMM) || (cached_type == TYPE_SHIFT_REG) || (cached_type == TYPE_ROTATE_IMM) || (cached_type == TYPE_EXTEND) || (cached_type == TYPE_MOV_IMM) || (cached_type == TYPE_MOV_REG) || (cached_type == TYPE_MVN_IMM) || (cached_type == TYPE_MVN_REG) || (cached_type == TYPE_MRS) || (cached_type == TYPE_MULTIPLE)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_type == TYPE_ALU_EXT) || (cached_type == TYPE_ALUS_EXT) || (cached_type == TYPE_ALU_SHIFT_IMM_LSL_1TO4) || (cached_type == TYPE_ALU_SHIFT_IMM_OTHER) || (cached_type == TYPE_ALUS_SHIFT_IMM) || (cached_type == TYPE_LOGIC_SHIFT_IMM) || (cached_type == TYPE_LOGICS_SHIFT_IMM) || (cached_type == TYPE_MOV_SHIFT) || (cached_type == TYPE_MVN_SHIFT)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && (! ((cached_predicated = get_attr_predicated (insn)) == PREDICATED_YES)) && ((cached_type == TYPE_ALU_SHIFT_REG) || (cached_type == TYPE_ALUS_SHIFT_REG) || (cached_type == TYPE_LOGIC_SHIFT_REG) || (cached_type == TYPE_LOGICS_SHIFT_REG) || (cached_type == TYPE_MOV_SHIFT_REG) || (cached_type == TYPE_MVN_SHIFT_REG)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_predicated = get_attr_predicated (insn)) == PREDICATED_YES) && ((cached_type == TYPE_ALU_SHIFT_REG) || (cached_type == TYPE_ALUS_SHIFT_REG) || (cached_type == TYPE_LOGIC_SHIFT_REG) || (cached_type == TYPE_LOGICS_SHIFT_REG) || (cached_type == TYPE_MOV_SHIFT_REG) || (cached_type == TYPE_MVN_SHIFT_REG)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_mul32 = get_attr_mul32 (insn)) == MUL32_YES))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_widen_mul64 = get_attr_widen_mul64 (insn)) == WIDEN_MUL64_YES))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_type == TYPE_UDIV) || (cached_type == TYPE_SDIV)))
        {
	  return 13 /* 0xd */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_type == TYPE_LOAD_BYTE) || (cached_type == TYPE_LOAD_4) || (cached_type == TYPE_LOAD_8)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_type == TYPE_LOAD_12) || (cached_type == TYPE_LOAD_16)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_type == TYPE_STORE_4) || (cached_type == TYPE_STORE_8)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_type == TYPE_STORE_12) || (cached_type == TYPE_STORE_16)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_ARITH_SIMPLE))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_ARITH_BASIC))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_ARITH_COMPLEX))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && (((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_MULTIPLY) || (cached_exynos_m1_neon_type == EXYNOS_M1_NEON_TYPE_NEON_MLA) || (cached_exynos_m1_neon_type == EXYNOS_M1_NEON_TYPE_NEON_SAT_MLA_LONG)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_SHIFT_ACC))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && (((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_SHIFT_IMM_BASIC) || (cached_exynos_m1_neon_type == EXYNOS_M1_NEON_TYPE_NEON_SHIFT_REG_BASIC)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && (((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_SHIFT_IMM_COMPLEX) || (cached_exynos_m1_neon_type == EXYNOS_M1_NEON_TYPE_NEON_SHIFT_REG_COMPLEX)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_FP_UNARY))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_FP_ADD))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_FP_ABD))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_FP_COMPARE))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_FP_REDUC_MINMAX))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_FP_REDUC_ADD))
        {
	  return 10 /* 0xa */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_FP_ROUND))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_FP_CVT))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_FP_MUL))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_FP_MLA))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_FP_ESTIMATE))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_FP_ESTIMATEX))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_FP_STEP))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_BITOPS))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_BITOPS_Q))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_BITINS))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_TBL))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_FROM_GP))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_TO_GP))
        {
	  return 9;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_type == TYPE_F_LOADS) || (cached_type == TYPE_F_LOADD) || (cached_type == TYPE_NEON_LDP)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && (cached_type == TYPE_NEON_LDP_Q))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && (((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_LOAD1_1) || (cached_exynos_m1_neon_type == EXYNOS_M1_NEON_TYPE_NEON_LOAD1_ALL)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_LOAD1_2))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_LOAD1_3))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_LOAD1_4))
        {
	  return 8;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_LOAD1_ONE))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_LOAD2_2))
        {
	  return 10 /* 0xa */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_LOAD2_ONE))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_LOAD2_ALL))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_LOAD3_3))
        {
	  return 12 /* 0xc */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_LOAD3_ONE))
        {
	  return 9;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_LOAD3_ALL))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_LOAD4_4))
        {
	  return 14 /* 0xe */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_LOAD4_ONE))
        {
	  return 9;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_LOAD4_ALL))
        {
	  return 8;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_type == TYPE_F_STORES) || (cached_type == TYPE_F_STORED) || (cached_type == TYPE_NEON_STP)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && (cached_type == TYPE_NEON_STP_Q))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_STORE1_1))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_STORE1_2))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_STORE1_3))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_STORE1_4))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_STORE1_ONE))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && (((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_STORE2_2) || (cached_exynos_m1_neon_type == EXYNOS_M1_NEON_TYPE_NEON_STORE2_ONE)))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && (((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_STORE3_3) || (cached_exynos_m1_neon_type == EXYNOS_M1_NEON_TYPE_NEON_STORE3_ONE)))
        {
	  return 16 /* 0x10 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && (((cached_exynos_m1_neon_type = get_attr_exynos_m1_neon_type (insn)) == EXYNOS_M1_NEON_TYPE_NEON_STORE4_4) || (cached_exynos_m1_neon_type == EXYNOS_M1_NEON_TYPE_NEON_STORE4_ONE)))
        {
	  return 17 /* 0x11 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_type == TYPE_FCONSTS) || (cached_type == TYPE_FCONSTD)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_type == TYPE_FADDS) || (cached_type == TYPE_FADDD)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_type == TYPE_FMULS) || (cached_type == TYPE_FMULD)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_type == TYPE_FMACS) || (cached_type == TYPE_FFMAS) || (cached_type == TYPE_FMACD) || (cached_type == TYPE_FFMAD)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_type == TYPE_F_CVT) || (cached_type == TYPE_F_RINTS) || (cached_type == TYPE_F_RINTD)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && (cached_type == TYPE_F_CVTF2I))
        {
	  return 13 /* 0xd */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && (cached_type == TYPE_F_CVTI2F))
        {
	  return 9;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_type == TYPE_FCMPS) || (cached_type == TYPE_FCMPD)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_type == TYPE_FCCMPS) || (cached_type == TYPE_FCCMPD)))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && (cached_type == TYPE_FCSEL))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_type == TYPE_FFARITHS) || (cached_type == TYPE_FFARITHD)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && (cached_type == TYPE_FMOV))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_type == TYPE_FDIVS) || (cached_type == TYPE_NEON_FP_DIV_S) || (cached_type == TYPE_NEON_FP_DIV_S_Q) || (cached_type == TYPE_FSQRTS) || (cached_type == TYPE_NEON_FP_SQRT_S) || (cached_type == TYPE_NEON_FP_SQRT_S_Q)))
        {
	  return 15 /* 0xf */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_type == TYPE_FDIVD) || (cached_type == TYPE_NEON_FP_DIV_D) || (cached_type == TYPE_NEON_FP_DIV_D_Q) || (cached_type == TYPE_FSQRTD) || (cached_type == TYPE_NEON_FP_SQRT_D) || (cached_type == TYPE_NEON_FP_SQRT_D_Q)))
        {
	  return 22 /* 0x16 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_type == TYPE_F_MINMAXS) || (cached_type == TYPE_F_MINMAXD)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_type == TYPE_CRYPTO_AESE) || (cached_type == TYPE_CRYPTO_AESMC) || (cached_type == TYPE_CRYPTO_SHA1_XOR) || (cached_type == TYPE_CRYPTO_SHA1_FAST) || (cached_type == TYPE_CRYPTO_SHA256_FAST)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_type == TYPE_CRYPTO_SHA1_SLOW) || (cached_type == TYPE_CRYPTO_SHA256_SLOW)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && ((cached_type == TYPE_NEON_MUL_B_LONG) || (cached_type == TYPE_NEON_MUL_H_LONG) || (cached_type == TYPE_NEON_MUL_S_LONG)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && (cached_type == TYPE_NEON_MUL_D_LONG))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_EXYNOSM1)))) && (cached_type == TYPE_CRC))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_FP_NEG_S) || (cached_type == TYPE_NEON_FP_NEG_D) || (cached_type == TYPE_NEON_FP_ABS_S) || (cached_type == TYPE_NEON_FP_ABS_D)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_FP_NEG_S_Q) || (cached_type == TYPE_NEON_FP_NEG_D_Q) || (cached_type == TYPE_NEON_FP_ABS_S_Q) || (cached_type == TYPE_NEON_FP_ABS_D_Q)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_FP_MINMAX_S) || (cached_type == TYPE_NEON_FP_MINMAX_D) || (cached_type == TYPE_NEON_FP_REDUC_MINMAX_S) || (cached_type == TYPE_NEON_FP_REDUC_MINMAX_D) || (cached_type == TYPE_NEON_FP_COMPARE_S) || (cached_type == TYPE_NEON_FP_COMPARE_D) || (cached_type == TYPE_NEON_FP_ROUND_S) || (cached_type == TYPE_NEON_FP_ROUND_D)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_FP_MINMAX_S_Q) || (cached_type == TYPE_NEON_FP_MINMAX_D_Q) || (cached_type == TYPE_NEON_FP_COMPARE_S_Q) || (cached_type == TYPE_NEON_FP_COMPARE_D_Q) || (cached_type == TYPE_NEON_FP_ROUND_S_Q) || (cached_type == TYPE_NEON_FP_ROUND_D_Q)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_FP_REDUC_MINMAX_S_Q) || (cached_type == TYPE_NEON_FP_REDUC_MINMAX_D_Q) || (cached_type == TYPE_NEON_FP_ABD_S) || (cached_type == TYPE_NEON_FP_ABD_D) || (cached_type == TYPE_NEON_FP_ADDSUB_S) || (cached_type == TYPE_NEON_FP_ADDSUB_D) || (cached_type == TYPE_NEON_FP_REDUC_ADD_S) || (cached_type == TYPE_NEON_FP_REDUC_ADD_D)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_FP_ABD_S_Q) || (cached_type == TYPE_NEON_FP_ABD_D_Q) || (cached_type == TYPE_NEON_FP_ADDSUB_S_Q) || (cached_type == TYPE_NEON_FP_ADDSUB_D_Q) || (cached_type == TYPE_NEON_FP_REDUC_ADD_S_Q) || (cached_type == TYPE_NEON_FP_REDUC_ADD_D_Q)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_FP_TO_INT_S) || (cached_type == TYPE_NEON_FP_TO_INT_D) || (cached_type == TYPE_NEON_INT_TO_FP_S) || (cached_type == TYPE_NEON_INT_TO_FP_D) || (cached_type == TYPE_NEON_FP_CVT_WIDEN_H) || (cached_type == TYPE_NEON_FP_CVT_WIDEN_S)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_FP_TO_INT_S_Q) || (cached_type == TYPE_NEON_FP_TO_INT_D_Q) || (cached_type == TYPE_NEON_INT_TO_FP_S_Q) || (cached_type == TYPE_NEON_INT_TO_FP_D_Q)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_FP_MUL_S) || (cached_type == TYPE_NEON_FP_MUL_S_SCALAR)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_FP_MLA_S) || (cached_type == TYPE_NEON_FP_MLA_S_SCALAR)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_FP_MUL_S_Q) || (cached_type == TYPE_NEON_FP_MUL_S_SCALAR_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_FP_MLA_S_Q) || (cached_type == TYPE_NEON_FP_MLA_S_SCALAR_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_NEON_FP_MUL_D))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_NEON_FP_MLA_D))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_FP_MUL_D_Q) || (cached_type == TYPE_NEON_FP_MUL_D_SCALAR_Q)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_FP_MLA_D_Q) || (cached_type == TYPE_NEON_FP_MLA_D_SCALAR_Q)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_FP_CVT_NARROW_S_Q) || (cached_type == TYPE_NEON_FP_CVT_NARROW_D_Q)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_NEON_FP_DIV_S))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_NEON_FP_DIV_D))
        {
	  return 11 /* 0xb */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_NEON_FP_DIV_S_Q))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_NEON_FP_DIV_D_Q))
        {
	  return 11 /* 0xb */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_NEON_FP_SQRT_S))
        {
	  return 12 /* 0xc */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_NEON_FP_SQRT_D))
        {
	  return 22 /* 0x16 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_NEON_FP_SQRT_S_Q))
        {
	  return 12 /* 0xc */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_NEON_FP_SQRT_D_Q))
        {
	  return 22 /* 0x16 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_ADD) || (cached_type == TYPE_NEON_REDUC_ADD) || (cached_type == TYPE_NEON_LOGIC) || (cached_type == TYPE_NEON_NEG) || (cached_type == TYPE_NEON_SUB)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_SHIFT_IMM_LONG) || (cached_type == TYPE_NEON_ADD_Q) || (cached_type == TYPE_NEON_REDUC_ADD_Q) || (cached_type == TYPE_NEON_LOGIC_Q) || (cached_type == TYPE_NEON_NEG_Q) || (cached_type == TYPE_NEON_SUB_Q)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_ADD_LONG) || (cached_type == TYPE_NEON_SUB_LONG) || (cached_type == TYPE_NEON_ADD_HALVE) || (cached_type == TYPE_NEON_SUB_HALVE) || (cached_type == TYPE_NEON_SHIFT_IMM) || (cached_type == TYPE_NEON_SHIFT_REG) || (cached_type == TYPE_NEON_MINMAX) || (cached_type == TYPE_NEON_ABS) || (cached_type == TYPE_NEON_COMPARE) || (cached_type == TYPE_NEON_COMPARE_ZERO) || (cached_type == TYPE_NEON_TST)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_ADD_HALVE_Q) || (cached_type == TYPE_NEON_SUB_HALVE_Q) || (cached_type == TYPE_NEON_SHIFT_IMM_Q) || (cached_type == TYPE_NEON_SHIFT_REG_Q) || (cached_type == TYPE_NEON_MINMAX_Q) || (cached_type == TYPE_NEON_ABS_Q) || (cached_type == TYPE_NEON_COMPARE_Q) || (cached_type == TYPE_NEON_COMPARE_ZERO_Q) || (cached_type == TYPE_NEON_TST_Q) || (cached_type == TYPE_NEON_REDUC_ADD_LONG)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_SHIFT_ACC) || (cached_type == TYPE_NEON_REDUC_ADD_ACC) || (cached_type == TYPE_NEON_ABD) || (cached_type == TYPE_NEON_QADD) || (cached_type == TYPE_NEON_QSUB) || (cached_type == TYPE_NEON_QABS) || (cached_type == TYPE_NEON_QNEG) || (cached_type == TYPE_NEON_SAT_SHIFT_IMM) || (cached_type == TYPE_NEON_SAT_SHIFT_IMM_NARROW_Q) || (cached_type == TYPE_NEON_SAT_SHIFT_REG) || (cached_type == TYPE_NEON_REDUC_MINMAX)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_NEON_REDUC_MINMAX_Q))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_SHIFT_ACC_Q) || (cached_type == TYPE_NEON_REDUC_ADD_ACC_Q) || (cached_type == TYPE_NEON_ABD_Q) || (cached_type == TYPE_NEON_ABD_LONG) || (cached_type == TYPE_NEON_QADD_Q) || (cached_type == TYPE_NEON_QSUB_Q) || (cached_type == TYPE_NEON_QABS_Q) || (cached_type == TYPE_NEON_QNEG_Q) || (cached_type == TYPE_NEON_SAT_SHIFT_IMM_Q) || (cached_type == TYPE_NEON_SAT_SHIFT_REG_Q)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_MUL_B) || (cached_type == TYPE_NEON_MUL_H) || (cached_type == TYPE_NEON_MUL_S) || (cached_type == TYPE_NEON_MUL_H_SCALAR) || (cached_type == TYPE_NEON_MUL_S_SCALAR) || (cached_type == TYPE_NEON_SAT_MUL_B) || (cached_type == TYPE_NEON_SAT_MUL_H) || (cached_type == TYPE_NEON_SAT_MUL_S) || (cached_type == TYPE_NEON_SAT_MUL_H_SCALAR) || (cached_type == TYPE_NEON_SAT_MUL_S_SCALAR)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_MLA_B) || (cached_type == TYPE_NEON_MLA_H) || (cached_type == TYPE_NEON_MLA_S) || (cached_type == TYPE_NEON_MLA_H_SCALAR) || (cached_type == TYPE_NEON_MLA_S_SCALAR)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_MUL_B_Q) || (cached_type == TYPE_NEON_MUL_H_Q) || (cached_type == TYPE_NEON_MUL_S_Q) || (cached_type == TYPE_NEON_MUL_H_SCALAR_Q) || (cached_type == TYPE_NEON_MUL_S_SCALAR_Q) || (cached_type == TYPE_NEON_SAT_MUL_B_Q) || (cached_type == TYPE_NEON_SAT_MUL_H_Q) || (cached_type == TYPE_NEON_SAT_MUL_S_Q) || (cached_type == TYPE_NEON_MUL_B_LONG) || (cached_type == TYPE_NEON_MUL_H_LONG) || (cached_type == TYPE_NEON_MUL_S_LONG) || (cached_type == TYPE_NEON_MUL_D_LONG) || (cached_type == TYPE_NEON_MUL_H_SCALAR_LONG) || (cached_type == TYPE_NEON_MUL_S_SCALAR_LONG) || (cached_type == TYPE_NEON_SAT_MUL_B_LONG) || (cached_type == TYPE_NEON_SAT_MUL_H_LONG) || (cached_type == TYPE_NEON_SAT_MUL_S_LONG) || (cached_type == TYPE_NEON_SAT_MUL_H_SCALAR_Q) || (cached_type == TYPE_NEON_SAT_MUL_S_SCALAR_Q) || (cached_type == TYPE_NEON_SAT_MUL_H_SCALAR_LONG) || (cached_type == TYPE_NEON_SAT_MUL_S_SCALAR_LONG)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_MLA_B_Q) || (cached_type == TYPE_NEON_MLA_H_Q) || (cached_type == TYPE_NEON_MLA_S_Q) || (cached_type == TYPE_NEON_MLA_H_SCALAR_Q) || (cached_type == TYPE_NEON_MLA_S_SCALAR_Q) || (cached_type == TYPE_NEON_MLA_B_LONG) || (cached_type == TYPE_NEON_MLA_H_LONG) || (cached_type == TYPE_NEON_MLA_S_LONG) || (cached_type == TYPE_NEON_MLA_H_SCALAR_LONG) || (cached_type == TYPE_NEON_MLA_S_SCALAR_LONG) || (cached_type == TYPE_NEON_SAT_MLA_B_LONG) || (cached_type == TYPE_NEON_SAT_MLA_H_LONG) || (cached_type == TYPE_NEON_SAT_MLA_S_LONG) || (cached_type == TYPE_NEON_SAT_MLA_H_SCALAR_LONG) || (cached_type == TYPE_NEON_SAT_MLA_S_SCALAR_LONG)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_ADD_HALVE_NARROW_Q) || (cached_type == TYPE_NEON_SUB_HALVE_NARROW_Q) || (cached_type == TYPE_NEON_ARITH_ACC)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_ADD_WIDEN) || (cached_type == TYPE_NEON_SUB_WIDEN)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_NEON_ARITH_ACC_Q))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_LOAD1_1REG) || (cached_type == TYPE_NEON_LOAD1_1REG_Q) || (cached_type == TYPE_NEON_LOAD1_ALL_LANES) || (cached_type == TYPE_NEON_LOAD2_ONE_LANE)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_LOAD1_2REG) || (cached_type == TYPE_NEON_LOAD2_2REG) || (cached_type == TYPE_NEON_LOAD2_ALL_LANES)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_LOAD1_2REG_Q) || (cached_type == TYPE_NEON_LOAD2_2REG_Q) || (cached_type == TYPE_NEON_LOAD2_ALL_LANES_Q) || (cached_type == TYPE_NEON_LOAD3_ONE_LANE) || (cached_type == TYPE_NEON_LOAD4_ONE_LANE) || (cached_type == TYPE_NEON_LDP) || (cached_type == TYPE_NEON_LDP_Q)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_LOAD1_3REG) || (cached_type == TYPE_NEON_LOAD3_3REG) || (cached_type == TYPE_NEON_LOAD3_ALL_LANES)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_LOAD1_3REG_Q) || (cached_type == TYPE_NEON_LOAD3_3REG_Q) || (cached_type == TYPE_NEON_LOAD3_ALL_LANES_Q)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_LOAD1_4REG) || (cached_type == TYPE_NEON_LOAD4_4REG)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_LOAD1_4REG_Q) || (cached_type == TYPE_NEON_LOAD4_4REG_Q) || (cached_type == TYPE_NEON_LOAD4_ALL_LANES) || (cached_type == TYPE_NEON_LOAD4_ALL_LANES_Q)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_ALUS_SREG) || (cached_type == TYPE_ALUS_IMM) || (cached_type == TYPE_ALUS_SHIFT_IMM) || (cached_type == TYPE_CSEL) || (cached_type == TYPE_ADC_REG) || (cached_type == TYPE_ALU_IMM) || (cached_type == TYPE_ALU_SREG) || (cached_type == TYPE_ALU_SHIFT_IMM_LSL_1TO4) || (cached_type == TYPE_ALU_SHIFT_IMM_OTHER) || (cached_type == TYPE_ALU_EXT) || (cached_type == TYPE_ALUS_EXT) || (cached_type == TYPE_LOGIC_IMM) || (cached_type == TYPE_LOGIC_REG) || (cached_type == TYPE_LOGIC_SHIFT_IMM) || (cached_type == TYPE_LOGICS_IMM) || (cached_type == TYPE_LOGICS_REG) || (cached_type == TYPE_LOGICS_SHIFT_IMM) || (cached_type == TYPE_MOV_REG)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_NEON_FROM_GP))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_NEON_FROM_GP_Q))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_NEON_DUP_Q))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_NEON_TO_GP))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_BSL) || (cached_type == TYPE_NEON_DUP) || (cached_type == TYPE_NEON_EXT) || (cached_type == TYPE_NEON_INS) || (cached_type == TYPE_NEON_INS_Q) || (cached_type == TYPE_NEON_MOVE) || (cached_type == TYPE_NEON_REV) || (cached_type == TYPE_NEON_TBL1) || (cached_type == TYPE_NEON_PERMUTE) || (cached_type == TYPE_NEON_SHIFT_IMM_NARROW_Q)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_BSL_Q) || (cached_type == TYPE_NEON_EXT_Q) || (cached_type == TYPE_NEON_MOVE_Q) || (cached_type == TYPE_NEON_REV_Q) || (cached_type == TYPE_NEON_TBL1_Q) || (cached_type == TYPE_NEON_PERMUTE_Q)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_CLS) || (cached_type == TYPE_NEON_CNT) || (cached_type == TYPE_NEON_RBIT)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_CLS_Q) || (cached_type == TYPE_NEON_CNT_Q) || (cached_type == TYPE_NEON_RBIT_Q) || (cached_type == TYPE_NEON_TBL2)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_FP_RECPE_S) || (cached_type == TYPE_NEON_FP_RECPE_D) || (cached_type == TYPE_NEON_FP_RSQRTE_S) || (cached_type == TYPE_NEON_FP_RSQRTE_D) || (cached_type == TYPE_NEON_FP_RECPX_S) || (cached_type == TYPE_NEON_FP_RECPX_D)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_FP_RECPE_S_Q) || (cached_type == TYPE_NEON_FP_RECPE_D_Q) || (cached_type == TYPE_NEON_FP_RSQRTE_S_Q) || (cached_type == TYPE_NEON_FP_RSQRTE_D_Q)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_NEON_FP_RECPS_S))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_NEON_FP_RECPS_S_Q))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_FP_RECPS_D) || (cached_type == TYPE_NEON_FP_RSQRTS_D)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_FP_RECPS_D_Q) || (cached_type == TYPE_NEON_FP_RSQRTS_D_Q)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_TBL2_Q) || (cached_type == TYPE_NEON_TBL3)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_TBL3_Q) || (cached_type == TYPE_NEON_TBL4)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_NEON_TBL4_Q))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_STORE1_1REG) || (cached_type == TYPE_NEON_STORE1_1REG_Q) || (cached_type == TYPE_NEON_STORE1_ONE_LANE) || (cached_type == TYPE_NEON_STORE1_ONE_LANE_Q) || (cached_type == TYPE_NEON_STORE1_2REG) || (cached_type == TYPE_NEON_STORE2_2REG) || (cached_type == TYPE_NEON_STORE2_ONE_LANE) || (cached_type == TYPE_NEON_STORE2_ONE_LANE_Q) || (cached_type == TYPE_NEON_STP)))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_STORE1_2REG_Q) || (cached_type == TYPE_NEON_STORE1_3REG) || (cached_type == TYPE_NEON_STORE1_4REG) || (cached_type == TYPE_NEON_STORE2_2REG_Q) || (cached_type == TYPE_NEON_STORE3_3REG) || (cached_type == TYPE_NEON_STORE4_4REG) || (cached_type == TYPE_NEON_STORE3_ONE_LANE) || (cached_type == TYPE_NEON_STORE3_ONE_LANE_Q) || (cached_type == TYPE_NEON_STORE4_ONE_LANE) || (cached_type == TYPE_NEON_STORE4_ONE_LANE_Q) || (cached_type == TYPE_NEON_STP_Q)))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_STORE1_3REG_Q) || (cached_type == TYPE_NEON_STORE3_3REG_Q)))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_NEON_STORE1_4REG_Q) || (cached_type == TYPE_NEON_STORE4_4REG_Q)))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_BRANCH))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_CALL))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_CRYPTO_SHA1_FAST))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_CRYPTO_AESMC))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_CRYPTO_SHA1_XOR) || (cached_type == TYPE_CRYPTO_SHA256_FAST) || (cached_type == TYPE_CRYPTO_PMULL)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_CRYPTO_SHA1_SLOW))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_CRYPTO_SHA256_SLOW))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_CRYPTO_AESE))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_F_LOADS) || (cached_type == TYPE_F_LOADD)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_F_STORES) || (cached_type == TYPE_F_STORED)))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_FCMPS) || (cached_type == TYPE_FCMPD) || (cached_type == TYPE_FCCMPS) || (cached_type == TYPE_FCCMPD)))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_F_CVTF2I))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_FFARITHS) || (cached_type == TYPE_FFARITHD) || (cached_type == TYPE_FCSEL)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_F_MINMAXD) || (cached_type == TYPE_F_MINMAXS) || (cached_type == TYPE_F_RINTD) || (cached_type == TYPE_F_RINTS)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_FADDD) || (cached_type == TYPE_FADDS)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_F_CVT))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_FMULS))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_FMACS) || (cached_type == TYPE_FFMAS)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_FMULD))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_FMACD) || (cached_type == TYPE_FFMAD)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_FDIVS))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_FDIVD))
        {
	  return 11 /* 0xb */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_FSQRTS))
        {
	  return 12 /* 0xc */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_FSQRTD))
        {
	  return 22 /* 0x16 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_F_MRC))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_F_MCR))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_FMOV) || (cached_type == TYPE_FCONSTS) || (cached_type == TYPE_FCONSTD)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_F_CVTI2F))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_LOAD_4) || (cached_type == TYPE_LOAD_8) || (cached_type == TYPE_LOAD_16)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_BFX) || (cached_type == TYPE_BFM) || (cached_type == TYPE_EXTEND) || (cached_type == TYPE_ROTATE_IMM) || (cached_type == TYPE_SHIFT_IMM)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_CRC))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_CLZ) || (cached_type == TYPE_RBIT) || (cached_type == TYPE_REV)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_MUL))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_MLA) || (cached_type == TYPE_SMLAL) || (cached_type == TYPE_UMLAL)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_SMULL) || (cached_type == TYPE_UMULL)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_SDIV) || (cached_type == TYPE_UDIV)))
        {
	  return 11 /* 0xb */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_MOV_IMM) || (cached_type == TYPE_SHIFT_REG)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_ADR))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_TRAP) || (cached_type == TYPE_BLOCK)))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_MRS))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && (cached_type == TYPE_MULTIPLE))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_FALKOR)))) && ((cached_type == TYPE_STORE_4) || (cached_type == TYPE_STORE_8) || (cached_type == TYPE_STORE_16)))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_FP_NEG_S) || (cached_type == TYPE_NEON_FP_NEG_D) || (cached_type == TYPE_NEON_FP_ABS_S) || (cached_type == TYPE_NEON_FP_ABS_D) || (cached_type == TYPE_NEON_FP_NEG_S_Q) || (cached_type == TYPE_NEON_FP_NEG_D_Q) || (cached_type == TYPE_NEON_FP_ABS_S_Q) || (cached_type == TYPE_NEON_FP_ABS_D_Q)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_FP_MINMAX_S) || (cached_type == TYPE_NEON_FP_MINMAX_D) || (cached_type == TYPE_NEON_FP_REDUC_MINMAX_S) || (cached_type == TYPE_NEON_FP_REDUC_MINMAX_D) || (cached_type == TYPE_NEON_FP_COMPARE_S) || (cached_type == TYPE_NEON_FP_COMPARE_D) || (cached_type == TYPE_NEON_FP_ROUND_S) || (cached_type == TYPE_NEON_FP_ROUND_D) || (cached_type == TYPE_NEON_FP_MINMAX_S_Q) || (cached_type == TYPE_NEON_FP_MINMAX_D_Q) || (cached_type == TYPE_NEON_FP_COMPARE_S_Q) || (cached_type == TYPE_NEON_FP_COMPARE_D_Q) || (cached_type == TYPE_NEON_FP_ROUND_S_Q) || (cached_type == TYPE_NEON_FP_ROUND_D_Q)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_FP_REDUC_MINMAX_S_Q) || (cached_type == TYPE_NEON_FP_REDUC_MINMAX_D_Q) || (cached_type == TYPE_NEON_FP_ABD_S) || (cached_type == TYPE_NEON_FP_ABD_D) || (cached_type == TYPE_NEON_FP_ADDSUB_S) || (cached_type == TYPE_NEON_FP_ADDSUB_D) || (cached_type == TYPE_NEON_FP_REDUC_ADD_S) || (cached_type == TYPE_NEON_FP_REDUC_ADD_D) || (cached_type == TYPE_NEON_FP_ABD_S_Q) || (cached_type == TYPE_NEON_FP_ABD_D_Q) || (cached_type == TYPE_NEON_FP_ADDSUB_S_Q) || (cached_type == TYPE_NEON_FP_ADDSUB_D_Q) || (cached_type == TYPE_NEON_FP_REDUC_ADD_S_Q) || (cached_type == TYPE_NEON_FP_REDUC_ADD_D_Q)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_FP_TO_INT_S) || (cached_type == TYPE_NEON_FP_TO_INT_D) || (cached_type == TYPE_NEON_INT_TO_FP_S) || (cached_type == TYPE_NEON_INT_TO_FP_D) || (cached_type == TYPE_NEON_FP_CVT_WIDEN_H) || (cached_type == TYPE_NEON_FP_CVT_WIDEN_S) || (cached_type == TYPE_NEON_FP_TO_INT_S_Q) || (cached_type == TYPE_NEON_FP_TO_INT_D_Q) || (cached_type == TYPE_NEON_INT_TO_FP_S_Q) || (cached_type == TYPE_NEON_INT_TO_FP_D_Q)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_FP_MUL_S) || (cached_type == TYPE_NEON_FP_MUL_S_SCALAR) || (cached_type == TYPE_NEON_FP_MUL_S_Q) || (cached_type == TYPE_NEON_FP_MUL_S_SCALAR_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_FP_MLA_S) || (cached_type == TYPE_NEON_FP_MLA_S_SCALAR) || (cached_type == TYPE_NEON_FP_MLA_S_Q) || (cached_type == TYPE_NEON_FP_MLA_S_SCALAR_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_FP_MUL_D) || (cached_type == TYPE_NEON_FP_MUL_D_Q) || (cached_type == TYPE_NEON_FP_MUL_D_SCALAR_Q)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_FP_MLA_D) || (cached_type == TYPE_NEON_FP_MLA_D_Q) || (cached_type == TYPE_NEON_FP_MLA_D_SCALAR_Q)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_FP_CVT_NARROW_S_Q) || (cached_type == TYPE_NEON_FP_CVT_NARROW_D_Q)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_NEON_FP_DIV_S))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_NEON_FP_DIV_D))
        {
	  return 11 /* 0xb */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_NEON_FP_DIV_S_Q))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_NEON_FP_DIV_D_Q))
        {
	  return 11 /* 0xb */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_NEON_FP_SQRT_S))
        {
	  return 12 /* 0xc */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_NEON_FP_SQRT_D))
        {
	  return 22 /* 0x16 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_NEON_FP_SQRT_S_Q))
        {
	  return 12 /* 0xc */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_NEON_FP_SQRT_D_Q))
        {
	  return 22 /* 0x16 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_ADD) || (cached_type == TYPE_NEON_REDUC_ADD) || (cached_type == TYPE_NEON_LOGIC) || (cached_type == TYPE_NEON_NEG) || (cached_type == TYPE_NEON_SUB) || (cached_type == TYPE_NEON_ADD_Q) || (cached_type == TYPE_NEON_REDUC_ADD_Q) || (cached_type == TYPE_NEON_LOGIC_Q) || (cached_type == TYPE_NEON_NEG_Q) || (cached_type == TYPE_NEON_SUB_Q)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_ADD_LONG) || (cached_type == TYPE_NEON_SUB_LONG) || (cached_type == TYPE_NEON_ADD_HALVE) || (cached_type == TYPE_NEON_SUB_HALVE) || (cached_type == TYPE_NEON_SHIFT_IMM) || (cached_type == TYPE_NEON_SHIFT_REG) || (cached_type == TYPE_NEON_MINMAX) || (cached_type == TYPE_NEON_ABS) || (cached_type == TYPE_NEON_COMPARE) || (cached_type == TYPE_NEON_COMPARE_ZERO) || (cached_type == TYPE_NEON_TST) || (cached_type == TYPE_NEON_SHIFT_IMM_LONG) || (cached_type == TYPE_NEON_REDUC_ADD_LONG) || (cached_type == TYPE_NEON_ADD_HALVE_Q) || (cached_type == TYPE_NEON_SUB_HALVE_Q) || (cached_type == TYPE_NEON_SHIFT_IMM_Q) || (cached_type == TYPE_NEON_SHIFT_REG_Q) || (cached_type == TYPE_NEON_MINMAX_Q) || (cached_type == TYPE_NEON_ABS_Q) || (cached_type == TYPE_NEON_COMPARE_Q) || (cached_type == TYPE_NEON_COMPARE_ZERO_Q) || (cached_type == TYPE_NEON_TST_Q)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_SHIFT_ACC) || (cached_type == TYPE_NEON_REDUC_ADD_ACC) || (cached_type == TYPE_NEON_ABD) || (cached_type == TYPE_NEON_QADD) || (cached_type == TYPE_NEON_QSUB) || (cached_type == TYPE_NEON_QABS) || (cached_type == TYPE_NEON_QNEG) || (cached_type == TYPE_NEON_SAT_SHIFT_IMM) || (cached_type == TYPE_NEON_SAT_SHIFT_IMM_NARROW_Q) || (cached_type == TYPE_NEON_SAT_SHIFT_REG) || (cached_type == TYPE_NEON_SHIFT_ACC_Q) || (cached_type == TYPE_NEON_REDUC_ADD_ACC_Q) || (cached_type == TYPE_NEON_ABD_Q) || (cached_type == TYPE_NEON_ABD_LONG) || (cached_type == TYPE_NEON_QADD_Q) || (cached_type == TYPE_NEON_QSUB_Q) || (cached_type == TYPE_NEON_QABS_Q) || (cached_type == TYPE_NEON_QNEG_Q) || (cached_type == TYPE_NEON_SAT_SHIFT_IMM_Q) || (cached_type == TYPE_NEON_SAT_SHIFT_REG_Q) || (cached_type == TYPE_NEON_ADD_HALVE_NARROW_Q) || (cached_type == TYPE_NEON_SUB_HALVE_NARROW_Q)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_REDUC_MINMAX) || (cached_type == TYPE_NEON_REDUC_MINMAX_Q) || (cached_type == TYPE_NEON_ARITH_ACC) || (cached_type == TYPE_NEON_ARITH_ACC_Q)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_MUL_B) || (cached_type == TYPE_NEON_MUL_H) || (cached_type == TYPE_NEON_MUL_S) || (cached_type == TYPE_NEON_MUL_H_SCALAR) || (cached_type == TYPE_NEON_MUL_S_SCALAR) || (cached_type == TYPE_NEON_SAT_MUL_B) || (cached_type == TYPE_NEON_SAT_MUL_H) || (cached_type == TYPE_NEON_SAT_MUL_S) || (cached_type == TYPE_NEON_SAT_MUL_H_SCALAR) || (cached_type == TYPE_NEON_SAT_MUL_S_SCALAR) || (cached_type == TYPE_NEON_MUL_B_Q) || (cached_type == TYPE_NEON_MUL_H_Q) || (cached_type == TYPE_NEON_MUL_S_Q) || (cached_type == TYPE_NEON_MUL_H_SCALAR_Q) || (cached_type == TYPE_NEON_MUL_S_SCALAR_Q) || (cached_type == TYPE_NEON_SAT_MUL_B_Q) || (cached_type == TYPE_NEON_SAT_MUL_H_Q) || (cached_type == TYPE_NEON_SAT_MUL_S_Q) || (cached_type == TYPE_NEON_MUL_B_LONG) || (cached_type == TYPE_NEON_MUL_H_LONG) || (cached_type == TYPE_NEON_MUL_S_LONG) || (cached_type == TYPE_NEON_MUL_D_LONG) || (cached_type == TYPE_NEON_MUL_H_SCALAR_LONG) || (cached_type == TYPE_NEON_MUL_S_SCALAR_LONG) || (cached_type == TYPE_NEON_SAT_MUL_B_LONG) || (cached_type == TYPE_NEON_SAT_MUL_H_LONG) || (cached_type == TYPE_NEON_SAT_MUL_S_LONG) || (cached_type == TYPE_NEON_SAT_MUL_H_SCALAR_Q) || (cached_type == TYPE_NEON_SAT_MUL_S_SCALAR_Q) || (cached_type == TYPE_NEON_SAT_MUL_H_SCALAR_LONG) || (cached_type == TYPE_NEON_SAT_MUL_S_SCALAR_LONG)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_MLA_B) || (cached_type == TYPE_NEON_MLA_H) || (cached_type == TYPE_NEON_MLA_S) || (cached_type == TYPE_NEON_MLA_H_SCALAR) || (cached_type == TYPE_NEON_MLA_S_SCALAR) || (cached_type == TYPE_NEON_MLA_B_Q) || (cached_type == TYPE_NEON_MLA_H_Q) || (cached_type == TYPE_NEON_MLA_S_Q) || (cached_type == TYPE_NEON_MLA_H_SCALAR_Q) || (cached_type == TYPE_NEON_MLA_S_SCALAR_Q) || (cached_type == TYPE_NEON_MLA_B_LONG) || (cached_type == TYPE_NEON_MLA_H_LONG) || (cached_type == TYPE_NEON_MLA_S_LONG) || (cached_type == TYPE_NEON_MLA_H_SCALAR_LONG) || (cached_type == TYPE_NEON_MLA_S_SCALAR_LONG) || (cached_type == TYPE_NEON_SAT_MLA_B_LONG) || (cached_type == TYPE_NEON_SAT_MLA_H_LONG) || (cached_type == TYPE_NEON_SAT_MLA_S_LONG) || (cached_type == TYPE_NEON_SAT_MLA_H_SCALAR_LONG) || (cached_type == TYPE_NEON_SAT_MLA_S_SCALAR_LONG)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_ADD_WIDEN) || (cached_type == TYPE_NEON_SUB_WIDEN)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_LOAD1_1REG) || (cached_type == TYPE_NEON_LOAD1_1REG_Q) || (cached_type == TYPE_NEON_LOAD1_ALL_LANES) || (cached_type == TYPE_NEON_LOAD2_ONE_LANE)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_LOAD1_2REG) || (cached_type == TYPE_NEON_LOAD2_2REG) || (cached_type == TYPE_NEON_LOAD2_ALL_LANES)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_LOAD1_2REG_Q) || (cached_type == TYPE_NEON_LOAD2_2REG_Q) || (cached_type == TYPE_NEON_LOAD2_ALL_LANES_Q) || (cached_type == TYPE_NEON_LOAD3_ONE_LANE) || (cached_type == TYPE_NEON_LOAD4_ONE_LANE) || (cached_type == TYPE_NEON_LDP) || (cached_type == TYPE_NEON_LDP_Q)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_LOAD1_3REG) || (cached_type == TYPE_NEON_LOAD3_3REG) || (cached_type == TYPE_NEON_LOAD3_ALL_LANES)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_LOAD1_3REG_Q) || (cached_type == TYPE_NEON_LOAD3_3REG_Q) || (cached_type == TYPE_NEON_LOAD3_ALL_LANES_Q)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_LOAD1_4REG) || (cached_type == TYPE_NEON_LOAD4_4REG)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_LOAD1_4REG_Q) || (cached_type == TYPE_NEON_LOAD4_4REG_Q) || (cached_type == TYPE_NEON_LOAD4_ALL_LANES) || (cached_type == TYPE_NEON_LOAD4_ALL_LANES_Q)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_ALUS_SREG) || (cached_type == TYPE_ALUS_IMM) || (cached_type == TYPE_ALUS_SHIFT_IMM) || (cached_type == TYPE_CSEL) || (cached_type == TYPE_ADC_REG) || (cached_type == TYPE_ALU_IMM) || (cached_type == TYPE_ALU_SREG) || (cached_type == TYPE_ALU_SHIFT_IMM_LSL_1TO4) || (cached_type == TYPE_ALU_SHIFT_IMM_OTHER) || (cached_type == TYPE_ALU_EXT) || (cached_type == TYPE_ALUS_EXT) || (cached_type == TYPE_LOGIC_IMM) || (cached_type == TYPE_LOGIC_REG) || (cached_type == TYPE_LOGIC_SHIFT_IMM) || (cached_type == TYPE_LOGICS_IMM) || (cached_type == TYPE_LOGICS_REG) || (cached_type == TYPE_LOGICS_SHIFT_IMM) || (cached_type == TYPE_MOV_REG)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_NEON_FROM_GP))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_NEON_FROM_GP_Q))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_NEON_DUP_Q))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_NEON_TO_GP))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_BSL) || (cached_type == TYPE_NEON_DUP) || (cached_type == TYPE_NEON_EXT) || (cached_type == TYPE_NEON_INS) || (cached_type == TYPE_NEON_INS_Q) || (cached_type == TYPE_NEON_MOVE) || (cached_type == TYPE_NEON_REV) || (cached_type == TYPE_NEON_TBL1) || (cached_type == TYPE_NEON_PERMUTE) || (cached_type == TYPE_NEON_SHIFT_IMM_NARROW_Q) || (cached_type == TYPE_NEON_BSL_Q) || (cached_type == TYPE_NEON_EXT_Q) || (cached_type == TYPE_NEON_MOVE_Q) || (cached_type == TYPE_NEON_REV_Q) || (cached_type == TYPE_NEON_TBL1_Q) || (cached_type == TYPE_NEON_PERMUTE_Q) || (cached_type == TYPE_NEON_TBL2_Q) || (cached_type == TYPE_NEON_TBL2)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_CLS) || (cached_type == TYPE_NEON_CNT) || (cached_type == TYPE_NEON_RBIT) || (cached_type == TYPE_NEON_CLS_Q) || (cached_type == TYPE_NEON_CNT_Q) || (cached_type == TYPE_NEON_RBIT_Q) || (cached_type == TYPE_NEON_TBL2) || (cached_type == TYPE_NEON_TBL3_Q) || (cached_type == TYPE_NEON_TBL3)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_FP_RECPE_S) || (cached_type == TYPE_NEON_FP_RECPE_D) || (cached_type == TYPE_NEON_FP_RSQRTE_S) || (cached_type == TYPE_NEON_FP_RSQRTE_D) || (cached_type == TYPE_NEON_FP_RECPX_S) || (cached_type == TYPE_NEON_FP_RECPX_D) || (cached_type == TYPE_NEON_FP_RECPE_S_Q) || (cached_type == TYPE_NEON_FP_RECPE_D_Q) || (cached_type == TYPE_NEON_FP_RSQRTE_S_Q) || (cached_type == TYPE_NEON_FP_RSQRTE_D_Q) || (cached_type == TYPE_NEON_TBL4_Q) || (cached_type == TYPE_NEON_TBL4)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_FP_RECPS_S) || (cached_type == TYPE_NEON_FP_RECPS_S_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_FP_RECPS_D) || (cached_type == TYPE_NEON_FP_RSQRTS_D) || (cached_type == TYPE_NEON_FP_RECPS_D_Q) || (cached_type == TYPE_NEON_FP_RSQRTS_D_Q)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_STORE1_1REG) || (cached_type == TYPE_NEON_STORE1_1REG_Q) || (cached_type == TYPE_NEON_STORE1_ONE_LANE) || (cached_type == TYPE_NEON_STORE1_ONE_LANE_Q) || (cached_type == TYPE_NEON_STORE1_2REG) || (cached_type == TYPE_NEON_STORE2_2REG) || (cached_type == TYPE_NEON_STORE2_ONE_LANE) || (cached_type == TYPE_NEON_STORE2_ONE_LANE_Q) || (cached_type == TYPE_NEON_STP)))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_STORE1_2REG_Q) || (cached_type == TYPE_NEON_STORE1_3REG) || (cached_type == TYPE_NEON_STORE1_4REG) || (cached_type == TYPE_NEON_STORE2_2REG_Q) || (cached_type == TYPE_NEON_STORE3_3REG) || (cached_type == TYPE_NEON_STORE4_4REG) || (cached_type == TYPE_NEON_STORE3_ONE_LANE) || (cached_type == TYPE_NEON_STORE3_ONE_LANE_Q) || (cached_type == TYPE_NEON_STORE4_ONE_LANE) || (cached_type == TYPE_NEON_STORE4_ONE_LANE_Q) || (cached_type == TYPE_NEON_STP_Q)))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_STORE1_3REG_Q) || (cached_type == TYPE_NEON_STORE3_3REG_Q)))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_NEON_STORE1_4REG_Q) || (cached_type == TYPE_NEON_STORE4_4REG_Q)))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_BRANCH))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_CALL))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_CRYPTO_SHA1_FAST))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_CRYPTO_AESMC))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_CRYPTO_SHA1_XOR) || (cached_type == TYPE_CRYPTO_SHA256_FAST) || (cached_type == TYPE_CRYPTO_PMULL) || (cached_type == TYPE_CRYPTO_AESE)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_CRYPTO_SHA1_SLOW))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_CRYPTO_SHA256_SLOW))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_F_LOADS) || (cached_type == TYPE_F_LOADD)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_F_STORES) || (cached_type == TYPE_F_STORED)))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_FCMPS) || (cached_type == TYPE_FCMPD) || (cached_type == TYPE_FCCMPS) || (cached_type == TYPE_FCCMPD)))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_F_CVTF2I))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_FFARITHS) || (cached_type == TYPE_FFARITHD) || (cached_type == TYPE_FCSEL)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_F_MINMAXD) || (cached_type == TYPE_F_MINMAXS) || (cached_type == TYPE_F_RINTD) || (cached_type == TYPE_F_RINTS)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_FADDD) || (cached_type == TYPE_FADDS)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_F_CVT))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_FMULS))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_FMACS) || (cached_type == TYPE_FFMAS)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_FMULD))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_FMACD) || (cached_type == TYPE_FFMAD)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_FDIVS))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_FDIVD))
        {
	  return 11 /* 0xb */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_FSQRTS))
        {
	  return 12 /* 0xc */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_FSQRTD))
        {
	  return 22 /* 0x16 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_F_MRC))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_F_MCR))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_FMOV) || (cached_type == TYPE_FCONSTS) || (cached_type == TYPE_FCONSTD)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_F_CVTI2F))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_LOAD_4) || (cached_type == TYPE_LOAD_8) || (cached_type == TYPE_LOAD_16)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_BFX) || (cached_type == TYPE_BFM) || (cached_type == TYPE_EXTEND) || (cached_type == TYPE_ROTATE_IMM) || (cached_type == TYPE_SHIFT_IMM)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_CRC))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_CLZ) || (cached_type == TYPE_RBIT) || (cached_type == TYPE_REV)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_MUL))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_MLA) || (cached_type == TYPE_SMLAL) || (cached_type == TYPE_UMLAL)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_SMULL) || (cached_type == TYPE_UMULL)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_SDIV) || (cached_type == TYPE_UDIV)))
        {
	  return 11 /* 0xb */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_MOV_IMM) || (cached_type == TYPE_SHIFT_REG) || (cached_type == TYPE_ADR)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_TRAP) || (cached_type == TYPE_BLOCK)))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_MRS))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && (cached_type == TYPE_MULTIPLE))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_SAPHIRA)))) && ((cached_type == TYPE_STORE_4) || (cached_type == TYPE_STORE_8) || (cached_type == TYPE_STORE_16)))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_ADC_IMM) || (cached_type == TYPE_ADC_REG) || (cached_type == TYPE_ADR) || (cached_type == TYPE_ALU_IMM) || (cached_type == TYPE_ALU_SREG) || (cached_type == TYPE_ALUS_IMM) || (cached_type == TYPE_ALUS_SREG) || (cached_type == TYPE_EXTEND) || (cached_type == TYPE_LOGIC_IMM) || (cached_type == TYPE_LOGIC_REG) || (cached_type == TYPE_LOGICS_IMM) || (cached_type == TYPE_LOGICS_REG) || (cached_type == TYPE_MOV_IMM) || (cached_type == TYPE_MOV_REG)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_BFM) || (cached_type == TYPE_BFX) || (cached_type == TYPE_EXTEND) || (cached_type == TYPE_ROTATE_IMM) || (cached_type == TYPE_SHIFT_IMM) || (cached_type == TYPE_SHIFT_REG) || (cached_type == TYPE_RBIT) || (cached_type == TYPE_REV)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_ALU_EXT) || (cached_type == TYPE_ALU_SHIFT_IMM_LSL_1TO4) || (cached_type == TYPE_ALU_SHIFT_IMM_OTHER) || (cached_type == TYPE_ALU_SHIFT_REG) || (cached_type == TYPE_ALUS_EXT) || (cached_type == TYPE_LOGIC_SHIFT_IMM) || (cached_type == TYPE_LOGIC_SHIFT_REG) || (cached_type == TYPE_LOGICS_SHIFT_IMM) || (cached_type == TYPE_LOGICS_SHIFT_REG) || (cached_type == TYPE_ALUS_SHIFT_IMM)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && (cached_type == TYPE_CSEL))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_MUL) || (cached_type == TYPE_MULS) || (cached_type == TYPE_MLA) || (cached_type == TYPE_MLAS) || (cached_type == TYPE_CLZ) || (cached_type == TYPE_SMULL) || (cached_type == TYPE_UMULL) || (cached_type == TYPE_SMLAL) || (cached_type == TYPE_UMLAL)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && (cached_type == TYPE_CRC))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_UDIV) || (cached_type == TYPE_SDIV)))
        {
	  return 22 /* 0x16 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && (cached_type == TYPE_STORE_4))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_STORE_8) || (cached_type == TYPE_STORE_16)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_LOAD_4) || (cached_type == TYPE_LOAD_8) || (cached_type == TYPE_LOAD_16)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_BRANCH) || (cached_type == TYPE_TRAP) || (cached_type == TYPE_CALL)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_FADDD) || (cached_type == TYPE_FADDS)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_FCONSTS) || (cached_type == TYPE_FCONSTD)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_FMOV) || (cached_type == TYPE_F_MINMAXS) || (cached_type == TYPE_F_MINMAXD)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_FFARITHS) || (cached_type == TYPE_FFARITHD)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && (cached_type == TYPE_FCSEL))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_F_MRC) || (cached_type == TYPE_F_MCR)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_FCMPS) || (cached_type == TYPE_FCMPD) || (cached_type == TYPE_FCCMPS) || (cached_type == TYPE_FCCMPD)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_FMACS) || (cached_type == TYPE_FMACD) || (cached_type == TYPE_FMULS) || (cached_type == TYPE_FMULD)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && (cached_type == TYPE_FDIVS))
        {
	  return 12 /* 0xc */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && (cached_type == TYPE_FDIVD))
        {
	  return 22 /* 0x16 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && (cached_type == TYPE_FSQRTS))
        {
	  return 17 /* 0x11 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && (cached_type == TYPE_FSQRTD))
        {
	  return 31 /* 0x1f */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_F_CVT) || (cached_type == TYPE_F_RINTS) || (cached_type == TYPE_F_RINTD)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_F_CVTF2I) || (cached_type == TYPE_F_CVTI2F)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_F_LOADD) || (cached_type == TYPE_F_LOADS) || (cached_type == TYPE_NEON_LOAD1_1REG) || (cached_type == TYPE_NEON_LOAD1_1REG_Q) || (cached_type == TYPE_NEON_LOAD1_2REG)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && (cached_type == TYPE_NEON_LOAD1_2REG_Q))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_F_STORED) || (cached_type == TYPE_F_STORES) || (cached_type == TYPE_NEON_STORE1_1REG) || (cached_type == TYPE_NEON_STORE1_1REG_Q) || (cached_type == TYPE_NEON_STORE1_ONE_LANE) || (cached_type == TYPE_NEON_STORE1_ONE_LANE_Q)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && (cached_type == TYPE_NEON_STORE1_2REG))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && (cached_type == TYPE_NEON_STORE1_2REG_Q))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && (cached_type == TYPE_NEON_LOAD1_ALL_LANES))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_NEON_LOGIC) || (cached_type == TYPE_NEON_BSL) || (cached_type == TYPE_NEON_FP_COMPARE_S) || (cached_type == TYPE_NEON_FP_COMPARE_D) || (cached_type == TYPE_NEON_MOVE) || (cached_type == TYPE_NEON_DUP) || (cached_type == TYPE_NEON_INS) || (cached_type == TYPE_NEON_FROM_GP) || (cached_type == TYPE_NEON_TO_GP) || (cached_type == TYPE_NEON_ABS) || (cached_type == TYPE_NEON_NEG) || (cached_type == TYPE_NEON_FP_NEG_S) || (cached_type == TYPE_NEON_FP_ABS_S)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_NEON_LOGIC_Q) || (cached_type == TYPE_NEON_BSL_Q) || (cached_type == TYPE_NEON_FP_COMPARE_S_Q) || (cached_type == TYPE_NEON_FP_COMPARE_D_Q) || (cached_type == TYPE_NEON_MOVE_Q) || (cached_type == TYPE_NEON_DUP_Q) || (cached_type == TYPE_NEON_INS_Q) || (cached_type == TYPE_NEON_FROM_GP_Q) || (cached_type == TYPE_NEON_TO_GP_Q) || (cached_type == TYPE_NEON_ABS_Q) || (cached_type == TYPE_NEON_NEG_Q) || (cached_type == TYPE_NEON_FP_NEG_S_Q) || (cached_type == TYPE_NEON_FP_NEG_D_Q) || (cached_type == TYPE_NEON_FP_ABS_S_Q) || (cached_type == TYPE_NEON_FP_ABS_D_Q)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_NEON_REDUC_ADD) || (cached_type == TYPE_NEON_REDUC_MINMAX) || (cached_type == TYPE_NEON_FP_REDUC_ADD_S) || (cached_type == TYPE_NEON_FP_REDUC_ADD_D) || (cached_type == TYPE_NEON_FP_TO_INT_S) || (cached_type == TYPE_NEON_FP_TO_INT_D) || (cached_type == TYPE_NEON_ADD_HALVE) || (cached_type == TYPE_NEON_SUB_HALVE) || (cached_type == TYPE_NEON_QADD) || (cached_type == TYPE_NEON_COMPARE) || (cached_type == TYPE_NEON_COMPARE_ZERO) || (cached_type == TYPE_NEON_MINMAX) || (cached_type == TYPE_NEON_ABD) || (cached_type == TYPE_NEON_ADD) || (cached_type == TYPE_NEON_SUB) || (cached_type == TYPE_NEON_FP_MINMAX_S) || (cached_type == TYPE_NEON_FP_MINMAX_D) || (cached_type == TYPE_NEON_CLS) || (cached_type == TYPE_NEON_QABS) || (cached_type == TYPE_NEON_QNEG) || (cached_type == TYPE_NEON_FP_ADDSUB_S) || (cached_type == TYPE_NEON_FP_ADDSUB_D) || (cached_type == TYPE_NEON_ARITH_ACC) || (cached_type == TYPE_NEON_REV) || (cached_type == TYPE_NEON_FP_ABD_S) || (cached_type == TYPE_NEON_FP_ABD_D) || (cached_type == TYPE_NEON_FP_REDUC_MINMAX_S)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_NEON_REDUC_ADD_Q) || (cached_type == TYPE_NEON_REDUC_MINMAX_Q) || (cached_type == TYPE_NEON_FP_REDUC_ADD_S_Q) || (cached_type == TYPE_NEON_FP_REDUC_ADD_D_Q) || (cached_type == TYPE_NEON_FP_TO_INT_S_Q) || (cached_type == TYPE_NEON_FP_TO_INT_D_Q) || (cached_type == TYPE_NEON_ADD_HALVE_Q) || (cached_type == TYPE_NEON_SUB_HALVE_Q) || (cached_type == TYPE_NEON_QADD_Q) || (cached_type == TYPE_NEON_COMPARE_Q) || (cached_type == TYPE_NEON_COMPARE_ZERO_Q) || (cached_type == TYPE_NEON_MINMAX_Q) || (cached_type == TYPE_NEON_ABD_Q) || (cached_type == TYPE_NEON_ADD_Q) || (cached_type == TYPE_NEON_SUB_Q) || (cached_type == TYPE_NEON_FP_MINMAX_S_Q) || (cached_type == TYPE_NEON_FP_MINMAX_D_Q) || (cached_type == TYPE_NEON_CLS_Q) || (cached_type == TYPE_NEON_QABS_Q) || (cached_type == TYPE_NEON_QNEG_Q) || (cached_type == TYPE_NEON_FP_ADDSUB_S_Q) || (cached_type == TYPE_NEON_FP_ADDSUB_D_Q) || (cached_type == TYPE_NEON_ADD_LONG) || (cached_type == TYPE_NEON_SUB_LONG) || (cached_type == TYPE_NEON_FP_ABD_S_Q) || (cached_type == TYPE_NEON_FP_ABD_D_Q) || (cached_type == TYPE_NEON_ARITH_ACC_Q) || (cached_type == TYPE_NEON_REV_Q) || (cached_type == TYPE_NEON_FP_REDUC_MINMAX_S_Q) || (cached_type == TYPE_NEON_FP_REDUC_MINMAX_D_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_NEON_FP_MUL_S) || (cached_type == TYPE_NEON_FP_MUL_D) || (cached_type == TYPE_NEON_FP_MLA_S) || (cached_type == TYPE_NEON_FP_MLA_D) || (cached_type == TYPE_NEON_MLA_B) || (cached_type == TYPE_NEON_MLA_H) || (cached_type == TYPE_NEON_MLA_S) || (cached_type == TYPE_NEON_MLA_H_SCALAR) || (cached_type == TYPE_NEON_MLA_S_SCALAR) || (cached_type == TYPE_NEON_EXT) || (cached_type == TYPE_NEON_SHIFT_IMM) || (cached_type == TYPE_NEON_PERMUTE) || (cached_type == TYPE_NEON_INT_TO_FP_S) || (cached_type == TYPE_NEON_INT_TO_FP_D) || (cached_type == TYPE_NEON_SHIFT_REG) || (cached_type == TYPE_NEON_SAT_SHIFT_REG) || (cached_type == TYPE_NEON_SHIFT_ACC) || (cached_type == TYPE_NEON_MUL_B) || (cached_type == TYPE_NEON_MUL_H) || (cached_type == TYPE_NEON_MUL_S) || (cached_type == TYPE_NEON_MUL_H_SCALAR) || (cached_type == TYPE_NEON_MUL_S_SCALAR) || (cached_type == TYPE_NEON_FP_MUL_S_SCALAR) || (cached_type == TYPE_NEON_FP_MLA_S_SCALAR)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_NEON_FP_MUL_S_Q) || (cached_type == TYPE_NEON_FP_MUL_D_Q) || (cached_type == TYPE_NEON_FP_MLA_S_Q) || (cached_type == TYPE_NEON_FP_MLA_D_Q) || (cached_type == TYPE_NEON_MLA_B_Q) || (cached_type == TYPE_NEON_MLA_H_Q) || (cached_type == TYPE_NEON_MLA_S_Q) || (cached_type == TYPE_NEON_MLA_H_SCALAR_Q) || (cached_type == TYPE_NEON_MLA_S_SCALAR_Q) || (cached_type == TYPE_NEON_EXT_Q) || (cached_type == TYPE_NEON_SHIFT_IMM_Q) || (cached_type == TYPE_NEON_PERMUTE_Q) || (cached_type == TYPE_NEON_INT_TO_FP_S_Q) || (cached_type == TYPE_NEON_INT_TO_FP_D_Q) || (cached_type == TYPE_NEON_SHIFT_REG_Q) || (cached_type == TYPE_NEON_SAT_SHIFT_REG_Q) || (cached_type == TYPE_NEON_SHIFT_ACC_Q) || (cached_type == TYPE_NEON_SHIFT_IMM_LONG) || (cached_type == TYPE_NEON_MUL_B_Q) || (cached_type == TYPE_NEON_MUL_H_Q) || (cached_type == TYPE_NEON_MUL_S_Q) || (cached_type == TYPE_NEON_MUL_H_SCALAR_Q) || (cached_type == TYPE_NEON_MUL_S_SCALAR_Q) || (cached_type == TYPE_NEON_FP_MUL_S_SCALAR_Q) || (cached_type == TYPE_NEON_FP_MUL_D_SCALAR_Q) || (cached_type == TYPE_NEON_MUL_B_LONG) || (cached_type == TYPE_NEON_MUL_H_LONG) || (cached_type == TYPE_NEON_MUL_S_LONG) || (cached_type == TYPE_NEON_SHIFT_IMM_NARROW_Q) || (cached_type == TYPE_NEON_FP_CVT_WIDEN_S) || (cached_type == TYPE_NEON_FP_CVT_NARROW_D_Q) || (cached_type == TYPE_NEON_FP_MLA_S_SCALAR_Q) || (cached_type == TYPE_NEON_FP_MLA_D_SCALAR_Q)))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && (cached_type == TYPE_CRYPTO_AESE))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && (cached_type == TYPE_CRYPTO_AESMC))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && (cached_type == TYPE_NEON_TBL1))
        {
	  return 160 /* 0xa0 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && (cached_type == TYPE_NEON_TBL1_Q))
        {
	  return 320 /* 0x140 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) && ((cached_type == TYPE_UNTYPED) || (cached_type == TYPE_MULTIPLE)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && (cached_type == TYPE_BRANCH))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && (cached_type == TYPE_CALL))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_F_LOADD) || (cached_type == TYPE_F_LOADS)))
        {
	  return 10 /* 0xa */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_F_STORED) || (cached_type == TYPE_F_STORES)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_FMOV) || (cached_type == TYPE_FCONSTS) || (cached_type == TYPE_FCONSTD)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && (cached_type == TYPE_F_MCR))
        {
	  return 10 /* 0xa */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && (cached_type == TYPE_F_MRC))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && (cached_type == TYPE_LOAD_16))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && (cached_type == TYPE_STORE_16))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_LOAD_4) || (cached_type == TYPE_LOAD_8)) && (get_attr_fp (insn) == FP_YES))
        {
	  return 10 /* 0xa */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_LOAD_4) || (cached_type == TYPE_LOAD_8)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_STORE_4) || (cached_type == TYPE_STORE_8)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_MOV_REG) || (cached_type == TYPE_MOV_IMM) || (cached_type == TYPE_MRS)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && (cached_type == TYPE_CSEL))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_ALU_IMM) || (cached_type == TYPE_ALU_SREG) || (cached_type == TYPE_ALU_SHIFT_IMM_LSL_1TO4) || (cached_type == TYPE_ALU_SHIFT_IMM_OTHER) || (cached_type == TYPE_ALU_EXT) || (cached_type == TYPE_ADC_REG) || (cached_type == TYPE_LOGIC_IMM) || (cached_type == TYPE_LOGIC_REG) || (cached_type == TYPE_LOGIC_SHIFT_IMM) || (cached_type == TYPE_CLZ) || (cached_type == TYPE_RBIT) || (cached_type == TYPE_ADR) || (cached_type == TYPE_MOV_REG) || (cached_type == TYPE_SHIFT_IMM) || (cached_type == TYPE_MOV_IMM) || (cached_type == TYPE_EXTEND) || (cached_type == TYPE_MULTIPLE)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && (cached_type == TYPE_SHIFT_REG))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && (cached_type == TYPE_REV))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_ALUS_IMM) || (cached_type == TYPE_ALUS_SREG) || (cached_type == TYPE_ALUS_SHIFT_IMM) || (cached_type == TYPE_ALUS_EXT) || (cached_type == TYPE_LOGICS_IMM) || (cached_type == TYPE_LOGICS_REG) || (cached_type == TYPE_LOGICS_SHIFT_IMM)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_mul32 = get_attr_mul32 (insn)) == MUL32_YES))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_widen_mul64 = get_attr_widen_mul64 (insn)) == WIDEN_MUL64_YES))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_SDIV) || (cached_type == TYPE_UDIV)))
        {
	  return 34 /* 0x22 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_FCMPD) || (cached_type == TYPE_FCMPS) || (cached_type == TYPE_FCCMPD) || (cached_type == TYPE_FCCMPS)))
        {
	  return 10 /* 0xa */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && (cached_type == TYPE_FCSEL))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && (cached_type == TYPE_BFX))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && (cached_type == TYPE_BFM))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_F_RINTD) || (cached_type == TYPE_F_RINTS)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && (cached_type == TYPE_F_CVT))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && (cached_type == TYPE_F_CVTF2I))
        {
	  return 11 /* 0xb */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && (cached_type == TYPE_F_CVTI2F))
        {
	  return 14 /* 0xe */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_FADDD) || (cached_type == TYPE_FADDS) || (cached_type == TYPE_FMULD) || (cached_type == TYPE_FMULS)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_FDIVS) || (cached_type == TYPE_FSQRTS)))
        {
	  return 22 /* 0x16 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && (cached_type == TYPE_FDIVD))
        {
	  return 28 /* 0x1c */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && (cached_type == TYPE_FSQRTD))
        {
	  return 28 /* 0x1c */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_FFARITHD) || (cached_type == TYPE_FFARITHS)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_F_MINMAXD) || (cached_type == TYPE_F_MINMAXS)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_DUP) || (cached_type == TYPE_NEON_DUP_Q)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_LOAD1_1REG) || (cached_type == TYPE_NEON_LOAD1_1REG_Q)))
        {
	  return 11 /* 0xb */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_STORE1_1REG) || (cached_type == TYPE_NEON_STORE1_1REG_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_LOGIC) || (cached_type == TYPE_NEON_LOGIC_Q) || (cached_type == TYPE_NEON_BSL) || (cached_type == TYPE_NEON_BSL_Q) || (cached_type == TYPE_NEON_MOVE) || (cached_type == TYPE_NEON_MOVE_Q)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_TO_GP) || (cached_type == TYPE_NEON_TO_GP_Q)))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_FROM_GP) || (cached_type == TYPE_NEON_FROM_GP_Q) || (cached_type == TYPE_NEON_INS) || (cached_type == TYPE_NEON_INS_Q)))
        {
	  return 14 /* 0xe */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_SHIFT_IMM) || (cached_type == TYPE_NEON_SHIFT_IMM_Q) || (cached_type == TYPE_NEON_SHIFT_REG) || (cached_type == TYPE_NEON_SHIFT_REG_Q) || (cached_type == TYPE_NEON_SHIFT_IMM_LONG) || (cached_type == TYPE_NEON_SAT_SHIFT_IMM) || (cached_type == TYPE_NEON_SAT_SHIFT_IMM_Q) || (cached_type == TYPE_NEON_SAT_SHIFT_IMM_NARROW_Q) || (cached_type == TYPE_NEON_SAT_SHIFT_REG) || (cached_type == TYPE_NEON_SAT_SHIFT_REG_Q) || (cached_type == TYPE_NEON_SHIFT_IMM_NARROW_Q)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_ADD) || (cached_type == TYPE_NEON_ADD_Q) || (cached_type == TYPE_NEON_SUB) || (cached_type == TYPE_NEON_SUB_Q) || (cached_type == TYPE_NEON_NEG) || (cached_type == TYPE_NEON_NEG_Q) || (cached_type == TYPE_NEON_ABS) || (cached_type == TYPE_NEON_ABS_Q) || (cached_type == TYPE_NEON_ABD_Q) || (cached_type == TYPE_NEON_ARITH_ACC) || (cached_type == TYPE_NEON_ARITH_ACC_Q) || (cached_type == TYPE_NEON_REDUC_ADD) || (cached_type == TYPE_NEON_REDUC_ADD_Q) || (cached_type == TYPE_NEON_ADD_HALVE) || (cached_type == TYPE_NEON_ADD_HALVE_Q) || (cached_type == TYPE_NEON_SUB_HALVE) || (cached_type == TYPE_NEON_SUB_HALVE_Q) || (cached_type == TYPE_NEON_QADD) || (cached_type == TYPE_NEON_QADD_Q) || (cached_type == TYPE_NEON_COMPARE) || (cached_type == TYPE_NEON_COMPARE_Q) || (cached_type == TYPE_NEON_COMPARE_ZERO) || (cached_type == TYPE_NEON_COMPARE_ZERO_Q) || (cached_type == TYPE_NEON_TST) || (cached_type == TYPE_NEON_TST_Q) || (cached_type == TYPE_NEON_MINMAX) || (cached_type == TYPE_NEON_MINMAX_Q)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_ARITH_ACC) || (cached_type == TYPE_NEON_ARITH_ACC_Q)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_MUL_B) || (cached_type == TYPE_NEON_MUL_B_Q) || (cached_type == TYPE_NEON_MUL_H) || (cached_type == TYPE_NEON_MUL_H_Q) || (cached_type == TYPE_NEON_MUL_S) || (cached_type == TYPE_NEON_MUL_S_Q) || (cached_type == TYPE_NEON_FP_MUL_S_SCALAR) || (cached_type == TYPE_NEON_FP_MUL_S_SCALAR_Q) || (cached_type == TYPE_NEON_FP_MUL_D_SCALAR_Q) || (cached_type == TYPE_NEON_MLA_B) || (cached_type == TYPE_NEON_MLA_B_Q) || (cached_type == TYPE_NEON_MLA_H) || (cached_type == TYPE_NEON_MLA_H_Q) || (cached_type == TYPE_NEON_MLA_S) || (cached_type == TYPE_NEON_MLA_S_Q) || (cached_type == TYPE_NEON_MLA_H_SCALAR) || (cached_type == TYPE_NEON_MLA_H_SCALAR_Q) || (cached_type == TYPE_NEON_MLA_S_SCALAR) || (cached_type == TYPE_NEON_MLA_S_SCALAR_Q) || (cached_type == TYPE_NEON_MLA_B_LONG) || (cached_type == TYPE_NEON_MLA_H_LONG) || (cached_type == TYPE_NEON_MLA_S_LONG) || (cached_type == TYPE_NEON_FP_MUL_S) || (cached_type == TYPE_NEON_FP_MUL_S_Q) || (cached_type == TYPE_NEON_FP_MUL_D) || (cached_type == TYPE_NEON_FP_MUL_D_Q) || (cached_type == TYPE_NEON_FP_MLA_S) || (cached_type == TYPE_NEON_FP_MLA_S_Q) || (cached_type == TYPE_NEON_FP_MLA_D) || (cached_type == TYPE_NEON_FP_MLA_D_Q) || (cached_type == TYPE_NEON_FP_MLA_S_SCALAR) || (cached_type == TYPE_NEON_FP_MLA_S_SCALAR_Q) || (cached_type == TYPE_NEON_FP_MLA_D_SCALAR_Q) || (cached_type == TYPE_NEON_SAT_MUL_B) || (cached_type == TYPE_NEON_SAT_MUL_B_Q) || (cached_type == TYPE_NEON_SAT_MUL_H) || (cached_type == TYPE_NEON_SAT_MUL_H_Q) || (cached_type == TYPE_NEON_SAT_MUL_S) || (cached_type == TYPE_NEON_SAT_MUL_S_Q) || (cached_type == TYPE_NEON_SAT_MUL_H_SCALAR) || (cached_type == TYPE_NEON_SAT_MUL_H_SCALAR_Q) || (cached_type == TYPE_NEON_SAT_MUL_S_SCALAR) || (cached_type == TYPE_NEON_SAT_MUL_S_SCALAR_Q) || (cached_type == TYPE_NEON_SAT_MUL_H_SCALAR_LONG) || (cached_type == TYPE_NEON_SAT_MUL_S_SCALAR_LONG) || (cached_type == TYPE_NEON_SAT_MLA_B_LONG) || (cached_type == TYPE_NEON_SAT_MLA_H_LONG) || (cached_type == TYPE_NEON_SAT_MLA_S_LONG) || (cached_type == TYPE_NEON_SAT_MLA_H_SCALAR_LONG) || (cached_type == TYPE_NEON_SAT_MLA_S_SCALAR_LONG)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_FP_ABD_S) || (cached_type == TYPE_NEON_FP_ABD_S_Q) || (cached_type == TYPE_NEON_FP_ABD_D) || (cached_type == TYPE_NEON_FP_ABD_D_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_FP_ADDSUB_S) || (cached_type == TYPE_NEON_FP_ADDSUB_S_Q) || (cached_type == TYPE_NEON_FP_ADDSUB_D) || (cached_type == TYPE_NEON_FP_ADDSUB_D_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_FP_DIV_S) || (cached_type == TYPE_NEON_FP_DIV_S_Q) || (cached_type == TYPE_NEON_FP_DIV_D) || (cached_type == TYPE_NEON_FP_DIV_D_Q)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_FP_NEG_S) || (cached_type == TYPE_NEON_FP_NEG_S_Q) || (cached_type == TYPE_NEON_FP_NEG_D) || (cached_type == TYPE_NEON_FP_NEG_D_Q) || (cached_type == TYPE_NEON_FP_ABS_S) || (cached_type == TYPE_NEON_FP_ABS_S_Q) || (cached_type == TYPE_NEON_FP_ABS_D) || (cached_type == TYPE_NEON_FP_ABS_D_Q)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_FP_ROUND_S) || (cached_type == TYPE_NEON_FP_ROUND_S_Q) || (cached_type == TYPE_NEON_FP_ROUND_D) || (cached_type == TYPE_NEON_FP_ROUND_D_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_INT_TO_FP_S) || (cached_type == TYPE_NEON_INT_TO_FP_S_Q) || (cached_type == TYPE_NEON_INT_TO_FP_D) || (cached_type == TYPE_NEON_INT_TO_FP_D_Q) || (cached_type == TYPE_NEON_FP_CVT_WIDEN_S) || (cached_type == TYPE_NEON_FP_CVT_NARROW_S_Q) || (cached_type == TYPE_NEON_FP_CVT_NARROW_D_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_FP_REDUC_ADD_S) || (cached_type == TYPE_NEON_FP_REDUC_ADD_S_Q) || (cached_type == TYPE_NEON_FP_REDUC_ADD_D) || (cached_type == TYPE_NEON_FP_REDUC_ADD_D_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_CLS) || (cached_type == TYPE_NEON_CLS_Q)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_STORE1_ONE_LANE) || (cached_type == TYPE_NEON_STORE1_ONE_LANE_Q) || (cached_type == TYPE_NEON_STP) || (cached_type == TYPE_NEON_STP_Q)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_SUB_HALVE_NARROW_Q) || (cached_type == TYPE_NEON_ADD_HALVE_NARROW_Q)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_SHIFT_ACC) || (cached_type == TYPE_NEON_SHIFT_ACC_Q)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_FP_COMPARE_S) || (cached_type == TYPE_NEON_FP_COMPARE_S_Q) || (cached_type == TYPE_NEON_FP_COMPARE_D) || (cached_type == TYPE_NEON_FP_COMPARE_D_Q)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_FP_SQRT_S) || (cached_type == TYPE_NEON_FP_SQRT_S_Q) || (cached_type == TYPE_NEON_FP_SQRT_D) || (cached_type == TYPE_NEON_FP_SQRT_D_Q)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_TBL1) || (cached_type == TYPE_NEON_TBL1_Q)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_TBL2) || (cached_type == TYPE_NEON_TBL2_Q)))
        {
	  return 8;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_PERMUTE) || (cached_type == TYPE_NEON_PERMUTE_Q)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && (cached_type == TYPE_NEON_LOAD1_ALL_LANES))
        {
	  return 10 /* 0xa */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_FP_RECPE_S) || (cached_type == TYPE_NEON_FP_RECPE_S_Q) || (cached_type == TYPE_NEON_FP_RECPE_D) || (cached_type == TYPE_NEON_FP_RECPE_D_Q) || (cached_type == TYPE_NEON_FP_RECPX_S) || (cached_type == TYPE_NEON_FP_RECPX_S_Q) || (cached_type == TYPE_NEON_FP_RECPX_D) || (cached_type == TYPE_NEON_FP_RECPX_D_Q)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_FP_RECPS_S) || (cached_type == TYPE_NEON_FP_RECPS_S_Q) || (cached_type == TYPE_NEON_FP_RECPS_D) || (cached_type == TYPE_NEON_FP_RECPS_D_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_XGENE1)))) && ((cached_type == TYPE_NEON_MUL_D_LONG) || (cached_type == TYPE_CRYPTO_PMULL)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_CALL) || (cached_type == TYPE_BRANCH) || (cached_type == TYPE_TRAP)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && (cached_type == TYPE_BLOCK))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && (cached_type == TYPE_MRS))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_MULTIPLE) || (cached_type == TYPE_UNTYPED)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && (cached_type == TYPE_MOV_REG))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_ALU_IMM) || (cached_type == TYPE_ALU_SREG) || (cached_type == TYPE_ALUS_IMM) || (cached_type == TYPE_ALUS_SREG) || (cached_type == TYPE_ADC_REG) || (cached_type == TYPE_ADC_IMM) || (cached_type == TYPE_ADCS_REG) || (cached_type == TYPE_ADCS_IMM) || (cached_type == TYPE_LOGIC_REG) || (cached_type == TYPE_LOGIC_IMM) || (cached_type == TYPE_LOGICS_REG) || (cached_type == TYPE_LOGICS_IMM) || (cached_type == TYPE_CSEL) || (cached_type == TYPE_ADR) || (cached_type == TYPE_MOV_IMM) || (cached_type == TYPE_SHIFT_REG) || (cached_type == TYPE_SHIFT_IMM) || (cached_type == TYPE_BFM) || (cached_type == TYPE_BFX) || (cached_type == TYPE_RBIT) || (cached_type == TYPE_REV) || (cached_type == TYPE_EXTEND) || (cached_type == TYPE_ROTATE_IMM)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_ALU_SHIFT_IMM_LSL_1TO4) || (cached_type == TYPE_ALU_SHIFT_IMM_OTHER) || (cached_type == TYPE_ALU_EXT) || (cached_type == TYPE_ALUS_SHIFT_IMM) || (cached_type == TYPE_ALUS_EXT) || (cached_type == TYPE_LOGIC_SHIFT_IMM) || (cached_type == TYPE_LOGICS_SHIFT_IMM)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_SDIV) || (cached_type == TYPE_UDIV)))
        {
	  return 13 /* 0xd */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_MLA) || (cached_type == TYPE_SMLAL) || (cached_type == TYPE_UMLAL)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_MUL) || (cached_type == TYPE_SMULL) || (cached_type == TYPE_UMULL)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && (cached_type == TYPE_CLZ))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && (cached_type == TYPE_LOAD_4))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_LOAD_8) || (cached_type == TYPE_LOAD_16)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && (cached_type == TYPE_STORE_4))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_STORE_8) || (cached_type == TYPE_STORE_16)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_FFARITHS) || (cached_type == TYPE_FFARITHD) || (cached_type == TYPE_F_MINMAXS) || (cached_type == TYPE_F_MINMAXD)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_FADDS) || (cached_type == TYPE_FADDD)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_FCMPS) || (cached_type == TYPE_FCMPD) || (cached_type == TYPE_FCCMPS) || (cached_type == TYPE_FCCMPD)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_FDIVS) || (cached_type == TYPE_FSQRTS)))
        {
	  return 16 /* 0x10 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_FDIVD) || (cached_type == TYPE_FSQRTD)))
        {
	  return 23 /* 0x17 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_FMULS) || (cached_type == TYPE_FMULD) || (cached_type == TYPE_FMACS) || (cached_type == TYPE_FMACD)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_F_RINTS) || (cached_type == TYPE_F_RINTD)))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && (cached_type == TYPE_FCSEL))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_F_CVTF2I) || (cached_type == TYPE_F_CVT) || (cached_type == TYPE_F_CVTI2F)))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_FCONSTS) || (cached_type == TYPE_FCONSTD) || (cached_type == TYPE_FMOV) || (cached_type == TYPE_F_MRC)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && (cached_type == TYPE_F_MCR))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_F_LOADS) || (cached_type == TYPE_F_LOADD)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_F_STORES) || (cached_type == TYPE_F_STORED)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_ABD) || (cached_type == TYPE_NEON_ABD_Q) || (cached_type == TYPE_NEON_ARITH_ACC) || (cached_type == TYPE_NEON_ARITH_ACC_Q) || (cached_type == TYPE_NEON_ABS) || (cached_type == TYPE_NEON_ABS_Q) || (cached_type == TYPE_NEON_ADD) || (cached_type == TYPE_NEON_ADD_Q) || (cached_type == TYPE_NEON_SUB) || (cached_type == TYPE_NEON_SUB_Q) || (cached_type == TYPE_NEON_NEG) || (cached_type == TYPE_NEON_NEG_Q) || (cached_type == TYPE_NEON_ADD_LONG) || (cached_type == TYPE_NEON_ADD_WIDEN) || (cached_type == TYPE_NEON_ADD_HALVE) || (cached_type == TYPE_NEON_ADD_HALVE_Q) || (cached_type == TYPE_NEON_SUB_LONG) || (cached_type == TYPE_NEON_SUB_WIDEN) || (cached_type == TYPE_NEON_SUB_HALVE) || (cached_type == TYPE_NEON_SUB_HALVE_Q) || (cached_type == TYPE_NEON_ADD_HALVE_NARROW_Q) || (cached_type == TYPE_NEON_SUB_HALVE_NARROW_Q) || (cached_type == TYPE_NEON_QABS) || (cached_type == TYPE_NEON_QABS_Q) || (cached_type == TYPE_NEON_QADD) || (cached_type == TYPE_NEON_QADD_Q) || (cached_type == TYPE_NEON_QNEG) || (cached_type == TYPE_NEON_QNEG_Q) || (cached_type == TYPE_NEON_QSUB) || (cached_type == TYPE_NEON_QSUB_Q) || (cached_type == TYPE_NEON_MINMAX) || (cached_type == TYPE_NEON_MINMAX_Q) || (cached_type == TYPE_NEON_REDUC_MINMAX) || (cached_type == TYPE_NEON_REDUC_MINMAX_Q) || (cached_type == TYPE_NEON_MUL_B) || (cached_type == TYPE_NEON_MUL_H) || (cached_type == TYPE_NEON_MUL_S) || (cached_type == TYPE_NEON_MUL_B_Q) || (cached_type == TYPE_NEON_MUL_H_Q) || (cached_type == TYPE_NEON_MUL_S_Q) || (cached_type == TYPE_NEON_SAT_MUL_B) || (cached_type == TYPE_NEON_SAT_MUL_H) || (cached_type == TYPE_NEON_SAT_MUL_S) || (cached_type == TYPE_NEON_SAT_MUL_B_Q) || (cached_type == TYPE_NEON_SAT_MUL_H_Q) || (cached_type == TYPE_NEON_SAT_MUL_S_Q) || (cached_type == TYPE_NEON_MLA_B) || (cached_type == TYPE_NEON_MLA_H) || (cached_type == TYPE_NEON_MLA_S) || (cached_type == TYPE_NEON_MLA_B_Q) || (cached_type == TYPE_NEON_MLA_H_Q) || (cached_type == TYPE_NEON_MLA_S_Q) || (cached_type == TYPE_NEON_MUL_B_LONG) || (cached_type == TYPE_NEON_MUL_H_LONG) || (cached_type == TYPE_NEON_MUL_S_LONG) || (cached_type == TYPE_NEON_MUL_D_LONG) || (cached_type == TYPE_NEON_SAT_MUL_B_LONG) || (cached_type == TYPE_NEON_SAT_MUL_H_LONG) || (cached_type == TYPE_NEON_SAT_MUL_S_LONG) || (cached_type == TYPE_NEON_MLA_B_LONG) || (cached_type == TYPE_NEON_MLA_H_LONG) || (cached_type == TYPE_NEON_MLA_S_LONG) || (cached_type == TYPE_NEON_SAT_MLA_B_LONG) || (cached_type == TYPE_NEON_SAT_MLA_H_LONG) || (cached_type == TYPE_NEON_SAT_MLA_S_LONG) || (cached_type == TYPE_NEON_SHIFT_ACC) || (cached_type == TYPE_NEON_SHIFT_ACC_Q) || (cached_type == TYPE_NEON_SHIFT_IMM) || (cached_type == TYPE_NEON_SHIFT_IMM_Q) || (cached_type == TYPE_NEON_SHIFT_REG) || (cached_type == TYPE_NEON_SHIFT_REG_Q) || (cached_type == TYPE_NEON_SHIFT_IMM_LONG) || (cached_type == TYPE_NEON_SHIFT_IMM_NARROW_Q) || (cached_type == TYPE_NEON_SAT_SHIFT_IMM) || (cached_type == TYPE_NEON_SAT_SHIFT_IMM_Q) || (cached_type == TYPE_NEON_SAT_SHIFT_REG) || (cached_type == TYPE_NEON_SAT_SHIFT_REG_Q) || (cached_type == TYPE_NEON_SAT_SHIFT_IMM_NARROW_Q)))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_REDUC_ADD) || (cached_type == TYPE_NEON_REDUC_ADD_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_COMPARE) || (cached_type == TYPE_NEON_COMPARE_Q) || (cached_type == TYPE_NEON_COMPARE_ZERO) || (cached_type == TYPE_NEON_TST) || (cached_type == TYPE_NEON_TST_Q)))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_LOGIC) || (cached_type == TYPE_NEON_LOGIC_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_FP_ABS_S) || (cached_type == TYPE_NEON_FP_ABS_D) || (cached_type == TYPE_NEON_FP_ABS_S_Q) || (cached_type == TYPE_NEON_FP_ABS_D_Q) || (cached_type == TYPE_NEON_FP_COMPARE_S) || (cached_type == TYPE_NEON_FP_COMPARE_D) || (cached_type == TYPE_NEON_FP_COMPARE_S_Q) || (cached_type == TYPE_NEON_FP_COMPARE_D_Q) || (cached_type == TYPE_NEON_FP_MINMAX_S) || (cached_type == TYPE_NEON_FP_MINMAX_D) || (cached_type == TYPE_NEON_FP_MINMAX_S_Q) || (cached_type == TYPE_NEON_FP_MINMAX_D_Q) || (cached_type == TYPE_NEON_FP_REDUC_MINMAX_S) || (cached_type == TYPE_NEON_FP_REDUC_MINMAX_D) || (cached_type == TYPE_NEON_FP_REDUC_MINMAX_S_Q) || (cached_type == TYPE_NEON_FP_REDUC_MINMAX_D_Q) || (cached_type == TYPE_NEON_FP_NEG_S) || (cached_type == TYPE_NEON_FP_NEG_D) || (cached_type == TYPE_NEON_FP_NEG_S_Q) || (cached_type == TYPE_NEON_FP_NEG_D_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_FP_ABD_S) || (cached_type == TYPE_NEON_FP_ABD_D) || (cached_type == TYPE_NEON_FP_ABD_S_Q) || (cached_type == TYPE_NEON_FP_ABD_D_Q) || (cached_type == TYPE_NEON_FP_ADDSUB_S) || (cached_type == TYPE_NEON_FP_ADDSUB_D) || (cached_type == TYPE_NEON_FP_ADDSUB_S_Q) || (cached_type == TYPE_NEON_FP_ADDSUB_D_Q) || (cached_type == TYPE_NEON_FP_REDUC_ADD_S) || (cached_type == TYPE_NEON_FP_REDUC_ADD_D) || (cached_type == TYPE_NEON_FP_REDUC_ADD_S_Q) || (cached_type == TYPE_NEON_FP_REDUC_ADD_D_Q) || (cached_type == TYPE_NEON_FP_MUL_S) || (cached_type == TYPE_NEON_FP_MUL_D) || (cached_type == TYPE_NEON_FP_MUL_S_Q) || (cached_type == TYPE_NEON_FP_MUL_D_Q) || (cached_type == TYPE_NEON_FP_MUL_S_SCALAR_Q) || (cached_type == TYPE_NEON_FP_MUL_D_SCALAR_Q) || (cached_type == TYPE_NEON_FP_MLA_S) || (cached_type == TYPE_NEON_FP_MLA_D) || (cached_type == TYPE_NEON_FP_MLA_S_Q) || (cached_type == TYPE_NEON_FP_MLA_D_Q)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_FP_CVT_WIDEN_S) || (cached_type == TYPE_NEON_FP_CVT_NARROW_D_Q) || (cached_type == TYPE_NEON_FP_TO_INT_S) || (cached_type == TYPE_NEON_FP_TO_INT_D) || (cached_type == TYPE_NEON_FP_TO_INT_S_Q) || (cached_type == TYPE_NEON_FP_TO_INT_D_Q) || (cached_type == TYPE_NEON_INT_TO_FP_S) || (cached_type == TYPE_NEON_INT_TO_FP_D) || (cached_type == TYPE_NEON_INT_TO_FP_S_Q) || (cached_type == TYPE_NEON_INT_TO_FP_D_Q) || (cached_type == TYPE_NEON_FP_ROUND_S) || (cached_type == TYPE_NEON_FP_ROUND_D) || (cached_type == TYPE_NEON_FP_ROUND_S_Q) || (cached_type == TYPE_NEON_FP_ROUND_D_Q)))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_FP_DIV_S) || (cached_type == TYPE_NEON_FP_DIV_S_Q)))
        {
	  return 16 /* 0x10 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_FP_DIV_D) || (cached_type == TYPE_NEON_FP_DIV_D_Q)))
        {
	  return 23 /* 0x17 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_RBIT) || (cached_type == TYPE_NEON_BSL) || (cached_type == TYPE_NEON_BSL_Q) || (cached_type == TYPE_NEON_CLS) || (cached_type == TYPE_NEON_CLS_Q) || (cached_type == TYPE_NEON_CNT) || (cached_type == TYPE_NEON_CNT_Q) || (cached_type == TYPE_NEON_FROM_GP) || (cached_type == TYPE_NEON_FROM_GP_Q) || (cached_type == TYPE_NEON_DUP) || (cached_type == TYPE_NEON_DUP_Q) || (cached_type == TYPE_NEON_EXT) || (cached_type == TYPE_NEON_EXT_Q) || (cached_type == TYPE_NEON_INS) || (cached_type == TYPE_NEON_INS_Q) || (cached_type == TYPE_NEON_MOVE) || (cached_type == TYPE_NEON_MOVE_Q) || (cached_type == TYPE_NEON_FP_RECPE_S) || (cached_type == TYPE_NEON_FP_RECPE_D) || (cached_type == TYPE_NEON_FP_RECPE_S_Q) || (cached_type == TYPE_NEON_FP_RECPE_D_Q) || (cached_type == TYPE_NEON_FP_RECPX_S) || (cached_type == TYPE_NEON_FP_RECPX_D) || (cached_type == TYPE_NEON_FP_RECPX_S_Q) || (cached_type == TYPE_NEON_FP_RECPX_D_Q) || (cached_type == TYPE_NEON_REV) || (cached_type == TYPE_NEON_REV_Q) || (cached_type == TYPE_NEON_PERMUTE) || (cached_type == TYPE_NEON_PERMUTE_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_FP_RECPS_S) || (cached_type == TYPE_NEON_FP_RECPS_S_Q) || (cached_type == TYPE_NEON_FP_RECPS_D) || (cached_type == TYPE_NEON_FP_RECPS_D_Q) || (cached_type == TYPE_NEON_FP_SQRT_S) || (cached_type == TYPE_NEON_FP_SQRT_S_Q) || (cached_type == TYPE_NEON_FP_SQRT_D) || (cached_type == TYPE_NEON_FP_SQRT_D_Q) || (cached_type == TYPE_NEON_FP_RSQRTE_S) || (cached_type == TYPE_NEON_FP_RSQRTE_S_Q) || (cached_type == TYPE_NEON_FP_RSQRTE_D) || (cached_type == TYPE_NEON_FP_RSQRTE_D_Q) || (cached_type == TYPE_NEON_FP_RSQRTS_S) || (cached_type == TYPE_NEON_FP_RSQRTS_S_Q) || (cached_type == TYPE_NEON_FP_RSQRTS_D) || (cached_type == TYPE_NEON_FP_RSQRTS_D_Q)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_TBL1) || (cached_type == TYPE_NEON_TBL1_Q) || (cached_type == TYPE_NEON_TBL2) || (cached_type == TYPE_NEON_TBL2_Q) || (cached_type == TYPE_NEON_TBL3) || (cached_type == TYPE_NEON_TBL3_Q) || (cached_type == TYPE_NEON_TBL4) || (cached_type == TYPE_NEON_TBL4_Q)))
        {
	  return 8;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_TO_GP) || (cached_type == TYPE_NEON_TO_GP_Q)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_LDP) || (cached_type == TYPE_NEON_LDP_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_LOAD1_1REG) || (cached_type == TYPE_NEON_LOAD1_1REG_Q) || (cached_type == TYPE_NEON_LOAD1_2REG) || (cached_type == TYPE_NEON_LOAD1_2REG_Q) || (cached_type == TYPE_NEON_LOAD1_3REG) || (cached_type == TYPE_NEON_LOAD1_3REG_Q) || (cached_type == TYPE_NEON_LOAD1_4REG) || (cached_type == TYPE_NEON_LOAD1_4REG_Q)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_LOAD1_ONE_LANE) || (cached_type == TYPE_NEON_LOAD1_ONE_LANE_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_LOAD1_ALL_LANES) || (cached_type == TYPE_NEON_LOAD1_ALL_LANES_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_LOAD2_2REG) || (cached_type == TYPE_NEON_LOAD2_2REG_Q) || (cached_type == TYPE_NEON_LOAD2_ONE_LANE) || (cached_type == TYPE_NEON_LOAD2_ONE_LANE_Q) || (cached_type == TYPE_NEON_LOAD2_ALL_LANES) || (cached_type == TYPE_NEON_LOAD2_ALL_LANES_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_LOAD3_3REG) || (cached_type == TYPE_NEON_LOAD3_3REG_Q) || (cached_type == TYPE_NEON_LOAD3_ONE_LANE) || (cached_type == TYPE_NEON_LOAD3_ONE_LANE_Q) || (cached_type == TYPE_NEON_LOAD3_ALL_LANES) || (cached_type == TYPE_NEON_LOAD3_ALL_LANES_Q)))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_LOAD4_4REG) || (cached_type == TYPE_NEON_LOAD4_4REG_Q) || (cached_type == TYPE_NEON_LOAD4_ONE_LANE) || (cached_type == TYPE_NEON_LOAD4_ONE_LANE_Q) || (cached_type == TYPE_NEON_LOAD4_ALL_LANES) || (cached_type == TYPE_NEON_LOAD4_ALL_LANES_Q)))
        {
	  return 8;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_STP) || (cached_type == TYPE_NEON_STP_Q)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_STORE1_1REG) || (cached_type == TYPE_NEON_STORE1_1REG_Q) || (cached_type == TYPE_NEON_STORE1_2REG) || (cached_type == TYPE_NEON_STORE1_2REG_Q) || (cached_type == TYPE_NEON_STORE1_3REG) || (cached_type == TYPE_NEON_STORE1_4REG)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_STORE1_ONE_LANE) || (cached_type == TYPE_NEON_STORE1_ONE_LANE_Q)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_STORE2_2REG) || (cached_type == TYPE_NEON_STORE2_2REG_Q) || (cached_type == TYPE_NEON_STORE2_ONE_LANE) || (cached_type == TYPE_NEON_STORE2_ONE_LANE_Q)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_STORE3_3REG) || (cached_type == TYPE_NEON_STORE3_3REG_Q) || (cached_type == TYPE_NEON_STORE3_ONE_LANE) || (cached_type == TYPE_NEON_STORE3_ONE_LANE_Q)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_NEON_STORE4_4REG) || (cached_type == TYPE_NEON_STORE4_4REG_Q) || (cached_type == TYPE_NEON_STORE4_ONE_LANE) || (cached_type == TYPE_NEON_STORE4_ONE_LANE_Q)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_CRYPTO_AESE) || (cached_type == TYPE_CRYPTO_AESMC)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && ((cached_type == TYPE_CRYPTO_SHA1_FAST) || (cached_type == TYPE_CRYPTO_SHA1_XOR) || (cached_type == TYPE_CRYPTO_SHA1_SLOW) || (cached_type == TYPE_CRYPTO_SHA256_FAST) || (cached_type == TYPE_CRYPTO_SHA256_SLOW)))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && (cached_type == TYPE_CRC))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))) && (cached_type == TYPE_CRYPTO_PMULL))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_ALU_IMM) || (cached_type == TYPE_LOGIC_IMM) || (cached_type == TYPE_ALU_SREG) || (cached_type == TYPE_LOGIC_REG) || (cached_type == TYPE_ADC_IMM) || (cached_type == TYPE_ADC_REG) || (cached_type == TYPE_ADR) || (cached_type == TYPE_BFM) || (cached_type == TYPE_CLZ) || (cached_type == TYPE_RBIT) || (cached_type == TYPE_REV) || (cached_type == TYPE_SHIFT_IMM) || (cached_type == TYPE_SHIFT_REG) || (cached_type == TYPE_MOV_IMM) || (cached_type == TYPE_MOV_REG) || (cached_type == TYPE_MVN_IMM) || (cached_type == TYPE_MVN_REG) || (cached_type == TYPE_MRS) || (cached_type == TYPE_MULTIPLE)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_ALUS_IMM) || (cached_type == TYPE_LOGICS_IMM) || (cached_type == TYPE_ALUS_SREG) || (cached_type == TYPE_LOGICS_REG) || (cached_type == TYPE_ADCS_IMM) || (cached_type == TYPE_ADCS_REG)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_EXTEND) || (cached_type == TYPE_ALU_SHIFT_IMM_LSL_1TO4) || (cached_type == TYPE_ALU_SHIFT_IMM_OTHER) || (cached_type == TYPE_ALU_SHIFT_REG) || (cached_type == TYPE_CRC) || (cached_type == TYPE_LOGIC_SHIFT_IMM) || (cached_type == TYPE_LOGIC_SHIFT_REG) || (cached_type == TYPE_MOV_SHIFT) || (cached_type == TYPE_MVN_SHIFT) || (cached_type == TYPE_MOV_SHIFT_REG) || (cached_type == TYPE_MVN_SHIFT_REG)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_ALUS_SHIFT_IMM) || (cached_type == TYPE_ALUS_SHIFT_REG) || (cached_type == TYPE_LOGICS_SHIFT_IMM) || (cached_type == TYPE_LOGICS_SHIFT_REG)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && (((cached_mul32 = get_attr_mul32 (insn)) == MUL32_YES) || ((cached_widen_mul64 = get_attr_widen_mul64 (insn)) == WIDEN_MUL64_YES)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_UDIV) || (cached_type == TYPE_SDIV)))
        {
	  return 10 /* 0xa */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && (cached_type == TYPE_BLOCK))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && (cached_type == TYPE_BRANCH))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_LOAD_4) || (cached_type == TYPE_LOAD_8)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_STORE_4) || (cached_type == TYPE_STORE_8)))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_NEON_ABD) || (cached_type == TYPE_NEON_ARITH_ACC)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && (cached_type == TYPE_NEON_ARITH_ACC_Q))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_tsv110_neon_type = get_attr_tsv110_neon_type (insn)) == TSV110_NEON_TYPE_NEON_ARITH_BASIC))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_tsv110_neon_type = get_attr_tsv110_neon_type (insn)) == TSV110_NEON_TYPE_NEON_ARITH_COMPLEX))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_tsv110_neon_type = get_attr_tsv110_neon_type (insn)) == TSV110_NEON_TYPE_NEON_MULTIPLY))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && (cached_type == TYPE_NEON_MUL_D_LONG))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_tsv110_neon_type = get_attr_tsv110_neon_type (insn)) == TSV110_NEON_TYPE_NEON_MULTIPLY_Q))
        {
	  return 8;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && (((cached_tsv110_neon_type = get_attr_tsv110_neon_type (insn)) == TSV110_NEON_TYPE_NEON_SHIFT_ACC) || (cached_tsv110_neon_type == TSV110_NEON_TYPE_NEON_SHIFT_IMM_BASIC) || (cached_tsv110_neon_type == TSV110_NEON_TYPE_NEON_SHIFT_IMM_COMPLEX) || (cached_tsv110_neon_type == TSV110_NEON_TYPE_NEON_SHIFT_REG_BASIC) || (cached_tsv110_neon_type == TSV110_NEON_TYPE_NEON_SHIFT_REG_COMPLEX)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && (((cached_tsv110_neon_type = get_attr_tsv110_neon_type (insn)) == TSV110_NEON_TYPE_NEON_SHIFT_REG_BASIC_Q) || (cached_tsv110_neon_type == TSV110_NEON_TYPE_NEON_SHIFT_REG_COMPLEX_Q)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_tsv110_neon_type = get_attr_tsv110_neon_type (insn)) == TSV110_NEON_TYPE_NEON_FP_NEGABS))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_tsv110_neon_type = get_attr_tsv110_neon_type (insn)) == TSV110_NEON_TYPE_NEON_FP_ARITH))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_tsv110_neon_type = get_attr_tsv110_neon_type (insn)) == TSV110_NEON_TYPE_NEON_FP_ARITH_Q))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_NEON_FP_MINMAX_S_Q) || (cached_type == TYPE_NEON_FP_MINMAX_D_Q)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_tsv110_neon_type = get_attr_tsv110_neon_type (insn)) == TSV110_NEON_TYPE_NEON_FP_REDUCTIONS_Q))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && (((cached_tsv110_neon_type = get_attr_tsv110_neon_type (insn)) == TSV110_NEON_TYPE_NEON_FP_CVT_INT) || (cached_tsv110_neon_type == TSV110_NEON_TYPE_NEON_FP_CVT_INT_Q)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_tsv110_neon_type = get_attr_tsv110_neon_type (insn)) == TSV110_NEON_TYPE_NEON_FP_MUL))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_tsv110_neon_type = get_attr_tsv110_neon_type (insn)) == TSV110_NEON_TYPE_NEON_FP_MUL_Q))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && (((cached_tsv110_neon_type = get_attr_tsv110_neon_type (insn)) == TSV110_NEON_TYPE_NEON_FP_MLA) || (cached_tsv110_neon_type == TSV110_NEON_TYPE_NEON_FP_RECPS_RSQRTS)))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_tsv110_neon_type = get_attr_tsv110_neon_type (insn)) == TSV110_NEON_TYPE_NEON_FP_RECPE_RSQRTE))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && (((cached_tsv110_neon_type = get_attr_tsv110_neon_type (insn)) == TSV110_NEON_TYPE_NEON_FP_MLA_Q) || (cached_tsv110_neon_type == TSV110_NEON_TYPE_NEON_FP_RECPS_RSQRTS_Q)))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_tsv110_neon_type = get_attr_tsv110_neon_type (insn)) == TSV110_NEON_TYPE_NEON_FP_RECPE_RSQRTE_Q))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_tsv110_neon_type = get_attr_tsv110_neon_type (insn)) == TSV110_NEON_TYPE_NEON_BITOPS))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_NEON_FROM_GP) || (cached_type == TYPE_F_MCR)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && (cached_type == TYPE_F_MCRR))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_tsv110_neon_type = get_attr_tsv110_neon_type (insn)) == TSV110_NEON_TYPE_NEON_BITOPS_Q))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_tsv110_neon_type = get_attr_tsv110_neon_type (insn)) == TSV110_NEON_TYPE_NEON_FROM_GP_Q))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_NEON_TO_GP) || (cached_type == TYPE_NEON_TO_GP_Q)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_NEON_LOAD1_ONE_LANE) || (cached_type == TYPE_NEON_LOAD1_ONE_LANE_Q) || (cached_type == TYPE_NEON_LOAD1_ALL_LANES) || (cached_type == TYPE_NEON_LOAD1_ALL_LANES_Q)))
        {
	  return 8;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_F_LOADS) || (cached_type == TYPE_F_LOADD) || (cached_type == TYPE_NEON_LOAD1_1REG) || (cached_type == TYPE_NEON_LOAD1_1REG_Q)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_NEON_LOAD1_2REG) || (cached_type == TYPE_NEON_LOAD1_2REG_Q)))
        {
	  return 6;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_NEON_LOAD1_3REG) || (cached_type == TYPE_NEON_LOAD1_3REG_Q)))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_NEON_LOAD1_4REG) || (cached_type == TYPE_NEON_LOAD1_4REG_Q)))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_NEON_LOAD1_2REG) || (cached_type == TYPE_NEON_LOAD1_2REG_Q) || (cached_type == TYPE_NEON_LOAD2_2REG) || (cached_type == TYPE_NEON_LOAD2_2REG_Q) || (cached_type == TYPE_NEON_LOAD2_ALL_LANES) || (cached_type == TYPE_NEON_LOAD2_ALL_LANES_Q) || (cached_type == TYPE_NEON_LOAD2_ONE_LANE) || (cached_type == TYPE_NEON_LOAD2_ONE_LANE_Q)))
        {
	  return 8;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_NEON_LOAD3_3REG) || (cached_type == TYPE_NEON_LOAD3_3REG_Q) || (cached_type == TYPE_NEON_LOAD3_ONE_LANE) || (cached_type == TYPE_NEON_LOAD3_ONE_LANE_Q) || (cached_type == TYPE_NEON_LOAD3_ALL_LANES) || (cached_type == TYPE_NEON_LOAD3_ALL_LANES_Q)))
        {
	  return 9;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_NEON_LOAD4_ALL_LANES) || (cached_type == TYPE_NEON_LOAD4_ALL_LANES_Q) || (cached_type == TYPE_NEON_LOAD4_ONE_LANE) || (cached_type == TYPE_NEON_LOAD4_ONE_LANE_Q)))
        {
	  return 9;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_NEON_LOAD4_ALL_LANES) || (cached_type == TYPE_NEON_LOAD4_ALL_LANES_Q) || (cached_type == TYPE_NEON_LOAD4_ONE_LANE) || (cached_type == TYPE_NEON_LOAD4_ONE_LANE_Q)))
        {
	  return 11 /* 0xb */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_tsv110_neon_type = get_attr_tsv110_neon_type (insn)) == TSV110_NEON_TYPE_NEON_STORE_A))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_tsv110_neon_type = get_attr_tsv110_neon_type (insn)) == TSV110_NEON_TYPE_NEON_STORE_B))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_tsv110_neon_type = get_attr_tsv110_neon_type (insn)) == TSV110_NEON_TYPE_NEON_STORE_COMPLEX))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_FCONSTS) || (cached_type == TYPE_FCONSTD) || (cached_type == TYPE_FMOV)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_FADDS) || (cached_type == TYPE_FADDD) || (cached_type == TYPE_FMULS) || (cached_type == TYPE_FMULD)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_FMACS) || (cached_type == TYPE_FFMAS) || (cached_type == TYPE_FMACD) || (cached_type == TYPE_FFMAD)))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && (cached_type == TYPE_F_CVT))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && (cached_type == TYPE_F_CVTF2I))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && (cached_type == TYPE_F_CVTI2F))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_FCMPS) || (cached_type == TYPE_FCMPD)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_FFARITHS) || (cached_type == TYPE_FFARITHD)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_FDIVS) || (cached_type == TYPE_NEON_FP_DIV_S) || (cached_type == TYPE_FDIVD) || (cached_type == TYPE_NEON_FP_DIV_D) || (cached_type == TYPE_NEON_FP_DIV_S_Q) || (cached_type == TYPE_NEON_FP_DIV_D_Q)))
        {
	  return 12 /* 0xc */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_FSQRTS) || (cached_type == TYPE_NEON_FP_SQRT_S) || (cached_type == TYPE_FSQRTD) || (cached_type == TYPE_NEON_FP_SQRT_D) || (cached_type == TYPE_NEON_FP_SQRT_S_Q) || (cached_type == TYPE_NEON_FP_SQRT_D_Q)))
        {
	  return 24 /* 0x18 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_CRYPTO_AESE) || (cached_type == TYPE_CRYPTO_AESMC)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_CRYPTO_SHA1_FAST) || (cached_type == TYPE_CRYPTO_SHA1_XOR)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && (cached_type == TYPE_CRYPTO_SHA256_FAST))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && ((cached_type == TYPE_CRYPTO_SHA1_SLOW) || (cached_type == TYPE_CRYPTO_SHA256_SLOW)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_TSV110)))) && (cached_type == TYPE_CALL))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_CALL) || (cached_type == TYPE_BRANCH) || (cached_type == TYPE_TRAP)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && (cached_type == TYPE_BLOCK))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && (cached_type == TYPE_MRS))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && (cached_type == TYPE_MULTIPLE))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && (cached_type == TYPE_MOV_REG))
        {
	  return 0;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_ALU_IMM) || (cached_type == TYPE_ALU_SREG) || (cached_type == TYPE_ALUS_IMM) || (cached_type == TYPE_ALUS_SREG) || (cached_type == TYPE_ADC_REG) || (cached_type == TYPE_ADC_IMM) || (cached_type == TYPE_ADCS_REG) || (cached_type == TYPE_ADCS_IMM) || (cached_type == TYPE_LOGIC_REG) || (cached_type == TYPE_LOGIC_IMM) || (cached_type == TYPE_LOGICS_REG) || (cached_type == TYPE_LOGICS_IMM) || (cached_type == TYPE_CSEL) || (cached_type == TYPE_ADR) || (cached_type == TYPE_MOV_IMM) || (cached_type == TYPE_SHIFT_REG) || (cached_type == TYPE_SHIFT_IMM) || (cached_type == TYPE_BFM) || (cached_type == TYPE_BFX) || (cached_type == TYPE_RBIT) || (cached_type == TYPE_REV) || (cached_type == TYPE_EXTEND) || (cached_type == TYPE_ROTATE_IMM)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_ALU_SHIFT_IMM_LSL_1TO4) || (cached_type == TYPE_ALU_SHIFT_IMM_OTHER) || (cached_type == TYPE_ALU_EXT) || (cached_type == TYPE_ALUS_SHIFT_IMM) || (cached_type == TYPE_ALUS_EXT) || (cached_type == TYPE_LOGIC_SHIFT_IMM) || (cached_type == TYPE_LOGICS_SHIFT_IMM)))
        {
	  return 2;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_ALU_SHIFT_IMM_LSL_1TO4) || (cached_type == TYPE_ALU_SHIFT_IMM_OTHER) || (cached_type == TYPE_ALU_EXT) || (cached_type == TYPE_ALUS_SHIFT_IMM) || (cached_type == TYPE_ALUS_EXT) || (cached_type == TYPE_LOGIC_SHIFT_IMM) || (cached_type == TYPE_LOGICS_SHIFT_IMM)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_SDIV) || (cached_type == TYPE_UDIV)))
        {
	  return 13 /* 0xd */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_MLA) || (cached_type == TYPE_SMLAL) || (cached_type == TYPE_UMLAL)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_MUL) || (cached_type == TYPE_SMULL) || (cached_type == TYPE_UMULL)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && (cached_type == TYPE_CLZ))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && (cached_type == TYPE_LOAD_4))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_LOAD_8) || (cached_type == TYPE_LOAD_16)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && (cached_type == TYPE_STORE_4))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_STORE_8) || (cached_type == TYPE_STORE_16)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_FFARITHS) || (cached_type == TYPE_FFARITHD) || (cached_type == TYPE_F_MINMAXS) || (cached_type == TYPE_F_MINMAXD)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_FADDS) || (cached_type == TYPE_FADDD)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_FADDS) || (cached_type == TYPE_FADDD)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_FCMPS) || (cached_type == TYPE_FCMPD) || (cached_type == TYPE_FCCMPS) || (cached_type == TYPE_FCCMPD)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_FDIVS) || (cached_type == TYPE_FSQRTS)))
        {
	  return 16 /* 0x10 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_FDIVD) || (cached_type == TYPE_FSQRTD)))
        {
	  return 23 /* 0x17 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_FMULS) || (cached_type == TYPE_FMULD) || (cached_type == TYPE_FMACS) || (cached_type == TYPE_FMACD)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_F_RINTS) || (cached_type == TYPE_F_RINTD)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && (cached_type == TYPE_FCSEL))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_F_CVTF2I) || (cached_type == TYPE_F_CVT) || (cached_type == TYPE_F_CVTI2F)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_FCONSTS) || (cached_type == TYPE_FCONSTD) || (cached_type == TYPE_FMOV) || (cached_type == TYPE_F_MRC)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_FCONSTS) || (cached_type == TYPE_FCONSTD) || (cached_type == TYPE_FMOV) || (cached_type == TYPE_F_MRC)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && (cached_type == TYPE_F_MCR))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_F_LOADS) || (cached_type == TYPE_F_LOADD)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_F_STORES) || (cached_type == TYPE_F_STORED)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_ABD) || (cached_type == TYPE_NEON_ABD_Q) || (cached_type == TYPE_NEON_ARITH_ACC) || (cached_type == TYPE_NEON_ARITH_ACC_Q) || (cached_type == TYPE_NEON_ABS) || (cached_type == TYPE_NEON_ABS_Q) || (cached_type == TYPE_NEON_ADD) || (cached_type == TYPE_NEON_ADD_Q) || (cached_type == TYPE_NEON_SUB) || (cached_type == TYPE_NEON_SUB_Q) || (cached_type == TYPE_NEON_NEG) || (cached_type == TYPE_NEON_NEG_Q) || (cached_type == TYPE_NEON_ADD_LONG) || (cached_type == TYPE_NEON_ADD_WIDEN) || (cached_type == TYPE_NEON_ADD_HALVE) || (cached_type == TYPE_NEON_ADD_HALVE_Q) || (cached_type == TYPE_NEON_SUB_LONG) || (cached_type == TYPE_NEON_SUB_WIDEN) || (cached_type == TYPE_NEON_SUB_HALVE) || (cached_type == TYPE_NEON_SUB_HALVE_Q) || (cached_type == TYPE_NEON_ADD_HALVE_NARROW_Q) || (cached_type == TYPE_NEON_SUB_HALVE_NARROW_Q) || (cached_type == TYPE_NEON_QABS) || (cached_type == TYPE_NEON_QABS_Q) || (cached_type == TYPE_NEON_QADD) || (cached_type == TYPE_NEON_QADD_Q) || (cached_type == TYPE_NEON_QNEG) || (cached_type == TYPE_NEON_QNEG_Q) || (cached_type == TYPE_NEON_QSUB) || (cached_type == TYPE_NEON_QSUB_Q) || (cached_type == TYPE_NEON_MINMAX) || (cached_type == TYPE_NEON_MINMAX_Q) || (cached_type == TYPE_NEON_REDUC_MINMAX) || (cached_type == TYPE_NEON_REDUC_MINMAX_Q) || (cached_type == TYPE_NEON_MUL_B) || (cached_type == TYPE_NEON_MUL_H) || (cached_type == TYPE_NEON_MUL_S) || (cached_type == TYPE_NEON_MUL_B_Q) || (cached_type == TYPE_NEON_MUL_H_Q) || (cached_type == TYPE_NEON_MUL_S_Q) || (cached_type == TYPE_NEON_SAT_MUL_B) || (cached_type == TYPE_NEON_SAT_MUL_H) || (cached_type == TYPE_NEON_SAT_MUL_S) || (cached_type == TYPE_NEON_SAT_MUL_B_Q) || (cached_type == TYPE_NEON_SAT_MUL_H_Q) || (cached_type == TYPE_NEON_SAT_MUL_S_Q) || (cached_type == TYPE_NEON_MLA_B) || (cached_type == TYPE_NEON_MLA_H) || (cached_type == TYPE_NEON_MLA_S) || (cached_type == TYPE_NEON_MLA_B_Q) || (cached_type == TYPE_NEON_MLA_H_Q) || (cached_type == TYPE_NEON_MLA_S_Q) || (cached_type == TYPE_NEON_MUL_B_LONG) || (cached_type == TYPE_NEON_MUL_H_LONG) || (cached_type == TYPE_NEON_MUL_S_LONG) || (cached_type == TYPE_NEON_MUL_D_LONG) || (cached_type == TYPE_NEON_SAT_MUL_B_LONG) || (cached_type == TYPE_NEON_SAT_MUL_H_LONG) || (cached_type == TYPE_NEON_SAT_MUL_S_LONG) || (cached_type == TYPE_NEON_MLA_B_LONG) || (cached_type == TYPE_NEON_MLA_H_LONG) || (cached_type == TYPE_NEON_MLA_S_LONG) || (cached_type == TYPE_NEON_SAT_MLA_B_LONG) || (cached_type == TYPE_NEON_SAT_MLA_H_LONG) || (cached_type == TYPE_NEON_SAT_MLA_S_LONG) || (cached_type == TYPE_NEON_SHIFT_ACC) || (cached_type == TYPE_NEON_SHIFT_ACC_Q) || (cached_type == TYPE_NEON_SHIFT_IMM) || (cached_type == TYPE_NEON_SHIFT_IMM_Q) || (cached_type == TYPE_NEON_SHIFT_REG) || (cached_type == TYPE_NEON_SHIFT_REG_Q) || (cached_type == TYPE_NEON_SHIFT_IMM_LONG) || (cached_type == TYPE_NEON_SHIFT_IMM_NARROW_Q) || (cached_type == TYPE_NEON_SAT_SHIFT_IMM) || (cached_type == TYPE_NEON_SAT_SHIFT_IMM_Q) || (cached_type == TYPE_NEON_SAT_SHIFT_REG) || (cached_type == TYPE_NEON_SAT_SHIFT_REG_Q) || (cached_type == TYPE_NEON_SAT_SHIFT_IMM_NARROW_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_REDUC_ADD) || (cached_type == TYPE_NEON_REDUC_ADD_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_COMPARE) || (cached_type == TYPE_NEON_COMPARE_Q) || (cached_type == TYPE_NEON_COMPARE_ZERO) || (cached_type == TYPE_NEON_TST) || (cached_type == TYPE_NEON_TST_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_LOGIC) || (cached_type == TYPE_NEON_LOGIC_Q)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_LOGIC) || (cached_type == TYPE_NEON_LOGIC_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_FP_ABS_S) || (cached_type == TYPE_NEON_FP_ABS_D) || (cached_type == TYPE_NEON_FP_ABS_S_Q) || (cached_type == TYPE_NEON_FP_ABS_D_Q) || (cached_type == TYPE_NEON_FP_COMPARE_S) || (cached_type == TYPE_NEON_FP_COMPARE_D) || (cached_type == TYPE_NEON_FP_COMPARE_S_Q) || (cached_type == TYPE_NEON_FP_COMPARE_D_Q) || (cached_type == TYPE_NEON_FP_MINMAX_S) || (cached_type == TYPE_NEON_FP_MINMAX_D) || (cached_type == TYPE_NEON_FP_MINMAX_S_Q) || (cached_type == TYPE_NEON_FP_MINMAX_D_Q) || (cached_type == TYPE_NEON_FP_REDUC_MINMAX_S) || (cached_type == TYPE_NEON_FP_REDUC_MINMAX_D) || (cached_type == TYPE_NEON_FP_REDUC_MINMAX_S_Q) || (cached_type == TYPE_NEON_FP_REDUC_MINMAX_D_Q) || (cached_type == TYPE_NEON_FP_NEG_S) || (cached_type == TYPE_NEON_FP_NEG_D) || (cached_type == TYPE_NEON_FP_NEG_S_Q) || (cached_type == TYPE_NEON_FP_NEG_D_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_FP_ABD_S) || (cached_type == TYPE_NEON_FP_ABD_D) || (cached_type == TYPE_NEON_FP_ABD_S_Q) || (cached_type == TYPE_NEON_FP_ABD_D_Q) || (cached_type == TYPE_NEON_FP_ADDSUB_S) || (cached_type == TYPE_NEON_FP_ADDSUB_D) || (cached_type == TYPE_NEON_FP_ADDSUB_S_Q) || (cached_type == TYPE_NEON_FP_ADDSUB_D_Q) || (cached_type == TYPE_NEON_FP_REDUC_ADD_S) || (cached_type == TYPE_NEON_FP_REDUC_ADD_D) || (cached_type == TYPE_NEON_FP_REDUC_ADD_S_Q) || (cached_type == TYPE_NEON_FP_REDUC_ADD_D_Q)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_FP_ABD_S) || (cached_type == TYPE_NEON_FP_ABD_D) || (cached_type == TYPE_NEON_FP_ABD_S_Q) || (cached_type == TYPE_NEON_FP_ABD_D_Q) || (cached_type == TYPE_NEON_FP_ADDSUB_S) || (cached_type == TYPE_NEON_FP_ADDSUB_D) || (cached_type == TYPE_NEON_FP_ADDSUB_S_Q) || (cached_type == TYPE_NEON_FP_ADDSUB_D_Q) || (cached_type == TYPE_NEON_FP_REDUC_ADD_S) || (cached_type == TYPE_NEON_FP_REDUC_ADD_D) || (cached_type == TYPE_NEON_FP_REDUC_ADD_S_Q) || (cached_type == TYPE_NEON_FP_REDUC_ADD_D_Q)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_FP_MUL_S) || (cached_type == TYPE_NEON_FP_MUL_D) || (cached_type == TYPE_NEON_FP_MUL_S_Q) || (cached_type == TYPE_NEON_FP_MUL_D_Q) || (cached_type == TYPE_NEON_FP_MUL_S_SCALAR_Q) || (cached_type == TYPE_NEON_FP_MUL_D_SCALAR_Q) || (cached_type == TYPE_NEON_FP_MLA_S) || (cached_type == TYPE_NEON_FP_MLA_D) || (cached_type == TYPE_NEON_FP_MLA_S_Q) || (cached_type == TYPE_NEON_FP_MLA_D_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_FP_CVT_WIDEN_S) || (cached_type == TYPE_NEON_FP_CVT_NARROW_D_Q) || (cached_type == TYPE_NEON_FP_TO_INT_S) || (cached_type == TYPE_NEON_FP_TO_INT_D) || (cached_type == TYPE_NEON_FP_TO_INT_S_Q) || (cached_type == TYPE_NEON_FP_TO_INT_D_Q) || (cached_type == TYPE_NEON_INT_TO_FP_S) || (cached_type == TYPE_NEON_INT_TO_FP_D) || (cached_type == TYPE_NEON_INT_TO_FP_S_Q) || (cached_type == TYPE_NEON_INT_TO_FP_D_Q) || (cached_type == TYPE_NEON_FP_ROUND_S) || (cached_type == TYPE_NEON_FP_ROUND_D) || (cached_type == TYPE_NEON_FP_ROUND_S_Q) || (cached_type == TYPE_NEON_FP_ROUND_D_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_FP_DIV_S) || (cached_type == TYPE_NEON_FP_DIV_S_Q)))
        {
	  return 16 /* 0x10 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_FP_DIV_D) || (cached_type == TYPE_NEON_FP_DIV_D_Q)))
        {
	  return 23 /* 0x17 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_RBIT) || (cached_type == TYPE_NEON_BSL) || (cached_type == TYPE_NEON_BSL_Q) || (cached_type == TYPE_NEON_CLS) || (cached_type == TYPE_NEON_CLS_Q) || (cached_type == TYPE_NEON_CNT) || (cached_type == TYPE_NEON_CNT_Q) || (cached_type == TYPE_NEON_MOVE) || (cached_type == TYPE_NEON_MOVE_Q)))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_RBIT) || (cached_type == TYPE_NEON_BSL) || (cached_type == TYPE_NEON_BSL_Q) || (cached_type == TYPE_NEON_CLS) || (cached_type == TYPE_NEON_CLS_Q) || (cached_type == TYPE_NEON_CNT) || (cached_type == TYPE_NEON_CNT_Q) || (cached_type == TYPE_NEON_FROM_GP) || (cached_type == TYPE_NEON_FROM_GP_Q) || (cached_type == TYPE_NEON_MOVE) || (cached_type == TYPE_NEON_MOVE_Q)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_DUP) || (cached_type == TYPE_NEON_DUP_Q) || (cached_type == TYPE_NEON_EXT) || (cached_type == TYPE_NEON_EXT_Q) || (cached_type == TYPE_NEON_INS) || (cached_type == TYPE_NEON_INS_Q) || (cached_type == TYPE_NEON_MOVE) || (cached_type == TYPE_NEON_MOVE_Q) || (cached_type == TYPE_NEON_FP_RECPE_S) || (cached_type == TYPE_NEON_FP_RECPE_D) || (cached_type == TYPE_NEON_FP_RECPE_S_Q) || (cached_type == TYPE_NEON_FP_RECPE_D_Q) || (cached_type == TYPE_NEON_FP_RECPX_S) || (cached_type == TYPE_NEON_FP_RECPX_D) || (cached_type == TYPE_NEON_FP_RECPX_S_Q) || (cached_type == TYPE_NEON_FP_RECPX_D_Q) || (cached_type == TYPE_NEON_REV) || (cached_type == TYPE_NEON_REV_Q) || (cached_type == TYPE_NEON_PERMUTE) || (cached_type == TYPE_NEON_PERMUTE_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_FP_RECPS_S) || (cached_type == TYPE_NEON_FP_RECPS_S_Q) || (cached_type == TYPE_NEON_FP_RECPS_D) || (cached_type == TYPE_NEON_FP_RECPS_D_Q) || (cached_type == TYPE_NEON_FP_SQRT_S) || (cached_type == TYPE_NEON_FP_SQRT_S_Q) || (cached_type == TYPE_NEON_FP_SQRT_D) || (cached_type == TYPE_NEON_FP_SQRT_D_Q) || (cached_type == TYPE_NEON_FP_RSQRTE_S) || (cached_type == TYPE_NEON_FP_RSQRTE_S_Q) || (cached_type == TYPE_NEON_FP_RSQRTE_D) || (cached_type == TYPE_NEON_FP_RSQRTE_D_Q) || (cached_type == TYPE_NEON_FP_RSQRTS_S) || (cached_type == TYPE_NEON_FP_RSQRTS_S_Q) || (cached_type == TYPE_NEON_FP_RSQRTS_D) || (cached_type == TYPE_NEON_FP_RSQRTS_D_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_TBL1) || (cached_type == TYPE_NEON_TBL1_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_TBL2) || (cached_type == TYPE_NEON_TBL2_Q)))
        {
	  return 10 /* 0xa */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_TBL3) || (cached_type == TYPE_NEON_TBL3_Q)))
        {
	  return 15 /* 0xf */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_TBL4) || (cached_type == TYPE_NEON_TBL4_Q)))
        {
	  return 20 /* 0x14 */;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_TO_GP) || (cached_type == TYPE_NEON_TO_GP_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_LDP) || (cached_type == TYPE_NEON_LDP_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_LOAD1_1REG) || (cached_type == TYPE_NEON_LOAD1_1REG_Q) || (cached_type == TYPE_NEON_LOAD1_2REG) || (cached_type == TYPE_NEON_LOAD1_2REG_Q) || (cached_type == TYPE_NEON_LOAD1_3REG) || (cached_type == TYPE_NEON_LOAD1_3REG_Q) || (cached_type == TYPE_NEON_LOAD1_4REG) || (cached_type == TYPE_NEON_LOAD1_4REG_Q)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_LOAD1_ONE_LANE) || (cached_type == TYPE_NEON_LOAD1_ONE_LANE_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_LOAD1_ALL_LANES) || (cached_type == TYPE_NEON_LOAD1_ALL_LANES_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_LOAD2_2REG) || (cached_type == TYPE_NEON_LOAD2_2REG_Q) || (cached_type == TYPE_NEON_LOAD2_ONE_LANE) || (cached_type == TYPE_NEON_LOAD2_ONE_LANE_Q) || (cached_type == TYPE_NEON_LOAD2_ALL_LANES) || (cached_type == TYPE_NEON_LOAD2_ALL_LANES_Q)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_LOAD3_3REG) || (cached_type == TYPE_NEON_LOAD3_3REG_Q) || (cached_type == TYPE_NEON_LOAD3_ONE_LANE) || (cached_type == TYPE_NEON_LOAD3_ONE_LANE_Q) || (cached_type == TYPE_NEON_LOAD3_ALL_LANES) || (cached_type == TYPE_NEON_LOAD3_ALL_LANES_Q)))
        {
	  return 7;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_LOAD4_4REG) || (cached_type == TYPE_NEON_LOAD4_4REG_Q) || (cached_type == TYPE_NEON_LOAD4_ONE_LANE) || (cached_type == TYPE_NEON_LOAD4_ONE_LANE_Q) || (cached_type == TYPE_NEON_LOAD4_ALL_LANES) || (cached_type == TYPE_NEON_LOAD4_ALL_LANES_Q)))
        {
	  return 8;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_STP) || (cached_type == TYPE_NEON_STP_Q)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_STORE1_1REG) || (cached_type == TYPE_NEON_STORE1_1REG_Q) || (cached_type == TYPE_NEON_STORE1_2REG) || (cached_type == TYPE_NEON_STORE1_2REG_Q) || (cached_type == TYPE_NEON_STORE1_3REG) || (cached_type == TYPE_NEON_STORE1_4REG)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_STORE1_ONE_LANE) || (cached_type == TYPE_NEON_STORE1_ONE_LANE_Q)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_STORE2_2REG) || (cached_type == TYPE_NEON_STORE2_2REG_Q) || (cached_type == TYPE_NEON_STORE2_ONE_LANE) || (cached_type == TYPE_NEON_STORE2_ONE_LANE_Q)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_STORE3_3REG) || (cached_type == TYPE_NEON_STORE3_3REG_Q) || (cached_type == TYPE_NEON_STORE3_ONE_LANE) || (cached_type == TYPE_NEON_STORE3_ONE_LANE_Q)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_NEON_STORE4_4REG) || (cached_type == TYPE_NEON_STORE4_4REG_Q) || (cached_type == TYPE_NEON_STORE4_ONE_LANE) || (cached_type == TYPE_NEON_STORE4_ONE_LANE_Q)))
        {
	  return 1;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_CRYPTO_AESE) || (cached_type == TYPE_CRYPTO_AESMC)))
        {
	  return 4;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && ((cached_type == TYPE_CRYPTO_SHA1_FAST) || (cached_type == TYPE_CRYPTO_SHA1_XOR) || (cached_type == TYPE_CRYPTO_SHA1_SLOW) || (cached_type == TYPE_CRYPTO_SHA256_FAST) || (cached_type == TYPE_CRYPTO_SHA256_SLOW)))
        {
	  return 5;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && (cached_type == TYPE_CRC))
        {
	  return 3;
        }
      else if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX3T110)))) && (cached_type == TYPE_CRYPTO_PMULL))
        {
	  return 5;
        }
      else
        {
	  return 0;
        }

    default:
      if ((((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX)))) || (((
#line 5 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64-tune.md"
(((enum attr_tune) aarch64_tune))) == (
(TUNE_THUNDERX2T99)))))
        {
	  return 1;
        }
      else
        {
	  return 0;
        }

    }
}

