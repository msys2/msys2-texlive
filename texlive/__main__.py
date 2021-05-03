import argparse
import sys
from pathlib import Path

from .constants import PACKAGE_COLLECTION
from .logger import logger
from .main import main_laucher

cli = argparse.ArgumentParser(description="Prepare texlive archives.")
subparsers = cli.add_subparsers(dest="subcommand")


def subcommand(args=[], parent=subparsers):
    def decorator(func):
        parser = parent.add_parser(func.__name__, description=func.__doc__)
        for arg in args:
            parser.add_argument(*arg[0], **arg[1])
        parser.set_defaults(func=func)

    return decorator


def argument(*name_or_flags, **kwargs):
    return ([*name_or_flags], kwargs)


def main():
    @subcommand(
        [
            argument(
                "package",
                type=str,
                help="The pacakge to build.",
                choices=PACKAGE_COLLECTION.keys(),
            ),
            argument("directory", type=str, help="The directory to save files."),
        ]
    )
    def build(args):
        logger.info("Starting...")
        logger.info("Package: %s", args.package)
        logger.info("Directory: %s", args.directory)
        main_laucher(
            PACKAGE_COLLECTION[args.package], Path(args.directory), args.package
        )

    @subcommand(
        [
            argument(
                "repo_path", type=Path, help="The path of the package repository."
            ),
            argument(
                "--texlive-bin",
                action="store_true",
                help="Edit texlive-bin also.",
                #default=False,
                dest="texlive_bin",
            ),
            argument(
                "--source-commit",
                type=Path,
                help="Commit from Github Texlive-source.",
                default=None,
                dest="source_commit",
            ),
        ]
    )
    def makepkgbuild(args):
        from .pkgbuilder import main
        main(args.repo_path, texlive_bin=args.texlive_bin,commit_version=args.source_commit)

    args = cli.parse_args()
    if args.subcommand is None:
        cli.print_help()
    else:
        args.func(args)


if __name__ == "__main__":
    sys.exit(main())
