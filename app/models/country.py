from sqlmodel import Field
from app.db.base_class import Base
from enum import Enum

class Country(Base, table=True):
    id: int | None = Field(primary_key=True, index=True, unique=True)
    name: str = Field(max_length=50)

class CountryEnum(Enum):
    UNKNOWN = 0, "Unknown"
    ARMENIA = 1, "Armenia"
    BELARUS = 2, "Belarus"
    KAZAKHSTAN = 3, "Kazakhstan"
    KYRGYZSTAN = 4, "Kyrgyzstan"
    RUSSIA = 5, "Russia"

    @property
    def code(self):
        return self.value[0]

    @property
    def label(self):
        return self.value[1]

    @classmethod
    def from_code(cls, code: int):
        for country in cls:
            if country.code == code:
                return country
        return cls.UNKNOWN

    @classmethod
    def get_all_labels(cls) -> list[str]:
        return [country.label for country in cls]

    @classmethod
    def get_all_codes(cls) -> list[int]:
        return [country.code for country in cls]

    @classmethod
    def get_all_countries(cls) -> list[Country]:
        return [Country(id=country.code, name=country.label) for country in cls]

    def __str__(self):
        return self.label




