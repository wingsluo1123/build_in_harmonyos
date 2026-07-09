// test_package/test.cpp — libzippp L1 测试
// 验证 libzippp 可以被链接和基本 API 可用

#include <libzippp.h>
#include <iostream>
#include <cstdlib>

int main() {
    using namespace libzippp;

    // 创建一个临时 ZIP 文件并写入
    const char* tmpPath = "/tmp/test_libzippp_l1.zip";
    const char* envTmp = std::getenv("TMPDIR");
    std::string zipPath = envTmp ? (std::string(envTmp) + "/test_libzippp_l1.zip") : tmpPath;

    // 创建 ZIP 并添加条目
    ZipArchive z1(zipPath.c_str(), ZipArchive::NEW);
    if (!z1.isOpen()) {
        std::cerr << "FAIL: 无法创建 ZIP 文件" << std::endl;
        return 1;
    }
    z1.addData("hello.txt", "Hello, libzippp!", 17);
    z1.close();

    // 重新打开并读取
    ZipArchive z2(zipPath.c_str(), ZipArchive::READ_ONLY);
    if (!z2.isOpen()) {
        std::cerr << "FAIL: 无法打开 ZIP 文件" << std::endl;
        return 1;
    }

    int nbEntries = z2.getNbEntries();
    if (nbEntries != 1) {
        std::cerr << "FAIL: 条目数应为 1，实际 " << nbEntries << std::endl;
        return 1;
    }

    std::string data = z2.readEntry("hello.txt", true);
    if (data != "Hello, libzippp!") {
        std::cerr << "FAIL: 内容不匹配: " << data << std::endl;
        return 1;
    }

    z2.close();

    std::cout << "PASS: libzippp 创建/读取 ZIP 验证通过" << std::endl;
    return 0;
}
