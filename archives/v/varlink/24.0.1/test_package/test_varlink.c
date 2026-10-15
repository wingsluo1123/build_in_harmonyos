/* test_varlink.c — varlink 24.0.1 消费者冒烟：
 * 包含公共头 <varlink.h>，调用 varlink_object_new()/varlink_object_unref()
 * 验证库可编译、链接、运行（VarlinkObject 生命周期）。
 */
#include <stdio.h>
#include <varlink.h>

int main(void)
{
    VarlinkObject *object = NULL;
    long rc = varlink_object_new(&object);
    if (rc != 0) {
        fprintf(stderr, "varlink_object_new failed: %s\n",
                varlink_error_string(rc));
        return 1;
    }
    varlink_object_unref(object);
    printf("varlink object_new/unref OK\n");
    return 0;
}
