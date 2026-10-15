cmake_minimum_required(VERSION 3.15)
project(picotts_consumer C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(picotts CONFIG REQUIRED)

add_executable(picotts_engine_contract picotts_engine_contract.c)
target_compile_options(picotts_engine_contract PRIVATE -Wall -Wextra -Werror)
target_link_libraries(picotts_engine_contract PRIVATE picotts::picotts)

# HarmonyOS PC 消费者端到端用例：文本 -> 合成 -> 落盘 WAV -> 校验容器
add_executable(picotts_wav_consumer picotts_wav_consumer.c)
target_compile_options(picotts_wav_consumer PRIVATE -Wall -Wextra -Werror)
target_link_libraries(picotts_wav_consumer PRIVATE picotts::picotts)
