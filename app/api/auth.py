import psycopg2
from fastapi import APIRouter, HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.security import create_access_token
from db.connection import DatabaseError, get_db_connection

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class LoginRequest(BaseModel):
    username: str
    password: str


class SignupRequest(BaseModel):
    username: str
    password: str
    org_name: str | None = None
    invite_code: str | None = None


def _auth_error():
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password",
    )


@router.post("/signup")
def signup(body: SignupRequest):
    if bool(body.org_name) == bool(body.invite_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide exactly one of org_name or invite_code.",
        )
    if len(body.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters.",
        )

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                if body.org_name:
                    cur.execute(
                        """
                        INSERT INTO organizations (name, invite_code)
                        VALUES (%s, gen_random_uuid()::text)
                        RETURNING id
                        """,
                        (body.org_name,),
                    )
                    org_id = cur.fetchone()[0]
                    role = "admin"
                else:
                    cur.execute(
                        "SELECT id FROM organizations WHERE invite_code = %s",
                        (body.invite_code,),
                    )
                    organization = cur.fetchone()
                    if not organization:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid invite code.",
                        )
                    org_id = organization[0]
                    role = "member"

                cur.execute(
                    """
                    INSERT INTO users (username, password_hash, org_id, role)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (body.username, pwd_context.hash(body.password), org_id, role),
                )
    except HTTPException:
        raise
    except psycopg2.errors.UniqueViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or organization name already exists.",
        ) from exc
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to Postgres.",
        ) from exc

    return {"username": body.username, "org_id": str(org_id), "role": role}


@router.post("/login")
def login(body: LoginRequest):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT password_hash, org_id, role FROM users WHERE username = %s",
                (body.username,),
            )
            user = cur.fetchone()
    finally:
        conn.close()

    if not user or not pwd_context.verify(body.password, user[0]):
        raise _auth_error()

    access_token = create_access_token(
        {
            "sub": body.username,
            "org_id": str(user[1]),
            "role": user[2],
        }
    )
    return {"access_token": access_token, "token_type": "bearer"}
