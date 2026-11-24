# Reproduction contract

The supplied main manuscript and companion supplement define settings, not verified experimental outputs. The new campaign does not reuse historical video scores or numerical targets as observations. Existing checkpoints, input assets and fixed upstream source revisions may be reused after hash verification.

## Frozen configuration

`configs/paper_v1.json` is the source of truth. Primary benchmark: 400 samples per method, mode and backbone; 512 information bits for every attack. The eight evaluation keys have 50 samples each. Development prompts and keys must be disjoint. The development manifest is a release gate and is not silently sampled from evaluation prompts.

Changes from historical pilots include 1776 selected coordinates, masked code construction, PCG64/positive-diagonal QR, RMS-normalized features, explicit segmentation and tie breaking, clean CRF18, Wan UniPC at50steps/CFG5/shift5 and Hunyuan shift7. Old pilots are not comparable reproductions.

## Explicit implementation decisions

The supplement leaves byte order and seed-to-integer conversion unspecified. Protocol v1 uses a 32-byte key followed by a four-byte big-endian group index, SHA-256, full digest interpreted big-endian, PCG64 and float64 reduced QR. Published configurations disclose this choice. Cross-platform QR variation must be tested; keys do not imply portable bit-identical BLAS results. Private canonical codebooks are hashed per run.

The 431 shortened BCH prefix bits are zero. The libbch shortened-byte interface processes the512informationbits and80paritybits; leading zero bits contribute no encoder remainder. Decoding verifies corrected parity by re-encoding. Failed decoding returns systematic decisions and remains in accuracy denominators. Successful BCH decoding is not authentication.

Short segments repeat the final frame to reach four content frames, prepend the first frame for causal encoding, and remain ineligible for multi-window chains. This makes the main figure's short-segment fallback explicit. Empty evidence emits512zero decisions with a `no_evidence` status, not a successful detection.

## Required reporting

Record git commit, lockfile, model/checkpoint hashes, prompt/image identifiers, deterministic attack maps, codec/version, information and coded BER, exact-message recovery, BCH success/failure/miscorrection, selected chain/fallback diagnostics, PSNR/SSIM, applicable sample counts, and timing warmup details. Methods receive the same prompt, generation seed and attack map. Blind readers never receive ground-truth message, source video or attack map.

VBench retains official applicability gates. Undefined dimensions are reported as missing. Short-clip geometry proxy scores must never be substituted into the official V-score column. No score is made to match manuscript tables by changing the denominator, selecting seeds, or filling failures.

## Hardware deviation

The author authorized current L40 generation in place of the manuscript A800. Precision and numerical settings stay fixed. Timing uses an idle L40; contention-invalidated runs are rerun. Generation placement/offloading and actual resource consumption are recorded. No paid resources are requested by the runner.

## Release gates

1. Core mathematical/codec unit tests and real VAE interface checks.
2. Clean-install end-to-end embed/export/attack/extract smoke tests on both backbones and modes.
3. Frozen public data manifest and disjoint development manifest.
4. Baseline ports with upstream revision/license and native readout contracts.
5. Primary and supplemental experiment receipts, integrity audits and table-generation scripts.
6. Independent fresh-environment reproduction; documented limitations and unmatched manuscript targets.

This repository is not yet through these gates. Missing implementations and pending results are not represented as complete.

### Frozen manifest bytes

Run receipts bind the exact bytes of the manifest. The development manifest SHA-256 is `8a3d1ec0397456faaff7a9cd98d7e7e1a05a15fc5e9a917745d0ce44affa76f7`, and the primary manifest SHA-256 is `348a52a3d122da7d5895e99246b2cc1bd344133b770f32af3363b73249447b58`. The repository preserves the original LF development file and CRLF primary file through Git checkout attributes. Transfer the files byte-for-byte when staging them on a compute server. To check an existing staging directory, run `sha256sum configs/development_manifest.json configs/primary_manifest.json` there. A JSON reserialization or line-ending conversion can preserve the prompts and seeds while changing the run receipt digest.
