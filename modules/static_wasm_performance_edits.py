# Literal source edits for the Chromium 8125 optional WebAssembly optimizations.
EDITS = (
    (
        "core/fxge/dib/cstretchengine.cpp",
        """
#include <algorithm>
#include <array>
#include <optional>
#include <type_traits>
#include <utility>

#include "core/fxcrt/check.h"
#include "core/fxcrt/check_op.h"
""",
        """
#include <algorithm>
#include <array>
#include <cstring>
#include <optional>
#include <type_traits>
#include <utility>
#include <vector>

#if defined(__wasm_simd128__)
#include <wasm_simd128.h>
#elif defined(__aarch64__) && defined(__ARM_NEON)
#include <arm_neon.h>
#endif

#include "core/fxcrt/check.h"
#include "core/fxcrt/check_op.h"
""",
    ),
    (
        "core/fxge/dib/cstretchengine.cpp",
        """
namespace {

size_t TotalBytesForWeightCount(size_t weight_count) {
  // Always room for one weight even for empty ranges due to declaration
  // of weights_[1] in the header. Don't shrink below this since
""",
        """
namespace {

#if defined(__wasm_simd128__) || (defined(__aarch64__) && defined(__ARM_NEON))
// The caller has validated both rows. Each positive coefficient fits in 16
// bits and their sum is at most 65536, so the shifted result fits in a byte.
[[clang::noinline]] void BlendVerticalBgrRows(
    const uint8_t* first,
    const uint8_t* second,
    uint8_t* dest,
    size_t bytes,
    uint16_t first_weight,
    uint16_t second_weight) {
  const size_t vector_bytes = bytes & ~size_t{15};
#if defined(__wasm_simd128__)
  const v128_t w0 = wasm_i16x8_splat(first_weight);
  const v128_t w1 = wasm_i16x8_splat(second_weight);
#endif
  UNSAFE_TODO({
    for (size_t offset = 0; offset < vector_bytes; offset += 16) {
#if defined(__wasm_simd128__)
      const v128_t a = wasm_v128_load(first + offset);
      const v128_t b = wasm_v128_load(second + offset);
      const v128_t a0 = wasm_u16x8_extend_low_u8x16(a);
      const v128_t a1 = wasm_u16x8_extend_high_u8x16(a);
      const v128_t b0 = wasm_u16x8_extend_low_u8x16(b);
      const v128_t b1 = wasm_u16x8_extend_high_u8x16(b);
      const v128_t s0 = wasm_i32x4_add(wasm_u32x4_extmul_low_u16x8(a0, w0),
                                      wasm_u32x4_extmul_low_u16x8(b0, w1));
      const v128_t s1 = wasm_i32x4_add(wasm_u32x4_extmul_high_u16x8(a0, w0),
                                      wasm_u32x4_extmul_high_u16x8(b0, w1));
      const v128_t s2 = wasm_i32x4_add(wasm_u32x4_extmul_low_u16x8(a1, w0),
                                      wasm_u32x4_extmul_low_u16x8(b1, w1));
      const v128_t s3 = wasm_i32x4_add(wasm_u32x4_extmul_high_u16x8(a1, w0),
                                      wasm_u32x4_extmul_high_u16x8(b1, w1));
      const v128_t lo = wasm_i16x8_shuffle(s0, s1, 1, 3, 5, 7, 9, 11, 13, 15);
      const v128_t hi = wasm_i16x8_shuffle(s2, s3, 1, 3, 5, 7, 9, 11, 13, 15);
      wasm_v128_store(dest + offset, wasm_u8x16_narrow_i16x8(lo, hi));
#else
      const uint8x16_t a = vld1q_u8(first + offset);
      const uint8x16_t b = vld1q_u8(second + offset);
      const uint16x8_t a0 = vmovl_u8(vget_low_u8(a));
      const uint16x8_t a1 = vmovl_high_u8(a);
      const uint16x8_t b0 = vmovl_u8(vget_low_u8(b));
      const uint16x8_t b1 = vmovl_high_u8(b);
      const uint32x4_t s0 = vmlal_n_u16(
          vmull_n_u16(vget_low_u16(a0), first_weight), vget_low_u16(b0),
          second_weight);
      const uint32x4_t s1 = vmlal_high_n_u16(
          vmull_high_n_u16(a0, first_weight), b0, second_weight);
      const uint32x4_t s2 = vmlal_n_u16(
          vmull_n_u16(vget_low_u16(a1), first_weight), vget_low_u16(b1),
          second_weight);
      const uint32x4_t s3 = vmlal_high_n_u16(
          vmull_high_n_u16(a1, first_weight), b1, second_weight);
      const uint16x8_t lo = vshrn_high_n_u32(vshrn_n_u32(s0, 16), s1, 16);
      const uint16x8_t hi = vshrn_high_n_u32(vshrn_n_u32(s2, 16), s3, 16);
      vst1q_u8(dest + offset, vmovn_high_u16(vmovn_u16(lo), hi));
#endif
    }
    for (size_t offset = vector_bytes; offset < bytes; ++offset) {
      dest[offset] = CStretchEngine::PixelFromFixed(
          uint32_t{first_weight} * first[offset] +
          uint32_t{second_weight} * second[offset]);
    }
  });
}

// Filter sixteen adjacent color bytes with the same vertical tap weights.
// Four-byte formats retain the destination's unused fourth byte.
bool StretchOpaqueScanlineSimd(pdfium::span<const uint8_t> intermediate,
                               pdfium::span<uint8_t> dest,
                               int width,
                               int bytes_per_pixel,
                               int pitch,
                               int source_top,
                               const CStretchEngine::PixelWeight& weights) {
  static_assert(CStretchEngine::kFixedPointBits == 16);
  if ((bytes_per_pixel != 3 && bytes_per_pixel != 4) || width <= 0 || pitch <= 0) {
    return false;
  }
  const size_t stride = static_cast<size_t>(pitch);
  const size_t bpp = static_cast<size_t>(bytes_per_pixel);
  const size_t pixels = static_cast<size_t>(width);
  if (pixels > std::min(stride, dest.size()) / bpp) {
    return false;
  }
  const size_t row_bytes = pixels * bpp;
  const auto coefficients = weights.GetWeights();
  if (coefficients.empty()) {
    return false;
  }
  const int64_t first = static_cast<int64_t>(weights.GetSrcStart()) - source_top;
  const int64_t last = static_cast<int64_t>(weights.src_end_) - source_top;
  if (row_bytes < 16 || first < 0 || last < first ||
      static_cast<uint64_t>(last) >= intermediate.size() / stride) {
    return false;
  }

  const size_t first_row = static_cast<size_t>(first);
  const size_t taps = static_cast<size_t>(last - first) + 1;
  if (bpp == 3 && taps <= 2) {
    const uint32_t w0 = coefficients.front();
    const uint32_t w1 =
        taps == 2 ? coefficients.back() : 0;
    constexpr uint32_t kOne = 1 << CStretchEngine::kFixedPointBits;
    // Keep the generic path for coefficients outside the narrow SIMD range.
    if (w0 <= kOne && w1 <= kOne && w0 + w1 <= kOne) {
      const auto first_src = intermediate.subspan(first_row * stride, row_bytes);
      const auto last_src = intermediate.subspan(
          static_cast<size_t>(last) * stride, row_bytes);
      if (w0 == kOne || w1 == kOne) {
        const auto src = w0 == kOne ? first_src : last_src;
        std::memcpy(dest.data(), src.data(), row_bytes);
        return true;
      }
      BlendVerticalBgrRows(first_src.data(), last_src.data(), dest.data(),
                           row_bytes, static_cast<uint16_t>(w0),
                           static_cast<uint16_t>(w1));
      return true;
    }
  }
#if defined(__wasm_simd128__)
  const v128_t keep_x = wasm_i8x16_make(0, 0, 0, -1, 0, 0, 0, -1,
                                        0, 0, 0, -1, 0, 0, 0, -1);
#else
  const uint8x16_t keep_x = {0, 0, 0, 255, 0, 0, 0, 255,
                              0, 0, 0, 255, 0, 0, 0, 255};
#endif
  const size_t vector_bytes = row_bytes & ~size_t{15};

  // The checks above cover every full input row and the output row. The
  // vector loop touches only complete blocks, and the scalar tail handles
  // the remaining bytes without reading pitch padding.
  UNSAFE_TODO({
    for (size_t offset = 0; offset < vector_bytes; offset += 16) {
#if defined(__wasm_simd128__)
      v128_t accum0 = wasm_i32x4_splat(0);
      v128_t accum1 = accum0;
      v128_t accum2 = accum0;
      v128_t accum3 = accum0;
      for (size_t tap = 0; tap < taps; ++tap) {
        const v128_t input = wasm_v128_load(
            intermediate.data() + (first_row + tap) * stride + offset);
        const v128_t lo = wasm_u16x8_extend_low_u8x16(input);
        const v128_t hi = wasm_u16x8_extend_high_u8x16(input);
        const v128_t weight = wasm_i32x4_splat(static_cast<int32_t>(
            coefficients[tap]));
        accum0 = wasm_i32x4_add(accum0, wasm_i32x4_mul(wasm_u32x4_extend_low_u16x8(lo), weight));
        accum1 = wasm_i32x4_add(accum1, wasm_i32x4_mul(wasm_u32x4_extend_high_u16x8(lo), weight));
        accum2 = wasm_i32x4_add(accum2, wasm_i32x4_mul(wasm_u32x4_extend_low_u16x8(hi), weight));
        accum3 = wasm_i32x4_add(accum3, wasm_i32x4_mul(wasm_u32x4_extend_high_u16x8(hi), weight));
      }
      // Selecting byte 2 of each 32-bit sum equals PixelFromFixed, including
      // its truncation to eight bits.
      const v128_t low_bytes = wasm_i8x16_shuffle(accum0, accum1,
          2, 6, 10, 14, 18, 22, 26, 30, 0, 0, 0, 0, 0, 0, 0, 0);
      const v128_t high_bytes = wasm_i8x16_shuffle(accum2, accum3,
          2, 6, 10, 14, 18, 22, 26, 30, 0, 0, 0, 0, 0, 0, 0, 0);
      v128_t packed = wasm_i8x16_shuffle(low_bytes, high_bytes,
          0, 1, 2, 3, 4, 5, 6, 7, 16, 17, 18, 19, 20, 21, 22, 23);
      if (bpp == 4) {
        packed = wasm_v128_bitselect(wasm_v128_load(dest.data() + offset), packed, keep_x);
      }
      wasm_v128_store(dest.data() + offset, packed);
#else
      uint32x4_t accum0 = vdupq_n_u32(0);
      uint32x4_t accum1 = accum0;
      uint32x4_t accum2 = accum0;
      uint32x4_t accum3 = accum0;
      for (size_t tap = 0; tap < taps; ++tap) {
        const uint8x16_t input =
            vld1q_u8(intermediate.data() + (first_row + tap) * stride + offset);
        const uint16x8_t lo = vmovl_u8(vget_low_u8(input));
        const uint16x8_t hi = vmovl_high_u8(input);
        const uint32_t weight = coefficients[tap];
        accum0 = vmlaq_n_u32(accum0, vmovl_u16(vget_low_u16(lo)), weight);
        accum1 = vmlaq_n_u32(accum1, vmovl_high_u16(lo), weight);
        accum2 = vmlaq_n_u32(accum2, vmovl_u16(vget_low_u16(hi)), weight);
        accum3 = vmlaq_n_u32(accum3, vmovl_high_u16(hi), weight);
      }
      const uint16x8_t low_words =
          vshrn_high_n_u32(vshrn_n_u32(accum0, 16), accum1, 16);
      const uint16x8_t high_words =
          vshrn_high_n_u32(vshrn_n_u32(accum2, 16), accum3, 16);
      uint8x16_t packed = vmovn_high_u16(vmovn_u16(low_words), high_words);
      if (bpp == 4) {
        packed = vbslq_u8(keep_x, vld1q_u8(dest.data() + offset), packed);
      }
      vst1q_u8(dest.data() + offset, packed);
#endif
    }
    for (size_t offset = vector_bytes; offset < row_bytes; ++offset) {
      if (bpp == 4 && offset % 4 == 3) {
        continue;
      }
      uint32_t accum = 0;
      for (size_t tap = 0; tap < taps; ++tap) {
        const uint32_t weight = coefficients[tap];
        accum += weight * intermediate[(first_row + tap) * stride + offset];
      }
      dest[offset] = CStretchEngine::PixelFromFixed(accum);
    }
  });
  return true;
}
#if defined(__wasm_simd128__)
using HorizontalAccum = v128_t;

HorizontalAccum ZeroHorizontalAccum() {
  return wasm_i32x4_splat(0);
}

HorizontalAccum AccumulateHorizontal(HorizontalAccum accum,
                                     uint32_t packed,
                                     uint32_t weight) {
  const v128_t bytes = wasm_i32x4_splat(static_cast<int32_t>(packed));
  const v128_t channels = wasm_u32x4_extend_low_u16x8(
      wasm_u16x8_extend_low_u8x16(bytes));
  return wasm_i32x4_add(
      accum, wasm_i32x4_mul(channels,
                          wasm_i32x4_splat(static_cast<int32_t>(weight))));
}

uint32_t PackHorizontal(HorizontalAccum accum) {
  const v128_t out = wasm_i8x16_shuffle(
      accum, accum, 2, 6, 10, 14, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);
  return wasm_u32x4_extract_lane(out, 0);
}
#else
using HorizontalAccum = uint32x4_t;

HorizontalAccum ZeroHorizontalAccum() {
  return vdupq_n_u32(0);
}

HorizontalAccum AccumulateHorizontal(HorizontalAccum accum,
                                     uint32_t packed,
                                     uint32_t weight) {
  const uint16x8_t words = vmovl_u8(vcreate_u8(packed));
  const uint32x4_t channels = vmovl_u16(vget_low_u16(words));
  return vmlaq_n_u32(accum, channels, weight);
}

uint32_t PackHorizontal(HorizontalAccum accum) {
  const uint16x4_t shifted = vshrn_n_u32(accum, 16);
  const uint8x8_t out = vmovn_u16(vcombine_u16(shifted, shifted));
  return vget_lane_u32(vreinterpret_u32_u8(out), 0);
}
#endif

struct IndexedTapPair {
  uint32_t first;
  uint32_t second;
  uint32_t first_weight;
  uint32_t second_weight;
};

std::vector<IndexedTapPair> BuildIndexedTapPairs(
    int left,
    int right,
    int source_width,
    const CStretchEngine::WeightTable& table) {
  const int64_t width = static_cast<int64_t>(right) - left;
  // Bound the extra allocation independently of the original weight table.
  constexpr int64_t kMaxPlanBytes = 1 << 20;
  if (source_width <= 0 || width <= 0 ||
      width > kMaxPlanBytes / static_cast<int64_t>(sizeof(IndexedTapPair))) {
    return {};
  }

  std::vector<IndexedTapPair> pairs;
  pairs.reserve(static_cast<size_t>(width));
  for (int col = left; col < right; ++col) {
    const auto* weights = table.GetPixelWeight(col);
    const int first = weights->src_start_;
    const int last = weights->src_end_;
    if (first < 0 || last < first || last >= source_width || last - first > 1 ||
        weights->GetWeights().empty()) {
      return {};
    }
    pairs.push_back(
        {static_cast<uint32_t>(first), static_cast<uint32_t>(last),
         weights->GetWeights().front(),
         first == last ? 0u : weights->GetWeights().back()});
  }
  return pairs;
}

[[clang::noinline]] void StretchIndexedTapPairRow(
    const uint8_t* src,
    const uint32_t* palette,
    uint8_t* dest,
    pdfium::span<const IndexedTapPair> pairs) {
  // The caller validates the row sizes and the palette. The plan contains
  // only valid source indices, including for single-tap columns.
  UNSAFE_TODO({
    for (const IndexedTapPair& pair : pairs) {
      HorizontalAccum accum = AccumulateHorizontal(
          ZeroHorizontalAccum(), palette[src[pair.first]], pair.first_weight);
      accum = AccumulateHorizontal(
          accum, palette[src[pair.second]], pair.second_weight);
      const uint32_t packed = PackHorizontal(accum);
      dest[0] = static_cast<uint8_t>(packed);
      dest[1] = static_cast<uint8_t>(packed >> 8);
      dest[2] = static_cast<uint8_t>(packed >> 16);
      dest += 3;
    }
  });
}


#endif

size_t TotalBytesForWeightCount(size_t weight_count) {
  // Always room for one weight even for empty ranges due to declaration
  // of weights_[1] in the header. Don't shrink below this since
""",
    ),
    (
        "core/fxge/dib/cstretchengine.cpp",
        """    return true;
  }

  const int Bpp = dest_bpp_ / 8;
  static const int kStrechPauseRows = 10;
  int rows_to_go = kStrechPauseRows;
""",
        """    return true;
  }

#if defined(__wasm_simd128__) || (defined(__aarch64__) && defined(__ARM_NEON))
  std::vector<IndexedTapPair> indexed_pairs;
  if (trans_method_ == TransformMethod::k8BppToManyBpp &&
      dest_format_ == FXDIB_Format::kBgr && src_palette_.size() >= 256) {
    indexed_pairs = BuildIndexedTapPairs(dest_clip_.left, dest_clip_.right,
                                        src_width_, weight_table_);
  }
#endif

  const int Bpp = dest_bpp_ / 8;
  static const int kStrechPauseRows = 10;
  int rows_to_go = kStrechPauseRows;
""",
    ),
    (
        "core/fxge/dib/cstretchengine.cpp",
        """        src_row_span = Expand1BppRow(src_row_span);
        [[fallthrough]];
      case TransformMethod::k8BppToManyBpp: {
        // 3 bytes per destination pixel, written contiguously.
        auto dest_pixels =
            fxcrt::reinterpret_span<FX_BGR_STRUCT<uint8_t>>(dest_span);
""",
        """        src_row_span = Expand1BppRow(src_row_span);
        [[fallthrough]];
      case TransformMethod::k8BppToManyBpp: {
#if defined(__wasm_simd128__) || (defined(__aarch64__) && defined(__ARM_NEON))
        if (!indexed_pairs.empty() &&
            static_cast<size_t>(src_width_) <= src_row_span.size() &&
            indexed_pairs.size() <= dest_span.size() / 3) {
          StretchIndexedTapPairRow(src_row_span.data(), src_palette_.data(),
                                   dest_span.data(), indexed_pairs);
          break;
        }
#endif
        // 3 bytes per destination pixel, written contiguously.
        auto dest_pixels =
            fxcrt::reinterpret_span<FX_BGR_STRUCT<uint8_t>>(dest_span);
""",
    ),
    (
        "core/fxge/dib/cstretchengine.cpp",
        """
  for (int row = dest_clip_.top; row < dest_clip_.bottom; ++row) {
    const PixelWeight* pWeights = table.GetPixelWeight(row);
    pdfium::span<const uint32_t> weights = pWeights->GetWeights();
    if (!weights.empty()) {
      CHECK_GE(pWeights->src_start_, src_clip_.top);
""",
        """
  for (int row = dest_clip_.top; row < dest_clip_.bottom; ++row) {
    const PixelWeight* pWeights = table.GetPixelWeight(row);
#if defined(__wasm_simd128__) || (defined(__aarch64__) && defined(__ARM_NEON))
    if ((trans_method_ == TransformMethod::k8BppToManyBpp ||
         trans_method_ == TransformMethod::kManyBpptoManyBpp) &&
        StretchOpaqueScanlineSimd(inter_buf_, dest_scanline_, dest_cols,
                                  DestBpp, inter_pitch_, src_clip_.top,
                                  *pWeights)) {
      dest_bitmap_->ComposeScanline(row - dest_clip_.top, dest_scanline_);
      continue;
    }
#endif
    pdfium::span<const uint32_t> weights = pWeights->GetWeights();
    if (!weights.empty()) {
      CHECK_GE(pWeights->src_start_, src_clip_.top);
""",
    ),
    (
        "core/fxge/dib/cfx_scanlinecompositor.cpp",
        """#include "core/fxge/dib/cfx_scanlinecompositor.h"

#include <algorithm>
#include <type_traits>

#include "core/fxcrt/check.h"
#include "core/fxcrt/check_op.h"
#include "core/fxcrt/compiler_specific.h"
""",
        """#include "core/fxge/dib/cfx_scanlinecompositor.h"

#include <algorithm>
#include <functional>
#include <type_traits>

#if defined(__wasm_simd128__)
#include <wasm_simd128.h>
#elif defined(__aarch64__) && defined(__ARM_NEON)
#include <arm_neon.h>
#endif

#include "core/fxcrt/check.h"
#include "core/fxcrt/check_op.h"
#include "core/fxcrt/compiler_specific.h"
""",
    ),
    (
        "core/fxge/dib/cfx_scanlinecompositor.cpp",
        """  });
}

// Copies a source pixel into a BGRA destination, forcing it opaque. The
// source may carry an alpha channel or not; it is ignored either way.
template <typename SrcPixelStruct, typename DestPixelStruct>
""",
        """  });
}

#if defined(__wasm_simd128__)
template <bool kRgbOrder, int Start>
v128_t ExpandFourBgrPixels(v128_t first, v128_t second) {
  constexpr int kFirstColor = kRgbOrder ? 2 : 0;
  constexpr int kThirdColor = kRgbOrder ? 0 : 2;
  const v128_t pixels = wasm_i8x16_shuffle(
      first, second, Start + kFirstColor, Start + 1, Start + kThirdColor, 0,
      Start + 3 + kFirstColor, Start + 4, Start + 3 + kThirdColor, 0,
      Start + 6 + kFirstColor, Start + 7, Start + 6 + kThirdColor, 0,
      Start + 9 + kFirstColor, Start + 10, Start + 9 + kThirdColor, 0);
  return wasm_v128_or(pixels, wasm_i32x4_splat(-16777216));
}
#endif

#if defined(__wasm_simd128__) || (defined(__aarch64__) && defined(__ARM_NEON))
template <bool kRgbOrder>
[[clang::noinline]] void ExpandBgrBlocks(const uint8_t* source,
                                        uint8_t* dest,
                                        size_t blocks) {
  // Each block reads exactly 48 source bytes and writes 64 output bytes.
  UNSAFE_TODO({
    for (; blocks != 0; --blocks, source += 48, dest += 64) {
#if defined(__wasm_simd128__)
      const v128_t first = wasm_v128_load(source);
      const v128_t middle = wasm_v128_load(source + 16);
      const v128_t last = wasm_v128_load(source + 32);
      wasm_v128_store(dest, ExpandFourBgrPixels<kRgbOrder, 0>(first, first));
      wasm_v128_store(dest + 16,
                      ExpandFourBgrPixels<kRgbOrder, 12>(first, middle));
      wasm_v128_store(dest + 32,
                      ExpandFourBgrPixels<kRgbOrder, 8>(middle, last));
      wasm_v128_store(dest + 48, ExpandFourBgrPixels<kRgbOrder, 4>(last, last));
#else
      const uint8x16x3_t bgr = vld3q_u8(source);
      const uint8x16x4_t pixels = {{
          bgr.val[kRgbOrder ? 2 : 0], bgr.val[1],
          bgr.val[kRgbOrder ? 0 : 2], vdupq_n_u8(255),
      }};
      vst4q_u8(dest, pixels);
#endif
    }
  });
}
#endif

// Copies a source pixel into a BGRA destination, forcing it opaque. The
// source may carry an alpha channel or not; it is ignored either way.
template <typename SrcPixelStruct, typename DestPixelStruct>
""",
    ),
    (
        "core/fxge/dib/cfx_scanlinecompositor.cpp",
        """    pdfium::span<DestPixelStruct> dest_span,
    pdfium::span<const uint8_t> src_span,
    int src_Bpp) {
  const size_t width = dest_span.size();
  if (src_Bpp == 3) {
    auto bgr_span = fxcrt::reinterpret_span<const FX_BGR_STRUCT<uint8_t>>(
""",
        """    pdfium::span<DestPixelStruct> dest_span,
    pdfium::span<const uint8_t> src_span,
    int src_Bpp) {
#if defined(__wasm_simd128__) || (defined(__aarch64__) && defined(__ARM_NEON))
  static_assert(sizeof(DestPixelStruct) == 4);
  const size_t blocks = dest_span.size() / 16;
  if (src_Bpp == 3 && blocks != 0 &&
      dest_span.size() <= src_span.size() / 3) {
    const auto source = src_span.first(dest_span.size() * 3);
    auto* out = reinterpret_cast<uint8_t*>(dest_span.data());
    const auto* out_end = reinterpret_cast<const uint8_t*>(
        UNSAFE_TODO(dest_span.data() + dest_span.size()));
    const auto* source_end = UNSAFE_TODO(source.data() + source.size());
    const std::less<const uint8_t*> less;
    if (!less(out, source_end) || !less(source.data(), out_end)) {
      constexpr bool kRgbOrder =
          std::is_same_v<DestPixelStruct, FX_RGBA_STRUCT<uint8_t>>;
      ExpandBgrBlocks<kRgbOrder>(source.data(), out, blocks);
      dest_span = dest_span.subspan(blocks * 16);
      src_span = src_span.subspan(blocks * 48);
      if (dest_span.empty()) {
        return;
      }
    }
  }
#endif
  const size_t width = dest_span.size();
  if (src_Bpp == 3) {
    auto bgr_span = fxcrt::reinterpret_span<const FX_BGR_STRUCT<uint8_t>>(
""",
    ),
    (
        "core/fxge/dib/cfx_scanlinecompositor.cpp",
        """  output.alpha = dest_alpha;
}

template <typename DestPixelStruct>
void CompositeRowBgra2Bgra(pdfium::span<const FX_BGRA_STRUCT<uint8_t>> src_span,
                           pdfium::span<const uint8_t> clip_span,
                           pdfium::span<DestPixelStruct> dest_span,
                           BlendMode blend_type) {
  const bool non_separable_blend = IsNonSeparableBlendMode(blend_type);
  if (clip_span.empty()) {
    if (non_separable_blend) {
""",
        """  output.alpha = dest_alpha;
}

#if defined(__wasm_simd128__) || (defined(__aarch64__) && defined(__ARM_NEON))
#if defined(__wasm_simd128__)
v128_t BlendOpaqueBgraHalf(v128_t src, v128_t dest, v128_t alpha) {
  const v128_t complement = wasm_i16x8_sub(wasm_i16x8_splat(255), alpha);
  const v128_t sum = wasm_i16x8_add(wasm_i16x8_mul(src, alpha),
                                   wasm_i16x8_mul(dest, complement));
  // For sums up to 255 * 255, this is exact integer division by 255.
  const v128_t rounded = wasm_i16x8_add(sum, wasm_i16x8_splat(1));
  return wasm_u16x8_shr(wasm_i16x8_add(rounded, wasm_u16x8_shr(rounded, 8)), 8);
}
#else
uint8x8_t BlendOpaqueBgraHalf(uint8x8_t src, uint8x8_t dest, uint8x8_t alpha) {
  const uint8x8_t complement = vmvn_u8(alpha);
  const uint16x8_t sum = vmlal_u8(vmull_u8(src, alpha), dest, complement);
  const uint16x8_t rounded = vaddq_u16(sum, vdupq_n_u16(1));
  return vshrn_n_u16(vaddq_u16(rounded, vshrq_n_u16(rounded, 8)), 8);
}
#endif

template <typename DestPixelStruct>
[[clang::noinline]] void CompositeNormalBgraRow(
    const FX_BGRA_STRUCT<uint8_t>* src,
    DestPixelStruct* dest,
    size_t count) {
  static_assert(sizeof(FX_BGRA_STRUCT<uint8_t>) == 4);
  static_assert(sizeof(DestPixelStruct) == 4);
  const auto blend_pixel = [](const auto& input, auto& output) {
    const auto src_alpha = input.alpha;
    if (output.alpha == 0) {
      CopyColorComponents(input, output);
      output.alpha = src_alpha;
    } else if (src_alpha != 0) {
      if (output.alpha == 255) {
        AlphaMergeToDest(input, output, src_alpha);
      } else {
        CompositePixelBgra2BgraNoBlend(input, src_alpha, output);
      }
    }
  };
  // The caller checks both spans once. Blocks with any translucent destination
  // keep the scalar straight-alpha behavior, including hidden RGB.
  UNSAFE_TODO({
    while (count >= 4) {
#if defined(__wasm_simd128__)
      const v128_t old = wasm_v128_load(dest);
      const v128_t mask = wasm_i32x4_splat(static_cast<int32_t>(0xff000000u));
      if (wasm_i32x4_all_true(wasm_i32x4_eq(wasm_v128_and(old, mask), mask))) {
        v128_t pixels = wasm_v128_load(src);
        if (wasm_v128_any_true(wasm_v128_and(pixels, mask))) {
          if constexpr (std::is_same_v<DestPixelStruct, FX_RGBA_STRUCT<uint8_t>>) {
            pixels = wasm_i8x16_shuffle(pixels, pixels, 2, 1, 0, 3, 6, 5,
                                        4, 7, 10, 9, 8, 11, 14, 13, 12, 15);
          }
          const v128_t alpha = wasm_i8x16_shuffle(pixels, pixels, 3, 3, 3, 3,
              7, 7, 7, 7, 11, 11, 11, 11, 15, 15, 15, 15);
          const v128_t lo = BlendOpaqueBgraHalf(
              wasm_u16x8_extend_low_u8x16(pixels),
              wasm_u16x8_extend_low_u8x16(old),
              wasm_u16x8_extend_low_u8x16(alpha));
          const v128_t hi = BlendOpaqueBgraHalf(
              wasm_u16x8_extend_high_u8x16(pixels),
              wasm_u16x8_extend_high_u8x16(old),
              wasm_u16x8_extend_high_u8x16(alpha));
          wasm_v128_store(dest, wasm_v128_or(wasm_u8x16_narrow_i16x8(lo, hi), mask));
        }
      } else
#else
      const uint8x16_t old = vld1q_u8(reinterpret_cast<const uint8_t*>(dest));
      const uint32x4_t mask = vdupq_n_u32(0xff000000u);
      if (vminvq_u32(vandq_u32(vreinterpretq_u32_u8(old), mask)) ==
          0xff000000u) {
        uint8x16_t pixels = vld1q_u8(reinterpret_cast<const uint8_t*>(src));
        if (vmaxvq_u32(vandq_u32(vreinterpretq_u32_u8(pixels), mask)) != 0) {
          if constexpr (std::is_same_v<DestPixelStruct, FX_RGBA_STRUCT<uint8_t>>) {
            const uint8x16_t swap_rb = {2, 1, 0, 3, 6, 5, 4, 7,
                                        10, 9, 8, 11, 14, 13, 12, 15};
            pixels = vqtbl1q_u8(pixels, swap_rb);
          }
          const uint8x16_t alpha_index = {3, 3, 3, 3, 7, 7, 7, 7,
                                           11, 11, 11, 11, 15, 15, 15, 15};
          const uint8x16_t alpha = vqtbl1q_u8(pixels, alpha_index);
          const uint8x8_t lo = BlendOpaqueBgraHalf(
              vget_low_u8(pixels), vget_low_u8(old), vget_low_u8(alpha));
          const uint8x8_t hi = BlendOpaqueBgraHalf(
              vget_high_u8(pixels), vget_high_u8(old), vget_high_u8(alpha));
          vst1q_u8(reinterpret_cast<uint8_t*>(dest),
                   vorrq_u8(vcombine_u8(lo, hi), vreinterpretq_u8_u32(mask)));
        }
      } else
#endif
      {
        for (size_t i = 0; i < 4; ++i) {
          blend_pixel(src[i], dest[i]);
        }
      }
      src += 4;
      dest += 4;
      count -= 4;
    }
    for (size_t i = 0; i < count; ++i) {
      blend_pixel(src[i], dest[i]);
    }
  });
}
#endif

template <typename DestPixelStruct>
void CompositeRowBgra2Bgra(pdfium::span<const FX_BGRA_STRUCT<uint8_t>> src_span,
                           pdfium::span<const uint8_t> clip_span,
                           pdfium::span<DestPixelStruct> dest_span,
                           BlendMode blend_type) {
#if defined(__wasm_simd128__) || (defined(__aarch64__) && defined(__ARM_NEON))
  if (clip_span.empty() && blend_type == BlendMode::kNormal &&
      src_span.size() <= dest_span.size()) {
    CompositeNormalBgraRow(src_span.data(), dest_span.data(), src_span.size());
    return;
  }
#endif
  const bool non_separable_blend = IsNonSeparableBlendMode(blend_type);
  if (clip_span.empty()) {
    if (non_separable_blend) {
""",
    ),
    (
        "core/fxge/cfx_renderdevice.cpp",
        """  }
}

void DrawNormalTextHelper(const RetainPtr<CFX_DIBitmap>& bitmap,
                          const CFX_DIBitmap* pGlyph,
                          int nrows,
""",
        """  }
}

[[clang::noinline]] void DrawNormalizedArgbGlyphRow(
    const uint8_t* src,
    uint8_t* dest,
    int count,
    int shift,
    bool has_prefix,
    const FX_BGRA_STRUCT<uint8_t>& bgra) {
  const auto apply = [&bgra](uint8_t* pixel, int src_alpha) {
    UNSAFE_TODO({
      const uint8_t back_alpha = pixel[3];
      if (back_alpha == 0) {
        pixel[0] = bgra.blue;
        pixel[1] = bgra.green;
        pixel[2] = bgra.red;
        pixel[3] = static_cast<uint8_t>(src_alpha);
      } else if (src_alpha != 0) {
        const uint8_t dest_alpha = CalculateDestAlpha(back_alpha, src_alpha);
        const int ratio = back_alpha == 255 ? src_alpha : src_alpha * 255 / dest_alpha;
        pixel[0] = AlphaMerge(pixel[0], bgra.blue, ratio);
        pixel[1] = AlphaMerge(pixel[1], bgra.green, ratio);
        pixel[2] = AlphaMerge(pixel[2], bgra.red, ratio);
        pixel[3] = dest_alpha;
      }
    });
  };
  // The caller validated the row spans and the prefix for shifted glyphs.
  UNSAFE_TODO({
    if (shift != 0) {
      const int value = has_prefix ? AverageRgb(src - shift)
                                   : (src[0] + (shift == 1 ? src[1] : 0)) / 3;
      const int alpha = CalcAlpha(TextGammaAdjust(value), bgra.alpha);
      if (alpha != 0) {
        apply(dest, alpha);
      }
      src += 3 - shift;
      dest += 4;
      --count;
    }
    for (int col = 0; col < count; ++col, src += 3, dest += 4) {
      apply(dest, CalcAlpha(TextGammaAdjust(AverageRgb(src)), bgra.alpha));
    }
  });
}

void DrawNormalTextHelper(const RetainPtr<CFX_DIBitmap>& bitmap,
                          const CFX_DIBitmap* pGlyph,
                          int nrows,
""",
    ),
    (
        "core/fxge/cfx_renderdevice.cpp",
        """      continue;
    }

    const uint8_t* src_scan =
        pGlyph->GetScanline(row)
            .subspan(static_cast<size_t>((start_col - left) * 3))
            .data();
    auto dest_span = bitmap->GetWritableScanline(dest_row).subspan(
        static_cast<size_t>(start_col * bytes_per_pixel));
    if (x_subpixel == 0) {
      for (int col = start_col; col < end_col; ++col) {
        if (normalize) {
""",
        """      continue;
    }

    const auto source = pGlyph->GetScanline(row).subspan(
        static_cast<size_t>((start_col - left) * 3));
    const uint8_t* src_scan = source.data();
    auto dest_span = bitmap->GetWritableScanline(dest_row).subspan(
        static_cast<size_t>(start_col * bytes_per_pixel));
    const int columns = end_col - start_col;
    if (normalize && has_alpha && columns > 0 &&
        static_cast<size_t>(columns) <= source.size() / 3 &&
        static_cast<size_t>(columns) <= dest_span.size() / 4) {
      const int shift = x_subpixel == 0 ? 0 : (x_subpixel == 1 ? 1 : 2);
      DrawNormalizedArgbGlyphRow(src_scan, dest_span.data(), columns, shift,
                                 start_col > left, bgra);
      continue;
    }
    if (x_subpixel == 0) {
      for (int col = start_col; col < end_col; ++col) {
        if (normalize) {
""",
    ),
    (
        "third_party/libjpeg_turbo/src/jidctint.c",
        """#include "jpeglib.h"
#include "jdct.h"               /* Private declarations for DCT subsystem */

#ifdef DCT_ISLOW_SUPPORTED


""",
        """#include "jpeglib.h"
#include "jdct.h"               /* Private declarations for DCT subsystem */

#if defined(__wasm_simd128__) && BITS_IN_JSAMPLE == 8 && \\
    !defined(SHORTxSHORT_32) && !defined(SHORTxLCONST_32)
#include <wasm_simd128.h>
#define JPEG_WASM_ISLOW 1
#endif

#ifdef DCT_ISLOW_SUPPORTED


""",
    ),
    (
        "third_party/libjpeg_turbo/src/jidctint.c",
        """#define DEQUANTIZE(coef, quantval)  (((ISLOW_MULT_TYPE)(coef)) * (quantval))


/*
 * Perform dequantization and inverse DCT on one block of coefficients.
 */
""",
        """#define DEQUANTIZE(coef, quantval)  (((ISLOW_MULT_TYPE)(coef)) * (quantval))


#ifdef JPEG_WASM_ISLOW

static inline __attribute__((always_inline)) v128_t
idct_mul(v128_t a, int constant)
{
  return wasm_i32x4_mul(a, wasm_i32x4_splat(constant));
}

static inline __attribute__((always_inline)) v128_t
idct_descale(v128_t a, int shift)
{
  return wasm_i32x4_shr(wasm_i32x4_add(a, wasm_i32x4_splat(1 << (shift - 1))),
                        shift);
}

/* Four independent 1-D transforms, using the scalar ISLOW constants. */
static inline __attribute__((always_inline)) void
idct_four(const v128_t in[8], v128_t out[8], int shift)
{
  v128_t z1 = idct_mul(wasm_i32x4_add(in[2], in[6]), FIX_0_541196100);
  v128_t t2 = wasm_i32x4_add(z1, idct_mul(in[6], -FIX_1_847759065));
  v128_t t3 = wasm_i32x4_add(z1, idct_mul(in[2], FIX_0_765366865));
  v128_t t0 = wasm_i32x4_shl(wasm_i32x4_add(in[0], in[4]), CONST_BITS);
  v128_t t1 = wasm_i32x4_shl(wasm_i32x4_sub(in[0], in[4]), CONST_BITS);
  const v128_t e0 = wasm_i32x4_add(t0, t3);
  const v128_t e3 = wasm_i32x4_sub(t0, t3);
  const v128_t e1 = wasm_i32x4_add(t1, t2);
  const v128_t e2 = wasm_i32x4_sub(t1, t2);

  z1 = idct_mul(wasm_i32x4_add(in[7], in[1]), -FIX_0_899976223);
  const v128_t z2 = idct_mul(wasm_i32x4_add(in[5], in[3]), -FIX_2_562915447);
  v128_t z3 = wasm_i32x4_add(in[7], in[3]);
  v128_t z4 = wasm_i32x4_add(in[5], in[1]);
  const v128_t z5 = idct_mul(wasm_i32x4_add(z3, z4), FIX_1_175875602);
  z3 = wasm_i32x4_add(idct_mul(z3, -FIX_1_961570560), z5);
  z4 = wasm_i32x4_add(idct_mul(z4, -FIX_0_390180644), z5);
  t0 = wasm_i32x4_add(idct_mul(in[7], FIX_0_298631336), wasm_i32x4_add(z1, z3));
  t1 = wasm_i32x4_add(idct_mul(in[5], FIX_2_053119869), wasm_i32x4_add(z2, z4));
  t2 = wasm_i32x4_add(idct_mul(in[3], FIX_3_072711026), wasm_i32x4_add(z2, z3));
  t3 = wasm_i32x4_add(idct_mul(in[1], FIX_1_501321110), wasm_i32x4_add(z1, z4));

  out[0] = idct_descale(wasm_i32x4_add(e0, t3), shift);
  out[7] = idct_descale(wasm_i32x4_sub(e0, t3), shift);
  out[1] = idct_descale(wasm_i32x4_add(e1, t2), shift);
  out[6] = idct_descale(wasm_i32x4_sub(e1, t2), shift);
  out[2] = idct_descale(wasm_i32x4_add(e2, t1), shift);
  out[5] = idct_descale(wasm_i32x4_sub(e2, t1), shift);
  out[3] = idct_descale(wasm_i32x4_add(e3, t0), shift);
  out[4] = idct_descale(wasm_i32x4_sub(e3, t0), shift);
}

static inline __attribute__((always_inline)) void
idct_transpose4(const v128_t in[4], v128_t out[4])
{
  const v128_t lo0 = wasm_i32x4_shuffle(in[0], in[1], 0, 4, 1, 5);
  const v128_t hi0 = wasm_i32x4_shuffle(in[0], in[1], 2, 6, 3, 7);
  const v128_t lo1 = wasm_i32x4_shuffle(in[2], in[3], 0, 4, 1, 5);
  const v128_t hi1 = wasm_i32x4_shuffle(in[2], in[3], 2, 6, 3, 7);
  out[0] = wasm_i32x4_shuffle(lo0, lo1, 0, 1, 4, 5);
  out[1] = wasm_i32x4_shuffle(lo0, lo1, 2, 3, 6, 7);
  out[2] = wasm_i32x4_shuffle(hi0, hi1, 0, 1, 4, 5);
  out[3] = wasm_i32x4_shuffle(hi0, hi1, 2, 3, 6, 7);
}

/* The post-IDCT range table clamps the signed low ten bits plus 128. */
static inline __attribute__((always_inline)) v128_t
idct_store_range(v128_t row)
{
  return wasm_i32x4_add(wasm_i32x4_shr(wasm_i32x4_shl(row, 22), 22),
                        wasm_i32x4_splat(128));
}

static void
idct_wasm_8x8(JCOEFPTR coef, const ISLOW_MULT_TYPE *quant,
             _JSAMPARRAY output, JDIMENSION output_col)
{
  const v128_t zero = wasm_i32x4_splat(0);
  v128_t non_dc = wasm_v128_and(wasm_v128_load(coef),
                               wasm_i16x8_make(0, -1, -1, -1, -1, -1, -1, -1));
  for (int y = 1; y < 8; ++y)
    non_dc = wasm_v128_or(non_dc, wasm_v128_load(coef + y * 8));

  if (!wasm_v128_any_true(non_dc)) {
    const v128_t dc = wasm_i32x4_splat(DEQUANTIZE(coef[0], quant[0]));
    const v128_t sample = idct_store_range(
        idct_descale(wasm_i32x4_shl(dc, PASS1_BITS), PASS1_BITS + 3));
    const v128_t words = wasm_i16x8_narrow_i32x4(sample, sample);
    const v128_t bytes = wasm_u8x16_narrow_i16x8(words, words);
    for (int y = 0; y < 8; ++y)
      wasm_v128_store64_lane(output[y] + output_col, bytes, 0);
    return;
  }

  v128_t low[8], high[8];
  for (int x = 0; x < 8; x += 4) {
    v128_t cols[8];
    for (int y = 0; y < 8; ++y) {
      const int i = y * 8 + x;
      const v128_t q = sizeof(ISLOW_MULT_TYPE) == 2
                         ? wasm_i32x4_load16x4(quant + i)
                         : wasm_v128_load(quant + i);
      cols[y] = wasm_i32x4_mul(wasm_i32x4_load16x4(coef + i), q);
    }
    idct_four(cols, x == 0 ? low : high, CONST_BITS - PASS1_BITS);
  }
  for (int y = 0; y < 8; y += 4) {
    v128_t rows[8], transformed[8], pixels[8];
    idct_transpose4(low + y, rows);
    idct_transpose4(high + y, rows + 4);
    idct_four(rows, transformed, CONST_BITS + PASS1_BITS + 3);
    idct_transpose4(transformed, pixels);
    idct_transpose4(transformed + 4, pixels + 4);
    for (int row = 0; row < 4; ++row) {
      const v128_t words = wasm_i16x8_narrow_i32x4(
          idct_store_range(pixels[row]), idct_store_range(pixels[row + 4]));
      const v128_t bytes = wasm_u8x16_narrow_i16x8(words, zero);
      wasm_v128_store64_lane(output[y + row] + output_col, bytes, 0);
    }
  }
}

#endif /* JPEG_WASM_ISLOW */

/*
 * Perform dequantization and inverse DCT on one block of coefficients.
 */
""",
    ),
    (
        "third_party/libjpeg_turbo/src/jidctint.c",
        """                 JCOEFPTR coef_block, _JSAMPARRAY output_buf,
                 JDIMENSION output_col)
{
  JLONG tmp0, tmp1, tmp2, tmp3;
  JLONG tmp10, tmp11, tmp12, tmp13;
  JLONG z1, z2, z3, z4, z5;
""",
        """                 JCOEFPTR coef_block, _JSAMPARRAY output_buf,
                 JDIMENSION output_col)
{
#ifdef JPEG_WASM_ISLOW
  (void)cinfo;
  idct_wasm_8x8(coef_block, (ISLOW_MULT_TYPE *)compptr->dct_table,
                output_buf, output_col);
#else
  JLONG tmp0, tmp1, tmp2, tmp3;
  JLONG tmp10, tmp11, tmp12, tmp13;
  JLONG z1, z2, z3, z4, z5;
""",
    ),
    (
        "third_party/libjpeg_turbo/src/jidctint.c",
        """
    wsptr += DCTSIZE;           /* advance pointer to next row */
  }
}

#ifdef IDCT_SCALING_SUPPORTED
""",
        """
    wsptr += DCTSIZE;           /* advance pointer to next row */
  }
#endif /* JPEG_WASM_ISLOW */
}

#ifdef IDCT_SCALING_SUPPORTED
""",
    ),
)
