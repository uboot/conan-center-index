cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(GstPluginsRs REQUIRED CONFIG)

if (STATIC)
    add_compile_definitions(GST_STATIC_COMPILATION)
endif()

add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} GstPluginsRs::gstrsrtp)
