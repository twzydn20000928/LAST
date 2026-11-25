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

The archival change register identifies the expansion from 20 to 400 videos
per method and mode as a planned protocol. For Table 4 it records that the
three-example means were carried forward when the planned sample size changed
to 30. Table 3's twenty rendered timing cells match the archived scenario
source. In particular the register records a VideoMark overhead change from
−1.97511043 s to +1.98 s. Neither figure supplies the paired timings needed
for the new Table 3. Use the signed difference measured for each pair. The
archived 400-video error histograms are explicitly labeled synthetic and are
excluded from error distributions, confidence intervals and exact-message totals.

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

The development I2V runs use 20 generated conditioning images, one per prompt.
For each prompt, use the first of its four development seeds to generate an
unmarked Hunyuan T2V clip, encode it at CRF18, and take its first decoded frame.
All four seeds then use that frame as their I2V input. The audit records the
source MP4 and image hashes and the assignment of all 80 development cases.
See the [generation commands](DATA.md#development-reproduction) and the
[conditioning audit](../results/development_conditioning_20.json).

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

## Legacy primary-reader receipt migration

The initial Hunyuan I2V LAST campaign used public commit
`c1f2f694cfb777053795e7bbf186b5776c9fecd0`. Its non-clean attack receipts did
not record the hash of the MP4 supplied to extraction. A later hash of a file
cannot retroactively prove what the old reader consumed. Original receipts
remain unchanged; independent `last.reextract` runs provide separate evidence.

To stop accumulating this gap without changing the legacy scientific code,
`tools/patches/legacy-c1f2-received-sha.patch` adds only two statements to that
commit's `src/last/evaluate.py`: hash the received MP4 before loading it and
check it again after extraction. Removing those additions restores the original
file; every other Python source hash was checked unchanged. The patch SHA-256
is `8488952018a07bebba3814b97054220168c32afe52c8e4e49cb8c5ea66c3b45e`.

For an explicitly separate legacy reproduction, from the current repository:

```bash
git worktree add --detach ../LAST-legacy-receipts c1f2f694cfb777053795e7bbf186b5776c9fecd0
git -C ../LAST-legacy-receipts apply ../LAST/tools/patches/legacy-c1f2-received-sha.patch
```

The example assumes the current checkout directory is named `LAST`; adjust
that patch path otherwise. Record both the base commit and patch hash. This
is a transparent patched legacy execution, not an unmodified checkout or a
claim that all later main-branch code is numerically identical.

At the migration checkpoint, eight primary cases were complete and 392 remained
(including two active generation subprocesses). Only owned scheduler parents
were replaced; those GPU subprocesses continued naturally. The full 400-case
manifest is unchanged. The remaining plan and the retained completed-case list
jointly cover all400 cases. The running campaign, independent historical audits
and final table aggregation still require completion; this record does not
certify all results or resolve cross-environment pixel differences.

## Reusing completed attack receipts

The current LAST/LFG and native-baseline evaluators rehash the received MP4
before skipping a completed condition. They reject a missing file, a changed
file, or a receipt without a received-video fingerprint. They also recheck the
received file after fresh extraction; native extraction checks its private state
has not changed. The LAST/LFG evaluator verifies the marked generation video
against its generation receipt. These checks do not change decoding or attacks.

Do not insert a current hash into a historical receipt to make it pass: it would
not establish what was extracted originally. Retain the historical observation
and perform an independently recorded re-extraction where needed. Frozen
running campaigns retain their original source versions; this stricter public
resume behavior applies to newly prepared source versions and plans.
# Figure 3 frame provenance

The submitted Figure 3 matches the archived qualitative grid: all 24 decoded
512 × 512 RGB image buffers have identical SHA256 fingerprints across the two
PDFs. The archive's frame manifest identifies Hunyuan I2V development cases
00 and 04, frames 4 and 16 (zero-based), from the early 16-information-bit
study. Its LAST column used the earlier SBIR reader/adapter configuration.
The archived preparation script assigns seeds 2026111300 and 2026111304.
Each conditioning image comes from frame zero of its earlier unmarked CRF18
video, resized to 512 × 512 using OpenCV area interpolation. Both historical
21-frame runs use the prompt “A natural video of the scene in the input image,
with gentle motion.” A new 65-frame run using those inputs would be a paired
illustrative rerun on development content.
These identifiers belong to the historical development suite. They are
distinct from the frozen primary sample IDs. The grid documents the original
illustration; it provides no measured 512-bit fidelity or recovery result.
For a new 512-bit visual comparison, use the paired generation outputs and
record their case IDs and MP4 fingerprints with the figure.
