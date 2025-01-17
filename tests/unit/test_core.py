"""Unit tests for resgenie/core.py"""

import pytest

from resgenie.core import Resume, ResumeContact
from tests.resources import HAPPY_PATH_YML_RESUME


def test_load_resume_from_file() -> None:
    """Happy path test to confirm we can load our resume from a file"""
    resume = HAPPY_PATH_YML_RESUME
    Resume.from_file(resume)


@pytest.mark.parametrize(
    "number, expected_exception",
    [
        ("5555555555", None),
        ("+55555555555", None),
        ("+1(555)5555555", None),
        ("(555) 555 5555", None),
        ("(555 555 5555", ValueError),
        ("555.555.555", ValueError),
        ("555.555.5555", None),
        ("555 555-5555", None),
    ],
)
def test_resume_contact_verify_phone(number: str, expected_exception: type[BaseException] | None) -> None:
    """Different use cases to ensure verify phone is good enough for US-based numbers"""
    # You would normally not call these validators, directly.
    # pylint: disable=fixme
    # TODO: Add more corner cases to test, or refactor the verify code with a library that does it for us.
    if not expected_exception:
        assert ResumeContact.verify_phone(number) == number  # type: ignore[call-arg]
    else:
        with pytest.raises(expected_exception):
            ResumeContact.verify_phone(number)  # type: ignore[call-arg]


def test_resume_skills_ranks() -> None:
    """Verify a ValueError is raised when resume skill ranks are duplicated"""
    buckets = {
        "spam": {"rank": 1, "entries": ["eggs"]},
        "waffles": {"rank": 2, "entries": ["pandan"]},
        "dosa": {"rank": 1, "entries": ["ham"]},
        "bulgogi": {"rank": 5, "entries": ["adobo"]},
    }

    with pytest.raises(ValueError) as exc_info:
        Resume.verify_ranks(buckets)  # type: ignore[call-arg]
    assert "Found: rank duplicates={1: ['spam', 'dosa']" in exc_info.value.args[0]


def test_resume_chart() -> None:
    """Test to ensure the chart is loading info correctly"""
    resume = HAPPY_PATH_YML_RESUME
    model = Resume.from_file(resume)
    assert model.charts
    chart_keys = model.charts[0].keys()
    expected_keys = [
        "perl",
        "objective-c",
        "c-sharp",
        "java",
        "windows-batch",
        "powershell",
        "cpp",
        "simics",
        "msbuild",
        "python",
        "groovy",
        "cmake",
        "gha",
        "docker",
    ]
    assert chart_keys == expected_keys

    dictionary = model.charts[0].key_x_values()
    assert all(key in dictionary for key in expected_keys)

    display_names = model.charts[0].keys_display_names()
    assert all(key in display_names for key in expected_keys)
