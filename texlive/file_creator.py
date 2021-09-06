import re
import typing
from pathlib import Path
from string import Template
from textwrap import dedent

from .logger import logger
from .requests_handler import retry_get

default_lefthyphenmin = "2"
default_righthyphenmin = "3"


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


def create_language_def(
    pkg_infos: typing.Dict[
        str, typing.Union[typing.Dict[str, typing.Union[str, list]]]
    ],
    filename_save: Path,
):
    """create_language_def This create language.def from the given
    :attr:`pkg_infos`. :attr:`pkg_infos` can be is from
    :func:`get_needed_packages_with_info`.

    Parameters
    ----------
    pkg_infos
        The dict of packages from
    filename_save
        The name of the file to save.
    """
    logger.info("Creating %s file", filename_save)
    key_value_search_regex = re.compile(r"(?P<key>\S*)=(?P<value>[\S]+)")
    final_file = "% test"  # this is to avoid empty files.

    def parse_string(temp: str) -> typing.Dict[str, str]:
        t_dict: typing.Dict[str, str] = {}
        for mat in key_value_search_regex.finditer(temp):
            if '"' not in mat.group("value"):
                t_dict[mat.group("key")] = mat.group("value")
        for i in [
            "name",
            "file",
            "file_patterns",
            "file_exceptions",
            "lefthyphenmin",
            "righthyphenmin",
            "synonyms",
        ]:
            if i not in t_dict:
                t_dict[i] = ""
        if t_dict["lefthyphenmin"] == "":
            t_dict["lefthyphenmin"] = default_lefthyphenmin
        if t_dict["righthyphenmin"] == "":
            t_dict["righthyphenmin"] = default_righthyphenmin
        return t_dict

    for pkg in pkg_infos:
        temp_pkg = pkg_infos[pkg]
        if "execute" in temp_pkg:
            temp = temp_pkg["execute"]
            if isinstance(temp, str):
                if "AddHyphen" in temp:
                    final_file += f"% from {temp_pkg['name']}:\n"
                    parsed_dict = parse_string(temp)
                    final_file += Template(
                        "\\addlanguage{$name}{$file}"
                        "{}{$lefthyphenmin}{$righthyphenmin}\n",
                    ).substitute(**parsed_dict)
                    if parsed_dict["synonyms"]:
                        synonyms = parsed_dict["synonyms"].split(",")
                        for i in synonyms:
                            parsed_dict["name"] = i
                            final_file += Template(
                                "\\addlanguage{$name}{$file}"
                                "{}{$lefthyphenmin}{$righthyphenmin}\n",
                            ).substitute(**parsed_dict)
            else:
                has_hypen = [True for each in temp if "AddHyphen" in each]
                if has_hypen:
                    final_file += f"% from {temp_pkg['name']}:\n"
                for each in temp:
                    if "AddHyphen" in each:
                        parsed_dict = parse_string(each)
                        final_file += Template(
                            "\\addlanguage{$name}{$file}"
                            "{}{$lefthyphenmin}{$righthyphenmin}\n"
                        ).substitute(**parsed_dict)
                        if parsed_dict["synonyms"]:
                            synonyms = parsed_dict["synonyms"].split(",")
                            for i in synonyms:
                                parsed_dict["name"] = i
                                final_file += Template(
                                    "\\addlanguage{$name}{$file}"
                                    "{}{$lefthyphenmin}{$righthyphenmin}\n"
                                ).substitute(**parsed_dict)
    with filename_save.open("w", encoding="utf-8") as f:
        f.write(final_file)
        logger.info("Wrote %s", filename_save)
    return filename_save


