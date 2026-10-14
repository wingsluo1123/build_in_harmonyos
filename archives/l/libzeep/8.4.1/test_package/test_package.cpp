// SPDX-FileCopyrightText: 2026 OpenHarmonyPCDeveloper
// SPDX-License-Identifier: BSL-1.0
//
// test_package for libzeep 8.4.1 — 通过公共 API 验证库可用：
//   1. zeep::uri 解析 RFC3986 URI 并读取 scheme/host/port
//   2. zeep::el::object::parse_JSON 解析 JSON 并读取字段

#include <zeep/uri.hpp>
#include <zeep/el/object.hpp>

#include <iostream>
#include <string>

int main()
{
	// --- 公共 API 1: zeep::uri ---
	zeep::uri u("https://example.com:8443/soap/service?q=1#frag");

	if (u.get_scheme() != "https" or u.get_host() != "example.com" or u.get_port() != 8443)
	{
		std::cerr << "uri parse failed: scheme=" << u.get_scheme()
		          << " host=" << u.get_host() << " port=" << u.get_port() << "\n";
		return 1;
	}
	std::cout << "uri ok: " << u.get_scheme() << "://" << u.get_host() << "\n";

	// --- 公共 API 2: zeep::el::object JSON ---
	auto v = zeep::el::object::parse_JSON(R"({"name":"libzeep","version":8.4})");
	if (not v.is_object() or v["name"].get<std::string>() != "libzeep")
	{
		std::cerr << "json parse failed\n";
		return 1;
	}
	std::cout << "json ok: name=" << v["name"].get<std::string>() << "\n";

	return 0;
}
