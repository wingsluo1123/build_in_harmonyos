#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <gmp.h>
#include <uninum/unicode.h>
#include <uninum/nsdefs.h>
#include <uninum/uninum.h>
static void require(int ok,const char *label) {
  if(!ok){fprintf(stderr,"FAIL %s (uninum_err=%d)\n",label,uninum_err);exit(1);}
}
static void pass(const char *s){printf("CONSUMER_PASS %s\n",s);fflush(stdout);}
static void number(UTF32 *s,unsigned long want) {
  union ns_rval value;
  StringToInt(&value,s,NS_TYPE_ULONG,NS_ANY);
  require(uninum_err==NS_ERROR_OKAY && value.u==want,"numeric conversion");
}
int main(void) {
  require(strcmp(uninum_version(),"2.7")==0,"upstream version");
  require(sizeof(UTF32)==sizeof(unsigned long),"public UTF32 ABI");
  pass("upstream version and public ABI");
  UTF32 western[]={ '2','8','3','7','5',0 };
  require(GuessNumberSystem(western)==NS_WESTERN_GENERIC,"Western guess");
  number(western,28375);pass("multidigit Western detection");
  UTF32 chinese[]={0x4e03,0x5341,0x4e03,0};
  number(chinese,77);pass("Chinese normalization and conversion");
  UTF32 legal[]={0x58f9,0x4edf,0x8cb3,0x4f70,0x53c3,0x62fe,0x8086,0};
  number(legal,1234);pass("expanding Chinese legal normalization");
  UTF32 arabic[]={0x0666,0x0664,0x0665,0x0663,0};
  number(arabic,6453);pass("Arabic multidigit conversion");
  union ns_rval value;
  value.u=123456789;
  UTF32 *out=IntToString(&value,NS_ARABIC_WESTERN,NS_TYPE_ULONG);
  require(out!=NULL && uninum_err==NS_ERROR_OKAY,"roundtrip allocation");
  StringToInt(&value,out,NS_TYPE_ULONG,NS_ANY);free(out);
  require(uninum_err==NS_ERROR_OKAY && value.u==123456789,"roundtrip value");
  pass("generated UTF32 roundtrip");
  UTF32 decimal[101];for(unsigned i=0;i<100;i++)decimal[i]='9';decimal[100]=0;
  StringToInt(&value,decimal,NS_TYPE_STRING,NS_WESTERN);
  require(uninum_err==NS_ERROR_OKAY && value.s && strlen(value.s)==100,"long GMP result");
  for(unsigned i=0;i<100;i++)require(value.s[i]=='9',"long GMP digits");free(value.s);
  pass("long arbitrary precision conversion");
  return 0;
}
