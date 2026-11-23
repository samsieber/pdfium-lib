#include "absl/debugging/internal/examine_stack.h"

#include "absl/base/attributes.h"

namespace absl {
ABSL_NAMESPACE_BEGIN
namespace debugging_internal {

namespace {
ABSL_CONST_INIT SymbolizeUrlEmitter debug_stack_trace_hook = nullptr;
}

void RegisterDebugStackTraceHook(SymbolizeUrlEmitter hook) {
  debug_stack_trace_hook = hook;
}

SymbolizeUrlEmitter GetDebugStackTraceHook() {
  return debug_stack_trace_hook;
}

void* GetProgramCounter(void* const vuc) {
  (void)vuc;
  return nullptr;
}

void DumpPCAndFrameSizesAndStackTrace(void* const pc,
                                      void* const stack[],
                                      int frame_sizes[],
                                      int depth,
                                      int min_dropped_frames,
                                      bool symbolize_stacktrace,
                                      OutputWriter* writer,
                                      void* writer_arg) {
  (void)pc;
  (void)stack;
  (void)frame_sizes;
  (void)depth;
  (void)min_dropped_frames;
  (void)symbolize_stacktrace;
  (void)writer;
  (void)writer_arg;
}

void DumpStackTrace(int min_dropped_frames,
                    int max_num_frames,
                    bool symbolize_stacktrace,
                    OutputWriter* writer,
                    void* writer_arg) {
  (void)min_dropped_frames;
  (void)max_num_frames;
  (void)symbolize_stacktrace;
  (void)writer;
  (void)writer_arg;
}

}  // namespace debugging_internal
ABSL_NAMESPACE_END
}  // namespace absl
