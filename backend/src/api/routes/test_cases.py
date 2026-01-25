import json
import os
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException
from src.api.models.test_case import TestCase, TestCaseCreate, TestCaseUpdate
from src.utils.config import settings

router = APIRouter()


def get_test_case_path(test_case_id: str) -> str:
    """Get file path for a test case"""
    # Check manual and phekb directories
    manual_path = os.path.join(settings.test_cases_dir, "manual", f"{test_case_id}.json")
    phekb_path = os.path.join(settings.test_cases_dir, "phekb", f"{test_case_id}.json")

    if os.path.exists(manual_path):
        return manual_path
    elif os.path.exists(phekb_path):
        return phekb_path

    return manual_path  # Default to manual for new test cases


def load_test_case(test_case_id: str) -> TestCase:
    """Load a test case from file"""
    file_path = get_test_case_path(test_case_id)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Test case {test_case_id} not found")

    with open(file_path, "r") as f:
        data = json.load(f)

    return TestCase(**data)


def save_test_case(test_case: TestCase) -> None:
    """Save a test case to file"""
    file_path = get_test_case_path(test_case.id)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "w") as f:
        json.dump(test_case.model_dump(), f, indent=2, default=str)


def list_test_case_ids() -> List[str]:
    """List all test case IDs"""
    test_case_ids = []

    for directory in ["manual", "phekb"]:
        dir_path = os.path.join(settings.test_cases_dir, directory)
        if os.path.exists(dir_path):
            for filename in os.listdir(dir_path):
                if filename.endswith(".json"):
                    test_case_ids.append(filename[:-5])  # Remove .json extension

    return test_case_ids


@router.get("", response_model=List[TestCase])
async def list_test_cases():
    """List all test cases"""
    test_case_ids = list_test_case_ids()
    test_cases = []

    for test_case_id in test_case_ids:
        try:
            test_case = load_test_case(test_case_id)
            test_cases.append(test_case)
        except Exception as e:
            # Skip invalid test cases
            print(f"Error loading test case {test_case_id}: {e}")

    return test_cases


@router.get("/{test_case_id}", response_model=TestCase)
async def get_test_case(test_case_id: str):
    """Get a specific test case"""
    return load_test_case(test_case_id)


@router.post("", response_model=TestCase, status_code=201)
async def create_test_case(test_case_create: TestCaseCreate):
    """Create a new test case"""
    # Generate ID from name
    test_case_id = test_case_create.name.lower().replace(" ", "-").replace("_", "-")

    # Check if test case already exists
    file_path = get_test_case_path(test_case_id)
    if os.path.exists(file_path):
        raise HTTPException(status_code=400, detail=f"Test case {test_case_id} already exists")

    # Create test case
    now = datetime.utcnow()
    test_case = TestCase(
        id=test_case_id,
        **test_case_create.model_dump(),
        created_at=now,
        updated_at=now,
    )

    save_test_case(test_case)
    return test_case


@router.put("/{test_case_id}", response_model=TestCase)
async def update_test_case(test_case_id: str, test_case_update: TestCaseUpdate):
    """Update a test case"""
    test_case = load_test_case(test_case_id)

    # Update fields
    update_data = test_case_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(test_case, field, value)

    test_case.updated_at = datetime.utcnow()

    save_test_case(test_case)
    return test_case


@router.delete("/{test_case_id}")
async def delete_test_case(test_case_id: str):
    """Delete a test case"""
    file_path = get_test_case_path(test_case_id)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Test case {test_case_id} not found")

    os.remove(file_path)
    return {"message": f"Test case {test_case_id} deleted successfully"}
