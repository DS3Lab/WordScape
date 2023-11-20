from oletools.oleid import RISK, OleID, Indicator
from oletools import ftguess, oleobj, ooxml
from oletools.common.codepages import get_codepage_name, codepage2codec

from typing import List, Tuple, Union

# these relationship types are taken care of during document annotation /
# sanitization
WHITELISTED_RELATIONSHIP_TYPES = [
    "hyperlink"
]

FATAL_INDICATORS = [
    "appname",
    "codepage",
    "encrypted",
    "ext_rels",
    "ObjectPool",
    "vba",
    "xlm",
    "flash"
]

PASS_RISK_LEVELS = [
    RISK.NONE,
    RISK.INFO,
    RISK.UNKNOWN,
    RISK.ERROR
]


def decode_bytes(bytes_: bytes, decoder: str):
    """
    Decode a bytes object to to a string.

    @param bytes_: bytes object
    @param decoder: type to decode to (default str)

    return: str
    """

    if bytes_ is None or isinstance(bytes_, str) or decoder is None:
        return bytes_
    try:
        bytes_decoded = bytes_.decode(decoder)
    except Exception as e:
        print(
            "caught exception while decoding bytes {}:"
            "\n\t{}".format(bytes_, e)
        )
        return bytes_

    return bytes_decoded


class MalDocCheck(OleID):
    def __init__(self, filename: str = None, data: bytes = None):
        """
        A handler to check for malicious files.

        @param filename: Document filename
        @param data: bytes representing the file to be checked (usually from an HTTP response)
        """
        super().__init__(filename=filename, data=data)

    @staticmethod
    def validate_indicators(
            indicators: List[Indicator]
    ) -> Tuple[bool, Union[str, None]]:
        """
        check whether one of the indicators is a risk

        @param indicators: list of indicators

        return: True if no risk, False if risk, and the reason for the risk
        """
        reasons = []
        for indicator in indicators:
            if indicator.id in FATAL_INDICATORS:
                if indicator.risk in PASS_RISK_LEVELS:
                    continue
                reasons.append("{}={}".format(indicator.id, indicator.value))

        if len(reasons) > 0:
            reason_str = ",".join(reasons)
            return False, reason_str

        return True, None

    def run(self) -> List[Indicator]:
        """
        Open file and run all checks on it.

        returns: list of :py:class:`Indicator`
        """
        self.ftg = ftguess.FileTypeGuesser(
            filepath=self.filename, data=self.data
        )
        ftype = self.ftg.ftype
        # if it's an unrecognized OLE file, display the root CLSID in
        # description:
        if self.ftg.filetype == ftguess.FTYPE.GENERIC_OLE:
            description = 'Unrecognized OLE file. Root CLSID: {} - {}'.format(
                self.ftg.root_clsid, self.ftg.root_clsid_name)
        else:
            description = ''

        ft = Indicator('ftype', value=ftype.longname, _type=str,
                       name='File format',
                       risk=RISK.INFO,
                       description=description)
        self.indicators.append(ft)
        ct = Indicator('container', value=ftype.container, _type=str,
                       name='Container format', risk=RISK.INFO,
                       description='Container type')
        self.indicators.append(ct)

        # check if it is actually an OLE file:
        if self.ftg.container == ftguess.CONTAINER.OLE:
            # reuse olefile already opened by ftguess
            self.ole = self.ftg.olefile

        self.check_properties()
        self.check_encrypted()
        self.check_macros()
        self.check_external_relationships()
        self.check_object_pool()
        self.check_flash()

        if self.ole is not None:
            self.ole.close()

        return self.indicators

    def check_properties(self):
        """
        Read summary information required for other check_* functions

        return: 2 :py:class:`Indicator`s (for presence of summary info and
                    application name) or None if file was not opened
        """
        if not self.ole:
            return None
        meta = self.ole.get_metadata()

        # get decoder
        codepage_name = None
        if meta.codepage is not None:
            codepage_name = '{}: {}'.format(
                meta.codepage, get_codepage_name(meta.codepage)
            )
        codepage = Indicator('codepage', codepage_name, _type=str,
                             name='Properties code page',
                             description='Code page used for properties',
                             risk=RISK.INFO)
        self.indicators.append(codepage)

        codec_name = None
        if meta.codepage is not None:
            codec_name = codepage2codec(meta.codepage)
        python_codec = Indicator(
            'python_codec', codec_name, _type=str,
            name='Python codec',
            description='Python codec used to decode properties',
            risk=RISK.INFO
        )
        self.indicators.append(python_codec)

        # get app name
        appname_decoded = decode_bytes(meta.creating_application, codec_name)
        appname = Indicator(
            'appname', appname_decoded, _type=str,
            name='Application name',
            description='Application name declared in properties',
            risk=RISK.INFO
        )
        self.indicators.append(appname)

        # get author name
        author_name = decode_bytes(meta.author, codec_name)
        author = Indicator(
            'author', author_name, _type=str,
            name='Author',
            description='Author declared in properties',
            risk=RISK.INFO
        )
        self.indicators.append(author)

        return appname, codepage, python_codec, author

    def check_external_relationships(self):
        """
        Check whether this file has external relationships
        (remote template, OLE object, etc).

        return: :py:class:`Indicator`
        """
        dsc = "External relationships such as remote templates, " \
              "remote OLE objects, etc"
        ext_rels = Indicator(
            'ext_rels', 'None', name='External Relationships', _type=int,
            risk=RISK.NONE,
            description=dsc, hide_if_false=False
        )
        self.indicators.append(ext_rels)

        # this check only works for OpenXML files
        if not self.ftg.is_openxml():
            return ext_rels

        # to collect relationship types:
        rel_types = set()

        # open an XmlParser, using a BytesIO instead of filename (to work in
        # memory)
        xmlparser = ooxml.XmlParser(self.data_bytesio)

        for rel_type, target in oleobj.find_external_relationships(xmlparser):
            if rel_type not in WHITELISTED_RELATIONSHIP_TYPES:
                rel_types.add(str(rel_type))

        if len(rel_types) > 0:
            ext_rels.value = ','.join(rel_types)

        if ext_rels.value != "None":
            ext_rels.description = \
                'External relationships found: {} - use oleobj' \
                ' for details'.format(', '.join(rel_types))
            ext_rels.risk = RISK.HIGH

        return ext_rels
