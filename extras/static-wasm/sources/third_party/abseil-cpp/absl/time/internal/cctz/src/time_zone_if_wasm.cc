#include "absl/time/internal/cctz/src/time_zone_if.h"

#include <memory>
#include <string>

#include "absl/base/config.h"
#include "absl/time/internal/cctz/src/time_zone_fixed.h"

namespace absl {
ABSL_NAMESPACE_BEGIN
namespace time_internal {
namespace cctz {

namespace {

class WasmFixedTimeZone : public TimeZoneIf {
 public:
  explicit WasmFixedTimeZone(seconds offset)
      : offset_(offset), name_(FixedOffsetToName(offset)),
        abbr_(FixedOffsetToAbbr(offset)) {}

  time_zone::absolute_lookup BreakTime(
      const time_point<seconds>& tp) const override {
    const auto shifted = civil_second() + ToUnixSeconds(tp) + offset_.count();
    return {shifted, static_cast<int>(offset_.count()), false, abbr_.c_str()};
  }

  time_zone::civil_lookup MakeTime(const civil_second& cs) const override {
    const time_point<seconds> tp =
        FromUnixSeconds(cs - civil_second() - offset_.count());
    return {time_zone::civil_lookup::UNIQUE, tp, tp, tp};
  }

  bool NextTransition(const time_point<seconds>&,
                      time_zone::civil_transition*) const override {
    return false;
  }

  bool PrevTransition(const time_point<seconds>&,
                      time_zone::civil_transition*) const override {
    return false;
  }

  std::string Version() const override {
    return std::string();
  }

  std::string Description() const override {
    return name_;
  }

 private:
  seconds offset_;
  std::string name_;
  std::string abbr_;
};

}  // namespace

std::unique_ptr<TimeZoneIf> TimeZoneIf::UTC() {
  return std::unique_ptr<TimeZoneIf>(new WasmFixedTimeZone(seconds::zero()));
}

std::unique_ptr<TimeZoneIf> TimeZoneIf::Make(const std::string& name) {
  seconds offset;
  if (FixedOffsetFromName(name, &offset)) {
    return std::unique_ptr<TimeZoneIf>(new WasmFixedTimeZone(offset));
  }
  return nullptr;
}

TimeZoneIf::~TimeZoneIf() {}

}  // namespace cctz
}  // namespace time_internal
ABSL_NAMESPACE_END
}  // namespace absl
