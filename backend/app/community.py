"""Seven Delhi calendar dates of completed items, separated by data mode."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request

from .households import private_response, reload_profile, transaction

router = APIRouter(dependencies=[Depends(private_response)])
DELHI = timezone(timedelta(hours=5, minutes=30))


def window():
    end = datetime.now(DELHI).date()
    return end - timedelta(days=6), end


def totals(db, mode, start, end, *, locality=None, household_id=None):
    threshold = 5 if locality is not None else 1
    predicate = "p.locality_key = lower(btrim(%s))" if locality is not None else "p.household_id = %s"
    row = db.execute(f"""
        WITH completed AS (
            SELECT p.household_id, i.card
            FROM daily_plans p JOIN plan_items i ON i.plan_id = p.id
            WHERE p.plan_date BETWEEN %s AND %s AND p.data_mode = %s AND {predicate}
              AND i.status = 'done'
        )
        SELECT count(DISTINCT household_id), count(*),
            CASE WHEN count(DISTINCT household_id) FILTER (WHERE card ? 'commute_example') >= %s
                 THEN sum((card #>> '{{commute_example,co2_difference_g}}')::numeric) END,
            CASE WHEN count(DISTINCT household_id) FILTER (WHERE card ? 'indoor_example') >= %s
                 THEN sum((card #>> '{{indoor_example,avoided_inhaled_pm25_ug}}')::numeric) END
        FROM completed HAVING count(DISTINCT household_id) >= %s
        """, (start, end, mode, locality if locality is not None else household_id,
              threshold, threshold, threshold)).fetchone()
    if row is None:
        return None
    return dict(households=row[0], actions=row[1], modeled_co2_g=row[2], modeled_pm25_ug=row[3])


@router.get("/community/digest")
def digest(request: Request, locality: str = Query(min_length=1, max_length=80)):
    start, end = window()
    with transaction() as db:
        summary = totals(db, request.app.state.mode, start, end, locality=locality)
    return dict(locality=locality.strip(), start=start, end=end, data_mode=request.app.state.mode, summary=summary)


@router.get("/plan/week")
def weekly(request: Request, profile=Depends(reload_profile)):
    start, end = window()
    with transaction() as db:
        summary = totals(db, request.app.state.mode, start, end, household_id=profile["id"])
    return dict(start=start, end=end, data_mode=request.app.state.mode, summary=summary)

@router.get("/community/example")
def example():
    start, end = window()
    # Fictional completed action counts for five example households.
    counts = [2, 1, 3, 2, 4]
    return dict(locality="Demo Delhi", start=start, end=end, data_mode="demo",
                summary=dict(households=len(counts), actions=sum(counts), modeled_co2_g=None, modeled_pm25_ug=None))
