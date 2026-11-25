"""Render Figure 4 from fifteen completed development runs."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import mean
from last.temporal import attack_map


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audit_cells(entries, root, config, *, all_development=False):
    manifest_path = config / "development_manifest.json"
    manifest = read(manifest_path)
    ids = [s["id"] for s in manifest["samples"]] if all_development else manifest["margin_sweep_ids"]
    samples = {s["id"]: s for s in manifest["samples"]}
    protocol = read(config / "paper_v1.json")
    strengths = protocol["margin_sweep"]["mu"]
    frames = protocol["video"]["frames"]
    video = protocol["video"]
    model = protocol["hunyuan"]
    required_settings = dict(steps=model["steps"], cfg=model["guidance"], shift=model["shift"],
                             frames=frames, size=[video["height"], video["width"]],
                             clean_crf=video["clean_crf"], fps=video["fps"], **protocol["precision"])
    seed = protocol["attacks"]["primary_map_seed"]
    attacks = ("noise", "compression", "blur", "drop", "insert", "clip")
    rows = {}
    paired = {}
    pipeline = None
    for entry in entries:
        name = entry["video_id"]
        folder = root / entry["run"]
        g = read(folder / "receipt.json")
        q = read(folder / "quality.json")
        mu = g["mu"]
        require(name in ids and mu in strengths and (name, mu) not in rows, "Unexpected or duplicate sweep cell")
        require(g["status"] == "completed" and g["method"] == "last" and g["mode"] == "i2v" and not g["fixed_target"]
                and not g["uniform_profile"], f"{folder}: incorrect writer")
        require(g["family"] == "hunyuan" and all(g["settings"].get(k) == v for k, v in required_settings.items()),
                f"{folder}: generation differs from the frozen Hunyuan I2V sweep protocol")
        case = read(folder / "case.json")
        require(g["case_sha256"] == digest(folder / "case.json") and case["video_id"] == name
                and case["development_manifest_sha256"] == digest(manifest_path)
                and case["seed"] == samples[name]["seed"] == g["seed"]
                and case["prompt"] == samples[name]["prompt"] and case["key_slot"] == samples[name]["key_slot"],
                f"{folder}: case mismatch")
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
            mapping = attack_map(name, attack, seed, frames, protocol["attacks"]["temporal_count"]) if attack in ("drop", "insert", "clip") else None
            require(r["status"] == "completed" and r["video_id"] == name and r["method"] == "last"
                    and r["condition"] == attack and r["source_sha256"] == marked
                    and r["received_sha256"] == received
                    and r["map_seed"] == seed and r["attack_map"] == mapping
                    and r["frames"] == (len(mapping) if mapping is not None else frames) and r["total_bits"] == 512
                    and type(r["correct_bits"]) is int and 0 <= r["correct_bits"] <= 512,
                    f"{stem}: attack receipt mismatch")
            counts[attack] = r["correct_bits"]
        require(paired.setdefault(name, pairing) == pairing, f"{folder}: strengths are unpaired")
        require(q["frames"] == frames and 0 < q["rgb_mse"] <= 1 and not q["identical"]
                and q["psnr_db"] is not None and math.isclose(q["psnr_db"], -10 * math.log10(q["rgb_mse"]), abs_tol=1e-8)
                and -1 <= q["ssim"] <= 1, f"{folder}: invalid paired quality measurements")
        rows[name, mu] = (counts, q["psnr_db"], q["ssim"])
    return rows, ids, strengths, attacks


def collect(index, config):
    rows, ids, strengths, attacks = audit_cells(read(index), index.parent, config)
    return summarize(rows, ids, strengths, attacks)


def summarize(rows, ids, strengths, attacks):
    require(len(rows) == len(ids) * len(strengths), "Incomplete sweep")
    summary = []
    for mu in strengths:
        counts = {c: sum(rows[n, mu][0][c] for n in ids) for c in ("clean", *attacks)}
        summary.append(dict(mu=mu, correct_bits=sum(counts[c] for c in attacks),
                            total_bits=len(ids)*len(attacks)*512, condition_bits=len(ids)*512,
                            **counts, psnr_db=mean(rows[n, mu][1] for n in ids),
                            ssim=mean(rows[n, mu][2] for n in ids)))
    return summary


def load_public_cells(path, config, *, all_development=False):
    dev = read(config / "development_manifest.json")
    ids = [s["id"] for s in dev["samples"]] if all_development else dev["margin_sweep_ids"]
    strengths = read(config / "paper_v1.json")["margin_sweep"]["mu"]
    attacks = ("noise", "compression", "blur", "drop", "insert", "clip")
    rows = {}
    for cell in read(path):
        key = (cell["video_id"], cell["mu"])
        counts = cell["correct_bits"]
        require(key[0] in ids and key[1] in strengths and key not in rows,
                "Unexpected or duplicate public sweep cell")
        require(set(counts) == {"clean", *attacks} and cell["bits_per_condition"] == 512
                and all(type(v) is int and 0 <= v <= 512 for v in counts.values()),
                "Invalid public sweep counts")
        require(math.isfinite(cell["psnr_db"]) and -1 <= cell["ssim"] <= 1,
                "Invalid public sweep quality")
        rows[key] = (counts, cell["psnr_db"], cell["ssim"])
    return rows, ids, strengths, attacks


def table5(rows):
    conditions = ("clean", "noise", "compression", "blur", "drop", "insert", "clip")
    lines = ["| μ | Clean | Noise | Cmprs | Blur | Drop | Insert | Clip | PSNR (dB) | SSIM |",
             "|" + "---:|" * 10]
    for r in rows:
        scores = [f"{r[c]/r['condition_bits']:.3f}" for c in conditions]
        values = [f"{r['mu']:.3f}", *scores, f"{r['psnr_db']:.2f}", f"{r['ssim']:.3f}"]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def export_public_cells(path, cells):
    public = [dict(video_id=name, mu=mu, correct_bits=counts, bits_per_condition=512,
                   psnr_db=psnr, ssim=ssim)
              for (name, mu), (counts, psnr, ssim) in sorted(cells.items())]
    with path.open("x", encoding="utf-8") as stream:
        json.dump(public, stream, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--index", type=Path, help="Index of private acquisition directories")
    source.add_argument("--cells", type=Path, help="Public audited per-video, per-margin measurements")
    parser.add_argument("--configs", type=Path, default=Path("configs"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tables-only", action="store_true", help="Export measurements and tables without Matplotlib")
    args = parser.parse_args()
    if args.index:
        cells = audit_cells(read(args.index), args.index.parent, args.configs)
    else:
        cells = load_public_cells(args.cells, args.configs)
    rows = summarize(*cells)
    if not args.tables_only:
        import matplotlib.pyplot as plt
    args.output.mkdir(parents=True, exist_ok=False)
    export_public_cells(args.output / "cells.json", cells[0])
    (args.output / "table5.md").write_text(table5(rows), encoding="utf-8")
    with (args.output / "margin-sweep.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    if not args.tables_only:
        fig, axes = plt.subplots(1, 3, figsize=(9, 3), constrained_layout=True)
        for field, label, axis in zip(("accuracy", "psnr_db", "ssim"), ("Bit accuracy (%)", "PSNR (dB)", "SSIM"), axes):
            values = [100*r["correct_bits"]/r["total_bits"] if field == "accuracy" else r[field] for r in rows]
            axis.plot([r["mu"] for r in rows], values, marker="o")
            axis.set(xlabel="Embedding margin μ", ylabel=label)
        fig.savefig(args.output / "margin-sweep.pdf")
        plt.close(fig)


if __name__ == "__main__":
    main()
