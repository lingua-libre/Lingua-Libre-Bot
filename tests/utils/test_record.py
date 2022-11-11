import pytest

from utils.record import create_record, extract_links_from_bindings

create_record_data = [
    ({'record': {'type': 'uri', 'value': 'https://lingualibre.org/entity/Q1551'},
      'file': {'type': 'uri',
               'value': 'http://commons.wikimedia.org/wiki/Special:FilePath/'
                        'LL-Q150%20%28fra%29-0x010C-perm%C3%A9able.wav'},
      'transcription': {'type': 'literal', 'value': 'perméable'},
      'languageQid': {'type': 'literal', 'value': 'Q150'},
      'residence': {'type': 'literal', 'value': 'Q147987'},
      'learningPlace': {'type': 'bnode', 'value': 't32286'},
      'languageLevel': {'type': 'uri', 'value': 'https://lingualibre.org/entity/Q15'}},
     "Q1551", "LL-Q150%20%28fra%29-0x010C-perm%C3%A9able.wav", "perméable", "Q147987", {},
     {"qid": "Q150", "learning": "t32286", "level": "Q15"}),
    ({'record': {'type': 'uri', 'value': 'https://lingualibre.org/entity/Q4266'},
      'wikipediaTitle': {'type': 'literal', 'value': 'fr:Holtzwihr'},
      'file': {'type': 'uri',
               'value': 'http://commons.wikimedia.org/wiki/Special:FilePath/LL-Q150%20%28fra%29-0x010C-Holtzwihr.wav'},
      'transcription': {'type': 'literal', 'value': 'Holtzwihr'},
      'languageQid': {'type': 'literal', 'value': 'Q150'},
      'residence': {'type': 'literal', 'value': 'Q147987'},
      'learningPlace': {'type': 'bnode', 'value': 't8223112'},
      'languageLevel': {'type': 'uri', 'value': 'https://lingualibre.org/entity/Q15'}},
     "Q4266", "LL-Q150%20%28fra%29-0x010C-Holtzwihr.wav", "Holtzwihr", "Q147987", {'wikipedia': 'fr:Holtzwihr'},
     {"qid": "Q150", "learning": "t8223112", "level": "Q15"})
]


@pytest.mark.parametrize("bindings,record_id,file,transcription,speaker_residence,links,language",
                         create_record_data,
                         ids=["normal", "wikipedia_link"])
def test_create_record(bindings, record_id, file, transcription, speaker_residence, links, language):
    record = create_record(bindings)
    assert record.id == record_id
    assert record.file == file
    assert record.transcription == transcription
    assert record.speaker_residence == speaker_residence
    assert record.links == links
    assert record.language == language

#
# @pytest.mark.parametrize("bindings,expected_links",
#                          create_record_data,
#                          ids=["none", "wikipedia_link"])
# def test_extract_links_from_bindings(bindings, expected_links):
#     links = extract_links_from_bindings(bindings)
#     assert links == expected_links
