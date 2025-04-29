
from fastapi import HTTPException, status

async def email_already_registered_exception() -> None:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Email already registered"
    )

async def role_not_found_exception(role_name: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Role '{role_name}' not found"
    )
async def status_not_found_exception(status_name: str) -> None:
    raise HTTPException(
        status_code=404,
        detail=f"Status '{status_name}' not found"
    )
