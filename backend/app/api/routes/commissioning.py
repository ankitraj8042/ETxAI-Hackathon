"""
DCBrain API — Commissioning QA Copilot (HERO Feature)
Test procedures, result analysis, and guided commissioning workflows.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models import CommissioningTest, TestResult, TestCategory

router = APIRouter()


@router.get("/tests")
async def list_tests(
    category: str = None,
    result: str = None,
    db: AsyncSession = Depends(get_db),
):
    """List all commissioning tests with optional filtering."""
    query = select(CommissioningTest).order_by(CommissioningTest.test_code)
    if category:
        query = query.where(CommissioningTest.category == category)
    if result:
        query = query.where(CommissioningTest.result == result)

    res = await db.execute(query)
    tests = res.scalars().all()

    return [
        {
            "id": str(t.id),
            "test_code": t.test_code,
            "name": t.name,
            "category": t.category.value,
            "standard_reference": t.standard_reference,
            "tier_requirement": t.tier_requirement,
            "result": t.result.value,
            "is_blocked": t.is_blocked,
            "blocked_by": t.blocked_by,
            "ist_level": t.ist_level,
            "ai_diagnosis": t.ai_diagnosis,
        }
        for t in tests
    ]


@router.get("/tests/{test_code}")
async def get_test_detail(test_code: str, db: AsyncSession = Depends(get_db)):
    """Get full test detail with procedure steps, criteria, results, and AI analysis."""
    result = await db.execute(
        select(CommissioningTest).where(CommissioningTest.test_code == test_code)
    )
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail=f"Test {test_code} not found")

    return {
        "id": str(test.id),
        "test_code": test.test_code,
        "name": test.name,
        "description": test.description,
        "category": test.category.value,
        "standard_reference": test.standard_reference,
        "tier_requirement": test.tier_requirement,
        "procedure_steps": test.procedure_steps,
        "acceptance_criteria": test.acceptance_criteria,
        "result": test.result.value,
        "test_date": test.test_date.isoformat() if test.test_date else None,
        "measured_values": test.measured_values,
        "ai_diagnosis": test.ai_diagnosis,
        "ai_fix_suggestion": test.ai_fix_suggestion,
        "ai_root_cause": test.ai_root_cause,
        "is_blocked": test.is_blocked,
        "blocked_by": test.blocked_by,
        "blocking_tests": test.blocking_tests,
        "ist_level": test.ist_level,
    }


@router.get("/readiness")
async def get_commissioning_readiness(db: AsyncSession = Depends(get_db)):
    """Get overall commissioning readiness summary."""
    res = await db.execute(select(CommissioningTest))
    tests = res.scalars().all()

    total = len(tests)
    by_result = {}
    by_category = {}
    blocked = []

    for t in tests:
        r = t.result.value
        by_result[r] = by_result.get(r, 0) + 1

        cat = t.category.value
        if cat not in by_category:
            by_category[cat] = {"total": 0, "pass": 0, "fail": 0, "blocked": 0}
        by_category[cat]["total"] += 1
        if t.result == TestResult.PASS:
            by_category[cat]["pass"] += 1
        elif t.result == TestResult.FAIL:
            by_category[cat]["fail"] += 1
        if t.is_blocked:
            by_category[cat]["blocked"] += 1
            blocked.append({
                "test_code": t.test_code,
                "name": t.name,
                "blocked_by": t.blocked_by,
            })

    passed = by_result.get("pass", 0)
    readiness_pct = int((passed / max(total, 1)) * 100)

    return {
        "readiness_pct": readiness_pct,
        "total_tests": total,
        "by_result": by_result,
        "by_category": by_category,
        "blocked_tests": blocked,
        "tests_can_proceed": total - len(blocked) - passed - by_result.get("fail", 0),
    }


@router.post("/analyze-results/{test_code}")
async def analyze_test_results(
    test_code: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger the Commissioning Agent to analyze test results and diagnose failures.
    This is the HERO feature demo endpoint.
    """
    from app.services.commissioning_service import commissioning_service
    res = await commissioning_service.analyze_test_results(test_code, db)
    if "status" in res and res["status"] == "error":
        raise HTTPException(status_code=404, detail=res["message"])
    return res
