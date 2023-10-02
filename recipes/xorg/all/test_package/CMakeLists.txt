cmake_minimum_required(VERSION 3.1)
project(test_package LANGUAGES C)

find_package(xorg REQUIRED CONFIG)

add_executable(test_package test_package.c)
find_package(PkgConfig REQUIRED)
pkg_check_modules(xorg REQUIRED IMPORTED_TARGET xorg)
target_link_libraries(${PROJECT_NAME} PRIVATE PkgConfig::xorg)
