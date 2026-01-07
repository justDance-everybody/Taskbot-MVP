"""
Property-based tests for CV Parser Service
Feature: taskbot-completion, Property 6: Resume Parse Round-Trip
Feature: taskbot-completion, Property 7: Resume Field Completeness
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import AsyncMock, MagicMock
from app.services.cv_parser import CVParser


# Strategy for generating valid resume data structures
def resume_data_strategy():
    """Generate valid resume data dictionaries"""
    return st.fixed_dictionaries({
        'name': st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Zs'),
            blacklist_characters='\n\r\t'
        )),
        'skills': st.lists(
            st.text(min_size=1, max_size=30, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'),
                blacklist_characters='\n\r\t'
            )),
            min_size=1,
            max_size=15
        ),
        'job_level': st.integers(min_value=1, max_value=5),
        'experience_years': st.integers(min_value=0, max_value=30),
        'education': st.text(min_size=1, max_size=200),
        'work_experience': st.text(min_size=1, max_size=500),
        'projects': st.text(min_size=1, max_size=500)
    })


# Strategy for generating file names
def filename_strategy():
    """Generate valid PDF file names"""
    return st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))
    ).map(lambda s: s.strip() + '.pdf' if s.strip() else 'resume.pdf')


@pytest.mark.asyncio
@settings(max_examples=100)
@given(
    resume_data=resume_data_strategy(),
    file_name=filename_strategy()
)
async def test_resume_field_completeness_property(resume_data, file_name):
    """
    Property 7: Resume Field Completeness
    
    For any parsed resume, the output SHALL contain all required fields:
    name, skills, job_level, experience_years, education, work_experience, projects.
    
    Validates: Requirements 3.2
    Feature: taskbot-completion, Property 7: Resume Field Completeness
    """
    # Create CV parser instance
    cv_parser = CVParser()
    
    # Test the validation and fill defaults method directly
    # This is the core logic that ensures field completeness
    validated_data = cv_parser._validate_and_fill_defaults(resume_data, file_name)
    
    # Property assertion: all required fields must be present
    required_fields = ['name', 'skills', 'job_level', 'experience_years', 
                      'education', 'work_experience', 'projects']
    
    for field in required_fields:
        assert field in validated_data, f"Required field '{field}' is missing from validated data"
    
    # Additional assertions: fields should have correct types
    assert isinstance(validated_data['name'], str), "name should be a string"
    assert isinstance(validated_data['skills'], list), "skills should be a list"
    assert isinstance(validated_data['job_level'], int), "job_level should be an integer"
    assert isinstance(validated_data['experience_years'], int), "experience_years should be an integer"
    assert isinstance(validated_data['education'], str), "education should be a string"
    assert isinstance(validated_data['work_experience'], str), "work_experience should be a string"
    assert isinstance(validated_data['projects'], str), "projects should be a string"
    
    # Validate constraints
    assert 1 <= validated_data['job_level'] <= 5, "job_level should be between 1 and 5"
    assert validated_data['experience_years'] >= 0, "experience_years should be non-negative"


@pytest.mark.asyncio
@settings(max_examples=100)
@given(
    resume_data=resume_data_strategy(),
    file_name=filename_strategy()
)
async def test_resume_parse_round_trip_property(resume_data, file_name):
    """
    Property 6: Resume Parse Round-Trip
    
    For any valid resume data structure, serializing to display format then parsing back
    SHALL preserve all essential fields (name, skills, experience_years).
    
    Validates: Requirements 3.5
    Feature: taskbot-completion, Property 6: Resume Parse Round-Trip
    """
    # Ensure we have valid input data
    assume(len(resume_data['name'].strip()) > 0)
    assume(len(resume_data['skills']) > 0)
    
    # Create CV parser instance
    cv_parser = CVParser()
    
    # Step 1: Validate and normalize the input data
    validated_data = cv_parser._validate_and_fill_defaults(resume_data, file_name)
    
    # Step 2: Serialize to a text format (simulating display/storage)
    serialized_text = _serialize_resume_to_text(validated_data)
    
    # Step 3: Parse back from text format (simulating re-parsing)
    # We simulate LLM parsing by extracting structured data from the text
    reparsed_data = _parse_resume_from_text(serialized_text, file_name)
    
    # Step 4: Validate the reparsed data
    revalidated_data = cv_parser._validate_and_fill_defaults(reparsed_data, file_name)
    
    # Property assertion: essential fields should be preserved
    # Name should be preserved (allowing for minor formatting differences)
    assert validated_data['name'].strip().lower() == revalidated_data['name'].strip().lower(), \
        f"Name not preserved: '{validated_data['name']}' != '{revalidated_data['name']}'"
    
    # Skills should be preserved (order may differ, but content should match)
    original_skills = set(s.strip().lower() for s in validated_data['skills'] if s.strip())
    reparsed_skills = set(s.strip().lower() for s in revalidated_data['skills'] if s.strip())
    assert original_skills == reparsed_skills, \
        f"Skills not preserved: {original_skills} != {reparsed_skills}"
    
    # Experience years should be preserved
    assert validated_data['experience_years'] == revalidated_data['experience_years'], \
        f"Experience years not preserved: {validated_data['experience_years']} != {revalidated_data['experience_years']}"


@pytest.mark.asyncio
@settings(max_examples=100)
@given(
    incomplete_data=st.fixed_dictionaries({
        'name': st.one_of(st.none(), st.just(''), st.text(min_size=1, max_size=50)),
        'skills': st.one_of(st.none(), st.just([]), st.lists(st.text(min_size=1, max_size=30), min_size=1, max_size=10)),
        'job_level': st.one_of(st.none(), st.integers(min_value=-5, max_value=10)),
        'experience_years': st.one_of(st.none(), st.integers(min_value=-5, max_value=50))
    }),
    file_name=filename_strategy()
)
async def test_resume_field_completeness_with_missing_data(incomplete_data, file_name):
    """
    Property 7 Edge Case: Field Completeness with Missing/Invalid Data
    
    For any resume data with missing or invalid fields, the validation SHALL
    fill in default values and mark for review when necessary.
    
    Validates: Requirements 3.2, 3.3
    Feature: taskbot-completion, Property 7: Resume Field Completeness
    """
    # Create CV parser instance
    cv_parser = CVParser()
    
    # Validate the incomplete data
    validated_data = cv_parser._validate_and_fill_defaults(incomplete_data, file_name)
    
    # Property assertion: all required fields must still be present with valid values
    required_fields = ['name', 'skills', 'job_level', 'experience_years', 
                      'education', 'work_experience', 'projects']
    
    for field in required_fields:
        assert field in validated_data, f"Required field '{field}' is missing"
    
    # Validate that defaults are sensible
    assert isinstance(validated_data['name'], str) and len(validated_data['name']) > 0, \
        "name should be a non-empty string"
    assert isinstance(validated_data['skills'], list), "skills should be a list"
    assert isinstance(validated_data['job_level'], int) and 1 <= validated_data['job_level'] <= 5, \
        "job_level should be an integer between 1 and 5"
    assert isinstance(validated_data['experience_years'], int) and validated_data['experience_years'] >= 0, \
        "experience_years should be a non-negative integer"
    
    # Check needs_review flag is set appropriately
    assert 'needs_review' in validated_data, "needs_review flag should be present"
    
    # If critical fields are missing, needs_review should be True
    if not incomplete_data.get('name') or not incomplete_data.get('skills'):
        assert validated_data['needs_review'] is True, \
            "needs_review should be True when critical fields are missing"


# Helper functions for round-trip testing

def _serialize_resume_to_text(resume_data: dict) -> str:
    """
    Serialize resume data to a text format (simulating display/storage)
    
    This simulates how a resume might be formatted for display or storage,
    then later re-parsed.
    """
    text_parts = [
        f"姓名: {resume_data['name']}",
        f"技能: {', '.join(resume_data['skills'])}",
        f"职级: {resume_data['job_level']}",
        f"工作年限: {resume_data['experience_years']}年",
        f"教育背景: {resume_data['education']}",
        f"工作经历: {resume_data['work_experience']}",
        f"项目经验: {resume_data['projects']}"
    ]
    return '\n'.join(text_parts)


def _parse_resume_from_text(text: str, file_name: str) -> dict:
    """
    Parse resume data from text format (simulating re-parsing)
    
    This simulates how the CV parser would extract structured data from text.
    """
    import re
    
    parsed = {}
    
    # Extract name
    name_match = re.search(r'姓名:\s*(.+)', text)
    if name_match:
        parsed['name'] = name_match.group(1).strip()
    
    # Extract skills
    skills_match = re.search(r'技能:\s*(.+)', text)
    if skills_match:
        skills_text = skills_match.group(1).strip()
        parsed['skills'] = [s.strip() for s in skills_text.split(',') if s.strip()]
    
    # Extract job level
    level_match = re.search(r'职级:\s*(\d+)', text)
    if level_match:
        parsed['job_level'] = int(level_match.group(1))
    
    # Extract experience years
    exp_match = re.search(r'工作年限:\s*(\d+)', text)
    if exp_match:
        parsed['experience_years'] = int(exp_match.group(1))
    
    # Extract education
    edu_match = re.search(r'教育背景:\s*(.+)', text)
    if edu_match:
        parsed['education'] = edu_match.group(1).strip()
    
    # Extract work experience
    work_match = re.search(r'工作经历:\s*(.+)', text)
    if work_match:
        parsed['work_experience'] = work_match.group(1).strip()
    
    # Extract projects
    proj_match = re.search(r'项目经验:\s*(.+)', text)
    if proj_match:
        parsed['projects'] = proj_match.group(1).strip()
    
    return parsed
