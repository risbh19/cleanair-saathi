"""One anonymous household per client-generated bearer token."""
from contextlib import contextmanager
from hashlib import sha256
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg import OperationalError
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field

from backend.db.migrate import connect


class ProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class Commute(ProfileInput):
    mode: Literal["walk", "cycle", "bus", "metro", "car", "two_wheeler", "auto"]
    distance_km: float = Field(gt=0, le=500)
    depart_time: str = Field(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
    return_time: str = Field(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")


class Member(ProfileInput):
    age_band: Literal["child", "teen", "adult", "older_adult"]
    sensitive: bool
    commutes: list[Commute] = Field(default_factory=list, max_length=10)


class Household(ProfileInput):
    lat: float = Field(ge=28.5, le=28.8)
    lon: float = Field(ge=77.0, le=77.4)
    locality: str = Field(min_length=1, max_length=80)
    home_type: Literal["flat", "independent_house", "other"]
    room_area_m2: float = Field(gt=0, le=1000)
    ceiling_m: float = Field(gt=0, le=20)
    windows_leaky: bool
    purifier_cadr_m3h: float = Field(ge=0, le=5000)
    cooking_fuel: Literal["lpg", "png", "electric", "biomass", "other"]
    budget_band: Literal["low", "medium", "high"]
    members: list[Member] = Field(min_length=1, max_length=30)


class SavedHousehold(Household):
    id: UUID


def session_digest(auth: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False))):
    try:
        token = UUID(auth.credentials if auth else "")
        if token.version != 4:
            raise ValueError
    except ValueError:
        raise HTTPException(401, "A random UUIDv4 bearer token is required",
                            headers={"WWW-Authenticate": "Bearer"}) from None
    return sha256(token.bytes).digest()


def private_response(response: Response):
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(prefix="/households", tags=["Households"], dependencies=[Depends(private_response)])


@contextmanager
def transaction():
    try:
        with connect() as db:
            yield db
    except OperationalError:
        raise HTTPException(503, "Household storage unavailable") from None


@router.post("", response_model=SavedHousehold)
def save(profile: Household, digest: bytes = Depends(session_digest)):
    home = profile.model_dump(exclude={"members"})
    home.update(lat=round(profile.lat, 2), lon=round(profile.lon, 2))
    with transaction() as db:
        household_id, = db.execute(
            """INSERT INTO households (id, session_digest, home) VALUES (%s, %s, %s)
               ON CONFLICT (session_digest) DO UPDATE SET home = EXCLUDED.home
               RETURNING id""", (uuid4(), digest, Jsonb(home))
        ).fetchone()
        db.execute("DELETE FROM members WHERE household_id = %s", (household_id,))
        for index, member in enumerate(profile.members):
            db.execute("INSERT INTO members VALUES (%s, %s, %s, %s)",
                       (household_id, index, member.age_band, member.sensitive))
            for pos, trip in enumerate(member.commutes):
                db.execute("INSERT INTO commutes VALUES (%s, %s, %s, %s)",
                           (household_id, index, pos, Jsonb(trip.model_dump())))
    return {**home, "id": household_id, "members": profile.members}


@router.get("/me", response_model=SavedHousehold)
def reload_profile(digest: bytes = Depends(session_digest)):
    with transaction() as db:
        row = db.execute("SELECT id, home FROM households WHERE session_digest = %s FOR SHARE",
                         (digest,)).fetchone()
        if row is None:
            raise HTTPException(404, "Household not found")
        household_id, home = row
        members = [
            {"age_band": age, "sensitive": sensitive, "commutes": []}
            for age, sensitive in db.execute(
                "SELECT age_band, sensitive FROM members WHERE household_id = %s ORDER BY position",
                (household_id,))
        ]
        for index, trip in db.execute(
            """SELECT member_position, journey FROM commutes WHERE household_id = %s
               ORDER BY member_position, position""", (household_id,)
        ):
            members[index]["commutes"].append(trip)
    return {**home, "id": household_id, "members": members}


@router.delete("/{household_id}", status_code=204)
def delete(household_id: UUID, digest: bytes = Depends(session_digest)):
    with transaction() as db:
        result = db.execute("DELETE FROM households WHERE id = %s AND session_digest = %s",
                            (household_id, digest))
        if result.rowcount == 0:
            raise HTTPException(404, "Household not found")
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
