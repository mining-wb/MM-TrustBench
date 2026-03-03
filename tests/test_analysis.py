# 阅卷与答案解析逻辑
import pytest
from src.analysis import extract_yes_no, normalize_label


#====== extract_yes_no ======
def test_extract_yes_no_explicit_yes():
    assert extract_yes_no("yes") == "yes"
    assert extract_yes_no("Answer: yes") == "yes"
    assert extract_yes_no("The answer is Yes.") == "yes"


def test_extract_yes_no_explicit_no():
    assert extract_yes_no("no") == "no"
    assert extract_yes_no("Answer: no") == "no"
    assert extract_yes_no("I see No person.") == "no"


def test_extract_yes_no_unknown_empty_or_error():
    assert extract_yes_no("") == "unknown"
    assert extract_yes_no("Error") == "unknown"


def test_extract_yes_no_uncertain_returns_unknown():
    assert extract_yes_no("I cannot determine") == "unknown"
    assert extract_yes_no("It is unclear") == "unknown"


def test_extract_yes_no_negative_phrase_to_no():
    assert extract_yes_no("There is no person in the image") == "no"
    assert extract_yes_no("There are no cats") == "no"


def test_extract_yes_no_positive_phrase_to_yes():
    assert extract_yes_no("There is a person in the image") == "yes"
    assert extract_yes_no("There are two dogs") == "yes"


#====== normalize_label ======
def test_normalize_label_yes():
    assert normalize_label("yes") == "yes"
    assert normalize_label("y") == "yes"
    assert normalize_label("YES") == "yes"


def test_normalize_label_no():
    assert normalize_label("no") == "no"
    assert normalize_label("n") == "no"
    assert normalize_label("NO") == "no"


def test_normalize_label_unknown():
    assert normalize_label("") == "unknown"
    assert normalize_label("other") == "unknown"
