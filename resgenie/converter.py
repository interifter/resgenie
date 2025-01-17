"""Converts the core model to a desired output.
Today, you must modify this file to modify the output format.
In the future, we hope to use something like jinja templating"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import markdown
from pyhtml2pdf import converter  # type: ignore[import-untyped]

import resgenie
from resgenie.core import Resume


@dataclass
class Converter(ABC):
    """Converter base"""

    resume: Resume

    @classmethod
    @abstractmethod
    def from_file(cls, file: str | Path) -> Converter:
        """Convert from file"""

    @abstractmethod
    def convert(
        self,
        # template: TemplateFile # One day we'll do this
    ) -> str:
        """Convert the resume to a resume string blob"""

    def to_file(
        self,
        file: str | Path,
        encoding: str = "UTF-8",
        # template: TemplateFile # One day we'll do this
    ) -> None:
        """Convert the resume and save it to a file"""
        content = self.convert()
        file = Path(file)
        with file.open("w+", encoding=encoding) as handle:
            handle.write(content)


@dataclass
class MarkdownConverter(Converter):
    """Converts our core model to a markdown format"""

    style_location: str = "style/style.css"
    style: str = field(init=False)

    def __post_init__(self) -> None:
        """Post-init activities for dataclass"""
        root = Path(resgenie.__file__).parent / self.style_location
        with root.open("r", encoding="UTF8") as handle:
            self.style = f"<style>\n{handle.read()}\n</style>\n"

    @classmethod
    def from_file(cls, file: str | Path) -> MarkdownConverter:
        """Convert from a yml or json Resume file"""
        return cls(
            resume=Resume.from_file(file),
        )

    def build_header(self) -> str:
        """Build the header of the resume"""
        body = self.style
        body += "\n\n"
        # contact
        body += f"# {self.resume.contact.name}\n"
        body += (
            f"{self.resume.contact.address.city}, {self.resume.contact.address.state} | "
            f"{self.resume.contact.phone} | {self.resume.contact.email}\n"
        )
        body += "\n"
        return body

    def build_summary(self) -> str:
        """Build the summary"""
        body = "# Professional Summary\n"
        body += f"{self.resume.summary}\n\n"
        return body

    def build_skills(self) -> str:
        """Build the skills table"""
        body = "# Skills\n"
        body += """
<style>
    td, th {
        border: none!important;
    }
</style>

        """
        body = body.strip()
        body += "\n"
        skills = self.resume.get_skills_by_rank(reverse=False)
        longest = max(len(x[1].entries) for x in skills)

        table = " | ".join([x[0] for x in skills])
        table = "| " + table + " |\n"
        for _ in skills:
            table += "|:--- "
        table += "|\n"

        for x in range(0, longest):
            entry = "| "
            for skill in skills:
                if len(skill[1].entries) > x:
                    entry += f"<span>&bull;</span> {skill[1].entries[x]}"
                else:
                    entry += " "
                entry += " |"
            entry += "\n"
            table += entry

        body += table
        body += "\n\n"
        return body

    def build_experience(self) -> str:
        """Build experience"""
        body = "# Professional Experience\n"
        for entry in self.resume.experience:
            body += f"## {entry.title}"
            if entry.focus:
                body += f" - {entry.focus}"
            body += "\n"
            body += f"**{entry.institution}** | {entry.start} - "
            if entry.end:
                body += entry.end
            else:
                body += "present"
            body += f" | *{entry.location}*\n\n"
            body += entry.summary
            body += "\n\n"
            for highlight in entry.highlights:
                body += f" * {highlight}\n"
            body += "\n"
        return body

    def build_education(self) -> str:
        """Build education"""
        body = "# Education and Course Work\n"
        for entry in self.resume.education:
            body += f"## {entry.degree}\n"
            body += f"**{entry.institution}** | {entry.end} | *{entry.location}*\n\n"
            body += f"*GPA*: {entry.gpa}\n\n"
            if entry.specialty:
                body += f"*Focus*: {entry.specialty}\n\n"
            if entry.minor:
                body += f"*Minor*: {entry.minor}\n\n"
        body += "\n"
        return body

    def convert(
        self,
        # template: TemplateFile # One day we'll do this
    ) -> str:
        """Convert the resume to a resume string blob"""
        # pylint: disable=fixme
        # TODO: Move support to template-based
        body = ""
        body += self.build_header()

        # summary
        body += self.build_summary()

        # skills
        body += self.build_skills()
        # experience

        body += self.build_experience()
        # education
        body += self.build_education()

        body += "\n*Generated with [resgenie](https://github.com/interifter/resgenie)*"
        return body

    def to_file(
        self,
        file: str | Path,
        encoding: str = "UTF-8",
        # template: TemplateFile # One day we'll do this
    ) -> None:
        """Convert the resume and save it to a file"""
        content = self.convert()
        file = Path(file)
        with file.open("w+", encoding=encoding) as handle:
            handle.write(content)


@dataclass
class HtmlConverter(Converter):
    """Converts our core model to a markdown format"""

    @classmethod
    def from_file(cls, file: str | Path) -> HtmlConverter:
        return cls(resume=Resume.from_file(file))

    def convert(self) -> str:
        """Convert to HTML"""

        html = markdown.markdown(MarkdownConverter(resume=self.resume).convert(), extensions=["tables"])
        html = "<head>\n" + html
        html = html.replace(f"<h1>{self.resume.contact.name}", f"\n</head>\n<body class='markdown-body'>\n<h1>{self.resume.contact.name}")
        html += "\n</body>"
        return cast(str, html)

    def to_file(
        self,
        file: str | Path,
        encoding: str = "UTF-8",
        # template: TemplateFile # One day we'll do this
    ) -> None:
        """Convert the resume and save it to a file"""
        content = self.convert()
        file = Path(file)
        with file.open("w+", encoding=encoding) as handle:
            handle.write(content)


@dataclass
class PdfConverter(Converter):
    """Converts our core model to a markdown format"""

    file: str | Path

    @classmethod
    def from_file(cls, file: str | Path) -> PdfConverter:
        return cls(resume=Resume.from_file(file), file=file)

    def convert(self) -> str:
        """Convert to Pdf"""
        raise NotImplementedError()

    def to_file(
        self,
        file: str | Path,
        encoding: str = "UTF-8",
        # template: TemplateFile # One day we'll do this
    ) -> None:
        """Convert the resume and save it to a file"""

        HtmlConverter.from_file(self.file).to_file("_resume.html")
        converter.convert(str(Path("_resume.html").absolute()), str(file), timeout=2, print_options={"author": self.resume.contact.email})
        Path("_resume.html").unlink()
        # # pylint: disable=no-value-for-parameter
        # cli(["-o", str(file), str(Path(self.file).absolute())], standalone_mode=False)
