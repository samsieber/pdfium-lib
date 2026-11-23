#include "absl/time/internal/cctz/include/cctz/time_zone.h"

#include <string>

#include "absl/base/config.h"
#include "absl/time/internal/cctz/src/time_zone_fixed.h"
#include "absl/time/internal/cctz/src/time_zone_impl.h"

namespace absl {
ABSL_NAMESPACE_BEGIN
namespace time_internal {
namespace cctz {

std::string time_zone::name() const { return effective_impl().Name(); }

time_zone::absolute_lookup time_zone::lookup(
    const time_point<seconds>& tp) const {
  return effective_impl().BreakTime(tp);
}

time_zone::civil_lookup time_zone::lookup(const civil_second& cs) const {
  return effective_impl().MakeTime(cs);
}

bool time_zone::next_transition(const time_point<seconds>& tp,
                                civil_transition* trans) const {
  return effective_impl().NextTransition(tp, trans);
}

bool time_zone::prev_transition(const time_point<seconds>& tp,
                                civil_transition* trans) const {
  return effective_impl().PrevTransition(tp, trans);
}

std::string time_zone::version() const { return effective_impl().Version(); }

std::string time_zone::description() const {
  return effective_impl().Description();
}

const time_zone::Impl& time_zone::effective_impl() const {
  if (impl_ == nullptr) {
    return *time_zone::Impl::UTC().impl_;
  }
  return *impl_;
}

bool load_time_zone(const std::string& name, time_zone* tz) {
  return time_zone::Impl::LoadTimeZone(name, tz);
}

time_zone utc_time_zone() {
  return time_zone::Impl::UTC();
}

time_zone fixed_time_zone(const seconds& offset) {
  time_zone tz;
  load_time_zone(FixedOffsetToName(offset), &tz);
  return tz;
}

time_zone local_time_zone() {
  return utc_time_zone();
}

}  // namespace cctz
}  // namespace time_internal
ABSL_NAMESPACE_END
}  // namespace absl
