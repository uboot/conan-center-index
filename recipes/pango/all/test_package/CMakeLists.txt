cmake_minimum_required(VERSION 3.15)
project(test_package)

find_package(pango REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.cpp)

if (CMAKE_SYSTEM_NAME STREQUAL "Windows")
    target_link_libraries(${PROJECT_NAME} PRIVATE pango::pangocairo)
else()
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(pangocairo REQUIRED IMPORTED_TARGET pangocairo)
    target_link_libraries(${PROJECT_NAME} PRIVATE PkgConfig::pangocairo)
endif()