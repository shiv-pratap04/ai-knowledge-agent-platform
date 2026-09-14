from fastapi import APIRouter, HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.security import create_access_token

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TEST_USERNAME = "testuser"
TEST_PASSWORD_HASH = pwd_context.hash("testpass123")


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginRequest):
    if body.username != TEST_USERNAME or not pwd_context.verify(body.password, TEST_PASSWORD_HASH):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    access_token = create_access_token({"sub": body.username})
    return {"access_token": access_token, "token_type": "bearer"}
