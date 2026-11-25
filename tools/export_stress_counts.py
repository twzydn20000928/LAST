"""Recount private stress predictions and export the public Table 15 input."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path

import numpy as np

from last.campaign import digest
from last.stress_evaluate import recount, verify_attack, verify_counts


def reader_identity(repo):
    if repo.is_file():
        with tarfile.open(repo, "r:*") as archive:
            members = [item for item in archive if item.isfile()
                       and re.fullmatch(r"(?:[^/]+/)?src/last/[^/]+\.py", item.name)]
            commit = archive.pax_headers.get("comment", "").strip()
            names = [Path(item.name).name for item in members]
            if not re.fullmatch(r"[0-9a-f]{40}", commit) or not names or len(names) != len(set(names)):
                raise ValueError("Expected a Git archive with a commit ID and unique reader sources")
            checksum = hashlib.sha256()
            for member in sorted(members, key=lambda item: Path(item.name).name):
                checksum.update(Path(member.name).name.encode())
                checksum.update(archive.extractfile(member).read())
            return commit, checksum.hexdigest()

    def git(*args):
        return subprocess.check_output(["git", "-C", str(repo), *args])

    commit = git("rev-parse", "HEAD").decode().strip()
    paths = git("ls-tree", "-r", "--name-only", commit, "src/last").decode().splitlines()
    files = sorted(Path(name).name for name in paths
                   if Path(name).parent.as_posix() == "src/last" and name.endswith(".py"))
    if not files:
        raise ValueError("Reader checkout lacks src/last Python sources")
    checksum = hashlib.sha256()
    for name in files:
        checksum.update(name.encode())
        checksum.update(git("show", f"{commit}:src/last/{name}"))
    return commit, checksum.hexdigest()


def export(run, attacks, evaluation, repo, *, alignment=False):
    commit, reader_sha = reader_identity(repo)
    generation = json.loads((run / "receipt.json").read_bytes())
    source_sha = digest(run / "marked.mp4")
    if (generation["status"] != "completed" or generation["method"] != "last"
            or generation["marked_sha256"] != source_sha):
        raise ValueError("Incomplete or mismatched source generation")
    family = generation["family"]
    truth = np.load(run / "message.npy", allow_pickle=False)
    rows = []
    seen = set()
    for receipt in sorted(attacks.rglob("attack.json")):
        folder = receipt.parent
        attack, video = verify_attack(folder, source_sha)
        target = evaluation / folder.relative_to(attacks)
        record = json.loads((target / "evaluation.json").read_bytes())
        decoded = target / "decoded_private.json"
        if (record["status"] != "completed" or record["source_sha256_files"] != reader_sha
                or record["source_sha256"] != source_sha or record["received_sha256"] != attack["received_sha256"]
                or record["decoded_sha256"] != digest(decoded)):
            raise ValueError("Reader provenance or prediction mismatch")
        for path in (receipt, video, run / "receipt.json", run / "marked.mp4",
                     run / "secret.key", run / "message.npy"):
            if record["input_sha256"][str(path.resolve())] != digest(path):
                raise ValueError("Private input changed since extraction")
        identity = attack["attack"], attack["seed"]
        if attack["video_id"] != run.name or identity in seen:
            raise ValueError("Wrong video or duplicate attack map")
        seen.add(identity)
        prediction = json.loads(decoded.read_bytes())
        verify_counts(record, prediction, truth, attack, family)
        row = {key: attack[key] for key in ("attack", "seed", "received_sha256")}
        row.update(recount(prediction, truth, attack["received_sha256"], family),
                   received_frames=attack["frames"])
        if alignment:
            from stress_chain_table import score

            route = prediction["route"]
            groups = prediction["groups"]
            if (route, groups) != (record["route"], record["groups"]):
                raise ValueError("Saved alignment differs from evaluation receipt")
            row.update(route=route, groups=groups, chain_lengths=None, alignment=None)
            if route == "ccta":
                row["alignment"] = score(prediction, attack)
                row["chain_lengths"] = [chain["length"] for chain in prediction["chains"]]
        for key in ("donor_sha256", "donor_video_id", "donor_plan_sha256"):
            if key in attack:
                row[key] = attack[key]
        rows.append(row)
    if not rows:
        raise ValueError("No attack receipts")
    return dict(video_id=run.name, family=family, mode=generation["mode"], method="last",
                reader_commit=commit, source_sha256=source_sha, rows=rows)


def write_report(path, report):
    # Publish only a complete JSON file. A second exporter must not overwrite the first.
    with tempfile.TemporaryDirectory(dir=path.parent) as staging:
        pending = Path(staging) / "counts.json"
        pending.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        os.link(pending, path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("run", "attacks", "evaluation", "reader-repo", "output"):
        parser.add_argument("--" + option, type=Path, required=True)
    parser.add_argument("--alignment", action="store_true", help="Score saved CCTA chains after extraction")
    args = parser.parse_args()
    report = export(args.run, args.attacks, args.evaluation, args.reader_repo, alignment=args.alignment)
    write_report(args.output, report)
