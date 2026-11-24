"""Seven Delhi calendar dates of completed items, separated by data mode."""
from datetime import datetime, timedelta, timezone

from hashlib import sha256

from pydantic import BaseModel, Field, UUID4
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


class SchoolRun(BaseModel):
    group_code: UUID4
    departure: str = Field(pattern=r"^(?:[01][0-9]|2[0-3]):(?:00|15|30|45)$")


@router.post("/community/school-run")
def join_run(offer: SchoolRun, profile=Depends(reload_profile)):
    """Opt-in matching inside an adult-organized group; return only an overlap flag."""
    _, today = window()
    household = profile["id"]
    group = sha256(offer.group_code.bytes).digest()
    hour, minute = map(int, offer.departure.split(":"))
    slot = 4 * hour + minute // 15
    with transaction() as db:
        db.execute("DELETE FROM school_run_offers WHERE expires_on < %s", (today,))
        db.execute("""INSERT INTO school_run_offers VALUES (%s,%s,lower(btrim(%s)),%s,%s)
            ON CONFLICT (household_id) DO UPDATE SET group_digest=EXCLUDED.group_digest,
            locality_key=EXCLUDED.locality_key, departure_slot=EXCLUDED.departure_slot,
            expires_on=EXCLUDED.expires_on""", (household, group, profile["locality"], slot, today + timedelta(days=6)))
        matched = db.execute("""SELECT EXISTS (SELECT FROM school_run_offers
            WHERE group_digest=%s AND household_id<>%s AND locality_key=lower(btrim(%s))
            AND departure_slot=%s AND expires_on >= %s)""", (group, household, profile["locality"], slot, today)).fetchone()[0]
    return {"matched": matched, "expires_on": today + timedelta(days=6)}


@router.delete("/community/school-run", status_code=204)
def leave_run(profile=Depends(reload_profile)):
    with transaction() as db:
        db.execute("DELETE FROM school_run_offers WHERE household_id=%s", (profile["id"],))
