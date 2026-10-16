/*
 * test_ws.cpp — functional consumer test for the ws (IXWebSocket) 11.4.6 package.
 *
 * Boots a WebSocket echo server on 127.0.0.1 (free port), connects a client
 * to it, sends a text message and asserts the payload round-trips back
 * unchanged. This exercises the real public API of the packaged library
 * (IXWebSocketServer + IXWebSocket handshake, transport and dispatch).
 */

#include <ixwebsocket/IXGetFreePort.h>
#include <ixwebsocket/IXWebSocket.h>
#include <ixwebsocket/IXWebSocketMessage.h>
#include <ixwebsocket/IXWebSocketMessageType.h>
#include <ixwebsocket/IXWebSocketServer.h>

#include <atomic>
#include <chrono>
#include <iostream>
#include <string>
#include <thread>

namespace
{
    const std::string kPayload = "hello-from-harmonyos-ohos";

    std::atomic<bool> gConnected{false};
    std::atomic<bool> gReceived{false};
    std::string gEchoed;

    bool waitFor(const std::atomic<bool>& flag, int timeoutMs)
    {
        for (int waited = 0; waited < timeoutMs; waited += 25)
        {
            if (flag.load())
            {
                return true;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(25));
        }
        return flag.load();
    }

    int runEchoRoundTrip()
    {
        const std::string host("127.0.0.1");
        const int port = ix::getFreePort();

        // --- server side: echo every text message back ---
        ix::WebSocketServer server(port, host);
        server.setOnClientMessageCallback(
            [](std::shared_ptr<ix::ConnectionState> connectionState,
               ix::WebSocket& webSocket,
               const ix::WebSocketMessagePtr& msg) {
                (void) connectionState;
                if (msg->type == ix::WebSocketMessageType::Message)
                {
                    webSocket.send(msg->str);
                }
            });
        if (!server.listenAndStart())
        {
            std::cerr << "ERROR: server failed to listen on " << host << ":" << port
                      << std::endl;
            return 1;
        }

        // --- client side ---
        ix::WebSocket client;
        client.setUrl("ws://" + host + ":" + std::to_string(port));
        client.setOnMessageCallback([](const ix::WebSocketMessagePtr& msg) {
            if (msg->type == ix::WebSocketMessageType::Open)
            {
                gConnected = true;
            }
            else if (msg->type == ix::WebSocketMessageType::Message)
            {
                gEchoed = msg->str;
                gReceived = true;
            }
        });
        client.start();

        int rc = 1;
        do
        {
            if (!waitFor(gConnected, 10000))
            {
                std::cerr << "ERROR: client did not connect" << std::endl;
                break;
            }
            client.send(kPayload);
            if (!waitFor(gReceived, 10000))
            {
                std::cerr << "ERROR: echo message never arrived" << std::endl;
                break;
            }
            if (gEchoed != kPayload)
            {
                std::cerr << "ERROR: payload mismatch: '" << gEchoed << "' != '"
                          << kPayload << "'" << std::endl;
                break;
            }
            std::cout << "echo round-trip OK: '" << gEchoed << "'" << std::endl;
            rc = 0;
        } while (false);

        client.stop();
        server.stop();
        return rc;
    }
} // namespace

int main()
{
    return runEchoRoundTrip();
}
