#include "absl/random/internal/seed_material.h"

#include <cassert>
#include <cstdint>

#include "absl/base/config.h"
#include "absl/types/optional.h"
#include "absl/types/span.h"

namespace absl {
ABSL_NAMESPACE_BEGIN
namespace random_internal {

bool ReadSeedMaterialFromOSEntropy(absl::Span<uint32_t> values) {
  assert(values.data() != nullptr);
  if (values.data() == nullptr) {
    return false;
  }
  return values.empty();
}

void MixIntoSeedMaterial(absl::Span<const uint32_t> sequence,
                         absl::Span<uint32_t> seed_material) {
  constexpr uint32_t kInitVal = 0x43b0d7e5;
  constexpr uint32_t kHashMul = 0x931e8875;
  constexpr uint32_t kMixMulL = 0xca01f9dd;
  constexpr uint32_t kMixMulR = 0x4973f715;
  constexpr uint32_t kShiftSize = sizeof(uint32_t) * 8 / 2;

  uint32_t hash_const = kInitVal;
  auto hash = [&](uint32_t value) {
    value ^= hash_const;
    hash_const *= kHashMul;
    value *= hash_const;
    value ^= value >> kShiftSize;
    return value;
  };

  auto mix = [&](uint32_t x, uint32_t y) {
    uint32_t result = kMixMulL * x - kMixMulR * y;
    result ^= result >> kShiftSize;
    return result;
  };

  for (const auto& seq_val : sequence) {
    for (auto& elem : seed_material) {
      elem = mix(elem, hash(seq_val));
    }
  }
}

absl::optional<uint32_t> GetSaltMaterial() {
  return absl::nullopt;
}

}  // namespace random_internal
ABSL_NAMESPACE_END
}  // namespace absl
