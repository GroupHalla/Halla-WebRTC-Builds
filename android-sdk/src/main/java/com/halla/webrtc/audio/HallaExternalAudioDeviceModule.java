package com.halla.webrtc.audio;

import android.content.Context;
import android.media.AudioFormat;

import org.webrtc.audio.AudioDeviceModule;
import org.webrtc.audio.JavaAudioDeviceModule;

import java.util.concurrent.atomic.AtomicBoolean;

/**
 * WebRTC AudioDeviceModule fed by external PCM instead of the microphone.
 *
 * <p>Input format is signed PCM 16-bit little-endian, mono, 48 kHz. Call
 * {@link #pushPcm16Mono48k(byte[], int, int)} from an AudioPlaybackCapture
 * worker. The module supplies paced 10 ms buffers to libwebrtc through the
 * public AudioBufferCallback API.</p>
 */
public final class HallaExternalAudioDeviceModule implements AutoCloseable {
    public static final int SAMPLE_RATE = 48_000;
    public static final int CHANNELS = 1;
    public static final int BYTES_PER_10_MS = 480 * 2;

    private final HallaPcmQueue queue = new HallaPcmQueue();
    private final JavaAudioDeviceModule module;
    private final AtomicBoolean released = new AtomicBoolean(false);

    private HallaExternalAudioDeviceModule(Context context) {
        module = JavaAudioDeviceModule.builder(context.getApplicationContext())
            .setInputSampleRate(SAMPLE_RATE)
            .setAudioFormat(AudioFormat.ENCODING_PCM_16BIT)
            .setUseStereoInput(false)
            .setUseHardwareAcousticEchoCanceler(false)
            .setUseHardwareNoiseSuppressor(false)
            .setAudioBufferCallback((buffer, audioFormat, channelCount, sampleRate,
                                     bytesRead, captureTimeNs) ->
                queue.fill(buffer, sampleRate, channelCount, audioFormat))
            .createAudioDeviceModule();
        // WebRtcAudioRecord still allocates/caches its native direct buffer and
        // invokes AudioBufferCallback, but does not open a second microphone.
        module.setAudioRecordEnabled(false);
    }

    public static HallaExternalAudioDeviceModule create(Context context) {
        if (context == null) throw new IllegalArgumentException("context == null");
        return new HallaExternalAudioDeviceModule(context);
    }

    /** Pass this module to PeerConnectionFactory.Builder.setAudioDeviceModule(). */
    public AudioDeviceModule audioDeviceModule() {
        if (released.get()) throw new IllegalStateException("module already released");
        return module;
    }

    public void pushPcm16Mono48k(byte[] pcm) {
        if (pcm != null) pushPcm16Mono48k(pcm, 0, pcm.length);
    }

    public void pushPcm16Mono48k(byte[] pcm, int offset, int length) {
        if (!released.get()) queue.push(pcm, offset, length);
    }

    public int bufferedMilliseconds() {
        return (queue.bufferedBytes() * 1000) / (SAMPLE_RATE * CHANNELS * 2);
    }

    /** Release after PeerConnectionFactory.dispose(). */
    @Override public void close() {
        if (!released.compareAndSet(false, true)) return;
        queue.release();
        module.release();
    }
}
