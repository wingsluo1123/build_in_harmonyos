/* profiled 消费方测试：链接 libprofile，与真实 profiled 守护进程完成
 * profile 枚举 / 存在性判断 / 切换往返（每一步打印具名用例结果）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <profiled/libprofile.h>

static int failures = 0;

static void
report(const char *name, int ok, const char *detail)
{
  printf("[CASE] %s: %s%s%s\n", name, ok ? "PASS" : "FAIL",
         detail && *detail ? " -- " : "", detail ? detail : "");
  fflush(stdout);
  if( !ok ) ++failures;
}

int
main(void)
{
  char **profiles = profile_get_profiles();
  int count = 0;

  while( profiles && profiles[count] ) ++count;
  report("profiles_listed", count >= 4, "builtin profiles >= 4");
  printf("  profiles(%d):", count);
  for( int i = 0; i < count; ++i ) printf(" %s", profiles[i]);
  printf("\n");

  report("has_profile_builtin", profile_has_profile("silent") == 1,
         "profile_has_profile(silent)");
  report("has_profile_unknown", profile_has_profile("no-such-profile") == 0,
         "profile_has_profile(no-such-profile)");

  int rc = profile_set_profile("silent");
  char *cur = profile_get_profile();
  report("switch_to_silent", rc == 0 && cur && strcmp(cur, "silent") == 0,
         cur ? cur : "()");
  free(cur);

  rc = profile_set_profile("general");
  cur = profile_get_profile();
  report("switch_back_general", rc == 0 && cur && strcmp(cur, "general") == 0,
         cur ? cur : "()");
  free(cur);

  profile_free_profiles(profiles);

  printf("[CASE] summary: %d failure(s)\n", failures);
  return failures ? 1 : 0;
}
