// Copyright 2026 The PDFium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include <memory>

#include "core/fxcrt/bytestring.h"
#include "core/fxcrt/fx_codepage_forward.h"
#include "core/fxge/cfx_gemodule.h"
#include "core/fxge/systemfontinfo_iface.h"

namespace {

class CFX_WasmFontInfo final : public SystemFontInfoIface {
 public:
  void EnumFontList(CFX_FontMapper* pMapper) override { (void)pMapper; }

  void* MapFont(CFX_FontMapper*,
                int weight,
                bool bItalic,
                FX_Charset charset,
                int pitch_family,
                const ByteString& face) override {
    (void)weight;
    (void)bItalic;
    (void)charset;
    (void)pitch_family;
    (void)face;
    return nullptr;
  }

  void* GetFont(const ByteString& face) override {
    (void)face;
    return nullptr;
  }

  size_t GetFontData(void* hFont,
                     uint32_t table,
                     pdfium::span<uint8_t> buffer) override {
    (void)hFont;
    (void)table;
    (void)buffer;
    return 0;
  }

  bool GetFaceName(void* hFont, ByteString* name) override {
    (void)hFont;
    (void)name;
    return false;
  }

  bool GetFontCharset(void* hFont, FX_Charset* charset) override {
    (void)hFont;
    (void)charset;
    return false;
  }

  void DeleteFont(void* hFont) override { (void)hFont; }
};

class CWasmPlatform final : public CFX_GEModule::PlatformIface {
 public:
  void Init() override {}
  void Terminate() override {}

  std::unique_ptr<SystemFontInfoIface> CreateDefaultSystemFontInfo() override {
    return std::make_unique<CFX_WasmFontInfo>();
  }
};

}  // namespace

// static
std::unique_ptr<CFX_GEModule::PlatformIface>
CFX_GEModule::PlatformIface::Create() {
  return std::make_unique<CWasmPlatform>();
}
