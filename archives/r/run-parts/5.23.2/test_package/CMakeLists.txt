cmake_minimum_required(VERSION 3.15)
project(run_parts_consumer C)

add_executable(consumer_hook consumer_hook.c)
target_link_options(consumer_hook PRIVATE -static)
