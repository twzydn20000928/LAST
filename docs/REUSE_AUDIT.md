# Historical resource and result reuse

The author permits reusing previous experiments. Reuse must preserve provenance;
an older result does not become a new-protocol observation by relabeling it.

| Resource | Decision | Required check |
|---|---|---|
| Downloaded model weights | Reuse | Repository revision, configuration and file hashes |
| Official prompts and conditioning images | Reuse | Stable sample IDs, source and image hashes |
| Prior implementation and environments | Adapt | Preserve upstream source; test against frozen numerical protocol |
| Old generated videos | Conditional | Same model, steps, scheduler, guidance, precision, seed, payload, carrier construction and codec |
| Prior bit accuracy or quality scores | Conditional | Same inputs, attacks, readout, score implementation and complete raw receipts |
| Development or hypothetical target tables | Exclude from benchmark | Never counted as held-out measurements |

No historical full benchmark result has yet passed this audit. Old pilot settings
include different frequency dimensions, codecs and Wan schedulers; these cannot
silently replace the paper protocol. The two fresh Hunyuan integration videos can
be reused for interface and attack diagnostics, but are not the frozen held-out
benchmark: their randomly generated keys do not implement its eight-key allocation.

## Attack implementation decisions

All attacks start from the exported CRF18 marked MP4, and altered outputs are
exported and re-read. Compression uses CRF28; other edits use CRF18. Pixel noise
is Gaussian with sigma .05 in [0,1], clipped then rounded to RGB8. Insertion noise
frames use independent uniform RGB8 pixels; the manuscript does not state that
distribution, so this is an explicit implementation choice. Temporal attack maps
and pixel RNG depend on video ID, attack and seed, never on watermark method.
Clean reads the original marked MP4 without a second encode. Attack maps are
recorded only by the evaluator and never passed to the blind reader.

## Development-input audit (2026-11-18)

The conditioning archive contains13image files not named in the primary manifest.
Twelve have prompts already used by the primary test set; the remaining checkpoint
file duplicates a primary image. None qualifies as a disjoint-prompt development
input. Different image bytes alone do not establish an independent prompt split.

The historical30null-video pilot was also audited: all30MP4hashes match its frozen
protocol, and its prompts do not overlap the primary manifest. However, there are
only **four unique prompts**. These are candidate source inputs, not30independent
scenes or new watermark measurements. Reusing their conditioning frames would
require public input artifacts, source hashes, an explicit reconstruction rule,
new disjoint keys and fresh paper-configured generation. No such development
benchmark is currently marked complete.

The new `configs/development_manifest.json` freezes 80 development cases from
verified SIGMark augmented prompt files: 20 distinct prompts, four seeds each,
eight new key slots with ten cases each. `last.development` selects prompts by
SHA256 ranking and dimension round robin, without reading outcomes; it rejects
casefold/whitespace-normalized primary prompt matches. This is exact-text
disjointness, not proof of semantic independence. The paper specifies the size
and separation but not these individual examples; this selection is an explicit
reconstruction choice. The three margin-sweep IDs use three different prompts.

```bash
python -m last.development --metadata-root /path/to/SIGMark-quality-metadata \
  --output /private/development_manifest.json
```

The published selection does not yet contain conditioning images. I2V input
acquisition remains a release requirement; primary test images/keys must not be
substituted. No development generation or parameter tuning is implied by
publishing this manifest.

Create private development keys/messages once, checking against your primary
state without printing or publishing either set of keys:

```bash
python -m last.prepare --manifest configs/development_manifest.json \
  --primary-manifest configs/primary_manifest.json \
  --exclude-state /private/primary-state --output /private/development-state
```

The command validates prompt and seed separation, primary state identity, and
eight distinct 32-byte primary keys. It creates eight new disjoint keys and 80
messages. Both directories must remain private and persistent across paired
methods. An existing output is refused; do not regenerate private state after
observing outcomes. Development state creation is tested and performed in the
reproduction environment; conditioning inputs and actual development runs are
still pending.

### Development conditioning reconstruction

The manuscript does not supply the development conditioning images. We use a
declared reconstruction: for each of the 20 development prompts, generate one
unmarked Hunyuan T2V reference using that prompt's first fixed seed and the
paper's 65-frame/512-square/50-step settings. Export CRF18 MP4, reread it, and
take frame zero as PNG. Reuse that image for all four I2V seeds of the prompt.
No watermark key/message or quality score is used to choose the image; do not
retry seeds to find a more favorable picture. This is not the original authors'
unreleased image set and does not alter primary test conditioning images.

```bash
python -m last.conditioning --prompt-index 0 \
  --model-dir /path/to/pinned-hunyuan-t2v \
  --output /private/development-conditioning/prompt-00 --memory-gib 8
```

Run indices 0 through 19 once. Receipts record manifest/source hashes, settings,
the actual video hash and selected PNG hash. Keep failed attempts and logs.
Availability of this entry point does not imply that all images have finished;
the complete image mapping must be verified before the I2V development campaign.
