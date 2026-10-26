// SPDX-License-Identifier: MIT
// Copyright (c) 2026 openswx contributors
#include <charconv>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <limits>
#include <string_view>
#include <system_error>

#include "openswstep/export.h"

namespace {
bool ReadIndex(std::string_view text, uint64_t& value) {
  const auto parsed =
      std::from_chars(text.data(), text.data() + text.size(), value);
  return parsed.ec == std::errc{} && parsed.ptr == text.data() + text.size();
}

const char* ErrorCodeName(openparasolid::ErrorCode code) {
  using openparasolid::ErrorCode;
  switch (code) {
    case ErrorCode::kIo:
      return "io";
    case ErrorCode::kInvalidHeader:
      return "invalid_header";
    case ErrorCode::kUnsupportedFormat:
      return "unsupported_format";
    case ErrorCode::kResourceLimit:
      return "resource_limit";
    case ErrorCode::kInvalidOptions:
      return "invalid_options";
    case ErrorCode::kInvalidSchema:
      return "invalid_schema";
    case ErrorCode::kInvalidRecord:
      return "invalid_record";
    case ErrorCode::kUnsupportedSchema:
      return "unsupported_schema";
  }
  return "unknown_error";
}

void WriteJsonString(std::string_view value) {
  constexpr char kHex[] = "0123456789abcdef";
  std::cout << '"';
  for (unsigned char character : value) {
    if (character == '"' || character == '\\') {
      std::cout << '\\' << static_cast<char>(character);
    } else if (character < 0x20) {
      std::cout << "\\u00" << kHex[character >> 4] << kHex[character & 15];
    } else {
      std::cout << static_cast<char>(character);
    }
  }
  std::cout << '"';
}

void ReportError(const openparasolid::ParseError& error) {
  std::cout << "{\"error_code\":\"" << ErrorCodeName(error.code)
            << "\",\"offset\":" << error.offset << ",\"message\":";
  WriteJsonString(error.message);
  std::cout << "}\n";
}
}  // namespace

int main(int argc, char** argv) {
  if (argc != 5) {
    std::cerr << "Usage: case_export <captured.sldprt> <payload-index> "
                 "<body-id> <output.step>\n";
    return 1;
  }
  uint64_t payload = 0;
  uint64_t body = 0;
  if (!ReadIndex(argv[2], payload) || !ReadIndex(argv[3], body) || body == 0 ||
      body > std::numeric_limits<uint32_t>::max() ||
      payload > std::numeric_limits<std::size_t>::max()) {
    std::cerr << "Invalid explicit payload/body selection\n";
    return 1;
  }
  // Initial captured fixtures have independently verified metre coordinates.
  // This driver neither selects a configuration nor resolves delta history.
  openswstep::ExportOptions options;
  options.length_unit = openswstep::LengthUnit::kMetre;
  options.tolerance = 1e-8;
  const char* chart =
      std::getenv("OPENSWX_CORPUS_INTERSECTION_CHART_TOLERANCE");
  const char* solve =
      std::getenv("OPENSWX_CORPUS_INTERSECTION_SOLVE_TOLERANCE");
  if (chart || solve) {
    const auto positive = [](const char* text, double& value) {
      if (!text) return false;
      const std::string_view input(text);
      const auto parsed =
          std::from_chars(input.data(), input.data() + input.size(), value);
      return parsed.ec == std::errc{} &&
             parsed.ptr == input.data() + input.size() &&
             std::isfinite(value) && value > 0;
    };
    openparasolid::IntersectionEvaluationOptions intersection;
    if (!positive(chart, intersection.chart_tolerance) ||
        !positive(solve, intersection.solve_tolerance)) {
      std::cerr << "Both OPENSWX_CORPUS_INTERSECTION_CHART_TOLERANCE and "
                   "OPENSWX_CORPUS_INTERSECTION_SOLVE_TOLERANCE must be "
                   "positive finite numbers when either is specified\n";
      return 1;
    }
    options.binding.intersection = intersection;
  }
  const auto step = openswstep::ExportSolidWorksFile(
      std::filesystem::path(argv[1]), static_cast<std::size_t>(payload),
      openparasolid::NodeId{static_cast<uint32_t>(body)}, options);
  if (!step.ok()) {
    ReportError(step.error());
    std::cerr << "Export failed at " << step.error().offset << ": "
              << step.error().message << '\n';
    return 2;
  }
  const auto written =
      openswstep::WriteStepFile(step.value(), std::filesystem::path(argv[4]));
  if (!written.ok()) {
    ReportError(written.error());
    std::cerr << written.error().message << '\n';
    return 3;
  }
  const auto& counts = step.value().statistics;
  std::cout << "{\"faces\":" << counts.faces << ",\"edges\":" << counts.edges
            << ",\"vertices\":" << counts.vertices
            << ",\"shells\":" << counts.shells
            << ",\"solids\":" << counts.solids << "}\n";
  return 0;
}
