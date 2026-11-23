#include "absl/base/internal/sysinfo.h"

#include "absl/base/config.h"

namespace absl {
ABSL_NAMESPACE_BEGIN
namespace base_internal {

int NumCPUs() {
  return 1;
}

double NominalCPUFrequency() {
  return 1.0;
}

pid_t GetTID() {
  return 1;
}

pid_t GetCachedTID() {
  return GetTID();
}

}  // namespace base_internal
ABSL_NAMESPACE_END
}  // namespace absl
