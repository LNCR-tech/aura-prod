"""Use: Tests bulk import repository helpers.
Where to use: Run this with pytest to verify bulk duplicate lookups stay correct for large inputs.
Role: Test layer. It protects repository lookup behavior from regressions.
"""

from __future__ import annotations

from app.models import Department, Program, Role, School, StudentProfile, User, UserRole
from app.repositories.import_repository import ImportRepository


def _create_school(test_db, *, code: str) -> School:
    school = School(
        name=f"Repo School {code}",
        school_name=f"Repo School {code}",
        school_code=code,
        address="Repo Test Address",
    )
    test_db.add(school)
    test_db.commit()
    return school


def _get_or_create_role(test_db, *, name: str) -> Role:
    role = test_db.query(Role).filter(Role.name == name).first()
    if role is None:
        role = Role(name=name)
        test_db.add(role)
        test_db.commit()
    return role


def _create_student(
    test_db,
    *,
    school_id: int,
    email: str,
    student_id: str,
    department_id: int,
    program_id: int,
) -> User:
    student_role = _get_or_create_role(test_db, name="student")
    user = User(
        email=email,
        school_id=school_id,
        first_name="Repo",
        last_name="Student",
        must_change_password=False,
    )
    user.set_password("StudentPass123!")
    test_db.add(user)
    test_db.commit()

    test_db.add(UserRole(user_id=user.id, role_id=student_role.id))
    test_db.add(
        StudentProfile(
            user_id=user.id,
            school_id=school_id,
            student_id=student_id,
            department_id=department_id,
            program_id=program_id,
            year_level=1,
        )
    )
    test_db.commit()
    return user


def test_existing_emails_handles_multiple_chunks(test_db, monkeypatch):
    monkeypatch.setattr("app.repositories.import_repository.BULK_LOOKUP_CHUNK_SIZE", 2)

    school = _create_school(test_db, code="REPO-EMAIL")
    department = Department(school_id=school.id, name="Computer Science")
    program = Program(school_id=school.id, name="BS Computer Science")
    program.departments.append(department)
    test_db.add_all([department, program])
    test_db.commit()

    _create_student(
        test_db,
        school_id=school.id,
        email="existing.one@example.edu",
        student_id="STU-00001",
        department_id=department.id,
        program_id=program.id,
    )
    _create_student(
        test_db,
        school_id=school.id,
        email="existing.two@example.edu",
        student_id="STU-00002",
        department_id=department.id,
        program_id=program.id,
    )

    repo = ImportRepository(test_db)
    existing = repo.existing_emails(
        [
            "existing.one@example.edu",
            "missing.one@example.edu",
            "existing.two@example.edu",
            "missing.two@example.edu",
            "existing.one@example.edu",
        ]
    )

    assert existing == {
        "existing.one@example.edu",
        "existing.two@example.edu",
    }


def test_existing_school_student_pairs_handles_multiple_chunks(test_db, monkeypatch):
    monkeypatch.setattr("app.repositories.import_repository.BULK_LOOKUP_CHUNK_SIZE", 2)

    school = _create_school(test_db, code="REPO-PAIR")
    department = Department(school_id=school.id, name="Computer Science")
    program = Program(school_id=school.id, name="BS Computer Science")
    program.departments.append(department)
    test_db.add_all([department, program])
    test_db.commit()

    _create_student(
        test_db,
        school_id=school.id,
        email="existing.pair.one@example.edu",
        student_id="STU-10001",
        department_id=department.id,
        program_id=program.id,
    )
    _create_student(
        test_db,
        school_id=school.id,
        email="existing.pair.two@example.edu",
        student_id="STU-10002",
        department_id=department.id,
        program_id=program.id,
    )

    repo = ImportRepository(test_db)
    existing_pairs = repo.existing_school_student_pairs(
        [
            (school.id, "STU-10001"),
            (school.id, "STU-99999"),
            (school.id, "STU-10002"),
            (school.id, "STU-88888"),
            (school.id, "STU-10001"),
        ]
    )

    assert existing_pairs == {
        (school.id, "STU-10001"),
        (school.id, "STU-10002"),
    }
