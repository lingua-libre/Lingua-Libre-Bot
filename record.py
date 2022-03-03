from dataclasses import dataclass
from typing import Dict


@dataclass
class Record:
    id: str
    file: str
    transcription: str
    speaker_residence: str
    links: Dict[str, str]
    language: Dict[str, str]
