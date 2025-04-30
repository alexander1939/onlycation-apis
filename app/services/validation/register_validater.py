from fastapi import HTTPException, status
import re

async def validate_password(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    if not re.search(r'[A-Z]', password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one uppercase letter"
        )
    if not re.search(r'[a-z]', password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one lowercase letter"
        )
    if not re.search(r'[\W_]', password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one special character"
        )


async def validate_privacy_policy_accepted(true: bool)-> None:
    if not true:
        raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must accept the privacy notice to continue with your registration."
            )
    
async def validate_first_name(first_name: str)-> None:
    if len(first_name) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your first name must have at least 3 characters"
        )
    if len (first_name) > 25:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your first name must be less than 25 characters."
        )
    
async def validate_last_name(last_name: str)-> None:
    if len(last_name) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your last name must have at least 3 characters"
        )
    if len (last_name) > 25:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your last name must be less than 25 characters."
        )