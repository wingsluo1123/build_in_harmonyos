#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stddef.h>
#include "dyncall.h"
#include "dyncall_callback.h"
#include "dyncall_thunk.h"
#include "dynload.h"

typedef struct { long long a, b; } I2;
typedef struct { long long a, b, c; } Big;
typedef struct { float a, b, c, d; } H4;

static I2 i2_func(I2 x) { x.a += 2; x.b += 3; return x; }
static Big big_func(Big x) { x.a += 2; x.b += 3; x.c += 4; return x; }
static H4 h4_func(H4 x) { x.a += 1; x.b += 2; x.c += 3; x.d += 4; return x; }
static I2 gp_spill(long long a, long long b, long long c, long long d,
                   long long e, long long f, long long g, I2 x, long long y)
{ x.a += a+b+c+d+e+f+g+y; x.b += y; return x; }
static H4 fp_spill(double a, double b, double c, double d, double e, double f, H4 x, double y)
{ x.a += a+b+c+d+e+f+y; return x; }

static char big_handler(DCCallback* cb, DCArgs* args, DCValue* result, void* user)
{
  Big x;
  (void)cb; (void)user;
  dcbArgAggr(args, &x);
  x = big_func(x);
  dcbReturnAggr(args, result, &x);
  return 'A';
}
static char gp_handler(DCCallback* cb, DCArgs* args, DCValue* result, void* user)
{
  I2 x;
  long long sum = 0, y;
  int i;
  (void)cb; (void)user;
  for(i=0;i<7;++i) sum += dcbArgLongLong(args);
  dcbArgAggr(args, &x);
  y = dcbArgLongLong(args);
  x.a += sum+y; x.b += y;
  dcbReturnAggr(args, result, &x);
  return 'A';
}
static char fp_handler(DCCallback* cb, DCArgs* args, DCValue* result, void* user)
{
  H4 x;
  double sum = 0;
  int i;
  (void)cb; (void)user;
  for(i=0;i<6;++i) sum += dcbArgDouble(args);
  dcbArgAggr(args, &x);
  x.a += sum+dcbArgDouble(args);
  dcbReturnAggr(args, result, &x);
  return 'A';
}

#define CHECK(x, label) do { if(!(x)) { fprintf(stderr,"FAIL %s\n",label); return 1; } ++passed; } while(0)
int main(void)
{
  DCaggr *ai = dcNewAggr(2,sizeof(I2)), *ab = dcNewAggr(3,sizeof(Big)), *ah = dcNewAggr(4,sizeof(H4));
  DCCallVM* vm = dcNewCallVM(4096);
  DCaggr* descriptors[2];
  DCCallback* cb;
  I2 i={11,22}, ir;
  Big b={1,2,3}, br;
  H4 h={1,2,3,4}, hr;
  int k, passed=0;
  CHECK(ai && ab && ah && vm,"allocation");
  dcAggrField(ai,'l',offsetof(I2,a),1); dcAggrField(ai,'l',offsetof(I2,b),1); dcCloseAggr(ai);
  dcAggrField(ab,'l',offsetof(Big,a),1); dcAggrField(ab,'l',offsetof(Big,b),1); dcAggrField(ab,'l',offsetof(Big,c),1); dcCloseAggr(ab);
  dcAggrField(ah,'f',offsetof(H4,a),1); dcAggrField(ah,'f',offsetof(H4,b),1); dcAggrField(ah,'f',offsetof(H4,c),1); dcAggrField(ah,'f',offsetof(H4,d),1); dcCloseAggr(ah);
  dcBeginCallAggr(vm,ai); dcArgAggr(vm,ai,&i); dcCallAggr(vm,(DCpointer)i2_func,ai,&ir);
  CHECK(ir.a==13 && ir.b==25,"i2_regs");
  dcReset(vm); dcBeginCallAggr(vm,ab); dcArgAggr(vm,ab,&b); dcCallAggr(vm,(DCpointer)big_func,ab,&br);
  CHECK(br.a==3 && br.b==5 && br.c==7 && b.a==1 && b.b==2 && b.c==3,"large_copy_x8");
  dcReset(vm); dcBeginCallAggr(vm,ah); dcArgAggr(vm,ah,&h); dcCallAggr(vm,(DCpointer)h4_func,ah,&hr);
  CHECK(hr.a==2 && hr.b==4 && hr.c==6 && hr.d==8,"hfa_return_four_regs");
  dcReset(vm); dcBeginCallAggr(vm,ai); for(k=1;k<=7;++k) dcArgLongLong(vm,k);
  dcArgAggr(vm,ai,&i); dcArgLongLong(vm,8); dcCallAggr(vm,(DCpointer)gp_spill,ai,&ir);
  CHECK(ir.a==47 && ir.b==30,"gp_spill_no_split");
  dcReset(vm); dcBeginCallAggr(vm,ah); for(k=1;k<=6;++k) dcArgDouble(vm,k);
  dcArgAggr(vm,ah,&h); dcArgDouble(vm,7); dcCallAggr(vm,(DCpointer)fp_spill,ah,&hr);
  CHECK(hr.a==29 && hr.b==2 && hr.c==3 && hr.d==4,"hfa_spill_exhausts_fp_bank");
  descriptors[0]=descriptors[1]=ab;
  cb=dcbNewCallback2("A)A",big_handler,NULL,descriptors);
  CHECK(cb!=NULL,"callback_big_alloc");
  br=((Big(*)(Big))cb)(b); dcbFreeCallback(cb);
  CHECK(br.a==3 && br.b==5 && br.c==7 && b.a==1,"callback_indirect_x8");
  descriptors[0]=descriptors[1]=ai;
  cb=dcbNewCallback2("lllllllAl)A",gp_handler,NULL,descriptors);
  CHECK(cb!=NULL,"callback_gp_alloc");
  ir=((I2(*)(long long,long long,long long,long long,long long,long long,long long,I2,long long))cb)(1,2,3,4,5,6,7,i,8);
  dcbFreeCallback(cb); CHECK(ir.a==47 && ir.b==30,"callback_gp_stack");
  descriptors[0]=descriptors[1]=ah;
  cb=dcbNewCallback2("ddddddAd)A",fp_handler,NULL,descriptors);
  CHECK(cb!=NULL,"callback_fp_alloc");
  hr=((H4(*)(double,double,double,double,double,double,H4,double))cb)(1,2,3,4,5,6,h,7);
  dcbFreeCallback(cb); CHECK(hr.a==29 && hr.b==2 && hr.c==3 && hr.d==4,"callback_hfa_stack_return");
  CHECK(dcGetError(vm)==DC_ERROR_NONE,"vm_error_state");
  dcFree(vm); dcFreeAggr(ai); dcFreeAggr(ab); dcFreeAggr(ah);
  DLLib* library = dlLoadLibrary(NULL);
  CHECK(library != NULL, "dynload_process");
  CHECK(dlFindSymbol(library, "printf") != NULL, "dynload_symbol");
  dlFreeLibrary(library);
  printf("AAPCS64_MINIMUM_ASSERTIONS %d\nCONSUMER_1_OF_1_PASS\n",passed);
  return 0;
}
