#include <SFML/Network/IpAddress.hpp>
#include <SFML/System/Clock.hpp>

int main() {
    sf::Clock clock;
    const sf::IpAddress loopback = sf::IpAddress::LocalHost;
    if (loopback.toString() != "127.0.0.1") {
        return 1;
    }
    return clock.getElapsedTime().asMicroseconds() >= 0 ? 0 : 2;
}
