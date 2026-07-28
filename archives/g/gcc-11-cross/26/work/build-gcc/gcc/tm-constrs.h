/* Generated automatically by the program 'build/genpreds'
   from the machine description file '/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/aarch64.md'.  */

#ifndef GCC_TM_CONSTRS_H
#define GCC_TM_CONSTRS_H

static inline bool
satisfies_constraint_m (rtx op)
{
  return (GET_CODE (op) == MEM) && (
#line 26 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/common.md"
(memory_address_addr_space_p (GET_MODE (op), XEXP (op, 0),
						 MEM_ADDR_SPACE (op))));
}
static inline bool
satisfies_constraint_o (rtx op)
{
  return (GET_CODE (op) == MEM) && (
#line 32 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/common.md"
(offsettable_nonstrict_memref_p (op)));
}
static inline bool
satisfies_constraint_V (rtx op)
{
  return (GET_CODE (op) == MEM) && ((
#line 41 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/common.md"
(memory_address_addr_space_p (GET_MODE (op), XEXP (op, 0),
						 MEM_ADDR_SPACE (op)))) && (!(
#line 43 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/common.md"
(offsettable_nonstrict_memref_p (op)))));
}
static inline bool
satisfies_constraint__l (rtx op)
{
  return (GET_CODE (op) == MEM) && ((
#line 50 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/common.md"
(GET_CODE (XEXP (op, 0)) == PRE_DEC)) || (
#line 51 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/common.md"
(GET_CODE (XEXP (op, 0)) == POST_DEC)));
}
static inline bool
satisfies_constraint__g (rtx op)
{
  return (GET_CODE (op) == MEM) && ((
#line 57 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/common.md"
(GET_CODE (XEXP (op, 0)) == PRE_INC)) || (
#line 58 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/common.md"
(GET_CODE (XEXP (op, 0)) == POST_INC)));
}
static inline bool
satisfies_constraint_p (rtx ARG_UNUSED (op))
{
  return 
#line 62 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/common.md"
(address_operand (op, VOIDmode));
}
static inline bool
satisfies_constraint_i (rtx op)
{
  return (
#line 66 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/common.md"
(CONSTANT_P (op))) && (
#line 67 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/common.md"
(!flag_pic || LEGITIMATE_PIC_OPERAND_P (op)));
}
static inline bool
satisfies_constraint_s (rtx op)
{
  return (
#line 71 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/common.md"
(CONSTANT_P (op))) && ((
#line 72 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/common.md"
(!CONST_SCALAR_INT_P (op))) && (
#line 73 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/common.md"
(!flag_pic || LEGITIMATE_PIC_OPERAND_P (op))));
}
static inline bool
satisfies_constraint_n (rtx op)
{
  return (
#line 77 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/common.md"
(CONST_SCALAR_INT_P (op))) && (
#line 78 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/common.md"
(!flag_pic || LEGITIMATE_PIC_OPERAND_P (op)));
}
static inline bool
satisfies_constraint_E (rtx op)
{
  return (
#line 82 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/common.md"
(CONST_DOUBLE_AS_FLOAT_P (op))) || (
#line 83 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/common.md"
(GET_CODE (op) == CONST_VECTOR
		    && GET_MODE_CLASS (GET_MODE (op)) == MODE_VECTOR_FLOAT));
}
static inline bool
satisfies_constraint_F (rtx op)
{
  return (
#line 89 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/common.md"
(CONST_DOUBLE_AS_FLOAT_P (op))) || (
#line 90 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/common.md"
(GET_CODE (op) == CONST_VECTOR
		    && GET_MODE_CLASS (GET_MODE (op)) == MODE_VECTOR_FLOAT));
}
static inline bool
satisfies_constraint_X (rtx ARG_UNUSED (op))
{
  return 
#line 95 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/common.md"
(true);
}
static inline bool
satisfies_constraint_c (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return cc_register (op, mode);
}
static inline bool
satisfies_constraint_I (rtx op)
{
  HOST_WIDE_INT ival = 0;
  if (CONST_INT_P (op))
    ival = INTVAL (op);
  return (GET_CODE (op) == CONST_INT) && (
#line 58 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_uimm12_shift (ival)));
}
static inline bool
satisfies_constraint_Uaa (rtx op)
{
  return (GET_CODE (op) == CONST_INT) && (
#line 63 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_pluslong_strict_immedate (op, VOIDmode)));
}
static inline bool
satisfies_constraint_Uai (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_sve_scalar_inc_dec_immediate (op, mode);
}
static inline bool
satisfies_constraint_Uav (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_sve_addvl_addpl_immediate (op, mode);
}
static inline bool
satisfies_constraint_Uat (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_split_add_offset_immediate (op, mode);
}
static inline bool
satisfies_constraint_J (rtx op)
{
  HOST_WIDE_INT ival = 0;
  if (CONST_INT_P (op))
    ival = INTVAL (op);
  return (GET_CODE (op) == CONST_INT) && (
#line 86 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_uimm12_shift (-ival)));
}
static inline bool
satisfies_constraint_K (rtx op)
{
  HOST_WIDE_INT ival = 0;
  if (CONST_INT_P (op))
    ival = INTVAL (op);
  return (GET_CODE (op) == CONST_INT) && (
#line 95 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_bitmask_imm (ival, SImode)));
}
static inline bool
satisfies_constraint_L (rtx op)
{
  HOST_WIDE_INT ival = 0;
  if (CONST_INT_P (op))
    ival = INTVAL (op);
  return (GET_CODE (op) == CONST_INT) && (
#line 100 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_bitmask_imm (ival, DImode)));
}
static inline bool
satisfies_constraint_M (rtx op)
{
  HOST_WIDE_INT ival = 0;
  if (CONST_INT_P (op))
    ival = INTVAL (op);
  return (GET_CODE (op) == CONST_INT) && (
#line 105 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_move_imm (ival, SImode)));
}
static inline bool
satisfies_constraint_N (rtx op)
{
  HOST_WIDE_INT ival = 0;
  if (CONST_INT_P (op))
    ival = INTVAL (op);
  return (GET_CODE (op) == CONST_INT) && (
#line 110 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_move_imm (ival, DImode)));
}
static inline bool
satisfies_constraint_Uti (rtx op)
{
  return ((GET_CODE (op) == CONST_INT) || (GET_CODE (op) == CONST_WIDE_INT)) && (
#line 116 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_mov128_immediate (op)));
}
static inline bool
satisfies_constraint_UsO (rtx op)
{
  HOST_WIDE_INT ival = 0;
  if (CONST_INT_P (op))
    ival = INTVAL (op);
  return (GET_CODE (op) == CONST_INT) && (
#line 121 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_and_bitmask_imm (ival, SImode)));
}
static inline bool
satisfies_constraint_UsP (rtx op)
{
  HOST_WIDE_INT ival = 0;
  if (CONST_INT_P (op))
    ival = INTVAL (op);
  return (GET_CODE (op) == CONST_INT) && (
#line 126 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_and_bitmask_imm (ival, DImode)));
}
static inline bool
satisfies_constraint_S (rtx op)
{
  switch (GET_CODE (op))
    {
    case CONST:
    case SYMBOL_REF:
    case LABEL_REF:
      break;
    default:
      return false;
    }
  return 
#line 131 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_symbolic_address_p (op));
}
static inline bool
satisfies_constraint_Y (rtx op)
{
  return (GET_CODE (op) == CONST_DOUBLE) && (
#line 136 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_float_const_zero_rtx_p (op)));
}
static inline bool
satisfies_constraint_Z (rtx op)
{
  return 
#line 140 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(op == CONST0_RTX (GET_MODE (op)));
}
static inline bool
satisfies_constraint_Ush (rtx op)
{
  return (GET_CODE (op) == HIGH) && (
#line 145 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_valid_symref (XEXP (op, 0), GET_MODE (XEXP (op, 0)))));
}
static inline bool
satisfies_constraint_Usa (rtx op)
{
  switch (GET_CODE (op))
    {
    case CONST:
    case SYMBOL_REF:
    case LABEL_REF:
      break;
    default:
      return false;
    }
  return (
#line 152 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_symbolic_address_p (op))) && (
#line 153 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_mov_operand_p (op, GET_MODE (op))));
}
static inline bool
satisfies_constraint_Uss (rtx op)
{
  HOST_WIDE_INT ival = 0;
  if (CONST_INT_P (op))
    ival = INTVAL (op);
  return (GET_CODE (op) == CONST_INT) && (
#line 159 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
((unsigned HOST_WIDE_INT) ival < 32));
}
static inline bool
satisfies_constraint_Usn (rtx op)
{
  HOST_WIDE_INT ival = 0;
  if (CONST_INT_P (op))
    ival = INTVAL (op);
  return (GET_CODE (op) == CONST_INT) && (
#line 164 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(IN_RANGE (ival, -31, 0)));
}
static inline bool
satisfies_constraint_Usd (rtx op)
{
  HOST_WIDE_INT ival = 0;
  if (CONST_INT_P (op))
    ival = INTVAL (op);
  return (GET_CODE (op) == CONST_INT) && (
#line 170 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
((unsigned HOST_WIDE_INT) ival < 64));
}
static inline bool
satisfies_constraint_Usf (rtx op)
{
  return (GET_CODE (op) == SYMBOL_REF) && (
#line 175 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(!(aarch64_is_noplt_call_p (op)
		      || aarch64_is_long_call_p (op))));
}
static inline bool
satisfies_constraint_Usg (rtx op)
{
  HOST_WIDE_INT ival = 0;
  if (CONST_INT_P (op))
    ival = INTVAL (op);
  return (GET_CODE (op) == CONST_INT) && (
#line 183 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(IN_RANGE (ival, 1, 31)));
}
static inline bool
satisfies_constraint_Usj (rtx op)
{
  HOST_WIDE_INT ival = 0;
  if (CONST_INT_P (op))
    ival = INTVAL (op);
  return (GET_CODE (op) == CONST_INT) && (
#line 190 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(IN_RANGE (ival, 1, 63)));
}
static inline bool
satisfies_constraint_UsM (rtx op)
{
  return 
#line 195 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(op == constm1_rtx);
}
static inline bool
satisfies_constraint_Ulc (rtx op)
{
  HOST_WIDE_INT ival = 0;
  if (CONST_INT_P (op))
    ival = INTVAL (op);
  return (GET_CODE (op) == CONST_INT) && (
#line 202 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_high_bits_all_ones_p (ival)));
}
static inline bool
satisfies_constraint_Usv (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_sve_cnt_immediate (op, mode);
}
static inline bool
satisfies_constraint_Usi (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_sve_index_immediate (op, mode);
}
static inline bool
satisfies_constraint_Ui1 (rtx op)
{
  return 
#line 219 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(op == const1_rtx);
}
static inline bool
satisfies_constraint_Ui2 (rtx op)
{
  HOST_WIDE_INT ival = 0;
  if (CONST_INT_P (op))
    ival = INTVAL (op);
  return (GET_CODE (op) == CONST_INT) && (
#line 225 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
((unsigned HOST_WIDE_INT) ival <= 3));
}
static inline bool
satisfies_constraint_Ui3 (rtx op)
{
  HOST_WIDE_INT ival = 0;
  if (CONST_INT_P (op))
    ival = INTVAL (op);
  return (GET_CODE (op) == CONST_INT) && (
#line 231 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
((unsigned HOST_WIDE_INT) ival <= 4));
}
static inline bool
satisfies_constraint_Ui7 (rtx op)
{
  HOST_WIDE_INT ival = 0;
  if (CONST_INT_P (op))
    ival = INTVAL (op);
  return (GET_CODE (op) == CONST_INT) && (
#line 237 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
((unsigned HOST_WIDE_INT) ival <= 7));
}
static inline bool
satisfies_constraint_Up3 (rtx op)
{
  HOST_WIDE_INT ival = 0;
  if (CONST_INT_P (op))
    ival = INTVAL (op);
  return (GET_CODE (op) == CONST_INT) && (
#line 243 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
((unsigned) exact_log2 (ival) <= 4));
}
static inline bool
satisfies_constraint_Uph (rtx op)
{
  return (GET_CODE (op) == CONST_INT) && (
#line 250 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_plushi_immediate (op, VOIDmode)));
}
static inline bool
satisfies_constraint_Q (rtx op)
{
  return (GET_CODE (op) == MEM) && (
#line 255 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(REG_P (XEXP (op, 0))));
}
static inline bool
satisfies_constraint_Ust (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_9bit_offset_memory_operand (op, mode);
}
static inline bool
satisfies_constraint_Ump (rtx op)
{
  return (GET_CODE (op) == MEM) && (
#line 266 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_legitimate_address_p (GET_MODE (op), XEXP (op, 0),
						  true, ADDR_QUERY_LDP_STP)));
}
static inline bool
satisfies_constraint_Umn (rtx op)
{
  return (GET_CODE (op) == MEM) && (
#line 276 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_legitimate_address_p (GET_MODE (op), XEXP (op, 0),
						  true,
						  ADDR_QUERY_LDP_STP_N)));
}
static inline bool
satisfies_constraint_UPb (rtx ARG_UNUSED (op))
{
  return 
#line 283 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_sve_prefetch_operand_p (op, VNx16QImode));
}
static inline bool
satisfies_constraint_UPd (rtx ARG_UNUSED (op))
{
  return 
#line 288 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_sve_prefetch_operand_p (op, VNx2DImode));
}
static inline bool
satisfies_constraint_UPh (rtx ARG_UNUSED (op))
{
  return 
#line 293 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_sve_prefetch_operand_p (op, VNx8HImode));
}
static inline bool
satisfies_constraint_UPw (rtx ARG_UNUSED (op))
{
  return 
#line 298 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_sve_prefetch_operand_p (op, VNx4SImode));
}
static inline bool
satisfies_constraint_Utf (rtx op)
{
  return (GET_CODE (op) == MEM) && (
#line 304 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_sve_ldff1_operand_p (op)));
}
static inline bool
satisfies_constraint_Utn (rtx op)
{
  return (GET_CODE (op) == MEM) && (
#line 310 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_sve_ldnf1_operand_p (op)));
}
static inline bool
satisfies_constraint_Utr (rtx op)
{
  return (GET_CODE (op) == MEM) && (
#line 317 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_sve_ldr_operand_p (op)));
}
static inline bool
satisfies_constraint_Utv (rtx op)
{
  return (GET_CODE (op) == MEM) && (
#line 324 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_simd_mem_operand_p (op)));
}
static inline bool
satisfies_constraint_Utq (rtx op)
{
  return (GET_CODE (op) == MEM) && ((
#line 330 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_legitimate_address_p (GET_MODE (op),
						  XEXP (op, 0), 1))) && (
#line 332 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_legitimate_address_p (V2DImode,
						  XEXP (op, 0), 1))));
}
static inline bool
satisfies_constraint_UtQ (rtx op)
{
  return (GET_CODE (op) == MEM) && (
#line 339 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_sve_ld1rq_operand_p (op)));
}
static inline bool
satisfies_constraint_UOb (rtx op)
{
  return (GET_CODE (op) == MEM) && (
#line 345 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_sve_ld1ro_operand_p (op, QImode)));
}
static inline bool
satisfies_constraint_UOh (rtx op)
{
  return (GET_CODE (op) == MEM) && (
#line 351 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_sve_ld1ro_operand_p (op, HImode)));
}
static inline bool
satisfies_constraint_UOw (rtx op)
{
  return (GET_CODE (op) == MEM) && (
#line 358 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_sve_ld1ro_operand_p (op, SImode)));
}
static inline bool
satisfies_constraint_UOd (rtx op)
{
  return (GET_CODE (op) == MEM) && (
#line 364 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_sve_ld1ro_operand_p (op, DImode)));
}
static inline bool
satisfies_constraint_Uty (rtx op)
{
  return (GET_CODE (op) == MEM) && (
#line 370 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_sve_ld1r_operand_p (op)));
}
static inline bool
satisfies_constraint_Utx (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_sve_struct_memory_operand (op, mode);
}
static inline bool
satisfies_constraint_Ufc (rtx op)
{
  switch (GET_CODE (op))
    {
    case CONST_DOUBLE:
    case CONST_VECTOR:
      break;
    default:
      return false;
    }
  return 
#line 382 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_float_const_representable_p (op));
}
static inline bool
satisfies_constraint_Uvi (rtx op)
{
  return (GET_CODE (op) == CONST_DOUBLE) && (
#line 388 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_can_const_movi_rtx_p (op, GET_MODE (op))));
}
static inline bool
satisfies_constraint_Do (rtx op)
{
  return (GET_CODE (op) == CONST_VECTOR) && (
#line 394 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_simd_valid_immediate (op, NULL,
						 AARCH64_CHECK_ORR)));
}
static inline bool
satisfies_constraint_Db (rtx op)
{
  return (GET_CODE (op) == CONST_VECTOR) && (
#line 401 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_simd_valid_immediate (op, NULL,
						 AARCH64_CHECK_BIC)));
}
static inline bool
satisfies_constraint_Dn (rtx op)
{
  switch (GET_CODE (op))
    {
    case CONST:
    case CONST_VECTOR:
      break;
    default:
      return false;
    }
  return 
#line 408 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_simd_valid_immediate (op, NULL));
}
static inline bool
satisfies_constraint_Dh (rtx op)
{
  return (GET_CODE (op) == CONST_INT) && (
#line 415 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_simd_scalar_immediate_valid_for_move (op,
						 HImode)));
}
static inline bool
satisfies_constraint_Dq (rtx op)
{
  return (GET_CODE (op) == CONST_INT) && (
#line 423 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_simd_scalar_immediate_valid_for_move (op,
						 QImode)));
}
static inline bool
satisfies_constraint_Dt (rtx op)
{
  return (GET_CODE (op) == CONST_DOUBLE) && (
#line 431 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_fpconst_pow2_recip (op) > 0));
}
static inline bool
satisfies_constraint_Dl (rtx op)
{
  switch (GET_CODE (op))
    {
    case CONST:
    case CONST_VECTOR:
      break;
    default:
      return false;
    }
  return 
#line 437 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_simd_shift_imm_p (op, GET_MODE (op),
						 true));
}
static inline bool
satisfies_constraint_Dr (rtx op)
{
  switch (GET_CODE (op))
    {
    case CONST:
    case CONST_VECTOR:
      break;
    default:
      return false;
    }
  return 
#line 444 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_simd_shift_imm_p (op, GET_MODE (op),
						 false));
}
static inline bool
satisfies_constraint_Dz (rtx op)
{
  switch (GET_CODE (op))
    {
    case CONST:
    case CONST_VECTOR:
      break;
    default:
      return false;
    }
  return 
#line 450 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(op == CONST0_RTX (GET_MODE (op)));
}
static inline bool
satisfies_constraint_Dm (rtx op)
{
  switch (GET_CODE (op))
    {
    case CONST:
    case CONST_VECTOR:
      break;
    default:
      return false;
    }
  return 
#line 456 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(op == CONST1_RTX (GET_MODE (op)));
}
static inline bool
satisfies_constraint_Dd (rtx op)
{
  return (GET_CODE (op) == CONST_INT) && (
#line 463 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_can_const_movi_rtx_p (op, DImode)));
}
static inline bool
satisfies_constraint_Ds (rtx op)
{
  return (GET_CODE (op) == CONST_INT) && (
#line 470 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_can_const_movi_rtx_p (op, SImode)));
}
static inline bool
satisfies_constraint_Dp (rtx op)
{
  return 
#line 475 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_address_valid_for_prefetch_p (op, true));
}
static inline bool
satisfies_constraint_vgb (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_sve_gather_immediate_b (op, mode);
}
static inline bool
satisfies_constraint_vgd (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_sve_gather_immediate_d (op, mode);
}
static inline bool
satisfies_constraint_vgh (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_sve_gather_immediate_h (op, mode);
}
static inline bool
satisfies_constraint_vgw (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_sve_gather_immediate_w (op, mode);
}
static inline bool
satisfies_constraint_vsa (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_sve_arith_immediate (op, mode);
}
static inline bool
satisfies_constraint_vsb (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_sve_vsb_immediate (op, mode);
}
static inline bool
satisfies_constraint_vsc (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_sve_cmp_vsc_immediate (op, mode);
}
static inline bool
satisfies_constraint_vss (rtx op)
{
  return 
#line 523 "/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/g/gcc-11-cross/26/work/gcc-11.5.0/gcc/config/aarch64/constraints.md"
(aarch64_sve_dup_immediate_p (op));
}
static inline bool
satisfies_constraint_vsd (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_sve_cmp_vsd_immediate (op, mode);
}
static inline bool
satisfies_constraint_vsi (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_sve_vector_inc_dec_immediate (op, mode);
}
static inline bool
satisfies_constraint_vsn (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_sve_sub_arith_immediate (op, mode);
}
static inline bool
satisfies_constraint_vsQ (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_sve_qadd_immediate (op, mode);
}
static inline bool
satisfies_constraint_vsS (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_sve_qsub_immediate (op, mode);
}
static inline bool
satisfies_constraint_vsl (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_sve_logical_immediate (op, mode);
}
static inline bool
satisfies_constraint_vsm (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_sve_vsm_immediate (op, mode);
}
static inline bool
satisfies_constraint_vsA (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_sve_float_arith_immediate (op, mode);
}
static inline bool
satisfies_constraint_vsB (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_sve_float_maxmin_immediate (op, mode);
}
static inline bool
satisfies_constraint_vsM (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_sve_float_mul_immediate (op, mode);
}
static inline bool
satisfies_constraint_vsN (rtx op)
{
  machine_mode mode = GET_MODE (op);
  return aarch64_sve_float_negated_arith_immediate (op, mode);
}
#endif /* tm-constrs.h */
