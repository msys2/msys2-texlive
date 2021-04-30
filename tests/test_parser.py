from texlive.main import *
import texlive.main
import pytest
from hypothesis import given
from hypothesis.strategies import from_regex, integers
from textwrap import dedent


@given(from_regex(perl_to_py_dict_regex, fullmatch=True))
def test_parse_tlpdb_single_line(param):
    # expected = {param.split()[0]:param.split()[1]}
    if param[0] == " ":
        assert parse_tlpdb(param) == {}
    else:
        assert parse_tlpdb(param) == {
            param.split(" ")[0]: " ".join(param.split(" ")[1:])
        }


@pytest.mark.parametrize(
    "param,expected",
    [
        ("1 2\n2 1", {"1": "2", "2": "1"}),
        (
            dedent(
                """\
            execute AddFormat name=jadetex engine=pdftex patterns=language.dat           options="*jadetex.ini"           fmttriggers=atbegshi,atveryend,babel,cm,everyshi,firstaid,hyphen-base,l3backend,l3kernel,l3packages,latex,latex-fonts,tex-ini-files,unicode-data,amsfonts,auxhook,bigintcalc,bitset,colortbl,cyrillic,dehyph,ec,etexcmds,fancyhdr,graphics,graphics-cfg,graphics-def,hycolor,hyperref,hyph-utf8,iftex,infwarerr,intcalc,kvdefinekeys,kvoptions,kvsetkeys,latex,latexconfig,letltxmacro,ltxcmds,marvosym,passivetex,pdfescape,pdftexcmds,psnfss,rerunfilecheck,stmaryrd,symbol,tipa,tools,ulem,uniquecounter,url,wasysym,zapfding
            execute AddFormat name=pdfjadetex engine=pdftex patterns=language.dat           options="*pdfjadetex.ini"           fmttriggers=atbegshi,atveryend,babel,cm,everyshi,firstaid,hyphen-base,l3backend,l3kernel,l3packages,latex,latex-fonts,tex-ini-files,unicode-data,amsfonts,auxhook,bigintcalc,bitset,colortbl,cyrillic,dehyph,ec,etexcmds,fancyhdr,graphics,graphics-cfg,graphics-def,hycolor,hyperref,hyph-utf8,iftex,infwarerr,intcalc,kvdefinekeys,kvoptions,kvsetkeys,latex,latexconfig,letltxmacro,ltxcmds,marvosym,passivetex,pdfescape,pdftexcmds,psnfss,rerunfilecheck,stmaryrd,symbol,tipa,tools,ulem,uniquecounter,url,wasysym,zapfding"""
            ),
            {
                "execute": [
                    'AddFormat name=jadetex engine=pdftex patterns=language.dat           options="*jadetex.ini"           fmttriggers=atbegshi,atveryend,babel,cm,everyshi,firstaid,hyphen-base,l3backend,l3kernel,l3packages,latex,latex-fonts,tex-ini-files,unicode-data,amsfonts,auxhook,bigintcalc,bitset,colortbl,cyrillic,dehyph,ec,etexcmds,fancyhdr,graphics,graphics-cfg,graphics-def,hycolor,hyperref,hyph-utf8,iftex,infwarerr,intcalc,kvdefinekeys,kvoptions,kvsetkeys,latex,latexconfig,letltxmacro,ltxcmds,marvosym,passivetex,pdfescape,pdftexcmds,psnfss,rerunfilecheck,stmaryrd,symbol,tipa,tools,ulem,uniquecounter,url,wasysym,zapfding',
                    'AddFormat name=pdfjadetex engine=pdftex patterns=language.dat           options="*pdfjadetex.ini"           fmttriggers=atbegshi,atveryend,babel,cm,everyshi,firstaid,hyphen-base,l3backend,l3kernel,l3packages,latex,latex-fonts,tex-ini-files,unicode-data,amsfonts,auxhook,bigintcalc,bitset,colortbl,cyrillic,dehyph,ec,etexcmds,fancyhdr,graphics,graphics-cfg,graphics-def,hycolor,hyperref,hyph-utf8,iftex,infwarerr,intcalc,kvdefinekeys,kvoptions,kvsetkeys,latex,latexconfig,letltxmacro,ltxcmds,marvosym,passivetex,pdfescape,pdftexcmds,psnfss,rerunfilecheck,stmaryrd,symbol,tipa,tools,ulem,uniquecounter,url,wasysym,zapfding',
                ]
            },
        ),
        (
            dedent(
                """\
            execute addMap mdbch.map
            execute addMap mdbch.map
            execute addMap mdbch.map
            execute addMap mdbch.map
            execute addMap mdbch.map
            execute addMap mdbch.map"""
            ),
            {"execute": ["addMap mdbch.map"] * 6},
        ),
        ("name hello", {"name": "hello"}),
        ("hello work", {"hello": "work"}),
        (
            dedent(
                """\
            name ctan-o-mat.amd64-freebsd
            category Package
            revision 47009
            shortdesc amd64-freebsd files of ctan-o-mat
            containersize 344
            containerchecksum 120fc79e1795b9655bd8f20fcebbefcfe99bfb4e5a6d1a5142ccf81e339cecd36fc854dcc7aef5987f14e2ebd6fb42a978348129f19566e48e2f08458965821a
            binfiles arch=amd64-freebsd size=1
            bin/amd64-freebsd/ctan-o-mat
            """
            ),
            {
                "name": "ctan-o-mat.amd64-freebsd",
                "category": "Package",
                "revision": "47009",
                "shortdesc": "amd64-freebsd files of ctan-o-mat",
                "containersize": "344",
                "containerchecksum": "120fc79e1795b9655bd8f20fcebbefcfe99bfb4e5a6d1a5142ccf81e339cecd36fc854dcc7aef5987f14e2ebd6fb42a978348129f19566e48e2f08458965821a",
                "binfiles": "arch=amd64-freebsd size=1",
            },
        ),
    ],
)
def test_parse_tlpdb_multiple(param, expected):
    assert parse_tlpdb(param) == expected


