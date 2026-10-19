/* ethtool/7.1 test_package — L0c 测试源文件声明件
 * CI build_and_test.sh L0c 要求 test_package/ 下存在测试源文件。
 * ethtool 是 CLI 应用：真正的消费者断言在 test_package/conanfile.py 的
 * test() 里对安装后二进制做（ethtool --version / ethtool -h 的退出码与
 * 输出特征串），本文件只声明该测试包归属，不参与断言计数。
 */
#include <stdio.h>

int main(void)
{
    printf("ethtool test package build OK\n");
    return 0;
}
