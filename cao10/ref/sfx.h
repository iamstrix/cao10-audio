#ifndef SFX_H
#define SFX_H
#include <stdint.h>
typedef struct {
    uint32_t waveform;
    float base_freq, slide, min_freq, vib_depth, vib_rate;
    float attack, sustain, decay, volume;
    uint32_t seed;
} SfxParams;
uint32_t sfx_sample_count(const SfxParams *p);
uint32_t sfx_generate(const SfxParams *p, int16_t *out, uint32_t capacity);
/* Input and output buffers must not overlap. Returns bytes, or zero on error. */
uint32_t sfx_write_wav(const int16_t *samples, uint32_t count, void *out, uint32_t capacity);
#endif
