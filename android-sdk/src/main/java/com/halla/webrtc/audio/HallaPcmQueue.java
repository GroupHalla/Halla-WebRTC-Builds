package com.halla.webrtc.audio;

import java.nio.ByteBuffer;
import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.concurrent.locks.LockSupport;

/** Bounded, paced PCM queue used by the external WebRTC AudioDeviceModule. */
final class HallaPcmQueue {
    private static final int MAX_BUFFERED_BYTES = 48_000 * 2 * 2; // 2 seconds, S16 mono
    private static final long CALLBACK_INTERVAL_NS = 10_000_000L;

    private final ArrayDeque<byte[]> chunks = new ArrayDeque<>();
    private int firstOffset;
    private int bufferedBytes;
    private long nextCallbackNs;
    private boolean released;

    synchronized void push(byte[] pcm, int offset, int length) {
        if (released || pcm == null || offset < 0 || length <= 0
                || offset + length > pcm.length) return;
        // PCM S16 must end on a complete sample.
        length -= length & 1;
        if (length == 0) return;
        chunks.addLast(Arrays.copyOfRange(pcm, offset, offset + length));
        bufferedBytes += length;
        while (bufferedBytes > MAX_BUFFERED_BYTES && !chunks.isEmpty()) {
            byte[] removed = chunks.removeFirst();
            bufferedBytes -= removed.length - firstOffset;
            firstOffset = 0;
        }
    }

    long fill(ByteBuffer destination, int sampleRate, int channels, int audioFormat) {
        pace();
        destination.clear();
        final int wanted = destination.capacity();
        int written = 0;
        synchronized (this) {
            if (!released) {
                while (written < wanted && !chunks.isEmpty()) {
                    byte[] chunk = chunks.peekFirst();
                    int count = Math.min(wanted - written, chunk.length - firstOffset);
                    destination.put(chunk, firstOffset, count);
                    firstOffset += count;
                    written += count;
                    bufferedBytes -= count;
                    if (firstOffset == chunk.length) {
                        chunks.removeFirst();
                        firstOffset = 0;
                    }
                }
            }
        }
        while (written++ < wanted) destination.put((byte) 0);
        destination.rewind();
        return System.nanoTime();
    }

    private void pace() {
        long now = System.nanoTime();
        long deadline;
        synchronized (this) {
            if (nextCallbackNs == 0 || now - nextCallbackNs > CALLBACK_INTERVAL_NS * 5) {
                nextCallbackNs = now;
            }
            deadline = nextCallbackNs;
            nextCallbackNs += CALLBACK_INTERVAL_NS;
        }
        long wait = deadline - now;
        if (wait > 0) LockSupport.parkNanos(wait);
    }

    synchronized int bufferedBytes() { return bufferedBytes; }

    synchronized void release() {
        released = true;
        chunks.clear();
        firstOffset = 0;
        bufferedBytes = 0;
    }
}
