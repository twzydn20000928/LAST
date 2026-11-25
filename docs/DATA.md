# Primary data preparation

`configs/primary_manifest.json` freezes the ordered400samples from the SIGMark
VBench2 augmented prompt subset:17dimensions with5prompts and4seeds each,
plus3diversity prompts with20seeds each. Eight held-out keys receive50videos
each. Prompt/image assets retain their upstream terms; the repository does not
relicense or bundle the images. See the source repository/revision in the manifest.

There are88dimension/prompt slots but84distinct prompt texts: some texts recur
across dimensions. Keep those slots for the official allocation and use text
deduplication when checking development/test separation.

To trace each primary sample to its upstream prompt text, fetch the pinned
metadata and replay the selection from the repository root:

```bash
python -m last.upstream --manifest configs/quality_metadata_manifest.json \
  --directory /path/to/sigmark-metadata --download
python tools/check_primary_prompts.py \
  --prompt-dir /path/to/sigmark-metadata/prompt_set/VBench2_aug_prompt
```

The checker verifies the Git blob ID of each of the 18 upstream prompt files.
Within each file the stride is the line count divided by the required prompt
count, rounded down. Selection starts at line zero. For example,
`Camera_Motion` uses lines 0, 21, 42, 63 and 84, with four seeds per prompt.
The output lists the source line and first sample index for every prompt slot,
after checking the text, dimension and repetition against all 400 manifest rows.

The I2V runs used the upstream image archive identified in the manifest. The
stored ZIP is 35,030,832 bytes and has 101 file entries. The experiment uses
88 distinct paths from it. The URL points to a mutable branch; check the ZIP
and each selected image. From the repository root in Bash on Linux:

```bash
set -e
assets=/path/to/images
mkdir -p "$assets"
url=$(python -c 'import json; print(json.load(open("configs/primary_manifest.json"))["source"]["image_archive_url"])')
curl --fail --location --retry 3 --output "$assets/images.zip" "$url"
printf '%s  %s\n' 4fb18a28837f59b14d73c4bfeea0b459729c7dd8f7fcb2264fe1c1a948268dd7 "$assets/images.zip" | sha256sum --check -
python - "$assets" <<'PY'
import json, sys, zipfile
from pathlib import Path

root = Path(sys.argv[1])
manifest = json.loads(Path("configs/primary_manifest.json").read_bytes())
with zipfile.ZipFile(root / "images.zip") as archive:
    names = archive.namelist()
    for name in sorted({row["image"] for row in manifest["samples"]}):
        if names.count(name) != 1:
            raise ValueError(f"Missing or duplicated archive entry: {name}")
        archive.extract(name, root)
PY
python -m last.data --manifest configs/primary_manifest.json --image-root "$assets"
```

On the archived inputs the last command reports 400 samples, 18 dimensions,
88 prompt slots, 84 distinct prompt texts and 88 verified images. Each I2V
replicate uses the image that its row names. Use a Linux filesystem for the
extraction commands. In a Windows temporary directory the ZIP digest matched
the archive on the experiment server, but extraction failed on a prompt-based
filename. The original filenames are part of the manifest paths. To export a
local generation case:

```bash
python -m last.data --manifest configs/primary_manifest.json --image-root /path/to/images \
  --case-index 0 --case-output /private/cases/paper-000.json
```

The case command checks the sample allocation and all 88 image hashes, then emits a local case file for
the generation interface without embedding server-specific paths in this repository.
Use the same sample ID, seed and conditioning image across methods/backbones.
Sample IDs, not worker order or completion order, determine attack RNG streams.

Create a private benchmark state once (the command refuses to overwrite a directory):

```bash
python -m last.prepare --manifest configs/primary_manifest.json --output /private/primary-state
```

This samples eight independent256bit keys and400independent512bit messages using
the operating system RNG. Keep this directory for all methods and both backbones.
Pass `--key /private/primary-state/keys/00.key` and
`--message /private/primary-state/messages/paper-000.bin` to `last.smoke` for
sample0; use each sample's manifest key slot. Keys and messages are not public
seeds. Re-running a study with fresh keys estimates the same protocol but is not
expected to reproduce every bit error exactly. To run generation, MP4 attacks,
extraction and paired fidelity on these same sample IDs, pass the manifest and
private state to the [primary campaign](CAMPAIGN.md). Use the resulting run root
as the input to [quality evaluation](QUALITY.md).

Development prompts must be disjoint from these84unique texts. The80-video development
manifest is frozen in `configs/development_manifest.json`; do not select
parameters by evaluating the primary manifest. The integration smoke case used
the first primary prompt only for interface diagnostics, so its results are not
part of the held-out benchmark or used to tune parameters.

## Development reproduction

The development split contains20distinct prompts with four seeds each, eight
new keys, and fixed sweep IDs dev-000/dev-004/dev-008. Its metadata-only selection
excludes normalized primary prompt text; this is not semantic independence.
To regenerate the manifest from verified official prompt assets:

```bash
python -m last.development --metadata-root /path/to/SIGMark-quality-metadata \
  --output /private/development-manifest.json
python -m last.prepare --manifest configs/development_manifest.json \
  --primary-manifest configs/primary_manifest.json --exclude-state /private/primary-state \
  --output /private/development-state
```

For I2V, generate one unmarked Hunyuan T2V conditioning video per prompt using
the first of its four seeds, then take frame0 after CRF18 MP4 rereading. This
is a disclosed reconstruction choice because the manuscript does not supply
development images. Do not screen images by quality or watermark outcomes.

```bash
python -m last.conditioning --prompt-index 0 --model-dir /path/to/hunyuan-t2v \
  --output /private/development-conditioning/prompt-00 --memory-gib 8
python -m last.development_case --sample-id dev-000 --mode i2v \
  --conditioning /private/development-conditioning/prompt-00 \
  --output /private/cases/dev-000.json
```

Repeat conditioning for indices0..19. Samples0..3 share prompt00's image,
samples4..7 share prompt01's image, and so on, retaining their own manifest seeds.
The case exporter verifies completed conditioning, manifest and image hashes,
prompt identity and first-seed provenance. For T2V, use `--mode t2v` without
`--conditioning`. Then pass the exported case and that sample's development
key/message to `last.smoke`; keep these fixed across strengths, writers and
backbones. The public commands are available; the full development experiment
has not yet completed.
