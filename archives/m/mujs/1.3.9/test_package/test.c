#include <stdio.h>
#include <stdlib.h>
#include <mujs.h>

static void jsB_print(js_State *J)
{
    int i, top = js_gettop(J);
    for (i = 1; i < top; ++i) {
        const char *s = js_tostring(J, i);
        if (i > 1) putchar(' ');
        fputs(s, stdout);
    }
    putchar('\n');
    js_pushundefined(J);
}

int main(void)
{
    js_State *J = js_newstate(NULL, NULL, JS_STRICT);
    if (!J) {
        fprintf(stderr, "Failed to create JS state\n");
        return 1;
    }

    /* Register print function (same as mujs CLI does) */
    js_newcfunction(J, jsB_print, "print", 0);
    js_setglobal(J, "print");

    /* Test 1: Basic math and string concatenation */
    int ret = js_dostring(J, "var x = 1 + 2 + 3; print('mujs test: ' + x);");
    if (ret != 0) {
        fprintf(stderr, "Test 1 failed: js_dostring returned %d\n", ret);
        js_freestate(J);
        return 1;
    }

    /* Test 2: JSON support */
    ret = js_dostring(J, "var obj = JSON.parse('{\"a\":10,\"b\":20}'); print(obj.a + obj.b);");
    if (ret != 0) {
        fprintf(stderr, "Test 2 failed: js_dostring returned %d\n", ret);
        js_freestate(J);
        return 1;
    }

    /* Test 3: Math object */
    ret = js_dostring(J, "print(Math.max(1, 2, 3));");
    if (ret != 0) {
        fprintf(stderr, "Test 3 failed: js_dostring returned %d\n", ret);
        js_freestate(J);
        return 1;
    }

    js_freestate(J);
    return 0;
}
