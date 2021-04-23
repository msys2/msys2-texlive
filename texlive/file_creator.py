import re
import typing
from pathlib import Path

from .logger import logger


def create_fmts(
    pkg_infos: typing.Dict[
        str, typing.Union[typing.Dict[str, typing.Union[str, list]]]
    ],
    filename_save: Path,
) -> Path:
    logger.info("Creating %s file", filename_save)
    key_value_search_regex = re.compile(r"(?P<key>\S*)=(?P<value>[\S]+)")
    quotes_search_regex = re.compile(
        r"((?<![\\])['\"])(?P<options>(?:.(?!(?<![\\])\1))*.?)\1"
    )
    final_file = ""

    def parse_perl_string(temp: str) -> typing.Dict[str, str]:
        t_dict: typing.Dict[str, str] = {}
        for mat in key_value_search_regex.finditer(temp):
            if '"' not in mat.group("value"):
                t_dict[mat.group("key")] = mat.group("value")
        quotes_search = quotes_search_regex.search(temp)
        if quotes_search:
            t_dict["options"] = quotes_search.group("options")
        for i in {"name", "engine", "patterns", "options"}:
            if i not in t_dict:
                t_dict[i] = "-"
        return t_dict

    for pkg in pkg_infos:
        temp_pkg = pkg_infos[pkg]
        if "execute" in temp_pkg:
            temp = temp_pkg["execute"]
            if isinstance(temp, str):
                if "AddFormat" in temp:
                    parsed_dict = parse_perl_string(temp)
                    final_file += "{name} {engine} {patterns} {options}\n".format(
                        **parsed_dict
                    )
            else:
                for each in temp:
                    if "AddFormat" in each:
                        parsed_dict = parse_perl_string(each)
                        final_file += "{name} {engine} {patterns} {options}\n".format(
                            **parsed_dict
                        )
    with filename_save.open("w", encoding="utf-8") as f:
        f.write(final_file)
        logger.info("Wrote %s", filename_save)
    return filename_save


def create_maps(
    pkg_infos: typing.Dict[
        str, typing.Union[typing.Dict[str, typing.Union[str, list]]]
    ],
    filename_save: Path,
) -> Path:
    logger.info("Creating %s file", filename_save)
    final_file = ""

    kanji_map_regex = re.compile(r"add(?P<final>KanjiMap[\s\S][^\n]*)")
    mixed_map_regex = re.compile(r"add(?P<final>MixedMap[\s\S][^\n]*)")
    map_regex = re.compile(r"add(?P<final>Map[\s\S][^\n]*)")

    def parse_string(temp: str):
        if "addMixedMap" in temp:
            res = mixed_map_regex.search(temp)
            if res:
                return res.group("final")
        elif "addMap" in temp:
            res = map_regex.search(temp)
            if res:
                return res.group("final")
        elif "addKanjiMap" in temp:
            res = kanji_map_regex.search(temp)
            if res:
                return res.group("final")

    for pkg in pkg_infos:
        temp_pkg = pkg_infos[pkg]
        if "execute" in temp_pkg:
            temp = temp_pkg["execute"]
            if isinstance(temp, str):
                if "addMap" in temp or "addMixedMap" in temp or "addKanjiMap" in temp:
                    final_file += parse_string(temp)
                    final_file += "\n"
            else:
                for each in temp:
                    if (
                        "addMap" in each
                        or "addMixedMap" in each
                        or "addKanjiMap" in each
                    ):
                        final_file += parse_string(each)
                        final_file += "\n"

    # let's sort the line
    temp_lines = final_file.split("\n")
    temp_lines.sort()
    final_file = "\n".join(temp_lines)
    final_file.strip()
    with filename_save.open("w", encoding="utf-8") as f:
        f.write(final_file)
        logger.info("Wrote %s", filename_save)
    return filename_save
