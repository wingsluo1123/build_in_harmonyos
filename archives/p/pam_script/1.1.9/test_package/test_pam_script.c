/*
 * Consumer test for the pam_script 1.1.9 Conan package on OpenHarmony.
 *
 * The package ships a loadable PAM module (lib/security/pam_script.so), so a
 * consumer test cannot link against it.  This test therefore
 *
 *   1. dlopen()s the installed module and resolves the six PAM module entry
 *      points (pam_sm_authenticate, pam_sm_setcred, pam_sm_acct_mgmt,
 *      pam_sm_chauthtok, pam_sm_open_session, pam_sm_close_session);
 *   2. drives the module through a real linux-pam stack: pam_start_confdir()
 *      with a private configuration directory, then pam_authenticate(),
 *      pam_setcred(), pam_acct_mgmt() and pam_end();
 *   3. verifies the documented option semantics end to end:
 *        - with onerr=success the module returns PAM_SUCCESS even though the
 *          configured script directory is not root-owned (the module's
 *          check_path_perms() rejects it, and onerr=success maps that to
 *          success);
 *        - without onerr=success (upstream default: fail) the same stack
 *          returns PAM_AUTH_ERR;
 *      in both cases the module must have obtained the user name and asked the
 *      application for the password through the PAM conversation callback,
 *      with the prompt string "Password: " that is hard coded upstream.
 *
 * A positive fork/exec of pam_script_auth cannot be produced here: upstream
 * check_path_perms() requires the script and its directory to be owned by
 * root:root, which a Conan consumer test running as an unprivileged user can
 * never satisfy.  The option handling above is the observable behaviour of the
 * same code path (option parsing, user lookup, authtok conversation and the
 * permission gate) that precedes the exec.
 */

#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <security/pam_appl.h>
#include <security/pam_modules.h>

#define PAM_SCRIPT_PASSWORD "s3cr3t"
#define PAM_SCRIPT_PROMPT "Password: "

static int g_conv_calls;
static char g_last_prompt[256];

static int converse(int num_msg, const struct pam_message **msg,
                    struct pam_response **resp, void *appdata_ptr)
{
    int i;
    struct pam_response *reply;

    (void) appdata_ptr;

    if (num_msg <= 0 || msg == NULL) {
        return PAM_CONV_ERR;
    }
    reply = (struct pam_response *) calloc((size_t) num_msg, sizeof(*reply));
    if (reply == NULL) {
        return PAM_BUF_ERR;
    }
    for (i = 0; i < num_msg; i++) {
        g_conv_calls++;
        if (msg[i]->msg != NULL) {
            snprintf(g_last_prompt, sizeof(g_last_prompt), "%s", msg[i]->msg);
        }
        if (msg[i]->msg_style == PAM_PROMPT_ECHO_OFF ||
            msg[i]->msg_style == PAM_PROMPT_ECHO_ON) {
            reply[i].resp = strdup(PAM_SCRIPT_PASSWORD);
            if (reply[i].resp == NULL) {
                while (i-- > 0) {
                    free(reply[i].resp);
                }
                free(reply);
                return PAM_BUF_ERR;
            }
            reply[i].resp_retcode = 0;
        }
    }
    *resp = reply;
    return PAM_SUCCESS;
}

static int g_checks;
static int g_failed;

static void check(int condition, const char *what)
{
    g_checks++;
    if (condition) {
        printf("PASS: %s\n", what);
    } else {
        g_failed++;
        printf("FAIL: %s\n", what);
    }
}

static void reset_conversation(void)
{
    g_conv_calls = 0;
    g_last_prompt[0] = '\0';
}

