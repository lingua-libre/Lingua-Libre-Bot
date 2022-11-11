import pytest

from utils import sparql


class MockResult:
    def __init__(self, value):
        self.__value = value

    def json(self):
        return self.__value


class MockSession:
    def post(self, url, data=None, json=None, **kwargs) -> MockResult:
        return MockResult({'results': {'bindings': [
            {'item': {'type': 'uri', 'value': 'http://www.wikidata.org/entity/Q5111'},
             'code': {'type': 'literal', 'value': 'ab'}},
            {'item': {'type': 'uri', 'value': 'http://www.wikidata.org/entity/Q27683'},
             'code': {'type': 'literal', 'value': 'ace'}}]}})


def test_query_wikidata():
    result = sparql.wikidata_post("VALID QUERY", session=MockSession())
    assert result == [{'item': {'type': 'uri', 'value': 'http://www.wikidata.org/entity/Q5111'},
                       'code': {'type': 'literal', 'value': 'ab'}}, {
                          'item': {'type': 'uri', 'value': 'http://www.wikidata.org/entity/Q27683'},
                          'code': {'type': 'literal', 'value': 'ace'}}]


@pytest.mark.parametrize("value,expected",
                         [("https://lingualibre.org/entity/Q15", "Q15"),
                          ("https://lingualibre.org/entity/Q1505", "Q1505"),
                          ("http://www.wikidata.org/entity/Q5111", "Q5111"),
                          ("http://www.wikidata.org/entity/Q27683", "Q27683"),
                          ("http://commons.wikimedia.org/wiki/Special:FilePath/"
                           "LL-Q150%20%28fra%29-0x010C-Holtzwihr.wav", "LL-Q150%20%28fra%29-0x010C-Holtzwihr.wav"),
                          ("http://commons.wikimedia.org/wiki/Special:FilePath/"
                           "LL-Q150%20%28fra%29-0x010C-perm%C3%A9able.wav",
                           "LL-Q150%20%28fra%29-0x010C-perm%C3%A9able.wav")],
                         ids=["lingualibre1", "lingualibre2", "wikidata1", "wikidata2", "commons1", "commons2"])
def test_extract_value_from_uri(value, expected):
    result = sparql.extract_value_from_uri(value)
    assert result == expected


@pytest.mark.parametrize("value", ["Q12348", "LL-Q150%20%28fra%29-0x010C-perm%C3%A9able.wav"], ids=["qid", "filename"])
def test_extract_value_fails_without_uri(value):
    with pytest.raises(sparql.UnknownUriPrefixException):
        sparql.extract_value_from_uri(value)
