import re

perl_to_py_dict_regex = re.compile(r"(?P<key>\S*) (?P<value>[\s\S][^\n]*)")
RETRY_INTERVAL = 10  # in seconds
PACKAGE_COLLECTION = {
    "texlive-core": "scheme-medium",
    "texlive-bibtexextra": "collection-bibtexextra",
    "texlive-fontsextra": "collection-fontsextra",
    "texlive-formatsextra": "collection-formatsextra",
    "texlive-games": "collection-games",
    "texlive-humanities": "collection-humanities",
    "texlive-langchinese": "collection-langchinese",
    "texlive-langcyrillic": "collection-langcyrillic",
    # "texlive-langextra": "collection-langextra",
    "texlive-langgreek": "collection-langgreek",
    "texlive-langjapanese": "collection-langjapanese",
    "texlive-langkorean": "collection-langkorean",
    "texlive-latexextra": "collection-latexextra",
    "texlive-music": "collection-music",
    "texlive-pictures": "collection-pictures",
    "texlive-pstricks": "collection-pstricks",
    "texlive-publishers": "collection-publishers",
    "texlive-science": "collection-mathscience",
}
TEXLIVE_GPG_PUBLIC_KEY_URL = "https://tug.org/texlive/files/texlive.asc"
