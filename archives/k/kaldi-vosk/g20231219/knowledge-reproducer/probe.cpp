#include <lapacke.h>
#include <cblas.h>
#include <cstdint>
#include <cmath>
#include <iostream>
static_assert(sizeof(lapack_int)==sizeof(int32_t), "LP64_REQUIRED");
static_assert(sizeof(blasint)==sizeof(lapack_int), "BLAS_LAPACK_WIDTH_MISMATCH");
int main() {
  const char u='U', d='N'; lapack_int n=2, info=0;
  float s[3]={2,1,4}; double a[3]={2,1,4};
#ifdef RAW_CALL
  dtptri_(&u,&d,&n,a,&info);
#else
  LAPACK_dtptri(&u,&d,&n,a,&info);
  if(info || std::abs(a[0]-.5)>1e-12 || std::abs(a[1]+.125)>1e-12 || std::abs(a[2]-.25)>1e-12)return 1;
  LAPACK_stptri(&u,&d,&n,s,&info);
  if(info || std::abs(s[0]-.5f)>1e-6 || std::abs(s[1]+.125f)>1e-6 || std::abs(s[2]-.25f)>1e-6)return 2;
  a[0]=0; a[1]=1; a[2]=4; LAPACK_dtptri(&u,&d,&n,a,&info);
  if(info!=1)return 3;
  s[0]=0; s[1]=1; s[2]=4; LAPACK_stptri(&u,&d,&n,s,&info);
  if(info!=1)return 4;
  std::cout << "PASS float/double packed inverse (3 entries each), singular INFO=1 for both; sizeof(lapack_int)=" << sizeof(lapack_int) << " sizeof(blasint)=" << sizeof(blasint) << '\n';
#endif
}
