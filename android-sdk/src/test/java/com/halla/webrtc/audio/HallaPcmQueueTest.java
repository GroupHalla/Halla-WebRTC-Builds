package com.halla.webrtc.audio;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;

import java.nio.ByteBuffer;
import org.junit.Test;

public class HallaPcmQueueTest {
    @Test public void preservesPcmAndPadsSilence() {
        HallaPcmQueue queue = new HallaPcmQueue();
        queue.push(new byte[] {1, 2, 3, 4}, 0, 4);
        ByteBuffer output = ByteBuffer.allocateDirect(8);
        queue.fill(output, 48_000, 1, 2);
        byte[] actual = new byte[8];
        output.get(actual);
        assertArrayEquals(new byte[] {1, 2, 3, 4, 0, 0, 0, 0}, actual);
        assertEquals(0, queue.bufferedBytes());
    }

    @Test public void rejectsPartialSamples() {
        HallaPcmQueue queue = new HallaPcmQueue();
        queue.push(new byte[] {9, 8, 7}, 0, 3);
        assertEquals(2, queue.bufferedBytes());
    }
}
