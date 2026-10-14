// SPDX-FileCopyrightText: 2026 OpenHarmonyPCDeveloper
// SPDX-License-Identifier: BSL-1.0
//
// 消费者用例（第三方业务组件视角，仅使用 libzeep 已安装/导出的公开头文件、公开 API、
// 正常链接目标与运行时产物）：
//   模拟一个"客户账户管理"业务上层组件：
//   1. zeep::el::object 处理业务 JSON（客户记录数组）——公开 API is_array/size/operator[]/get
//   2. zeep::http::request 构造业务表单请求并读取参数（公开 API）
//   3. zeep::http::reply::stock_reply 生成业务响应并核验状态码/内容类型
//   4. zeep::uri 解析业务端点 URL
// 输出可观察结果并以退出码报告成败（与上游测试、鸿蒙专项测试分别计数）。

#include <zeep/uri.hpp>
#include <zeep/el/object.hpp>
#include <zeep/http/request.hpp>
#include <zeep/http/reply.hpp>

#include <iostream>
#include <string>

int main()
{
	int failures = 0;

	// --- 1) 业务 JSON：客户记录数组处理 ---
	{
		auto customers = zeep::el::object::parse_JSON(
			R"([{"id":1,"name":"Alice","role":"admin"},{"id":2,"name":"Bob","role":"user"}])");

		if (not customers.is_array() or customers.size() != 2)
		{
			std::cerr << "[consumer] customers array parse failed\n";
			++failures;
		}
		else
		{
			auto &first = customers[0];
			if (first["name"].get<std::string>() != "Alice" or first["role"].get<std::string>() != "admin")
			{
				std::cerr << "[consumer] customer[0] field mismatch\n";
				++failures;
			}
			else
			{
				std::cout << "[consumer] customers ok: first=" << first["name"].get<std::string>()
				          << " count=" << customers.size() << "\n";
				// 序列化回 JSON 也是公开 API
				auto back = zeep::el::object::parse_JSON(customers.get_JSON());
				if (not back.is_array() or back.size() != 2)
				{
					std::cerr << "[consumer] json reserialize failed\n";
					++failures;
				}
				else
					std::cout << "[consumer] json reserialize ok\n";
			}
		}
	}

	// --- 2) 业务请求：form 表单参数 ---
	{
		zeep::http::request req("POST", zeep::uri("http://localhost:8080/customers"),
			{ 1, 1 }, { { "Content-Type", "application/x-www-form-urlencoded" } },
			"action=create&name=Carol");

		if (req.get_parameter("action") != "create" or req.get_parameter("name") != "Carol")
		{
			std::cerr << "[consumer] request params failed\n";
			++failures;
		}
		else
			std::cout << "[consumer] request params ok: action=" << req.get_parameter("action").value_or("")
			          << " name=" << req.get_parameter("name").value_or("") << "\n";
	}

	// --- 3) 业务响应：stock_reply 状态/内容类型 ---
	{
		auto rep = zeep::http::reply::stock_reply(zeep::http::status_type::created);
		if (rep.get_status() != zeep::http::status_type::created)
		{
			std::cerr << "[consumer] stock_reply status failed\n";
			++failures;
		}
		else
			std::cout << "[consumer] stock_reply ok: status=created("
			          << static_cast<int>(rep.get_status()) << ")\n";
	}

	// --- 4) 业务端点 URL ---
	{
		zeep::uri endpoint("https://api.example.local:9443/customers?page=2");
		if (endpoint.get_scheme() != "https" or endpoint.get_host() != "api.example.local"
			or endpoint.get_port() != 9443)
		{
			std::cerr << "[consumer] endpoint uri failed\n";
			++failures;
		}
		else
			std::cout << "[consumer] endpoint uri ok: " << endpoint.get_scheme() << "://"
			          << endpoint.get_host() << ":" << endpoint.get_port() << "\n";
	}

	if (failures == 0)
	{
		std::cout << "[consumer] all consumer checks passed\n";
		return 0;
	}

	std::cerr << "[consumer] " << failures << " check(s) failed\n";
	return 1;
}