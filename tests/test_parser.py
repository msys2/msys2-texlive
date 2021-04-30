from texlive.main import *
import pytest
from hypothesis import given
from hypothesis.strategies import from_regex
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
