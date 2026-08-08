/*
 * test.c — L1 smoke test for xmlrpc-c
 *
 * Verifies the core XML-RPC value creation and parsing API.
 * Links against libxmlrpc and libxmlrpc_util.
 */
#include <xmlrpc-c/base.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    xmlrpc_env env;
    xmlrpc_env_init(&env);

    /* Create an integer value */
    xmlrpc_value *val = xmlrpc_int_new(&env, 42);
    if (env.fault_occurred) {
        fprintf(stderr, "xmlrpc_int_new failed: %s\n", env.fault_string);
        xmlrpc_env_clean(&env);
        return 1;
    }

    /* Read it back */
    xmlrpc_int result = 0;
    xmlrpc_read_int(&env, val, &result);
    if (env.fault_occurred) {
        fprintf(stderr, "xmlrpc_read_int failed: %s\n", env.fault_string);
        xmlrpc_DECREF(val);
        xmlrpc_env_clean(&env);
        return 1;
    }

    if (result != 42) {
        fprintf(stderr, "Expected 42, got %d\n", result);
        xmlrpc_DECREF(val);
        xmlrpc_env_clean(&env);
        return 1;
    }

    /* Test string value */
    xmlrpc_value *str = xmlrpc_string_new(&env, "hello world");
    if (env.fault_occurred) {
        fprintf(stderr, "xmlrpc_string_new failed: %s\n", env.fault_string);
        xmlrpc_DECREF(val);
        xmlrpc_env_clean(&env);
        return 1;
    }

    xmlrpc_DECREF(str);
    xmlrpc_DECREF(val);
    xmlrpc_env_clean(&env);

    printf("xmlrpc-c test: OK\n");
    return 0;
}
