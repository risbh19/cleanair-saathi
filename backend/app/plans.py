"""Persist the first plan generated for a household, Delhi date and data mode."""
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict

from .engine.commute import Comparison, Leg, calculate_comparison
from .households import private_response, session_digest, transaction

router = APIRouter(prefix="/plan", tags=["Plans"], dependencies=[Depends(private_response)])


def commute_example(db, profile):
    examples = {"car": "petrol_hatchback_lt1000cc", "two_wheeler": "scooter_lt110cc"}
    for member in profile["members"]:
        for trip in member["commutes"]:
            mode = examples.get(trip["mode"])
            if mode:
                scenario = Comparison(distance_km=trip["distance_km"], baseline=Leg(mode=mode),
                                      alternative=Leg(mode="intracity_bus"))
                return calculate_comparison(db, scenario)
    return None


def load_or_create(profile, day, mode, generate):
    with transaction() as db:
        # Serialize first reads for this household and exclude concurrent deletion.
        if db.execute("SELECT id FROM households WHERE id = %s FOR UPDATE", (profile["id"],)).fetchone() is None:
            raise HTTPException(404, "Household not found")
        row = db.execute("""SELECT id, band_used, as_of FROM daily_plans
                            WHERE household_id = %s AND plan_date = %s AND data_mode = %s""",
                         (profile["id"], day, mode)).fetchone()
        if row is None:
            band, as_of, actions = generate()
            row = db.execute("""INSERT INTO daily_plans (household_id, plan_date, data_mode, band_used, as_of)
                                VALUES (%s,%s,%s,%s,%s) RETURNING id, band_used, as_of""",
                             (profile["id"], day, mode, band, as_of)).fetchone()
            for position, action in enumerate(actions):
                if action["id"] == "compare_motor_trip":
                    example = commute_example(db, profile)
                    if example is not None:
                        action = {**action, "commute_example": example}
                db.execute("INSERT INTO plan_items (id, plan_id, position, card) VALUES (%s,%s,%s,%s)",
                           (uuid4(), row[0], position, Jsonb(action)))
        items = db.execute("SELECT id, card, status FROM plan_items WHERE plan_id = %s ORDER BY position",
                           (row[0],)).fetchall()
        return {"plan_date": day, "data_mode": mode, "band_used": row[1], "as_of": row[2],
                "actions": [{**card, "item_id": item_id, "status": status} for item_id, card, status in items]}


class Progress(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["planned", "done", "skipped"]


@router.post("/items/{item_id}/status")
def set_status(item_id: UUID, progress: Progress, digest: bytes = Depends(session_digest)):
    with transaction() as db:
        row = db.execute("""UPDATE plan_items AS i SET status = %s
                            FROM daily_plans AS p JOIN households AS h ON h.id = p.household_id
                            WHERE i.plan_id = p.id AND i.id = %s AND h.session_digest = %s
                            RETURNING i.id, i.status""", (progress.status, item_id, digest)).fetchone()
        if row is None:
            raise HTTPException(404, "Plan item not found")
        return {"item_id": row[0], "status": row[1]}