int main(int argc, char **argv)
{
    static const char *symbols[] = {
        "pam_sm_authenticate",
        "pam_sm_setcred",
        "pam_sm_acct_mgmt",
        "pam_sm_chauthtok",
        "pam_sm_open_session",
        "pam_sm_close_session",
    };
    struct pam_conv conv;
    pam_handle_t *pamh = NULL;
    void *module;
    size_t i;
    int retval;

    if (argc != 3) {
        fprintf(stderr, "usage: %s <pam_script.so> <pam conf dir>\n", argv[0]);
        return 2;
    }

    printf("module: %s\n", argv[1]);
    printf("confdir: %s\n", argv[2]);

    /* 1. the packaged artifact is a loadable PAM module */
    module = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    check(module != NULL, "dlopen() of the installed pam_script.so succeeds");
    if (module == NULL) {
        printf("dlopen error: %s\n", dlerror());
        printf("PAM-SCRIPT-CONSUMER-SUMMARY total=%d pass=%d fail=%d\n",
               g_checks, g_checks - g_failed, g_failed);
        return 1;
    }
    for (i = 0; i < sizeof(symbols) / sizeof(symbols[0]); i++) {
        char what[128];
        void *entry = dlsym(module, symbols[i]);
        snprintf(what, sizeof(what), "module exports %s", symbols[i]);
        check(entry != NULL, what);
    }

    conv.conv = converse;
    conv.appdata_ptr = NULL;

    /* 2. onerr=success: the module runs and reports success */
    reset_conversation();
    retval = pam_start_confdir("pam15853ok", "pamscriptuser", &conv, argv[2], &pamh);
    check(retval == PAM_SUCCESS, "pam_start_confdir() loads the pam_script auth stack");
    if (retval != PAM_SUCCESS) {
        printf("pam_start_confdir error: %d\n", retval);
    } else {
        retval = pam_authenticate(pamh, 0);
        check(retval == PAM_SUCCESS,
              "pam_authenticate() returns PAM_SUCCESS for onerr=success");
        if (retval != PAM_SUCCESS) {
            printf("pam_authenticate returned %d (%s)\n", retval, pam_strerror(pamh, retval));
        }
        check(g_conv_calls == 1, "the module asked the application for one password");
        check(strcmp(g_last_prompt, PAM_SCRIPT_PROMPT) == 0,
              "the conversation prompt is the upstream \"Password: \" text");

        retval = pam_setcred(pamh, PAM_REINITIALIZE_CRED);
        check(retval == PAM_SUCCESS, "pam_setcred() returns PAM_SUCCESS");

        retval = pam_acct_mgmt(pamh, 0);
        check(retval == PAM_SUCCESS,
              "pam_acct_mgmt() returns PAM_SUCCESS for onerr=success");

        retval = pam_end(pamh, PAM_SUCCESS);
        check(retval == PAM_SUCCESS, "pam_end() releases the handle");
        pamh = NULL;
    }

    /* 3. upstream default (onerr=fail): the same stack denies the login */
    reset_conversation();
    retval = pam_start_confdir("pam15853fail", "pamscriptuser", &conv, argv[2], &pamh);
    check(retval == PAM_SUCCESS, "pam_start_confdir() loads the default-option stack");
    if (retval == PAM_SUCCESS) {
        retval = pam_authenticate(pamh, 0);
        check(retval == PAM_AUTH_ERR,
              "pam_authenticate() returns PAM_AUTH_ERR with the upstream default onerr=fail");
        if (retval != PAM_AUTH_ERR) {
            printf("pam_authenticate returned %d (%s)\n", retval, pam_strerror(pamh, retval));
        }
        check(g_conv_calls == 1,
              "the default-option stack also asked for the password exactly once");
        check(strcmp(g_last_prompt, PAM_SCRIPT_PROMPT) == 0,
              "the default-option stack used the same \"Password: \" prompt");
        pam_end(pamh, retval);
        pamh = NULL;
    }

    dlclose(module);

    printf("PAM-SCRIPT-CONSUMER-SUMMARY total=%d pass=%d fail=%d\n",
           g_checks, g_checks - g_failed, g_failed);
    return g_failed == 0 ? 0 : 1;
}
