import re

perl_to_py_dict_regex = re.compile(r"(?P<key>\S*) (?P<value>[\s\S][^\n]*)")
RETRY_INTERVAL = 10  # in seconds
PACKAGE_COLLECTION = {
    "texlive-core": [
        "collection-basic",
        "collection-xetex",
        "collection-context",
        "collection-latex",
    ],
    "texlive-bibtex-extra": "collection-bibtexextra",
    "texlive-extra-utils": "collection-binextra",
    "texlive-fonts-extra": "collection-fontsextra",
    "texlive-fonts-recommended": "collection-fontsrecommended",
    "texlive-font-utils": "collection-fontutils",
    "texlive-formats-extra": "collection-formatsextra",
    "texlive-games": "collection-games",
    "texlive-humanities": "collection-humanities",
    "texlive-lang-arabic": "collection-langarabic",
    "texlive-lang-chinese": "collection-langchinese",
    "texlive-lang-cjk": "collection-langcjk",
    "texlive-lang-cyrillic": "collection-langcyrillic",
    "texlive-lang-czechslovak": "collection-langczechslovak",
    "texlive-lang-english": "collection-langenglish",
    "texlive-lang-european": "collection-langeuropean",
    "texlive-lang-french": "collection-langfrench",
    "texlive-lang-german": "collection-langgerman",
    "texlive-lang-greek": "collection-langgreek",
    "texlive-lang-italian": "collection-langitalian",
    "texlive-lang-japanese": "collection-langjapanese",
    "texlive-lang-korean": "collection-langkorean",
    "texlive-lang-other": "collection-langother",
    "texlive-lang-polish": "collection-langpolish",
    "texlive-lang-portuguese": "collection-langportuguese",
    "texlive-lang-spanish": "collection-langspanish",
    "texlive-latex-extra": "collection-latexextra",
    "texlive-latex-recommended": "collection-latexrecommended",
    "texlive-luatex": "collection-luatex",
    "texlive-metapost": "collection-metapost",
    "texlive-music": "collection-music",
    "texlive-pictures": "collection-pictures",
    "texlive-plain-generic": "collection-plaingeneric",
    "texlive-pstricks": "collection-pstricks",
    "texlive-publishers": "collection-publishers",
    "texlive-science": "collection-mathscience",
}
