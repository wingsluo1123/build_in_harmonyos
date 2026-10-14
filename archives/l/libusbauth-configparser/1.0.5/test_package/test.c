/*
 * Consumer test for libusbauth-configparser (1.0.5).
 *
 * Links against libusbauth-configparser::libusbauth-configparser and exercises
 * the exported public API without needing a real usbauth config file.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <usbauth/usbauth-configparser.h>

static int fails = 0;

static void check(int cond, const char *what)
{
    if (!cond) {
        printf("FAIL: %s\n", what);
        fails++;
    }
}

int main(void)
{
    /* --- parameter string <-> enum (exported mapping tables) --- */
    check(usbauth_str_to_param("idVendor") == idVendor, "str_to_param(idVendor)");
    check(usbauth_str_to_param("idProduct") == idProduct, "str_to_param(idProduct)");
    check(usbauth_str_to_param("bInterfaceClass") == bInterfaceClass,
          "str_to_param(bInterfaceClass)");
    check(usbauth_str_to_param("not-a-param") == INVALID,
          "str_to_param(unknown) -> INVALID");
    check(strcmp(usbauth_param_to_str(idVendor), "idVendor") == 0,
          "param_to_str(idVendor)");
    check(strcmp(usbauth_param_to_str(busnum), "busnum") == 0,
          "param_to_str(busnum)");

    /* --- operator string <-> enum --- */
    check(usbauth_str_to_op("==") == eq, "str_to_op(==) -> eq");
    check(usbauth_str_to_op("!=") == neq, "str_to_op(!=) -> neq");
    check(usbauth_str_to_op(">=") == ge, "str_to_op(>=) -> ge");
    check(strcmp(usbauth_op_to_str(neq), "!=") == 0, "op_to_str(neq)");
    check(strcmp(usbauth_op_to_str(l), "<") == 0, "op_to_str(l)");

    /* --- value types from the exported per-parameter map --- */
    check(usbauth_get_param_type(idVendor) == HEX, "idVendor is HEX");
    check(usbauth_get_param_type(busnum) == DEC, "busnum is DEC");
    check(usbauth_get_param_type(manufacturer) == STRING, "manufacturer is STRING");

    /* --- generic string<->enum helper over a caller array --- */
    static const char *ops[] = {"a", "b", "c"};
    check(usbauth_str_to_enum("b", ops, 3) == 1, "str_to_enum finds 'b' at 1");
    check(usbauth_str_to_enum("z", ops, 3) == INVALID,
          "str_to_enum(unknown) -> INVALID");

    /* --- build a Data entry from strings --- */
    struct Data d;
    memset(&d, 0, sizeof d);
    check(usbauth_convert_str_to_data(&d, "idVendor", "==", "1234") == true,
          "convert_str_to_data(valid) -> true");
    check(d.param == idVendor, "Data.param == idVendor");
    check(d.op == eq, "Data.op == eq");
    check(d.val != NULL && strcmp(d.val, "1234") == 0, "Data.val == \"1234\"");
    check(usbauth_convert_str_to_data(&d, "nonsense", "==", "1") == false,
          "convert_str_to_data(bad param) -> false");
    check(usbauth_convert_str_to_data(&d, "idVendor", "==", NULL) == false,
          "convert_str_to_data(NULL val) -> false");

    /* --- sub_length clamps at zero --- */
    check(usbauth_sub_length(10, 3) == 7, "sub_length(10,3) == 7");
    check(usbauth_sub_length(3, 10) == 0, "sub_length(3,10) == 0 (clamped)");
    check(usbauth_sub_length(4, 4) == 0, "sub_length(4,4) == 0");

    /* --- reading a missing config fails gracefully (-1), never crashes --- */
    setenv("USBAUTH_CONFIG", "/nonexistent/usbauth-does-not-exist.conf", 1);
    check(usbauth_config_read() == -1, "config_read(missing file) -> -1");
    struct Auth *auths = (struct Auth *)0x1;
    unsigned len = 99;
    usbauth_config_get_auths(&auths, &len);
    check(auths == NULL && len == 0,
          "get_auths -> empty (NULL/0) after a failed read");

    if (fails) {
        printf("FAIL: libusbauth-configparser consumer test (%d failure(s))\n", fails);
        return 1;
    }
    printf("PASS: libusbauth-configparser consumer test OK\n");
    return 0;
}