def test_dependency(monkeypatch):
    def mock_split_texlive_tlpdb():
        return (
            [
                dedent(
                    """\
            name garrigues
            category Package
            revision 15878
            shortdesc MetaPost macros for the reproduction of Garrigues' Easter nomogram
            relocated 1
            longdesc MetaPost macros for the reproduction of Garrigues' Easter
            longdesc nomogram. These macros are described in Denis Roegel: An
            longdesc introduction to nomography: Garrigues' nomogram for the
            longdesc computation of Easter, TUGboat (volume 30, number 1, 2009,
            longdesc pages 88-104)
            containersize 8268
            containerchecksum e1440fcf8eb0ccd3b140649c590c902882a8a5a02d4cc14589ed44193f3a70bf13839e9de9663c500bb6874d6fce34f5a21c07e38a7456738548b6ebf449b258
            doccontainersize 532
            doccontainerchecksum 0c91f7e1c8fe4910fa7052440edd9afd81c8932e99368219c8a5037bddfa4c8c11037576e9c94721062df9cf7fd5d467389ddcf3aed3e1853be38846c049100f
            docfiles size=2
            RELOC/doc/metapost/garrigues/README details="Readme"
            RELOC/doc/metapost/garrigues/article.txt
            runfiles size=9
            RELOC/metapost/garrigues/garrigues.mp
            catalogue-ctan /graphics/metapost/contrib/macros/garrigues
            catalogue-license lppl
            catalogue-topics calculation
            """
                )
            ]
            * 100
        )

    monkeypatch.setattr(
        texlive.main, "split_texlive_tlpdb_into_para", mock_split_texlive_tlpdb
    )
    all_pkg = get_all_packages()
    assert len(all_pkg) == 1
    assert 'garrigues' in all_pkg
    test = all_pkg['garrigues']
    assert test['category'] == 'Package'
    assert len(test['longdesc']) == 5

def test_split_texlive_tlpdb_into_para(setup_texlive_tlpdb):
    assert len(split_texlive_tlpdb_into_para()) > 7000