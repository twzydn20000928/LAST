"""Command-line utilities for reader-owned LAST inputs."""
import argparse
import json
import os
import secrets
from pathlib import Path


def write_private(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    keygen = commands.add_parser("keygen")
    keygen.add_argument("--output", type=Path, required=True)

    case = commands.add_parser("prepare-video", help="Prepare one video for last.smoke")
    case.add_argument("--output", type=Path, required=True, help="New private directory")
    case.add_argument("--prompt", required=True)
    case.add_argument("--seed", type=int, default=42)
    case.add_argument("--image", type=Path, help="Conditioning image for image-to-video")
    payload = case.add_mutually_exclusive_group(required=True)
    payload.add_argument("--text", help="UTF-8 text up to 64 bytes, padded with zero bytes")
    payload.add_argument("--message-file", type=Path, help="Exactly 64 binary bytes")
    args = parser.parse_args()
    if args.command == "keygen":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        write_private(args.output, secrets.token_bytes(32))
        print(json.dumps({"created": str(args.output), "note": "Keep this file private; never commit it."}))
        return

    if not args.prompt.strip():
        parser.error("Supply a nonempty prompt")
    if not -(2**63) <= args.seed < 2**64:
        parser.error("Seed is outside the supported PyTorch manual_seed range")
    spec = {"prompt": args.prompt, "seed": args.seed}
    if args.image is not None:
        image = args.image.expanduser().resolve()
        if not image.is_file():
            parser.error("Conditioning image must be an existing file")
        spec["image"] = str(image)
    if args.text is not None:
        data = args.text.encode("utf-8")
        if len(data) > 64:
            parser.error("Text exceeds 64 UTF-8 bytes")
        data = data.ljust(64, b"\x00")
    else:
        data = args.message_file.read_bytes()
        if len(data) != 64:
            parser.error("Binary message must contain exactly 64 bytes")

    args.output.mkdir(parents=True, mode=0o700, exist_ok=False)
    write_private(args.output / "secret.key", secrets.token_bytes(32))
    write_private(args.output / "message.bin", data)
    write_private(args.output / "case.json", json.dumps(spec).encode("utf-8"))
    print(json.dumps({"created": str(args.output), "information_bits": 512}))


if __name__ == "__main__":
    main()
