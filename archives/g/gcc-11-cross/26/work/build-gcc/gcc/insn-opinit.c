/* Generated automatically by the program `genopinit'
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
#include "varasm.h"
#include "stor-layout.h"
#include "calls.h"
#include "memmodel.h"
#include "tm_p.h"
#include "flags.h"
#include "insn-config.h"
#include "expmed.h"
#include "dojump.h"
#include "explow.h"
#include "emit-rtl.h"
#include "stmt.h"
#include "expr.h"
#include "insn-codes.h"
#include "optabs.h"

struct optab_pat {
  unsigned scode;
  enum insn_code icode;
};

static const struct optab_pat pats[NUM_OPTAB_PATTERNS] = {
  { 0x010d0e, CODE_FOR_extendqihi2 },
  { 0x010d0f, CODE_FOR_extendqisi2 },
  { 0x010d10, CODE_FOR_extendqidi2 },
  { 0x010e0f, CODE_FOR_extendhisi2 },
  { 0x010e10, CODE_FOR_extendhidi2 },
  { 0x010f10, CODE_FOR_extendsidi2 },
  { 0x012729, CODE_FOR_extendhfsf2 },
  { 0x01272a, CODE_FOR_extendhfdf2 },
  { 0x01292a, CODE_FOR_extendsfdf2 },
  { 0x014045, CODE_FOR_extendv8qiv8hi2 },
  { 0x014147, CODE_FOR_extendv4hiv4si2 },
  { 0x014249, CODE_FOR_extendv2siv2di2 },
  { 0x015b46, CODE_FOR_extendvnx2qivnx8hi2 },
  { 0x015b48, CODE_FOR_extendvnx2qivnx4si2 },
  { 0x015b4a, CODE_FOR_extendvnx2qivnx2di2 },
  { 0x015b5d, CODE_FOR_extendvnx2qivnx2hi2 },
  { 0x015b5f, CODE_FOR_extendvnx2qivnx4hi2 },
  { 0x015b60, CODE_FOR_extendvnx2qivnx2si2 },
  { 0x015c46, CODE_FOR_extendvnx4qivnx8hi2 },
  { 0x015c48, CODE_FOR_extendvnx4qivnx4si2 },
  { 0x015c4a, CODE_FOR_extendvnx4qivnx2di2 },
  { 0x015c5d, CODE_FOR_extendvnx4qivnx2hi2 },
  { 0x015c5f, CODE_FOR_extendvnx4qivnx4hi2 },
  { 0x015c60, CODE_FOR_extendvnx4qivnx2si2 },
  { 0x015d46, CODE_FOR_extendvnx2hivnx8hi2 },
  { 0x015d48, CODE_FOR_extendvnx2hivnx4si2 },
  { 0x015d4a, CODE_FOR_extendvnx2hivnx2di2 },
  { 0x015d5d, CODE_FOR_extendvnx2hivnx2hi2 },
  { 0x015d5f, CODE_FOR_extendvnx2hivnx4hi2 },
  { 0x015d60, CODE_FOR_extendvnx2hivnx2si2 },
  { 0x015e46, CODE_FOR_extendvnx8qivnx8hi2 },
  { 0x015e48, CODE_FOR_extendvnx8qivnx4si2 },
  { 0x015e4a, CODE_FOR_extendvnx8qivnx2di2 },
  { 0x015e5d, CODE_FOR_extendvnx8qivnx2hi2 },
  { 0x015e5f, CODE_FOR_extendvnx8qivnx4hi2 },
  { 0x015e60, CODE_FOR_extendvnx8qivnx2si2 },
  { 0x015f46, CODE_FOR_extendvnx4hivnx8hi2 },
  { 0x015f48, CODE_FOR_extendvnx4hivnx4si2 },
  { 0x015f4a, CODE_FOR_extendvnx4hivnx2di2 },
  { 0x015f5d, CODE_FOR_extendvnx4hivnx2hi2 },
  { 0x015f5f, CODE_FOR_extendvnx4hivnx4hi2 },
  { 0x015f60, CODE_FOR_extendvnx4hivnx2si2 },
  { 0x016046, CODE_FOR_extendvnx2sivnx8hi2 },
  { 0x016048, CODE_FOR_extendvnx2sivnx4si2 },
  { 0x01604a, CODE_FOR_extendvnx2sivnx2di2 },
  { 0x01605d, CODE_FOR_extendvnx2sivnx2hi2 },
  { 0x01605f, CODE_FOR_extendvnx2sivnx4hi2 },
  { 0x016060, CODE_FOR_extendvnx2sivnx2si2 },
  { 0x022927, CODE_FOR_truncsfhf2 },
  { 0x022a27, CODE_FOR_truncdfhf2 },
  { 0x022a29, CODE_FOR_truncdfsf2 },
  { 0x024540, CODE_FOR_truncv8hiv8qi2 },
  { 0x02465b, CODE_FOR_truncvnx8hivnx2qi2 },
  { 0x02465c, CODE_FOR_truncvnx8hivnx4qi2 },
  { 0x02465d, CODE_FOR_truncvnx8hivnx2hi2 },
  { 0x02465e, CODE_FOR_truncvnx8hivnx8qi2 },
  { 0x02465f, CODE_FOR_truncvnx8hivnx4hi2 },
  { 0x024660, CODE_FOR_truncvnx8hivnx2si2 },
  { 0x024741, CODE_FOR_truncv4siv4hi2 },
  { 0x02485b, CODE_FOR_truncvnx4sivnx2qi2 },
  { 0x02485c, CODE_FOR_truncvnx4sivnx4qi2 },
  { 0x02485d, CODE_FOR_truncvnx4sivnx2hi2 },
  { 0x02485e, CODE_FOR_truncvnx4sivnx8qi2 },
  { 0x02485f, CODE_FOR_truncvnx4sivnx4hi2 },
  { 0x024860, CODE_FOR_truncvnx4sivnx2si2 },
  { 0x024942, CODE_FOR_truncv2div2si2 },
  { 0x024a5b, CODE_FOR_truncvnx2divnx2qi2 },
  { 0x024a5c, CODE_FOR_truncvnx2divnx4qi2 },
  { 0x024a5d, CODE_FOR_truncvnx2divnx2hi2 },
  { 0x024a5e, CODE_FOR_truncvnx2divnx8qi2 },
  { 0x024a5f, CODE_FOR_truncvnx2divnx4hi2 },
  { 0x024a60, CODE_FOR_truncvnx2divnx2si2 },
  { 0x025d5b, CODE_FOR_truncvnx2hivnx2qi2 },
  { 0x025d5c, CODE_FOR_truncvnx2hivnx4qi2 },
  { 0x025d5d, CODE_FOR_truncvnx2hivnx2hi2 },
  { 0x025d5e, CODE_FOR_truncvnx2hivnx8qi2 },
  { 0x025d5f, CODE_FOR_truncvnx2hivnx4hi2 },
  { 0x025d60, CODE_FOR_truncvnx2hivnx2si2 },
  { 0x025f5b, CODE_FOR_truncvnx4hivnx2qi2 },
  { 0x025f5c, CODE_FOR_truncvnx4hivnx4qi2 },
  { 0x025f5d, CODE_FOR_truncvnx4hivnx2hi2 },
  { 0x025f5e, CODE_FOR_truncvnx4hivnx8qi2 },
  { 0x025f5f, CODE_FOR_truncvnx4hivnx4hi2 },
  { 0x025f60, CODE_FOR_truncvnx4hivnx2si2 },
  { 0x02605b, CODE_FOR_truncvnx2sivnx2qi2 },
  { 0x02605c, CODE_FOR_truncvnx2sivnx4qi2 },
  { 0x02605d, CODE_FOR_truncvnx2sivnx2hi2 },
  { 0x02605e, CODE_FOR_truncvnx2sivnx8qi2 },
  { 0x02605f, CODE_FOR_truncvnx2sivnx4hi2 },
  { 0x026060, CODE_FOR_truncvnx2sivnx2si2 },
  { 0x030d0e, CODE_FOR_zero_extendqihi2 },
  { 0x030d0f, CODE_FOR_zero_extendqisi2 },
  { 0x030d10, CODE_FOR_zero_extendqidi2 },
  { 0x030e0f, CODE_FOR_zero_extendhisi2 },
  { 0x030e10, CODE_FOR_zero_extendhidi2 },
  { 0x030f10, CODE_FOR_zero_extendsidi2 },
  { 0x034045, CODE_FOR_zero_extendv8qiv8hi2 },
  { 0x034147, CODE_FOR_zero_extendv4hiv4si2 },
  { 0x034249, CODE_FOR_zero_extendv2siv2di2 },
  { 0x035b46, CODE_FOR_zero_extendvnx2qivnx8hi2 },
  { 0x035b48, CODE_FOR_zero_extendvnx2qivnx4si2 },
  { 0x035b4a, CODE_FOR_zero_extendvnx2qivnx2di2 },
  { 0x035b5d, CODE_FOR_zero_extendvnx2qivnx2hi2 },
  { 0x035b5f, CODE_FOR_zero_extendvnx2qivnx4hi2 },
  { 0x035b60, CODE_FOR_zero_extendvnx2qivnx2si2 },
  { 0x035c46, CODE_FOR_zero_extendvnx4qivnx8hi2 },
  { 0x035c48, CODE_FOR_zero_extendvnx4qivnx4si2 },
  { 0x035c4a, CODE_FOR_zero_extendvnx4qivnx2di2 },
  { 0x035c5d, CODE_FOR_zero_extendvnx4qivnx2hi2 },
  { 0x035c5f, CODE_FOR_zero_extendvnx4qivnx4hi2 },
  { 0x035c60, CODE_FOR_zero_extendvnx4qivnx2si2 },
  { 0x035d46, CODE_FOR_zero_extendvnx2hivnx8hi2 },
  { 0x035d48, CODE_FOR_zero_extendvnx2hivnx4si2 },
  { 0x035d4a, CODE_FOR_zero_extendvnx2hivnx2di2 },
  { 0x035d5d, CODE_FOR_zero_extendvnx2hivnx2hi2 },
  { 0x035d5f, CODE_FOR_zero_extendvnx2hivnx4hi2 },
  { 0x035d60, CODE_FOR_zero_extendvnx2hivnx2si2 },
  { 0x035e46, CODE_FOR_zero_extendvnx8qivnx8hi2 },
  { 0x035e48, CODE_FOR_zero_extendvnx8qivnx4si2 },
  { 0x035e4a, CODE_FOR_zero_extendvnx8qivnx2di2 },
  { 0x035e5d, CODE_FOR_zero_extendvnx8qivnx2hi2 },
  { 0x035e5f, CODE_FOR_zero_extendvnx8qivnx4hi2 },
  { 0x035e60, CODE_FOR_zero_extendvnx8qivnx2si2 },
  { 0x035f46, CODE_FOR_zero_extendvnx4hivnx8hi2 },
  { 0x035f48, CODE_FOR_zero_extendvnx4hivnx4si2 },
  { 0x035f4a, CODE_FOR_zero_extendvnx4hivnx2di2 },
  { 0x035f5d, CODE_FOR_zero_extendvnx4hivnx2hi2 },
  { 0x035f5f, CODE_FOR_zero_extendvnx4hivnx4hi2 },
  { 0x035f60, CODE_FOR_zero_extendvnx4hivnx2si2 },
  { 0x036046, CODE_FOR_zero_extendvnx2sivnx8hi2 },
  { 0x036048, CODE_FOR_zero_extendvnx2sivnx4si2 },
  { 0x03604a, CODE_FOR_zero_extendvnx2sivnx2di2 },
  { 0x03605d, CODE_FOR_zero_extendvnx2sivnx2hi2 },
  { 0x03605f, CODE_FOR_zero_extendvnx2sivnx4hi2 },
  { 0x036060, CODE_FOR_zero_extendvnx2sivnx2si2 },
  { 0x046341, CODE_FOR_fixv4hfv4hi2 },
  { 0x046442, CODE_FOR_fixv2sfv2si2 },
  { 0x046745, CODE_FOR_fixv8hfv8hi2 },
  { 0x046a47, CODE_FOR_fixv4sfv4si2 },
  { 0x046c49, CODE_FOR_fixv2dfv2di2 },
  { 0x056341, CODE_FOR_fixunsv4hfv4hi2 },
  { 0x056442, CODE_FOR_fixunsv2sfv2si2 },
  { 0x056745, CODE_FOR_fixunsv8hfv8hi2 },
  { 0x056a47, CODE_FOR_fixunsv4sfv4si2 },
  { 0x056c49, CODE_FOR_fixunsv2dfv2di2 },
  { 0x060e27, CODE_FOR_floathihf2 },
  { 0x060f27, CODE_FOR_floatsihf2 },
  { 0x060f29, CODE_FOR_floatsisf2 },
  { 0x060f2a, CODE_FOR_floatsidf2 },
  { 0x061027, CODE_FOR_floatdihf2 },
  { 0x061029, CODE_FOR_floatdisf2 },
  { 0x06102a, CODE_FOR_floatdidf2 },
  { 0x064163, CODE_FOR_floatv4hiv4hf2 },
  { 0x064264, CODE_FOR_floatv2siv2sf2 },
  { 0x064567, CODE_FOR_floatv8hiv8hf2 },
  { 0x064669, CODE_FOR_floatvnx8hivnx8hf2 },
  { 0x06476a, CODE_FOR_floatv4siv4sf2 },
  { 0x06486b, CODE_FOR_floatvnx4sivnx4sf2 },
  { 0x06496c, CODE_FOR_floatv2div2df2 },
  { 0x064a6d, CODE_FOR_floatvnx2divnx2df2 },
  { 0x070e27, CODE_FOR_floatunshihf2 },
  { 0x070f27, CODE_FOR_floatunssihf2 },
  { 0x070f29, CODE_FOR_floatunssisf2 },
  { 0x070f2a, CODE_FOR_floatunssidf2 },
  { 0x071027, CODE_FOR_floatunsdihf2 },
  { 0x071029, CODE_FOR_floatunsdisf2 },
  { 0x07102a, CODE_FOR_floatunsdidf2 },
  { 0x074163, CODE_FOR_floatunsv4hiv4hf2 },
  { 0x074264, CODE_FOR_floatunsv2siv2sf2 },
  { 0x074567, CODE_FOR_floatunsv8hiv8hf2 },
  { 0x074669, CODE_FOR_floatunsvnx8hivnx8hf2 },
  { 0x07476a, CODE_FOR_floatunsv4siv4sf2 },
  { 0x07486b, CODE_FOR_floatunsvnx4sivnx4sf2 },
  { 0x07496c, CODE_FOR_floatunsv2div2df2 },
  { 0x074a6d, CODE_FOR_floatunsvnx2divnx2df2 },
  { 0x08290f, CODE_FOR_lrintsfsi2 },
  { 0x082910, CODE_FOR_lrintsfdi2 },
  { 0x082a0f, CODE_FOR_lrintdfsi2 },
  { 0x082a10, CODE_FOR_lrintdfdi2 },
  { 0x09270e, CODE_FOR_lroundhfhi2 },
  { 0x09270f, CODE_FOR_lroundhfsi2 },
  { 0x092710, CODE_FOR_lroundhfdi2 },
  { 0x09290f, CODE_FOR_lroundsfsi2 },
  { 0x092910, CODE_FOR_lroundsfdi2 },
  { 0x092a0f, CODE_FOR_lrounddfsi2 },
  { 0x092a10, CODE_FOR_lrounddfdi2 },
  { 0x096341, CODE_FOR_lroundv4hfv4hi2 },
  { 0x096442, CODE_FOR_lroundv2sfv2si2 },
  { 0x096745, CODE_FOR_lroundv8hfv8hi2 },
  { 0x096a47, CODE_FOR_lroundv4sfv4si2 },
  { 0x096c49, CODE_FOR_lroundv2dfv2di2 },
  { 0x0a270e, CODE_FOR_lfloorhfhi2 },
  { 0x0a270f, CODE_FOR_lfloorhfsi2 },
  { 0x0a2710, CODE_FOR_lfloorhfdi2 },
  { 0x0a290f, CODE_FOR_lfloorsfsi2 },
  { 0x0a2910, CODE_FOR_lfloorsfdi2 },
  { 0x0a2a0f, CODE_FOR_lfloordfsi2 },
  { 0x0a2a10, CODE_FOR_lfloordfdi2 },
  { 0x0a6341, CODE_FOR_lfloorv4hfv4hi2 },
  { 0x0a6442, CODE_FOR_lfloorv2sfv2si2 },
  { 0x0a6745, CODE_FOR_lfloorv8hfv8hi2 },
  { 0x0a6a47, CODE_FOR_lfloorv4sfv4si2 },
  { 0x0a6c49, CODE_FOR_lfloorv2dfv2di2 },
  { 0x0b270e, CODE_FOR_lceilhfhi2 },
  { 0x0b270f, CODE_FOR_lceilhfsi2 },
  { 0x0b2710, CODE_FOR_lceilhfdi2 },
  { 0x0b290f, CODE_FOR_lceilsfsi2 },
  { 0x0b2910, CODE_FOR_lceilsfdi2 },
  { 0x0b2a0f, CODE_FOR_lceildfsi2 },
  { 0x0b2a10, CODE_FOR_lceildfdi2 },
  { 0x0b6341, CODE_FOR_lceilv4hfv4hi2 },
  { 0x0b6442, CODE_FOR_lceilv2sfv2si2 },
  { 0x0b6745, CODE_FOR_lceilv8hfv8hi2 },
  { 0x0b6a47, CODE_FOR_lceilv4sfv4si2 },
  { 0x0b6c49, CODE_FOR_lceilv2dfv2di2 },
  { 0x10270e, CODE_FOR_fix_trunchfhi2 },
  { 0x10270f, CODE_FOR_fix_trunchfsi2 },
  { 0x102710, CODE_FOR_fix_trunchfdi2 },
  { 0x10290f, CODE_FOR_fix_truncsfsi2 },
  { 0x102910, CODE_FOR_fix_truncsfdi2 },
  { 0x102a0f, CODE_FOR_fix_truncdfsi2 },
  { 0x102a10, CODE_FOR_fix_truncdfdi2 },
  { 0x106341, CODE_FOR_fix_truncv4hfv4hi2 },
  { 0x106442, CODE_FOR_fix_truncv2sfv2si2 },
  { 0x106745, CODE_FOR_fix_truncv8hfv8hi2 },
  { 0x106946, CODE_FOR_fix_truncvnx8hfvnx8hi2 },
  { 0x106a47, CODE_FOR_fix_truncv4sfv4si2 },
  { 0x106b48, CODE_FOR_fix_truncvnx4sfvnx4si2 },
  { 0x106c49, CODE_FOR_fix_truncv2dfv2di2 },
  { 0x106d4a, CODE_FOR_fix_truncvnx2dfvnx2di2 },
  { 0x11270e, CODE_FOR_fixuns_trunchfhi2 },
  { 0x11270f, CODE_FOR_fixuns_trunchfsi2 },
  { 0x112710, CODE_FOR_fixuns_trunchfdi2 },
  { 0x11290f, CODE_FOR_fixuns_truncsfsi2 },
  { 0x112910, CODE_FOR_fixuns_truncsfdi2 },
  { 0x112a0f, CODE_FOR_fixuns_truncdfsi2 },
  { 0x112a10, CODE_FOR_fixuns_truncdfdi2 },
  { 0x116341, CODE_FOR_fixuns_truncv4hfv4hi2 },
  { 0x116442, CODE_FOR_fixuns_truncv2sfv2si2 },
  { 0x116745, CODE_FOR_fixuns_truncv8hfv8hi2 },
  { 0x116946, CODE_FOR_fixuns_truncvnx8hfvnx8hi2 },
  { 0x116a47, CODE_FOR_fixuns_truncv4sfv4si2 },
  { 0x116b48, CODE_FOR_fixuns_truncvnx4sfvnx4si2 },
  { 0x116c49, CODE_FOR_fixuns_truncv2dfv2di2 },
  { 0x116d4a, CODE_FOR_fixuns_truncvnx2dfvnx2di2 },
  { 0x120f10, CODE_FOR_mulsidi3 },
  { 0x121011, CODE_FOR_mulditi3 },
  { 0x130f10, CODE_FOR_umulsidi3 },
  { 0x131011, CODE_FOR_umulditi3 },
  { 0x150f10, CODE_FOR_maddsidi4 },
  { 0x160f10, CODE_FOR_umaddsidi4 },
  { 0x190f10, CODE_FOR_msubsidi4 },
  { 0x1a0f10, CODE_FOR_umsubsidi4 },
  { 0x1d4312, CODE_FOR_vec_load_lanesoiv16qi },
  { 0x1d4313, CODE_FOR_vec_load_lanesciv16qi },
  { 0x1d4314, CODE_FOR_vec_load_lanesxiv16qi },
  { 0x1d444b, CODE_FOR_vec_load_lanesvnx32qivnx16qi },
  { 0x1d4450, CODE_FOR_vec_load_lanesvnx48qivnx16qi },
  { 0x1d4455, CODE_FOR_vec_load_lanesvnx64qivnx16qi },
  { 0x1d4512, CODE_FOR_vec_load_lanesoiv8hi },
  { 0x1d4513, CODE_FOR_vec_load_lanesciv8hi },
  { 0x1d4514, CODE_FOR_vec_load_lanesxiv8hi },
  { 0x1d464c, CODE_FOR_vec_load_lanesvnx16hivnx8hi },
  { 0x1d4651, CODE_FOR_vec_load_lanesvnx24hivnx8hi },
  { 0x1d4656, CODE_FOR_vec_load_lanesvnx32hivnx8hi },
  { 0x1d4712, CODE_FOR_vec_load_lanesoiv4si },
  { 0x1d4713, CODE_FOR_vec_load_lanesciv4si },
  { 0x1d4714, CODE_FOR_vec_load_lanesxiv4si },
  { 0x1d484d, CODE_FOR_vec_load_lanesvnx8sivnx4si },
  { 0x1d4852, CODE_FOR_vec_load_lanesvnx12sivnx4si },
  { 0x1d4857, CODE_FOR_vec_load_lanesvnx16sivnx4si },
  { 0x1d4912, CODE_FOR_vec_load_lanesoiv2di },
  { 0x1d4913, CODE_FOR_vec_load_lanesciv2di },
  { 0x1d4914, CODE_FOR_vec_load_lanesxiv2di },
  { 0x1d4a4e, CODE_FOR_vec_load_lanesvnx4divnx2di },
  { 0x1d4a53, CODE_FOR_vec_load_lanesvnx6divnx2di },
  { 0x1d4a58, CODE_FOR_vec_load_lanesvnx8divnx2di },
  { 0x1d6612, CODE_FOR_vec_load_lanesoiv8bf },
  { 0x1d6613, CODE_FOR_vec_load_lanesciv8bf },
  { 0x1d6614, CODE_FOR_vec_load_lanesxiv8bf },
  { 0x1d6712, CODE_FOR_vec_load_lanesoiv8hf },
  { 0x1d6713, CODE_FOR_vec_load_lanesciv8hf },
  { 0x1d6714, CODE_FOR_vec_load_lanesxiv8hf },
  { 0x1d686e, CODE_FOR_vec_load_lanesvnx16bfvnx8bf },
  { 0x1d6872, CODE_FOR_vec_load_lanesvnx24bfvnx8bf },
  { 0x1d6876, CODE_FOR_vec_load_lanesvnx32bfvnx8bf },
  { 0x1d696f, CODE_FOR_vec_load_lanesvnx16hfvnx8hf },
  { 0x1d6973, CODE_FOR_vec_load_lanesvnx24hfvnx8hf },
  { 0x1d6977, CODE_FOR_vec_load_lanesvnx32hfvnx8hf },
  { 0x1d6a12, CODE_FOR_vec_load_lanesoiv4sf },
  { 0x1d6a13, CODE_FOR_vec_load_lanesciv4sf },
  { 0x1d6a14, CODE_FOR_vec_load_lanesxiv4sf },
  { 0x1d6b70, CODE_FOR_vec_load_lanesvnx8sfvnx4sf },
  { 0x1d6b74, CODE_FOR_vec_load_lanesvnx12sfvnx4sf },
  { 0x1d6b78, CODE_FOR_vec_load_lanesvnx16sfvnx4sf },
  { 0x1d6c12, CODE_FOR_vec_load_lanesoiv2df },
  { 0x1d6c13, CODE_FOR_vec_load_lanesciv2df },
  { 0x1d6c14, CODE_FOR_vec_load_lanesxiv2df },
  { 0x1d6d71, CODE_FOR_vec_load_lanesvnx4dfvnx2df },
  { 0x1d6d75, CODE_FOR_vec_load_lanesvnx6dfvnx2df },
  { 0x1d6d79, CODE_FOR_vec_load_lanesvnx8dfvnx2df },
  { 0x1e4312, CODE_FOR_vec_store_lanesoiv16qi },
  { 0x1e4313, CODE_FOR_vec_store_lanesciv16qi },
  { 0x1e4314, CODE_FOR_vec_store_lanesxiv16qi },
  { 0x1e444b, CODE_FOR_vec_store_lanesvnx32qivnx16qi },
  { 0x1e4450, CODE_FOR_vec_store_lanesvnx48qivnx16qi },
  { 0x1e4455, CODE_FOR_vec_store_lanesvnx64qivnx16qi },
  { 0x1e4512, CODE_FOR_vec_store_lanesoiv8hi },
  { 0x1e4513, CODE_FOR_vec_store_lanesciv8hi },
  { 0x1e4514, CODE_FOR_vec_store_lanesxiv8hi },
  { 0x1e464c, CODE_FOR_vec_store_lanesvnx16hivnx8hi },
  { 0x1e4651, CODE_FOR_vec_store_lanesvnx24hivnx8hi },
  { 0x1e4656, CODE_FOR_vec_store_lanesvnx32hivnx8hi },
  { 0x1e4712, CODE_FOR_vec_store_lanesoiv4si },
  { 0x1e4713, CODE_FOR_vec_store_lanesciv4si },
  { 0x1e4714, CODE_FOR_vec_store_lanesxiv4si },
  { 0x1e484d, CODE_FOR_vec_store_lanesvnx8sivnx4si },
  { 0x1e4852, CODE_FOR_vec_store_lanesvnx12sivnx4si },
  { 0x1e4857, CODE_FOR_vec_store_lanesvnx16sivnx4si },
  { 0x1e4912, CODE_FOR_vec_store_lanesoiv2di },
  { 0x1e4913, CODE_FOR_vec_store_lanesciv2di },
  { 0x1e4914, CODE_FOR_vec_store_lanesxiv2di },
  { 0x1e4a4e, CODE_FOR_vec_store_lanesvnx4divnx2di },
  { 0x1e4a53, CODE_FOR_vec_store_lanesvnx6divnx2di },
  { 0x1e4a58, CODE_FOR_vec_store_lanesvnx8divnx2di },
  { 0x1e6612, CODE_FOR_vec_store_lanesoiv8bf },
  { 0x1e6613, CODE_FOR_vec_store_lanesciv8bf },
  { 0x1e6614, CODE_FOR_vec_store_lanesxiv8bf },
  { 0x1e6712, CODE_FOR_vec_store_lanesoiv8hf },
  { 0x1e6713, CODE_FOR_vec_store_lanesciv8hf },
  { 0x1e6714, CODE_FOR_vec_store_lanesxiv8hf },
  { 0x1e686e, CODE_FOR_vec_store_lanesvnx16bfvnx8bf },
  { 0x1e6872, CODE_FOR_vec_store_lanesvnx24bfvnx8bf },
  { 0x1e6876, CODE_FOR_vec_store_lanesvnx32bfvnx8bf },
  { 0x1e696f, CODE_FOR_vec_store_lanesvnx16hfvnx8hf },
  { 0x1e6973, CODE_FOR_vec_store_lanesvnx24hfvnx8hf },
  { 0x1e6977, CODE_FOR_vec_store_lanesvnx32hfvnx8hf },
  { 0x1e6a12, CODE_FOR_vec_store_lanesoiv4sf },
  { 0x1e6a13, CODE_FOR_vec_store_lanesciv4sf },
  { 0x1e6a14, CODE_FOR_vec_store_lanesxiv4sf },
  { 0x1e6b70, CODE_FOR_vec_store_lanesvnx8sfvnx4sf },
  { 0x1e6b74, CODE_FOR_vec_store_lanesvnx12sfvnx4sf },
  { 0x1e6b78, CODE_FOR_vec_store_lanesvnx16sfvnx4sf },
  { 0x1e6c12, CODE_FOR_vec_store_lanesoiv2df },
  { 0x1e6c13, CODE_FOR_vec_store_lanesciv2df },
  { 0x1e6c14, CODE_FOR_vec_store_lanesxiv2df },
  { 0x1e6d71, CODE_FOR_vec_store_lanesvnx4dfvnx2df },
  { 0x1e6d75, CODE_FOR_vec_store_lanesvnx6dfvnx2df },
  { 0x1e6d79, CODE_FOR_vec_store_lanesvnx8dfvnx2df },
  { 0x1f444b, CODE_FOR_vec_mask_load_lanesvnx32qivnx16qi },
  { 0x1f4450, CODE_FOR_vec_mask_load_lanesvnx48qivnx16qi },
  { 0x1f4455, CODE_FOR_vec_mask_load_lanesvnx64qivnx16qi },
  { 0x1f464c, CODE_FOR_vec_mask_load_lanesvnx16hivnx8hi },
  { 0x1f4651, CODE_FOR_vec_mask_load_lanesvnx24hivnx8hi },
  { 0x1f4656, CODE_FOR_vec_mask_load_lanesvnx32hivnx8hi },
  { 0x1f484d, CODE_FOR_vec_mask_load_lanesvnx8sivnx4si },
  { 0x1f4852, CODE_FOR_vec_mask_load_lanesvnx12sivnx4si },
  { 0x1f4857, CODE_FOR_vec_mask_load_lanesvnx16sivnx4si },
  { 0x1f4a4e, CODE_FOR_vec_mask_load_lanesvnx4divnx2di },
  { 0x1f4a53, CODE_FOR_vec_mask_load_lanesvnx6divnx2di },
  { 0x1f4a58, CODE_FOR_vec_mask_load_lanesvnx8divnx2di },
  { 0x1f686e, CODE_FOR_vec_mask_load_lanesvnx16bfvnx8bf },
  { 0x1f6872, CODE_FOR_vec_mask_load_lanesvnx24bfvnx8bf },
  { 0x1f6876, CODE_FOR_vec_mask_load_lanesvnx32bfvnx8bf },
  { 0x1f696f, CODE_FOR_vec_mask_load_lanesvnx16hfvnx8hf },
  { 0x1f6973, CODE_FOR_vec_mask_load_lanesvnx24hfvnx8hf },
  { 0x1f6977, CODE_FOR_vec_mask_load_lanesvnx32hfvnx8hf },
  { 0x1f6b70, CODE_FOR_vec_mask_load_lanesvnx8sfvnx4sf },
  { 0x1f6b74, CODE_FOR_vec_mask_load_lanesvnx12sfvnx4sf },
  { 0x1f6b78, CODE_FOR_vec_mask_load_lanesvnx16sfvnx4sf },
  { 0x1f6d71, CODE_FOR_vec_mask_load_lanesvnx4dfvnx2df },
  { 0x1f6d75, CODE_FOR_vec_mask_load_lanesvnx6dfvnx2df },
  { 0x1f6d79, CODE_FOR_vec_mask_load_lanesvnx8dfvnx2df },
  { 0x20444b, CODE_FOR_vec_mask_store_lanesvnx32qivnx16qi },
  { 0x204450, CODE_FOR_vec_mask_store_lanesvnx48qivnx16qi },
  { 0x204455, CODE_FOR_vec_mask_store_lanesvnx64qivnx16qi },
  { 0x20464c, CODE_FOR_vec_mask_store_lanesvnx16hivnx8hi },
  { 0x204651, CODE_FOR_vec_mask_store_lanesvnx24hivnx8hi },
  { 0x204656, CODE_FOR_vec_mask_store_lanesvnx32hivnx8hi },
  { 0x20484d, CODE_FOR_vec_mask_store_lanesvnx8sivnx4si },
  { 0x204852, CODE_FOR_vec_mask_store_lanesvnx12sivnx4si },
  { 0x204857, CODE_FOR_vec_mask_store_lanesvnx16sivnx4si },
  { 0x204a4e, CODE_FOR_vec_mask_store_lanesvnx4divnx2di },
  { 0x204a53, CODE_FOR_vec_mask_store_lanesvnx6divnx2di },
  { 0x204a58, CODE_FOR_vec_mask_store_lanesvnx8divnx2di },
  { 0x20686e, CODE_FOR_vec_mask_store_lanesvnx16bfvnx8bf },
  { 0x206872, CODE_FOR_vec_mask_store_lanesvnx24bfvnx8bf },
  { 0x206876, CODE_FOR_vec_mask_store_lanesvnx32bfvnx8bf },
  { 0x20696f, CODE_FOR_vec_mask_store_lanesvnx16hfvnx8hf },
  { 0x206973, CODE_FOR_vec_mask_store_lanesvnx24hfvnx8hf },
  { 0x206977, CODE_FOR_vec_mask_store_lanesvnx32hfvnx8hf },
  { 0x206b70, CODE_FOR_vec_mask_store_lanesvnx8sfvnx4sf },
  { 0x206b74, CODE_FOR_vec_mask_store_lanesvnx12sfvnx4sf },
  { 0x206b78, CODE_FOR_vec_mask_store_lanesvnx16sfvnx4sf },
  { 0x206d71, CODE_FOR_vec_mask_store_lanesvnx4dfvnx2df },
  { 0x206d75, CODE_FOR_vec_mask_store_lanesvnx6dfvnx2df },
  { 0x206d79, CODE_FOR_vec_mask_store_lanesvnx8dfvnx2df },
  { 0x211010, CODE_FOR_vconddidi },
  { 0x214040, CODE_FOR_vcondv8qiv8qi },
  { 0x214141, CODE_FOR_vcondv4hiv4hi },
  { 0x214242, CODE_FOR_vcondv2siv2si },
  { 0x214264, CODE_FOR_vcondv2sfv2si },
  { 0x214343, CODE_FOR_vcondv16qiv16qi },
  { 0x214444, CODE_FOR_vcondvnx16qivnx16qi },
  { 0x214446, CODE_FOR_vcondvnx8hivnx16qi },
  { 0x214448, CODE_FOR_vcondvnx4sivnx16qi },
  { 0x21444a, CODE_FOR_vcondvnx2divnx16qi },
  { 0x21445b, CODE_FOR_vcondvnx2qivnx16qi },
  { 0x21445c, CODE_FOR_vcondvnx4qivnx16qi },
  { 0x21445d, CODE_FOR_vcondvnx2hivnx16qi },
  { 0x21445e, CODE_FOR_vcondvnx8qivnx16qi },
  { 0x21445f, CODE_FOR_vcondvnx4hivnx16qi },
  { 0x214460, CODE_FOR_vcondvnx2sivnx16qi },
  { 0x214468, CODE_FOR_vcondvnx8bfvnx16qi },
  { 0x214469, CODE_FOR_vcondvnx8hfvnx16qi },
  { 0x21446b, CODE_FOR_vcondvnx4sfvnx16qi },
  { 0x21446d, CODE_FOR_vcondvnx2dfvnx16qi },
  { 0x21447a, CODE_FOR_vcondvnx2bfvnx16qi },
  { 0x21447b, CODE_FOR_vcondvnx2hfvnx16qi },
  { 0x21447c, CODE_FOR_vcondvnx4bfvnx16qi },
  { 0x21447d, CODE_FOR_vcondvnx4hfvnx16qi },
  { 0x21447e, CODE_FOR_vcondvnx2sfvnx16qi },
  { 0x214545, CODE_FOR_vcondv8hiv8hi },
  { 0x214644, CODE_FOR_vcondvnx16qivnx8hi },
  { 0x214646, CODE_FOR_vcondvnx8hivnx8hi },
  { 0x214648, CODE_FOR_vcondvnx4sivnx8hi },
  { 0x21464a, CODE_FOR_vcondvnx2divnx8hi },
  { 0x21465b, CODE_FOR_vcondvnx2qivnx8hi },
  { 0x21465c, CODE_FOR_vcondvnx4qivnx8hi },
  { 0x21465d, CODE_FOR_vcondvnx2hivnx8hi },
  { 0x21465e, CODE_FOR_vcondvnx8qivnx8hi },
  { 0x21465f, CODE_FOR_vcondvnx4hivnx8hi },
  { 0x214660, CODE_FOR_vcondvnx2sivnx8hi },
  { 0x214668, CODE_FOR_vcondvnx8bfvnx8hi },
  { 0x214669, CODE_FOR_vcondvnx8hfvnx8hi },
  { 0x21466b, CODE_FOR_vcondvnx4sfvnx8hi },
  { 0x21466d, CODE_FOR_vcondvnx2dfvnx8hi },
  { 0x21467a, CODE_FOR_vcondvnx2bfvnx8hi },
  { 0x21467b, CODE_FOR_vcondvnx2hfvnx8hi },
  { 0x21467c, CODE_FOR_vcondvnx4bfvnx8hi },
  { 0x21467d, CODE_FOR_vcondvnx4hfvnx8hi },
  { 0x21467e, CODE_FOR_vcondvnx2sfvnx8hi },
  { 0x214747, CODE_FOR_vcondv4siv4si },
  { 0x21476a, CODE_FOR_vcondv4sfv4si },
  { 0x214844, CODE_FOR_vcondvnx16qivnx4si },
  { 0x214846, CODE_FOR_vcondvnx8hivnx4si },
  { 0x214848, CODE_FOR_vcondvnx4sivnx4si },
  { 0x21484a, CODE_FOR_vcondvnx2divnx4si },
  { 0x21485b, CODE_FOR_vcondvnx2qivnx4si },
  { 0x21485c, CODE_FOR_vcondvnx4qivnx4si },
  { 0x21485d, CODE_FOR_vcondvnx2hivnx4si },
  { 0x21485e, CODE_FOR_vcondvnx8qivnx4si },
  { 0x21485f, CODE_FOR_vcondvnx4hivnx4si },
  { 0x214860, CODE_FOR_vcondvnx2sivnx4si },
  { 0x214868, CODE_FOR_vcondvnx8bfvnx4si },
  { 0x214869, CODE_FOR_vcondvnx8hfvnx4si },
  { 0x21486b, CODE_FOR_vcondvnx4sfvnx4si },
  { 0x21486d, CODE_FOR_vcondvnx2dfvnx4si },
  { 0x21487a, CODE_FOR_vcondvnx2bfvnx4si },
  { 0x21487b, CODE_FOR_vcondvnx2hfvnx4si },
  { 0x21487c, CODE_FOR_vcondvnx4bfvnx4si },
  { 0x21487d, CODE_FOR_vcondvnx4hfvnx4si },
  { 0x21487e, CODE_FOR_vcondvnx2sfvnx4si },
  { 0x214949, CODE_FOR_vcondv2div2di },
  { 0x21496c, CODE_FOR_vcondv2dfv2di },
  { 0x214a44, CODE_FOR_vcondvnx16qivnx2di },
  { 0x214a46, CODE_FOR_vcondvnx8hivnx2di },
  { 0x214a48, CODE_FOR_vcondvnx4sivnx2di },
  { 0x214a4a, CODE_FOR_vcondvnx2divnx2di },
  { 0x214a5b, CODE_FOR_vcondvnx2qivnx2di },
  { 0x214a5c, CODE_FOR_vcondvnx4qivnx2di },
  { 0x214a5d, CODE_FOR_vcondvnx2hivnx2di },
  { 0x214a5e, CODE_FOR_vcondvnx8qivnx2di },
  { 0x214a5f, CODE_FOR_vcondvnx4hivnx2di },
  { 0x214a60, CODE_FOR_vcondvnx2sivnx2di },
  { 0x214a68, CODE_FOR_vcondvnx8bfvnx2di },
  { 0x214a69, CODE_FOR_vcondvnx8hfvnx2di },
  { 0x214a6b, CODE_FOR_vcondvnx4sfvnx2di },
  { 0x214a6d, CODE_FOR_vcondvnx2dfvnx2di },
  { 0x214a7a, CODE_FOR_vcondvnx2bfvnx2di },
  { 0x214a7b, CODE_FOR_vcondvnx2hfvnx2di },
  { 0x214a7c, CODE_FOR_vcondvnx4bfvnx2di },
  { 0x214a7d, CODE_FOR_vcondvnx4hfvnx2di },
  { 0x214a7e, CODE_FOR_vcondvnx2sfvnx2di },
  { 0x215b44, CODE_FOR_vcondvnx16qivnx2qi },
  { 0x215b46, CODE_FOR_vcondvnx8hivnx2qi },
  { 0x215b48, CODE_FOR_vcondvnx4sivnx2qi },
  { 0x215b4a, CODE_FOR_vcondvnx2divnx2qi },
  { 0x215b5b, CODE_FOR_vcondvnx2qivnx2qi },
  { 0x215b5c, CODE_FOR_vcondvnx4qivnx2qi },
  { 0x215b5d, CODE_FOR_vcondvnx2hivnx2qi },
  { 0x215b5e, CODE_FOR_vcondvnx8qivnx2qi },
  { 0x215b5f, CODE_FOR_vcondvnx4hivnx2qi },
  { 0x215b60, CODE_FOR_vcondvnx2sivnx2qi },
  { 0x215b68, CODE_FOR_vcondvnx8bfvnx2qi },
  { 0x215b69, CODE_FOR_vcondvnx8hfvnx2qi },
  { 0x215b6b, CODE_FOR_vcondvnx4sfvnx2qi },
  { 0x215b6d, CODE_FOR_vcondvnx2dfvnx2qi },
  { 0x215b7a, CODE_FOR_vcondvnx2bfvnx2qi },
  { 0x215b7b, CODE_FOR_vcondvnx2hfvnx2qi },
  { 0x215b7c, CODE_FOR_vcondvnx4bfvnx2qi },
  { 0x215b7d, CODE_FOR_vcondvnx4hfvnx2qi },
  { 0x215b7e, CODE_FOR_vcondvnx2sfvnx2qi },
  { 0x215c44, CODE_FOR_vcondvnx16qivnx4qi },
  { 0x215c46, CODE_FOR_vcondvnx8hivnx4qi },
  { 0x215c48, CODE_FOR_vcondvnx4sivnx4qi },
  { 0x215c4a, CODE_FOR_vcondvnx2divnx4qi },
  { 0x215c5b, CODE_FOR_vcondvnx2qivnx4qi },
  { 0x215c5c, CODE_FOR_vcondvnx4qivnx4qi },
  { 0x215c5d, CODE_FOR_vcondvnx2hivnx4qi },
  { 0x215c5e, CODE_FOR_vcondvnx8qivnx4qi },
  { 0x215c5f, CODE_FOR_vcondvnx4hivnx4qi },
  { 0x215c60, CODE_FOR_vcondvnx2sivnx4qi },
  { 0x215c68, CODE_FOR_vcondvnx8bfvnx4qi },
  { 0x215c69, CODE_FOR_vcondvnx8hfvnx4qi },
  { 0x215c6b, CODE_FOR_vcondvnx4sfvnx4qi },
  { 0x215c6d, CODE_FOR_vcondvnx2dfvnx4qi },
  { 0x215c7a, CODE_FOR_vcondvnx2bfvnx4qi },
  { 0x215c7b, CODE_FOR_vcondvnx2hfvnx4qi },
  { 0x215c7c, CODE_FOR_vcondvnx4bfvnx4qi },
  { 0x215c7d, CODE_FOR_vcondvnx4hfvnx4qi },
  { 0x215c7e, CODE_FOR_vcondvnx2sfvnx4qi },
  { 0x215d44, CODE_FOR_vcondvnx16qivnx2hi },
  { 0x215d46, CODE_FOR_vcondvnx8hivnx2hi },
  { 0x215d48, CODE_FOR_vcondvnx4sivnx2hi },
  { 0x215d4a, CODE_FOR_vcondvnx2divnx2hi },
  { 0x215d5b, CODE_FOR_vcondvnx2qivnx2hi },
  { 0x215d5c, CODE_FOR_vcondvnx4qivnx2hi },
  { 0x215d5d, CODE_FOR_vcondvnx2hivnx2hi },
  { 0x215d5e, CODE_FOR_vcondvnx8qivnx2hi },
  { 0x215d5f, CODE_FOR_vcondvnx4hivnx2hi },
  { 0x215d60, CODE_FOR_vcondvnx2sivnx2hi },
  { 0x215d68, CODE_FOR_vcondvnx8bfvnx2hi },
  { 0x215d69, CODE_FOR_vcondvnx8hfvnx2hi },
  { 0x215d6b, CODE_FOR_vcondvnx4sfvnx2hi },
  { 0x215d6d, CODE_FOR_vcondvnx2dfvnx2hi },
  { 0x215d7a, CODE_FOR_vcondvnx2bfvnx2hi },
  { 0x215d7b, CODE_FOR_vcondvnx2hfvnx2hi },
  { 0x215d7c, CODE_FOR_vcondvnx4bfvnx2hi },
  { 0x215d7d, CODE_FOR_vcondvnx4hfvnx2hi },
  { 0x215d7e, CODE_FOR_vcondvnx2sfvnx2hi },
  { 0x215e44, CODE_FOR_vcondvnx16qivnx8qi },
  { 0x215e46, CODE_FOR_vcondvnx8hivnx8qi },
  { 0x215e48, CODE_FOR_vcondvnx4sivnx8qi },
  { 0x215e4a, CODE_FOR_vcondvnx2divnx8qi },
  { 0x215e5b, CODE_FOR_vcondvnx2qivnx8qi },
  { 0x215e5c, CODE_FOR_vcondvnx4qivnx8qi },
  { 0x215e5d, CODE_FOR_vcondvnx2hivnx8qi },
  { 0x215e5e, CODE_FOR_vcondvnx8qivnx8qi },
  { 0x215e5f, CODE_FOR_vcondvnx4hivnx8qi },
  { 0x215e60, CODE_FOR_vcondvnx2sivnx8qi },
  { 0x215e68, CODE_FOR_vcondvnx8bfvnx8qi },
  { 0x215e69, CODE_FOR_vcondvnx8hfvnx8qi },
  { 0x215e6b, CODE_FOR_vcondvnx4sfvnx8qi },
  { 0x215e6d, CODE_FOR_vcondvnx2dfvnx8qi },
  { 0x215e7a, CODE_FOR_vcondvnx2bfvnx8qi },
  { 0x215e7b, CODE_FOR_vcondvnx2hfvnx8qi },
  { 0x215e7c, CODE_FOR_vcondvnx4bfvnx8qi },
  { 0x215e7d, CODE_FOR_vcondvnx4hfvnx8qi },
  { 0x215e7e, CODE_FOR_vcondvnx2sfvnx8qi },
  { 0x215f44, CODE_FOR_vcondvnx16qivnx4hi },
  { 0x215f46, CODE_FOR_vcondvnx8hivnx4hi },
  { 0x215f48, CODE_FOR_vcondvnx4sivnx4hi },
  { 0x215f4a, CODE_FOR_vcondvnx2divnx4hi },
  { 0x215f5b, CODE_FOR_vcondvnx2qivnx4hi },
  { 0x215f5c, CODE_FOR_vcondvnx4qivnx4hi },
  { 0x215f5d, CODE_FOR_vcondvnx2hivnx4hi },
  { 0x215f5e, CODE_FOR_vcondvnx8qivnx4hi },
  { 0x215f5f, CODE_FOR_vcondvnx4hivnx4hi },
  { 0x215f60, CODE_FOR_vcondvnx2sivnx4hi },
  { 0x215f68, CODE_FOR_vcondvnx8bfvnx4hi },
  { 0x215f69, CODE_FOR_vcondvnx8hfvnx4hi },
  { 0x215f6b, CODE_FOR_vcondvnx4sfvnx4hi },
  { 0x215f6d, CODE_FOR_vcondvnx2dfvnx4hi },
  { 0x215f7a, CODE_FOR_vcondvnx2bfvnx4hi },
  { 0x215f7b, CODE_FOR_vcondvnx2hfvnx4hi },
  { 0x215f7c, CODE_FOR_vcondvnx4bfvnx4hi },
  { 0x215f7d, CODE_FOR_vcondvnx4hfvnx4hi },
  { 0x215f7e, CODE_FOR_vcondvnx2sfvnx4hi },
  { 0x216044, CODE_FOR_vcondvnx16qivnx2si },
  { 0x216046, CODE_FOR_vcondvnx8hivnx2si },
  { 0x216048, CODE_FOR_vcondvnx4sivnx2si },
  { 0x21604a, CODE_FOR_vcondvnx2divnx2si },
  { 0x21605b, CODE_FOR_vcondvnx2qivnx2si },
  { 0x21605c, CODE_FOR_vcondvnx4qivnx2si },
  { 0x21605d, CODE_FOR_vcondvnx2hivnx2si },
  { 0x21605e, CODE_FOR_vcondvnx8qivnx2si },
  { 0x21605f, CODE_FOR_vcondvnx4hivnx2si },
  { 0x216060, CODE_FOR_vcondvnx2sivnx2si },
  { 0x216068, CODE_FOR_vcondvnx8bfvnx2si },
  { 0x216069, CODE_FOR_vcondvnx8hfvnx2si },
  { 0x21606b, CODE_FOR_vcondvnx4sfvnx2si },
  { 0x21606d, CODE_FOR_vcondvnx2dfvnx2si },
  { 0x21607a, CODE_FOR_vcondvnx2bfvnx2si },
  { 0x21607b, CODE_FOR_vcondvnx2hfvnx2si },
  { 0x21607c, CODE_FOR_vcondvnx4bfvnx2si },
  { 0x21607d, CODE_FOR_vcondvnx4hfvnx2si },
  { 0x21607e, CODE_FOR_vcondvnx2sfvnx2si },
  { 0x216442, CODE_FOR_vcondv2siv2sf },
  { 0x216464, CODE_FOR_vcondv2sfv2sf },
  { 0x216946, CODE_FOR_vcondvnx8hivnx8hf },
  { 0x216968, CODE_FOR_vcondvnx8bfvnx8hf },
  { 0x216969, CODE_FOR_vcondvnx8hfvnx8hf },
  { 0x216a47, CODE_FOR_vcondv4siv4sf },
  { 0x216a6a, CODE_FOR_vcondv4sfv4sf },
  { 0x216b48, CODE_FOR_vcondvnx4sivnx4sf },
  { 0x216b6b, CODE_FOR_vcondvnx4sfvnx4sf },
  { 0x216c49, CODE_FOR_vcondv2div2df },
  { 0x216c6c, CODE_FOR_vcondv2dfv2df },
  { 0x216d4a, CODE_FOR_vcondvnx2divnx2df },
  { 0x216d6d, CODE_FOR_vcondvnx2dfvnx2df },
  { 0x221010, CODE_FOR_vcondudidi },
  { 0x224040, CODE_FOR_vconduv8qiv8qi },
  { 0x224141, CODE_FOR_vconduv4hiv4hi },
  { 0x224242, CODE_FOR_vconduv2siv2si },
  { 0x224264, CODE_FOR_vconduv2sfv2si },
  { 0x224343, CODE_FOR_vconduv16qiv16qi },
  { 0x224444, CODE_FOR_vconduvnx16qivnx16qi },
  { 0x224446, CODE_FOR_vconduvnx8hivnx16qi },
  { 0x224448, CODE_FOR_vconduvnx4sivnx16qi },
  { 0x22444a, CODE_FOR_vconduvnx2divnx16qi },
  { 0x22445b, CODE_FOR_vconduvnx2qivnx16qi },
  { 0x22445c, CODE_FOR_vconduvnx4qivnx16qi },
  { 0x22445d, CODE_FOR_vconduvnx2hivnx16qi },
  { 0x22445e, CODE_FOR_vconduvnx8qivnx16qi },
  { 0x22445f, CODE_FOR_vconduvnx4hivnx16qi },
  { 0x224460, CODE_FOR_vconduvnx2sivnx16qi },
  { 0x224468, CODE_FOR_vconduvnx8bfvnx16qi },
  { 0x224469, CODE_FOR_vconduvnx8hfvnx16qi },
  { 0x22446b, CODE_FOR_vconduvnx4sfvnx16qi },
  { 0x22446d, CODE_FOR_vconduvnx2dfvnx16qi },
  { 0x22447a, CODE_FOR_vconduvnx2bfvnx16qi },
  { 0x22447b, CODE_FOR_vconduvnx2hfvnx16qi },
  { 0x22447c, CODE_FOR_vconduvnx4bfvnx16qi },
  { 0x22447d, CODE_FOR_vconduvnx4hfvnx16qi },
  { 0x22447e, CODE_FOR_vconduvnx2sfvnx16qi },
  { 0x224545, CODE_FOR_vconduv8hiv8hi },
  { 0x224644, CODE_FOR_vconduvnx16qivnx8hi },
  { 0x224646, CODE_FOR_vconduvnx8hivnx8hi },
  { 0x224648, CODE_FOR_vconduvnx4sivnx8hi },
  { 0x22464a, CODE_FOR_vconduvnx2divnx8hi },
  { 0x22465b, CODE_FOR_vconduvnx2qivnx8hi },
  { 0x22465c, CODE_FOR_vconduvnx4qivnx8hi },
  { 0x22465d, CODE_FOR_vconduvnx2hivnx8hi },
  { 0x22465e, CODE_FOR_vconduvnx8qivnx8hi },
  { 0x22465f, CODE_FOR_vconduvnx4hivnx8hi },
  { 0x224660, CODE_FOR_vconduvnx2sivnx8hi },
  { 0x224668, CODE_FOR_vconduvnx8bfvnx8hi },
  { 0x224669, CODE_FOR_vconduvnx8hfvnx8hi },
  { 0x22466b, CODE_FOR_vconduvnx4sfvnx8hi },
  { 0x22466d, CODE_FOR_vconduvnx2dfvnx8hi },
  { 0x22467a, CODE_FOR_vconduvnx2bfvnx8hi },
  { 0x22467b, CODE_FOR_vconduvnx2hfvnx8hi },
  { 0x22467c, CODE_FOR_vconduvnx4bfvnx8hi },
  { 0x22467d, CODE_FOR_vconduvnx4hfvnx8hi },
  { 0x22467e, CODE_FOR_vconduvnx2sfvnx8hi },
  { 0x224747, CODE_FOR_vconduv4siv4si },
  { 0x22476a, CODE_FOR_vconduv4sfv4si },
  { 0x224844, CODE_FOR_vconduvnx16qivnx4si },
  { 0x224846, CODE_FOR_vconduvnx8hivnx4si },
  { 0x224848, CODE_FOR_vconduvnx4sivnx4si },
  { 0x22484a, CODE_FOR_vconduvnx2divnx4si },
  { 0x22485b, CODE_FOR_vconduvnx2qivnx4si },
  { 0x22485c, CODE_FOR_vconduvnx4qivnx4si },
  { 0x22485d, CODE_FOR_vconduvnx2hivnx4si },
  { 0x22485e, CODE_FOR_vconduvnx8qivnx4si },
  { 0x22485f, CODE_FOR_vconduvnx4hivnx4si },
  { 0x224860, CODE_FOR_vconduvnx2sivnx4si },
  { 0x224868, CODE_FOR_vconduvnx8bfvnx4si },
  { 0x224869, CODE_FOR_vconduvnx8hfvnx4si },
  { 0x22486b, CODE_FOR_vconduvnx4sfvnx4si },
  { 0x22486d, CODE_FOR_vconduvnx2dfvnx4si },
  { 0x22487a, CODE_FOR_vconduvnx2bfvnx4si },
  { 0x22487b, CODE_FOR_vconduvnx2hfvnx4si },
  { 0x22487c, CODE_FOR_vconduvnx4bfvnx4si },
  { 0x22487d, CODE_FOR_vconduvnx4hfvnx4si },
  { 0x22487e, CODE_FOR_vconduvnx2sfvnx4si },
  { 0x224949, CODE_FOR_vconduv2div2di },
  { 0x22496c, CODE_FOR_vconduv2dfv2di },
  { 0x224a44, CODE_FOR_vconduvnx16qivnx2di },
  { 0x224a46, CODE_FOR_vconduvnx8hivnx2di },
  { 0x224a48, CODE_FOR_vconduvnx4sivnx2di },
  { 0x224a4a, CODE_FOR_vconduvnx2divnx2di },
  { 0x224a5b, CODE_FOR_vconduvnx2qivnx2di },
  { 0x224a5c, CODE_FOR_vconduvnx4qivnx2di },
  { 0x224a5d, CODE_FOR_vconduvnx2hivnx2di },
  { 0x224a5e, CODE_FOR_vconduvnx8qivnx2di },
  { 0x224a5f, CODE_FOR_vconduvnx4hivnx2di },
  { 0x224a60, CODE_FOR_vconduvnx2sivnx2di },
  { 0x224a68, CODE_FOR_vconduvnx8bfvnx2di },
  { 0x224a69, CODE_FOR_vconduvnx8hfvnx2di },
  { 0x224a6b, CODE_FOR_vconduvnx4sfvnx2di },
  { 0x224a6d, CODE_FOR_vconduvnx2dfvnx2di },
  { 0x224a7a, CODE_FOR_vconduvnx2bfvnx2di },
  { 0x224a7b, CODE_FOR_vconduvnx2hfvnx2di },
  { 0x224a7c, CODE_FOR_vconduvnx4bfvnx2di },
  { 0x224a7d, CODE_FOR_vconduvnx4hfvnx2di },
  { 0x224a7e, CODE_FOR_vconduvnx2sfvnx2di },
  { 0x225b44, CODE_FOR_vconduvnx16qivnx2qi },
  { 0x225b46, CODE_FOR_vconduvnx8hivnx2qi },
  { 0x225b48, CODE_FOR_vconduvnx4sivnx2qi },
  { 0x225b4a, CODE_FOR_vconduvnx2divnx2qi },
  { 0x225b5b, CODE_FOR_vconduvnx2qivnx2qi },
  { 0x225b5c, CODE_FOR_vconduvnx4qivnx2qi },
  { 0x225b5d, CODE_FOR_vconduvnx2hivnx2qi },
  { 0x225b5e, CODE_FOR_vconduvnx8qivnx2qi },
  { 0x225b5f, CODE_FOR_vconduvnx4hivnx2qi },
  { 0x225b60, CODE_FOR_vconduvnx2sivnx2qi },
  { 0x225b68, CODE_FOR_vconduvnx8bfvnx2qi },
  { 0x225b69, CODE_FOR_vconduvnx8hfvnx2qi },
  { 0x225b6b, CODE_FOR_vconduvnx4sfvnx2qi },
  { 0x225b6d, CODE_FOR_vconduvnx2dfvnx2qi },
  { 0x225b7a, CODE_FOR_vconduvnx2bfvnx2qi },
  { 0x225b7b, CODE_FOR_vconduvnx2hfvnx2qi },
  { 0x225b7c, CODE_FOR_vconduvnx4bfvnx2qi },
  { 0x225b7d, CODE_FOR_vconduvnx4hfvnx2qi },
  { 0x225b7e, CODE_FOR_vconduvnx2sfvnx2qi },
  { 0x225c44, CODE_FOR_vconduvnx16qivnx4qi },
  { 0x225c46, CODE_FOR_vconduvnx8hivnx4qi },
  { 0x225c48, CODE_FOR_vconduvnx4sivnx4qi },
  { 0x225c4a, CODE_FOR_vconduvnx2divnx4qi },
  { 0x225c5b, CODE_FOR_vconduvnx2qivnx4qi },
  { 0x225c5c, CODE_FOR_vconduvnx4qivnx4qi },
  { 0x225c5d, CODE_FOR_vconduvnx2hivnx4qi },
  { 0x225c5e, CODE_FOR_vconduvnx8qivnx4qi },
  { 0x225c5f, CODE_FOR_vconduvnx4hivnx4qi },
  { 0x225c60, CODE_FOR_vconduvnx2sivnx4qi },
  { 0x225c68, CODE_FOR_vconduvnx8bfvnx4qi },
  { 0x225c69, CODE_FOR_vconduvnx8hfvnx4qi },
  { 0x225c6b, CODE_FOR_vconduvnx4sfvnx4qi },
  { 0x225c6d, CODE_FOR_vconduvnx2dfvnx4qi },
  { 0x225c7a, CODE_FOR_vconduvnx2bfvnx4qi },
  { 0x225c7b, CODE_FOR_vconduvnx2hfvnx4qi },
  { 0x225c7c, CODE_FOR_vconduvnx4bfvnx4qi },
  { 0x225c7d, CODE_FOR_vconduvnx4hfvnx4qi },
  { 0x225c7e, CODE_FOR_vconduvnx2sfvnx4qi },
  { 0x225d44, CODE_FOR_vconduvnx16qivnx2hi },
  { 0x225d46, CODE_FOR_vconduvnx8hivnx2hi },
  { 0x225d48, CODE_FOR_vconduvnx4sivnx2hi },
  { 0x225d4a, CODE_FOR_vconduvnx2divnx2hi },
  { 0x225d5b, CODE_FOR_vconduvnx2qivnx2hi },
  { 0x225d5c, CODE_FOR_vconduvnx4qivnx2hi },
  { 0x225d5d, CODE_FOR_vconduvnx2hivnx2hi },
  { 0x225d5e, CODE_FOR_vconduvnx8qivnx2hi },
  { 0x225d5f, CODE_FOR_vconduvnx4hivnx2hi },
  { 0x225d60, CODE_FOR_vconduvnx2sivnx2hi },
  { 0x225d68, CODE_FOR_vconduvnx8bfvnx2hi },
  { 0x225d69, CODE_FOR_vconduvnx8hfvnx2hi },
  { 0x225d6b, CODE_FOR_vconduvnx4sfvnx2hi },
  { 0x225d6d, CODE_FOR_vconduvnx2dfvnx2hi },
  { 0x225d7a, CODE_FOR_vconduvnx2bfvnx2hi },
  { 0x225d7b, CODE_FOR_vconduvnx2hfvnx2hi },
  { 0x225d7c, CODE_FOR_vconduvnx4bfvnx2hi },
  { 0x225d7d, CODE_FOR_vconduvnx4hfvnx2hi },
  { 0x225d7e, CODE_FOR_vconduvnx2sfvnx2hi },
  { 0x225e44, CODE_FOR_vconduvnx16qivnx8qi },
  { 0x225e46, CODE_FOR_vconduvnx8hivnx8qi },
  { 0x225e48, CODE_FOR_vconduvnx4sivnx8qi },
  { 0x225e4a, CODE_FOR_vconduvnx2divnx8qi },
  { 0x225e5b, CODE_FOR_vconduvnx2qivnx8qi },
  { 0x225e5c, CODE_FOR_vconduvnx4qivnx8qi },
  { 0x225e5d, CODE_FOR_vconduvnx2hivnx8qi },
  { 0x225e5e, CODE_FOR_vconduvnx8qivnx8qi },
  { 0x225e5f, CODE_FOR_vconduvnx4hivnx8qi },
  { 0x225e60, CODE_FOR_vconduvnx2sivnx8qi },
  { 0x225e68, CODE_FOR_vconduvnx8bfvnx8qi },
  { 0x225e69, CODE_FOR_vconduvnx8hfvnx8qi },
  { 0x225e6b, CODE_FOR_vconduvnx4sfvnx8qi },
  { 0x225e6d, CODE_FOR_vconduvnx2dfvnx8qi },
  { 0x225e7a, CODE_FOR_vconduvnx2bfvnx8qi },
  { 0x225e7b, CODE_FOR_vconduvnx2hfvnx8qi },
  { 0x225e7c, CODE_FOR_vconduvnx4bfvnx8qi },
  { 0x225e7d, CODE_FOR_vconduvnx4hfvnx8qi },
  { 0x225e7e, CODE_FOR_vconduvnx2sfvnx8qi },
  { 0x225f44, CODE_FOR_vconduvnx16qivnx4hi },
  { 0x225f46, CODE_FOR_vconduvnx8hivnx4hi },
  { 0x225f48, CODE_FOR_vconduvnx4sivnx4hi },
  { 0x225f4a, CODE_FOR_vconduvnx2divnx4hi },
  { 0x225f5b, CODE_FOR_vconduvnx2qivnx4hi },
  { 0x225f5c, CODE_FOR_vconduvnx4qivnx4hi },
  { 0x225f5d, CODE_FOR_vconduvnx2hivnx4hi },
  { 0x225f5e, CODE_FOR_vconduvnx8qivnx4hi },
  { 0x225f5f, CODE_FOR_vconduvnx4hivnx4hi },
  { 0x225f60, CODE_FOR_vconduvnx2sivnx4hi },
  { 0x225f68, CODE_FOR_vconduvnx8bfvnx4hi },
  { 0x225f69, CODE_FOR_vconduvnx8hfvnx4hi },
  { 0x225f6b, CODE_FOR_vconduvnx4sfvnx4hi },
  { 0x225f6d, CODE_FOR_vconduvnx2dfvnx4hi },
  { 0x225f7a, CODE_FOR_vconduvnx2bfvnx4hi },
  { 0x225f7b, CODE_FOR_vconduvnx2hfvnx4hi },
  { 0x225f7c, CODE_FOR_vconduvnx4bfvnx4hi },
  { 0x225f7d, CODE_FOR_vconduvnx4hfvnx4hi },
  { 0x225f7e, CODE_FOR_vconduvnx2sfvnx4hi },
  { 0x226044, CODE_FOR_vconduvnx16qivnx2si },
  { 0x226046, CODE_FOR_vconduvnx8hivnx2si },
  { 0x226048, CODE_FOR_vconduvnx4sivnx2si },
  { 0x22604a, CODE_FOR_vconduvnx2divnx2si },
  { 0x22605b, CODE_FOR_vconduvnx2qivnx2si },
  { 0x22605c, CODE_FOR_vconduvnx4qivnx2si },
  { 0x22605d, CODE_FOR_vconduvnx2hivnx2si },
  { 0x22605e, CODE_FOR_vconduvnx8qivnx2si },
  { 0x22605f, CODE_FOR_vconduvnx4hivnx2si },
  { 0x226060, CODE_FOR_vconduvnx2sivnx2si },
  { 0x226068, CODE_FOR_vconduvnx8bfvnx2si },
  { 0x226069, CODE_FOR_vconduvnx8hfvnx2si },
  { 0x22606b, CODE_FOR_vconduvnx4sfvnx2si },
  { 0x22606d, CODE_FOR_vconduvnx2dfvnx2si },
  { 0x22607a, CODE_FOR_vconduvnx2bfvnx2si },
  { 0x22607b, CODE_FOR_vconduvnx2hfvnx2si },
  { 0x22607c, CODE_FOR_vconduvnx4bfvnx2si },
  { 0x22607d, CODE_FOR_vconduvnx4hfvnx2si },
  { 0x22607e, CODE_FOR_vconduvnx2sfvnx2si },
  { 0x241010, CODE_FOR_vcond_mask_didi },
  { 0x243c3c, CODE_FOR_vcond_mask_vnx16bivnx16bi },
  { 0x243c44, CODE_FOR_vcond_mask_vnx16qivnx16bi },
  { 0x243d3d, CODE_FOR_vcond_mask_vnx8bivnx8bi },
  { 0x243d46, CODE_FOR_vcond_mask_vnx8hivnx8bi },
  { 0x243d5e, CODE_FOR_vcond_mask_vnx8qivnx8bi },
  { 0x243d68, CODE_FOR_vcond_mask_vnx8bfvnx8bi },
  { 0x243d69, CODE_FOR_vcond_mask_vnx8hfvnx8bi },
  { 0x243e3e, CODE_FOR_vcond_mask_vnx4bivnx4bi },
  { 0x243e48, CODE_FOR_vcond_mask_vnx4sivnx4bi },
  { 0x243e5c, CODE_FOR_vcond_mask_vnx4qivnx4bi },
  { 0x243e5f, CODE_FOR_vcond_mask_vnx4hivnx4bi },
  { 0x243e6b, CODE_FOR_vcond_mask_vnx4sfvnx4bi },
  { 0x243e7c, CODE_FOR_vcond_mask_vnx4bfvnx4bi },
  { 0x243e7d, CODE_FOR_vcond_mask_vnx4hfvnx4bi },
  { 0x243f3f, CODE_FOR_vcond_mask_vnx2bivnx2bi },
  { 0x243f4a, CODE_FOR_vcond_mask_vnx2divnx2bi },
  { 0x243f5b, CODE_FOR_vcond_mask_vnx2qivnx2bi },
  { 0x243f5d, CODE_FOR_vcond_mask_vnx2hivnx2bi },
  { 0x243f60, CODE_FOR_vcond_mask_vnx2sivnx2bi },
  { 0x243f6d, CODE_FOR_vcond_mask_vnx2dfvnx2bi },
  { 0x243f7a, CODE_FOR_vcond_mask_vnx2bfvnx2bi },
  { 0x243f7b, CODE_FOR_vcond_mask_vnx2hfvnx2bi },
  { 0x243f7e, CODE_FOR_vcond_mask_vnx2sfvnx2bi },
  { 0x244040, CODE_FOR_vcond_mask_v8qiv8qi },
  { 0x244141, CODE_FOR_vcond_mask_v4hiv4hi },
  { 0x244242, CODE_FOR_vcond_mask_v2siv2si },
  { 0x244264, CODE_FOR_vcond_mask_v2sfv2si },
  { 0x244343, CODE_FOR_vcond_mask_v16qiv16qi },
  { 0x244545, CODE_FOR_vcond_mask_v8hiv8hi },
  { 0x244747, CODE_FOR_vcond_mask_v4siv4si },
  { 0x24476a, CODE_FOR_vcond_mask_v4sfv4si },
  { 0x244949, CODE_FOR_vcond_mask_v2div2di },
  { 0x24496c, CODE_FOR_vcond_mask_v2dfv2di },
  { 0x251010, CODE_FOR_vec_cmpdidi },
  { 0x253c44, CODE_FOR_vec_cmpvnx16qivnx16bi },
  { 0x253d46, CODE_FOR_vec_cmpvnx8hivnx8bi },
  { 0x253d5e, CODE_FOR_vec_cmpvnx8qivnx8bi },
  { 0x253d69, CODE_FOR_vec_cmpvnx8hfvnx8bi },
  { 0x253e48, CODE_FOR_vec_cmpvnx4sivnx4bi },
  { 0x253e5c, CODE_FOR_vec_cmpvnx4qivnx4bi },
  { 0x253e5f, CODE_FOR_vec_cmpvnx4hivnx4bi },
  { 0x253e6b, CODE_FOR_vec_cmpvnx4sfvnx4bi },
  { 0x253f4a, CODE_FOR_vec_cmpvnx2divnx2bi },
  { 0x253f5b, CODE_FOR_vec_cmpvnx2qivnx2bi },
  { 0x253f5d, CODE_FOR_vec_cmpvnx2hivnx2bi },
  { 0x253f60, CODE_FOR_vec_cmpvnx2sivnx2bi },
  { 0x253f6d, CODE_FOR_vec_cmpvnx2dfvnx2bi },
  { 0x254040, CODE_FOR_vec_cmpv8qiv8qi },
  { 0x254141, CODE_FOR_vec_cmpv4hiv4hi },
  { 0x254242, CODE_FOR_vec_cmpv2siv2si },
  { 0x254264, CODE_FOR_vec_cmpv2sfv2si },
  { 0x254343, CODE_FOR_vec_cmpv16qiv16qi },
  { 0x254545, CODE_FOR_vec_cmpv8hiv8hi },
  { 0x254747, CODE_FOR_vec_cmpv4siv4si },
  { 0x25476a, CODE_FOR_vec_cmpv4sfv4si },
  { 0x254949, CODE_FOR_vec_cmpv2div2di },
  { 0x25496c, CODE_FOR_vec_cmpv2dfv2di },
  { 0x261010, CODE_FOR_vec_cmpudidi },
  { 0x263c44, CODE_FOR_vec_cmpuvnx16qivnx16bi },
  { 0x263d46, CODE_FOR_vec_cmpuvnx8hivnx8bi },
  { 0x263d5e, CODE_FOR_vec_cmpuvnx8qivnx8bi },
  { 0x263e48, CODE_FOR_vec_cmpuvnx4sivnx4bi },
  { 0x263e5c, CODE_FOR_vec_cmpuvnx4qivnx4bi },
  { 0x263e5f, CODE_FOR_vec_cmpuvnx4hivnx4bi },
  { 0x263f4a, CODE_FOR_vec_cmpuvnx2divnx2bi },
  { 0x263f5b, CODE_FOR_vec_cmpuvnx2qivnx2bi },
  { 0x263f5d, CODE_FOR_vec_cmpuvnx2hivnx2bi },
  { 0x263f60, CODE_FOR_vec_cmpuvnx2sivnx2bi },
  { 0x264040, CODE_FOR_vec_cmpuv8qiv8qi },
  { 0x264141, CODE_FOR_vec_cmpuv4hiv4hi },
  { 0x264242, CODE_FOR_vec_cmpuv2siv2si },
  { 0x264343, CODE_FOR_vec_cmpuv16qiv16qi },
  { 0x264545, CODE_FOR_vec_cmpuv8hiv8hi },
  { 0x264747, CODE_FOR_vec_cmpuv4siv4si },
  { 0x264949, CODE_FOR_vec_cmpuv2div2di },
  { 0x283c44, CODE_FOR_maskloadvnx16qivnx16bi },
  { 0x283d46, CODE_FOR_maskloadvnx8hivnx8bi },
  { 0x283d5e, CODE_FOR_maskloadvnx8qivnx8bi },
  { 0x283d68, CODE_FOR_maskloadvnx8bfvnx8bi },
  { 0x283d69, CODE_FOR_maskloadvnx8hfvnx8bi },
  { 0x283e48, CODE_FOR_maskloadvnx4sivnx4bi },
  { 0x283e5c, CODE_FOR_maskloadvnx4qivnx4bi },
  { 0x283e5f, CODE_FOR_maskloadvnx4hivnx4bi },
  { 0x283e6b, CODE_FOR_maskloadvnx4sfvnx4bi },
  { 0x283e7c, CODE_FOR_maskloadvnx4bfvnx4bi },
  { 0x283e7d, CODE_FOR_maskloadvnx4hfvnx4bi },
  { 0x283f4a, CODE_FOR_maskloadvnx2divnx2bi },
  { 0x283f5b, CODE_FOR_maskloadvnx2qivnx2bi },
  { 0x283f5d, CODE_FOR_maskloadvnx2hivnx2bi },
  { 0x283f60, CODE_FOR_maskloadvnx2sivnx2bi },
  { 0x283f6d, CODE_FOR_maskloadvnx2dfvnx2bi },
  { 0x283f7a, CODE_FOR_maskloadvnx2bfvnx2bi },
  { 0x283f7b, CODE_FOR_maskloadvnx2hfvnx2bi },
  { 0x283f7e, CODE_FOR_maskloadvnx2sfvnx2bi },
  { 0x293c44, CODE_FOR_maskstorevnx16qivnx16bi },
  { 0x293d46, CODE_FOR_maskstorevnx8hivnx8bi },
  { 0x293d5e, CODE_FOR_maskstorevnx8qivnx8bi },
  { 0x293d68, CODE_FOR_maskstorevnx8bfvnx8bi },
  { 0x293d69, CODE_FOR_maskstorevnx8hfvnx8bi },
  { 0x293e48, CODE_FOR_maskstorevnx4sivnx4bi },
  { 0x293e5c, CODE_FOR_maskstorevnx4qivnx4bi },
  { 0x293e5f, CODE_FOR_maskstorevnx4hivnx4bi },
  { 0x293e6b, CODE_FOR_maskstorevnx4sfvnx4bi },
  { 0x293e7c, CODE_FOR_maskstorevnx4bfvnx4bi },
  { 0x293e7d, CODE_FOR_maskstorevnx4hfvnx4bi },
  { 0x293f4a, CODE_FOR_maskstorevnx2divnx2bi },
  { 0x293f5b, CODE_FOR_maskstorevnx2qivnx2bi },
  { 0x293f5d, CODE_FOR_maskstorevnx2hivnx2bi },
  { 0x293f60, CODE_FOR_maskstorevnx2sivnx2bi },
  { 0x293f6d, CODE_FOR_maskstorevnx2dfvnx2bi },
  { 0x293f7a, CODE_FOR_maskstorevnx2bfvnx2bi },
  { 0x293f7b, CODE_FOR_maskstorevnx2hfvnx2bi },
  { 0x293f7e, CODE_FOR_maskstorevnx2sfvnx2bi },
  { 0x2a4848, CODE_FOR_gather_loadvnx4sivnx4si },
  { 0x2a485c, CODE_FOR_gather_loadvnx4qivnx4si },
  { 0x2a485f, CODE_FOR_gather_loadvnx4hivnx4si },
  { 0x2a486b, CODE_FOR_gather_loadvnx4sfvnx4si },
  { 0x2a487c, CODE_FOR_gather_loadvnx4bfvnx4si },
  { 0x2a487d, CODE_FOR_gather_loadvnx4hfvnx4si },
  { 0x2a4a4a, CODE_FOR_gather_loadvnx2divnx2di },
  { 0x2a4a5b, CODE_FOR_gather_loadvnx2qivnx2di },
  { 0x2a4a5d, CODE_FOR_gather_loadvnx2hivnx2di },
  { 0x2a4a60, CODE_FOR_gather_loadvnx2sivnx2di },
  { 0x2a4a6d, CODE_FOR_gather_loadvnx2dfvnx2di },
  { 0x2a4a7a, CODE_FOR_gather_loadvnx2bfvnx2di },
  { 0x2a4a7b, CODE_FOR_gather_loadvnx2hfvnx2di },
  { 0x2a4a7e, CODE_FOR_gather_loadvnx2sfvnx2di },
  { 0x2b4848, CODE_FOR_mask_gather_loadvnx4sivnx4si },
  { 0x2b485c, CODE_FOR_mask_gather_loadvnx4qivnx4si },
  { 0x2b485f, CODE_FOR_mask_gather_loadvnx4hivnx4si },
  { 0x2b486b, CODE_FOR_mask_gather_loadvnx4sfvnx4si },
  { 0x2b487c, CODE_FOR_mask_gather_loadvnx4bfvnx4si },
  { 0x2b487d, CODE_FOR_mask_gather_loadvnx4hfvnx4si },
  { 0x2b4a4a, CODE_FOR_mask_gather_loadvnx2divnx2di },
  { 0x2b4a5b, CODE_FOR_mask_gather_loadvnx2qivnx2di },
  { 0x2b4a5d, CODE_FOR_mask_gather_loadvnx2hivnx2di },
  { 0x2b4a60, CODE_FOR_mask_gather_loadvnx2sivnx2di },
  { 0x2b4a6d, CODE_FOR_mask_gather_loadvnx2dfvnx2di },
  { 0x2b4a7a, CODE_FOR_mask_gather_loadvnx2bfvnx2di },
  { 0x2b4a7b, CODE_FOR_mask_gather_loadvnx2hfvnx2di },
  { 0x2b4a7e, CODE_FOR_mask_gather_loadvnx2sfvnx2di },
  { 0x2c4848, CODE_FOR_scatter_storevnx4sivnx4si },
  { 0x2c485c, CODE_FOR_scatter_storevnx4qivnx4si },
  { 0x2c485f, CODE_FOR_scatter_storevnx4hivnx4si },
  { 0x2c486b, CODE_FOR_scatter_storevnx4sfvnx4si },
  { 0x2c487c, CODE_FOR_scatter_storevnx4bfvnx4si },
  { 0x2c487d, CODE_FOR_scatter_storevnx4hfvnx4si },
  { 0x2c4a4a, CODE_FOR_scatter_storevnx2divnx2di },
  { 0x2c4a5b, CODE_FOR_scatter_storevnx2qivnx2di },
  { 0x2c4a5d, CODE_FOR_scatter_storevnx2hivnx2di },
  { 0x2c4a60, CODE_FOR_scatter_storevnx2sivnx2di },
  { 0x2c4a6d, CODE_FOR_scatter_storevnx2dfvnx2di },
  { 0x2c4a7a, CODE_FOR_scatter_storevnx2bfvnx2di },
  { 0x2c4a7b, CODE_FOR_scatter_storevnx2hfvnx2di },
  { 0x2c4a7e, CODE_FOR_scatter_storevnx2sfvnx2di },
  { 0x2d4848, CODE_FOR_mask_scatter_storevnx4sivnx4si },
  { 0x2d485c, CODE_FOR_mask_scatter_storevnx4qivnx4si },
  { 0x2d485f, CODE_FOR_mask_scatter_storevnx4hivnx4si },
  { 0x2d486b, CODE_FOR_mask_scatter_storevnx4sfvnx4si },
  { 0x2d487c, CODE_FOR_mask_scatter_storevnx4bfvnx4si },
  { 0x2d487d, CODE_FOR_mask_scatter_storevnx4hfvnx4si },
  { 0x2d4a4a, CODE_FOR_mask_scatter_storevnx2divnx2di },
  { 0x2d4a5b, CODE_FOR_mask_scatter_storevnx2qivnx2di },
  { 0x2d4a5d, CODE_FOR_mask_scatter_storevnx2hivnx2di },
  { 0x2d4a60, CODE_FOR_mask_scatter_storevnx2sivnx2di },
  { 0x2d4a6d, CODE_FOR_mask_scatter_storevnx2dfvnx2di },
  { 0x2d4a7a, CODE_FOR_mask_scatter_storevnx2bfvnx2di },
  { 0x2d4a7b, CODE_FOR_mask_scatter_storevnx2hfvnx2di },
  { 0x2d4a7e, CODE_FOR_mask_scatter_storevnx2sfvnx2di },
  { 0x2e0d3c, CODE_FOR_vec_extractvnx16biqi },
  { 0x2e0d40, CODE_FOR_vec_extractv8qiqi },
  { 0x2e0d43, CODE_FOR_vec_extractv16qiqi },
  { 0x2e0d44, CODE_FOR_vec_extractvnx16qiqi },
  { 0x2e0e3d, CODE_FOR_vec_extractvnx8bihi },
  { 0x2e0e41, CODE_FOR_vec_extractv4hihi },
  { 0x2e0e45, CODE_FOR_vec_extractv8hihi },
  { 0x2e0e46, CODE_FOR_vec_extractvnx8hihi },
  { 0x2e0f3e, CODE_FOR_vec_extractvnx4bisi },
  { 0x2e0f42, CODE_FOR_vec_extractv2sisi },
  { 0x2e0f47, CODE_FOR_vec_extractv4sisi },
  { 0x2e0f48, CODE_FOR_vec_extractvnx4sisi },
  { 0x2e103f, CODE_FOR_vec_extractvnx2bidi },
  { 0x2e1049, CODE_FOR_vec_extractv2didi },
  { 0x2e104a, CODE_FOR_vec_extractvnx2didi },
  { 0x2e2763, CODE_FOR_vec_extractv4hfhf },
  { 0x2e2767, CODE_FOR_vec_extractv8hfhf },
  { 0x2e2769, CODE_FOR_vec_extractvnx8hfhf },
  { 0x2e2862, CODE_FOR_vec_extractv4bfbf },
  { 0x2e2866, CODE_FOR_vec_extractv8bfbf },
  { 0x2e2868, CODE_FOR_vec_extractvnx8bfbf },
  { 0x2e2964, CODE_FOR_vec_extractv2sfsf },
  { 0x2e296a, CODE_FOR_vec_extractv4sfsf },
  { 0x2e296b, CODE_FOR_vec_extractvnx4sfsf },
  { 0x2e2a6c, CODE_FOR_vec_extractv2dfdf },
  { 0x2e2a6d, CODE_FOR_vec_extractvnx2dfdf },
  { 0x2e4043, CODE_FOR_vec_extractv16qiv8qi },
  { 0x2e4145, CODE_FOR_vec_extractv8hiv4hi },
  { 0x2e4247, CODE_FOR_vec_extractv4siv2si },
  { 0x2e6266, CODE_FOR_vec_extractv8bfv4bf },
  { 0x2e6367, CODE_FOR_vec_extractv8hfv4hf },
  { 0x2e646a, CODE_FOR_vec_extractv4sfv2sf },
  { 0x2e656c, CODE_FOR_vec_extractv2dfv1df },
  { 0x2f0d40, CODE_FOR_vec_initv8qiqi },
  { 0x2f0d43, CODE_FOR_vec_initv16qiqi },
  { 0x2f0d44, CODE_FOR_vec_initvnx16qiqi },
  { 0x2f0e41, CODE_FOR_vec_initv4hihi },
  { 0x2f0e45, CODE_FOR_vec_initv8hihi },
  { 0x2f0e46, CODE_FOR_vec_initvnx8hihi },
  { 0x2f0f42, CODE_FOR_vec_initv2sisi },
  { 0x2f0f47, CODE_FOR_vec_initv4sisi },
  { 0x2f0f48, CODE_FOR_vec_initvnx4sisi },
  { 0x2f1049, CODE_FOR_vec_initv2didi },
  { 0x2f104a, CODE_FOR_vec_initvnx2didi },
  { 0x2f2763, CODE_FOR_vec_initv4hfhf },
  { 0x2f2767, CODE_FOR_vec_initv8hfhf },
  { 0x2f2769, CODE_FOR_vec_initvnx8hfhf },
  { 0x2f2862, CODE_FOR_vec_initv4bfbf },
  { 0x2f2866, CODE_FOR_vec_initv8bfbf },
  { 0x2f2868, CODE_FOR_vec_initvnx8bfbf },
  { 0x2f2964, CODE_FOR_vec_initv2sfsf },
  { 0x2f296a, CODE_FOR_vec_initv4sfsf },
  { 0x2f296b, CODE_FOR_vec_initvnx4sfsf },
  { 0x2f2a6c, CODE_FOR_vec_initv2dfdf },
  { 0x2f2a6d, CODE_FOR_vec_initvnx2dfdf },
  { 0x2f4043, CODE_FOR_vec_initv16qiv8qi },
  { 0x2f4145, CODE_FOR_vec_initv8hiv4hi },
  { 0x2f4247, CODE_FOR_vec_initv4siv2si },
  { 0x2f6266, CODE_FOR_vec_initv8bfv4bf },
  { 0x2f6367, CODE_FOR_vec_initv8hfv4hf },
  { 0x2f646a, CODE_FOR_vec_initv4sfv2sf },
  { 0x303c0f, CODE_FOR_while_ultsivnx16bi },
  { 0x303c10, CODE_FOR_while_ultdivnx16bi },
  { 0x303d0f, CODE_FOR_while_ultsivnx8bi },
  { 0x303d10, CODE_FOR_while_ultdivnx8bi },
  { 0x303e0f, CODE_FOR_while_ultsivnx4bi },
  { 0x303e10, CODE_FOR_while_ultdivnx4bi },
  { 0x303f0f, CODE_FOR_while_ultsivnx2bi },
  { 0x303f10, CODE_FOR_while_ultdivnx2bi },
  { 0x31000f, CODE_FOR_addsi3 },
  { 0x310010, CODE_FOR_adddi3 },
  { 0x310011, CODE_FOR_addti3 },
  { 0x310027, CODE_FOR_addhf3 },
  { 0x310029, CODE_FOR_addsf3 },
  { 0x31002a, CODE_FOR_adddf3 },
  { 0x310040, CODE_FOR_addv8qi3 },
  { 0x310041, CODE_FOR_addv4hi3 },
  { 0x310042, CODE_FOR_addv2si3 },
  { 0x310043, CODE_FOR_addv16qi3 },
  { 0x310044, CODE_FOR_addvnx16qi3 },
  { 0x310045, CODE_FOR_addv8hi3 },
  { 0x310046, CODE_FOR_addvnx8hi3 },
  { 0x310047, CODE_FOR_addv4si3 },
  { 0x310048, CODE_FOR_addvnx4si3 },
  { 0x310049, CODE_FOR_addv2di3 },
  { 0x31004a, CODE_FOR_addvnx2di3 },
  { 0x31005b, CODE_FOR_addvnx2qi3 },
  { 0x31005c, CODE_FOR_addvnx4qi3 },
  { 0x31005d, CODE_FOR_addvnx2hi3 },
  { 0x31005e, CODE_FOR_addvnx8qi3 },
  { 0x31005f, CODE_FOR_addvnx4hi3 },
  { 0x310060, CODE_FOR_addvnx2si3 },
  { 0x310063, CODE_FOR_addv4hf3 },
  { 0x310064, CODE_FOR_addv2sf3 },
  { 0x310067, CODE_FOR_addv8hf3 },
  { 0x310069, CODE_FOR_addvnx8hf3 },
  { 0x31006a, CODE_FOR_addv4sf3 },
  { 0x31006b, CODE_FOR_addvnx4sf3 },
  { 0x31006c, CODE_FOR_addv2df3 },
  { 0x31006d, CODE_FOR_addvnx2df3 },
  { 0x35000f, CODE_FOR_subsi3 },
  { 0x350010, CODE_FOR_subdi3 },
  { 0x350011, CODE_FOR_subti3 },
  { 0x350027, CODE_FOR_subhf3 },
  { 0x350029, CODE_FOR_subsf3 },
  { 0x35002a, CODE_FOR_subdf3 },
  { 0x350040, CODE_FOR_subv8qi3 },
  { 0x350041, CODE_FOR_subv4hi3 },
  { 0x350042, CODE_FOR_subv2si3 },
  { 0x350043, CODE_FOR_subv16qi3 },
  { 0x350044, CODE_FOR_subvnx16qi3 },
  { 0x350045, CODE_FOR_subv8hi3 },
  { 0x350046, CODE_FOR_subvnx8hi3 },
  { 0x350047, CODE_FOR_subv4si3 },
  { 0x350048, CODE_FOR_subvnx4si3 },
  { 0x350049, CODE_FOR_subv2di3 },
  { 0x35004a, CODE_FOR_subvnx2di3 },
  { 0x35005b, CODE_FOR_subvnx2qi3 },
  { 0x35005c, CODE_FOR_subvnx4qi3 },
  { 0x35005d, CODE_FOR_subvnx2hi3 },
  { 0x35005e, CODE_FOR_subvnx8qi3 },
  { 0x35005f, CODE_FOR_subvnx4hi3 },
  { 0x350060, CODE_FOR_subvnx2si3 },
  { 0x350063, CODE_FOR_subv4hf3 },
  { 0x350064, CODE_FOR_subv2sf3 },
  { 0x350067, CODE_FOR_subv8hf3 },
  { 0x350069, CODE_FOR_subvnx8hf3 },
  { 0x35006a, CODE_FOR_subv4sf3 },
  { 0x35006b, CODE_FOR_subvnx4sf3 },
  { 0x35006c, CODE_FOR_subv2df3 },
  { 0x35006d, CODE_FOR_subvnx2df3 },
  { 0x39000f, CODE_FOR_mulsi3 },
  { 0x390010, CODE_FOR_muldi3 },
  { 0x390011, CODE_FOR_multi3 },
  { 0x390027, CODE_FOR_mulhf3 },
  { 0x390029, CODE_FOR_mulsf3 },
  { 0x39002a, CODE_FOR_muldf3 },
  { 0x390040, CODE_FOR_mulv8qi3 },
  { 0x390041, CODE_FOR_mulv4hi3 },
  { 0x390042, CODE_FOR_mulv2si3 },
  { 0x390043, CODE_FOR_mulv16qi3 },
  { 0x390044, CODE_FOR_mulvnx16qi3 },
  { 0x390045, CODE_FOR_mulv8hi3 },
  { 0x390046, CODE_FOR_mulvnx8hi3 },
  { 0x390047, CODE_FOR_mulv4si3 },
  { 0x390048, CODE_FOR_mulvnx4si3 },
  { 0x39004a, CODE_FOR_mulvnx2di3 },
  { 0x39005b, CODE_FOR_mulvnx2qi3 },
  { 0x39005c, CODE_FOR_mulvnx4qi3 },
  { 0x39005d, CODE_FOR_mulvnx2hi3 },
  { 0x39005e, CODE_FOR_mulvnx8qi3 },
  { 0x39005f, CODE_FOR_mulvnx4hi3 },
  { 0x390060, CODE_FOR_mulvnx2si3 },
  { 0x390063, CODE_FOR_mulv4hf3 },
  { 0x390064, CODE_FOR_mulv2sf3 },
  { 0x390067, CODE_FOR_mulv8hf3 },
  { 0x390069, CODE_FOR_mulvnx8hf3 },
  { 0x39006a, CODE_FOR_mulv4sf3 },
  { 0x39006b, CODE_FOR_mulvnx4sf3 },
  { 0x39006c, CODE_FOR_mulv2df3 },
  { 0x39006d, CODE_FOR_mulvnx2df3 },
  { 0x3d000f, CODE_FOR_divsi3 },
  { 0x3d0010, CODE_FOR_divdi3 },
  { 0x3d0027, CODE_FOR_divhf3 },
  { 0x3d0029, CODE_FOR_divsf3 },
  { 0x3d002a, CODE_FOR_divdf3 },
  { 0x3d0048, CODE_FOR_divvnx4si3 },
  { 0x3d004a, CODE_FOR_divvnx2di3 },
  { 0x3d0063, CODE_FOR_divv4hf3 },
  { 0x3d0064, CODE_FOR_divv2sf3 },
  { 0x3d0067, CODE_FOR_divv8hf3 },
  { 0x3d0069, CODE_FOR_divvnx8hf3 },
  { 0x3d006a, CODE_FOR_divv4sf3 },
  { 0x3d006b, CODE_FOR_divvnx4sf3 },
  { 0x3d006c, CODE_FOR_divv2df3 },
  { 0x3d006d, CODE_FOR_divvnx2df3 },
  { 0x40000f, CODE_FOR_udivsi3 },
  { 0x400010, CODE_FOR_udivdi3 },
  { 0x400048, CODE_FOR_udivvnx4si3 },
  { 0x40004a, CODE_FOR_udivvnx2di3 },
  { 0x44000f, CODE_FOR_modsi3 },
  { 0x440010, CODE_FOR_moddi3 },
  { 0x460063, CODE_FOR_ftruncv4hf2 },
  { 0x460064, CODE_FOR_ftruncv2sf2 },
  { 0x460067, CODE_FOR_ftruncv8hf2 },
  { 0x46006a, CODE_FOR_ftruncv4sf2 },
  { 0x46006c, CODE_FOR_ftruncv2df2 },
  { 0x47000f, CODE_FOR_andsi3 },
  { 0x470010, CODE_FOR_anddi3 },
  { 0x47003c, CODE_FOR_andvnx16bi3 },
  { 0x47003d, CODE_FOR_andvnx8bi3 },
  { 0x47003e, CODE_FOR_andvnx4bi3 },
  { 0x47003f, CODE_FOR_andvnx2bi3 },
  { 0x470040, CODE_FOR_andv8qi3 },
  { 0x470041, CODE_FOR_andv4hi3 },
  { 0x470042, CODE_FOR_andv2si3 },
  { 0x470043, CODE_FOR_andv16qi3 },
  { 0x470044, CODE_FOR_andvnx16qi3 },
  { 0x470045, CODE_FOR_andv8hi3 },
  { 0x470046, CODE_FOR_andvnx8hi3 },
  { 0x470047, CODE_FOR_andv4si3 },
  { 0x470048, CODE_FOR_andvnx4si3 },
  { 0x470049, CODE_FOR_andv2di3 },
  { 0x47004a, CODE_FOR_andvnx2di3 },
  { 0x47005b, CODE_FOR_andvnx2qi3 },
  { 0x47005c, CODE_FOR_andvnx4qi3 },
  { 0x47005d, CODE_FOR_andvnx2hi3 },
  { 0x47005e, CODE_FOR_andvnx8qi3 },
  { 0x47005f, CODE_FOR_andvnx4hi3 },
  { 0x470060, CODE_FOR_andvnx2si3 },
  { 0x48000f, CODE_FOR_iorsi3 },
  { 0x480010, CODE_FOR_iordi3 },
  { 0x48003c, CODE_FOR_iorvnx16bi3 },
  { 0x48003d, CODE_FOR_iorvnx8bi3 },
  { 0x48003e, CODE_FOR_iorvnx4bi3 },
  { 0x48003f, CODE_FOR_iorvnx2bi3 },
  { 0x480040, CODE_FOR_iorv8qi3 },
  { 0x480041, CODE_FOR_iorv4hi3 },
  { 0x480042, CODE_FOR_iorv2si3 },
  { 0x480043, CODE_FOR_iorv16qi3 },
  { 0x480044, CODE_FOR_iorvnx16qi3 },
  { 0x480045, CODE_FOR_iorv8hi3 },
  { 0x480046, CODE_FOR_iorvnx8hi3 },
  { 0x480047, CODE_FOR_iorv4si3 },
  { 0x480048, CODE_FOR_iorvnx4si3 },
  { 0x480049, CODE_FOR_iorv2di3 },
  { 0x48004a, CODE_FOR_iorvnx2di3 },
  { 0x48005b, CODE_FOR_iorvnx2qi3 },
  { 0x48005c, CODE_FOR_iorvnx4qi3 },
  { 0x48005d, CODE_FOR_iorvnx2hi3 },
  { 0x48005e, CODE_FOR_iorvnx8qi3 },
  { 0x48005f, CODE_FOR_iorvnx4hi3 },
  { 0x480060, CODE_FOR_iorvnx2si3 },
  { 0x49000f, CODE_FOR_xorsi3 },
  { 0x490010, CODE_FOR_xordi3 },
  { 0x49003c, CODE_FOR_xorvnx16bi3 },
  { 0x49003d, CODE_FOR_xorvnx8bi3 },
  { 0x49003e, CODE_FOR_xorvnx4bi3 },
  { 0x49003f, CODE_FOR_xorvnx2bi3 },
  { 0x490040, CODE_FOR_xorv8qi3 },
  { 0x490041, CODE_FOR_xorv4hi3 },
  { 0x490042, CODE_FOR_xorv2si3 },
  { 0x490043, CODE_FOR_xorv16qi3 },
  { 0x490044, CODE_FOR_xorvnx16qi3 },
  { 0x490045, CODE_FOR_xorv8hi3 },
  { 0x490046, CODE_FOR_xorvnx8hi3 },
  { 0x490047, CODE_FOR_xorv4si3 },
  { 0x490048, CODE_FOR_xorvnx4si3 },
  { 0x490049, CODE_FOR_xorv2di3 },
  { 0x49004a, CODE_FOR_xorvnx2di3 },
  { 0x49005b, CODE_FOR_xorvnx2qi3 },
  { 0x49005c, CODE_FOR_xorvnx4qi3 },
  { 0x49005d, CODE_FOR_xorvnx2hi3 },
  { 0x49005e, CODE_FOR_xorvnx8qi3 },
  { 0x49005f, CODE_FOR_xorvnx4hi3 },
  { 0x490060, CODE_FOR_xorvnx2si3 },
  { 0x4a000d, CODE_FOR_ashlqi3 },
  { 0x4a000e, CODE_FOR_ashlhi3 },
  { 0x4a000f, CODE_FOR_ashlsi3 },
  { 0x4a0010, CODE_FOR_ashldi3 },
  { 0x4a0040, CODE_FOR_ashlv8qi3 },
  { 0x4a0041, CODE_FOR_ashlv4hi3 },
  { 0x4a0042, CODE_FOR_ashlv2si3 },
  { 0x4a0043, CODE_FOR_ashlv16qi3 },
  { 0x4a0044, CODE_FOR_ashlvnx16qi3 },
  { 0x4a0045, CODE_FOR_ashlv8hi3 },
  { 0x4a0046, CODE_FOR_ashlvnx8hi3 },
  { 0x4a0047, CODE_FOR_ashlv4si3 },
  { 0x4a0048, CODE_FOR_ashlvnx4si3 },
  { 0x4a0049, CODE_FOR_ashlv2di3 },
  { 0x4a004a, CODE_FOR_ashlvnx2di3 },
  { 0x4a005b, CODE_FOR_ashlvnx2qi3 },
  { 0x4a005c, CODE_FOR_ashlvnx4qi3 },
  { 0x4a005d, CODE_FOR_ashlvnx2hi3 },
  { 0x4a005e, CODE_FOR_ashlvnx8qi3 },
  { 0x4a005f, CODE_FOR_ashlvnx4hi3 },
  { 0x4a0060, CODE_FOR_ashlvnx2si3 },
  { 0x4d000f, CODE_FOR_ashrsi3 },
  { 0x4d0010, CODE_FOR_ashrdi3 },
  { 0x4d0040, CODE_FOR_ashrv8qi3 },
  { 0x4d0041, CODE_FOR_ashrv4hi3 },
  { 0x4d0042, CODE_FOR_ashrv2si3 },
  { 0x4d0043, CODE_FOR_ashrv16qi3 },
  { 0x4d0044, CODE_FOR_ashrvnx16qi3 },
  { 0x4d0045, CODE_FOR_ashrv8hi3 },
  { 0x4d0046, CODE_FOR_ashrvnx8hi3 },
  { 0x4d0047, CODE_FOR_ashrv4si3 },
  { 0x4d0048, CODE_FOR_ashrvnx4si3 },
  { 0x4d0049, CODE_FOR_ashrv2di3 },
  { 0x4d004a, CODE_FOR_ashrvnx2di3 },
  { 0x4d005b, CODE_FOR_ashrvnx2qi3 },
  { 0x4d005c, CODE_FOR_ashrvnx4qi3 },
  { 0x4d005d, CODE_FOR_ashrvnx2hi3 },
  { 0x4d005e, CODE_FOR_ashrvnx8qi3 },
  { 0x4d005f, CODE_FOR_ashrvnx4hi3 },
  { 0x4d0060, CODE_FOR_ashrvnx2si3 },
  { 0x4e000f, CODE_FOR_lshrsi3 },
  { 0x4e0010, CODE_FOR_lshrdi3 },
  { 0x4e0040, CODE_FOR_lshrv8qi3 },
  { 0x4e0041, CODE_FOR_lshrv4hi3 },
  { 0x4e0042, CODE_FOR_lshrv2si3 },
  { 0x4e0043, CODE_FOR_lshrv16qi3 },
  { 0x4e0044, CODE_FOR_lshrvnx16qi3 },
  { 0x4e0045, CODE_FOR_lshrv8hi3 },
  { 0x4e0046, CODE_FOR_lshrvnx8hi3 },
  { 0x4e0047, CODE_FOR_lshrv4si3 },
  { 0x4e0048, CODE_FOR_lshrvnx4si3 },
  { 0x4e0049, CODE_FOR_lshrv2di3 },
  { 0x4e004a, CODE_FOR_lshrvnx2di3 },
  { 0x4e005b, CODE_FOR_lshrvnx2qi3 },
  { 0x4e005c, CODE_FOR_lshrvnx4qi3 },
  { 0x4e005d, CODE_FOR_lshrvnx2hi3 },
  { 0x4e005e, CODE_FOR_lshrvnx8qi3 },
  { 0x4e005f, CODE_FOR_lshrvnx4hi3 },
  { 0x4e0060, CODE_FOR_lshrvnx2si3 },
  { 0x4f000f, CODE_FOR_rotlsi3 },
  { 0x4f0010, CODE_FOR_rotldi3 },
  { 0x50000f, CODE_FOR_rotrsi3 },
  { 0x500010, CODE_FOR_rotrdi3 },
  { 0x510040, CODE_FOR_vashlv8qi3 },
  { 0x510041, CODE_FOR_vashlv4hi3 },
  { 0x510042, CODE_FOR_vashlv2si3 },
  { 0x510043, CODE_FOR_vashlv16qi3 },
  { 0x510044, CODE_FOR_vashlvnx16qi3 },
  { 0x510045, CODE_FOR_vashlv8hi3 },
  { 0x510046, CODE_FOR_vashlvnx8hi3 },
  { 0x510047, CODE_FOR_vashlv4si3 },
  { 0x510048, CODE_FOR_vashlvnx4si3 },
  { 0x510049, CODE_FOR_vashlv2di3 },
  { 0x51004a, CODE_FOR_vashlvnx2di3 },
  { 0x51005b, CODE_FOR_vashlvnx2qi3 },
  { 0x51005c, CODE_FOR_vashlvnx4qi3 },
  { 0x51005d, CODE_FOR_vashlvnx2hi3 },
  { 0x51005e, CODE_FOR_vashlvnx8qi3 },
  { 0x51005f, CODE_FOR_vashlvnx4hi3 },
  { 0x510060, CODE_FOR_vashlvnx2si3 },
  { 0x520040, CODE_FOR_vashrv8qi3 },
  { 0x520041, CODE_FOR_vashrv4hi3 },
  { 0x520042, CODE_FOR_vashrv2si3 },
  { 0x520043, CODE_FOR_vashrv16qi3 },
  { 0x520044, CODE_FOR_vashrvnx16qi3 },
  { 0x520045, CODE_FOR_vashrv8hi3 },
  { 0x520046, CODE_FOR_vashrvnx8hi3 },
  { 0x520047, CODE_FOR_vashrv4si3 },
  { 0x520048, CODE_FOR_vashrvnx4si3 },
  { 0x52004a, CODE_FOR_vashrvnx2di3 },
  { 0x52005b, CODE_FOR_vashrvnx2qi3 },
  { 0x52005c, CODE_FOR_vashrvnx4qi3 },
  { 0x52005d, CODE_FOR_vashrvnx2hi3 },
  { 0x52005e, CODE_FOR_vashrvnx8qi3 },
  { 0x52005f, CODE_FOR_vashrvnx4hi3 },
  { 0x520060, CODE_FOR_vashrvnx2si3 },
  { 0x530040, CODE_FOR_vlshrv8qi3 },
  { 0x530041, CODE_FOR_vlshrv4hi3 },
  { 0x530042, CODE_FOR_vlshrv2si3 },
  { 0x530043, CODE_FOR_vlshrv16qi3 },
  { 0x530044, CODE_FOR_vlshrvnx16qi3 },
  { 0x530045, CODE_FOR_vlshrv8hi3 },
  { 0x530046, CODE_FOR_vlshrvnx8hi3 },
  { 0x530047, CODE_FOR_vlshrv4si3 },
  { 0x530048, CODE_FOR_vlshrvnx4si3 },
  { 0x53004a, CODE_FOR_vlshrvnx2di3 },
  { 0x53005b, CODE_FOR_vlshrvnx2qi3 },
  { 0x53005c, CODE_FOR_vlshrvnx4qi3 },
  { 0x53005d, CODE_FOR_vlshrvnx2hi3 },
  { 0x53005e, CODE_FOR_vlshrvnx8qi3 },
  { 0x53005f, CODE_FOR_vlshrvnx4hi3 },
  { 0x530060, CODE_FOR_vlshrvnx2si3 },
  { 0x560029, CODE_FOR_sminsf3 },
  { 0x56002a, CODE_FOR_smindf3 },
  { 0x560040, CODE_FOR_sminv8qi3 },
  { 0x560041, CODE_FOR_sminv4hi3 },
  { 0x560042, CODE_FOR_sminv2si3 },
  { 0x560043, CODE_FOR_sminv16qi3 },
  { 0x560044, CODE_FOR_sminvnx16qi3 },
  { 0x560045, CODE_FOR_sminv8hi3 },
  { 0x560046, CODE_FOR_sminvnx8hi3 },
  { 0x560047, CODE_FOR_sminv4si3 },
  { 0x560048, CODE_FOR_sminvnx4si3 },
  { 0x560049, CODE_FOR_sminv2di3 },
  { 0x56004a, CODE_FOR_sminvnx2di3 },
  { 0x56005b, CODE_FOR_sminvnx2qi3 },
  { 0x56005c, CODE_FOR_sminvnx4qi3 },
  { 0x56005d, CODE_FOR_sminvnx2hi3 },
  { 0x56005e, CODE_FOR_sminvnx8qi3 },
  { 0x56005f, CODE_FOR_sminvnx4hi3 },
  { 0x560060, CODE_FOR_sminvnx2si3 },
  { 0x560063, CODE_FOR_sminv4hf3 },
  { 0x560064, CODE_FOR_sminv2sf3 },
  { 0x560067, CODE_FOR_sminv8hf3 },
  { 0x560069, CODE_FOR_sminvnx8hf3 },
  { 0x56006a, CODE_FOR_sminv4sf3 },
  { 0x56006b, CODE_FOR_sminvnx4sf3 },
  { 0x56006c, CODE_FOR_sminv2df3 },
  { 0x56006d, CODE_FOR_sminvnx2df3 },
  { 0x570029, CODE_FOR_smaxsf3 },
  { 0x57002a, CODE_FOR_smaxdf3 },
  { 0x570040, CODE_FOR_smaxv8qi3 },
  { 0x570041, CODE_FOR_smaxv4hi3 },
  { 0x570042, CODE_FOR_smaxv2si3 },
  { 0x570043, CODE_FOR_smaxv16qi3 },
  { 0x570044, CODE_FOR_smaxvnx16qi3 },
  { 0x570045, CODE_FOR_smaxv8hi3 },
  { 0x570046, CODE_FOR_smaxvnx8hi3 },
  { 0x570047, CODE_FOR_smaxv4si3 },
  { 0x570048, CODE_FOR_smaxvnx4si3 },
  { 0x570049, CODE_FOR_smaxv2di3 },
  { 0x57004a, CODE_FOR_smaxvnx2di3 },
  { 0x57005b, CODE_FOR_smaxvnx2qi3 },
  { 0x57005c, CODE_FOR_smaxvnx4qi3 },
  { 0x57005d, CODE_FOR_smaxvnx2hi3 },
  { 0x57005e, CODE_FOR_smaxvnx8qi3 },
  { 0x57005f, CODE_FOR_smaxvnx4hi3 },
  { 0x570060, CODE_FOR_smaxvnx2si3 },
  { 0x570063, CODE_FOR_smaxv4hf3 },
  { 0x570064, CODE_FOR_smaxv2sf3 },
  { 0x570067, CODE_FOR_smaxv8hf3 },
  { 0x570069, CODE_FOR_smaxvnx8hf3 },
  { 0x57006a, CODE_FOR_smaxv4sf3 },
  { 0x57006b, CODE_FOR_smaxvnx4sf3 },
  { 0x57006c, CODE_FOR_smaxv2df3 },
  { 0x57006d, CODE_FOR_smaxvnx2df3 },
  { 0x580040, CODE_FOR_uminv8qi3 },
  { 0x580041, CODE_FOR_uminv4hi3 },
  { 0x580042, CODE_FOR_uminv2si3 },
  { 0x580043, CODE_FOR_uminv16qi3 },
  { 0x580044, CODE_FOR_uminvnx16qi3 },
  { 0x580045, CODE_FOR_uminv8hi3 },
  { 0x580046, CODE_FOR_uminvnx8hi3 },
  { 0x580047, CODE_FOR_uminv4si3 },
  { 0x580048, CODE_FOR_uminvnx4si3 },
  { 0x580049, CODE_FOR_uminv2di3 },
  { 0x58004a, CODE_FOR_uminvnx2di3 },
  { 0x58005b, CODE_FOR_uminvnx2qi3 },
  { 0x58005c, CODE_FOR_uminvnx4qi3 },
  { 0x58005d, CODE_FOR_uminvnx2hi3 },
  { 0x58005e, CODE_FOR_uminvnx8qi3 },
  { 0x58005f, CODE_FOR_uminvnx4hi3 },
  { 0x580060, CODE_FOR_uminvnx2si3 },
  { 0x59000f, CODE_FOR_umaxsi3 },
  { 0x590010, CODE_FOR_umaxdi3 },
  { 0x590040, CODE_FOR_umaxv8qi3 },
  { 0x590041, CODE_FOR_umaxv4hi3 },
  { 0x590042, CODE_FOR_umaxv2si3 },
  { 0x590043, CODE_FOR_umaxv16qi3 },
  { 0x590044, CODE_FOR_umaxvnx16qi3 },
  { 0x590045, CODE_FOR_umaxv8hi3 },
  { 0x590046, CODE_FOR_umaxvnx8hi3 },
  { 0x590047, CODE_FOR_umaxv4si3 },
  { 0x590048, CODE_FOR_umaxvnx4si3 },
  { 0x590049, CODE_FOR_umaxv2di3 },
  { 0x59004a, CODE_FOR_umaxvnx2di3 },
  { 0x59005b, CODE_FOR_umaxvnx2qi3 },
  { 0x59005c, CODE_FOR_umaxvnx4qi3 },
  { 0x59005d, CODE_FOR_umaxvnx2hi3 },
  { 0x59005e, CODE_FOR_umaxvnx8qi3 },
  { 0x59005f, CODE_FOR_umaxvnx4hi3 },
  { 0x590060, CODE_FOR_umaxvnx2si3 },
  { 0x5a000f, CODE_FOR_negsi2 },
  { 0x5a0010, CODE_FOR_negdi2 },
  { 0x5a0027, CODE_FOR_neghf2 },
  { 0x5a0029, CODE_FOR_negsf2 },
  { 0x5a002a, CODE_FOR_negdf2 },
  { 0x5a0040, CODE_FOR_negv8qi2 },
  { 0x5a0041, CODE_FOR_negv4hi2 },
  { 0x5a0042, CODE_FOR_negv2si2 },
  { 0x5a0043, CODE_FOR_negv16qi2 },
  { 0x5a0044, CODE_FOR_negvnx16qi2 },
  { 0x5a0045, CODE_FOR_negv8hi2 },
  { 0x5a0046, CODE_FOR_negvnx8hi2 },
  { 0x5a0047, CODE_FOR_negv4si2 },
  { 0x5a0048, CODE_FOR_negvnx4si2 },
  { 0x5a0049, CODE_FOR_negv2di2 },
  { 0x5a004a, CODE_FOR_negvnx2di2 },
  { 0x5a005b, CODE_FOR_negvnx2qi2 },
  { 0x5a005c, CODE_FOR_negvnx4qi2 },
  { 0x5a005d, CODE_FOR_negvnx2hi2 },
  { 0x5a005e, CODE_FOR_negvnx8qi2 },
  { 0x5a005f, CODE_FOR_negvnx4hi2 },
  { 0x5a0060, CODE_FOR_negvnx2si2 },
  { 0x5a0063, CODE_FOR_negv4hf2 },
  { 0x5a0064, CODE_FOR_negv2sf2 },
  { 0x5a0067, CODE_FOR_negv8hf2 },
  { 0x5a0069, CODE_FOR_negvnx8hf2 },
  { 0x5a006a, CODE_FOR_negv4sf2 },
  { 0x5a006b, CODE_FOR_negvnx4sf2 },
  { 0x5a006c, CODE_FOR_negv2df2 },
  { 0x5a006d, CODE_FOR_negvnx2df2 },
  { 0x5e000f, CODE_FOR_abssi2 },
  { 0x5e0010, CODE_FOR_absdi2 },
  { 0x5e0027, CODE_FOR_abshf2 },
  { 0x5e0029, CODE_FOR_abssf2 },
  { 0x5e002a, CODE_FOR_absdf2 },
  { 0x5e0040, CODE_FOR_absv8qi2 },
  { 0x5e0041, CODE_FOR_absv4hi2 },
  { 0x5e0042, CODE_FOR_absv2si2 },
  { 0x5e0043, CODE_FOR_absv16qi2 },
  { 0x5e0044, CODE_FOR_absvnx16qi2 },
  { 0x5e0045, CODE_FOR_absv8hi2 },
  { 0x5e0046, CODE_FOR_absvnx8hi2 },
  { 0x5e0047, CODE_FOR_absv4si2 },
  { 0x5e0048, CODE_FOR_absvnx4si2 },
  { 0x5e0049, CODE_FOR_absv2di2 },
  { 0x5e004a, CODE_FOR_absvnx2di2 },
  { 0x5e005b, CODE_FOR_absvnx2qi2 },
  { 0x5e005c, CODE_FOR_absvnx4qi2 },
  { 0x5e005d, CODE_FOR_absvnx2hi2 },
  { 0x5e005e, CODE_FOR_absvnx8qi2 },
  { 0x5e005f, CODE_FOR_absvnx4hi2 },
  { 0x5e0060, CODE_FOR_absvnx2si2 },
  { 0x5e0063, CODE_FOR_absv4hf2 },
  { 0x5e0064, CODE_FOR_absv2sf2 },
  { 0x5e0067, CODE_FOR_absv8hf2 },
  { 0x5e0069, CODE_FOR_absvnx8hf2 },
  { 0x5e006a, CODE_FOR_absv4sf2 },
  { 0x5e006b, CODE_FOR_absvnx4sf2 },
  { 0x5e006c, CODE_FOR_absv2df2 },
  { 0x5e006d, CODE_FOR_absvnx2df2 },
  { 0x60000f, CODE_FOR_one_cmplsi2 },
  { 0x600010, CODE_FOR_one_cmpldi2 },
  { 0x60003c, CODE_FOR_one_cmplvnx16bi2 },
  { 0x60003d, CODE_FOR_one_cmplvnx8bi2 },
  { 0x60003e, CODE_FOR_one_cmplvnx4bi2 },
  { 0x60003f, CODE_FOR_one_cmplvnx2bi2 },
  { 0x600040, CODE_FOR_one_cmplv8qi2 },
  { 0x600041, CODE_FOR_one_cmplv4hi2 },
  { 0x600042, CODE_FOR_one_cmplv2si2 },
  { 0x600043, CODE_FOR_one_cmplv16qi2 },
  { 0x600044, CODE_FOR_one_cmplvnx16qi2 },
  { 0x600045, CODE_FOR_one_cmplv8hi2 },
  { 0x600046, CODE_FOR_one_cmplvnx8hi2 },
  { 0x600047, CODE_FOR_one_cmplv4si2 },
  { 0x600048, CODE_FOR_one_cmplvnx4si2 },
  { 0x600049, CODE_FOR_one_cmplv2di2 },
  { 0x60004a, CODE_FOR_one_cmplvnx2di2 },
  { 0x60005b, CODE_FOR_one_cmplvnx2qi2 },
  { 0x60005c, CODE_FOR_one_cmplvnx4qi2 },
  { 0x60005d, CODE_FOR_one_cmplvnx2hi2 },
  { 0x60005e, CODE_FOR_one_cmplvnx8qi2 },
  { 0x60005f, CODE_FOR_one_cmplvnx4hi2 },
  { 0x600060, CODE_FOR_one_cmplvnx2si2 },
  { 0x61000e, CODE_FOR_bswaphi2 },
  { 0x61000f, CODE_FOR_bswapsi2 },
  { 0x610010, CODE_FOR_bswapdi2 },
  { 0x610041, CODE_FOR_bswapv4hi2 },
  { 0x610042, CODE_FOR_bswapv2si2 },
  { 0x610045, CODE_FOR_bswapv8hi2 },
  { 0x610047, CODE_FOR_bswapv4si2 },
  { 0x610049, CODE_FOR_bswapv2di2 },
  { 0x62000f, CODE_FOR_ffssi2 },
  { 0x620010, CODE_FOR_ffsdi2 },
  { 0x63000f, CODE_FOR_clzsi2 },
  { 0x630010, CODE_FOR_clzdi2 },
  { 0x630040, CODE_FOR_clzv8qi2 },
  { 0x630041, CODE_FOR_clzv4hi2 },
  { 0x630042, CODE_FOR_clzv2si2 },
  { 0x630043, CODE_FOR_clzv16qi2 },
  { 0x630044, CODE_FOR_clzvnx16qi2 },
  { 0x630045, CODE_FOR_clzv8hi2 },
  { 0x630046, CODE_FOR_clzvnx8hi2 },
  { 0x630047, CODE_FOR_clzv4si2 },
  { 0x630048, CODE_FOR_clzvnx4si2 },
  { 0x63004a, CODE_FOR_clzvnx2di2 },
  { 0x63005b, CODE_FOR_clzvnx2qi2 },
  { 0x63005c, CODE_FOR_clzvnx4qi2 },
  { 0x63005d, CODE_FOR_clzvnx2hi2 },
  { 0x63005e, CODE_FOR_clzvnx8qi2 },
  { 0x63005f, CODE_FOR_clzvnx4hi2 },
  { 0x630060, CODE_FOR_clzvnx2si2 },
  { 0x64000f, CODE_FOR_ctzsi2 },
  { 0x640010, CODE_FOR_ctzdi2 },
  { 0x640042, CODE_FOR_ctzv2si2 },
  { 0x640047, CODE_FOR_ctzv4si2 },
  { 0x65000f, CODE_FOR_clrsbsi2 },
  { 0x650010, CODE_FOR_clrsbdi2 },
  { 0x650040, CODE_FOR_clrsbv8qi2 },
  { 0x650041, CODE_FOR_clrsbv4hi2 },
  { 0x650042, CODE_FOR_clrsbv2si2 },
  { 0x650043, CODE_FOR_clrsbv16qi2 },
  { 0x650044, CODE_FOR_clrsbvnx16qi2 },
  { 0x650045, CODE_FOR_clrsbv8hi2 },
  { 0x650046, CODE_FOR_clrsbvnx8hi2 },
  { 0x650047, CODE_FOR_clrsbv4si2 },
  { 0x650048, CODE_FOR_clrsbvnx4si2 },
  { 0x65004a, CODE_FOR_clrsbvnx2di2 },
  { 0x65005b, CODE_FOR_clrsbvnx2qi2 },
  { 0x65005c, CODE_FOR_clrsbvnx4qi2 },
  { 0x65005d, CODE_FOR_clrsbvnx2hi2 },
  { 0x65005e, CODE_FOR_clrsbvnx8qi2 },
  { 0x65005f, CODE_FOR_clrsbvnx4hi2 },
  { 0x650060, CODE_FOR_clrsbvnx2si2 },
  { 0x66000f, CODE_FOR_popcountsi2 },
  { 0x660010, CODE_FOR_popcountdi2 },
  { 0x660040, CODE_FOR_popcountv8qi2 },
  { 0x660043, CODE_FOR_popcountv16qi2 },
  { 0x660044, CODE_FOR_popcountvnx16qi2 },
  { 0x660046, CODE_FOR_popcountvnx8hi2 },
  { 0x660048, CODE_FOR_popcountvnx4si2 },
  { 0x66004a, CODE_FOR_popcountvnx2di2 },
  { 0x66005b, CODE_FOR_popcountvnx2qi2 },
  { 0x66005c, CODE_FOR_popcountvnx4qi2 },
  { 0x66005d, CODE_FOR_popcountvnx2hi2 },
  { 0x66005e, CODE_FOR_popcountvnx8qi2 },
  { 0x66005f, CODE_FOR_popcountvnx4hi2 },
  { 0x660060, CODE_FOR_popcountvnx2si2 },
  { 0x720027, CODE_FOR_sqrthf2 },
  { 0x720029, CODE_FOR_sqrtsf2 },
  { 0x72002a, CODE_FOR_sqrtdf2 },
  { 0x720063, CODE_FOR_sqrtv4hf2 },
  { 0x720064, CODE_FOR_sqrtv2sf2 },
  { 0x720067, CODE_FOR_sqrtv8hf2 },
  { 0x720069, CODE_FOR_sqrtvnx8hf2 },
  { 0x72006a, CODE_FOR_sqrtv4sf2 },
  { 0x72006b, CODE_FOR_sqrtvnx4sf2 },
  { 0x72006c, CODE_FOR_sqrtv2df2 },
  { 0x72006d, CODE_FOR_sqrtvnx2df2 },
  { 0x81000d, CODE_FOR_movqi },
  { 0x81000e, CODE_FOR_movhi },
  { 0x81000f, CODE_FOR_movsi },
  { 0x810010, CODE_FOR_movdi },
  { 0x810011, CODE_FOR_movti },
  { 0x810012, CODE_FOR_movoi },
  { 0x810013, CODE_FOR_movci },
  { 0x810014, CODE_FOR_movxi },
  { 0x810027, CODE_FOR_movhf },
  { 0x810028, CODE_FOR_movbf },
  { 0x810029, CODE_FOR_movsf },
  { 0x81002a, CODE_FOR_movdf },
  { 0x81002b, CODE_FOR_movtf },
  { 0x81003c, CODE_FOR_movvnx16bi },
  { 0x81003d, CODE_FOR_movvnx8bi },
  { 0x81003e, CODE_FOR_movvnx4bi },
  { 0x81003f, CODE_FOR_movvnx2bi },
  { 0x810040, CODE_FOR_movv8qi },
  { 0x810041, CODE_FOR_movv4hi },
  { 0x810042, CODE_FOR_movv2si },
  { 0x810043, CODE_FOR_movv16qi },
  { 0x810044, CODE_FOR_movvnx16qi },
  { 0x810045, CODE_FOR_movv8hi },
  { 0x810046, CODE_FOR_movvnx8hi },
  { 0x810047, CODE_FOR_movv4si },
  { 0x810048, CODE_FOR_movvnx4si },
  { 0x810049, CODE_FOR_movv2di },
  { 0x81004a, CODE_FOR_movvnx2di },
  { 0x81004b, CODE_FOR_movvnx32qi },
  { 0x81004c, CODE_FOR_movvnx16hi },
  { 0x81004d, CODE_FOR_movvnx8si },
  { 0x81004e, CODE_FOR_movvnx4di },
  { 0x810050, CODE_FOR_movvnx48qi },
  { 0x810051, CODE_FOR_movvnx24hi },
  { 0x810052, CODE_FOR_movvnx12si },
  { 0x810053, CODE_FOR_movvnx6di },
  { 0x810055, CODE_FOR_movvnx64qi },
  { 0x810056, CODE_FOR_movvnx32hi },
  { 0x810057, CODE_FOR_movvnx16si },
  { 0x810058, CODE_FOR_movvnx8di },
  { 0x81005b, CODE_FOR_movvnx2qi },
  { 0x81005c, CODE_FOR_movvnx4qi },
  { 0x81005d, CODE_FOR_movvnx2hi },
  { 0x81005e, CODE_FOR_movvnx8qi },
  { 0x81005f, CODE_FOR_movvnx4hi },
  { 0x810060, CODE_FOR_movvnx2si },
  { 0x810062, CODE_FOR_movv4bf },
  { 0x810063, CODE_FOR_movv4hf },
  { 0x810064, CODE_FOR_movv2sf },
  { 0x810066, CODE_FOR_movv8bf },
  { 0x810067, CODE_FOR_movv8hf },
  { 0x810068, CODE_FOR_movvnx8bf },
  { 0x810069, CODE_FOR_movvnx8hf },
  { 0x81006a, CODE_FOR_movv4sf },
  { 0x81006b, CODE_FOR_movvnx4sf },
  { 0x81006c, CODE_FOR_movv2df },
  { 0x81006d, CODE_FOR_movvnx2df },
  { 0x81006e, CODE_FOR_movvnx16bf },
  { 0x81006f, CODE_FOR_movvnx16hf },
  { 0x810070, CODE_FOR_movvnx8sf },
  { 0x810071, CODE_FOR_movvnx4df },
  { 0x810072, CODE_FOR_movvnx24bf },
  { 0x810073, CODE_FOR_movvnx24hf },
  { 0x810074, CODE_FOR_movvnx12sf },
  { 0x810075, CODE_FOR_movvnx6df },
  { 0x810076, CODE_FOR_movvnx32bf },
  { 0x810077, CODE_FOR_movvnx32hf },
  { 0x810078, CODE_FOR_movvnx16sf },
  { 0x810079, CODE_FOR_movvnx8df },
  { 0x81007a, CODE_FOR_movvnx2bf },
  { 0x81007b, CODE_FOR_movvnx2hf },
  { 0x81007c, CODE_FOR_movvnx4bf },
  { 0x81007d, CODE_FOR_movvnx4hf },
  { 0x81007e, CODE_FOR_movvnx2sf },
  { 0x830040, CODE_FOR_movmisalignv8qi },
  { 0x830041, CODE_FOR_movmisalignv4hi },
  { 0x830042, CODE_FOR_movmisalignv2si },
  { 0x830043, CODE_FOR_movmisalignv16qi },
  { 0x830044, CODE_FOR_movmisalignvnx16qi },
  { 0x830045, CODE_FOR_movmisalignv8hi },
  { 0x830046, CODE_FOR_movmisalignvnx8hi },
  { 0x830047, CODE_FOR_movmisalignv4si },
  { 0x830048, CODE_FOR_movmisalignvnx4si },
  { 0x830049, CODE_FOR_movmisalignv2di },
  { 0x83004a, CODE_FOR_movmisalignvnx2di },
  { 0x83005b, CODE_FOR_movmisalignvnx2qi },
  { 0x83005c, CODE_FOR_movmisalignvnx4qi },
  { 0x83005d, CODE_FOR_movmisalignvnx2hi },
  { 0x83005e, CODE_FOR_movmisalignvnx8qi },
  { 0x83005f, CODE_FOR_movmisalignvnx4hi },
  { 0x830060, CODE_FOR_movmisalignvnx2si },
  { 0x830064, CODE_FOR_movmisalignv2sf },
  { 0x830068, CODE_FOR_movmisalignvnx8bf },
  { 0x830069, CODE_FOR_movmisalignvnx8hf },
  { 0x83006a, CODE_FOR_movmisalignv4sf },
  { 0x83006b, CODE_FOR_movmisalignvnx4sf },
  { 0x83006c, CODE_FOR_movmisalignv2df },
  { 0x83006d, CODE_FOR_movmisalignvnx2df },
  { 0x83007a, CODE_FOR_movmisalignvnx2bf },
  { 0x83007b, CODE_FOR_movmisalignvnx2hf },
  { 0x83007c, CODE_FOR_movmisalignvnx4bf },
  { 0x83007d, CODE_FOR_movmisalignvnx4hf },
  { 0x83007e, CODE_FOR_movmisalignvnx2sf },
  { 0x85000f, CODE_FOR_insvsi },
  { 0x850010, CODE_FOR_insvdi },
  { 0x8e0002, CODE_FOR_cbranchcc4 },
  { 0x8e000f, CODE_FOR_cbranchsi4 },
  { 0x8e0010, CODE_FOR_cbranchdi4 },
  { 0x8e0029, CODE_FOR_cbranchsf4 },
  { 0x8e002a, CODE_FOR_cbranchdf4 },
  { 0x8e003c, CODE_FOR_cbranchvnx16bi4 },
  { 0x8e003d, CODE_FOR_cbranchvnx8bi4 },
  { 0x8e003e, CODE_FOR_cbranchvnx4bi4 },
  { 0x8e003f, CODE_FOR_cbranchvnx2bi4 },
  { 0x90000f, CODE_FOR_negsicc },
  { 0x900010, CODE_FOR_negdicc },
  { 0x91000f, CODE_FOR_notsicc },
  { 0x910010, CODE_FOR_notdicc },
  { 0x92000d, CODE_FOR_movqicc },
  { 0x92000e, CODE_FOR_movhicc },
  { 0x92000f, CODE_FOR_movsicc },
  { 0x920010, CODE_FOR_movdicc },
  { 0x920029, CODE_FOR_movsfcc },
  { 0x92002a, CODE_FOR_movdfcc },
  { 0x930044, CODE_FOR_cond_addvnx16qi },
  { 0x930046, CODE_FOR_cond_addvnx8hi },
  { 0x930048, CODE_FOR_cond_addvnx4si },
  { 0x93004a, CODE_FOR_cond_addvnx2di },
  { 0x93005b, CODE_FOR_cond_addvnx2qi },
  { 0x93005c, CODE_FOR_cond_addvnx4qi },
  { 0x93005d, CODE_FOR_cond_addvnx2hi },
  { 0x93005e, CODE_FOR_cond_addvnx8qi },
  { 0x93005f, CODE_FOR_cond_addvnx4hi },
  { 0x930060, CODE_FOR_cond_addvnx2si },
  { 0x930069, CODE_FOR_cond_addvnx8hf },
  { 0x93006b, CODE_FOR_cond_addvnx4sf },
  { 0x93006d, CODE_FOR_cond_addvnx2df },
  { 0x940044, CODE_FOR_cond_subvnx16qi },
  { 0x940046, CODE_FOR_cond_subvnx8hi },
  { 0x940048, CODE_FOR_cond_subvnx4si },
  { 0x94004a, CODE_FOR_cond_subvnx2di },
  { 0x94005b, CODE_FOR_cond_subvnx2qi },
  { 0x94005c, CODE_FOR_cond_subvnx4qi },
  { 0x94005d, CODE_FOR_cond_subvnx2hi },
  { 0x94005e, CODE_FOR_cond_subvnx8qi },
  { 0x94005f, CODE_FOR_cond_subvnx4hi },
  { 0x940060, CODE_FOR_cond_subvnx2si },
  { 0x940069, CODE_FOR_cond_subvnx8hf },
  { 0x94006b, CODE_FOR_cond_subvnx4sf },
  { 0x94006d, CODE_FOR_cond_subvnx2df },
  { 0x950044, CODE_FOR_cond_mulvnx16qi },
  { 0x950046, CODE_FOR_cond_mulvnx8hi },
  { 0x950048, CODE_FOR_cond_mulvnx4si },
  { 0x95004a, CODE_FOR_cond_mulvnx2di },
  { 0x95005b, CODE_FOR_cond_mulvnx2qi },
  { 0x95005c, CODE_FOR_cond_mulvnx4qi },
  { 0x95005d, CODE_FOR_cond_mulvnx2hi },
  { 0x95005e, CODE_FOR_cond_mulvnx8qi },
  { 0x95005f, CODE_FOR_cond_mulvnx4hi },
  { 0x950060, CODE_FOR_cond_mulvnx2si },
  { 0x950069, CODE_FOR_cond_mulvnx8hf },
  { 0x95006b, CODE_FOR_cond_mulvnx4sf },
  { 0x95006d, CODE_FOR_cond_mulvnx2df },
  { 0x960048, CODE_FOR_cond_divvnx4si },
  { 0x96004a, CODE_FOR_cond_divvnx2di },
  { 0x960069, CODE_FOR_cond_divvnx8hf },
  { 0x96006b, CODE_FOR_cond_divvnx4sf },
  { 0x96006d, CODE_FOR_cond_divvnx2df },
  { 0x980048, CODE_FOR_cond_udivvnx4si },
  { 0x98004a, CODE_FOR_cond_udivvnx2di },
  { 0x9a0044, CODE_FOR_cond_andvnx16qi },
  { 0x9a0046, CODE_FOR_cond_andvnx8hi },
  { 0x9a0048, CODE_FOR_cond_andvnx4si },
  { 0x9a004a, CODE_FOR_cond_andvnx2di },
  { 0x9a005b, CODE_FOR_cond_andvnx2qi },
  { 0x9a005c, CODE_FOR_cond_andvnx4qi },
  { 0x9a005d, CODE_FOR_cond_andvnx2hi },
  { 0x9a005e, CODE_FOR_cond_andvnx8qi },
  { 0x9a005f, CODE_FOR_cond_andvnx4hi },
  { 0x9a0060, CODE_FOR_cond_andvnx2si },
  { 0x9b0044, CODE_FOR_cond_iorvnx16qi },
  { 0x9b0046, CODE_FOR_cond_iorvnx8hi },
  { 0x9b0048, CODE_FOR_cond_iorvnx4si },
  { 0x9b004a, CODE_FOR_cond_iorvnx2di },
  { 0x9b005b, CODE_FOR_cond_iorvnx2qi },
  { 0x9b005c, CODE_FOR_cond_iorvnx4qi },
  { 0x9b005d, CODE_FOR_cond_iorvnx2hi },
  { 0x9b005e, CODE_FOR_cond_iorvnx8qi },
  { 0x9b005f, CODE_FOR_cond_iorvnx4hi },
  { 0x9b0060, CODE_FOR_cond_iorvnx2si },
  { 0x9c0044, CODE_FOR_cond_xorvnx16qi },
  { 0x9c0046, CODE_FOR_cond_xorvnx8hi },
  { 0x9c0048, CODE_FOR_cond_xorvnx4si },
  { 0x9c004a, CODE_FOR_cond_xorvnx2di },
  { 0x9c005b, CODE_FOR_cond_xorvnx2qi },
  { 0x9c005c, CODE_FOR_cond_xorvnx4qi },
  { 0x9c005d, CODE_FOR_cond_xorvnx2hi },
  { 0x9c005e, CODE_FOR_cond_xorvnx8qi },
  { 0x9c005f, CODE_FOR_cond_xorvnx4hi },
  { 0x9c0060, CODE_FOR_cond_xorvnx2si },
  { 0x9d0044, CODE_FOR_cond_ashlvnx16qi },
  { 0x9d0046, CODE_FOR_cond_ashlvnx8hi },
  { 0x9d0048, CODE_FOR_cond_ashlvnx4si },
  { 0x9d004a, CODE_FOR_cond_ashlvnx2di },
  { 0x9d005b, CODE_FOR_cond_ashlvnx2qi },
  { 0x9d005c, CODE_FOR_cond_ashlvnx4qi },
  { 0x9d005d, CODE_FOR_cond_ashlvnx2hi },
  { 0x9d005e, CODE_FOR_cond_ashlvnx8qi },
  { 0x9d005f, CODE_FOR_cond_ashlvnx4hi },
  { 0x9d0060, CODE_FOR_cond_ashlvnx2si },
  { 0x9e0044, CODE_FOR_cond_ashrvnx16qi },
  { 0x9e0046, CODE_FOR_cond_ashrvnx8hi },
  { 0x9e0048, CODE_FOR_cond_ashrvnx4si },
  { 0x9e004a, CODE_FOR_cond_ashrvnx2di },
  { 0x9e005b, CODE_FOR_cond_ashrvnx2qi },
  { 0x9e005c, CODE_FOR_cond_ashrvnx4qi },
  { 0x9e005d, CODE_FOR_cond_ashrvnx2hi },
  { 0x9e005e, CODE_FOR_cond_ashrvnx8qi },
  { 0x9e005f, CODE_FOR_cond_ashrvnx4hi },
  { 0x9e0060, CODE_FOR_cond_ashrvnx2si },
  { 0x9f0044, CODE_FOR_cond_lshrvnx16qi },
  { 0x9f0046, CODE_FOR_cond_lshrvnx8hi },
  { 0x9f0048, CODE_FOR_cond_lshrvnx4si },
  { 0x9f004a, CODE_FOR_cond_lshrvnx2di },
  { 0x9f005b, CODE_FOR_cond_lshrvnx2qi },
  { 0x9f005c, CODE_FOR_cond_lshrvnx4qi },
  { 0x9f005d, CODE_FOR_cond_lshrvnx2hi },
  { 0x9f005e, CODE_FOR_cond_lshrvnx8qi },
  { 0x9f005f, CODE_FOR_cond_lshrvnx4hi },
  { 0x9f0060, CODE_FOR_cond_lshrvnx2si },
  { 0xa00044, CODE_FOR_cond_sminvnx16qi },
  { 0xa00046, CODE_FOR_cond_sminvnx8hi },
  { 0xa00048, CODE_FOR_cond_sminvnx4si },
  { 0xa0004a, CODE_FOR_cond_sminvnx2di },
  { 0xa0005b, CODE_FOR_cond_sminvnx2qi },
  { 0xa0005c, CODE_FOR_cond_sminvnx4qi },
  { 0xa0005d, CODE_FOR_cond_sminvnx2hi },
  { 0xa0005e, CODE_FOR_cond_sminvnx8qi },
  { 0xa0005f, CODE_FOR_cond_sminvnx4hi },
  { 0xa00060, CODE_FOR_cond_sminvnx2si },
  { 0xa00069, CODE_FOR_cond_sminvnx8hf },
  { 0xa0006b, CODE_FOR_cond_sminvnx4sf },
  { 0xa0006d, CODE_FOR_cond_sminvnx2df },
  { 0xa10044, CODE_FOR_cond_smaxvnx16qi },
  { 0xa10046, CODE_FOR_cond_smaxvnx8hi },
  { 0xa10048, CODE_FOR_cond_smaxvnx4si },
  { 0xa1004a, CODE_FOR_cond_smaxvnx2di },
  { 0xa1005b, CODE_FOR_cond_smaxvnx2qi },
  { 0xa1005c, CODE_FOR_cond_smaxvnx4qi },
  { 0xa1005d, CODE_FOR_cond_smaxvnx2hi },
  { 0xa1005e, CODE_FOR_cond_smaxvnx8qi },
  { 0xa1005f, CODE_FOR_cond_smaxvnx4hi },
  { 0xa10060, CODE_FOR_cond_smaxvnx2si },
  { 0xa10069, CODE_FOR_cond_smaxvnx8hf },
  { 0xa1006b, CODE_FOR_cond_smaxvnx4sf },
  { 0xa1006d, CODE_FOR_cond_smaxvnx2df },
  { 0xa20044, CODE_FOR_cond_uminvnx16qi },
  { 0xa20046, CODE_FOR_cond_uminvnx8hi },
  { 0xa20048, CODE_FOR_cond_uminvnx4si },
  { 0xa2004a, CODE_FOR_cond_uminvnx2di },
  { 0xa2005b, CODE_FOR_cond_uminvnx2qi },
  { 0xa2005c, CODE_FOR_cond_uminvnx4qi },
  { 0xa2005d, CODE_FOR_cond_uminvnx2hi },
  { 0xa2005e, CODE_FOR_cond_uminvnx8qi },
  { 0xa2005f, CODE_FOR_cond_uminvnx4hi },
  { 0xa20060, CODE_FOR_cond_uminvnx2si },
  { 0xa30044, CODE_FOR_cond_umaxvnx16qi },
  { 0xa30046, CODE_FOR_cond_umaxvnx8hi },
  { 0xa30048, CODE_FOR_cond_umaxvnx4si },
  { 0xa3004a, CODE_FOR_cond_umaxvnx2di },
  { 0xa3005b, CODE_FOR_cond_umaxvnx2qi },
  { 0xa3005c, CODE_FOR_cond_umaxvnx4qi },
  { 0xa3005d, CODE_FOR_cond_umaxvnx2hi },
  { 0xa3005e, CODE_FOR_cond_umaxvnx8qi },
  { 0xa3005f, CODE_FOR_cond_umaxvnx4hi },
  { 0xa30060, CODE_FOR_cond_umaxvnx2si },
  { 0xa40044, CODE_FOR_cond_fmavnx16qi },
  { 0xa40046, CODE_FOR_cond_fmavnx8hi },
  { 0xa40048, CODE_FOR_cond_fmavnx4si },
  { 0xa4004a, CODE_FOR_cond_fmavnx2di },
  { 0xa4005b, CODE_FOR_cond_fmavnx2qi },
  { 0xa4005c, CODE_FOR_cond_fmavnx4qi },
  { 0xa4005d, CODE_FOR_cond_fmavnx2hi },
  { 0xa4005e, CODE_FOR_cond_fmavnx8qi },
  { 0xa4005f, CODE_FOR_cond_fmavnx4hi },
  { 0xa40060, CODE_FOR_cond_fmavnx2si },
  { 0xa40069, CODE_FOR_cond_fmavnx8hf },
  { 0xa4006b, CODE_FOR_cond_fmavnx4sf },
  { 0xa4006d, CODE_FOR_cond_fmavnx2df },
  { 0xa50069, CODE_FOR_cond_fmsvnx8hf },
  { 0xa5006b, CODE_FOR_cond_fmsvnx4sf },
  { 0xa5006d, CODE_FOR_cond_fmsvnx2df },
  { 0xa60044, CODE_FOR_cond_fnmavnx16qi },
  { 0xa60046, CODE_FOR_cond_fnmavnx8hi },
  { 0xa60048, CODE_FOR_cond_fnmavnx4si },
  { 0xa6004a, CODE_FOR_cond_fnmavnx2di },
  { 0xa6005b, CODE_FOR_cond_fnmavnx2qi },
  { 0xa6005c, CODE_FOR_cond_fnmavnx4qi },
  { 0xa6005d, CODE_FOR_cond_fnmavnx2hi },
  { 0xa6005e, CODE_FOR_cond_fnmavnx8qi },
  { 0xa6005f, CODE_FOR_cond_fnmavnx4hi },
  { 0xa60060, CODE_FOR_cond_fnmavnx2si },
  { 0xa60069, CODE_FOR_cond_fnmavnx8hf },
  { 0xa6006b, CODE_FOR_cond_fnmavnx4sf },
  { 0xa6006d, CODE_FOR_cond_fnmavnx2df },
  { 0xa70069, CODE_FOR_cond_fnmsvnx8hf },
  { 0xa7006b, CODE_FOR_cond_fnmsvnx4sf },
  { 0xa7006d, CODE_FOR_cond_fnmsvnx2df },
  { 0xa8000f, CODE_FOR_cmovsi6 },
  { 0xa80010, CODE_FOR_cmovdi6 },
  { 0xa80029, CODE_FOR_cmovsf6 },
  { 0xa8002a, CODE_FOR_cmovdf6 },
  { 0xa90002, CODE_FOR_cstorecc4 },
  { 0xa9000f, CODE_FOR_cstoresi4 },
  { 0xa90010, CODE_FOR_cstoredi4 },
  { 0xa90029, CODE_FOR_cstoresf4 },
  { 0xa9002a, CODE_FOR_cstoredf4 },
  { 0xab000f, CODE_FOR_addvsi4 },
  { 0xab0010, CODE_FOR_addvdi4 },
  { 0xab0011, CODE_FOR_addvti4 },
  { 0xac000f, CODE_FOR_subvsi4 },
  { 0xac0010, CODE_FOR_subvdi4 },
  { 0xac0011, CODE_FOR_subvti4 },
  { 0xae000f, CODE_FOR_uaddvsi4 },
  { 0xae0010, CODE_FOR_uaddvdi4 },
  { 0xae0011, CODE_FOR_uaddvti4 },
  { 0xaf000f, CODE_FOR_usubvsi4 },
  { 0xaf0010, CODE_FOR_usubvdi4 },
  { 0xaf0011, CODE_FOR_usubvti4 },
  { 0xb1000f, CODE_FOR_negvsi3 },
  { 0xb10010, CODE_FOR_negvdi3 },
  { 0xb10011, CODE_FOR_negvti3 },
  { 0xb30010, CODE_FOR_smuldi3_highpart },
  { 0xb30044, CODE_FOR_smulvnx16qi3_highpart },
  { 0xb30046, CODE_FOR_smulvnx8hi3_highpart },
  { 0xb30048, CODE_FOR_smulvnx4si3_highpart },
  { 0xb3004a, CODE_FOR_smulvnx2di3_highpart },
  { 0xb3005b, CODE_FOR_smulvnx2qi3_highpart },
  { 0xb3005c, CODE_FOR_smulvnx4qi3_highpart },
  { 0xb3005d, CODE_FOR_smulvnx2hi3_highpart },
  { 0xb3005e, CODE_FOR_smulvnx8qi3_highpart },
  { 0xb3005f, CODE_FOR_smulvnx4hi3_highpart },
  { 0xb30060, CODE_FOR_smulvnx2si3_highpart },
  { 0xb40010, CODE_FOR_umuldi3_highpart },
  { 0xb40044, CODE_FOR_umulvnx16qi3_highpart },
  { 0xb40046, CODE_FOR_umulvnx8hi3_highpart },
  { 0xb40048, CODE_FOR_umulvnx4si3_highpart },
  { 0xb4004a, CODE_FOR_umulvnx2di3_highpart },
  { 0xb4005b, CODE_FOR_umulvnx2qi3_highpart },
  { 0xb4005c, CODE_FOR_umulvnx4qi3_highpart },
  { 0xb4005d, CODE_FOR_umulvnx2hi3_highpart },
  { 0xb4005e, CODE_FOR_umulvnx8qi3_highpart },
  { 0xb4005f, CODE_FOR_umulvnx4hi3_highpart },
  { 0xb40060, CODE_FOR_umulvnx2si3_highpart },
  { 0xb80010, CODE_FOR_cpymemdi },
  { 0xba0010, CODE_FOR_setmemdi },
  { 0xbc0027, CODE_FOR_fmahf4 },
  { 0xbc0029, CODE_FOR_fmasf4 },
  { 0xbc002a, CODE_FOR_fmadf4 },
  { 0xbc0044, CODE_FOR_fmavnx16qi4 },
  { 0xbc0046, CODE_FOR_fmavnx8hi4 },
  { 0xbc0048, CODE_FOR_fmavnx4si4 },
  { 0xbc004a, CODE_FOR_fmavnx2di4 },
  { 0xbc005b, CODE_FOR_fmavnx2qi4 },
  { 0xbc005c, CODE_FOR_fmavnx4qi4 },
  { 0xbc005d, CODE_FOR_fmavnx2hi4 },
  { 0xbc005e, CODE_FOR_fmavnx8qi4 },
  { 0xbc005f, CODE_FOR_fmavnx4hi4 },
  { 0xbc0060, CODE_FOR_fmavnx2si4 },
  { 0xbc0063, CODE_FOR_fmav4hf4 },
  { 0xbc0064, CODE_FOR_fmav2sf4 },
  { 0xbc0067, CODE_FOR_fmav8hf4 },
  { 0xbc0069, CODE_FOR_fmavnx8hf4 },
  { 0xbc006a, CODE_FOR_fmav4sf4 },
  { 0xbc006b, CODE_FOR_fmavnx4sf4 },
  { 0xbc006c, CODE_FOR_fmav2df4 },
  { 0xbc006d, CODE_FOR_fmavnx2df4 },
  { 0xbd0029, CODE_FOR_fmssf4 },
  { 0xbd002a, CODE_FOR_fmsdf4 },
  { 0xbd0069, CODE_FOR_fmsvnx8hf4 },
  { 0xbd006b, CODE_FOR_fmsvnx4sf4 },
  { 0xbd006d, CODE_FOR_fmsvnx2df4 },
  { 0xbe0027, CODE_FOR_fnmahf4 },
  { 0xbe0029, CODE_FOR_fnmasf4 },
  { 0xbe002a, CODE_FOR_fnmadf4 },
  { 0xbe0044, CODE_FOR_fnmavnx16qi4 },
  { 0xbe0046, CODE_FOR_fnmavnx8hi4 },
  { 0xbe0048, CODE_FOR_fnmavnx4si4 },
  { 0xbe004a, CODE_FOR_fnmavnx2di4 },
  { 0xbe005b, CODE_FOR_fnmavnx2qi4 },
  { 0xbe005c, CODE_FOR_fnmavnx4qi4 },
  { 0xbe005d, CODE_FOR_fnmavnx2hi4 },
  { 0xbe005e, CODE_FOR_fnmavnx8qi4 },
  { 0xbe005f, CODE_FOR_fnmavnx4hi4 },
  { 0xbe0060, CODE_FOR_fnmavnx2si4 },
  { 0xbe0063, CODE_FOR_fnmav4hf4 },
  { 0xbe0064, CODE_FOR_fnmav2sf4 },
  { 0xbe0067, CODE_FOR_fnmav8hf4 },
  { 0xbe0069, CODE_FOR_fnmavnx8hf4 },
  { 0xbe006a, CODE_FOR_fnmav4sf4 },
  { 0xbe006b, CODE_FOR_fnmavnx4sf4 },
  { 0xbe006c, CODE_FOR_fnmav2df4 },
  { 0xbe006d, CODE_FOR_fnmavnx2df4 },
  { 0xbf0029, CODE_FOR_fnmssf4 },
  { 0xbf002a, CODE_FOR_fnmsdf4 },
  { 0xbf0069, CODE_FOR_fnmsvnx8hf4 },
  { 0xbf006b, CODE_FOR_fnmsvnx4sf4 },
  { 0xbf006d, CODE_FOR_fnmsvnx2df4 },
  { 0xc00027, CODE_FOR_rinthf2 },
  { 0xc00029, CODE_FOR_rintsf2 },
  { 0xc0002a, CODE_FOR_rintdf2 },
  { 0xc00063, CODE_FOR_rintv4hf2 },
  { 0xc00064, CODE_FOR_rintv2sf2 },
  { 0xc00067, CODE_FOR_rintv8hf2 },
  { 0xc00069, CODE_FOR_rintvnx8hf2 },
  { 0xc0006a, CODE_FOR_rintv4sf2 },
  { 0xc0006b, CODE_FOR_rintvnx4sf2 },
  { 0xc0006c, CODE_FOR_rintv2df2 },
  { 0xc0006d, CODE_FOR_rintvnx2df2 },
  { 0xc10027, CODE_FOR_roundhf2 },
  { 0xc10029, CODE_FOR_roundsf2 },
  { 0xc1002a, CODE_FOR_rounddf2 },
  { 0xc10063, CODE_FOR_roundv4hf2 },
  { 0xc10064, CODE_FOR_roundv2sf2 },
  { 0xc10067, CODE_FOR_roundv8hf2 },
  { 0xc10069, CODE_FOR_roundvnx8hf2 },
  { 0xc1006a, CODE_FOR_roundv4sf2 },
  { 0xc1006b, CODE_FOR_roundvnx4sf2 },
  { 0xc1006c, CODE_FOR_roundv2df2 },
  { 0xc1006d, CODE_FOR_roundvnx2df2 },
  { 0xc30027, CODE_FOR_floorhf2 },
  { 0xc30029, CODE_FOR_floorsf2 },
  { 0xc3002a, CODE_FOR_floordf2 },
  { 0xc30063, CODE_FOR_floorv4hf2 },
  { 0xc30064, CODE_FOR_floorv2sf2 },
  { 0xc30067, CODE_FOR_floorv8hf2 },
  { 0xc30069, CODE_FOR_floorvnx8hf2 },
  { 0xc3006a, CODE_FOR_floorv4sf2 },
  { 0xc3006b, CODE_FOR_floorvnx4sf2 },
  { 0xc3006c, CODE_FOR_floorv2df2 },
  { 0xc3006d, CODE_FOR_floorvnx2df2 },
  { 0xc40027, CODE_FOR_ceilhf2 },
  { 0xc40029, CODE_FOR_ceilsf2 },
  { 0xc4002a, CODE_FOR_ceildf2 },
  { 0xc40063, CODE_FOR_ceilv4hf2 },
  { 0xc40064, CODE_FOR_ceilv2sf2 },
  { 0xc40067, CODE_FOR_ceilv8hf2 },
  { 0xc40069, CODE_FOR_ceilvnx8hf2 },
  { 0xc4006a, CODE_FOR_ceilv4sf2 },
  { 0xc4006b, CODE_FOR_ceilvnx4sf2 },
  { 0xc4006c, CODE_FOR_ceilv2df2 },
  { 0xc4006d, CODE_FOR_ceilvnx2df2 },
  { 0xc50027, CODE_FOR_btrunchf2 },
  { 0xc50029, CODE_FOR_btruncsf2 },
  { 0xc5002a, CODE_FOR_btruncdf2 },
  { 0xc50063, CODE_FOR_btruncv4hf2 },
  { 0xc50064, CODE_FOR_btruncv2sf2 },
  { 0xc50067, CODE_FOR_btruncv8hf2 },
  { 0xc50069, CODE_FOR_btruncvnx8hf2 },
  { 0xc5006a, CODE_FOR_btruncv4sf2 },
  { 0xc5006b, CODE_FOR_btruncvnx4sf2 },
  { 0xc5006c, CODE_FOR_btruncv2df2 },
  { 0xc5006d, CODE_FOR_btruncvnx2df2 },
  { 0xc60027, CODE_FOR_nearbyinthf2 },
  { 0xc60029, CODE_FOR_nearbyintsf2 },
  { 0xc6002a, CODE_FOR_nearbyintdf2 },
  { 0xc60063, CODE_FOR_nearbyintv4hf2 },
  { 0xc60064, CODE_FOR_nearbyintv2sf2 },
  { 0xc60067, CODE_FOR_nearbyintv8hf2 },
  { 0xc60069, CODE_FOR_nearbyintvnx8hf2 },
  { 0xc6006a, CODE_FOR_nearbyintv4sf2 },
  { 0xc6006b, CODE_FOR_nearbyintvnx4sf2 },
  { 0xc6006c, CODE_FOR_nearbyintv2df2 },
  { 0xc6006d, CODE_FOR_nearbyintvnx2df2 },
  { 0xce0029, CODE_FOR_copysignsf3 },
  { 0xce002a, CODE_FOR_copysigndf3 },
  { 0xce0063, CODE_FOR_copysignv4hf3 },
  { 0xce0064, CODE_FOR_copysignv2sf3 },
  { 0xce0067, CODE_FOR_copysignv8hf3 },
  { 0xce0069, CODE_FOR_copysignvnx8hf3 },
  { 0xce006a, CODE_FOR_copysignv4sf3 },
  { 0xce006b, CODE_FOR_copysignvnx4sf3 },
  { 0xce006c, CODE_FOR_copysignv2df3 },
  { 0xce006d, CODE_FOR_copysignvnx2df3 },
  { 0xcf0029, CODE_FOR_xorsignsf3 },
  { 0xcf002a, CODE_FOR_xorsigndf3 },
  { 0xcf0063, CODE_FOR_xorsignv4hf3 },
  { 0xcf0064, CODE_FOR_xorsignv2sf3 },
  { 0xcf0067, CODE_FOR_xorsignv8hf3 },
  { 0xcf0069, CODE_FOR_xorsignvnx8hf3 },
  { 0xcf006a, CODE_FOR_xorsignv4sf3 },
  { 0xcf006b, CODE_FOR_xorsignvnx4sf3 },
  { 0xcf006c, CODE_FOR_xorsignv2df3 },
  { 0xcf006d, CODE_FOR_xorsignvnx2df3 },
  { 0xd00044, CODE_FOR_cadd90vnx16qi3 },
  { 0xd00046, CODE_FOR_cadd90vnx8hi3 },
  { 0xd00048, CODE_FOR_cadd90vnx4si3 },
  { 0xd0004a, CODE_FOR_cadd90vnx2di3 },
  { 0xd00063, CODE_FOR_cadd90v4hf3 },
  { 0xd00064, CODE_FOR_cadd90v2sf3 },
  { 0xd00067, CODE_FOR_cadd90v8hf3 },
  { 0xd00069, CODE_FOR_cadd90vnx8hf3 },
  { 0xd0006a, CODE_FOR_cadd90v4sf3 },
  { 0xd0006b, CODE_FOR_cadd90vnx4sf3 },
  { 0xd0006c, CODE_FOR_cadd90v2df3 },
  { 0xd0006d, CODE_FOR_cadd90vnx2df3 },
  { 0xd10044, CODE_FOR_cadd270vnx16qi3 },
  { 0xd10046, CODE_FOR_cadd270vnx8hi3 },
  { 0xd10048, CODE_FOR_cadd270vnx4si3 },
  { 0xd1004a, CODE_FOR_cadd270vnx2di3 },
  { 0xd10063, CODE_FOR_cadd270v4hf3 },
  { 0xd10064, CODE_FOR_cadd270v2sf3 },
  { 0xd10067, CODE_FOR_cadd270v8hf3 },
  { 0xd10069, CODE_FOR_cadd270vnx8hf3 },
  { 0xd1006a, CODE_FOR_cadd270v4sf3 },
  { 0xd1006b, CODE_FOR_cadd270vnx4sf3 },
  { 0xd1006c, CODE_FOR_cadd270v2df3 },
  { 0xd1006d, CODE_FOR_cadd270vnx2df3 },
  { 0xd20044, CODE_FOR_cmulvnx16qi3 },
  { 0xd20046, CODE_FOR_cmulvnx8hi3 },
  { 0xd20048, CODE_FOR_cmulvnx4si3 },
  { 0xd2004a, CODE_FOR_cmulvnx2di3 },
  { 0xd20063, CODE_FOR_cmulv4hf3 },
  { 0xd20064, CODE_FOR_cmulv2sf3 },
  { 0xd20067, CODE_FOR_cmulv8hf3 },
  { 0xd20069, CODE_FOR_cmulvnx8hf3 },
  { 0xd2006a, CODE_FOR_cmulv4sf3 },
  { 0xd2006b, CODE_FOR_cmulvnx4sf3 },
  { 0xd2006c, CODE_FOR_cmulv2df3 },
  { 0xd2006d, CODE_FOR_cmulvnx2df3 },
  { 0xd30044, CODE_FOR_cmul_conjvnx16qi3 },
  { 0xd30046, CODE_FOR_cmul_conjvnx8hi3 },
  { 0xd30048, CODE_FOR_cmul_conjvnx4si3 },
  { 0xd3004a, CODE_FOR_cmul_conjvnx2di3 },
  { 0xd30063, CODE_FOR_cmul_conjv4hf3 },
  { 0xd30064, CODE_FOR_cmul_conjv2sf3 },
  { 0xd30067, CODE_FOR_cmul_conjv8hf3 },
  { 0xd30069, CODE_FOR_cmul_conjvnx8hf3 },
  { 0xd3006a, CODE_FOR_cmul_conjv4sf3 },
  { 0xd3006b, CODE_FOR_cmul_conjvnx4sf3 },
  { 0xd3006c, CODE_FOR_cmul_conjv2df3 },
  { 0xd3006d, CODE_FOR_cmul_conjvnx2df3 },
  { 0xd40044, CODE_FOR_cmlavnx16qi4 },
  { 0xd40046, CODE_FOR_cmlavnx8hi4 },
  { 0xd40048, CODE_FOR_cmlavnx4si4 },
  { 0xd4004a, CODE_FOR_cmlavnx2di4 },
  { 0xd40063, CODE_FOR_cmlav4hf4 },
  { 0xd40064, CODE_FOR_cmlav2sf4 },
  { 0xd40067, CODE_FOR_cmlav8hf4 },
  { 0xd40069, CODE_FOR_cmlavnx8hf4 },
  { 0xd4006a, CODE_FOR_cmlav4sf4 },
  { 0xd4006b, CODE_FOR_cmlavnx4sf4 },
  { 0xd4006c, CODE_FOR_cmlav2df4 },
  { 0xd4006d, CODE_FOR_cmlavnx2df4 },
  { 0xd50044, CODE_FOR_cmla_conjvnx16qi4 },
  { 0xd50046, CODE_FOR_cmla_conjvnx8hi4 },
  { 0xd50048, CODE_FOR_cmla_conjvnx4si4 },
  { 0xd5004a, CODE_FOR_cmla_conjvnx2di4 },
  { 0xd50063, CODE_FOR_cmla_conjv4hf4 },
  { 0xd50064, CODE_FOR_cmla_conjv2sf4 },
  { 0xd50067, CODE_FOR_cmla_conjv8hf4 },
  { 0xd50069, CODE_FOR_cmla_conjvnx8hf4 },
  { 0xd5006a, CODE_FOR_cmla_conjv4sf4 },
  { 0xd5006b, CODE_FOR_cmla_conjvnx4sf4 },
  { 0xd5006c, CODE_FOR_cmla_conjv2df4 },
  { 0xd5006d, CODE_FOR_cmla_conjvnx2df4 },
  { 0xd60044, CODE_FOR_cmlsvnx16qi4 },
  { 0xd60046, CODE_FOR_cmlsvnx8hi4 },
  { 0xd60048, CODE_FOR_cmlsvnx4si4 },
  { 0xd6004a, CODE_FOR_cmlsvnx2di4 },
  { 0xd60063, CODE_FOR_cmlsv4hf4 },
  { 0xd60064, CODE_FOR_cmlsv2sf4 },
  { 0xd60067, CODE_FOR_cmlsv8hf4 },
  { 0xd60069, CODE_FOR_cmlsvnx8hf4 },
  { 0xd6006a, CODE_FOR_cmlsv4sf4 },
  { 0xd6006b, CODE_FOR_cmlsvnx4sf4 },
  { 0xd6006c, CODE_FOR_cmlsv2df4 },
  { 0xd6006d, CODE_FOR_cmlsvnx2df4 },
  { 0xd70044, CODE_FOR_cmls_conjvnx16qi4 },
  { 0xd70046, CODE_FOR_cmls_conjvnx8hi4 },
  { 0xd70048, CODE_FOR_cmls_conjvnx4si4 },
  { 0xd7004a, CODE_FOR_cmls_conjvnx2di4 },
  { 0xd70063, CODE_FOR_cmls_conjv4hf4 },
  { 0xd70064, CODE_FOR_cmls_conjv2sf4 },
  { 0xd70067, CODE_FOR_cmls_conjv8hf4 },
  { 0xd70069, CODE_FOR_cmls_conjvnx8hf4 },
  { 0xd7006a, CODE_FOR_cmls_conjv4sf4 },
  { 0xd7006b, CODE_FOR_cmls_conjvnx4sf4 },
  { 0xd7006c, CODE_FOR_cmls_conjv2df4 },
  { 0xd7006d, CODE_FOR_cmls_conjvnx2df4 },
  { 0xea0029, CODE_FOR_rsqrtsf2 },
  { 0xea002a, CODE_FOR_rsqrtdf2 },
  { 0xea0064, CODE_FOR_rsqrtv2sf2 },
  { 0xea006a, CODE_FOR_rsqrtv4sf2 },
  { 0xea006b, CODE_FOR_rsqrtvnx4sf2 },
  { 0xea006c, CODE_FOR_rsqrtv2df2 },
  { 0xea006d, CODE_FOR_rsqrtvnx2df2 },
  { 0xec0064, CODE_FOR_signbitv2sf2 },
  { 0xec006a, CODE_FOR_signbitv4sf2 },
  { 0xf30027, CODE_FOR_fmaxhf3 },
  { 0xf30029, CODE_FOR_fmaxsf3 },
  { 0xf3002a, CODE_FOR_fmaxdf3 },
  { 0xf30063, CODE_FOR_fmaxv4hf3 },
  { 0xf30064, CODE_FOR_fmaxv2sf3 },
  { 0xf30067, CODE_FOR_fmaxv8hf3 },
  { 0xf30069, CODE_FOR_fmaxvnx8hf3 },
  { 0xf3006a, CODE_FOR_fmaxv4sf3 },
  { 0xf3006b, CODE_FOR_fmaxvnx4sf3 },
  { 0xf3006c, CODE_FOR_fmaxv2df3 },
  { 0xf3006d, CODE_FOR_fmaxvnx2df3 },
  { 0xf40027, CODE_FOR_fminhf3 },
  { 0xf40029, CODE_FOR_fminsf3 },
  { 0xf4002a, CODE_FOR_fmindf3 },
  { 0xf40063, CODE_FOR_fminv4hf3 },
  { 0xf40064, CODE_FOR_fminv2sf3 },
  { 0xf40067, CODE_FOR_fminv8hf3 },
  { 0xf40069, CODE_FOR_fminvnx8hf3 },
  { 0xf4006a, CODE_FOR_fminv4sf3 },
  { 0xf4006b, CODE_FOR_fminvnx4sf3 },
  { 0xf4006c, CODE_FOR_fminv2df3 },
  { 0xf4006d, CODE_FOR_fminvnx2df3 },
  { 0xf50040, CODE_FOR_reduc_smax_scal_v8qi },
  { 0xf50041, CODE_FOR_reduc_smax_scal_v4hi },
  { 0xf50042, CODE_FOR_reduc_smax_scal_v2si },
  { 0xf50043, CODE_FOR_reduc_smax_scal_v16qi },
  { 0xf50044, CODE_FOR_reduc_smax_scal_vnx16qi },
  { 0xf50045, CODE_FOR_reduc_smax_scal_v8hi },
  { 0xf50046, CODE_FOR_reduc_smax_scal_vnx8hi },
  { 0xf50047, CODE_FOR_reduc_smax_scal_v4si },
  { 0xf50048, CODE_FOR_reduc_smax_scal_vnx4si },
  { 0xf5004a, CODE_FOR_reduc_smax_scal_vnx2di },
  { 0xf50063, CODE_FOR_reduc_smax_scal_v4hf },
  { 0xf50064, CODE_FOR_reduc_smax_scal_v2sf },
  { 0xf50067, CODE_FOR_reduc_smax_scal_v8hf },
  { 0xf50069, CODE_FOR_reduc_smax_scal_vnx8hf },
  { 0xf5006a, CODE_FOR_reduc_smax_scal_v4sf },
  { 0xf5006b, CODE_FOR_reduc_smax_scal_vnx4sf },
  { 0xf5006c, CODE_FOR_reduc_smax_scal_v2df },
  { 0xf5006d, CODE_FOR_reduc_smax_scal_vnx2df },
  { 0xf60040, CODE_FOR_reduc_smin_scal_v8qi },
  { 0xf60041, CODE_FOR_reduc_smin_scal_v4hi },
  { 0xf60042, CODE_FOR_reduc_smin_scal_v2si },
  { 0xf60043, CODE_FOR_reduc_smin_scal_v16qi },
  { 0xf60044, CODE_FOR_reduc_smin_scal_vnx16qi },
  { 0xf60045, CODE_FOR_reduc_smin_scal_v8hi },
  { 0xf60046, CODE_FOR_reduc_smin_scal_vnx8hi },
  { 0xf60047, CODE_FOR_reduc_smin_scal_v4si },
  { 0xf60048, CODE_FOR_reduc_smin_scal_vnx4si },
  { 0xf6004a, CODE_FOR_reduc_smin_scal_vnx2di },
  { 0xf60063, CODE_FOR_reduc_smin_scal_v4hf },
  { 0xf60064, CODE_FOR_reduc_smin_scal_v2sf },
  { 0xf60067, CODE_FOR_reduc_smin_scal_v8hf },
  { 0xf60069, CODE_FOR_reduc_smin_scal_vnx8hf },
  { 0xf6006a, CODE_FOR_reduc_smin_scal_v4sf },
  { 0xf6006b, CODE_FOR_reduc_smin_scal_vnx4sf },
  { 0xf6006c, CODE_FOR_reduc_smin_scal_v2df },
  { 0xf6006d, CODE_FOR_reduc_smin_scal_vnx2df },
  { 0xf70040, CODE_FOR_reduc_plus_scal_v8qi },
  { 0xf70041, CODE_FOR_reduc_plus_scal_v4hi },
  { 0xf70042, CODE_FOR_reduc_plus_scal_v2si },
  { 0xf70043, CODE_FOR_reduc_plus_scal_v16qi },
  { 0xf70044, CODE_FOR_reduc_plus_scal_vnx16qi },
  { 0xf70045, CODE_FOR_reduc_plus_scal_v8hi },
  { 0xf70046, CODE_FOR_reduc_plus_scal_vnx8hi },
  { 0xf70047, CODE_FOR_reduc_plus_scal_v4si },
  { 0xf70048, CODE_FOR_reduc_plus_scal_vnx4si },
  { 0xf70049, CODE_FOR_reduc_plus_scal_v2di },
  { 0xf7004a, CODE_FOR_reduc_plus_scal_vnx2di },
  { 0xf70064, CODE_FOR_reduc_plus_scal_v2sf },
  { 0xf70069, CODE_FOR_reduc_plus_scal_vnx8hf },
  { 0xf7006a, CODE_FOR_reduc_plus_scal_v4sf },
  { 0xf7006b, CODE_FOR_reduc_plus_scal_vnx4sf },
  { 0xf7006c, CODE_FOR_reduc_plus_scal_v2df },
  { 0xf7006d, CODE_FOR_reduc_plus_scal_vnx2df },
  { 0xf80040, CODE_FOR_reduc_umax_scal_v8qi },
  { 0xf80041, CODE_FOR_reduc_umax_scal_v4hi },
  { 0xf80042, CODE_FOR_reduc_umax_scal_v2si },
  { 0xf80043, CODE_FOR_reduc_umax_scal_v16qi },
  { 0xf80044, CODE_FOR_reduc_umax_scal_vnx16qi },
  { 0xf80045, CODE_FOR_reduc_umax_scal_v8hi },
  { 0xf80046, CODE_FOR_reduc_umax_scal_vnx8hi },
  { 0xf80047, CODE_FOR_reduc_umax_scal_v4si },
  { 0xf80048, CODE_FOR_reduc_umax_scal_vnx4si },
  { 0xf8004a, CODE_FOR_reduc_umax_scal_vnx2di },
  { 0xf90040, CODE_FOR_reduc_umin_scal_v8qi },
  { 0xf90041, CODE_FOR_reduc_umin_scal_v4hi },
  { 0xf90042, CODE_FOR_reduc_umin_scal_v2si },
  { 0xf90043, CODE_FOR_reduc_umin_scal_v16qi },
  { 0xf90044, CODE_FOR_reduc_umin_scal_vnx16qi },
  { 0xf90045, CODE_FOR_reduc_umin_scal_v8hi },
  { 0xf90046, CODE_FOR_reduc_umin_scal_vnx8hi },
  { 0xf90047, CODE_FOR_reduc_umin_scal_v4si },
  { 0xf90048, CODE_FOR_reduc_umin_scal_vnx4si },
  { 0xf9004a, CODE_FOR_reduc_umin_scal_vnx2di },
  { 0xfa0044, CODE_FOR_reduc_and_scal_vnx16qi },
  { 0xfa0046, CODE_FOR_reduc_and_scal_vnx8hi },
  { 0xfa0048, CODE_FOR_reduc_and_scal_vnx4si },
  { 0xfa004a, CODE_FOR_reduc_and_scal_vnx2di },
  { 0xfb0044, CODE_FOR_reduc_ior_scal_vnx16qi },
  { 0xfb0046, CODE_FOR_reduc_ior_scal_vnx8hi },
  { 0xfb0048, CODE_FOR_reduc_ior_scal_vnx4si },
  { 0xfb004a, CODE_FOR_reduc_ior_scal_vnx2di },
  { 0xfc0044, CODE_FOR_reduc_xor_scal_vnx16qi },
  { 0xfc0046, CODE_FOR_reduc_xor_scal_vnx8hi },
  { 0xfc0048, CODE_FOR_reduc_xor_scal_vnx4si },
  { 0xfc004a, CODE_FOR_reduc_xor_scal_vnx2di },
  { 0xfd0069, CODE_FOR_fold_left_plus_vnx8hf },
  { 0xfd006b, CODE_FOR_fold_left_plus_vnx4sf },
  { 0xfd006d, CODE_FOR_fold_left_plus_vnx2df },
  { 0xfe0069, CODE_FOR_mask_fold_left_plus_vnx8hf },
  { 0xfe006b, CODE_FOR_mask_fold_left_plus_vnx4sf },
  { 0xfe006d, CODE_FOR_mask_fold_left_plus_vnx2df },
  { 0xff0044, CODE_FOR_extract_last_vnx16qi },
  { 0xff0046, CODE_FOR_extract_last_vnx8hi },
  { 0xff0048, CODE_FOR_extract_last_vnx4si },
  { 0xff004a, CODE_FOR_extract_last_vnx2di },
  { 0xff0068, CODE_FOR_extract_last_vnx8bf },
  { 0xff0069, CODE_FOR_extract_last_vnx8hf },
  { 0xff006b, CODE_FOR_extract_last_vnx4sf },
  { 0xff006d, CODE_FOR_extract_last_vnx2df },
  { 0x1000044, CODE_FOR_fold_extract_last_vnx16qi },
  { 0x1000046, CODE_FOR_fold_extract_last_vnx8hi },
  { 0x1000048, CODE_FOR_fold_extract_last_vnx4si },
  { 0x100004a, CODE_FOR_fold_extract_last_vnx2di },
  { 0x1000068, CODE_FOR_fold_extract_last_vnx8bf },
  { 0x1000069, CODE_FOR_fold_extract_last_vnx8hf },
  { 0x100006b, CODE_FOR_fold_extract_last_vnx4sf },
  { 0x100006d, CODE_FOR_fold_extract_last_vnx2df },
  { 0x1010040, CODE_FOR_avgv8qi3_floor },
  { 0x1010041, CODE_FOR_avgv4hi3_floor },
  { 0x1010042, CODE_FOR_avgv2si3_floor },
  { 0x1010043, CODE_FOR_avgv16qi3_floor },
  { 0x1010044, CODE_FOR_avgvnx16qi3_floor },
  { 0x1010045, CODE_FOR_avgv8hi3_floor },
  { 0x1010046, CODE_FOR_avgvnx8hi3_floor },
  { 0x1010047, CODE_FOR_avgv4si3_floor },
  { 0x1010048, CODE_FOR_avgvnx4si3_floor },
  { 0x101004a, CODE_FOR_avgvnx2di3_floor },
  { 0x1020040, CODE_FOR_uavgv8qi3_floor },
  { 0x1020041, CODE_FOR_uavgv4hi3_floor },
  { 0x1020042, CODE_FOR_uavgv2si3_floor },
  { 0x1020043, CODE_FOR_uavgv16qi3_floor },
  { 0x1020044, CODE_FOR_uavgvnx16qi3_floor },
  { 0x1020045, CODE_FOR_uavgv8hi3_floor },
  { 0x1020046, CODE_FOR_uavgvnx8hi3_floor },
  { 0x1020047, CODE_FOR_uavgv4si3_floor },
  { 0x1020048, CODE_FOR_uavgvnx4si3_floor },
  { 0x102004a, CODE_FOR_uavgvnx2di3_floor },
  { 0x1030040, CODE_FOR_avgv8qi3_ceil },
  { 0x1030041, CODE_FOR_avgv4hi3_ceil },
  { 0x1030042, CODE_FOR_avgv2si3_ceil },
  { 0x1030043, CODE_FOR_avgv16qi3_ceil },
  { 0x1030044, CODE_FOR_avgvnx16qi3_ceil },
  { 0x1030045, CODE_FOR_avgv8hi3_ceil },
  { 0x1030046, CODE_FOR_avgvnx8hi3_ceil },
  { 0x1030047, CODE_FOR_avgv4si3_ceil },
  { 0x1030048, CODE_FOR_avgvnx4si3_ceil },
  { 0x103004a, CODE_FOR_avgvnx2di3_ceil },
  { 0x1040040, CODE_FOR_uavgv8qi3_ceil },
  { 0x1040041, CODE_FOR_uavgv4hi3_ceil },
  { 0x1040042, CODE_FOR_uavgv2si3_ceil },
  { 0x1040043, CODE_FOR_uavgv16qi3_ceil },
  { 0x1040044, CODE_FOR_uavgvnx16qi3_ceil },
  { 0x1040045, CODE_FOR_uavgv8hi3_ceil },
  { 0x1040046, CODE_FOR_uavgvnx8hi3_ceil },
  { 0x1040047, CODE_FOR_uavgv4si3_ceil },
  { 0x1040048, CODE_FOR_uavgvnx4si3_ceil },
  { 0x104004a, CODE_FOR_uavgvnx2di3_ceil },
  { 0x1050040, CODE_FOR_sdot_prodv8qi },
  { 0x1050043, CODE_FOR_sdot_prodv16qi },
  { 0x1050044, CODE_FOR_sdot_prodvnx16qi },
  { 0x1050046, CODE_FOR_sdot_prodvnx8hi },
  { 0x1060040, CODE_FOR_widen_ssumv8qi3 },
  { 0x1060041, CODE_FOR_widen_ssumv4hi3 },
  { 0x1060042, CODE_FOR_widen_ssumv2si3 },
  { 0x1060043, CODE_FOR_widen_ssumv16qi3 },
  { 0x1060045, CODE_FOR_widen_ssumv8hi3 },
  { 0x1060047, CODE_FOR_widen_ssumv4si3 },
  { 0x1070040, CODE_FOR_udot_prodv8qi },
  { 0x1070043, CODE_FOR_udot_prodv16qi },
  { 0x1070044, CODE_FOR_udot_prodvnx16qi },
  { 0x1070046, CODE_FOR_udot_prodvnx8hi },
  { 0x1080040, CODE_FOR_widen_usumv8qi3 },
  { 0x1080041, CODE_FOR_widen_usumv4hi3 },
  { 0x1080042, CODE_FOR_widen_usumv2si3 },
  { 0x1080043, CODE_FOR_widen_usumv16qi3 },
  { 0x1080045, CODE_FOR_widen_usumv8hi3 },
  { 0x1080047, CODE_FOR_widen_usumv4si3 },
  { 0x1090043, CODE_FOR_usadv16qi },
  { 0x1090044, CODE_FOR_usadvnx16qi },
  { 0x1090046, CODE_FOR_usadvnx8hi },
  { 0x10a0043, CODE_FOR_ssadv16qi },
  { 0x10a0044, CODE_FOR_ssadvnx16qi },
  { 0x10a0046, CODE_FOR_ssadvnx8hi },
  { 0x10b0044, CODE_FOR_smulhsvnx16qi3 },
  { 0x10b0046, CODE_FOR_smulhsvnx8hi3 },
  { 0x10b0048, CODE_FOR_smulhsvnx4si3 },
  { 0x10c0044, CODE_FOR_smulhrsvnx16qi3 },
  { 0x10c0046, CODE_FOR_smulhrsvnx8hi3 },
  { 0x10c0048, CODE_FOR_smulhrsvnx4si3 },
  { 0x10d0044, CODE_FOR_umulhsvnx16qi3 },
  { 0x10d0046, CODE_FOR_umulhsvnx8hi3 },
  { 0x10d0048, CODE_FOR_umulhsvnx4si3 },
  { 0x10e0044, CODE_FOR_umulhrsvnx16qi3 },
  { 0x10e0046, CODE_FOR_umulhrsvnx8hi3 },
  { 0x10e0048, CODE_FOR_umulhrsvnx4si3 },
  { 0x10f0044, CODE_FOR_sdiv_pow2vnx16qi3 },
  { 0x10f0046, CODE_FOR_sdiv_pow2vnx8hi3 },
  { 0x10f0048, CODE_FOR_sdiv_pow2vnx4si3 },
  { 0x10f004a, CODE_FOR_sdiv_pow2vnx2di3 },
  { 0x10f005b, CODE_FOR_sdiv_pow2vnx2qi3 },
  { 0x10f005c, CODE_FOR_sdiv_pow2vnx4qi3 },
  { 0x10f005d, CODE_FOR_sdiv_pow2vnx2hi3 },
  { 0x10f005e, CODE_FOR_sdiv_pow2vnx8qi3 },
  { 0x10f005f, CODE_FOR_sdiv_pow2vnx4hi3 },
  { 0x10f0060, CODE_FOR_sdiv_pow2vnx2si3 },
  { 0x110006d, CODE_FOR_vec_pack_sfix_trunc_vnx2df },
  { 0x1120010, CODE_FOR_vec_pack_trunc_di },
  { 0x112002a, CODE_FOR_vec_pack_trunc_df },
  { 0x112003d, CODE_FOR_vec_pack_trunc_vnx8bi },
  { 0x112003e, CODE_FOR_vec_pack_trunc_vnx4bi },
  { 0x112003f, CODE_FOR_vec_pack_trunc_vnx2bi },
  { 0x1120041, CODE_FOR_vec_pack_trunc_v4hi },
  { 0x1120042, CODE_FOR_vec_pack_trunc_v2si },
  { 0x1120045, CODE_FOR_vec_pack_trunc_v8hi },
  { 0x1120046, CODE_FOR_vec_pack_trunc_vnx8hi },
  { 0x1120047, CODE_FOR_vec_pack_trunc_v4si },
  { 0x1120048, CODE_FOR_vec_pack_trunc_vnx4si },
  { 0x1120049, CODE_FOR_vec_pack_trunc_v2di },
  { 0x112004a, CODE_FOR_vec_pack_trunc_vnx2di },
  { 0x112006b, CODE_FOR_vec_pack_trunc_vnx4sf },
  { 0x112006c, CODE_FOR_vec_pack_trunc_v2df },
  { 0x112006d, CODE_FOR_vec_pack_trunc_vnx2df },
  { 0x113006d, CODE_FOR_vec_pack_ufix_trunc_vnx2df },
  { 0x1180040, CODE_FOR_vec_permv8qi },
  { 0x1180043, CODE_FOR_vec_permv16qi },
  { 0x1180044, CODE_FOR_vec_permvnx16qi },
  { 0x1180046, CODE_FOR_vec_permvnx8hi },
  { 0x1180048, CODE_FOR_vec_permvnx4si },
  { 0x118004a, CODE_FOR_vec_permvnx2di },
  { 0x1180068, CODE_FOR_vec_permvnx8bf },
  { 0x1180069, CODE_FOR_vec_permvnx8hf },
  { 0x118006b, CODE_FOR_vec_permvnx4sf },
  { 0x118006d, CODE_FOR_vec_permvnx2df },
  { 0x11a0040, CODE_FOR_vec_setv8qi },
  { 0x11a0041, CODE_FOR_vec_setv4hi },
  { 0x11a0042, CODE_FOR_vec_setv2si },
  { 0x11a0043, CODE_FOR_vec_setv16qi },
  { 0x11a0045, CODE_FOR_vec_setv8hi },
  { 0x11a0047, CODE_FOR_vec_setv4si },
  { 0x11a0049, CODE_FOR_vec_setv2di },
  { 0x11a0062, CODE_FOR_vec_setv4bf },
  { 0x11a0063, CODE_FOR_vec_setv4hf },
  { 0x11a0064, CODE_FOR_vec_setv2sf },
  { 0x11a0066, CODE_FOR_vec_setv8bf },
  { 0x11a0067, CODE_FOR_vec_setv8hf },
  { 0x11a006a, CODE_FOR_vec_setv4sf },
  { 0x11a006c, CODE_FOR_vec_setv2df },
  { 0x11c0040, CODE_FOR_vec_shr_v8qi },
  { 0x11c0041, CODE_FOR_vec_shr_v4hi },
  { 0x11c0042, CODE_FOR_vec_shr_v2si },
  { 0x11c0062, CODE_FOR_vec_shr_v4bf },
  { 0x11c0063, CODE_FOR_vec_shr_v4hf },
  { 0x11c0064, CODE_FOR_vec_shr_v2sf },
  { 0x1210048, CODE_FOR_vec_unpacks_float_hi_vnx4si },
  { 0x1220048, CODE_FOR_vec_unpacks_float_lo_vnx4si },
  { 0x123003c, CODE_FOR_vec_unpacks_hi_vnx16bi },
  { 0x123003d, CODE_FOR_vec_unpacks_hi_vnx8bi },
  { 0x123003e, CODE_FOR_vec_unpacks_hi_vnx4bi },
  { 0x1230043, CODE_FOR_vec_unpacks_hi_v16qi },
  { 0x1230044, CODE_FOR_vec_unpacks_hi_vnx16qi },
  { 0x1230045, CODE_FOR_vec_unpacks_hi_v8hi },
  { 0x1230046, CODE_FOR_vec_unpacks_hi_vnx8hi },
  { 0x1230047, CODE_FOR_vec_unpacks_hi_v4si },
  { 0x1230048, CODE_FOR_vec_unpacks_hi_vnx4si },
  { 0x1230067, CODE_FOR_vec_unpacks_hi_v8hf },
  { 0x1230069, CODE_FOR_vec_unpacks_hi_vnx8hf },
  { 0x123006a, CODE_FOR_vec_unpacks_hi_v4sf },
  { 0x123006b, CODE_FOR_vec_unpacks_hi_vnx4sf },
  { 0x124003c, CODE_FOR_vec_unpacks_lo_vnx16bi },
  { 0x124003d, CODE_FOR_vec_unpacks_lo_vnx8bi },
  { 0x124003e, CODE_FOR_vec_unpacks_lo_vnx4bi },
  { 0x1240043, CODE_FOR_vec_unpacks_lo_v16qi },
  { 0x1240044, CODE_FOR_vec_unpacks_lo_vnx16qi },
  { 0x1240045, CODE_FOR_vec_unpacks_lo_v8hi },
  { 0x1240046, CODE_FOR_vec_unpacks_lo_vnx8hi },
  { 0x1240047, CODE_FOR_vec_unpacks_lo_v4si },
  { 0x1240048, CODE_FOR_vec_unpacks_lo_vnx4si },
  { 0x1240067, CODE_FOR_vec_unpacks_lo_v8hf },
  { 0x1240069, CODE_FOR_vec_unpacks_lo_vnx8hf },
  { 0x124006a, CODE_FOR_vec_unpacks_lo_v4sf },
  { 0x124006b, CODE_FOR_vec_unpacks_lo_vnx4sf },
  { 0x1270048, CODE_FOR_vec_unpacku_float_hi_vnx4si },
  { 0x1280048, CODE_FOR_vec_unpacku_float_lo_vnx4si },
  { 0x129003c, CODE_FOR_vec_unpacku_hi_vnx16bi },
  { 0x129003d, CODE_FOR_vec_unpacku_hi_vnx8bi },
  { 0x129003e, CODE_FOR_vec_unpacku_hi_vnx4bi },
  { 0x1290043, CODE_FOR_vec_unpacku_hi_v16qi },
  { 0x1290044, CODE_FOR_vec_unpacku_hi_vnx16qi },
  { 0x1290045, CODE_FOR_vec_unpacku_hi_v8hi },
  { 0x1290046, CODE_FOR_vec_unpacku_hi_vnx8hi },
  { 0x1290047, CODE_FOR_vec_unpacku_hi_v4si },
  { 0x1290048, CODE_FOR_vec_unpacku_hi_vnx4si },
  { 0x12a003c, CODE_FOR_vec_unpacku_lo_vnx16bi },
  { 0x12a003d, CODE_FOR_vec_unpacku_lo_vnx8bi },
  { 0x12a003e, CODE_FOR_vec_unpacku_lo_vnx4bi },
  { 0x12a0043, CODE_FOR_vec_unpacku_lo_v16qi },
  { 0x12a0044, CODE_FOR_vec_unpacku_lo_vnx16qi },
  { 0x12a0045, CODE_FOR_vec_unpacku_lo_v8hi },
  { 0x12a0046, CODE_FOR_vec_unpacku_lo_vnx8hi },
  { 0x12a0047, CODE_FOR_vec_unpacku_lo_v4si },
  { 0x12a0048, CODE_FOR_vec_unpacku_lo_vnx4si },
  { 0x12c0043, CODE_FOR_vec_widen_smult_hi_v16qi },
  { 0x12c0045, CODE_FOR_vec_widen_smult_hi_v8hi },
  { 0x12c0047, CODE_FOR_vec_widen_smult_hi_v4si },
  { 0x12d0043, CODE_FOR_vec_widen_smult_lo_v16qi },
  { 0x12d0045, CODE_FOR_vec_widen_smult_lo_v8hi },
  { 0x12d0047, CODE_FOR_vec_widen_smult_lo_v4si },
  { 0x12f0043, CODE_FOR_vec_widen_ssubl_hi_v16qi },
  { 0x12f0045, CODE_FOR_vec_widen_ssubl_hi_v8hi },
  { 0x12f0047, CODE_FOR_vec_widen_ssubl_hi_v4si },
  { 0x1300043, CODE_FOR_vec_widen_ssubl_lo_v16qi },
  { 0x1300045, CODE_FOR_vec_widen_ssubl_lo_v8hi },
  { 0x1300047, CODE_FOR_vec_widen_ssubl_lo_v4si },
  { 0x1310043, CODE_FOR_vec_widen_saddl_hi_v16qi },
  { 0x1310045, CODE_FOR_vec_widen_saddl_hi_v8hi },
  { 0x1310047, CODE_FOR_vec_widen_saddl_hi_v4si },
  { 0x1320043, CODE_FOR_vec_widen_saddl_lo_v16qi },
  { 0x1320045, CODE_FOR_vec_widen_saddl_lo_v8hi },
  { 0x1320047, CODE_FOR_vec_widen_saddl_lo_v4si },
  { 0x1330043, CODE_FOR_vec_widen_sshiftl_hi_v16qi },
  { 0x1330045, CODE_FOR_vec_widen_sshiftl_hi_v8hi },
  { 0x1330047, CODE_FOR_vec_widen_sshiftl_hi_v4si },
  { 0x1340043, CODE_FOR_vec_widen_sshiftl_lo_v16qi },
  { 0x1340045, CODE_FOR_vec_widen_sshiftl_lo_v8hi },
  { 0x1340047, CODE_FOR_vec_widen_sshiftl_lo_v4si },
  { 0x1360043, CODE_FOR_vec_widen_umult_hi_v16qi },
  { 0x1360045, CODE_FOR_vec_widen_umult_hi_v8hi },
  { 0x1360047, CODE_FOR_vec_widen_umult_hi_v4si },
  { 0x1370043, CODE_FOR_vec_widen_umult_lo_v16qi },
  { 0x1370045, CODE_FOR_vec_widen_umult_lo_v8hi },
  { 0x1370047, CODE_FOR_vec_widen_umult_lo_v4si },
  { 0x1390043, CODE_FOR_vec_widen_ushiftl_hi_v16qi },
  { 0x1390045, CODE_FOR_vec_widen_ushiftl_hi_v8hi },
  { 0x1390047, CODE_FOR_vec_widen_ushiftl_hi_v4si },
  { 0x13a0043, CODE_FOR_vec_widen_ushiftl_lo_v16qi },
  { 0x13a0045, CODE_FOR_vec_widen_ushiftl_lo_v8hi },
  { 0x13a0047, CODE_FOR_vec_widen_ushiftl_lo_v4si },
  { 0x13b0043, CODE_FOR_vec_widen_usubl_hi_v16qi },
  { 0x13b0045, CODE_FOR_vec_widen_usubl_hi_v8hi },
  { 0x13b0047, CODE_FOR_vec_widen_usubl_hi_v4si },
  { 0x13c0043, CODE_FOR_vec_widen_usubl_lo_v16qi },
  { 0x13c0045, CODE_FOR_vec_widen_usubl_lo_v8hi },
  { 0x13c0047, CODE_FOR_vec_widen_usubl_lo_v4si },
  { 0x13d0043, CODE_FOR_vec_widen_uaddl_hi_v16qi },
  { 0x13d0045, CODE_FOR_vec_widen_uaddl_hi_v8hi },
  { 0x13d0047, CODE_FOR_vec_widen_uaddl_hi_v4si },
  { 0x13e0043, CODE_FOR_vec_widen_uaddl_lo_v16qi },
  { 0x13e0045, CODE_FOR_vec_widen_uaddl_lo_v8hi },
  { 0x13e0047, CODE_FOR_vec_widen_uaddl_lo_v4si },
  { 0x146000d, CODE_FOR_atomic_add_fetchqi },
  { 0x146000e, CODE_FOR_atomic_add_fetchhi },
  { 0x146000f, CODE_FOR_atomic_add_fetchsi },
  { 0x1460010, CODE_FOR_atomic_add_fetchdi },
  { 0x147000d, CODE_FOR_atomic_addqi },
  { 0x147000e, CODE_FOR_atomic_addhi },
  { 0x147000f, CODE_FOR_atomic_addsi },
  { 0x1470010, CODE_FOR_atomic_adddi },
  { 0x148000d, CODE_FOR_atomic_and_fetchqi },
  { 0x148000e, CODE_FOR_atomic_and_fetchhi },
  { 0x148000f, CODE_FOR_atomic_and_fetchsi },
  { 0x1480010, CODE_FOR_atomic_and_fetchdi },
  { 0x149000d, CODE_FOR_atomic_andqi },
  { 0x149000e, CODE_FOR_atomic_andhi },
  { 0x149000f, CODE_FOR_atomic_andsi },
  { 0x1490010, CODE_FOR_atomic_anddi },
  { 0x14d000d, CODE_FOR_atomic_compare_and_swapqi },
  { 0x14d000e, CODE_FOR_atomic_compare_and_swaphi },
  { 0x14d000f, CODE_FOR_atomic_compare_and_swapsi },
  { 0x14d0010, CODE_FOR_atomic_compare_and_swapdi },
  { 0x14d0011, CODE_FOR_atomic_compare_and_swapti },
  { 0x14e000d, CODE_FOR_atomic_exchangeqi },
  { 0x14e000e, CODE_FOR_atomic_exchangehi },
  { 0x14e000f, CODE_FOR_atomic_exchangesi },
  { 0x14e0010, CODE_FOR_atomic_exchangedi },
  { 0x14f000d, CODE_FOR_atomic_fetch_addqi },
  { 0x14f000e, CODE_FOR_atomic_fetch_addhi },
  { 0x14f000f, CODE_FOR_atomic_fetch_addsi },
  { 0x14f0010, CODE_FOR_atomic_fetch_adddi },
  { 0x150000d, CODE_FOR_atomic_fetch_andqi },
  { 0x150000e, CODE_FOR_atomic_fetch_andhi },
  { 0x150000f, CODE_FOR_atomic_fetch_andsi },
  { 0x1500010, CODE_FOR_atomic_fetch_anddi },
  { 0x151000d, CODE_FOR_atomic_fetch_nandqi },
  { 0x151000e, CODE_FOR_atomic_fetch_nandhi },
  { 0x151000f, CODE_FOR_atomic_fetch_nandsi },
  { 0x1510010, CODE_FOR_atomic_fetch_nanddi },
  { 0x152000d, CODE_FOR_atomic_fetch_orqi },
  { 0x152000e, CODE_FOR_atomic_fetch_orhi },
  { 0x152000f, CODE_FOR_atomic_fetch_orsi },
  { 0x1520010, CODE_FOR_atomic_fetch_ordi },
  { 0x153000d, CODE_FOR_atomic_fetch_subqi },
  { 0x153000e, CODE_FOR_atomic_fetch_subhi },
  { 0x153000f, CODE_FOR_atomic_fetch_subsi },
  { 0x1530010, CODE_FOR_atomic_fetch_subdi },
  { 0x154000d, CODE_FOR_atomic_fetch_xorqi },
  { 0x154000e, CODE_FOR_atomic_fetch_xorhi },
  { 0x154000f, CODE_FOR_atomic_fetch_xorsi },
  { 0x1540010, CODE_FOR_atomic_fetch_xordi },
  { 0x155000d, CODE_FOR_atomic_loadqi },
  { 0x155000e, CODE_FOR_atomic_loadhi },
  { 0x155000f, CODE_FOR_atomic_loadsi },
  { 0x1550010, CODE_FOR_atomic_loaddi },
  { 0x156000d, CODE_FOR_atomic_nand_fetchqi },
  { 0x156000e, CODE_FOR_atomic_nand_fetchhi },
  { 0x156000f, CODE_FOR_atomic_nand_fetchsi },
  { 0x1560010, CODE_FOR_atomic_nand_fetchdi },
  { 0x157000d, CODE_FOR_atomic_nandqi },
  { 0x157000e, CODE_FOR_atomic_nandhi },
  { 0x157000f, CODE_FOR_atomic_nandsi },
  { 0x1570010, CODE_FOR_atomic_nanddi },
  { 0x158000d, CODE_FOR_atomic_or_fetchqi },
  { 0x158000e, CODE_FOR_atomic_or_fetchhi },
  { 0x158000f, CODE_FOR_atomic_or_fetchsi },
  { 0x1580010, CODE_FOR_atomic_or_fetchdi },
  { 0x159000d, CODE_FOR_atomic_orqi },
  { 0x159000e, CODE_FOR_atomic_orhi },
  { 0x159000f, CODE_FOR_atomic_orsi },
  { 0x1590010, CODE_FOR_atomic_ordi },
  { 0x15a000d, CODE_FOR_atomic_storeqi },
  { 0x15a000e, CODE_FOR_atomic_storehi },
  { 0x15a000f, CODE_FOR_atomic_storesi },
  { 0x15a0010, CODE_FOR_atomic_storedi },
  { 0x15b000d, CODE_FOR_atomic_sub_fetchqi },
  { 0x15b000e, CODE_FOR_atomic_sub_fetchhi },
  { 0x15b000f, CODE_FOR_atomic_sub_fetchsi },
  { 0x15b0010, CODE_FOR_atomic_sub_fetchdi },
  { 0x15c000d, CODE_FOR_atomic_subqi },
  { 0x15c000e, CODE_FOR_atomic_subhi },
  { 0x15c000f, CODE_FOR_atomic_subsi },
  { 0x15c0010, CODE_FOR_atomic_subdi },
  { 0x15d000d, CODE_FOR_atomic_xor_fetchqi },
  { 0x15d000e, CODE_FOR_atomic_xor_fetchhi },
  { 0x15d000f, CODE_FOR_atomic_xor_fetchsi },
  { 0x15d0010, CODE_FOR_atomic_xor_fetchdi },
  { 0x15e000d, CODE_FOR_atomic_xorqi },
  { 0x15e000e, CODE_FOR_atomic_xorhi },
  { 0x15e000f, CODE_FOR_atomic_xorsi },
  { 0x15e0010, CODE_FOR_atomic_xordi },
  { 0x15f0010, CODE_FOR_get_thread_pointerdi },
  { 0x161000f, CODE_FOR_check_raw_ptrssi },
  { 0x1610010, CODE_FOR_check_raw_ptrsdi },
  { 0x162000f, CODE_FOR_check_war_ptrssi },
  { 0x1620010, CODE_FOR_check_war_ptrsdi },
  { 0x163003c, CODE_FOR_vec_duplicatevnx16bi },
  { 0x163003d, CODE_FOR_vec_duplicatevnx8bi },
  { 0x163003e, CODE_FOR_vec_duplicatevnx4bi },
  { 0x163003f, CODE_FOR_vec_duplicatevnx2bi },
  { 0x1630044, CODE_FOR_vec_duplicatevnx16qi },
  { 0x1630046, CODE_FOR_vec_duplicatevnx8hi },
  { 0x1630048, CODE_FOR_vec_duplicatevnx4si },
  { 0x163004a, CODE_FOR_vec_duplicatevnx2di },
  { 0x163005b, CODE_FOR_vec_duplicatevnx2qi },
  { 0x163005c, CODE_FOR_vec_duplicatevnx4qi },
  { 0x163005d, CODE_FOR_vec_duplicatevnx2hi },
  { 0x163005e, CODE_FOR_vec_duplicatevnx8qi },
  { 0x163005f, CODE_FOR_vec_duplicatevnx4hi },
  { 0x1630060, CODE_FOR_vec_duplicatevnx2si },
  { 0x1630068, CODE_FOR_vec_duplicatevnx8bf },
  { 0x1630069, CODE_FOR_vec_duplicatevnx8hf },
  { 0x163006b, CODE_FOR_vec_duplicatevnx4sf },
  { 0x163006d, CODE_FOR_vec_duplicatevnx2df },
  { 0x163007a, CODE_FOR_vec_duplicatevnx2bf },
  { 0x163007b, CODE_FOR_vec_duplicatevnx2hf },
  { 0x163007c, CODE_FOR_vec_duplicatevnx4bf },
  { 0x163007d, CODE_FOR_vec_duplicatevnx4hf },
  { 0x163007e, CODE_FOR_vec_duplicatevnx2sf },
  { 0x1640044, CODE_FOR_vec_seriesvnx16qi },
  { 0x1640046, CODE_FOR_vec_seriesvnx8hi },
  { 0x1640048, CODE_FOR_vec_seriesvnx4si },
  { 0x164004a, CODE_FOR_vec_seriesvnx2di },
  { 0x164005b, CODE_FOR_vec_seriesvnx2qi },
  { 0x164005c, CODE_FOR_vec_seriesvnx4qi },
  { 0x164005d, CODE_FOR_vec_seriesvnx2hi },
  { 0x164005e, CODE_FOR_vec_seriesvnx8qi },
  { 0x164005f, CODE_FOR_vec_seriesvnx4hi },
  { 0x1640060, CODE_FOR_vec_seriesvnx2si },
  { 0x1650044, CODE_FOR_vec_shl_insert_vnx16qi },
  { 0x1650046, CODE_FOR_vec_shl_insert_vnx8hi },
  { 0x1650048, CODE_FOR_vec_shl_insert_vnx4si },
  { 0x165004a, CODE_FOR_vec_shl_insert_vnx2di },
  { 0x1650068, CODE_FOR_vec_shl_insert_vnx8bf },
  { 0x1650069, CODE_FOR_vec_shl_insert_vnx8hf },
  { 0x165006b, CODE_FOR_vec_shl_insert_vnx4sf },
  { 0x165006d, CODE_FOR_vec_shl_insert_vnx2df },
};

void
init_all_optabs (struct target_optabs *optabs)
{
  bool *ena = optabs->pat_enable;
  ena[0] = HAVE_extendqihi2;
  ena[1] = HAVE_extendqisi2;
  ena[2] = HAVE_extendqidi2;
  ena[3] = HAVE_extendhisi2;
  ena[4] = HAVE_extendhidi2;
  ena[5] = HAVE_extendsidi2;
  ena[6] = HAVE_extendhfsf2;
  ena[7] = HAVE_extendhfdf2;
  ena[8] = HAVE_extendsfdf2;
  ena[9] = HAVE_extendv8qiv8hi2;
  ena[10] = HAVE_extendv4hiv4si2;
  ena[11] = HAVE_extendv2siv2di2;
  ena[12] = HAVE_extendvnx2qivnx8hi2;
  ena[13] = HAVE_extendvnx2qivnx4si2;
  ena[14] = HAVE_extendvnx2qivnx2di2;
  ena[15] = HAVE_extendvnx2qivnx2hi2;
  ena[16] = HAVE_extendvnx2qivnx4hi2;
  ena[17] = HAVE_extendvnx2qivnx2si2;
  ena[18] = HAVE_extendvnx4qivnx8hi2;
  ena[19] = HAVE_extendvnx4qivnx4si2;
  ena[20] = HAVE_extendvnx4qivnx2di2;
  ena[21] = HAVE_extendvnx4qivnx2hi2;
  ena[22] = HAVE_extendvnx4qivnx4hi2;
  ena[23] = HAVE_extendvnx4qivnx2si2;
  ena[24] = HAVE_extendvnx2hivnx8hi2;
  ena[25] = HAVE_extendvnx2hivnx4si2;
  ena[26] = HAVE_extendvnx2hivnx2di2;
  ena[27] = HAVE_extendvnx2hivnx2hi2;
  ena[28] = HAVE_extendvnx2hivnx4hi2;
  ena[29] = HAVE_extendvnx2hivnx2si2;
  ena[30] = HAVE_extendvnx8qivnx8hi2;
  ena[31] = HAVE_extendvnx8qivnx4si2;
  ena[32] = HAVE_extendvnx8qivnx2di2;
  ena[33] = HAVE_extendvnx8qivnx2hi2;
  ena[34] = HAVE_extendvnx8qivnx4hi2;
  ena[35] = HAVE_extendvnx8qivnx2si2;
  ena[36] = HAVE_extendvnx4hivnx8hi2;
  ena[37] = HAVE_extendvnx4hivnx4si2;
  ena[38] = HAVE_extendvnx4hivnx2di2;
  ena[39] = HAVE_extendvnx4hivnx2hi2;
  ena[40] = HAVE_extendvnx4hivnx4hi2;
  ena[41] = HAVE_extendvnx4hivnx2si2;
  ena[42] = HAVE_extendvnx2sivnx8hi2;
  ena[43] = HAVE_extendvnx2sivnx4si2;
  ena[44] = HAVE_extendvnx2sivnx2di2;
  ena[45] = HAVE_extendvnx2sivnx2hi2;
  ena[46] = HAVE_extendvnx2sivnx4hi2;
  ena[47] = HAVE_extendvnx2sivnx2si2;
  ena[48] = HAVE_truncsfhf2;
  ena[49] = HAVE_truncdfhf2;
  ena[50] = HAVE_truncdfsf2;
  ena[51] = HAVE_truncv8hiv8qi2;
  ena[52] = HAVE_truncvnx8hivnx2qi2;
  ena[53] = HAVE_truncvnx8hivnx4qi2;
  ena[54] = HAVE_truncvnx8hivnx2hi2;
  ena[55] = HAVE_truncvnx8hivnx8qi2;
  ena[56] = HAVE_truncvnx8hivnx4hi2;
  ena[57] = HAVE_truncvnx8hivnx2si2;
  ena[58] = HAVE_truncv4siv4hi2;
  ena[59] = HAVE_truncvnx4sivnx2qi2;
  ena[60] = HAVE_truncvnx4sivnx4qi2;
  ena[61] = HAVE_truncvnx4sivnx2hi2;
  ena[62] = HAVE_truncvnx4sivnx8qi2;
  ena[63] = HAVE_truncvnx4sivnx4hi2;
  ena[64] = HAVE_truncvnx4sivnx2si2;
  ena[65] = HAVE_truncv2div2si2;
  ena[66] = HAVE_truncvnx2divnx2qi2;
  ena[67] = HAVE_truncvnx2divnx4qi2;
  ena[68] = HAVE_truncvnx2divnx2hi2;
  ena[69] = HAVE_truncvnx2divnx8qi2;
  ena[70] = HAVE_truncvnx2divnx4hi2;
  ena[71] = HAVE_truncvnx2divnx2si2;
  ena[72] = HAVE_truncvnx2hivnx2qi2;
  ena[73] = HAVE_truncvnx2hivnx4qi2;
  ena[74] = HAVE_truncvnx2hivnx2hi2;
  ena[75] = HAVE_truncvnx2hivnx8qi2;
  ena[76] = HAVE_truncvnx2hivnx4hi2;
  ena[77] = HAVE_truncvnx2hivnx2si2;
  ena[78] = HAVE_truncvnx4hivnx2qi2;
  ena[79] = HAVE_truncvnx4hivnx4qi2;
  ena[80] = HAVE_truncvnx4hivnx2hi2;
  ena[81] = HAVE_truncvnx4hivnx8qi2;
  ena[82] = HAVE_truncvnx4hivnx4hi2;
  ena[83] = HAVE_truncvnx4hivnx2si2;
  ena[84] = HAVE_truncvnx2sivnx2qi2;
  ena[85] = HAVE_truncvnx2sivnx4qi2;
  ena[86] = HAVE_truncvnx2sivnx2hi2;
  ena[87] = HAVE_truncvnx2sivnx8qi2;
  ena[88] = HAVE_truncvnx2sivnx4hi2;
  ena[89] = HAVE_truncvnx2sivnx2si2;
  ena[90] = HAVE_zero_extendqihi2;
  ena[91] = HAVE_zero_extendqisi2;
  ena[92] = HAVE_zero_extendqidi2;
  ena[93] = HAVE_zero_extendhisi2;
  ena[94] = HAVE_zero_extendhidi2;
  ena[95] = HAVE_zero_extendsidi2;
  ena[96] = HAVE_zero_extendv8qiv8hi2;
  ena[97] = HAVE_zero_extendv4hiv4si2;
  ena[98] = HAVE_zero_extendv2siv2di2;
  ena[99] = HAVE_zero_extendvnx2qivnx8hi2;
  ena[100] = HAVE_zero_extendvnx2qivnx4si2;
  ena[101] = HAVE_zero_extendvnx2qivnx2di2;
  ena[102] = HAVE_zero_extendvnx2qivnx2hi2;
  ena[103] = HAVE_zero_extendvnx2qivnx4hi2;
  ena[104] = HAVE_zero_extendvnx2qivnx2si2;
  ena[105] = HAVE_zero_extendvnx4qivnx8hi2;
  ena[106] = HAVE_zero_extendvnx4qivnx4si2;
  ena[107] = HAVE_zero_extendvnx4qivnx2di2;
  ena[108] = HAVE_zero_extendvnx4qivnx2hi2;
  ena[109] = HAVE_zero_extendvnx4qivnx4hi2;
  ena[110] = HAVE_zero_extendvnx4qivnx2si2;
  ena[111] = HAVE_zero_extendvnx2hivnx8hi2;
  ena[112] = HAVE_zero_extendvnx2hivnx4si2;
  ena[113] = HAVE_zero_extendvnx2hivnx2di2;
  ena[114] = HAVE_zero_extendvnx2hivnx2hi2;
  ena[115] = HAVE_zero_extendvnx2hivnx4hi2;
  ena[116] = HAVE_zero_extendvnx2hivnx2si2;
  ena[117] = HAVE_zero_extendvnx8qivnx8hi2;
  ena[118] = HAVE_zero_extendvnx8qivnx4si2;
  ena[119] = HAVE_zero_extendvnx8qivnx2di2;
  ena[120] = HAVE_zero_extendvnx8qivnx2hi2;
  ena[121] = HAVE_zero_extendvnx8qivnx4hi2;
  ena[122] = HAVE_zero_extendvnx8qivnx2si2;
  ena[123] = HAVE_zero_extendvnx4hivnx8hi2;
  ena[124] = HAVE_zero_extendvnx4hivnx4si2;
  ena[125] = HAVE_zero_extendvnx4hivnx2di2;
  ena[126] = HAVE_zero_extendvnx4hivnx2hi2;
  ena[127] = HAVE_zero_extendvnx4hivnx4hi2;
  ena[128] = HAVE_zero_extendvnx4hivnx2si2;
  ena[129] = HAVE_zero_extendvnx2sivnx8hi2;
  ena[130] = HAVE_zero_extendvnx2sivnx4si2;
  ena[131] = HAVE_zero_extendvnx2sivnx2di2;
  ena[132] = HAVE_zero_extendvnx2sivnx2hi2;
  ena[133] = HAVE_zero_extendvnx2sivnx4hi2;
  ena[134] = HAVE_zero_extendvnx2sivnx2si2;
  ena[135] = HAVE_fixv4hfv4hi2;
  ena[136] = HAVE_fixv2sfv2si2;
  ena[137] = HAVE_fixv8hfv8hi2;
  ena[138] = HAVE_fixv4sfv4si2;
  ena[139] = HAVE_fixv2dfv2di2;
  ena[140] = HAVE_fixunsv4hfv4hi2;
  ena[141] = HAVE_fixunsv2sfv2si2;
  ena[142] = HAVE_fixunsv8hfv8hi2;
  ena[143] = HAVE_fixunsv4sfv4si2;
  ena[144] = HAVE_fixunsv2dfv2di2;
  ena[145] = HAVE_floathihf2;
  ena[146] = HAVE_floatsihf2;
  ena[147] = HAVE_floatsisf2;
  ena[148] = HAVE_floatsidf2;
  ena[149] = HAVE_floatdihf2;
  ena[150] = HAVE_floatdisf2;
  ena[151] = HAVE_floatdidf2;
  ena[152] = HAVE_floatv4hiv4hf2;
  ena[153] = HAVE_floatv2siv2sf2;
  ena[154] = HAVE_floatv8hiv8hf2;
  ena[155] = HAVE_floatvnx8hivnx8hf2;
  ena[156] = HAVE_floatv4siv4sf2;
  ena[157] = HAVE_floatvnx4sivnx4sf2;
  ena[158] = HAVE_floatv2div2df2;
  ena[159] = HAVE_floatvnx2divnx2df2;
  ena[160] = HAVE_floatunshihf2;
  ena[161] = HAVE_floatunssihf2;
  ena[162] = HAVE_floatunssisf2;
  ena[163] = HAVE_floatunssidf2;
  ena[164] = HAVE_floatunsdihf2;
  ena[165] = HAVE_floatunsdisf2;
  ena[166] = HAVE_floatunsdidf2;
  ena[167] = HAVE_floatunsv4hiv4hf2;
  ena[168] = HAVE_floatunsv2siv2sf2;
  ena[169] = HAVE_floatunsv8hiv8hf2;
  ena[170] = HAVE_floatunsvnx8hivnx8hf2;
  ena[171] = HAVE_floatunsv4siv4sf2;
  ena[172] = HAVE_floatunsvnx4sivnx4sf2;
  ena[173] = HAVE_floatunsv2div2df2;
  ena[174] = HAVE_floatunsvnx2divnx2df2;
  ena[175] = HAVE_lrintsfsi2;
  ena[176] = HAVE_lrintsfdi2;
  ena[177] = HAVE_lrintdfsi2;
  ena[178] = HAVE_lrintdfdi2;
  ena[179] = HAVE_lroundhfhi2;
  ena[180] = HAVE_lroundhfsi2;
  ena[181] = HAVE_lroundhfdi2;
  ena[182] = HAVE_lroundsfsi2;
  ena[183] = HAVE_lroundsfdi2;
  ena[184] = HAVE_lrounddfsi2;
  ena[185] = HAVE_lrounddfdi2;
  ena[186] = HAVE_lroundv4hfv4hi2;
  ena[187] = HAVE_lroundv2sfv2si2;
  ena[188] = HAVE_lroundv8hfv8hi2;
  ena[189] = HAVE_lroundv4sfv4si2;
  ena[190] = HAVE_lroundv2dfv2di2;
  ena[191] = HAVE_lfloorhfhi2;
  ena[192] = HAVE_lfloorhfsi2;
  ena[193] = HAVE_lfloorhfdi2;
  ena[194] = HAVE_lfloorsfsi2;
  ena[195] = HAVE_lfloorsfdi2;
  ena[196] = HAVE_lfloordfsi2;
  ena[197] = HAVE_lfloordfdi2;
  ena[198] = HAVE_lfloorv4hfv4hi2;
  ena[199] = HAVE_lfloorv2sfv2si2;
  ena[200] = HAVE_lfloorv8hfv8hi2;
  ena[201] = HAVE_lfloorv4sfv4si2;
  ena[202] = HAVE_lfloorv2dfv2di2;
  ena[203] = HAVE_lceilhfhi2;
  ena[204] = HAVE_lceilhfsi2;
  ena[205] = HAVE_lceilhfdi2;
  ena[206] = HAVE_lceilsfsi2;
  ena[207] = HAVE_lceilsfdi2;
  ena[208] = HAVE_lceildfsi2;
  ena[209] = HAVE_lceildfdi2;
  ena[210] = HAVE_lceilv4hfv4hi2;
  ena[211] = HAVE_lceilv2sfv2si2;
  ena[212] = HAVE_lceilv8hfv8hi2;
  ena[213] = HAVE_lceilv4sfv4si2;
  ena[214] = HAVE_lceilv2dfv2di2;
  ena[215] = HAVE_fix_trunchfhi2;
  ena[216] = HAVE_fix_trunchfsi2;
  ena[217] = HAVE_fix_trunchfdi2;
  ena[218] = HAVE_fix_truncsfsi2;
  ena[219] = HAVE_fix_truncsfdi2;
  ena[220] = HAVE_fix_truncdfsi2;
  ena[221] = HAVE_fix_truncdfdi2;
  ena[222] = HAVE_fix_truncv4hfv4hi2;
  ena[223] = HAVE_fix_truncv2sfv2si2;
  ena[224] = HAVE_fix_truncv8hfv8hi2;
  ena[225] = HAVE_fix_truncvnx8hfvnx8hi2;
  ena[226] = HAVE_fix_truncv4sfv4si2;
  ena[227] = HAVE_fix_truncvnx4sfvnx4si2;
  ena[228] = HAVE_fix_truncv2dfv2di2;
  ena[229] = HAVE_fix_truncvnx2dfvnx2di2;
  ena[230] = HAVE_fixuns_trunchfhi2;
  ena[231] = HAVE_fixuns_trunchfsi2;
  ena[232] = HAVE_fixuns_trunchfdi2;
  ena[233] = HAVE_fixuns_truncsfsi2;
  ena[234] = HAVE_fixuns_truncsfdi2;
  ena[235] = HAVE_fixuns_truncdfsi2;
  ena[236] = HAVE_fixuns_truncdfdi2;
  ena[237] = HAVE_fixuns_truncv4hfv4hi2;
  ena[238] = HAVE_fixuns_truncv2sfv2si2;
  ena[239] = HAVE_fixuns_truncv8hfv8hi2;
  ena[240] = HAVE_fixuns_truncvnx8hfvnx8hi2;
  ena[241] = HAVE_fixuns_truncv4sfv4si2;
  ena[242] = HAVE_fixuns_truncvnx4sfvnx4si2;
  ena[243] = HAVE_fixuns_truncv2dfv2di2;
  ena[244] = HAVE_fixuns_truncvnx2dfvnx2di2;
  ena[245] = HAVE_mulsidi3;
  ena[246] = HAVE_mulditi3;
  ena[247] = HAVE_umulsidi3;
  ena[248] = HAVE_umulditi3;
  ena[249] = HAVE_maddsidi4;
  ena[250] = HAVE_umaddsidi4;
  ena[251] = HAVE_msubsidi4;
  ena[252] = HAVE_umsubsidi4;
  ena[253] = HAVE_vec_load_lanesoiv16qi;
  ena[254] = HAVE_vec_load_lanesciv16qi;
  ena[255] = HAVE_vec_load_lanesxiv16qi;
  ena[256] = HAVE_vec_load_lanesvnx32qivnx16qi;
  ena[257] = HAVE_vec_load_lanesvnx48qivnx16qi;
  ena[258] = HAVE_vec_load_lanesvnx64qivnx16qi;
  ena[259] = HAVE_vec_load_lanesoiv8hi;
  ena[260] = HAVE_vec_load_lanesciv8hi;
  ena[261] = HAVE_vec_load_lanesxiv8hi;
  ena[262] = HAVE_vec_load_lanesvnx16hivnx8hi;
  ena[263] = HAVE_vec_load_lanesvnx24hivnx8hi;
  ena[264] = HAVE_vec_load_lanesvnx32hivnx8hi;
  ena[265] = HAVE_vec_load_lanesoiv4si;
  ena[266] = HAVE_vec_load_lanesciv4si;
  ena[267] = HAVE_vec_load_lanesxiv4si;
  ena[268] = HAVE_vec_load_lanesvnx8sivnx4si;
  ena[269] = HAVE_vec_load_lanesvnx12sivnx4si;
  ena[270] = HAVE_vec_load_lanesvnx16sivnx4si;
  ena[271] = HAVE_vec_load_lanesoiv2di;
  ena[272] = HAVE_vec_load_lanesciv2di;
  ena[273] = HAVE_vec_load_lanesxiv2di;
  ena[274] = HAVE_vec_load_lanesvnx4divnx2di;
  ena[275] = HAVE_vec_load_lanesvnx6divnx2di;
  ena[276] = HAVE_vec_load_lanesvnx8divnx2di;
  ena[277] = HAVE_vec_load_lanesoiv8bf;
  ena[278] = HAVE_vec_load_lanesciv8bf;
  ena[279] = HAVE_vec_load_lanesxiv8bf;
  ena[280] = HAVE_vec_load_lanesoiv8hf;
  ena[281] = HAVE_vec_load_lanesciv8hf;
  ena[282] = HAVE_vec_load_lanesxiv8hf;
  ena[283] = HAVE_vec_load_lanesvnx16bfvnx8bf;
  ena[284] = HAVE_vec_load_lanesvnx24bfvnx8bf;
  ena[285] = HAVE_vec_load_lanesvnx32bfvnx8bf;
  ena[286] = HAVE_vec_load_lanesvnx16hfvnx8hf;
  ena[287] = HAVE_vec_load_lanesvnx24hfvnx8hf;
  ena[288] = HAVE_vec_load_lanesvnx32hfvnx8hf;
  ena[289] = HAVE_vec_load_lanesoiv4sf;
  ena[290] = HAVE_vec_load_lanesciv4sf;
  ena[291] = HAVE_vec_load_lanesxiv4sf;
  ena[292] = HAVE_vec_load_lanesvnx8sfvnx4sf;
  ena[293] = HAVE_vec_load_lanesvnx12sfvnx4sf;
  ena[294] = HAVE_vec_load_lanesvnx16sfvnx4sf;
  ena[295] = HAVE_vec_load_lanesoiv2df;
  ena[296] = HAVE_vec_load_lanesciv2df;
  ena[297] = HAVE_vec_load_lanesxiv2df;
  ena[298] = HAVE_vec_load_lanesvnx4dfvnx2df;
  ena[299] = HAVE_vec_load_lanesvnx6dfvnx2df;
  ena[300] = HAVE_vec_load_lanesvnx8dfvnx2df;
  ena[301] = HAVE_vec_store_lanesoiv16qi;
  ena[302] = HAVE_vec_store_lanesciv16qi;
  ena[303] = HAVE_vec_store_lanesxiv16qi;
  ena[304] = HAVE_vec_store_lanesvnx32qivnx16qi;
  ena[305] = HAVE_vec_store_lanesvnx48qivnx16qi;
  ena[306] = HAVE_vec_store_lanesvnx64qivnx16qi;
  ena[307] = HAVE_vec_store_lanesoiv8hi;
  ena[308] = HAVE_vec_store_lanesciv8hi;
  ena[309] = HAVE_vec_store_lanesxiv8hi;
  ena[310] = HAVE_vec_store_lanesvnx16hivnx8hi;
  ena[311] = HAVE_vec_store_lanesvnx24hivnx8hi;
  ena[312] = HAVE_vec_store_lanesvnx32hivnx8hi;
  ena[313] = HAVE_vec_store_lanesoiv4si;
  ena[314] = HAVE_vec_store_lanesciv4si;
  ena[315] = HAVE_vec_store_lanesxiv4si;
  ena[316] = HAVE_vec_store_lanesvnx8sivnx4si;
  ena[317] = HAVE_vec_store_lanesvnx12sivnx4si;
  ena[318] = HAVE_vec_store_lanesvnx16sivnx4si;
  ena[319] = HAVE_vec_store_lanesoiv2di;
  ena[320] = HAVE_vec_store_lanesciv2di;
  ena[321] = HAVE_vec_store_lanesxiv2di;
  ena[322] = HAVE_vec_store_lanesvnx4divnx2di;
  ena[323] = HAVE_vec_store_lanesvnx6divnx2di;
  ena[324] = HAVE_vec_store_lanesvnx8divnx2di;
  ena[325] = HAVE_vec_store_lanesoiv8bf;
  ena[326] = HAVE_vec_store_lanesciv8bf;
  ena[327] = HAVE_vec_store_lanesxiv8bf;
  ena[328] = HAVE_vec_store_lanesoiv8hf;
  ena[329] = HAVE_vec_store_lanesciv8hf;
  ena[330] = HAVE_vec_store_lanesxiv8hf;
  ena[331] = HAVE_vec_store_lanesvnx16bfvnx8bf;
  ena[332] = HAVE_vec_store_lanesvnx24bfvnx8bf;
  ena[333] = HAVE_vec_store_lanesvnx32bfvnx8bf;
  ena[334] = HAVE_vec_store_lanesvnx16hfvnx8hf;
  ena[335] = HAVE_vec_store_lanesvnx24hfvnx8hf;
  ena[336] = HAVE_vec_store_lanesvnx32hfvnx8hf;
  ena[337] = HAVE_vec_store_lanesoiv4sf;
  ena[338] = HAVE_vec_store_lanesciv4sf;
  ena[339] = HAVE_vec_store_lanesxiv4sf;
  ena[340] = HAVE_vec_store_lanesvnx8sfvnx4sf;
  ena[341] = HAVE_vec_store_lanesvnx12sfvnx4sf;
  ena[342] = HAVE_vec_store_lanesvnx16sfvnx4sf;
  ena[343] = HAVE_vec_store_lanesoiv2df;
  ena[344] = HAVE_vec_store_lanesciv2df;
  ena[345] = HAVE_vec_store_lanesxiv2df;
  ena[346] = HAVE_vec_store_lanesvnx4dfvnx2df;
  ena[347] = HAVE_vec_store_lanesvnx6dfvnx2df;
  ena[348] = HAVE_vec_store_lanesvnx8dfvnx2df;
  ena[349] = HAVE_vec_mask_load_lanesvnx32qivnx16qi;
  ena[350] = HAVE_vec_mask_load_lanesvnx48qivnx16qi;
  ena[351] = HAVE_vec_mask_load_lanesvnx64qivnx16qi;
  ena[352] = HAVE_vec_mask_load_lanesvnx16hivnx8hi;
  ena[353] = HAVE_vec_mask_load_lanesvnx24hivnx8hi;
  ena[354] = HAVE_vec_mask_load_lanesvnx32hivnx8hi;
  ena[355] = HAVE_vec_mask_load_lanesvnx8sivnx4si;
  ena[356] = HAVE_vec_mask_load_lanesvnx12sivnx4si;
  ena[357] = HAVE_vec_mask_load_lanesvnx16sivnx4si;
  ena[358] = HAVE_vec_mask_load_lanesvnx4divnx2di;
  ena[359] = HAVE_vec_mask_load_lanesvnx6divnx2di;
  ena[360] = HAVE_vec_mask_load_lanesvnx8divnx2di;
  ena[361] = HAVE_vec_mask_load_lanesvnx16bfvnx8bf;
  ena[362] = HAVE_vec_mask_load_lanesvnx24bfvnx8bf;
  ena[363] = HAVE_vec_mask_load_lanesvnx32bfvnx8bf;
  ena[364] = HAVE_vec_mask_load_lanesvnx16hfvnx8hf;
  ena[365] = HAVE_vec_mask_load_lanesvnx24hfvnx8hf;
  ena[366] = HAVE_vec_mask_load_lanesvnx32hfvnx8hf;
  ena[367] = HAVE_vec_mask_load_lanesvnx8sfvnx4sf;
  ena[368] = HAVE_vec_mask_load_lanesvnx12sfvnx4sf;
  ena[369] = HAVE_vec_mask_load_lanesvnx16sfvnx4sf;
  ena[370] = HAVE_vec_mask_load_lanesvnx4dfvnx2df;
  ena[371] = HAVE_vec_mask_load_lanesvnx6dfvnx2df;
  ena[372] = HAVE_vec_mask_load_lanesvnx8dfvnx2df;
  ena[373] = HAVE_vec_mask_store_lanesvnx32qivnx16qi;
  ena[374] = HAVE_vec_mask_store_lanesvnx48qivnx16qi;
  ena[375] = HAVE_vec_mask_store_lanesvnx64qivnx16qi;
  ena[376] = HAVE_vec_mask_store_lanesvnx16hivnx8hi;
  ena[377] = HAVE_vec_mask_store_lanesvnx24hivnx8hi;
  ena[378] = HAVE_vec_mask_store_lanesvnx32hivnx8hi;
  ena[379] = HAVE_vec_mask_store_lanesvnx8sivnx4si;
  ena[380] = HAVE_vec_mask_store_lanesvnx12sivnx4si;
  ena[381] = HAVE_vec_mask_store_lanesvnx16sivnx4si;
  ena[382] = HAVE_vec_mask_store_lanesvnx4divnx2di;
  ena[383] = HAVE_vec_mask_store_lanesvnx6divnx2di;
  ena[384] = HAVE_vec_mask_store_lanesvnx8divnx2di;
  ena[385] = HAVE_vec_mask_store_lanesvnx16bfvnx8bf;
  ena[386] = HAVE_vec_mask_store_lanesvnx24bfvnx8bf;
  ena[387] = HAVE_vec_mask_store_lanesvnx32bfvnx8bf;
  ena[388] = HAVE_vec_mask_store_lanesvnx16hfvnx8hf;
  ena[389] = HAVE_vec_mask_store_lanesvnx24hfvnx8hf;
  ena[390] = HAVE_vec_mask_store_lanesvnx32hfvnx8hf;
  ena[391] = HAVE_vec_mask_store_lanesvnx8sfvnx4sf;
  ena[392] = HAVE_vec_mask_store_lanesvnx12sfvnx4sf;
  ena[393] = HAVE_vec_mask_store_lanesvnx16sfvnx4sf;
  ena[394] = HAVE_vec_mask_store_lanesvnx4dfvnx2df;
  ena[395] = HAVE_vec_mask_store_lanesvnx6dfvnx2df;
  ena[396] = HAVE_vec_mask_store_lanesvnx8dfvnx2df;
  ena[397] = HAVE_vconddidi;
  ena[398] = HAVE_vcondv8qiv8qi;
  ena[399] = HAVE_vcondv4hiv4hi;
  ena[400] = HAVE_vcondv2siv2si;
  ena[401] = HAVE_vcondv2sfv2si;
  ena[402] = HAVE_vcondv16qiv16qi;
  ena[403] = HAVE_vcondvnx16qivnx16qi;
  ena[404] = HAVE_vcondvnx8hivnx16qi;
  ena[405] = HAVE_vcondvnx4sivnx16qi;
  ena[406] = HAVE_vcondvnx2divnx16qi;
  ena[407] = HAVE_vcondvnx2qivnx16qi;
  ena[408] = HAVE_vcondvnx4qivnx16qi;
  ena[409] = HAVE_vcondvnx2hivnx16qi;
  ena[410] = HAVE_vcondvnx8qivnx16qi;
  ena[411] = HAVE_vcondvnx4hivnx16qi;
  ena[412] = HAVE_vcondvnx2sivnx16qi;
  ena[413] = HAVE_vcondvnx8bfvnx16qi;
  ena[414] = HAVE_vcondvnx8hfvnx16qi;
  ena[415] = HAVE_vcondvnx4sfvnx16qi;
  ena[416] = HAVE_vcondvnx2dfvnx16qi;
  ena[417] = HAVE_vcondvnx2bfvnx16qi;
  ena[418] = HAVE_vcondvnx2hfvnx16qi;
  ena[419] = HAVE_vcondvnx4bfvnx16qi;
  ena[420] = HAVE_vcondvnx4hfvnx16qi;
  ena[421] = HAVE_vcondvnx2sfvnx16qi;
  ena[422] = HAVE_vcondv8hiv8hi;
  ena[423] = HAVE_vcondvnx16qivnx8hi;
  ena[424] = HAVE_vcondvnx8hivnx8hi;
  ena[425] = HAVE_vcondvnx4sivnx8hi;
  ena[426] = HAVE_vcondvnx2divnx8hi;
  ena[427] = HAVE_vcondvnx2qivnx8hi;
  ena[428] = HAVE_vcondvnx4qivnx8hi;
  ena[429] = HAVE_vcondvnx2hivnx8hi;
  ena[430] = HAVE_vcondvnx8qivnx8hi;
  ena[431] = HAVE_vcondvnx4hivnx8hi;
  ena[432] = HAVE_vcondvnx2sivnx8hi;
  ena[433] = HAVE_vcondvnx8bfvnx8hi;
  ena[434] = HAVE_vcondvnx8hfvnx8hi;
  ena[435] = HAVE_vcondvnx4sfvnx8hi;
  ena[436] = HAVE_vcondvnx2dfvnx8hi;
  ena[437] = HAVE_vcondvnx2bfvnx8hi;
  ena[438] = HAVE_vcondvnx2hfvnx8hi;
  ena[439] = HAVE_vcondvnx4bfvnx8hi;
  ena[440] = HAVE_vcondvnx4hfvnx8hi;
  ena[441] = HAVE_vcondvnx2sfvnx8hi;
  ena[442] = HAVE_vcondv4siv4si;
  ena[443] = HAVE_vcondv4sfv4si;
  ena[444] = HAVE_vcondvnx16qivnx4si;
  ena[445] = HAVE_vcondvnx8hivnx4si;
  ena[446] = HAVE_vcondvnx4sivnx4si;
  ena[447] = HAVE_vcondvnx2divnx4si;
  ena[448] = HAVE_vcondvnx2qivnx4si;
  ena[449] = HAVE_vcondvnx4qivnx4si;
  ena[450] = HAVE_vcondvnx2hivnx4si;
  ena[451] = HAVE_vcondvnx8qivnx4si;
  ena[452] = HAVE_vcondvnx4hivnx4si;
  ena[453] = HAVE_vcondvnx2sivnx4si;
  ena[454] = HAVE_vcondvnx8bfvnx4si;
  ena[455] = HAVE_vcondvnx8hfvnx4si;
  ena[456] = HAVE_vcondvnx4sfvnx4si;
  ena[457] = HAVE_vcondvnx2dfvnx4si;
  ena[458] = HAVE_vcondvnx2bfvnx4si;
  ena[459] = HAVE_vcondvnx2hfvnx4si;
  ena[460] = HAVE_vcondvnx4bfvnx4si;
  ena[461] = HAVE_vcondvnx4hfvnx4si;
  ena[462] = HAVE_vcondvnx2sfvnx4si;
  ena[463] = HAVE_vcondv2div2di;
  ena[464] = HAVE_vcondv2dfv2di;
  ena[465] = HAVE_vcondvnx16qivnx2di;
  ena[466] = HAVE_vcondvnx8hivnx2di;
  ena[467] = HAVE_vcondvnx4sivnx2di;
  ena[468] = HAVE_vcondvnx2divnx2di;
  ena[469] = HAVE_vcondvnx2qivnx2di;
  ena[470] = HAVE_vcondvnx4qivnx2di;
  ena[471] = HAVE_vcondvnx2hivnx2di;
  ena[472] = HAVE_vcondvnx8qivnx2di;
  ena[473] = HAVE_vcondvnx4hivnx2di;
  ena[474] = HAVE_vcondvnx2sivnx2di;
  ena[475] = HAVE_vcondvnx8bfvnx2di;
  ena[476] = HAVE_vcondvnx8hfvnx2di;
  ena[477] = HAVE_vcondvnx4sfvnx2di;
  ena[478] = HAVE_vcondvnx2dfvnx2di;
  ena[479] = HAVE_vcondvnx2bfvnx2di;
  ena[480] = HAVE_vcondvnx2hfvnx2di;
  ena[481] = HAVE_vcondvnx4bfvnx2di;
  ena[482] = HAVE_vcondvnx4hfvnx2di;
  ena[483] = HAVE_vcondvnx2sfvnx2di;
  ena[484] = HAVE_vcondvnx16qivnx2qi;
  ena[485] = HAVE_vcondvnx8hivnx2qi;
  ena[486] = HAVE_vcondvnx4sivnx2qi;
  ena[487] = HAVE_vcondvnx2divnx2qi;
  ena[488] = HAVE_vcondvnx2qivnx2qi;
  ena[489] = HAVE_vcondvnx4qivnx2qi;
  ena[490] = HAVE_vcondvnx2hivnx2qi;
  ena[491] = HAVE_vcondvnx8qivnx2qi;
  ena[492] = HAVE_vcondvnx4hivnx2qi;
  ena[493] = HAVE_vcondvnx2sivnx2qi;
  ena[494] = HAVE_vcondvnx8bfvnx2qi;
  ena[495] = HAVE_vcondvnx8hfvnx2qi;
  ena[496] = HAVE_vcondvnx4sfvnx2qi;
  ena[497] = HAVE_vcondvnx2dfvnx2qi;
  ena[498] = HAVE_vcondvnx2bfvnx2qi;
  ena[499] = HAVE_vcondvnx2hfvnx2qi;
  ena[500] = HAVE_vcondvnx4bfvnx2qi;
  ena[501] = HAVE_vcondvnx4hfvnx2qi;
  ena[502] = HAVE_vcondvnx2sfvnx2qi;
  ena[503] = HAVE_vcondvnx16qivnx4qi;
  ena[504] = HAVE_vcondvnx8hivnx4qi;
  ena[505] = HAVE_vcondvnx4sivnx4qi;
  ena[506] = HAVE_vcondvnx2divnx4qi;
  ena[507] = HAVE_vcondvnx2qivnx4qi;
  ena[508] = HAVE_vcondvnx4qivnx4qi;
  ena[509] = HAVE_vcondvnx2hivnx4qi;
  ena[510] = HAVE_vcondvnx8qivnx4qi;
  ena[511] = HAVE_vcondvnx4hivnx4qi;
  ena[512] = HAVE_vcondvnx2sivnx4qi;
  ena[513] = HAVE_vcondvnx8bfvnx4qi;
  ena[514] = HAVE_vcondvnx8hfvnx4qi;
  ena[515] = HAVE_vcondvnx4sfvnx4qi;
  ena[516] = HAVE_vcondvnx2dfvnx4qi;
  ena[517] = HAVE_vcondvnx2bfvnx4qi;
  ena[518] = HAVE_vcondvnx2hfvnx4qi;
  ena[519] = HAVE_vcondvnx4bfvnx4qi;
  ena[520] = HAVE_vcondvnx4hfvnx4qi;
  ena[521] = HAVE_vcondvnx2sfvnx4qi;
  ena[522] = HAVE_vcondvnx16qivnx2hi;
  ena[523] = HAVE_vcondvnx8hivnx2hi;
  ena[524] = HAVE_vcondvnx4sivnx2hi;
  ena[525] = HAVE_vcondvnx2divnx2hi;
  ena[526] = HAVE_vcondvnx2qivnx2hi;
  ena[527] = HAVE_vcondvnx4qivnx2hi;
  ena[528] = HAVE_vcondvnx2hivnx2hi;
  ena[529] = HAVE_vcondvnx8qivnx2hi;
  ena[530] = HAVE_vcondvnx4hivnx2hi;
  ena[531] = HAVE_vcondvnx2sivnx2hi;
  ena[532] = HAVE_vcondvnx8bfvnx2hi;
  ena[533] = HAVE_vcondvnx8hfvnx2hi;
  ena[534] = HAVE_vcondvnx4sfvnx2hi;
  ena[535] = HAVE_vcondvnx2dfvnx2hi;
  ena[536] = HAVE_vcondvnx2bfvnx2hi;
  ena[537] = HAVE_vcondvnx2hfvnx2hi;
  ena[538] = HAVE_vcondvnx4bfvnx2hi;
  ena[539] = HAVE_vcondvnx4hfvnx2hi;
  ena[540] = HAVE_vcondvnx2sfvnx2hi;
  ena[541] = HAVE_vcondvnx16qivnx8qi;
  ena[542] = HAVE_vcondvnx8hivnx8qi;
  ena[543] = HAVE_vcondvnx4sivnx8qi;
  ena[544] = HAVE_vcondvnx2divnx8qi;
  ena[545] = HAVE_vcondvnx2qivnx8qi;
  ena[546] = HAVE_vcondvnx4qivnx8qi;
  ena[547] = HAVE_vcondvnx2hivnx8qi;
  ena[548] = HAVE_vcondvnx8qivnx8qi;
  ena[549] = HAVE_vcondvnx4hivnx8qi;
  ena[550] = HAVE_vcondvnx2sivnx8qi;
  ena[551] = HAVE_vcondvnx8bfvnx8qi;
  ena[552] = HAVE_vcondvnx8hfvnx8qi;
  ena[553] = HAVE_vcondvnx4sfvnx8qi;
  ena[554] = HAVE_vcondvnx2dfvnx8qi;
  ena[555] = HAVE_vcondvnx2bfvnx8qi;
  ena[556] = HAVE_vcondvnx2hfvnx8qi;
  ena[557] = HAVE_vcondvnx4bfvnx8qi;
  ena[558] = HAVE_vcondvnx4hfvnx8qi;
  ena[559] = HAVE_vcondvnx2sfvnx8qi;
  ena[560] = HAVE_vcondvnx16qivnx4hi;
  ena[561] = HAVE_vcondvnx8hivnx4hi;
  ena[562] = HAVE_vcondvnx4sivnx4hi;
  ena[563] = HAVE_vcondvnx2divnx4hi;
  ena[564] = HAVE_vcondvnx2qivnx4hi;
  ena[565] = HAVE_vcondvnx4qivnx4hi;
  ena[566] = HAVE_vcondvnx2hivnx4hi;
  ena[567] = HAVE_vcondvnx8qivnx4hi;
  ena[568] = HAVE_vcondvnx4hivnx4hi;
  ena[569] = HAVE_vcondvnx2sivnx4hi;
  ena[570] = HAVE_vcondvnx8bfvnx4hi;
  ena[571] = HAVE_vcondvnx8hfvnx4hi;
  ena[572] = HAVE_vcondvnx4sfvnx4hi;
  ena[573] = HAVE_vcondvnx2dfvnx4hi;
  ena[574] = HAVE_vcondvnx2bfvnx4hi;
  ena[575] = HAVE_vcondvnx2hfvnx4hi;
  ena[576] = HAVE_vcondvnx4bfvnx4hi;
  ena[577] = HAVE_vcondvnx4hfvnx4hi;
  ena[578] = HAVE_vcondvnx2sfvnx4hi;
  ena[579] = HAVE_vcondvnx16qivnx2si;
  ena[580] = HAVE_vcondvnx8hivnx2si;
  ena[581] = HAVE_vcondvnx4sivnx2si;
  ena[582] = HAVE_vcondvnx2divnx2si;
  ena[583] = HAVE_vcondvnx2qivnx2si;
  ena[584] = HAVE_vcondvnx4qivnx2si;
  ena[585] = HAVE_vcondvnx2hivnx2si;
  ena[586] = HAVE_vcondvnx8qivnx2si;
  ena[587] = HAVE_vcondvnx4hivnx2si;
  ena[588] = HAVE_vcondvnx2sivnx2si;
  ena[589] = HAVE_vcondvnx8bfvnx2si;
  ena[590] = HAVE_vcondvnx8hfvnx2si;
  ena[591] = HAVE_vcondvnx4sfvnx2si;
  ena[592] = HAVE_vcondvnx2dfvnx2si;
  ena[593] = HAVE_vcondvnx2bfvnx2si;
  ena[594] = HAVE_vcondvnx2hfvnx2si;
  ena[595] = HAVE_vcondvnx4bfvnx2si;
  ena[596] = HAVE_vcondvnx4hfvnx2si;
  ena[597] = HAVE_vcondvnx2sfvnx2si;
  ena[598] = HAVE_vcondv2siv2sf;
  ena[599] = HAVE_vcondv2sfv2sf;
  ena[600] = HAVE_vcondvnx8hivnx8hf;
  ena[601] = HAVE_vcondvnx8bfvnx8hf;
  ena[602] = HAVE_vcondvnx8hfvnx8hf;
  ena[603] = HAVE_vcondv4siv4sf;
  ena[604] = HAVE_vcondv4sfv4sf;
  ena[605] = HAVE_vcondvnx4sivnx4sf;
  ena[606] = HAVE_vcondvnx4sfvnx4sf;
  ena[607] = HAVE_vcondv2div2df;
  ena[608] = HAVE_vcondv2dfv2df;
  ena[609] = HAVE_vcondvnx2divnx2df;
  ena[610] = HAVE_vcondvnx2dfvnx2df;
  ena[611] = HAVE_vcondudidi;
  ena[612] = HAVE_vconduv8qiv8qi;
  ena[613] = HAVE_vconduv4hiv4hi;
  ena[614] = HAVE_vconduv2siv2si;
  ena[615] = HAVE_vconduv2sfv2si;
  ena[616] = HAVE_vconduv16qiv16qi;
  ena[617] = HAVE_vconduvnx16qivnx16qi;
  ena[618] = HAVE_vconduvnx8hivnx16qi;
  ena[619] = HAVE_vconduvnx4sivnx16qi;
  ena[620] = HAVE_vconduvnx2divnx16qi;
  ena[621] = HAVE_vconduvnx2qivnx16qi;
  ena[622] = HAVE_vconduvnx4qivnx16qi;
  ena[623] = HAVE_vconduvnx2hivnx16qi;
  ena[624] = HAVE_vconduvnx8qivnx16qi;
  ena[625] = HAVE_vconduvnx4hivnx16qi;
  ena[626] = HAVE_vconduvnx2sivnx16qi;
  ena[627] = HAVE_vconduvnx8bfvnx16qi;
  ena[628] = HAVE_vconduvnx8hfvnx16qi;
  ena[629] = HAVE_vconduvnx4sfvnx16qi;
  ena[630] = HAVE_vconduvnx2dfvnx16qi;
  ena[631] = HAVE_vconduvnx2bfvnx16qi;
  ena[632] = HAVE_vconduvnx2hfvnx16qi;
  ena[633] = HAVE_vconduvnx4bfvnx16qi;
  ena[634] = HAVE_vconduvnx4hfvnx16qi;
  ena[635] = HAVE_vconduvnx2sfvnx16qi;
  ena[636] = HAVE_vconduv8hiv8hi;
  ena[637] = HAVE_vconduvnx16qivnx8hi;
  ena[638] = HAVE_vconduvnx8hivnx8hi;
  ena[639] = HAVE_vconduvnx4sivnx8hi;
  ena[640] = HAVE_vconduvnx2divnx8hi;
  ena[641] = HAVE_vconduvnx2qivnx8hi;
  ena[642] = HAVE_vconduvnx4qivnx8hi;
  ena[643] = HAVE_vconduvnx2hivnx8hi;
  ena[644] = HAVE_vconduvnx8qivnx8hi;
  ena[645] = HAVE_vconduvnx4hivnx8hi;
  ena[646] = HAVE_vconduvnx2sivnx8hi;
  ena[647] = HAVE_vconduvnx8bfvnx8hi;
  ena[648] = HAVE_vconduvnx8hfvnx8hi;
  ena[649] = HAVE_vconduvnx4sfvnx8hi;
  ena[650] = HAVE_vconduvnx2dfvnx8hi;
  ena[651] = HAVE_vconduvnx2bfvnx8hi;
  ena[652] = HAVE_vconduvnx2hfvnx8hi;
  ena[653] = HAVE_vconduvnx4bfvnx8hi;
  ena[654] = HAVE_vconduvnx4hfvnx8hi;
  ena[655] = HAVE_vconduvnx2sfvnx8hi;
  ena[656] = HAVE_vconduv4siv4si;
  ena[657] = HAVE_vconduv4sfv4si;
  ena[658] = HAVE_vconduvnx16qivnx4si;
  ena[659] = HAVE_vconduvnx8hivnx4si;
  ena[660] = HAVE_vconduvnx4sivnx4si;
  ena[661] = HAVE_vconduvnx2divnx4si;
  ena[662] = HAVE_vconduvnx2qivnx4si;
  ena[663] = HAVE_vconduvnx4qivnx4si;
  ena[664] = HAVE_vconduvnx2hivnx4si;
  ena[665] = HAVE_vconduvnx8qivnx4si;
  ena[666] = HAVE_vconduvnx4hivnx4si;
  ena[667] = HAVE_vconduvnx2sivnx4si;
  ena[668] = HAVE_vconduvnx8bfvnx4si;
  ena[669] = HAVE_vconduvnx8hfvnx4si;
  ena[670] = HAVE_vconduvnx4sfvnx4si;
  ena[671] = HAVE_vconduvnx2dfvnx4si;
  ena[672] = HAVE_vconduvnx2bfvnx4si;
  ena[673] = HAVE_vconduvnx2hfvnx4si;
  ena[674] = HAVE_vconduvnx4bfvnx4si;
  ena[675] = HAVE_vconduvnx4hfvnx4si;
  ena[676] = HAVE_vconduvnx2sfvnx4si;
  ena[677] = HAVE_vconduv2div2di;
  ena[678] = HAVE_vconduv2dfv2di;
  ena[679] = HAVE_vconduvnx16qivnx2di;
  ena[680] = HAVE_vconduvnx8hivnx2di;
  ena[681] = HAVE_vconduvnx4sivnx2di;
  ena[682] = HAVE_vconduvnx2divnx2di;
  ena[683] = HAVE_vconduvnx2qivnx2di;
  ena[684] = HAVE_vconduvnx4qivnx2di;
  ena[685] = HAVE_vconduvnx2hivnx2di;
  ena[686] = HAVE_vconduvnx8qivnx2di;
  ena[687] = HAVE_vconduvnx4hivnx2di;
  ena[688] = HAVE_vconduvnx2sivnx2di;
  ena[689] = HAVE_vconduvnx8bfvnx2di;
  ena[690] = HAVE_vconduvnx8hfvnx2di;
  ena[691] = HAVE_vconduvnx4sfvnx2di;
  ena[692] = HAVE_vconduvnx2dfvnx2di;
  ena[693] = HAVE_vconduvnx2bfvnx2di;
  ena[694] = HAVE_vconduvnx2hfvnx2di;
  ena[695] = HAVE_vconduvnx4bfvnx2di;
  ena[696] = HAVE_vconduvnx4hfvnx2di;
  ena[697] = HAVE_vconduvnx2sfvnx2di;
  ena[698] = HAVE_vconduvnx16qivnx2qi;
  ena[699] = HAVE_vconduvnx8hivnx2qi;
  ena[700] = HAVE_vconduvnx4sivnx2qi;
  ena[701] = HAVE_vconduvnx2divnx2qi;
  ena[702] = HAVE_vconduvnx2qivnx2qi;
  ena[703] = HAVE_vconduvnx4qivnx2qi;
  ena[704] = HAVE_vconduvnx2hivnx2qi;
  ena[705] = HAVE_vconduvnx8qivnx2qi;
  ena[706] = HAVE_vconduvnx4hivnx2qi;
  ena[707] = HAVE_vconduvnx2sivnx2qi;
  ena[708] = HAVE_vconduvnx8bfvnx2qi;
  ena[709] = HAVE_vconduvnx8hfvnx2qi;
  ena[710] = HAVE_vconduvnx4sfvnx2qi;
  ena[711] = HAVE_vconduvnx2dfvnx2qi;
  ena[712] = HAVE_vconduvnx2bfvnx2qi;
  ena[713] = HAVE_vconduvnx2hfvnx2qi;
  ena[714] = HAVE_vconduvnx4bfvnx2qi;
  ena[715] = HAVE_vconduvnx4hfvnx2qi;
  ena[716] = HAVE_vconduvnx2sfvnx2qi;
  ena[717] = HAVE_vconduvnx16qivnx4qi;
  ena[718] = HAVE_vconduvnx8hivnx4qi;
  ena[719] = HAVE_vconduvnx4sivnx4qi;
  ena[720] = HAVE_vconduvnx2divnx4qi;
  ena[721] = HAVE_vconduvnx2qivnx4qi;
  ena[722] = HAVE_vconduvnx4qivnx4qi;
  ena[723] = HAVE_vconduvnx2hivnx4qi;
  ena[724] = HAVE_vconduvnx8qivnx4qi;
  ena[725] = HAVE_vconduvnx4hivnx4qi;
  ena[726] = HAVE_vconduvnx2sivnx4qi;
  ena[727] = HAVE_vconduvnx8bfvnx4qi;
  ena[728] = HAVE_vconduvnx8hfvnx4qi;
  ena[729] = HAVE_vconduvnx4sfvnx4qi;
  ena[730] = HAVE_vconduvnx2dfvnx4qi;
  ena[731] = HAVE_vconduvnx2bfvnx4qi;
  ena[732] = HAVE_vconduvnx2hfvnx4qi;
  ena[733] = HAVE_vconduvnx4bfvnx4qi;
  ena[734] = HAVE_vconduvnx4hfvnx4qi;
  ena[735] = HAVE_vconduvnx2sfvnx4qi;
  ena[736] = HAVE_vconduvnx16qivnx2hi;
  ena[737] = HAVE_vconduvnx8hivnx2hi;
  ena[738] = HAVE_vconduvnx4sivnx2hi;
  ena[739] = HAVE_vconduvnx2divnx2hi;
  ena[740] = HAVE_vconduvnx2qivnx2hi;
  ena[741] = HAVE_vconduvnx4qivnx2hi;
  ena[742] = HAVE_vconduvnx2hivnx2hi;
  ena[743] = HAVE_vconduvnx8qivnx2hi;
  ena[744] = HAVE_vconduvnx4hivnx2hi;
  ena[745] = HAVE_vconduvnx2sivnx2hi;
  ena[746] = HAVE_vconduvnx8bfvnx2hi;
  ena[747] = HAVE_vconduvnx8hfvnx2hi;
  ena[748] = HAVE_vconduvnx4sfvnx2hi;
  ena[749] = HAVE_vconduvnx2dfvnx2hi;
  ena[750] = HAVE_vconduvnx2bfvnx2hi;
  ena[751] = HAVE_vconduvnx2hfvnx2hi;
  ena[752] = HAVE_vconduvnx4bfvnx2hi;
  ena[753] = HAVE_vconduvnx4hfvnx2hi;
  ena[754] = HAVE_vconduvnx2sfvnx2hi;
  ena[755] = HAVE_vconduvnx16qivnx8qi;
  ena[756] = HAVE_vconduvnx8hivnx8qi;
  ena[757] = HAVE_vconduvnx4sivnx8qi;
  ena[758] = HAVE_vconduvnx2divnx8qi;
  ena[759] = HAVE_vconduvnx2qivnx8qi;
  ena[760] = HAVE_vconduvnx4qivnx8qi;
  ena[761] = HAVE_vconduvnx2hivnx8qi;
  ena[762] = HAVE_vconduvnx8qivnx8qi;
  ena[763] = HAVE_vconduvnx4hivnx8qi;
  ena[764] = HAVE_vconduvnx2sivnx8qi;
  ena[765] = HAVE_vconduvnx8bfvnx8qi;
  ena[766] = HAVE_vconduvnx8hfvnx8qi;
  ena[767] = HAVE_vconduvnx4sfvnx8qi;
  ena[768] = HAVE_vconduvnx2dfvnx8qi;
  ena[769] = HAVE_vconduvnx2bfvnx8qi;
  ena[770] = HAVE_vconduvnx2hfvnx8qi;
  ena[771] = HAVE_vconduvnx4bfvnx8qi;
  ena[772] = HAVE_vconduvnx4hfvnx8qi;
  ena[773] = HAVE_vconduvnx2sfvnx8qi;
  ena[774] = HAVE_vconduvnx16qivnx4hi;
  ena[775] = HAVE_vconduvnx8hivnx4hi;
  ena[776] = HAVE_vconduvnx4sivnx4hi;
  ena[777] = HAVE_vconduvnx2divnx4hi;
  ena[778] = HAVE_vconduvnx2qivnx4hi;
  ena[779] = HAVE_vconduvnx4qivnx4hi;
  ena[780] = HAVE_vconduvnx2hivnx4hi;
  ena[781] = HAVE_vconduvnx8qivnx4hi;
  ena[782] = HAVE_vconduvnx4hivnx4hi;
  ena[783] = HAVE_vconduvnx2sivnx4hi;
  ena[784] = HAVE_vconduvnx8bfvnx4hi;
  ena[785] = HAVE_vconduvnx8hfvnx4hi;
  ena[786] = HAVE_vconduvnx4sfvnx4hi;
  ena[787] = HAVE_vconduvnx2dfvnx4hi;
  ena[788] = HAVE_vconduvnx2bfvnx4hi;
  ena[789] = HAVE_vconduvnx2hfvnx4hi;
  ena[790] = HAVE_vconduvnx4bfvnx4hi;
  ena[791] = HAVE_vconduvnx4hfvnx4hi;
  ena[792] = HAVE_vconduvnx2sfvnx4hi;
  ena[793] = HAVE_vconduvnx16qivnx2si;
  ena[794] = HAVE_vconduvnx8hivnx2si;
  ena[795] = HAVE_vconduvnx4sivnx2si;
  ena[796] = HAVE_vconduvnx2divnx2si;
  ena[797] = HAVE_vconduvnx2qivnx2si;
  ena[798] = HAVE_vconduvnx4qivnx2si;
  ena[799] = HAVE_vconduvnx2hivnx2si;
  ena[800] = HAVE_vconduvnx8qivnx2si;
  ena[801] = HAVE_vconduvnx4hivnx2si;
  ena[802] = HAVE_vconduvnx2sivnx2si;
  ena[803] = HAVE_vconduvnx8bfvnx2si;
  ena[804] = HAVE_vconduvnx8hfvnx2si;
  ena[805] = HAVE_vconduvnx4sfvnx2si;
  ena[806] = HAVE_vconduvnx2dfvnx2si;
  ena[807] = HAVE_vconduvnx2bfvnx2si;
  ena[808] = HAVE_vconduvnx2hfvnx2si;
  ena[809] = HAVE_vconduvnx4bfvnx2si;
  ena[810] = HAVE_vconduvnx4hfvnx2si;
  ena[811] = HAVE_vconduvnx2sfvnx2si;
  ena[812] = HAVE_vcond_mask_didi;
  ena[813] = HAVE_vcond_mask_vnx16bivnx16bi;
  ena[814] = HAVE_vcond_mask_vnx16qivnx16bi;
  ena[815] = HAVE_vcond_mask_vnx8bivnx8bi;
  ena[816] = HAVE_vcond_mask_vnx8hivnx8bi;
  ena[817] = HAVE_vcond_mask_vnx8qivnx8bi;
  ena[818] = HAVE_vcond_mask_vnx8bfvnx8bi;
  ena[819] = HAVE_vcond_mask_vnx8hfvnx8bi;
  ena[820] = HAVE_vcond_mask_vnx4bivnx4bi;
  ena[821] = HAVE_vcond_mask_vnx4sivnx4bi;
  ena[822] = HAVE_vcond_mask_vnx4qivnx4bi;
  ena[823] = HAVE_vcond_mask_vnx4hivnx4bi;
  ena[824] = HAVE_vcond_mask_vnx4sfvnx4bi;
  ena[825] = HAVE_vcond_mask_vnx4bfvnx4bi;
  ena[826] = HAVE_vcond_mask_vnx4hfvnx4bi;
  ena[827] = HAVE_vcond_mask_vnx2bivnx2bi;
  ena[828] = HAVE_vcond_mask_vnx2divnx2bi;
  ena[829] = HAVE_vcond_mask_vnx2qivnx2bi;
  ena[830] = HAVE_vcond_mask_vnx2hivnx2bi;
  ena[831] = HAVE_vcond_mask_vnx2sivnx2bi;
  ena[832] = HAVE_vcond_mask_vnx2dfvnx2bi;
  ena[833] = HAVE_vcond_mask_vnx2bfvnx2bi;
  ena[834] = HAVE_vcond_mask_vnx2hfvnx2bi;
  ena[835] = HAVE_vcond_mask_vnx2sfvnx2bi;
  ena[836] = HAVE_vcond_mask_v8qiv8qi;
  ena[837] = HAVE_vcond_mask_v4hiv4hi;
  ena[838] = HAVE_vcond_mask_v2siv2si;
  ena[839] = HAVE_vcond_mask_v2sfv2si;
  ena[840] = HAVE_vcond_mask_v16qiv16qi;
  ena[841] = HAVE_vcond_mask_v8hiv8hi;
  ena[842] = HAVE_vcond_mask_v4siv4si;
  ena[843] = HAVE_vcond_mask_v4sfv4si;
  ena[844] = HAVE_vcond_mask_v2div2di;
  ena[845] = HAVE_vcond_mask_v2dfv2di;
  ena[846] = HAVE_vec_cmpdidi;
  ena[847] = HAVE_vec_cmpvnx16qivnx16bi;
  ena[848] = HAVE_vec_cmpvnx8hivnx8bi;
  ena[849] = HAVE_vec_cmpvnx8qivnx8bi;
  ena[850] = HAVE_vec_cmpvnx8hfvnx8bi;
  ena[851] = HAVE_vec_cmpvnx4sivnx4bi;
  ena[852] = HAVE_vec_cmpvnx4qivnx4bi;
  ena[853] = HAVE_vec_cmpvnx4hivnx4bi;
  ena[854] = HAVE_vec_cmpvnx4sfvnx4bi;
  ena[855] = HAVE_vec_cmpvnx2divnx2bi;
  ena[856] = HAVE_vec_cmpvnx2qivnx2bi;
  ena[857] = HAVE_vec_cmpvnx2hivnx2bi;
  ena[858] = HAVE_vec_cmpvnx2sivnx2bi;
  ena[859] = HAVE_vec_cmpvnx2dfvnx2bi;
  ena[860] = HAVE_vec_cmpv8qiv8qi;
  ena[861] = HAVE_vec_cmpv4hiv4hi;
  ena[862] = HAVE_vec_cmpv2siv2si;
  ena[863] = HAVE_vec_cmpv2sfv2si;
  ena[864] = HAVE_vec_cmpv16qiv16qi;
  ena[865] = HAVE_vec_cmpv8hiv8hi;
  ena[866] = HAVE_vec_cmpv4siv4si;
  ena[867] = HAVE_vec_cmpv4sfv4si;
  ena[868] = HAVE_vec_cmpv2div2di;
  ena[869] = HAVE_vec_cmpv2dfv2di;
  ena[870] = HAVE_vec_cmpudidi;
  ena[871] = HAVE_vec_cmpuvnx16qivnx16bi;
  ena[872] = HAVE_vec_cmpuvnx8hivnx8bi;
  ena[873] = HAVE_vec_cmpuvnx8qivnx8bi;
  ena[874] = HAVE_vec_cmpuvnx4sivnx4bi;
  ena[875] = HAVE_vec_cmpuvnx4qivnx4bi;
  ena[876] = HAVE_vec_cmpuvnx4hivnx4bi;
  ena[877] = HAVE_vec_cmpuvnx2divnx2bi;
  ena[878] = HAVE_vec_cmpuvnx2qivnx2bi;
  ena[879] = HAVE_vec_cmpuvnx2hivnx2bi;
  ena[880] = HAVE_vec_cmpuvnx2sivnx2bi;
  ena[881] = HAVE_vec_cmpuv8qiv8qi;
  ena[882] = HAVE_vec_cmpuv4hiv4hi;
  ena[883] = HAVE_vec_cmpuv2siv2si;
  ena[884] = HAVE_vec_cmpuv16qiv16qi;
  ena[885] = HAVE_vec_cmpuv8hiv8hi;
  ena[886] = HAVE_vec_cmpuv4siv4si;
  ena[887] = HAVE_vec_cmpuv2div2di;
  ena[888] = HAVE_maskloadvnx16qivnx16bi;
  ena[889] = HAVE_maskloadvnx8hivnx8bi;
  ena[890] = HAVE_maskloadvnx8qivnx8bi;
  ena[891] = HAVE_maskloadvnx8bfvnx8bi;
  ena[892] = HAVE_maskloadvnx8hfvnx8bi;
  ena[893] = HAVE_maskloadvnx4sivnx4bi;
  ena[894] = HAVE_maskloadvnx4qivnx4bi;
  ena[895] = HAVE_maskloadvnx4hivnx4bi;
  ena[896] = HAVE_maskloadvnx4sfvnx4bi;
  ena[897] = HAVE_maskloadvnx4bfvnx4bi;
  ena[898] = HAVE_maskloadvnx4hfvnx4bi;
  ena[899] = HAVE_maskloadvnx2divnx2bi;
  ena[900] = HAVE_maskloadvnx2qivnx2bi;
  ena[901] = HAVE_maskloadvnx2hivnx2bi;
  ena[902] = HAVE_maskloadvnx2sivnx2bi;
  ena[903] = HAVE_maskloadvnx2dfvnx2bi;
  ena[904] = HAVE_maskloadvnx2bfvnx2bi;
  ena[905] = HAVE_maskloadvnx2hfvnx2bi;
  ena[906] = HAVE_maskloadvnx2sfvnx2bi;
  ena[907] = HAVE_maskstorevnx16qivnx16bi;
  ena[908] = HAVE_maskstorevnx8hivnx8bi;
  ena[909] = HAVE_maskstorevnx8qivnx8bi;
  ena[910] = HAVE_maskstorevnx8bfvnx8bi;
  ena[911] = HAVE_maskstorevnx8hfvnx8bi;
  ena[912] = HAVE_maskstorevnx4sivnx4bi;
  ena[913] = HAVE_maskstorevnx4qivnx4bi;
  ena[914] = HAVE_maskstorevnx4hivnx4bi;
  ena[915] = HAVE_maskstorevnx4sfvnx4bi;
  ena[916] = HAVE_maskstorevnx4bfvnx4bi;
  ena[917] = HAVE_maskstorevnx4hfvnx4bi;
  ena[918] = HAVE_maskstorevnx2divnx2bi;
  ena[919] = HAVE_maskstorevnx2qivnx2bi;
  ena[920] = HAVE_maskstorevnx2hivnx2bi;
  ena[921] = HAVE_maskstorevnx2sivnx2bi;
  ena[922] = HAVE_maskstorevnx2dfvnx2bi;
  ena[923] = HAVE_maskstorevnx2bfvnx2bi;
  ena[924] = HAVE_maskstorevnx2hfvnx2bi;
  ena[925] = HAVE_maskstorevnx2sfvnx2bi;
  ena[926] = HAVE_gather_loadvnx4sivnx4si;
  ena[927] = HAVE_gather_loadvnx4qivnx4si;
  ena[928] = HAVE_gather_loadvnx4hivnx4si;
  ena[929] = HAVE_gather_loadvnx4sfvnx4si;
  ena[930] = HAVE_gather_loadvnx4bfvnx4si;
  ena[931] = HAVE_gather_loadvnx4hfvnx4si;
  ena[932] = HAVE_gather_loadvnx2divnx2di;
  ena[933] = HAVE_gather_loadvnx2qivnx2di;
  ena[934] = HAVE_gather_loadvnx2hivnx2di;
  ena[935] = HAVE_gather_loadvnx2sivnx2di;
  ena[936] = HAVE_gather_loadvnx2dfvnx2di;
  ena[937] = HAVE_gather_loadvnx2bfvnx2di;
  ena[938] = HAVE_gather_loadvnx2hfvnx2di;
  ena[939] = HAVE_gather_loadvnx2sfvnx2di;
  ena[940] = HAVE_mask_gather_loadvnx4sivnx4si;
  ena[941] = HAVE_mask_gather_loadvnx4qivnx4si;
  ena[942] = HAVE_mask_gather_loadvnx4hivnx4si;
  ena[943] = HAVE_mask_gather_loadvnx4sfvnx4si;
  ena[944] = HAVE_mask_gather_loadvnx4bfvnx4si;
  ena[945] = HAVE_mask_gather_loadvnx4hfvnx4si;
  ena[946] = HAVE_mask_gather_loadvnx2divnx2di;
  ena[947] = HAVE_mask_gather_loadvnx2qivnx2di;
  ena[948] = HAVE_mask_gather_loadvnx2hivnx2di;
  ena[949] = HAVE_mask_gather_loadvnx2sivnx2di;
  ena[950] = HAVE_mask_gather_loadvnx2dfvnx2di;
  ena[951] = HAVE_mask_gather_loadvnx2bfvnx2di;
  ena[952] = HAVE_mask_gather_loadvnx2hfvnx2di;
  ena[953] = HAVE_mask_gather_loadvnx2sfvnx2di;
  ena[954] = HAVE_scatter_storevnx4sivnx4si;
  ena[955] = HAVE_scatter_storevnx4qivnx4si;
  ena[956] = HAVE_scatter_storevnx4hivnx4si;
  ena[957] = HAVE_scatter_storevnx4sfvnx4si;
  ena[958] = HAVE_scatter_storevnx4bfvnx4si;
  ena[959] = HAVE_scatter_storevnx4hfvnx4si;
  ena[960] = HAVE_scatter_storevnx2divnx2di;
  ena[961] = HAVE_scatter_storevnx2qivnx2di;
  ena[962] = HAVE_scatter_storevnx2hivnx2di;
  ena[963] = HAVE_scatter_storevnx2sivnx2di;
  ena[964] = HAVE_scatter_storevnx2dfvnx2di;
  ena[965] = HAVE_scatter_storevnx2bfvnx2di;
  ena[966] = HAVE_scatter_storevnx2hfvnx2di;
  ena[967] = HAVE_scatter_storevnx2sfvnx2di;
  ena[968] = HAVE_mask_scatter_storevnx4sivnx4si;
  ena[969] = HAVE_mask_scatter_storevnx4qivnx4si;
  ena[970] = HAVE_mask_scatter_storevnx4hivnx4si;
  ena[971] = HAVE_mask_scatter_storevnx4sfvnx4si;
  ena[972] = HAVE_mask_scatter_storevnx4bfvnx4si;
  ena[973] = HAVE_mask_scatter_storevnx4hfvnx4si;
  ena[974] = HAVE_mask_scatter_storevnx2divnx2di;
  ena[975] = HAVE_mask_scatter_storevnx2qivnx2di;
  ena[976] = HAVE_mask_scatter_storevnx2hivnx2di;
  ena[977] = HAVE_mask_scatter_storevnx2sivnx2di;
  ena[978] = HAVE_mask_scatter_storevnx2dfvnx2di;
  ena[979] = HAVE_mask_scatter_storevnx2bfvnx2di;
  ena[980] = HAVE_mask_scatter_storevnx2hfvnx2di;
  ena[981] = HAVE_mask_scatter_storevnx2sfvnx2di;
  ena[982] = HAVE_vec_extractvnx16biqi;
  ena[983] = HAVE_vec_extractv8qiqi;
  ena[984] = HAVE_vec_extractv16qiqi;
  ena[985] = HAVE_vec_extractvnx16qiqi;
  ena[986] = HAVE_vec_extractvnx8bihi;
  ena[987] = HAVE_vec_extractv4hihi;
  ena[988] = HAVE_vec_extractv8hihi;
  ena[989] = HAVE_vec_extractvnx8hihi;
  ena[990] = HAVE_vec_extractvnx4bisi;
  ena[991] = HAVE_vec_extractv2sisi;
  ena[992] = HAVE_vec_extractv4sisi;
  ena[993] = HAVE_vec_extractvnx4sisi;
  ena[994] = HAVE_vec_extractvnx2bidi;
  ena[995] = HAVE_vec_extractv2didi;
  ena[996] = HAVE_vec_extractvnx2didi;
  ena[997] = HAVE_vec_extractv4hfhf;
  ena[998] = HAVE_vec_extractv8hfhf;
  ena[999] = HAVE_vec_extractvnx8hfhf;
  ena[1000] = HAVE_vec_extractv4bfbf;
  ena[1001] = HAVE_vec_extractv8bfbf;
  ena[1002] = HAVE_vec_extractvnx8bfbf;
  ena[1003] = HAVE_vec_extractv2sfsf;
  ena[1004] = HAVE_vec_extractv4sfsf;
  ena[1005] = HAVE_vec_extractvnx4sfsf;
  ena[1006] = HAVE_vec_extractv2dfdf;
  ena[1007] = HAVE_vec_extractvnx2dfdf;
  ena[1008] = HAVE_vec_extractv16qiv8qi;
  ena[1009] = HAVE_vec_extractv8hiv4hi;
  ena[1010] = HAVE_vec_extractv4siv2si;
  ena[1011] = HAVE_vec_extractv8bfv4bf;
  ena[1012] = HAVE_vec_extractv8hfv4hf;
  ena[1013] = HAVE_vec_extractv4sfv2sf;
  ena[1014] = HAVE_vec_extractv2dfv1df;
  ena[1015] = HAVE_vec_initv8qiqi;
  ena[1016] = HAVE_vec_initv16qiqi;
  ena[1017] = HAVE_vec_initvnx16qiqi;
  ena[1018] = HAVE_vec_initv4hihi;
  ena[1019] = HAVE_vec_initv8hihi;
  ena[1020] = HAVE_vec_initvnx8hihi;
  ena[1021] = HAVE_vec_initv2sisi;
  ena[1022] = HAVE_vec_initv4sisi;
  ena[1023] = HAVE_vec_initvnx4sisi;
  ena[1024] = HAVE_vec_initv2didi;
  ena[1025] = HAVE_vec_initvnx2didi;
  ena[1026] = HAVE_vec_initv4hfhf;
  ena[1027] = HAVE_vec_initv8hfhf;
  ena[1028] = HAVE_vec_initvnx8hfhf;
  ena[1029] = HAVE_vec_initv4bfbf;
  ena[1030] = HAVE_vec_initv8bfbf;
  ena[1031] = HAVE_vec_initvnx8bfbf;
  ena[1032] = HAVE_vec_initv2sfsf;
  ena[1033] = HAVE_vec_initv4sfsf;
  ena[1034] = HAVE_vec_initvnx4sfsf;
  ena[1035] = HAVE_vec_initv2dfdf;
  ena[1036] = HAVE_vec_initvnx2dfdf;
  ena[1037] = HAVE_vec_initv16qiv8qi;
  ena[1038] = HAVE_vec_initv8hiv4hi;
  ena[1039] = HAVE_vec_initv4siv2si;
  ena[1040] = HAVE_vec_initv8bfv4bf;
  ena[1041] = HAVE_vec_initv8hfv4hf;
  ena[1042] = HAVE_vec_initv4sfv2sf;
  ena[1043] = HAVE_while_ultsivnx16bi;
  ena[1044] = HAVE_while_ultdivnx16bi;
  ena[1045] = HAVE_while_ultsivnx8bi;
  ena[1046] = HAVE_while_ultdivnx8bi;
  ena[1047] = HAVE_while_ultsivnx4bi;
  ena[1048] = HAVE_while_ultdivnx4bi;
  ena[1049] = HAVE_while_ultsivnx2bi;
  ena[1050] = HAVE_while_ultdivnx2bi;
  ena[1051] = HAVE_addsi3;
  ena[1052] = HAVE_adddi3;
  ena[1053] = HAVE_addti3;
  ena[1054] = HAVE_addhf3;
  ena[1055] = HAVE_addsf3;
  ena[1056] = HAVE_adddf3;
  ena[1057] = HAVE_addv8qi3;
  ena[1058] = HAVE_addv4hi3;
  ena[1059] = HAVE_addv2si3;
  ena[1060] = HAVE_addv16qi3;
  ena[1061] = HAVE_addvnx16qi3;
  ena[1062] = HAVE_addv8hi3;
  ena[1063] = HAVE_addvnx8hi3;
  ena[1064] = HAVE_addv4si3;
  ena[1065] = HAVE_addvnx4si3;
  ena[1066] = HAVE_addv2di3;
  ena[1067] = HAVE_addvnx2di3;
  ena[1068] = HAVE_addvnx2qi3;
  ena[1069] = HAVE_addvnx4qi3;
  ena[1070] = HAVE_addvnx2hi3;
  ena[1071] = HAVE_addvnx8qi3;
  ena[1072] = HAVE_addvnx4hi3;
  ena[1073] = HAVE_addvnx2si3;
  ena[1074] = HAVE_addv4hf3;
  ena[1075] = HAVE_addv2sf3;
  ena[1076] = HAVE_addv8hf3;
  ena[1077] = HAVE_addvnx8hf3;
  ena[1078] = HAVE_addv4sf3;
  ena[1079] = HAVE_addvnx4sf3;
  ena[1080] = HAVE_addv2df3;
  ena[1081] = HAVE_addvnx2df3;
  ena[1082] = HAVE_subsi3;
  ena[1083] = HAVE_subdi3;
  ena[1084] = HAVE_subti3;
  ena[1085] = HAVE_subhf3;
  ena[1086] = HAVE_subsf3;
  ena[1087] = HAVE_subdf3;
  ena[1088] = HAVE_subv8qi3;
  ena[1089] = HAVE_subv4hi3;
  ena[1090] = HAVE_subv2si3;
  ena[1091] = HAVE_subv16qi3;
  ena[1092] = HAVE_subvnx16qi3;
  ena[1093] = HAVE_subv8hi3;
  ena[1094] = HAVE_subvnx8hi3;
  ena[1095] = HAVE_subv4si3;
  ena[1096] = HAVE_subvnx4si3;
  ena[1097] = HAVE_subv2di3;
  ena[1098] = HAVE_subvnx2di3;
  ena[1099] = HAVE_subvnx2qi3;
  ena[1100] = HAVE_subvnx4qi3;
  ena[1101] = HAVE_subvnx2hi3;
  ena[1102] = HAVE_subvnx8qi3;
  ena[1103] = HAVE_subvnx4hi3;
  ena[1104] = HAVE_subvnx2si3;
  ena[1105] = HAVE_subv4hf3;
  ena[1106] = HAVE_subv2sf3;
  ena[1107] = HAVE_subv8hf3;
  ena[1108] = HAVE_subvnx8hf3;
  ena[1109] = HAVE_subv4sf3;
  ena[1110] = HAVE_subvnx4sf3;
  ena[1111] = HAVE_subv2df3;
  ena[1112] = HAVE_subvnx2df3;
  ena[1113] = HAVE_mulsi3;
  ena[1114] = HAVE_muldi3;
  ena[1115] = HAVE_multi3;
  ena[1116] = HAVE_mulhf3;
  ena[1117] = HAVE_mulsf3;
  ena[1118] = HAVE_muldf3;
  ena[1119] = HAVE_mulv8qi3;
  ena[1120] = HAVE_mulv4hi3;
  ena[1121] = HAVE_mulv2si3;
  ena[1122] = HAVE_mulv16qi3;
  ena[1123] = HAVE_mulvnx16qi3;
  ena[1124] = HAVE_mulv8hi3;
  ena[1125] = HAVE_mulvnx8hi3;
  ena[1126] = HAVE_mulv4si3;
  ena[1127] = HAVE_mulvnx4si3;
  ena[1128] = HAVE_mulvnx2di3;
  ena[1129] = HAVE_mulvnx2qi3;
  ena[1130] = HAVE_mulvnx4qi3;
  ena[1131] = HAVE_mulvnx2hi3;
  ena[1132] = HAVE_mulvnx8qi3;
  ena[1133] = HAVE_mulvnx4hi3;
  ena[1134] = HAVE_mulvnx2si3;
  ena[1135] = HAVE_mulv4hf3;
  ena[1136] = HAVE_mulv2sf3;
  ena[1137] = HAVE_mulv8hf3;
  ena[1138] = HAVE_mulvnx8hf3;
  ena[1139] = HAVE_mulv4sf3;
  ena[1140] = HAVE_mulvnx4sf3;
  ena[1141] = HAVE_mulv2df3;
  ena[1142] = HAVE_mulvnx2df3;
  ena[1143] = HAVE_divsi3;
  ena[1144] = HAVE_divdi3;
  ena[1145] = HAVE_divhf3;
  ena[1146] = HAVE_divsf3;
  ena[1147] = HAVE_divdf3;
  ena[1148] = HAVE_divvnx4si3;
  ena[1149] = HAVE_divvnx2di3;
  ena[1150] = HAVE_divv4hf3;
  ena[1151] = HAVE_divv2sf3;
  ena[1152] = HAVE_divv8hf3;
  ena[1153] = HAVE_divvnx8hf3;
  ena[1154] = HAVE_divv4sf3;
  ena[1155] = HAVE_divvnx4sf3;
  ena[1156] = HAVE_divv2df3;
  ena[1157] = HAVE_divvnx2df3;
  ena[1158] = HAVE_udivsi3;
  ena[1159] = HAVE_udivdi3;
  ena[1160] = HAVE_udivvnx4si3;
  ena[1161] = HAVE_udivvnx2di3;
  ena[1162] = HAVE_modsi3;
  ena[1163] = HAVE_moddi3;
  ena[1164] = HAVE_ftruncv4hf2;
  ena[1165] = HAVE_ftruncv2sf2;
  ena[1166] = HAVE_ftruncv8hf2;
  ena[1167] = HAVE_ftruncv4sf2;
  ena[1168] = HAVE_ftruncv2df2;
  ena[1169] = HAVE_andsi3;
  ena[1170] = HAVE_anddi3;
  ena[1171] = HAVE_andvnx16bi3;
  ena[1172] = HAVE_andvnx8bi3;
  ena[1173] = HAVE_andvnx4bi3;
  ena[1174] = HAVE_andvnx2bi3;
  ena[1175] = HAVE_andv8qi3;
  ena[1176] = HAVE_andv4hi3;
  ena[1177] = HAVE_andv2si3;
  ena[1178] = HAVE_andv16qi3;
  ena[1179] = HAVE_andvnx16qi3;
  ena[1180] = HAVE_andv8hi3;
  ena[1181] = HAVE_andvnx8hi3;
  ena[1182] = HAVE_andv4si3;
  ena[1183] = HAVE_andvnx4si3;
  ena[1184] = HAVE_andv2di3;
  ena[1185] = HAVE_andvnx2di3;
  ena[1186] = HAVE_andvnx2qi3;
  ena[1187] = HAVE_andvnx4qi3;
  ena[1188] = HAVE_andvnx2hi3;
  ena[1189] = HAVE_andvnx8qi3;
  ena[1190] = HAVE_andvnx4hi3;
  ena[1191] = HAVE_andvnx2si3;
  ena[1192] = HAVE_iorsi3;
  ena[1193] = HAVE_iordi3;
  ena[1194] = HAVE_iorvnx16bi3;
  ena[1195] = HAVE_iorvnx8bi3;
  ena[1196] = HAVE_iorvnx4bi3;
  ena[1197] = HAVE_iorvnx2bi3;
  ena[1198] = HAVE_iorv8qi3;
  ena[1199] = HAVE_iorv4hi3;
  ena[1200] = HAVE_iorv2si3;
  ena[1201] = HAVE_iorv16qi3;
  ena[1202] = HAVE_iorvnx16qi3;
  ena[1203] = HAVE_iorv8hi3;
  ena[1204] = HAVE_iorvnx8hi3;
  ena[1205] = HAVE_iorv4si3;
  ena[1206] = HAVE_iorvnx4si3;
  ena[1207] = HAVE_iorv2di3;
  ena[1208] = HAVE_iorvnx2di3;
  ena[1209] = HAVE_iorvnx2qi3;
  ena[1210] = HAVE_iorvnx4qi3;
  ena[1211] = HAVE_iorvnx2hi3;
  ena[1212] = HAVE_iorvnx8qi3;
  ena[1213] = HAVE_iorvnx4hi3;
  ena[1214] = HAVE_iorvnx2si3;
  ena[1215] = HAVE_xorsi3;
  ena[1216] = HAVE_xordi3;
  ena[1217] = HAVE_xorvnx16bi3;
  ena[1218] = HAVE_xorvnx8bi3;
  ena[1219] = HAVE_xorvnx4bi3;
  ena[1220] = HAVE_xorvnx2bi3;
  ena[1221] = HAVE_xorv8qi3;
  ena[1222] = HAVE_xorv4hi3;
  ena[1223] = HAVE_xorv2si3;
  ena[1224] = HAVE_xorv16qi3;
  ena[1225] = HAVE_xorvnx16qi3;
  ena[1226] = HAVE_xorv8hi3;
  ena[1227] = HAVE_xorvnx8hi3;
  ena[1228] = HAVE_xorv4si3;
  ena[1229] = HAVE_xorvnx4si3;
  ena[1230] = HAVE_xorv2di3;
  ena[1231] = HAVE_xorvnx2di3;
  ena[1232] = HAVE_xorvnx2qi3;
  ena[1233] = HAVE_xorvnx4qi3;
  ena[1234] = HAVE_xorvnx2hi3;
  ena[1235] = HAVE_xorvnx8qi3;
  ena[1236] = HAVE_xorvnx4hi3;
  ena[1237] = HAVE_xorvnx2si3;
  ena[1238] = HAVE_ashlqi3;
  ena[1239] = HAVE_ashlhi3;
  ena[1240] = HAVE_ashlsi3;
  ena[1241] = HAVE_ashldi3;
  ena[1242] = HAVE_ashlv8qi3;
  ena[1243] = HAVE_ashlv4hi3;
  ena[1244] = HAVE_ashlv2si3;
  ena[1245] = HAVE_ashlv16qi3;
  ena[1246] = HAVE_ashlvnx16qi3;
  ena[1247] = HAVE_ashlv8hi3;
  ena[1248] = HAVE_ashlvnx8hi3;
  ena[1249] = HAVE_ashlv4si3;
  ena[1250] = HAVE_ashlvnx4si3;
  ena[1251] = HAVE_ashlv2di3;
  ena[1252] = HAVE_ashlvnx2di3;
  ena[1253] = HAVE_ashlvnx2qi3;
  ena[1254] = HAVE_ashlvnx4qi3;
  ena[1255] = HAVE_ashlvnx2hi3;
  ena[1256] = HAVE_ashlvnx8qi3;
  ena[1257] = HAVE_ashlvnx4hi3;
  ena[1258] = HAVE_ashlvnx2si3;
  ena[1259] = HAVE_ashrsi3;
  ena[1260] = HAVE_ashrdi3;
  ena[1261] = HAVE_ashrv8qi3;
  ena[1262] = HAVE_ashrv4hi3;
  ena[1263] = HAVE_ashrv2si3;
  ena[1264] = HAVE_ashrv16qi3;
  ena[1265] = HAVE_ashrvnx16qi3;
  ena[1266] = HAVE_ashrv8hi3;
  ena[1267] = HAVE_ashrvnx8hi3;
  ena[1268] = HAVE_ashrv4si3;
  ena[1269] = HAVE_ashrvnx4si3;
  ena[1270] = HAVE_ashrv2di3;
  ena[1271] = HAVE_ashrvnx2di3;
  ena[1272] = HAVE_ashrvnx2qi3;
  ena[1273] = HAVE_ashrvnx4qi3;
  ena[1274] = HAVE_ashrvnx2hi3;
  ena[1275] = HAVE_ashrvnx8qi3;
  ena[1276] = HAVE_ashrvnx4hi3;
  ena[1277] = HAVE_ashrvnx2si3;
  ena[1278] = HAVE_lshrsi3;
  ena[1279] = HAVE_lshrdi3;
  ena[1280] = HAVE_lshrv8qi3;
  ena[1281] = HAVE_lshrv4hi3;
  ena[1282] = HAVE_lshrv2si3;
  ena[1283] = HAVE_lshrv16qi3;
  ena[1284] = HAVE_lshrvnx16qi3;
  ena[1285] = HAVE_lshrv8hi3;
  ena[1286] = HAVE_lshrvnx8hi3;
  ena[1287] = HAVE_lshrv4si3;
  ena[1288] = HAVE_lshrvnx4si3;
  ena[1289] = HAVE_lshrv2di3;
  ena[1290] = HAVE_lshrvnx2di3;
  ena[1291] = HAVE_lshrvnx2qi3;
  ena[1292] = HAVE_lshrvnx4qi3;
  ena[1293] = HAVE_lshrvnx2hi3;
  ena[1294] = HAVE_lshrvnx8qi3;
  ena[1295] = HAVE_lshrvnx4hi3;
  ena[1296] = HAVE_lshrvnx2si3;
  ena[1297] = HAVE_rotlsi3;
  ena[1298] = HAVE_rotldi3;
  ena[1299] = HAVE_rotrsi3;
  ena[1300] = HAVE_rotrdi3;
  ena[1301] = HAVE_vashlv8qi3;
  ena[1302] = HAVE_vashlv4hi3;
  ena[1303] = HAVE_vashlv2si3;
  ena[1304] = HAVE_vashlv16qi3;
  ena[1305] = HAVE_vashlvnx16qi3;
  ena[1306] = HAVE_vashlv8hi3;
  ena[1307] = HAVE_vashlvnx8hi3;
  ena[1308] = HAVE_vashlv4si3;
  ena[1309] = HAVE_vashlvnx4si3;
  ena[1310] = HAVE_vashlv2di3;
  ena[1311] = HAVE_vashlvnx2di3;
  ena[1312] = HAVE_vashlvnx2qi3;
  ena[1313] = HAVE_vashlvnx4qi3;
  ena[1314] = HAVE_vashlvnx2hi3;
  ena[1315] = HAVE_vashlvnx8qi3;
  ena[1316] = HAVE_vashlvnx4hi3;
  ena[1317] = HAVE_vashlvnx2si3;
  ena[1318] = HAVE_vashrv8qi3;
  ena[1319] = HAVE_vashrv4hi3;
  ena[1320] = HAVE_vashrv2si3;
  ena[1321] = HAVE_vashrv16qi3;
  ena[1322] = HAVE_vashrvnx16qi3;
  ena[1323] = HAVE_vashrv8hi3;
  ena[1324] = HAVE_vashrvnx8hi3;
  ena[1325] = HAVE_vashrv4si3;
  ena[1326] = HAVE_vashrvnx4si3;
  ena[1327] = HAVE_vashrvnx2di3;
  ena[1328] = HAVE_vashrvnx2qi3;
  ena[1329] = HAVE_vashrvnx4qi3;
  ena[1330] = HAVE_vashrvnx2hi3;
  ena[1331] = HAVE_vashrvnx8qi3;
  ena[1332] = HAVE_vashrvnx4hi3;
  ena[1333] = HAVE_vashrvnx2si3;
  ena[1334] = HAVE_vlshrv8qi3;
  ena[1335] = HAVE_vlshrv4hi3;
  ena[1336] = HAVE_vlshrv2si3;
  ena[1337] = HAVE_vlshrv16qi3;
  ena[1338] = HAVE_vlshrvnx16qi3;
  ena[1339] = HAVE_vlshrv8hi3;
  ena[1340] = HAVE_vlshrvnx8hi3;
  ena[1341] = HAVE_vlshrv4si3;
  ena[1342] = HAVE_vlshrvnx4si3;
  ena[1343] = HAVE_vlshrvnx2di3;
  ena[1344] = HAVE_vlshrvnx2qi3;
  ena[1345] = HAVE_vlshrvnx4qi3;
  ena[1346] = HAVE_vlshrvnx2hi3;
  ena[1347] = HAVE_vlshrvnx8qi3;
  ena[1348] = HAVE_vlshrvnx4hi3;
  ena[1349] = HAVE_vlshrvnx2si3;
  ena[1350] = HAVE_sminsf3;
  ena[1351] = HAVE_smindf3;
  ena[1352] = HAVE_sminv8qi3;
  ena[1353] = HAVE_sminv4hi3;
  ena[1354] = HAVE_sminv2si3;
  ena[1355] = HAVE_sminv16qi3;
  ena[1356] = HAVE_sminvnx16qi3;
  ena[1357] = HAVE_sminv8hi3;
  ena[1358] = HAVE_sminvnx8hi3;
  ena[1359] = HAVE_sminv4si3;
  ena[1360] = HAVE_sminvnx4si3;
  ena[1361] = HAVE_sminv2di3;
  ena[1362] = HAVE_sminvnx2di3;
  ena[1363] = HAVE_sminvnx2qi3;
  ena[1364] = HAVE_sminvnx4qi3;
  ena[1365] = HAVE_sminvnx2hi3;
  ena[1366] = HAVE_sminvnx8qi3;
  ena[1367] = HAVE_sminvnx4hi3;
  ena[1368] = HAVE_sminvnx2si3;
  ena[1369] = HAVE_sminv4hf3;
  ena[1370] = HAVE_sminv2sf3;
  ena[1371] = HAVE_sminv8hf3;
  ena[1372] = HAVE_sminvnx8hf3;
  ena[1373] = HAVE_sminv4sf3;
  ena[1374] = HAVE_sminvnx4sf3;
  ena[1375] = HAVE_sminv2df3;
  ena[1376] = HAVE_sminvnx2df3;
  ena[1377] = HAVE_smaxsf3;
  ena[1378] = HAVE_smaxdf3;
  ena[1379] = HAVE_smaxv8qi3;
  ena[1380] = HAVE_smaxv4hi3;
  ena[1381] = HAVE_smaxv2si3;
  ena[1382] = HAVE_smaxv16qi3;
  ena[1383] = HAVE_smaxvnx16qi3;
  ena[1384] = HAVE_smaxv8hi3;
  ena[1385] = HAVE_smaxvnx8hi3;
  ena[1386] = HAVE_smaxv4si3;
  ena[1387] = HAVE_smaxvnx4si3;
  ena[1388] = HAVE_smaxv2di3;
  ena[1389] = HAVE_smaxvnx2di3;
  ena[1390] = HAVE_smaxvnx2qi3;
  ena[1391] = HAVE_smaxvnx4qi3;
  ena[1392] = HAVE_smaxvnx2hi3;
  ena[1393] = HAVE_smaxvnx8qi3;
  ena[1394] = HAVE_smaxvnx4hi3;
  ena[1395] = HAVE_smaxvnx2si3;
  ena[1396] = HAVE_smaxv4hf3;
  ena[1397] = HAVE_smaxv2sf3;
  ena[1398] = HAVE_smaxv8hf3;
  ena[1399] = HAVE_smaxvnx8hf3;
  ena[1400] = HAVE_smaxv4sf3;
  ena[1401] = HAVE_smaxvnx4sf3;
  ena[1402] = HAVE_smaxv2df3;
  ena[1403] = HAVE_smaxvnx2df3;
  ena[1404] = HAVE_uminv8qi3;
  ena[1405] = HAVE_uminv4hi3;
  ena[1406] = HAVE_uminv2si3;
  ena[1407] = HAVE_uminv16qi3;
  ena[1408] = HAVE_uminvnx16qi3;
  ena[1409] = HAVE_uminv8hi3;
  ena[1410] = HAVE_uminvnx8hi3;
  ena[1411] = HAVE_uminv4si3;
  ena[1412] = HAVE_uminvnx4si3;
  ena[1413] = HAVE_uminv2di3;
  ena[1414] = HAVE_uminvnx2di3;
  ena[1415] = HAVE_uminvnx2qi3;
  ena[1416] = HAVE_uminvnx4qi3;
  ena[1417] = HAVE_uminvnx2hi3;
  ena[1418] = HAVE_uminvnx8qi3;
  ena[1419] = HAVE_uminvnx4hi3;
  ena[1420] = HAVE_uminvnx2si3;
  ena[1421] = HAVE_umaxsi3;
  ena[1422] = HAVE_umaxdi3;
  ena[1423] = HAVE_umaxv8qi3;
  ena[1424] = HAVE_umaxv4hi3;
  ena[1425] = HAVE_umaxv2si3;
  ena[1426] = HAVE_umaxv16qi3;
  ena[1427] = HAVE_umaxvnx16qi3;
  ena[1428] = HAVE_umaxv8hi3;
  ena[1429] = HAVE_umaxvnx8hi3;
  ena[1430] = HAVE_umaxv4si3;
  ena[1431] = HAVE_umaxvnx4si3;
  ena[1432] = HAVE_umaxv2di3;
  ena[1433] = HAVE_umaxvnx2di3;
  ena[1434] = HAVE_umaxvnx2qi3;
  ena[1435] = HAVE_umaxvnx4qi3;
  ena[1436] = HAVE_umaxvnx2hi3;
  ena[1437] = HAVE_umaxvnx8qi3;
  ena[1438] = HAVE_umaxvnx4hi3;
  ena[1439] = HAVE_umaxvnx2si3;
  ena[1440] = HAVE_negsi2;
  ena[1441] = HAVE_negdi2;
  ena[1442] = HAVE_neghf2;
  ena[1443] = HAVE_negsf2;
  ena[1444] = HAVE_negdf2;
  ena[1445] = HAVE_negv8qi2;
  ena[1446] = HAVE_negv4hi2;
  ena[1447] = HAVE_negv2si2;
  ena[1448] = HAVE_negv16qi2;
  ena[1449] = HAVE_negvnx16qi2;
  ena[1450] = HAVE_negv8hi2;
  ena[1451] = HAVE_negvnx8hi2;
  ena[1452] = HAVE_negv4si2;
  ena[1453] = HAVE_negvnx4si2;
  ena[1454] = HAVE_negv2di2;
  ena[1455] = HAVE_negvnx2di2;
  ena[1456] = HAVE_negvnx2qi2;
  ena[1457] = HAVE_negvnx4qi2;
  ena[1458] = HAVE_negvnx2hi2;
  ena[1459] = HAVE_negvnx8qi2;
  ena[1460] = HAVE_negvnx4hi2;
  ena[1461] = HAVE_negvnx2si2;
  ena[1462] = HAVE_negv4hf2;
  ena[1463] = HAVE_negv2sf2;
  ena[1464] = HAVE_negv8hf2;
  ena[1465] = HAVE_negvnx8hf2;
  ena[1466] = HAVE_negv4sf2;
  ena[1467] = HAVE_negvnx4sf2;
  ena[1468] = HAVE_negv2df2;
  ena[1469] = HAVE_negvnx2df2;
  ena[1470] = HAVE_abssi2;
  ena[1471] = HAVE_absdi2;
  ena[1472] = HAVE_abshf2;
  ena[1473] = HAVE_abssf2;
  ena[1474] = HAVE_absdf2;
  ena[1475] = HAVE_absv8qi2;
  ena[1476] = HAVE_absv4hi2;
  ena[1477] = HAVE_absv2si2;
  ena[1478] = HAVE_absv16qi2;
  ena[1479] = HAVE_absvnx16qi2;
  ena[1480] = HAVE_absv8hi2;
  ena[1481] = HAVE_absvnx8hi2;
  ena[1482] = HAVE_absv4si2;
  ena[1483] = HAVE_absvnx4si2;
  ena[1484] = HAVE_absv2di2;
  ena[1485] = HAVE_absvnx2di2;
  ena[1486] = HAVE_absvnx2qi2;
  ena[1487] = HAVE_absvnx4qi2;
  ena[1488] = HAVE_absvnx2hi2;
  ena[1489] = HAVE_absvnx8qi2;
  ena[1490] = HAVE_absvnx4hi2;
  ena[1491] = HAVE_absvnx2si2;
  ena[1492] = HAVE_absv4hf2;
  ena[1493] = HAVE_absv2sf2;
  ena[1494] = HAVE_absv8hf2;
  ena[1495] = HAVE_absvnx8hf2;
  ena[1496] = HAVE_absv4sf2;
  ena[1497] = HAVE_absvnx4sf2;
  ena[1498] = HAVE_absv2df2;
  ena[1499] = HAVE_absvnx2df2;
  ena[1500] = HAVE_one_cmplsi2;
  ena[1501] = HAVE_one_cmpldi2;
  ena[1502] = HAVE_one_cmplvnx16bi2;
  ena[1503] = HAVE_one_cmplvnx8bi2;
  ena[1504] = HAVE_one_cmplvnx4bi2;
  ena[1505] = HAVE_one_cmplvnx2bi2;
  ena[1506] = HAVE_one_cmplv8qi2;
  ena[1507] = HAVE_one_cmplv4hi2;
  ena[1508] = HAVE_one_cmplv2si2;
  ena[1509] = HAVE_one_cmplv16qi2;
  ena[1510] = HAVE_one_cmplvnx16qi2;
  ena[1511] = HAVE_one_cmplv8hi2;
  ena[1512] = HAVE_one_cmplvnx8hi2;
  ena[1513] = HAVE_one_cmplv4si2;
  ena[1514] = HAVE_one_cmplvnx4si2;
  ena[1515] = HAVE_one_cmplv2di2;
  ena[1516] = HAVE_one_cmplvnx2di2;
  ena[1517] = HAVE_one_cmplvnx2qi2;
  ena[1518] = HAVE_one_cmplvnx4qi2;
  ena[1519] = HAVE_one_cmplvnx2hi2;
  ena[1520] = HAVE_one_cmplvnx8qi2;
  ena[1521] = HAVE_one_cmplvnx4hi2;
  ena[1522] = HAVE_one_cmplvnx2si2;
  ena[1523] = HAVE_bswaphi2;
  ena[1524] = HAVE_bswapsi2;
  ena[1525] = HAVE_bswapdi2;
  ena[1526] = HAVE_bswapv4hi2;
  ena[1527] = HAVE_bswapv2si2;
  ena[1528] = HAVE_bswapv8hi2;
  ena[1529] = HAVE_bswapv4si2;
  ena[1530] = HAVE_bswapv2di2;
  ena[1531] = HAVE_ffssi2;
  ena[1532] = HAVE_ffsdi2;
  ena[1533] = HAVE_clzsi2;
  ena[1534] = HAVE_clzdi2;
  ena[1535] = HAVE_clzv8qi2;
  ena[1536] = HAVE_clzv4hi2;
  ena[1537] = HAVE_clzv2si2;
  ena[1538] = HAVE_clzv16qi2;
  ena[1539] = HAVE_clzvnx16qi2;
  ena[1540] = HAVE_clzv8hi2;
  ena[1541] = HAVE_clzvnx8hi2;
  ena[1542] = HAVE_clzv4si2;
  ena[1543] = HAVE_clzvnx4si2;
  ena[1544] = HAVE_clzvnx2di2;
  ena[1545] = HAVE_clzvnx2qi2;
  ena[1546] = HAVE_clzvnx4qi2;
  ena[1547] = HAVE_clzvnx2hi2;
  ena[1548] = HAVE_clzvnx8qi2;
  ena[1549] = HAVE_clzvnx4hi2;
  ena[1550] = HAVE_clzvnx2si2;
  ena[1551] = HAVE_ctzsi2;
  ena[1552] = HAVE_ctzdi2;
  ena[1553] = HAVE_ctzv2si2;
  ena[1554] = HAVE_ctzv4si2;
  ena[1555] = HAVE_clrsbsi2;
  ena[1556] = HAVE_clrsbdi2;
  ena[1557] = HAVE_clrsbv8qi2;
  ena[1558] = HAVE_clrsbv4hi2;
  ena[1559] = HAVE_clrsbv2si2;
  ena[1560] = HAVE_clrsbv16qi2;
  ena[1561] = HAVE_clrsbvnx16qi2;
  ena[1562] = HAVE_clrsbv8hi2;
  ena[1563] = HAVE_clrsbvnx8hi2;
  ena[1564] = HAVE_clrsbv4si2;
  ena[1565] = HAVE_clrsbvnx4si2;
  ena[1566] = HAVE_clrsbvnx2di2;
  ena[1567] = HAVE_clrsbvnx2qi2;
  ena[1568] = HAVE_clrsbvnx4qi2;
  ena[1569] = HAVE_clrsbvnx2hi2;
  ena[1570] = HAVE_clrsbvnx8qi2;
  ena[1571] = HAVE_clrsbvnx4hi2;
  ena[1572] = HAVE_clrsbvnx2si2;
  ena[1573] = HAVE_popcountsi2;
  ena[1574] = HAVE_popcountdi2;
  ena[1575] = HAVE_popcountv8qi2;
  ena[1576] = HAVE_popcountv16qi2;
  ena[1577] = HAVE_popcountvnx16qi2;
  ena[1578] = HAVE_popcountvnx8hi2;
  ena[1579] = HAVE_popcountvnx4si2;
  ena[1580] = HAVE_popcountvnx2di2;
  ena[1581] = HAVE_popcountvnx2qi2;
  ena[1582] = HAVE_popcountvnx4qi2;
  ena[1583] = HAVE_popcountvnx2hi2;
  ena[1584] = HAVE_popcountvnx8qi2;
  ena[1585] = HAVE_popcountvnx4hi2;
  ena[1586] = HAVE_popcountvnx2si2;
  ena[1587] = HAVE_sqrthf2;
  ena[1588] = HAVE_sqrtsf2;
  ena[1589] = HAVE_sqrtdf2;
  ena[1590] = HAVE_sqrtv4hf2;
  ena[1591] = HAVE_sqrtv2sf2;
  ena[1592] = HAVE_sqrtv8hf2;
  ena[1593] = HAVE_sqrtvnx8hf2;
  ena[1594] = HAVE_sqrtv4sf2;
  ena[1595] = HAVE_sqrtvnx4sf2;
  ena[1596] = HAVE_sqrtv2df2;
  ena[1597] = HAVE_sqrtvnx2df2;
  ena[1598] = HAVE_movqi;
  ena[1599] = HAVE_movhi;
  ena[1600] = HAVE_movsi;
  ena[1601] = HAVE_movdi;
  ena[1602] = HAVE_movti;
  ena[1603] = HAVE_movoi;
  ena[1604] = HAVE_movci;
  ena[1605] = HAVE_movxi;
  ena[1606] = HAVE_movhf;
  ena[1607] = HAVE_movbf;
  ena[1608] = HAVE_movsf;
  ena[1609] = HAVE_movdf;
  ena[1610] = HAVE_movtf;
  ena[1611] = HAVE_movvnx16bi;
  ena[1612] = HAVE_movvnx8bi;
  ena[1613] = HAVE_movvnx4bi;
  ena[1614] = HAVE_movvnx2bi;
  ena[1615] = HAVE_movv8qi;
  ena[1616] = HAVE_movv4hi;
  ena[1617] = HAVE_movv2si;
  ena[1618] = HAVE_movv16qi;
  ena[1619] = HAVE_movvnx16qi;
  ena[1620] = HAVE_movv8hi;
  ena[1621] = HAVE_movvnx8hi;
  ena[1622] = HAVE_movv4si;
  ena[1623] = HAVE_movvnx4si;
  ena[1624] = HAVE_movv2di;
  ena[1625] = HAVE_movvnx2di;
  ena[1626] = HAVE_movvnx32qi;
  ena[1627] = HAVE_movvnx16hi;
  ena[1628] = HAVE_movvnx8si;
  ena[1629] = HAVE_movvnx4di;
  ena[1630] = HAVE_movvnx48qi;
  ena[1631] = HAVE_movvnx24hi;
  ena[1632] = HAVE_movvnx12si;
  ena[1633] = HAVE_movvnx6di;
  ena[1634] = HAVE_movvnx64qi;
  ena[1635] = HAVE_movvnx32hi;
  ena[1636] = HAVE_movvnx16si;
  ena[1637] = HAVE_movvnx8di;
  ena[1638] = HAVE_movvnx2qi;
  ena[1639] = HAVE_movvnx4qi;
  ena[1640] = HAVE_movvnx2hi;
  ena[1641] = HAVE_movvnx8qi;
  ena[1642] = HAVE_movvnx4hi;
  ena[1643] = HAVE_movvnx2si;
  ena[1644] = HAVE_movv4bf;
  ena[1645] = HAVE_movv4hf;
  ena[1646] = HAVE_movv2sf;
  ena[1647] = HAVE_movv8bf;
  ena[1648] = HAVE_movv8hf;
  ena[1649] = HAVE_movvnx8bf;
  ena[1650] = HAVE_movvnx8hf;
  ena[1651] = HAVE_movv4sf;
  ena[1652] = HAVE_movvnx4sf;
  ena[1653] = HAVE_movv2df;
  ena[1654] = HAVE_movvnx2df;
  ena[1655] = HAVE_movvnx16bf;
  ena[1656] = HAVE_movvnx16hf;
  ena[1657] = HAVE_movvnx8sf;
  ena[1658] = HAVE_movvnx4df;
  ena[1659] = HAVE_movvnx24bf;
  ena[1660] = HAVE_movvnx24hf;
  ena[1661] = HAVE_movvnx12sf;
  ena[1662] = HAVE_movvnx6df;
  ena[1663] = HAVE_movvnx32bf;
  ena[1664] = HAVE_movvnx32hf;
  ena[1665] = HAVE_movvnx16sf;
  ena[1666] = HAVE_movvnx8df;
  ena[1667] = HAVE_movvnx2bf;
  ena[1668] = HAVE_movvnx2hf;
  ena[1669] = HAVE_movvnx4bf;
  ena[1670] = HAVE_movvnx4hf;
  ena[1671] = HAVE_movvnx2sf;
  ena[1672] = HAVE_movmisalignv8qi;
  ena[1673] = HAVE_movmisalignv4hi;
  ena[1674] = HAVE_movmisalignv2si;
  ena[1675] = HAVE_movmisalignv16qi;
  ena[1676] = HAVE_movmisalignvnx16qi;
  ena[1677] = HAVE_movmisalignv8hi;
  ena[1678] = HAVE_movmisalignvnx8hi;
  ena[1679] = HAVE_movmisalignv4si;
  ena[1680] = HAVE_movmisalignvnx4si;
  ena[1681] = HAVE_movmisalignv2di;
  ena[1682] = HAVE_movmisalignvnx2di;
  ena[1683] = HAVE_movmisalignvnx2qi;
  ena[1684] = HAVE_movmisalignvnx4qi;
  ena[1685] = HAVE_movmisalignvnx2hi;
  ena[1686] = HAVE_movmisalignvnx8qi;
  ena[1687] = HAVE_movmisalignvnx4hi;
  ena[1688] = HAVE_movmisalignvnx2si;
  ena[1689] = HAVE_movmisalignv2sf;
  ena[1690] = HAVE_movmisalignvnx8bf;
  ena[1691] = HAVE_movmisalignvnx8hf;
  ena[1692] = HAVE_movmisalignv4sf;
  ena[1693] = HAVE_movmisalignvnx4sf;
  ena[1694] = HAVE_movmisalignv2df;
  ena[1695] = HAVE_movmisalignvnx2df;
  ena[1696] = HAVE_movmisalignvnx2bf;
  ena[1697] = HAVE_movmisalignvnx2hf;
  ena[1698] = HAVE_movmisalignvnx4bf;
  ena[1699] = HAVE_movmisalignvnx4hf;
  ena[1700] = HAVE_movmisalignvnx2sf;
  ena[1701] = HAVE_insvsi;
  ena[1702] = HAVE_insvdi;
  ena[1703] = HAVE_cbranchcc4;
  ena[1704] = HAVE_cbranchsi4;
  ena[1705] = HAVE_cbranchdi4;
  ena[1706] = HAVE_cbranchsf4;
  ena[1707] = HAVE_cbranchdf4;
  ena[1708] = HAVE_cbranchvnx16bi4;
  ena[1709] = HAVE_cbranchvnx8bi4;
  ena[1710] = HAVE_cbranchvnx4bi4;
  ena[1711] = HAVE_cbranchvnx2bi4;
  ena[1712] = HAVE_negsicc;
  ena[1713] = HAVE_negdicc;
  ena[1714] = HAVE_notsicc;
  ena[1715] = HAVE_notdicc;
  ena[1716] = HAVE_movqicc;
  ena[1717] = HAVE_movhicc;
  ena[1718] = HAVE_movsicc;
  ena[1719] = HAVE_movdicc;
  ena[1720] = HAVE_movsfcc;
  ena[1721] = HAVE_movdfcc;
  ena[1722] = HAVE_cond_addvnx16qi;
  ena[1723] = HAVE_cond_addvnx8hi;
  ena[1724] = HAVE_cond_addvnx4si;
  ena[1725] = HAVE_cond_addvnx2di;
  ena[1726] = HAVE_cond_addvnx2qi;
  ena[1727] = HAVE_cond_addvnx4qi;
  ena[1728] = HAVE_cond_addvnx2hi;
  ena[1729] = HAVE_cond_addvnx8qi;
  ena[1730] = HAVE_cond_addvnx4hi;
  ena[1731] = HAVE_cond_addvnx2si;
  ena[1732] = HAVE_cond_addvnx8hf;
  ena[1733] = HAVE_cond_addvnx4sf;
  ena[1734] = HAVE_cond_addvnx2df;
  ena[1735] = HAVE_cond_subvnx16qi;
  ena[1736] = HAVE_cond_subvnx8hi;
  ena[1737] = HAVE_cond_subvnx4si;
  ena[1738] = HAVE_cond_subvnx2di;
  ena[1739] = HAVE_cond_subvnx2qi;
  ena[1740] = HAVE_cond_subvnx4qi;
  ena[1741] = HAVE_cond_subvnx2hi;
  ena[1742] = HAVE_cond_subvnx8qi;
  ena[1743] = HAVE_cond_subvnx4hi;
  ena[1744] = HAVE_cond_subvnx2si;
  ena[1745] = HAVE_cond_subvnx8hf;
  ena[1746] = HAVE_cond_subvnx4sf;
  ena[1747] = HAVE_cond_subvnx2df;
  ena[1748] = HAVE_cond_mulvnx16qi;
  ena[1749] = HAVE_cond_mulvnx8hi;
  ena[1750] = HAVE_cond_mulvnx4si;
  ena[1751] = HAVE_cond_mulvnx2di;
  ena[1752] = HAVE_cond_mulvnx2qi;
  ena[1753] = HAVE_cond_mulvnx4qi;
  ena[1754] = HAVE_cond_mulvnx2hi;
  ena[1755] = HAVE_cond_mulvnx8qi;
  ena[1756] = HAVE_cond_mulvnx4hi;
  ena[1757] = HAVE_cond_mulvnx2si;
  ena[1758] = HAVE_cond_mulvnx8hf;
  ena[1759] = HAVE_cond_mulvnx4sf;
  ena[1760] = HAVE_cond_mulvnx2df;
  ena[1761] = HAVE_cond_divvnx4si;
  ena[1762] = HAVE_cond_divvnx2di;
  ena[1763] = HAVE_cond_divvnx8hf;
  ena[1764] = HAVE_cond_divvnx4sf;
  ena[1765] = HAVE_cond_divvnx2df;
  ena[1766] = HAVE_cond_udivvnx4si;
  ena[1767] = HAVE_cond_udivvnx2di;
  ena[1768] = HAVE_cond_andvnx16qi;
  ena[1769] = HAVE_cond_andvnx8hi;
  ena[1770] = HAVE_cond_andvnx4si;
  ena[1771] = HAVE_cond_andvnx2di;
  ena[1772] = HAVE_cond_andvnx2qi;
  ena[1773] = HAVE_cond_andvnx4qi;
  ena[1774] = HAVE_cond_andvnx2hi;
  ena[1775] = HAVE_cond_andvnx8qi;
  ena[1776] = HAVE_cond_andvnx4hi;
  ena[1777] = HAVE_cond_andvnx2si;
  ena[1778] = HAVE_cond_iorvnx16qi;
  ena[1779] = HAVE_cond_iorvnx8hi;
  ena[1780] = HAVE_cond_iorvnx4si;
  ena[1781] = HAVE_cond_iorvnx2di;
  ena[1782] = HAVE_cond_iorvnx2qi;
  ena[1783] = HAVE_cond_iorvnx4qi;
  ena[1784] = HAVE_cond_iorvnx2hi;
  ena[1785] = HAVE_cond_iorvnx8qi;
  ena[1786] = HAVE_cond_iorvnx4hi;
  ena[1787] = HAVE_cond_iorvnx2si;
  ena[1788] = HAVE_cond_xorvnx16qi;
  ena[1789] = HAVE_cond_xorvnx8hi;
  ena[1790] = HAVE_cond_xorvnx4si;
  ena[1791] = HAVE_cond_xorvnx2di;
  ena[1792] = HAVE_cond_xorvnx2qi;
  ena[1793] = HAVE_cond_xorvnx4qi;
  ena[1794] = HAVE_cond_xorvnx2hi;
  ena[1795] = HAVE_cond_xorvnx8qi;
  ena[1796] = HAVE_cond_xorvnx4hi;
  ena[1797] = HAVE_cond_xorvnx2si;
  ena[1798] = HAVE_cond_ashlvnx16qi;
  ena[1799] = HAVE_cond_ashlvnx8hi;
  ena[1800] = HAVE_cond_ashlvnx4si;
  ena[1801] = HAVE_cond_ashlvnx2di;
  ena[1802] = HAVE_cond_ashlvnx2qi;
  ena[1803] = HAVE_cond_ashlvnx4qi;
  ena[1804] = HAVE_cond_ashlvnx2hi;
  ena[1805] = HAVE_cond_ashlvnx8qi;
  ena[1806] = HAVE_cond_ashlvnx4hi;
  ena[1807] = HAVE_cond_ashlvnx2si;
  ena[1808] = HAVE_cond_ashrvnx16qi;
  ena[1809] = HAVE_cond_ashrvnx8hi;
  ena[1810] = HAVE_cond_ashrvnx4si;
  ena[1811] = HAVE_cond_ashrvnx2di;
  ena[1812] = HAVE_cond_ashrvnx2qi;
  ena[1813] = HAVE_cond_ashrvnx4qi;
  ena[1814] = HAVE_cond_ashrvnx2hi;
  ena[1815] = HAVE_cond_ashrvnx8qi;
  ena[1816] = HAVE_cond_ashrvnx4hi;
  ena[1817] = HAVE_cond_ashrvnx2si;
  ena[1818] = HAVE_cond_lshrvnx16qi;
  ena[1819] = HAVE_cond_lshrvnx8hi;
  ena[1820] = HAVE_cond_lshrvnx4si;
  ena[1821] = HAVE_cond_lshrvnx2di;
  ena[1822] = HAVE_cond_lshrvnx2qi;
  ena[1823] = HAVE_cond_lshrvnx4qi;
  ena[1824] = HAVE_cond_lshrvnx2hi;
  ena[1825] = HAVE_cond_lshrvnx8qi;
  ena[1826] = HAVE_cond_lshrvnx4hi;
  ena[1827] = HAVE_cond_lshrvnx2si;
  ena[1828] = HAVE_cond_sminvnx16qi;
  ena[1829] = HAVE_cond_sminvnx8hi;
  ena[1830] = HAVE_cond_sminvnx4si;
  ena[1831] = HAVE_cond_sminvnx2di;
  ena[1832] = HAVE_cond_sminvnx2qi;
  ena[1833] = HAVE_cond_sminvnx4qi;
  ena[1834] = HAVE_cond_sminvnx2hi;
  ena[1835] = HAVE_cond_sminvnx8qi;
  ena[1836] = HAVE_cond_sminvnx4hi;
  ena[1837] = HAVE_cond_sminvnx2si;
  ena[1838] = HAVE_cond_sminvnx8hf;
  ena[1839] = HAVE_cond_sminvnx4sf;
  ena[1840] = HAVE_cond_sminvnx2df;
  ena[1841] = HAVE_cond_smaxvnx16qi;
  ena[1842] = HAVE_cond_smaxvnx8hi;
  ena[1843] = HAVE_cond_smaxvnx4si;
  ena[1844] = HAVE_cond_smaxvnx2di;
  ena[1845] = HAVE_cond_smaxvnx2qi;
  ena[1846] = HAVE_cond_smaxvnx4qi;
  ena[1847] = HAVE_cond_smaxvnx2hi;
  ena[1848] = HAVE_cond_smaxvnx8qi;
  ena[1849] = HAVE_cond_smaxvnx4hi;
  ena[1850] = HAVE_cond_smaxvnx2si;
  ena[1851] = HAVE_cond_smaxvnx8hf;
  ena[1852] = HAVE_cond_smaxvnx4sf;
  ena[1853] = HAVE_cond_smaxvnx2df;
  ena[1854] = HAVE_cond_uminvnx16qi;
  ena[1855] = HAVE_cond_uminvnx8hi;
  ena[1856] = HAVE_cond_uminvnx4si;
  ena[1857] = HAVE_cond_uminvnx2di;
  ena[1858] = HAVE_cond_uminvnx2qi;
  ena[1859] = HAVE_cond_uminvnx4qi;
  ena[1860] = HAVE_cond_uminvnx2hi;
  ena[1861] = HAVE_cond_uminvnx8qi;
  ena[1862] = HAVE_cond_uminvnx4hi;
  ena[1863] = HAVE_cond_uminvnx2si;
  ena[1864] = HAVE_cond_umaxvnx16qi;
  ena[1865] = HAVE_cond_umaxvnx8hi;
  ena[1866] = HAVE_cond_umaxvnx4si;
  ena[1867] = HAVE_cond_umaxvnx2di;
  ena[1868] = HAVE_cond_umaxvnx2qi;
  ena[1869] = HAVE_cond_umaxvnx4qi;
  ena[1870] = HAVE_cond_umaxvnx2hi;
  ena[1871] = HAVE_cond_umaxvnx8qi;
  ena[1872] = HAVE_cond_umaxvnx4hi;
  ena[1873] = HAVE_cond_umaxvnx2si;
  ena[1874] = HAVE_cond_fmavnx16qi;
  ena[1875] = HAVE_cond_fmavnx8hi;
  ena[1876] = HAVE_cond_fmavnx4si;
  ena[1877] = HAVE_cond_fmavnx2di;
  ena[1878] = HAVE_cond_fmavnx2qi;
  ena[1879] = HAVE_cond_fmavnx4qi;
  ena[1880] = HAVE_cond_fmavnx2hi;
  ena[1881] = HAVE_cond_fmavnx8qi;
  ena[1882] = HAVE_cond_fmavnx4hi;
  ena[1883] = HAVE_cond_fmavnx2si;
  ena[1884] = HAVE_cond_fmavnx8hf;
  ena[1885] = HAVE_cond_fmavnx4sf;
  ena[1886] = HAVE_cond_fmavnx2df;
  ena[1887] = HAVE_cond_fmsvnx8hf;
  ena[1888] = HAVE_cond_fmsvnx4sf;
  ena[1889] = HAVE_cond_fmsvnx2df;
  ena[1890] = HAVE_cond_fnmavnx16qi;
  ena[1891] = HAVE_cond_fnmavnx8hi;
  ena[1892] = HAVE_cond_fnmavnx4si;
  ena[1893] = HAVE_cond_fnmavnx2di;
  ena[1894] = HAVE_cond_fnmavnx2qi;
  ena[1895] = HAVE_cond_fnmavnx4qi;
  ena[1896] = HAVE_cond_fnmavnx2hi;
  ena[1897] = HAVE_cond_fnmavnx8qi;
  ena[1898] = HAVE_cond_fnmavnx4hi;
  ena[1899] = HAVE_cond_fnmavnx2si;
  ena[1900] = HAVE_cond_fnmavnx8hf;
  ena[1901] = HAVE_cond_fnmavnx4sf;
  ena[1902] = HAVE_cond_fnmavnx2df;
  ena[1903] = HAVE_cond_fnmsvnx8hf;
  ena[1904] = HAVE_cond_fnmsvnx4sf;
  ena[1905] = HAVE_cond_fnmsvnx2df;
  ena[1906] = HAVE_cmovsi6;
  ena[1907] = HAVE_cmovdi6;
  ena[1908] = HAVE_cmovsf6;
  ena[1909] = HAVE_cmovdf6;
  ena[1910] = HAVE_cstorecc4;
  ena[1911] = HAVE_cstoresi4;
  ena[1912] = HAVE_cstoredi4;
  ena[1913] = HAVE_cstoresf4;
  ena[1914] = HAVE_cstoredf4;
  ena[1915] = HAVE_addvsi4;
  ena[1916] = HAVE_addvdi4;
  ena[1917] = HAVE_addvti4;
  ena[1918] = HAVE_subvsi4;
  ena[1919] = HAVE_subvdi4;
  ena[1920] = HAVE_subvti4;
  ena[1921] = HAVE_uaddvsi4;
  ena[1922] = HAVE_uaddvdi4;
  ena[1923] = HAVE_uaddvti4;
  ena[1924] = HAVE_usubvsi4;
  ena[1925] = HAVE_usubvdi4;
  ena[1926] = HAVE_usubvti4;
  ena[1927] = HAVE_negvsi3;
  ena[1928] = HAVE_negvdi3;
  ena[1929] = HAVE_negvti3;
  ena[1930] = HAVE_smuldi3_highpart;
  ena[1931] = HAVE_smulvnx16qi3_highpart;
  ena[1932] = HAVE_smulvnx8hi3_highpart;
  ena[1933] = HAVE_smulvnx4si3_highpart;
  ena[1934] = HAVE_smulvnx2di3_highpart;
  ena[1935] = HAVE_smulvnx2qi3_highpart;
  ena[1936] = HAVE_smulvnx4qi3_highpart;
  ena[1937] = HAVE_smulvnx2hi3_highpart;
  ena[1938] = HAVE_smulvnx8qi3_highpart;
  ena[1939] = HAVE_smulvnx4hi3_highpart;
  ena[1940] = HAVE_smulvnx2si3_highpart;
  ena[1941] = HAVE_umuldi3_highpart;
  ena[1942] = HAVE_umulvnx16qi3_highpart;
  ena[1943] = HAVE_umulvnx8hi3_highpart;
  ena[1944] = HAVE_umulvnx4si3_highpart;
  ena[1945] = HAVE_umulvnx2di3_highpart;
  ena[1946] = HAVE_umulvnx2qi3_highpart;
  ena[1947] = HAVE_umulvnx4qi3_highpart;
  ena[1948] = HAVE_umulvnx2hi3_highpart;
  ena[1949] = HAVE_umulvnx8qi3_highpart;
  ena[1950] = HAVE_umulvnx4hi3_highpart;
  ena[1951] = HAVE_umulvnx2si3_highpart;
  ena[1952] = HAVE_cpymemdi;
  ena[1953] = HAVE_setmemdi;
  ena[1954] = HAVE_fmahf4;
  ena[1955] = HAVE_fmasf4;
  ena[1956] = HAVE_fmadf4;
  ena[1957] = HAVE_fmavnx16qi4;
  ena[1958] = HAVE_fmavnx8hi4;
  ena[1959] = HAVE_fmavnx4si4;
  ena[1960] = HAVE_fmavnx2di4;
  ena[1961] = HAVE_fmavnx2qi4;
  ena[1962] = HAVE_fmavnx4qi4;
  ena[1963] = HAVE_fmavnx2hi4;
  ena[1964] = HAVE_fmavnx8qi4;
  ena[1965] = HAVE_fmavnx4hi4;
  ena[1966] = HAVE_fmavnx2si4;
  ena[1967] = HAVE_fmav4hf4;
  ena[1968] = HAVE_fmav2sf4;
  ena[1969] = HAVE_fmav8hf4;
  ena[1970] = HAVE_fmavnx8hf4;
  ena[1971] = HAVE_fmav4sf4;
  ena[1972] = HAVE_fmavnx4sf4;
  ena[1973] = HAVE_fmav2df4;
  ena[1974] = HAVE_fmavnx2df4;
  ena[1975] = HAVE_fmssf4;
  ena[1976] = HAVE_fmsdf4;
  ena[1977] = HAVE_fmsvnx8hf4;
  ena[1978] = HAVE_fmsvnx4sf4;
  ena[1979] = HAVE_fmsvnx2df4;
  ena[1980] = HAVE_fnmahf4;
  ena[1981] = HAVE_fnmasf4;
  ena[1982] = HAVE_fnmadf4;
  ena[1983] = HAVE_fnmavnx16qi4;
  ena[1984] = HAVE_fnmavnx8hi4;
  ena[1985] = HAVE_fnmavnx4si4;
  ena[1986] = HAVE_fnmavnx2di4;
  ena[1987] = HAVE_fnmavnx2qi4;
  ena[1988] = HAVE_fnmavnx4qi4;
  ena[1989] = HAVE_fnmavnx2hi4;
  ena[1990] = HAVE_fnmavnx8qi4;
  ena[1991] = HAVE_fnmavnx4hi4;
  ena[1992] = HAVE_fnmavnx2si4;
  ena[1993] = HAVE_fnmav4hf4;
  ena[1994] = HAVE_fnmav2sf4;
  ena[1995] = HAVE_fnmav8hf4;
  ena[1996] = HAVE_fnmavnx8hf4;
  ena[1997] = HAVE_fnmav4sf4;
  ena[1998] = HAVE_fnmavnx4sf4;
  ena[1999] = HAVE_fnmav2df4;
  ena[2000] = HAVE_fnmavnx2df4;
  ena[2001] = HAVE_fnmssf4;
  ena[2002] = HAVE_fnmsdf4;
  ena[2003] = HAVE_fnmsvnx8hf4;
  ena[2004] = HAVE_fnmsvnx4sf4;
  ena[2005] = HAVE_fnmsvnx2df4;
  ena[2006] = HAVE_rinthf2;
  ena[2007] = HAVE_rintsf2;
  ena[2008] = HAVE_rintdf2;
  ena[2009] = HAVE_rintv4hf2;
  ena[2010] = HAVE_rintv2sf2;
  ena[2011] = HAVE_rintv8hf2;
  ena[2012] = HAVE_rintvnx8hf2;
  ena[2013] = HAVE_rintv4sf2;
  ena[2014] = HAVE_rintvnx4sf2;
  ena[2015] = HAVE_rintv2df2;
  ena[2016] = HAVE_rintvnx2df2;
  ena[2017] = HAVE_roundhf2;
  ena[2018] = HAVE_roundsf2;
  ena[2019] = HAVE_rounddf2;
  ena[2020] = HAVE_roundv4hf2;
  ena[2021] = HAVE_roundv2sf2;
  ena[2022] = HAVE_roundv8hf2;
  ena[2023] = HAVE_roundvnx8hf2;
  ena[2024] = HAVE_roundv4sf2;
  ena[2025] = HAVE_roundvnx4sf2;
  ena[2026] = HAVE_roundv2df2;
  ena[2027] = HAVE_roundvnx2df2;
  ena[2028] = HAVE_floorhf2;
  ena[2029] = HAVE_floorsf2;
  ena[2030] = HAVE_floordf2;
  ena[2031] = HAVE_floorv4hf2;
  ena[2032] = HAVE_floorv2sf2;
  ena[2033] = HAVE_floorv8hf2;
  ena[2034] = HAVE_floorvnx8hf2;
  ena[2035] = HAVE_floorv4sf2;
  ena[2036] = HAVE_floorvnx4sf2;
  ena[2037] = HAVE_floorv2df2;
  ena[2038] = HAVE_floorvnx2df2;
  ena[2039] = HAVE_ceilhf2;
  ena[2040] = HAVE_ceilsf2;
  ena[2041] = HAVE_ceildf2;
  ena[2042] = HAVE_ceilv4hf2;
  ena[2043] = HAVE_ceilv2sf2;
  ena[2044] = HAVE_ceilv8hf2;
  ena[2045] = HAVE_ceilvnx8hf2;
  ena[2046] = HAVE_ceilv4sf2;
  ena[2047] = HAVE_ceilvnx4sf2;
  ena[2048] = HAVE_ceilv2df2;
  ena[2049] = HAVE_ceilvnx2df2;
  ena[2050] = HAVE_btrunchf2;
  ena[2051] = HAVE_btruncsf2;
  ena[2052] = HAVE_btruncdf2;
  ena[2053] = HAVE_btruncv4hf2;
  ena[2054] = HAVE_btruncv2sf2;
  ena[2055] = HAVE_btruncv8hf2;
  ena[2056] = HAVE_btruncvnx8hf2;
  ena[2057] = HAVE_btruncv4sf2;
  ena[2058] = HAVE_btruncvnx4sf2;
  ena[2059] = HAVE_btruncv2df2;
  ena[2060] = HAVE_btruncvnx2df2;
  ena[2061] = HAVE_nearbyinthf2;
  ena[2062] = HAVE_nearbyintsf2;
  ena[2063] = HAVE_nearbyintdf2;
  ena[2064] = HAVE_nearbyintv4hf2;
  ena[2065] = HAVE_nearbyintv2sf2;
  ena[2066] = HAVE_nearbyintv8hf2;
  ena[2067] = HAVE_nearbyintvnx8hf2;
  ena[2068] = HAVE_nearbyintv4sf2;
  ena[2069] = HAVE_nearbyintvnx4sf2;
  ena[2070] = HAVE_nearbyintv2df2;
  ena[2071] = HAVE_nearbyintvnx2df2;
  ena[2072] = HAVE_copysignsf3;
  ena[2073] = HAVE_copysigndf3;
  ena[2074] = HAVE_copysignv4hf3;
  ena[2075] = HAVE_copysignv2sf3;
  ena[2076] = HAVE_copysignv8hf3;
  ena[2077] = HAVE_copysignvnx8hf3;
  ena[2078] = HAVE_copysignv4sf3;
  ena[2079] = HAVE_copysignvnx4sf3;
  ena[2080] = HAVE_copysignv2df3;
  ena[2081] = HAVE_copysignvnx2df3;
  ena[2082] = HAVE_xorsignsf3;
  ena[2083] = HAVE_xorsigndf3;
  ena[2084] = HAVE_xorsignv4hf3;
  ena[2085] = HAVE_xorsignv2sf3;
  ena[2086] = HAVE_xorsignv8hf3;
  ena[2087] = HAVE_xorsignvnx8hf3;
  ena[2088] = HAVE_xorsignv4sf3;
  ena[2089] = HAVE_xorsignvnx4sf3;
  ena[2090] = HAVE_xorsignv2df3;
  ena[2091] = HAVE_xorsignvnx2df3;
  ena[2092] = HAVE_cadd90vnx16qi3;
  ena[2093] = HAVE_cadd90vnx8hi3;
  ena[2094] = HAVE_cadd90vnx4si3;
  ena[2095] = HAVE_cadd90vnx2di3;
  ena[2096] = HAVE_cadd90v4hf3;
  ena[2097] = HAVE_cadd90v2sf3;
  ena[2098] = HAVE_cadd90v8hf3;
  ena[2099] = HAVE_cadd90vnx8hf3;
  ena[2100] = HAVE_cadd90v4sf3;
  ena[2101] = HAVE_cadd90vnx4sf3;
  ena[2102] = HAVE_cadd90v2df3;
  ena[2103] = HAVE_cadd90vnx2df3;
  ena[2104] = HAVE_cadd270vnx16qi3;
  ena[2105] = HAVE_cadd270vnx8hi3;
  ena[2106] = HAVE_cadd270vnx4si3;
  ena[2107] = HAVE_cadd270vnx2di3;
  ena[2108] = HAVE_cadd270v4hf3;
  ena[2109] = HAVE_cadd270v2sf3;
  ena[2110] = HAVE_cadd270v8hf3;
  ena[2111] = HAVE_cadd270vnx8hf3;
  ena[2112] = HAVE_cadd270v4sf3;
  ena[2113] = HAVE_cadd270vnx4sf3;
  ena[2114] = HAVE_cadd270v2df3;
  ena[2115] = HAVE_cadd270vnx2df3;
  ena[2116] = HAVE_cmulvnx16qi3;
  ena[2117] = HAVE_cmulvnx8hi3;
  ena[2118] = HAVE_cmulvnx4si3;
  ena[2119] = HAVE_cmulvnx2di3;
  ena[2120] = HAVE_cmulv4hf3;
  ena[2121] = HAVE_cmulv2sf3;
  ena[2122] = HAVE_cmulv8hf3;
  ena[2123] = HAVE_cmulvnx8hf3;
  ena[2124] = HAVE_cmulv4sf3;
  ena[2125] = HAVE_cmulvnx4sf3;
  ena[2126] = HAVE_cmulv2df3;
  ena[2127] = HAVE_cmulvnx2df3;
  ena[2128] = HAVE_cmul_conjvnx16qi3;
  ena[2129] = HAVE_cmul_conjvnx8hi3;
  ena[2130] = HAVE_cmul_conjvnx4si3;
  ena[2131] = HAVE_cmul_conjvnx2di3;
  ena[2132] = HAVE_cmul_conjv4hf3;
  ena[2133] = HAVE_cmul_conjv2sf3;
  ena[2134] = HAVE_cmul_conjv8hf3;
  ena[2135] = HAVE_cmul_conjvnx8hf3;
  ena[2136] = HAVE_cmul_conjv4sf3;
  ena[2137] = HAVE_cmul_conjvnx4sf3;
  ena[2138] = HAVE_cmul_conjv2df3;
  ena[2139] = HAVE_cmul_conjvnx2df3;
  ena[2140] = HAVE_cmlavnx16qi4;
  ena[2141] = HAVE_cmlavnx8hi4;
  ena[2142] = HAVE_cmlavnx4si4;
  ena[2143] = HAVE_cmlavnx2di4;
  ena[2144] = HAVE_cmlav4hf4;
  ena[2145] = HAVE_cmlav2sf4;
  ena[2146] = HAVE_cmlav8hf4;
  ena[2147] = HAVE_cmlavnx8hf4;
  ena[2148] = HAVE_cmlav4sf4;
  ena[2149] = HAVE_cmlavnx4sf4;
  ena[2150] = HAVE_cmlav2df4;
  ena[2151] = HAVE_cmlavnx2df4;
  ena[2152] = HAVE_cmla_conjvnx16qi4;
  ena[2153] = HAVE_cmla_conjvnx8hi4;
  ena[2154] = HAVE_cmla_conjvnx4si4;
  ena[2155] = HAVE_cmla_conjvnx2di4;
  ena[2156] = HAVE_cmla_conjv4hf4;
  ena[2157] = HAVE_cmla_conjv2sf4;
  ena[2158] = HAVE_cmla_conjv8hf4;
  ena[2159] = HAVE_cmla_conjvnx8hf4;
  ena[2160] = HAVE_cmla_conjv4sf4;
  ena[2161] = HAVE_cmla_conjvnx4sf4;
  ena[2162] = HAVE_cmla_conjv2df4;
  ena[2163] = HAVE_cmla_conjvnx2df4;
  ena[2164] = HAVE_cmlsvnx16qi4;
  ena[2165] = HAVE_cmlsvnx8hi4;
  ena[2166] = HAVE_cmlsvnx4si4;
  ena[2167] = HAVE_cmlsvnx2di4;
  ena[2168] = HAVE_cmlsv4hf4;
  ena[2169] = HAVE_cmlsv2sf4;
  ena[2170] = HAVE_cmlsv8hf4;
  ena[2171] = HAVE_cmlsvnx8hf4;
  ena[2172] = HAVE_cmlsv4sf4;
  ena[2173] = HAVE_cmlsvnx4sf4;
  ena[2174] = HAVE_cmlsv2df4;
  ena[2175] = HAVE_cmlsvnx2df4;
  ena[2176] = HAVE_cmls_conjvnx16qi4;
  ena[2177] = HAVE_cmls_conjvnx8hi4;
  ena[2178] = HAVE_cmls_conjvnx4si4;
  ena[2179] = HAVE_cmls_conjvnx2di4;
  ena[2180] = HAVE_cmls_conjv4hf4;
  ena[2181] = HAVE_cmls_conjv2sf4;
  ena[2182] = HAVE_cmls_conjv8hf4;
  ena[2183] = HAVE_cmls_conjvnx8hf4;
  ena[2184] = HAVE_cmls_conjv4sf4;
  ena[2185] = HAVE_cmls_conjvnx4sf4;
  ena[2186] = HAVE_cmls_conjv2df4;
  ena[2187] = HAVE_cmls_conjvnx2df4;
  ena[2188] = HAVE_rsqrtsf2;
  ena[2189] = HAVE_rsqrtdf2;
  ena[2190] = HAVE_rsqrtv2sf2;
  ena[2191] = HAVE_rsqrtv4sf2;
  ena[2192] = HAVE_rsqrtvnx4sf2;
  ena[2193] = HAVE_rsqrtv2df2;
  ena[2194] = HAVE_rsqrtvnx2df2;
  ena[2195] = HAVE_signbitv2sf2;
  ena[2196] = HAVE_signbitv4sf2;
  ena[2197] = HAVE_fmaxhf3;
  ena[2198] = HAVE_fmaxsf3;
  ena[2199] = HAVE_fmaxdf3;
  ena[2200] = HAVE_fmaxv4hf3;
  ena[2201] = HAVE_fmaxv2sf3;
  ena[2202] = HAVE_fmaxv8hf3;
  ena[2203] = HAVE_fmaxvnx8hf3;
  ena[2204] = HAVE_fmaxv4sf3;
  ena[2205] = HAVE_fmaxvnx4sf3;
  ena[2206] = HAVE_fmaxv2df3;
  ena[2207] = HAVE_fmaxvnx2df3;
  ena[2208] = HAVE_fminhf3;
  ena[2209] = HAVE_fminsf3;
  ena[2210] = HAVE_fmindf3;
  ena[2211] = HAVE_fminv4hf3;
  ena[2212] = HAVE_fminv2sf3;
  ena[2213] = HAVE_fminv8hf3;
  ena[2214] = HAVE_fminvnx8hf3;
  ena[2215] = HAVE_fminv4sf3;
  ena[2216] = HAVE_fminvnx4sf3;
  ena[2217] = HAVE_fminv2df3;
  ena[2218] = HAVE_fminvnx2df3;
  ena[2219] = HAVE_reduc_smax_scal_v8qi;
  ena[2220] = HAVE_reduc_smax_scal_v4hi;
  ena[2221] = HAVE_reduc_smax_scal_v2si;
  ena[2222] = HAVE_reduc_smax_scal_v16qi;
  ena[2223] = HAVE_reduc_smax_scal_vnx16qi;
  ena[2224] = HAVE_reduc_smax_scal_v8hi;
  ena[2225] = HAVE_reduc_smax_scal_vnx8hi;
  ena[2226] = HAVE_reduc_smax_scal_v4si;
  ena[2227] = HAVE_reduc_smax_scal_vnx4si;
  ena[2228] = HAVE_reduc_smax_scal_vnx2di;
  ena[2229] = HAVE_reduc_smax_scal_v4hf;
  ena[2230] = HAVE_reduc_smax_scal_v2sf;
  ena[2231] = HAVE_reduc_smax_scal_v8hf;
  ena[2232] = HAVE_reduc_smax_scal_vnx8hf;
  ena[2233] = HAVE_reduc_smax_scal_v4sf;
  ena[2234] = HAVE_reduc_smax_scal_vnx4sf;
  ena[2235] = HAVE_reduc_smax_scal_v2df;
  ena[2236] = HAVE_reduc_smax_scal_vnx2df;
  ena[2237] = HAVE_reduc_smin_scal_v8qi;
  ena[2238] = HAVE_reduc_smin_scal_v4hi;
  ena[2239] = HAVE_reduc_smin_scal_v2si;
  ena[2240] = HAVE_reduc_smin_scal_v16qi;
  ena[2241] = HAVE_reduc_smin_scal_vnx16qi;
  ena[2242] = HAVE_reduc_smin_scal_v8hi;
  ena[2243] = HAVE_reduc_smin_scal_vnx8hi;
  ena[2244] = HAVE_reduc_smin_scal_v4si;
  ena[2245] = HAVE_reduc_smin_scal_vnx4si;
  ena[2246] = HAVE_reduc_smin_scal_vnx2di;
  ena[2247] = HAVE_reduc_smin_scal_v4hf;
  ena[2248] = HAVE_reduc_smin_scal_v2sf;
  ena[2249] = HAVE_reduc_smin_scal_v8hf;
  ena[2250] = HAVE_reduc_smin_scal_vnx8hf;
  ena[2251] = HAVE_reduc_smin_scal_v4sf;
  ena[2252] = HAVE_reduc_smin_scal_vnx4sf;
  ena[2253] = HAVE_reduc_smin_scal_v2df;
  ena[2254] = HAVE_reduc_smin_scal_vnx2df;
  ena[2255] = HAVE_reduc_plus_scal_v8qi;
  ena[2256] = HAVE_reduc_plus_scal_v4hi;
  ena[2257] = HAVE_reduc_plus_scal_v2si;
  ena[2258] = HAVE_reduc_plus_scal_v16qi;
  ena[2259] = HAVE_reduc_plus_scal_vnx16qi;
  ena[2260] = HAVE_reduc_plus_scal_v8hi;
  ena[2261] = HAVE_reduc_plus_scal_vnx8hi;
  ena[2262] = HAVE_reduc_plus_scal_v4si;
  ena[2263] = HAVE_reduc_plus_scal_vnx4si;
  ena[2264] = HAVE_reduc_plus_scal_v2di;
  ena[2265] = HAVE_reduc_plus_scal_vnx2di;
  ena[2266] = HAVE_reduc_plus_scal_v2sf;
  ena[2267] = HAVE_reduc_plus_scal_vnx8hf;
  ena[2268] = HAVE_reduc_plus_scal_v4sf;
  ena[2269] = HAVE_reduc_plus_scal_vnx4sf;
  ena[2270] = HAVE_reduc_plus_scal_v2df;
  ena[2271] = HAVE_reduc_plus_scal_vnx2df;
  ena[2272] = HAVE_reduc_umax_scal_v8qi;
  ena[2273] = HAVE_reduc_umax_scal_v4hi;
  ena[2274] = HAVE_reduc_umax_scal_v2si;
  ena[2275] = HAVE_reduc_umax_scal_v16qi;
  ena[2276] = HAVE_reduc_umax_scal_vnx16qi;
  ena[2277] = HAVE_reduc_umax_scal_v8hi;
  ena[2278] = HAVE_reduc_umax_scal_vnx8hi;
  ena[2279] = HAVE_reduc_umax_scal_v4si;
  ena[2280] = HAVE_reduc_umax_scal_vnx4si;
  ena[2281] = HAVE_reduc_umax_scal_vnx2di;
  ena[2282] = HAVE_reduc_umin_scal_v8qi;
  ena[2283] = HAVE_reduc_umin_scal_v4hi;
  ena[2284] = HAVE_reduc_umin_scal_v2si;
  ena[2285] = HAVE_reduc_umin_scal_v16qi;
  ena[2286] = HAVE_reduc_umin_scal_vnx16qi;
  ena[2287] = HAVE_reduc_umin_scal_v8hi;
  ena[2288] = HAVE_reduc_umin_scal_vnx8hi;
  ena[2289] = HAVE_reduc_umin_scal_v4si;
  ena[2290] = HAVE_reduc_umin_scal_vnx4si;
  ena[2291] = HAVE_reduc_umin_scal_vnx2di;
  ena[2292] = HAVE_reduc_and_scal_vnx16qi;
  ena[2293] = HAVE_reduc_and_scal_vnx8hi;
  ena[2294] = HAVE_reduc_and_scal_vnx4si;
  ena[2295] = HAVE_reduc_and_scal_vnx2di;
  ena[2296] = HAVE_reduc_ior_scal_vnx16qi;
  ena[2297] = HAVE_reduc_ior_scal_vnx8hi;
  ena[2298] = HAVE_reduc_ior_scal_vnx4si;
  ena[2299] = HAVE_reduc_ior_scal_vnx2di;
  ena[2300] = HAVE_reduc_xor_scal_vnx16qi;
  ena[2301] = HAVE_reduc_xor_scal_vnx8hi;
  ena[2302] = HAVE_reduc_xor_scal_vnx4si;
  ena[2303] = HAVE_reduc_xor_scal_vnx2di;
  ena[2304] = HAVE_fold_left_plus_vnx8hf;
  ena[2305] = HAVE_fold_left_plus_vnx4sf;
  ena[2306] = HAVE_fold_left_plus_vnx2df;
  ena[2307] = HAVE_mask_fold_left_plus_vnx8hf;
  ena[2308] = HAVE_mask_fold_left_plus_vnx4sf;
  ena[2309] = HAVE_mask_fold_left_plus_vnx2df;
  ena[2310] = HAVE_extract_last_vnx16qi;
  ena[2311] = HAVE_extract_last_vnx8hi;
  ena[2312] = HAVE_extract_last_vnx4si;
  ena[2313] = HAVE_extract_last_vnx2di;
  ena[2314] = HAVE_extract_last_vnx8bf;
  ena[2315] = HAVE_extract_last_vnx8hf;
  ena[2316] = HAVE_extract_last_vnx4sf;
  ena[2317] = HAVE_extract_last_vnx2df;
  ena[2318] = HAVE_fold_extract_last_vnx16qi;
  ena[2319] = HAVE_fold_extract_last_vnx8hi;
  ena[2320] = HAVE_fold_extract_last_vnx4si;
  ena[2321] = HAVE_fold_extract_last_vnx2di;
  ena[2322] = HAVE_fold_extract_last_vnx8bf;
  ena[2323] = HAVE_fold_extract_last_vnx8hf;
  ena[2324] = HAVE_fold_extract_last_vnx4sf;
  ena[2325] = HAVE_fold_extract_last_vnx2df;
  ena[2326] = HAVE_avgv8qi3_floor;
  ena[2327] = HAVE_avgv4hi3_floor;
  ena[2328] = HAVE_avgv2si3_floor;
  ena[2329] = HAVE_avgv16qi3_floor;
  ena[2330] = HAVE_avgvnx16qi3_floor;
  ena[2331] = HAVE_avgv8hi3_floor;
  ena[2332] = HAVE_avgvnx8hi3_floor;
  ena[2333] = HAVE_avgv4si3_floor;
  ena[2334] = HAVE_avgvnx4si3_floor;
  ena[2335] = HAVE_avgvnx2di3_floor;
  ena[2336] = HAVE_uavgv8qi3_floor;
  ena[2337] = HAVE_uavgv4hi3_floor;
  ena[2338] = HAVE_uavgv2si3_floor;
  ena[2339] = HAVE_uavgv16qi3_floor;
  ena[2340] = HAVE_uavgvnx16qi3_floor;
  ena[2341] = HAVE_uavgv8hi3_floor;
  ena[2342] = HAVE_uavgvnx8hi3_floor;
  ena[2343] = HAVE_uavgv4si3_floor;
  ena[2344] = HAVE_uavgvnx4si3_floor;
  ena[2345] = HAVE_uavgvnx2di3_floor;
  ena[2346] = HAVE_avgv8qi3_ceil;
  ena[2347] = HAVE_avgv4hi3_ceil;
  ena[2348] = HAVE_avgv2si3_ceil;
  ena[2349] = HAVE_avgv16qi3_ceil;
  ena[2350] = HAVE_avgvnx16qi3_ceil;
  ena[2351] = HAVE_avgv8hi3_ceil;
  ena[2352] = HAVE_avgvnx8hi3_ceil;
  ena[2353] = HAVE_avgv4si3_ceil;
  ena[2354] = HAVE_avgvnx4si3_ceil;
  ena[2355] = HAVE_avgvnx2di3_ceil;
  ena[2356] = HAVE_uavgv8qi3_ceil;
  ena[2357] = HAVE_uavgv4hi3_ceil;
  ena[2358] = HAVE_uavgv2si3_ceil;
  ena[2359] = HAVE_uavgv16qi3_ceil;
  ena[2360] = HAVE_uavgvnx16qi3_ceil;
  ena[2361] = HAVE_uavgv8hi3_ceil;
  ena[2362] = HAVE_uavgvnx8hi3_ceil;
  ena[2363] = HAVE_uavgv4si3_ceil;
  ena[2364] = HAVE_uavgvnx4si3_ceil;
  ena[2365] = HAVE_uavgvnx2di3_ceil;
  ena[2366] = HAVE_sdot_prodv8qi;
  ena[2367] = HAVE_sdot_prodv16qi;
  ena[2368] = HAVE_sdot_prodvnx16qi;
  ena[2369] = HAVE_sdot_prodvnx8hi;
  ena[2370] = HAVE_widen_ssumv8qi3;
  ena[2371] = HAVE_widen_ssumv4hi3;
  ena[2372] = HAVE_widen_ssumv2si3;
  ena[2373] = HAVE_widen_ssumv16qi3;
  ena[2374] = HAVE_widen_ssumv8hi3;
  ena[2375] = HAVE_widen_ssumv4si3;
  ena[2376] = HAVE_udot_prodv8qi;
  ena[2377] = HAVE_udot_prodv16qi;
  ena[2378] = HAVE_udot_prodvnx16qi;
  ena[2379] = HAVE_udot_prodvnx8hi;
  ena[2380] = HAVE_widen_usumv8qi3;
  ena[2381] = HAVE_widen_usumv4hi3;
  ena[2382] = HAVE_widen_usumv2si3;
  ena[2383] = HAVE_widen_usumv16qi3;
  ena[2384] = HAVE_widen_usumv8hi3;
  ena[2385] = HAVE_widen_usumv4si3;
  ena[2386] = HAVE_usadv16qi;
  ena[2387] = HAVE_usadvnx16qi;
  ena[2388] = HAVE_usadvnx8hi;
  ena[2389] = HAVE_ssadv16qi;
  ena[2390] = HAVE_ssadvnx16qi;
  ena[2391] = HAVE_ssadvnx8hi;
  ena[2392] = HAVE_smulhsvnx16qi3;
  ena[2393] = HAVE_smulhsvnx8hi3;
  ena[2394] = HAVE_smulhsvnx4si3;
  ena[2395] = HAVE_smulhrsvnx16qi3;
  ena[2396] = HAVE_smulhrsvnx8hi3;
  ena[2397] = HAVE_smulhrsvnx4si3;
  ena[2398] = HAVE_umulhsvnx16qi3;
  ena[2399] = HAVE_umulhsvnx8hi3;
  ena[2400] = HAVE_umulhsvnx4si3;
  ena[2401] = HAVE_umulhrsvnx16qi3;
  ena[2402] = HAVE_umulhrsvnx8hi3;
  ena[2403] = HAVE_umulhrsvnx4si3;
  ena[2404] = HAVE_sdiv_pow2vnx16qi3;
  ena[2405] = HAVE_sdiv_pow2vnx8hi3;
  ena[2406] = HAVE_sdiv_pow2vnx4si3;
  ena[2407] = HAVE_sdiv_pow2vnx2di3;
  ena[2408] = HAVE_sdiv_pow2vnx2qi3;
  ena[2409] = HAVE_sdiv_pow2vnx4qi3;
  ena[2410] = HAVE_sdiv_pow2vnx2hi3;
  ena[2411] = HAVE_sdiv_pow2vnx8qi3;
  ena[2412] = HAVE_sdiv_pow2vnx4hi3;
  ena[2413] = HAVE_sdiv_pow2vnx2si3;
  ena[2414] = HAVE_vec_pack_sfix_trunc_vnx2df;
  ena[2415] = HAVE_vec_pack_trunc_di;
  ena[2416] = HAVE_vec_pack_trunc_df;
  ena[2417] = HAVE_vec_pack_trunc_vnx8bi;
  ena[2418] = HAVE_vec_pack_trunc_vnx4bi;
  ena[2419] = HAVE_vec_pack_trunc_vnx2bi;
  ena[2420] = HAVE_vec_pack_trunc_v4hi;
  ena[2421] = HAVE_vec_pack_trunc_v2si;
  ena[2422] = HAVE_vec_pack_trunc_v8hi;
  ena[2423] = HAVE_vec_pack_trunc_vnx8hi;
  ena[2424] = HAVE_vec_pack_trunc_v4si;
  ena[2425] = HAVE_vec_pack_trunc_vnx4si;
  ena[2426] = HAVE_vec_pack_trunc_v2di;
  ena[2427] = HAVE_vec_pack_trunc_vnx2di;
  ena[2428] = HAVE_vec_pack_trunc_vnx4sf;
  ena[2429] = HAVE_vec_pack_trunc_v2df;
  ena[2430] = HAVE_vec_pack_trunc_vnx2df;
  ena[2431] = HAVE_vec_pack_ufix_trunc_vnx2df;
  ena[2432] = HAVE_vec_permv8qi;
  ena[2433] = HAVE_vec_permv16qi;
  ena[2434] = HAVE_vec_permvnx16qi;
  ena[2435] = HAVE_vec_permvnx8hi;
  ena[2436] = HAVE_vec_permvnx4si;
  ena[2437] = HAVE_vec_permvnx2di;
  ena[2438] = HAVE_vec_permvnx8bf;
  ena[2439] = HAVE_vec_permvnx8hf;
  ena[2440] = HAVE_vec_permvnx4sf;
  ena[2441] = HAVE_vec_permvnx2df;
  ena[2442] = HAVE_vec_setv8qi;
  ena[2443] = HAVE_vec_setv4hi;
  ena[2444] = HAVE_vec_setv2si;
  ena[2445] = HAVE_vec_setv16qi;
  ena[2446] = HAVE_vec_setv8hi;
  ena[2447] = HAVE_vec_setv4si;
  ena[2448] = HAVE_vec_setv2di;
  ena[2449] = HAVE_vec_setv4bf;
  ena[2450] = HAVE_vec_setv4hf;
  ena[2451] = HAVE_vec_setv2sf;
  ena[2452] = HAVE_vec_setv8bf;
  ena[2453] = HAVE_vec_setv8hf;
  ena[2454] = HAVE_vec_setv4sf;
  ena[2455] = HAVE_vec_setv2df;
  ena[2456] = HAVE_vec_shr_v8qi;
  ena[2457] = HAVE_vec_shr_v4hi;
  ena[2458] = HAVE_vec_shr_v2si;
  ena[2459] = HAVE_vec_shr_v4bf;
  ena[2460] = HAVE_vec_shr_v4hf;
  ena[2461] = HAVE_vec_shr_v2sf;
  ena[2462] = HAVE_vec_unpacks_float_hi_vnx4si;
  ena[2463] = HAVE_vec_unpacks_float_lo_vnx4si;
  ena[2464] = HAVE_vec_unpacks_hi_vnx16bi;
  ena[2465] = HAVE_vec_unpacks_hi_vnx8bi;
  ena[2466] = HAVE_vec_unpacks_hi_vnx4bi;
  ena[2467] = HAVE_vec_unpacks_hi_v16qi;
  ena[2468] = HAVE_vec_unpacks_hi_vnx16qi;
  ena[2469] = HAVE_vec_unpacks_hi_v8hi;
  ena[2470] = HAVE_vec_unpacks_hi_vnx8hi;
  ena[2471] = HAVE_vec_unpacks_hi_v4si;
  ena[2472] = HAVE_vec_unpacks_hi_vnx4si;
  ena[2473] = HAVE_vec_unpacks_hi_v8hf;
  ena[2474] = HAVE_vec_unpacks_hi_vnx8hf;
  ena[2475] = HAVE_vec_unpacks_hi_v4sf;
  ena[2476] = HAVE_vec_unpacks_hi_vnx4sf;
  ena[2477] = HAVE_vec_unpacks_lo_vnx16bi;
  ena[2478] = HAVE_vec_unpacks_lo_vnx8bi;
  ena[2479] = HAVE_vec_unpacks_lo_vnx4bi;
  ena[2480] = HAVE_vec_unpacks_lo_v16qi;
  ena[2481] = HAVE_vec_unpacks_lo_vnx16qi;
  ena[2482] = HAVE_vec_unpacks_lo_v8hi;
  ena[2483] = HAVE_vec_unpacks_lo_vnx8hi;
  ena[2484] = HAVE_vec_unpacks_lo_v4si;
  ena[2485] = HAVE_vec_unpacks_lo_vnx4si;
  ena[2486] = HAVE_vec_unpacks_lo_v8hf;
  ena[2487] = HAVE_vec_unpacks_lo_vnx8hf;
  ena[2488] = HAVE_vec_unpacks_lo_v4sf;
  ena[2489] = HAVE_vec_unpacks_lo_vnx4sf;
  ena[2490] = HAVE_vec_unpacku_float_hi_vnx4si;
  ena[2491] = HAVE_vec_unpacku_float_lo_vnx4si;
  ena[2492] = HAVE_vec_unpacku_hi_vnx16bi;
  ena[2493] = HAVE_vec_unpacku_hi_vnx8bi;
  ena[2494] = HAVE_vec_unpacku_hi_vnx4bi;
  ena[2495] = HAVE_vec_unpacku_hi_v16qi;
  ena[2496] = HAVE_vec_unpacku_hi_vnx16qi;
  ena[2497] = HAVE_vec_unpacku_hi_v8hi;
  ena[2498] = HAVE_vec_unpacku_hi_vnx8hi;
  ena[2499] = HAVE_vec_unpacku_hi_v4si;
  ena[2500] = HAVE_vec_unpacku_hi_vnx4si;
  ena[2501] = HAVE_vec_unpacku_lo_vnx16bi;
  ena[2502] = HAVE_vec_unpacku_lo_vnx8bi;
  ena[2503] = HAVE_vec_unpacku_lo_vnx4bi;
  ena[2504] = HAVE_vec_unpacku_lo_v16qi;
  ena[2505] = HAVE_vec_unpacku_lo_vnx16qi;
  ena[2506] = HAVE_vec_unpacku_lo_v8hi;
  ena[2507] = HAVE_vec_unpacku_lo_vnx8hi;
  ena[2508] = HAVE_vec_unpacku_lo_v4si;
  ena[2509] = HAVE_vec_unpacku_lo_vnx4si;
  ena[2510] = HAVE_vec_widen_smult_hi_v16qi;
  ena[2511] = HAVE_vec_widen_smult_hi_v8hi;
  ena[2512] = HAVE_vec_widen_smult_hi_v4si;
  ena[2513] = HAVE_vec_widen_smult_lo_v16qi;
  ena[2514] = HAVE_vec_widen_smult_lo_v8hi;
  ena[2515] = HAVE_vec_widen_smult_lo_v4si;
  ena[2516] = HAVE_vec_widen_ssubl_hi_v16qi;
  ena[2517] = HAVE_vec_widen_ssubl_hi_v8hi;
  ena[2518] = HAVE_vec_widen_ssubl_hi_v4si;
  ena[2519] = HAVE_vec_widen_ssubl_lo_v16qi;
  ena[2520] = HAVE_vec_widen_ssubl_lo_v8hi;
  ena[2521] = HAVE_vec_widen_ssubl_lo_v4si;
  ena[2522] = HAVE_vec_widen_saddl_hi_v16qi;
  ena[2523] = HAVE_vec_widen_saddl_hi_v8hi;
  ena[2524] = HAVE_vec_widen_saddl_hi_v4si;
  ena[2525] = HAVE_vec_widen_saddl_lo_v16qi;
  ena[2526] = HAVE_vec_widen_saddl_lo_v8hi;
  ena[2527] = HAVE_vec_widen_saddl_lo_v4si;
  ena[2528] = HAVE_vec_widen_sshiftl_hi_v16qi;
  ena[2529] = HAVE_vec_widen_sshiftl_hi_v8hi;
  ena[2530] = HAVE_vec_widen_sshiftl_hi_v4si;
  ena[2531] = HAVE_vec_widen_sshiftl_lo_v16qi;
  ena[2532] = HAVE_vec_widen_sshiftl_lo_v8hi;
  ena[2533] = HAVE_vec_widen_sshiftl_lo_v4si;
  ena[2534] = HAVE_vec_widen_umult_hi_v16qi;
  ena[2535] = HAVE_vec_widen_umult_hi_v8hi;
  ena[2536] = HAVE_vec_widen_umult_hi_v4si;
  ena[2537] = HAVE_vec_widen_umult_lo_v16qi;
  ena[2538] = HAVE_vec_widen_umult_lo_v8hi;
  ena[2539] = HAVE_vec_widen_umult_lo_v4si;
  ena[2540] = HAVE_vec_widen_ushiftl_hi_v16qi;
  ena[2541] = HAVE_vec_widen_ushiftl_hi_v8hi;
  ena[2542] = HAVE_vec_widen_ushiftl_hi_v4si;
  ena[2543] = HAVE_vec_widen_ushiftl_lo_v16qi;
  ena[2544] = HAVE_vec_widen_ushiftl_lo_v8hi;
  ena[2545] = HAVE_vec_widen_ushiftl_lo_v4si;
  ena[2546] = HAVE_vec_widen_usubl_hi_v16qi;
  ena[2547] = HAVE_vec_widen_usubl_hi_v8hi;
  ena[2548] = HAVE_vec_widen_usubl_hi_v4si;
  ena[2549] = HAVE_vec_widen_usubl_lo_v16qi;
  ena[2550] = HAVE_vec_widen_usubl_lo_v8hi;
  ena[2551] = HAVE_vec_widen_usubl_lo_v4si;
  ena[2552] = HAVE_vec_widen_uaddl_hi_v16qi;
  ena[2553] = HAVE_vec_widen_uaddl_hi_v8hi;
  ena[2554] = HAVE_vec_widen_uaddl_hi_v4si;
  ena[2555] = HAVE_vec_widen_uaddl_lo_v16qi;
  ena[2556] = HAVE_vec_widen_uaddl_lo_v8hi;
  ena[2557] = HAVE_vec_widen_uaddl_lo_v4si;
  ena[2558] = HAVE_atomic_add_fetchqi;
  ena[2559] = HAVE_atomic_add_fetchhi;
  ena[2560] = HAVE_atomic_add_fetchsi;
  ena[2561] = HAVE_atomic_add_fetchdi;
  ena[2562] = HAVE_atomic_addqi;
  ena[2563] = HAVE_atomic_addhi;
  ena[2564] = HAVE_atomic_addsi;
  ena[2565] = HAVE_atomic_adddi;
  ena[2566] = HAVE_atomic_and_fetchqi;
  ena[2567] = HAVE_atomic_and_fetchhi;
  ena[2568] = HAVE_atomic_and_fetchsi;
  ena[2569] = HAVE_atomic_and_fetchdi;
  ena[2570] = HAVE_atomic_andqi;
  ena[2571] = HAVE_atomic_andhi;
  ena[2572] = HAVE_atomic_andsi;
  ena[2573] = HAVE_atomic_anddi;
  ena[2574] = HAVE_atomic_compare_and_swapqi;
  ena[2575] = HAVE_atomic_compare_and_swaphi;
  ena[2576] = HAVE_atomic_compare_and_swapsi;
  ena[2577] = HAVE_atomic_compare_and_swapdi;
  ena[2578] = HAVE_atomic_compare_and_swapti;
  ena[2579] = HAVE_atomic_exchangeqi;
  ena[2580] = HAVE_atomic_exchangehi;
  ena[2581] = HAVE_atomic_exchangesi;
  ena[2582] = HAVE_atomic_exchangedi;
  ena[2583] = HAVE_atomic_fetch_addqi;
  ena[2584] = HAVE_atomic_fetch_addhi;
  ena[2585] = HAVE_atomic_fetch_addsi;
  ena[2586] = HAVE_atomic_fetch_adddi;
  ena[2587] = HAVE_atomic_fetch_andqi;
  ena[2588] = HAVE_atomic_fetch_andhi;
  ena[2589] = HAVE_atomic_fetch_andsi;
  ena[2590] = HAVE_atomic_fetch_anddi;
  ena[2591] = HAVE_atomic_fetch_nandqi;
  ena[2592] = HAVE_atomic_fetch_nandhi;
  ena[2593] = HAVE_atomic_fetch_nandsi;
  ena[2594] = HAVE_atomic_fetch_nanddi;
  ena[2595] = HAVE_atomic_fetch_orqi;
  ena[2596] = HAVE_atomic_fetch_orhi;
  ena[2597] = HAVE_atomic_fetch_orsi;
  ena[2598] = HAVE_atomic_fetch_ordi;
  ena[2599] = HAVE_atomic_fetch_subqi;
  ena[2600] = HAVE_atomic_fetch_subhi;
  ena[2601] = HAVE_atomic_fetch_subsi;
  ena[2602] = HAVE_atomic_fetch_subdi;
  ena[2603] = HAVE_atomic_fetch_xorqi;
  ena[2604] = HAVE_atomic_fetch_xorhi;
  ena[2605] = HAVE_atomic_fetch_xorsi;
  ena[2606] = HAVE_atomic_fetch_xordi;
  ena[2607] = HAVE_atomic_loadqi;
  ena[2608] = HAVE_atomic_loadhi;
  ena[2609] = HAVE_atomic_loadsi;
  ena[2610] = HAVE_atomic_loaddi;
  ena[2611] = HAVE_atomic_nand_fetchqi;
  ena[2612] = HAVE_atomic_nand_fetchhi;
  ena[2613] = HAVE_atomic_nand_fetchsi;
  ena[2614] = HAVE_atomic_nand_fetchdi;
  ena[2615] = HAVE_atomic_nandqi;
  ena[2616] = HAVE_atomic_nandhi;
  ena[2617] = HAVE_atomic_nandsi;
  ena[2618] = HAVE_atomic_nanddi;
  ena[2619] = HAVE_atomic_or_fetchqi;
  ena[2620] = HAVE_atomic_or_fetchhi;
  ena[2621] = HAVE_atomic_or_fetchsi;
  ena[2622] = HAVE_atomic_or_fetchdi;
  ena[2623] = HAVE_atomic_orqi;
  ena[2624] = HAVE_atomic_orhi;
  ena[2625] = HAVE_atomic_orsi;
  ena[2626] = HAVE_atomic_ordi;
  ena[2627] = HAVE_atomic_storeqi;
  ena[2628] = HAVE_atomic_storehi;
  ena[2629] = HAVE_atomic_storesi;
  ena[2630] = HAVE_atomic_storedi;
  ena[2631] = HAVE_atomic_sub_fetchqi;
  ena[2632] = HAVE_atomic_sub_fetchhi;
  ena[2633] = HAVE_atomic_sub_fetchsi;
  ena[2634] = HAVE_atomic_sub_fetchdi;
  ena[2635] = HAVE_atomic_subqi;
  ena[2636] = HAVE_atomic_subhi;
  ena[2637] = HAVE_atomic_subsi;
  ena[2638] = HAVE_atomic_subdi;
  ena[2639] = HAVE_atomic_xor_fetchqi;
  ena[2640] = HAVE_atomic_xor_fetchhi;
  ena[2641] = HAVE_atomic_xor_fetchsi;
  ena[2642] = HAVE_atomic_xor_fetchdi;
  ena[2643] = HAVE_atomic_xorqi;
  ena[2644] = HAVE_atomic_xorhi;
  ena[2645] = HAVE_atomic_xorsi;
  ena[2646] = HAVE_atomic_xordi;
  ena[2647] = HAVE_get_thread_pointerdi;
  ena[2648] = HAVE_check_raw_ptrssi;
  ena[2649] = HAVE_check_raw_ptrsdi;
  ena[2650] = HAVE_check_war_ptrssi;
  ena[2651] = HAVE_check_war_ptrsdi;
  ena[2652] = HAVE_vec_duplicatevnx16bi;
  ena[2653] = HAVE_vec_duplicatevnx8bi;
  ena[2654] = HAVE_vec_duplicatevnx4bi;
  ena[2655] = HAVE_vec_duplicatevnx2bi;
  ena[2656] = HAVE_vec_duplicatevnx16qi;
  ena[2657] = HAVE_vec_duplicatevnx8hi;
  ena[2658] = HAVE_vec_duplicatevnx4si;
  ena[2659] = HAVE_vec_duplicatevnx2di;
  ena[2660] = HAVE_vec_duplicatevnx2qi;
  ena[2661] = HAVE_vec_duplicatevnx4qi;
  ena[2662] = HAVE_vec_duplicatevnx2hi;
  ena[2663] = HAVE_vec_duplicatevnx8qi;
  ena[2664] = HAVE_vec_duplicatevnx4hi;
  ena[2665] = HAVE_vec_duplicatevnx2si;
  ena[2666] = HAVE_vec_duplicatevnx8bf;
  ena[2667] = HAVE_vec_duplicatevnx8hf;
  ena[2668] = HAVE_vec_duplicatevnx4sf;
  ena[2669] = HAVE_vec_duplicatevnx2df;
  ena[2670] = HAVE_vec_duplicatevnx2bf;
  ena[2671] = HAVE_vec_duplicatevnx2hf;
  ena[2672] = HAVE_vec_duplicatevnx4bf;
  ena[2673] = HAVE_vec_duplicatevnx4hf;
  ena[2674] = HAVE_vec_duplicatevnx2sf;
  ena[2675] = HAVE_vec_seriesvnx16qi;
  ena[2676] = HAVE_vec_seriesvnx8hi;
  ena[2677] = HAVE_vec_seriesvnx4si;
  ena[2678] = HAVE_vec_seriesvnx2di;
  ena[2679] = HAVE_vec_seriesvnx2qi;
  ena[2680] = HAVE_vec_seriesvnx4qi;
  ena[2681] = HAVE_vec_seriesvnx2hi;
  ena[2682] = HAVE_vec_seriesvnx8qi;
  ena[2683] = HAVE_vec_seriesvnx4hi;
  ena[2684] = HAVE_vec_seriesvnx2si;
  ena[2685] = HAVE_vec_shl_insert_vnx16qi;
  ena[2686] = HAVE_vec_shl_insert_vnx8hi;
  ena[2687] = HAVE_vec_shl_insert_vnx4si;
  ena[2688] = HAVE_vec_shl_insert_vnx2di;
  ena[2689] = HAVE_vec_shl_insert_vnx8bf;
  ena[2690] = HAVE_vec_shl_insert_vnx8hf;
  ena[2691] = HAVE_vec_shl_insert_vnx4sf;
  ena[2692] = HAVE_vec_shl_insert_vnx2df;
}

static int
lookup_handler (unsigned scode)
{
  int l = 0, h = ARRAY_SIZE (pats), m;
  while (h > l)
    {
      m = (h + l) / 2;
      if (scode == pats[m].scode)
        return m;
      else if (scode < pats[m].scode)
        h = m;
      else
        l = m + 1;
    }
  return -1;
}

enum insn_code
raw_optab_handler (unsigned scode)
{
  int i = lookup_handler (scode);
  return (i >= 0 && this_fn_optabs->pat_enable[i]
          ? pats[i].icode : CODE_FOR_nothing);
}

bool
swap_optab_enable (optab op, machine_mode m, bool set)
{
  unsigned scode = (op << 16) | m;
  int i = lookup_handler (scode);
  if (i >= 0)
    {
      bool ret = this_fn_optabs->pat_enable[i];
      this_fn_optabs->pat_enable[i] = set;
      return ret;
    }
  else
    {
      gcc_assert (!set);
      return false;
    }
}

const struct convert_optab_libcall_d convlib_def[NUM_CONVLIB_OPTABS] = {
  { "extend", gen_extend_conv_libfunc },
  { "trunc", gen_trunc_conv_libfunc },
  { NULL, NULL },
  { "fix", gen_fp_to_int_conv_libfunc },
  { "fixuns", gen_fp_to_int_conv_libfunc },
  { "float", gen_int_to_fp_conv_libfunc },
  { NULL, gen_ufloat_conv_libfunc },
  { "lrint", gen_int_to_fp_nondecimal_conv_libfunc },
  { "lround", gen_int_to_fp_nondecimal_conv_libfunc },
  { "lfloor", gen_int_to_fp_nondecimal_conv_libfunc },
  { "lceil", gen_int_to_fp_nondecimal_conv_libfunc },
  { "fract", gen_fract_conv_libfunc },
  { "fractuns", gen_fractuns_conv_libfunc },
  { "satfract", gen_satfract_conv_libfunc },
  { "satfractuns", gen_satfractuns_conv_libfunc },
};

const struct optab_libcall_d normlib_def[NUM_NORMLIB_OPTABS] = {
  { '3', "add", gen_int_fp_fixed_libfunc },
  { '3', "add", gen_intv_fp_libfunc },
  { '3', "ssadd", gen_signed_fixed_libfunc },
  { '3', "usadd", gen_unsigned_fixed_libfunc },
  { '3', "sub", gen_int_fp_fixed_libfunc },
  { '3', "sub", gen_intv_fp_libfunc },
  { '3', "sssub", gen_signed_fixed_libfunc },
  { '3', "ussub", gen_unsigned_fixed_libfunc },
  { '3', "mul", gen_int_fp_fixed_libfunc },
  { '3', "mul", gen_intv_fp_libfunc },
  { '3', "ssmul", gen_signed_fixed_libfunc },
  { '3', "usmul", gen_unsigned_fixed_libfunc },
  { '3', "div", gen_int_fp_signed_fixed_libfunc },
  { '3', "divv", gen_int_libfunc },
  { '3', "ssdiv", gen_signed_fixed_libfunc },
  { '3', "udiv", gen_int_unsigned_fixed_libfunc },
  { '3', "usdiv", gen_unsigned_fixed_libfunc },
  { '\0', NULL, NULL },
  { '\0', NULL, NULL },
  { '3', "mod", gen_int_libfunc },
  { '3', "umod", gen_int_libfunc },
  { '2', "ftrunc", gen_fp_libfunc },
  { '3', "and", gen_int_libfunc },
  { '3', "ior", gen_int_libfunc },
  { '3', "xor", gen_int_libfunc },
  { '3', "ashl", gen_int_fixed_libfunc },
  { '3', "ssashl", gen_signed_fixed_libfunc },
  { '3', "usashl", gen_unsigned_fixed_libfunc },
  { '3', "ashr", gen_int_signed_fixed_libfunc },
  { '3', "lshr", gen_int_unsigned_fixed_libfunc },
  { '\0', NULL, NULL },
  { '\0', NULL, NULL },
  { '\0', NULL, NULL },
  { '\0', NULL, NULL },
  { '\0', NULL, NULL },
  { '\0', NULL, NULL },
  { '\0', NULL, NULL },
  { '3', "min", gen_int_fp_libfunc },
  { '3', "max", gen_int_fp_libfunc },
  { '3', "umin", gen_int_libfunc },
  { '3', "umax", gen_int_libfunc },
  { '2', "neg", gen_int_fp_fixed_libfunc },
  { '2', "neg", gen_intv_fp_libfunc },
  { '2', "ssneg", gen_signed_fixed_libfunc },
  { '2', "usneg", gen_unsigned_fixed_libfunc },
  { '\0', NULL, NULL },
  { '\0', NULL, NULL },
  { '2', "one_cmpl", gen_int_libfunc },
  { '\0', NULL, NULL },
  { '2', "ffs", gen_int_libfunc },
  { '2', "clz", gen_int_libfunc },
  { '2', "ctz", gen_int_libfunc },
  { '2', "clrsb", gen_int_libfunc },
  { '2', "popcount", gen_int_libfunc },
  { '2', "parity", gen_int_libfunc },
  { '2', "cmp", gen_int_fp_fixed_libfunc },
  { '2', "ucmp", gen_int_libfunc },
  { '2', "eq", gen_fp_libfunc },
  { '2', "ne", gen_fp_libfunc },
  { '2', "gt", gen_fp_libfunc },
  { '2', "ge", gen_fp_libfunc },
  { '2', "lt", gen_fp_libfunc },
  { '2', "le", gen_fp_libfunc },
  { '2', "unord", gen_fp_libfunc },
  { '2', "powi", gen_fp_libfunc },
  { '\0', NULL, NULL },
  { '\0', NULL, NULL },
  { '\0', NULL, NULL },
  { '\0', NULL, NULL },
  { '\0', NULL, NULL },
  { '\0', NULL, NULL },
  { '\0', NULL, NULL },
  { '\0', NULL, NULL },
  { '\0', NULL, NULL },
  { '\0', NULL, NULL },
  { '\0', NULL, NULL },
  { '\0', NULL, NULL },
  { '\0', NULL, NULL },
  { '\0', NULL, NULL },
  { '\0', NULL, NULL },
};

enum rtx_code const optab_to_code_[NUM_OPTABS] = {
  UNKNOWN,
  SIGN_EXTEND,
  TRUNCATE,
  ZERO_EXTEND,
  FIX,
  UNSIGNED_FIX,
  FLOAT,
  UNSIGNED_FLOAT,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  FRACT_CONVERT,
  UNSIGNED_FRACT_CONVERT,
  SAT_FRACT,
  UNSIGNED_SAT_FRACT,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  PLUS,
  PLUS,
  SS_PLUS,
  US_PLUS,
  MINUS,
  MINUS,
  SS_MINUS,
  US_MINUS,
  MULT,
  MULT,
  SS_MULT,
  US_MULT,
  DIV,
  DIV,
  SS_DIV,
  UDIV,
  US_DIV,
  UNKNOWN,
  UNKNOWN,
  MOD,
  UMOD,
  UNKNOWN,
  AND,
  IOR,
  XOR,
  ASHIFT,
  SS_ASHIFT,
  US_ASHIFT,
  ASHIFTRT,
  LSHIFTRT,
  ROTATE,
  ROTATERT,
  ASHIFT,
  ASHIFTRT,
  LSHIFTRT,
  ROTATE,
  ROTATERT,
  SMIN,
  SMAX,
  UMIN,
  UMAX,
  NEG,
  NEG,
  SS_NEG,
  US_NEG,
  ABS,
  ABS,
  NOT,
  BSWAP,
  FFS,
  CLZ,
  CTZ,
  CLRSB,
  POPCOUNT,
  PARITY,
  UNKNOWN,
  UNKNOWN,
  EQ,
  NE,
  GT,
  GE,
  LT,
  LE,
  UNORDERED,
  UNKNOWN,
  SQRT,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  SET,
  STRICT_LOW_PART,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  COMPARE,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  FMA,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
  VEC_DUPLICATE,
  VEC_SERIES,
  UNKNOWN,
  UNKNOWN,
  UNKNOWN,
};

const optab code_to_optab_[NUM_RTX_CODE] = {
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  mov_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  movstrict_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  cbranch_optab,
  add_optab,
  sub_optab,
  neg_optab,
  smul_optab,
  ssmul_optab,
  usmul_optab,
  sdiv_optab,
  ssdiv_optab,
  usdiv_optab,
  smod_optab,
  udiv_optab,
  umod_optab,
  and_optab,
  ior_optab,
  xor_optab,
  one_cmpl_optab,
  ashl_optab,
  rotl_optab,
  ashr_optab,
  lshr_optab,
  rotr_optab,
  smin_optab,
  smax_optab,
  umin_optab,
  umax_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  ne_optab,
  eq_optab,
  ge_optab,
  gt_optab,
  le_optab,
  lt_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unord_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  abs_optab,
  sqrt_optab,
  bswap_optab,
  ffs_optab,
  clrsb_optab,
  clz_optab,
  ctz_optab,
  popcount_optab,
  parity_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  vec_duplicate_optab,
  vec_series_optab,
  ssadd_optab,
  usadd_optab,
  sssub_optab,
  ssneg_optab,
  usneg_optab,
  unknown_optab,
  ssashl_optab,
  usashl_optab,
  ussub_optab,
  unknown_optab,
  unknown_optab,
  fma_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
  unknown_optab,
};

