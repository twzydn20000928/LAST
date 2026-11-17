# Primary data preparation

`configs/primary_manifest.json` freezes the ordered400samples from the SIGMark
VBench2 augmented prompt subset:17dimensions with5prompts and4seeds each,
plus3diversity prompts with20seeds each. Eight held-out keys receive50videos
each. Prompt/image assets retain their upstream terms; the repository does not
relicense or bundle the images. See the source repository/revision in the manifest.

There are88dimension/prompt slots but84distinct prompt texts: some texts recur
across dimensions. Keep those slots for the official allocation and use text
deduplication when checking development/test separation.

Download the image archive from its `source.image_archive_url` and extract it
into a reader-selected directory containing `VBench2_aug_img_prompt/`. The URL
is an upstream mutable location, so the per-image SHA256 checks are mandatory.

```bash
python -m last.data --manifest configs/primary_manifest.json --image-root /path/to/images
python -m last.data --manifest configs/primary_manifest.json --image-root /path/to/images \
  --case-index 0 --case-output /private/cases/paper-000.json
```

The first command checks the complete sample allocation and all88image hashes.
It fails on missing or modified images. The second emits a local case file for
the generation interface without embedding server-specific paths in this repository.
Use the same sample ID, seed and conditioning image across methods/backbones.
Sample IDs, not worker order or completion order, determine attack RNG streams.

Development prompts must be disjoint from these84unique texts. The80-video development
manifest is a separate release gate and is not yet published; do not select
parameters by evaluating the primary manifest. The integration smoke case used
the first primary prompt only for interface diagnostics, so its results are not
part of the held-out benchmark or used to tune parameters.
