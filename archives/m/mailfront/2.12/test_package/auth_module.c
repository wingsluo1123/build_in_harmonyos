#include <bglibs/sysdeps.h>
#include <cvm/module.h>
#include <unistd.h>

const char program[] = "mailfront_testcvm";

int cvm_module_init(void)
{
  return 0;
}

int cvm_module_lookup(void)
{
  if (cvm_module_credentials[CVM_CRED_ACCOUNT].s == 0)
    return CVME_NOCRED;
  if (str_diffs(&cvm_module_credentials[CVM_CRED_ACCOUNT], "testuser"))
    return CVME_PERMFAIL;
  return 0;
}

int cvm_module_authenticate(void)
{
  CVM_CRED_REQUIRED(PASSWORD);
  if (str_diffs(&cvm_module_credentials[CVM_CRED_PASSWORD], "testpass"))
    return CVME_PERMFAIL;
  return 0;
}

int cvm_module_results(void)
{
  cvm_fact_username = "testuser";
  cvm_fact_userid = getuid();
  cvm_fact_groupid = getgid();
  cvm_fact_realname = "Mailfront Test User";
  cvm_fact_directory = "/data/storage/el2/base/cache";
  cvm_fact_shell = "/bin/false";
  cvm_fact_mailbox = "mailfront-test";
  cvm_fact_groupname = 0;
  return 0;
}

void cvm_module_stop(void)
{
}
