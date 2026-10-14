// SPDX-FileCopyrightText: 2026 OpenHarmonyPCDeveloper
// SPDX-License-Identifier: BSL-1.0
//
// 鸿蒙专项测试 — libzeep 8.4.1 在 OpenHarmony PC（OHOS aarch64）上的真实可执行验证。
// 与上游测试/test_package/消费者用例分别计数，验证 OHOS 适配关键路径：
//   1. zeep::uri 公开 API 解析 RFC3986 URI（验证 OHOS 下 URI 解析正确性）
//   2. zeep::el::object JSON 公开 API 往返（parse_JSON → get_JSON，验证 fmt 替换后的序列化）
//   3. 本机 HTTP daemon 往返：在 OHOS loopback 上启动真实 daemon + controller，
//      经 zeep::http::get_request 发起 GET 并校验状态码与响应体
//      （验证 HTTP 服务器/客户端在 OHOS 上可编译、链接、运行）

#include <zeep/uri.hpp>
#include <zeep/el/object.hpp>
#include <zeep/http/client.hpp>
#include <zeep/http/controller.hpp>
#include <zeep/http/daemon.hpp>
#include <zeep/http/html-controller.hpp>
#include <zeep/http/reply.hpp>
#include <zeep/http/server.hpp>

#include <chrono>
#include <iostream>
#include <random>
#include <string>
#include <thread>

using namespace std::chrono_literals;

namespace
{

// 简单 JSON 控制器：GET / → application/json 响应体
class ohos_json_controller : public zeep::http::html_controller_v1
{
  public:
	ohos_json_controller()
		: zeep::http::html_controller_v1("/")
	{
		mount("", &ohos_json_controller::handle_index);
	}

	void handle_index(const zeep::http::request & /*req*/, const zeep::http::scope & /*scope*/, zeep::http::reply &rep)
	{
		rep = zeep::http::reply::stock_reply(zeep::http::status_type::ok);
		rep.set_content(R"({"service":"libzeep","os":"OHOS","ok":true})", "application/json");
	}
};

} // namespace

int main()
{
	int failures = 0;

	// --- 1) zeep::uri 公开 API ---
	{
		zeep::uri u("https://example.com:8443/soap/service?q=1#frag");
		if (u.get_scheme() != "https" or u.get_host() != "example.com" or u.get_port() != 8443)
		{
			std::cerr << "[ohos] uri parse failed: scheme=" << u.get_scheme()
			          << " host=" << u.get_host() << " port=" << u.get_port() << "\n";
			++failures;
		}
		else
			std::cout << "[ohos] uri ok: " << u.get_scheme() << "://" << u.get_host() << "\n";
	}

	// --- 2) zeep::el::object JSON 公开 API 往返 ---
	{
		auto v = zeep::el::object::parse_JSON(R"({"name":"libzeep","version":8.4,"ok":true})");
		auto round = zeep::el::object::parse_JSON(v.get_JSON());
		if (not v.is_object() or v["name"].get<std::string>() != "libzeep" or not round.is_object())
		{
			std::cerr << "[ohos] json roundtrip failed\n";
			++failures;
		}
		else
			std::cout << "[ohos] json roundtrip ok: name=" << v["name"].get<std::string>() << "\n";
	}

	// --- 3) 本机 HTTP daemon 往返（OHOS loopback）---
	{
		zeep::http::daemon d([]()
			{
			auto server = new zeep::http::server;
			server->add_controller(new ohos_json_controller());
			return server; },
			"zeep-ohos-test");

		std::random_device rng;
		uint16_t port = 1024 + (rng() % 10240);

		std::thread t([&d, port]
			{ return d.run_foreground("::", port); });

		std::this_thread::sleep_for(100ms);

		zeep::uri uri("http://localhost:" + std::to_string(port) + "/");

		try
		{
			auto reply = zeep::http::get_request(uri);
			if (reply.get_status() != zeep::http::status_type::ok)
			{
				std::cerr << "[ohos] http daemon roundtrip: status != ok\n";
				++failures;
			}
			else
			{
				auto body = reply.get_content();
				auto j = zeep::el::object::parse_JSON(body);
				if (j.is_object() and j["service"].get<std::string>() == "libzeep" and j["ok"].get<bool>())
					std::cout << "[ohos] http daemon roundtrip ok\n";
				else
				{
					std::cerr << "[ohos] http daemon roundtrip: body unexpected: " << body << "\n";
					++failures;
				}
			}
		}
		catch (const std::exception &ex)
		{
			std::cerr << "[ohos] http daemon roundtrip exception: " << ex.what() << "\n";
			++failures;
		}

		// OHOS 上 HTTP_HAS_UNIX_DAEMON=0，daemon::stop() 不存在（公开 API 守卫）；
		// 测试进程即将退出，detach 让 run_foreground 线程随进程退出自然结束
		t.detach();
	}

	if (failures == 0)
	{
		std::cout << "[ohos] all HarmonyOS-specific checks passed\n";
		return 0;
	}

	std::cerr << "[ohos] " << failures << " check(s) failed\n";
	return 1;
}
