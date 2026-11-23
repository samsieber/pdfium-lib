// Copyright 2026 The PDFium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "core/fxcrt/fileaccess_iface.h"

#include <memory>

namespace {

class CFX_FileAccess_Wasm final : public FileAccessIface {
 public:
  bool Open(const ByteString&) override { return false; }

  void Close() override {}
  FX_FILESIZE GetSize() const override { return 0; }
  FX_FILESIZE GetPosition() const override { return static_cast<FX_FILESIZE>(-1); }

  FX_FILESIZE SetPosition(FX_FILESIZE pos) override {
    (void)pos;
    return static_cast<FX_FILESIZE>(-1);
  }

  size_t Read(pdfium::span<uint8_t> buffer) override {
    (void)buffer;
    return 0;
  }

  bool Write(pdfium::span<const uint8_t>) override { return false; }

  size_t ReadPos(pdfium::span<uint8_t> buffer, FX_FILESIZE pos) override {
    (void)buffer;
    (void)pos;
    return 0;
  }

  bool Flush() override { return false; }

  bool Truncate(FX_FILESIZE szFile) override {
    (void)szFile;
    return false;
  }
};

}  // namespace

// static
std::unique_ptr<FileAccessIface> FileAccessIface::Create() {
  return std::make_unique<CFX_FileAccess_Wasm>();
}
