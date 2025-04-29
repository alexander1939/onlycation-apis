
from fastapi import HTTPException, status

async def email_already_registered_exception() -> None:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Error registering email, please try another email."
    )

async def role_not_found_exception(role_name: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"An error occurred during registration."
    )
async def status_not_found_exception(status_name: str) -> None:
    raise HTTPException(
        status_code=404,
        detail=f"An error occurred during registration."
    )

async def unexpected_exception() -> None:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An internal error occurred. Please try again later."
    )