def create_language_dat(
    pkg_infos: typing.Dict[
        str, typing.Union[typing.Dict[str, typing.Union[str, list]]]
    ],
    filename_save: Path,
):
    """This create language.dat from the given
    :attr:`pkg_infos`. :attr:`pkg_infos` can be is from
    :func:`get_needed_packages_with_info`.

    Parameters
    ----------
    pkg_infos
        The dict of packages from
    filename_save
        The name of the file to save.
    """
    logger.info("Creating %s file", filename_save)
    key_value_search_regex = re.compile(r"(?P<key>\S*)=(?P<value>[\S]+)")
    final_file = "% test"  # this is to avoid empty files.

    def parse_string(temp: str) -> typing.Dict[str, str]:
        t_dict: typing.Dict[str, str] = {}
        for mat in key_value_search_regex.finditer(temp):
            if '"' not in mat.group("value"):
                t_dict[mat.group("key")] = mat.group("value")
        for i in [
            "name",
            "file",
            "file_patterns",
            "file_exceptions",
            "lefthyphenmin",
            "righthyphenmin",
            "synonyms",
        ]:
            if i not in t_dict:
                t_dict[i] = ""
        return t_dict

    for pkg in pkg_infos:
        temp_pkg = pkg_infos[pkg]
        if "execute" in temp_pkg:
            temp = temp_pkg["execute"]
            if isinstance(temp, str):
                if "AddHyphen" in temp:
                    final_file += f"% from {temp_pkg['name']}:\n"
                    parsed_dict = parse_string(temp)
                    final_file += Template(
                        "$name $file\n",
                    ).substitute(**parsed_dict)
                    if parsed_dict["synonyms"]:
                        synonyms = parsed_dict["synonyms"].split(",")
                        for i in synonyms:
                            parsed_dict["name"] = i
                            final_file += Template("=$name\n").substitute(**parsed_dict)
            else:
                has_hypen = [True for each in temp if "AddHyphen" in each]
                if has_hypen:
                    final_file += f"% from {temp_pkg['name']}:\n"
                for each in temp:
                    if "AddHyphen" in each:
                        parsed_dict = parse_string(each)
                        final_file += Template(
                            "$name $file\n",
                        ).substitute(**parsed_dict)
                        if parsed_dict["synonyms"]:
                            synonyms = parsed_dict["synonyms"].split(",")
                            for i in synonyms:
                                parsed_dict["name"] = i
                                final_file += Template("=$name\n").substitute(
                                    **parsed_dict
                                )
    with filename_save.open("w", encoding="utf-8") as f:
        f.write(final_file)
        logger.info("Wrote %s", filename_save)
    return filename_save


def create_language_lua(
    pkg_infos: typing.Dict[
        str, typing.Union[typing.Dict[str, typing.Union[str, list]]]
    ],
    filename_save: Path,
):
    """This create language.dat from the given
    :attr:`pkg_infos`. :attr:`pkg_infos` can be is from
    :func:`get_needed_packages_with_info`.

    Parameters
    ----------
    pkg_infos
        The dict of packages from
    filename_save
        The name of the file to save.
    """
    logger.info("Creating %s file", filename_save)
    key_value_search_regex = re.compile(r"(?P<key>\S*)=(?P<value>[\S]+)")
    quotes_search_regex = re.compile(
        r"((?<![\\])['\"])(?P<luaspecial>(?:.(?!(?<![\\])\1))*.?)\1"
    )
    final_file = "-- test"  # this is to avoid empty files.

    def parse_string(temp: str) -> typing.Dict[str, str]:
        t_dict: typing.Dict[str, str] = {}
        for mat in key_value_search_regex.finditer(temp):
            if '"' not in mat.group("value"):
                t_dict[mat.group("key")] = mat.group("value")
        quotes_search = quotes_search_regex.search(temp)
        if quotes_search:
            t_dict["luaspecial"] = quotes_search.group("luaspecial")
        for i in [
            "name",
            "file",
            "file_patterns",
            "file_exceptions",
            "lefthyphenmin",
            "righthyphenmin",
            "synonyms",
            "luaspecial",
        ]:
            if i not in t_dict:
                t_dict[i] = ""
        if t_dict["lefthyphenmin"] == "":
            t_dict["lefthyphenmin"] = default_lefthyphenmin
        if t_dict["righthyphenmin"] == "":
            t_dict["righthyphenmin"] = default_righthyphenmin
        return t_dict

    for pkg in pkg_infos:
        temp_pkg = pkg_infos[pkg]
        if "execute" in temp_pkg:
            temp = temp_pkg["execute"]
            if isinstance(temp, str):
                if "AddHyphen" in temp:
                    final_file += f"-- from {temp_pkg['name']}:\n"
                    parsed_dict = parse_string(temp)
                    if parsed_dict["synonyms"]:
                        parsed_dict[
                            "synonyms"
                        ] = f"""'{"', '".join(parsed_dict['synonyms'].split(','))}'"""
                    if not parsed_dict["luaspecial"]:
                        final_file += Template(
                            dedent(
                                """\
                            ['$name'] = {
                                loader = '$file',
                                lefthyphenmin = $lefthyphenmin,
                                righthyphenmin = $righthyphenmin,
                                synonyms = { $synonyms },
                                patterns = '$file_patterns',
                                hyphenation = '$file_exceptions',
                            },
                            """
                            ),
                        ).substitute(**parsed_dict)
                    else:
                        print(parsed_dict["luaspecial"])
                        final_file += Template(
                            dedent(
                                """\
                            ['$name'] = {
                                loader = '$file',
                                lefthyphenmin = $lefthyphenmin,
                                righthyphenmin = $righthyphenmin,
                                synonyms = { $synonyms },
                                patterns = '$file_patterns',
                                hyphenation = '$file_exceptions',
                                special = '$luaspecial',
                            },
                            """
                            ),
                        ).substitute(**parsed_dict)
            else:
                has_hypen = [True for each in temp if "AddHyphen" in each]
                if has_hypen:
                    final_file += f"-- from {temp_pkg['name']}:\n"
                for each in temp:
                    if "AddHyphen" in each:
                        parsed_dict = parse_string(each)
                        if parsed_dict["synonyms"]:
                            parsed_dict["synonyms"] = (
                                "'"
                                f"""{"', '".join(parsed_dict['synonyms'].split(','))}"""
                                "'"
                            )
                        if not parsed_dict["luaspecial"]:
                            final_file += Template(
                                dedent(
                                    """\
                                ['$name'] = {
                                    loader = '$file',
                                    lefthyphenmin = $lefthyphenmin,
                                    righthyphenmin = $righthyphenmin,
                                    synonyms = { $synonyms },
                                    patterns = '$file_patterns',
                                    hyphenation = '$file_exceptions',
                                },
                                """
                                ),
                            ).substitute(**parsed_dict)
                        else:
                            print(parsed_dict["luaspecial"])
                            final_file += Template(
                                dedent(
                                    """\
                                ['$name'] = {
                                    loader = '$file',
                                    lefthyphenmin = $lefthyphenmin,
                                    righthyphenmin = $righthyphenmin,
                                    synonyms = { $synonyms },
                                    patterns = '$file_patterns',
                                    hyphenation = '$file_exceptions',
                                    special = '$luaspecial',
                                },
                                """
                                ),
                            ).substitute(**parsed_dict)
    with filename_save.open("w", encoding="utf-8") as f:
        f.write(final_file)
        logger.info("Wrote %s", filename_save)
    return filename_save


