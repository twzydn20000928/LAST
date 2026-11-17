# Third-party components

This license covers the new LAST source only, not third-party checkpoints, datasets or dependencies. Obtain models/data from their original providers and comply with their licenses. We do not redistribute model weights or generated FLUX condition images.

- HunyuanVideo / HunyuanVideo-I2V: Tencent model releases and community Diffusers conversion.
- Wan2.2: Wan-AI A14B official Diffusers checkpoints.
- SIGMark: dataset/prompt protocol and comparison baseline, https://github.com/JeremyZhao1998/SIGMark-release . Its original source is kept separate when running comparisons.
- VBench2: official quality evaluation, https://github.com/Vchitect/VBench . Applicability gates and valid denominators must be preserved.
- Diffusers / Transformers / Accelerate: model execution and CPU offloading.
- NumPy / PyTorch / SciPy: numerical operations.
- bchlib/libbch: error-correcting code implementation; see their own license before redistribution.
- OpenCV / FFmpeg: optical flow, video decoding and encoding.

Baseline ports and any redistributed third-party source must include their exact upstream revision and license before release. Initial tests use synthetic data, not secret evaluation materials.
