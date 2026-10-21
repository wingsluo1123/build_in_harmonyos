#include <asio.hpp>
#include <array>
#include <chrono>
#include <iostream>
#include <string>

int main() {
    if (ASIO_VERSION != 103802) return 1;
    asio::io_context context;
    int completed = 0;
    asio::post(context, [&] { ++completed; });
    asio::steady_timer timer(context, std::chrono::milliseconds(5));
    timer.async_wait([&](const asio::error_code& error) { if (!error) ++completed; });
    context.run();
    if (completed != 2) return 2;
    std::cout << "CONSUMER_API_PASS=1/1 post steady-timer\n";

    using asio::ip::tcp;
    tcp::acceptor listener(context, tcp::endpoint(asio::ip::address_v4::loopback(), 0));
    tcp::socket client(context), server(context);
    client.connect(listener.local_endpoint());
    listener.accept(server);
    const std::string payload = "鸿蒙 Asio 回环数据";
    asio::write(client, asio::buffer(payload));
    std::string received(payload.size(), '\0');
    asio::read(server, asio::buffer(received));
    if (received != payload) return 3;
    client.shutdown(tcp::socket::shutdown_send);
    std::array<char, 1> extra;
    asio::error_code error;
    if (server.read_some(asio::buffer(extra), error) != 0 || error != asio::error::eof) return 4;
    server.close(); client.close(); listener.close();
    std::cout << "ASIO_HARMONY_E2E_PASS=1/1 loopback-tcp utf8-payload exact-read graceful-eof\n";
    return 0;
}
