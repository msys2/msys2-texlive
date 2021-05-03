import argparse
from pathlib import Path
import sys
from .constants import PACKAGE_COLLECTION
from .logger import logger
from .main import main_laucher


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

    main_laucher(PACKAGE_COLLECTION[args.package], Path(args.directory), args.package)


if __name__ == "__main__":
    sys.exit(main())
