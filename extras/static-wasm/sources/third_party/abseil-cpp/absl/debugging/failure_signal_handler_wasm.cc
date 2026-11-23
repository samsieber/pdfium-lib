#include "absl/debugging/failure_signal_handler.h"

namespace absl {
ABSL_NAMESPACE_BEGIN

void InstallFailureSignalHandler(const FailureSignalHandlerOptions& options) {
  (void)options;
}

namespace debugging_internal {

const char* FailureSignalToString(int signo) {
  (void)signo;
  return "";
}

}  // namespace debugging_internal

ABSL_NAMESPACE_END
}  // namespace absl
