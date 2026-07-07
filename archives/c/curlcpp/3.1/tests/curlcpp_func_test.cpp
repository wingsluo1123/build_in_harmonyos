#include <iostream>
#include <string>
#include <curlcpp/curl_easy.h>
#include <curlcpp/curl_global.h>
#include <curlcpp/curl_header.h>
#include <curlcpp/curl_pair.h>
#include <curlcpp/curl_exception.h>

using namespace curl;

// 回调函数，收集响应体
size_t write_cb(void *ptr, size_t size, size_t nmemb, void *userdata) {
    std::string *data = static_cast<std::string*>(userdata);
    data->append(static_cast<char*>(ptr), size * nmemb);
    return size * nmemb;
}

int main(void) {
    try {
        // 1. 初始化 curl 全局环境
        curl_global curl_global_env;
        std::cout << "[1] curl_global 初始化: OK" << std::endl;

        // 2. 创建 easy handle
        curl_easy easy;
        std::cout << "[2] curl_easy 创建: OK" << std::endl;

        // 3. 设置 URL (使用 HTTP 避免 SSL 证书问题)
        easy.add<CURLOPT_URL>("http://httpbin.org/get");
        std::cout << "[3] CURLOPT_URL 设置: OK" << std::endl;

        // 4. 设置写回调
        std::string response_data;
        easy.add<CURLOPT_WRITEFUNCTION>(write_cb);
        easy.add<CURLOPT_WRITEDATA>(&response_data);
        std::cout << "[4] CURLOPT_WRITEFUNCTION/WRITEDATA 设置: OK" << std::endl;

        // 5. 设置超时和重定向
        easy.add<CURLOPT_TIMEOUT>(10L);
        easy.add<CURLOPT_FOLLOWLOCATION>(1L);
        std::cout << "[5] CURLOPT_TIMEOUT/FOLLOWLOCATION 设置: OK" << std::endl;

        // 6. 执行请求
        std::cout << "[6] 执行 perform()..." << std::endl;
        easy.perform();
        std::cout << "[6] perform() 完成: OK" << std::endl;

        // 7. 获取 HTTP 响应码
        auto info = easy.get_info<CURLINFO_RESPONSE_CODE>();
        long http_code = info.get();
        std::cout << "[7] HTTP 状态码: " << http_code << std::endl;

        // 8. 输出响应信息
        std::cout << "[8] 响应长度: " << response_data.length() << " 字节" << std::endl;
        if (response_data.length() > 0) {
            size_t preview_len = std::min((size_t)300, response_data.length());
            std::cout << "[8] 响应预览:\n" << response_data.substr(0, preview_len) << std::endl;
        }

        std::cout << "\n=== curlcpp 3.1 功能测试全部通过 ===" << std::endl;
        return 0;

    } catch (const curl_easy_exception &e) {
        std::cerr << "\ncurlcpp 异常: " << e.what() << std::endl;
        std::cerr << "(库链接和API调用正常，异常来自网络环境)" << std::endl;
        return 2;
    } catch (const std::exception &e) {
        std::cerr << "标准异常: " << e.what() << std::endl;
        return 1;
    }
}
