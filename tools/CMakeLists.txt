# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
cmake_minimum_required(VERSION 3.20)
project(openswx_corpus_checks LANGUAGES CXX)
set(OPENSWX_SOURCE_DIR "$ENV{OPENSWX_SOURCE_DIR}" CACHE PATH "openswx checkout")
if(NOT EXISTS "${OPENSWX_SOURCE_DIR}/libopenswstep/CMakeLists.txt")
  message(FATAL_ERROR "Set OPENSWX_SOURCE_DIR to an openswx checkout")
endif()
set(BUILD_TESTING OFF CACHE BOOL "Library unit tests are run separately" FORCE)
add_subdirectory("${OPENSWX_SOURCE_DIR}/libopenswstep" openswstep)
add_executable(cylinder_export cylinder_export.cc)
target_compile_features(cylinder_export PRIVATE cxx_std_20)
target_compile_options(cylinder_export PRIVATE
  $<$<CXX_COMPILER_ID:GNU,Clang>:-Wall -Wextra -Wpedantic -fno-exceptions>)
target_link_libraries(cylinder_export PRIVATE openswstep)