def create_linked_scripts(
    pkg_infos: typing.Dict[
        str, typing.Union[typing.Dict[str, typing.Union[str, list]]]
    ],
    filename_save: Path,
    all_packages: typing.Dict[str, typing.Dict[str, typing.Union[list, str]]],
    texlive_tlpdb_split: typing.List[str],
):
    """This create ``<package-name>.scripts`` from the given
    :attr:`pkg_infos`. :attr:`pkg_infos` can be is from
    :func:`get_needed_packages_with_info`.
    ``<package-name>.scripts`` will contain the exectuable to be
    created when packaging, which should be sourceable in a bash
    shell.

    Parameters
    ----------
    pkg_infos
        The dict of packages from
    filename_save
        The name of the file to save.
    all_packages
        A list of all package from :func:`get_all_packages`
    texlive_tlpdb_split
        A list of contents in ``texlive.tlpdb``
        from :func:`split_texlive_tlpdb_into_para`.
    """
    logger.info("Creating %s file", filename_save)
    final_file = "# This file contains linked scripts list for the package.\n"
    final_file += 'linked_scripts="'
    find_script_regex = re.compile(
        r"^( *)texmf-dist\/scripts\/(?P<script>(?P<script_name>[\/\w\-]*)\.(?P<script_ext>[\/\w\-]*))",  # noqa: E501
        re.MULTILINE,
    )
    # See https://github.com/msys2/msys2-texlive/issues/10 for discussions
    # get the `scripts.lst`, iter through `texlive.tlpdb` and if it exists add it
    # or else skip.
    all_scripts = retry_get(
        "https://github.com/TeX-Live/texlive-source/raw/trunk/texk/texlive/linked_scripts/scripts.lst"  # noqa: E501
    ).text.split("\n")
    for pkg in pkg_infos:
        for n, all_pkg_iter in enumerate(all_packages):
            if pkg == all_pkg_iter:
                temp_str = texlive_tlpdb_split[n]
                for script in find_script_regex.finditer(temp_str):
                    if script.group("script") in all_scripts:
                        final_file += script.group("script") + "\n"
                break
    final_file += '"'
    with filename_save.open("w", encoding="utf-8", newline="\n") as f:
        f.write(final_file)
        logger.info("Wrote %s", filename_save)
