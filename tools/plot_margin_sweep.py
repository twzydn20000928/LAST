"""Render Figure 4 from fifteen completed development runs."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import mean


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def collect(index, config):
    manifest_path = config / "development_manifest.json"
    manifest = read(manifest_path)
    ids = manifest["margin_sweep_ids"]
    samples = {s["id"]: s for s in manifest["samples"]}
    strengths = read(config / "paper_v1.json")["margin_sweep"]["mu"]
    attacks = ("noise", "compression", "blur", "drop", "insert", "clip")
    rows = {}
    paired = {}
    pipeline = None
    for entry in read(index):
        name = entry["video_id"]
        folder = index.parent / entry["run"]
        g = read(folder / "receipt.json")
        q = read(folder / "quality.json")
        mu = g["mu"]
        require(name in ids and mu in strengths and (name, mu) not in rows, "Unexpected or duplicate sweep cell")
        require(g["status"] == "completed" and g["method"] == "last" and not g["fixed_target"]
                and not g["uniform_profile"], f"{folder}: incorrect writer")
        case = read(folder / "case.json")
        require(g["case_sha256"] == digest(folder / "case.json") and case["video_id"] == name
                and case["development_manifest_sha256"] == digest(manifest_path)
                and case["seed"] == samples[name]["seed"] == g["seed"]
                and case["prompt"] == samples[name]["prompt"], f"{folder}: case mismatch")
        identity = (g["family"], g["mode"], g["source_sha256"], g["settings"], g["model_directory"])
        if pipeline is None:
            pipeline = identity
        require(identity == pipeline, "Mixed generation configurations")
        reference = digest(folder / "reference.mp4")
        marked = digest(folder / "marked.mp4")
        require(reference == q["reference_sha256"] and marked == q["marked_sha256"] == g["marked_sha256"],
                f"{folder}: MP4 mismatch")
        pairing = [reference, g["case_sha256"], digest(folder / "secret.key"), digest(folder / "message.npy")]
        counts = {}
        for attack in ("clean", *attacks):
            stem = folder / "attacks" / attack
            r = read(stem.with_suffix(".json"))
            received = marked if attack == "clean" else digest(stem.with_suffix(".mp4"))
            require(r["status"] == "completed" and r["video_id"] == name and r["method"] == "last"
                    and r["condition"] == attack and r["source_sha256"] == marked
                    and r["received_sha256"] == received
                    and r["map_seed"] == 0 and r["total_bits"] == 512
                    and type(r["correct_bits"]) is int and 0 <= r["correct_bits"] <= 512,
                    f"{stem}: attack receipt mismatch")
            pairing.append(r["attack_map"])
            counts[attack] = r["correct_bits"]
        require(paired.setdefault(name, pairing) == pairing, f"{folder}: strengths are unpaired")
        require(q["psnr_db"] is not None and math.isfinite(q["psnr_db"]) and math.isfinite(q["ssim"]),
                f"{folder}: finite quality values required for this plot")
        rows[name, mu] = (counts, q["psnr_db"], q["ssim"])
    require(len(rows) == len(ids) * len(strengths), "Incomplete sweep")
    summary = []
    for mu in strengths:
        counts = {c: sum(rows[n, mu][0][c] for n in ids) for c in ("clean", *attacks)}
        summary.append(dict(mu=mu, correct_bits=sum(counts[c] for c in attacks),
                            total_bits=len(ids)*len(attacks)*512, condition_bits=len(ids)*512,
                            **counts, psnr_db=mean(rows[n, mu][1] for n in ids),
                            ssim=mean(rows[n, mu][2] for n in ids)))
    return summary


def table5(rows):
    conditions = ("clean", "noise", "compression", "blur", "drop", "insert", "clip")
    lines = ["| μ | Clean | Noise | Cmprs | Blur | Drop | Insert | Clip | PSNR (dB) | SSIM |",
             "|" + "---:|" * 10]
    for r in rows:
        scores = [f"{r[c]/r['condition_bits']:.3f}" for c in conditions]
        values = [f"{r['mu']:.3f}", *scores, f"{r['psnr_db']:.2f}", f"{r['ssim']:.3f}"]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--configs", type=Path, default=Path("configs"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = collect(args.index, args.configs)
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(9, 3), constrained_layout=True)
    for field, label, axis in zip(("accuracy", "psnr_db", "ssim"), ("Bit accuracy (%)", "PSNR (dB)", "SSIM"), axes):
        values = [100*r["correct_bits"]/r["total_bits"] if field == "accuracy" else r[field] for r in rows]
        axis.plot([r["mu"] for r in rows], values, marker="o")
        axis.set(xlabel="Embedding margin μ", ylabel=label)
    args.output.mkdir(parents=True, exist_ok=False)
    fig.savefig(args.output / "margin-sweep.pdf")
    plt.close(fig)
    (args.output / "table5.md").write_text(table5(rows), encoding="utf-8")
    with (args.output / "margin-sweep.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
