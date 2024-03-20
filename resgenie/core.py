"""Core pydantic models for the transformations. Assumes US-based values"""

from __future__ import annotations
from pathlib import Path
import re
from typing import TypeVar
from pydantic import BaseModel, EmailStr, field_validator
import yaml

Model = TypeVar("Model", bound="YamlModel")

_PHONE_PATTERN = r"(\+[0-9]{0,3})?[\(\s\-]?([0-9]{3})[\)\s\.\-]?\s?([0-9]{3})[\s\.\-]?([0-9]{4})"
_AREA_CODE_PATTERN = r"\([0-9]{3}\)"
_COMPILED_PHONE_PATTERN = re.compile(_PHONE_PATTERN)
_COMPILED_AREA_CODE_PATTERN = re.compile(_AREA_CODE_PATTERN)


class YamlModel(BaseModel):
    """Enabled YAML parsing for the pydantic BaseModel"""

    @classmethod
    def from_file(cls: type[Model], filename: Path | str, encoding: str = "UTF-8") -> Model:
        """Load a pydantic model from a file, using the target encoding.
        Supports YAML and JSON formats"""
        filename = Path(filename)
        with filename.open("r", encoding=encoding) as handle:
            data = yaml.load(handle, yaml.SafeLoader)
        return cls.model_validate(data)


class ResumeAddress(BaseModel):
    """Resume Address information"""

    city: str
    state: str


class ResumeContact(BaseModel):
    """Resume Contact information"""

    email: EmailStr
    name: str
    phone: str
    address: ResumeAddress

    @field_validator("phone", mode="before")
    @classmethod
    def verify_phone(cls, value: str) -> str:
        """Verify the phone number looks like a phone number"""
        results = re.search(_COMPILED_PHONE_PATTERN, value)
        if not results or not results.lastindex or results.lastindex < 4:
            raise ValueError(f"Could not find all parts of {value=}. Expected 3 required and one optional (country code).")
        if ("(" in value or ")" in value) and not re.findall(_COMPILED_AREA_CODE_PATTERN, value):
            raise ValueError(f"'(' or ')' exists, but could not match {_AREA_CODE_PATTERN}. Please correct your number")
        return value


class ResumeEducationEntry(BaseModel):
    """An entry representing some form of education"""

    degree: str
    end: str | None = None
    gpa: float
    institution: str
    location: str
    minor: str | None
    active: bool = True
    specialty: str | None = None


class ResumeExperienceEntry(BaseModel):
    """An entry representing experience at work or other institution"""

    institution: str
    focus: str | None = None
    title: str
    start: str
    end: str | None = None
    location: str
    summary: str
    highlights: list[str] = []


class ResumeSkillGroup(BaseModel):
    """A collection of ranked skills"""

    rank: int
    entries: list[str]


class Resume(YamlModel):
    """A Resume model"""

    contact: ResumeContact
    summary: str
    education: list[ResumeEducationEntry]
    experience: list[ResumeExperienceEntry]
    skills: dict[str, ResumeSkillGroup]

    @field_validator("skills", mode="before")
    @classmethod
    def verify_ranks(cls, value: dict[str, dict[str, int | list[str]]]) -> dict[str, dict[str, int | list[str]]]:
        """Verify there are no colliding ranks"""
        ranks: dict[int | None, str] = {}
        duplicates: dict[int | None, list[str]] = {}
        for key, item in value.items():
            rank: int | None = item.get("rank", None)  # type: ignore[assignment]
            if rank in ranks:
                if rank not in duplicates:
                    duplicates[rank] = [ranks[rank]]
                duplicates[rank].append(key)
            ranks[rank] = key
        if duplicates:
            raise ValueError(f"Ranks must be unique. Found: rank {duplicates=}")
        return value

    def get_skills_by_rank(self, reverse: bool = False) -> list[tuple[str, ResumeSkillGroup]]:
        """Get the skills in order of rank. Optionally reverse the list"""
        ranks = [x.rank for x in self.skills.values()]
        ranks.sort(reverse=reverse)
        ordered: list[tuple[str, ResumeSkillGroup]] = []
        for rank in ranks:
            skill = next((k, v) for k, v in self.skills.items() if v.rank == rank)
            ordered.append(skill)
        return ordered
