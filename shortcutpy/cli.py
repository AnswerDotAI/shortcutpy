import argparse, subprocess, sys, tempfile
from pathlib import Path

from .compiler import compile_file, compile_source, default_output_name, default_output_path, materialize_artifact
from .shortcuts_db import dump_shortcut_text


def open_output_path(src: Path, name: str) -> Path:
    return Path(tempfile.mkdtemp(prefix="shortcutpy-open-")) / f"{default_output_name(name)}.shortcut"


def compile_main(argv: list[str]) -> None:
    p = argparse.ArgumentParser(prog="shortcutpy")
    p.add_argument("source", type=Path)
    p.add_argument("-O", "--output", type=Path)
    p.add_argument("-o", "--open", action="store_true")
    p.add_argument("--skip-sign", action="store_true")
    p.add_argument("--mode", choices=["anyone", "people-who-know-me"], default="people-who-know-me")
    p.add_argument("--keep-unsigned", action="store_true")
    args = p.parse_args(argv)
    if args.open and not args.output:
        artifact = compile_source(args.source.read_text(), filename=str(args.source))
        output = open_output_path(args.source, artifact.program.meta.name)
        materialize_artifact(artifact, args.source, output=output, sign=not args.skip_sign, mode=args.mode, keep_unsigned=args.keep_unsigned)
    else:
        artifact = compile_file(args.source, output=args.output, sign=not args.skip_sign, mode=args.mode, keep_unsigned=args.keep_unsigned)
        output = args.output or default_output_path(args.source, artifact.program.meta.name)
    if args.open: subprocess.run(["open", str(output)], check=True)


def dump_main(argv: list[str]) -> None:
    p = argparse.ArgumentParser(prog="shortcutpy dump")
    p.add_argument("name")
    p.add_argument("-O", "--output", type=Path)
    args = p.parse_args(argv)
    text = dump_shortcut_text(args.name)
    if args.output: args.output.write_text(text)
    else: sys.stdout.write(text)


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "dump": dump_main(argv[1:])
    else: compile_main(argv)


if __name__ == "__main__": main()
