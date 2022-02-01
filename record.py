from dataclasses import dataclass
from typing import Dict

from speaker import Speaker


@dataclass
class Record:
    id: str
    file: str
    date: str
    transcription: str
    qualifier: str
    user: str
    speaker: Speaker
    links: Dict[str, str]
    language: Dict[str, str]
