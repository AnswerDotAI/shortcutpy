from __future__ import annotations

import argparse, subprocess
from pathlib import Path

from .compiler import compile_file


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="shortcutpy")
    p.add_argument("source", type=Path)
    p.add_argument("-O", "--output", type=Path)
    p.add_argument("-o", "--open", action="store_true")
    p.add_argument("--skip-sign", action="store_true")
    p.add_argument("--mode", choices=["anyone", "people-who-know-me"], default="people-who-know-me")
    p.add_argument("--keep-unsigned", action="store_true")
    args = p.parse_args(argv)
    output = args.output or args.source.with_suffix(".shortcut")
    compile_file(args.source, output=output, sign=not args.skip_sign, mode=args.mode, keep_unsigned=args.keep_unsigned)
    if args.open: subprocess.run(["open", str(output)], check=True)


if __name__ == "__main__": main()
