// Smoke de CONSUMIDOR GCC: inclui todos os headers públicos do SDK que o
// HallaWebRtcSession.cpp (o TU mais pesado do app) usa, compilados com o
// mesmo g++/libstdc++ do build do app. O factory smoke abaixo valida link e
// runtime; este valida que NENHUM header do SDK rejeita o GCC antes do
// release (ex.: -Wchanges-meaning, que o clang do build do SDK aceita).

#include <cstddef>
using nullptr_t = std::nullptr_t; // headers do webrtc usam nullptr_t global

#include "api/create_peerconnection_factory.h"
#include "api/audio_codecs/builtin_audio_decoder_factory.h"
#include "api/audio_codecs/builtin_audio_encoder_factory.h"
#include "api/jsep.h"
#include "api/make_ref_counted.h"
#include "api/media_stream_interface.h"
#include "api/rtp_receiver_interface.h"
#include "api/rtp_transceiver_interface.h"
#include "api/audio/audio_device_defines.h"
#include "modules/audio_device/include/audio_device_default.h"
#include "api/video/i420_buffer.h"
#include "api/video/video_frame.h"
#include "api/video_codecs/video_decoder_factory.h"
#include "api/video_codecs/video_encoder_factory.h"
#include "modules/video_coding/codecs/vp8/include/vp8.h"
#include "libyuv/convert.h"
#include "libyuv/convert_from.h"
#include "libyuv/scale.h"
#include "rtc_base/ref_counted_object.h"
#include "rtc_base/ssl_adapter.h"
#include "rtc_base/thread.h"

int main() {
    return 0;
}
