# @file CMakeLists.txt
# @brief Builds the protocol library, command-line tools, tests, benchmark, and optional fuzz target.
# @details Target and option locations are indexed in docs/generated/symbol-index.md.

cmake_minimum_required(VERSION 3.25)
project(
  industrial_memory_protocol_workbench
  VERSION 1.0.0
  DESCRIPTION "Defensive C++20 workbench for a synthetic industrial memory protocol"
  LANGUAGES CXX)

option(IMLP_BUILD_TESTS "Build deterministic unit, integration, and property tests" ON)
option(IMLP_BUILD_FUZZER "Build the libFuzzer parser target (Clang only)" OFF)
option(IMLP_ENABLE_SANITIZERS "Enable AddressSanitizer and UndefinedBehaviorSanitizer" OFF)
option(IMLP_ENABLE_COVERAGE "Enable Clang source-based coverage instrumentation" OFF)

set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

function(imlp_set_warnings target_name)
  if(MSVC)
    target_compile_options(${target_name} PRIVATE /W4 /WX /permissive- /Zc:__cplusplus /utf-8)
  else()
    target_compile_options(
      ${target_name}
      PRIVATE -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wshadow -Werror)
  endif()
endfunction()

function(imlp_enable_instrumentation target_name)
  if(IMLP_ENABLE_SANITIZERS)
    if(NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
      message(FATAL_ERROR "Sanitizers require Clang or GCC")
    endif()
    target_compile_options(${target_name} PRIVATE -fno-omit-frame-pointer -fsanitize=address,undefined)
    target_link_options(${target_name} PRIVATE -fno-omit-frame-pointer -fsanitize=address,undefined)
  endif()

  if(IMLP_ENABLE_COVERAGE)
    if(NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang")
      message(FATAL_ERROR "Source-based coverage requires Clang")
    endif()
    target_compile_options(${target_name} PRIVATE -fprofile-instr-generate -fcoverage-mapping)
    target_link_options(${target_name} PRIVATE -fprofile-instr-generate -fcoverage-mapping)
  endif()
endfunction()

add_library(
  imlp
  src/client.cpp
  src/codec.cpp
  src/memory_map.cpp
  src/server.cpp
  src/transport.cpp)
target_include_directories(
  imlp
  PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
         $<INSTALL_INTERFACE:include>)
target_compile_features(imlp PUBLIC cxx_std_20)
imlp_set_warnings(imlp)
imlp_enable_instrumentation(imlp)

add_executable(imlp-cli apps/cli_main.cpp)
target_link_libraries(imlp-cli PRIVATE imlp)
imlp_set_warnings(imlp-cli)
imlp_enable_instrumentation(imlp-cli)

add_executable(imlp-benchmark apps/benchmark_main.cpp)
target_link_libraries(imlp-benchmark PRIVATE imlp)
imlp_set_warnings(imlp-benchmark)
imlp_enable_instrumentation(imlp-benchmark)

if(IMLP_BUILD_TESTS)
  include(CTest)
  add_executable(
    imlp-tests
    tests/test_client.cpp
    tests/test_codec.cpp
    tests/test_main.cpp
    tests/test_memory.cpp
    tests/test_properties.cpp)
  target_link_libraries(imlp-tests PRIVATE imlp)
  imlp_set_warnings(imlp-tests)
  imlp_enable_instrumentation(imlp-tests)
  add_test(NAME imlp-tests COMMAND imlp-tests)
endif()

if(IMLP_BUILD_FUZZER)
  if(NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    message(FATAL_ERROR "The fuzz target requires Clang and its matching libFuzzer runtime")
  endif()
  add_executable(imlp-codec-fuzzer fuzz/codec_fuzzer.cpp)
  target_link_libraries(imlp-codec-fuzzer PRIVATE imlp)
  target_compile_options(imlp-codec-fuzzer PRIVATE -fsanitize=fuzzer,address,undefined)
  target_link_options(imlp-codec-fuzzer PRIVATE -fsanitize=fuzzer,address,undefined)
  imlp_set_warnings(imlp-codec-fuzzer)
endif()

include(GNUInstallDirs)
install(TARGETS imlp imlp-cli EXPORT imlpTargets)
install(DIRECTORY include/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})

