"""Core pydantic models for the transformations. Assumes US-based values"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated, TypeVar

import yaml
from pydantic import BaseModel, EmailStr, Field, field_validator

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


class ResumeWyeAxisDataPoint(BaseModel):
    """A data point in the yAxis entry"""

    value: float
    display: str = ""


class ResumeWyeAxisEntry(BaseModel):
    """A y-axis entry"""

    y_value: Annotated[str | int, Field(alias="yValue")]
    data: dict[str, ResumeWyeAxisDataPoint]

    def keys(self) -> list[str]:
        """Returns the list of keys, ordered in discovered order"""
        return list(self.data.keys())

    def keys_display_names(self) -> dict[str, str]:
        """Get the key mapping for its display"""
        return {x: (x if not y.display else y.display) for x, y in self.data.items()}


class ResumeChartEntry(BaseModel):
    """A Chart Entry"""

    title: str
    points: list[ResumeWyeAxisEntry]

    def keys(self) -> list[str]:
        """Returns the list of keys, ordered in discovered order"""
        keys: list[str] = []
        for point in self.points:
            for key in point.keys():
                if key in keys:
                    continue
                keys.append(key)
        return keys

    def key_x_values(self) -> dict[str, list[float]]:
        """Return a dictionary of the key value pairs"""
        data: dict[str, list[float]] = {x: [] for x in self.keys()}
        for point in self.points:
            for key in data.keys():
                entry = point.data.get(key, None)
                if entry:
                    data[key].append(entry.value)
                else:
                    data[key].append(0.0)
        return data

    def keys_display_names(self) -> dict[str, str]:
        """Get the key mapping for its display"""
        keys: dict[str, str] = {}
        for point in self.points:
            for key, value in point.keys_display_names().items():
                if key in keys:
                    continue
                keys[key] = value
        return keys


class Resume(YamlModel):
    """A Resume model"""

    contact: ResumeContact
    summary: str
    education: list[ResumeEducationEntry]
    experience: list[ResumeExperienceEntry]
    skills: dict[str, ResumeSkillGroup]
    charts: list[ResumeChartEntry] | None = None

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
