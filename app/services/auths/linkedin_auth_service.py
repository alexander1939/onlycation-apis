from typing import Dict, Any, Optional
import httpx
import logging
import urllib.parse
import secrets
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

from app.configs.settings import settings
from app.models.users.user import User
from app.models import Role, Status
from app.schemas.auths.auth_schema import Token, UserInDB, OAuthUserCreate, UserResponse, LoginResponse
from app.cores.security import get_password_hash, verify_password

# Configure logging
logger = logging.getLogger(__name__)

class LinkedInAuthService:
    """Service for handling LinkedIn OAuth2 authentication."""
    
    def __init__(self):
        """Initialize LinkedIn OAuth service with configuration from settings."""
        self.client_id = settings.LINKEDIN_CLIENT_ID
        self.client_secret = settings.LINKEDIN_CLIENT_SECRET
        self.redirect_uri = settings.LINKEDIN_REDIRECT_URI
        self.token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        self.user_info_url = "https://api.linkedin.com/v2/me"
        self.userinfo_oidc_url = "https://api.linkedin.com/v2/userinfo"
        self.email_url = "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))"

    def get_authorization_url(self, state: str | None = None) -> Dict[str, str]:
        """
        Generate LinkedIn OAuth2 authorization URL with required scopes.
        
        Returns:
            Dict[str, str]: Dictionary containing the authorization URL
            
        Raises:
            HTTPException: If LinkedIn OAuth is not properly configured
        """
        if not self.client_id or not self.redirect_uri:
            logger.error("LinkedIn OAuth not properly configured - missing client_id or redirect_uri")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="LinkedIn OAuth is not properly configured"
            )
            
        # Use OpenID Connect scopes per requirement
        scope = "openid profile email"
        # Allow caller to pass a specific state (e.g., register:student). Default to a static string for now.
        state = state or "random_string_for_csrf"
        
        # URL-encode redirect_uri and scope to satisfy LinkedIn requirements
        encoded_redirect = urllib.parse.quote(self.redirect_uri, safe="")
        encoded_scope = urllib.parse.quote(scope)

        auth_url = (
            "https://www.linkedin.com/oauth/v2/authorization"
            f"?response_type=code"
            f"&client_id={self.client_id}"
            f"&redirect_uri={encoded_redirect}"
            f"&scope={encoded_scope}"
            f"&state={state}"
        )
        
        return {"authorization_url": auth_url}

    def _role_id_for_key(self, role_key: str) -> int:
        """Map a logical role key to a database Role.id.
        teacher -> 2, student -> 3
        """
        return 2 if role_key == "teacher" else 3

    async def _resolve_role(self, db: AsyncSession, role_key: str) -> Role:
        """Resolve a role by fixed ID first, then by multilingual names.
        This avoids environment differences (IDs or localized names).
        """
        # 1) Try by fixed ID mapping
        desired_role_id = self._role_id_for_key(role_key)
        result = await db.execute(select(Role).where(Role.id == desired_role_id))
        role = result.scalar_one_or_none()
        if role:
            logger.info(f"Resolved role by ID {desired_role_id}: {role.name}")
            return role

        # 2) Fallback by possible names
        possible_names = [role_key]
        if role_key == "teacher":
            possible_names += ["docente", "profesor"]
        elif role_key == "student":
            possible_names += ["estudiante", "alumno"]

        result = await db.execute(select(Role).where(Role.name.in_(possible_names)))
        role = result.scalar_one_or_none()
        if role:
            logger.info(f"Resolved role by name: {role.name}")
            return role

        logger.error(f"Unable to resolve role for key '{role_key}' using IDs or names {possible_names}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Role not found for requested type: {role_key}")

    async def get_access_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.
        
        Args:
            code: The authorization code from LinkedIn callback
            
        Returns:
            Dict containing access token and related info
            
        Raises:
            HTTPException: If token exchange fails
        """
        if not code:
            logger.error("No authorization code provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code is required"
            )
            
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url, 
                    data=data, 
                    headers=headers,
                    timeout=10.0
                )
                
                response.raise_for_status()
                token_data = response.json()
                
                if not token_data.get("access_token"):
                    logger.error("No access token in LinkedIn response")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No access token in LinkedIn response"
                    )
                    
                return token_data
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting LinkedIn access token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get access token from LinkedIn: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error getting LinkedIn access token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while authenticating with LinkedIn"
            )

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get user profile and email from LinkedIn API.
        
        Args:
            access_token: Valid LinkedIn access token
            
        Returns:
            Dict containing user information (email, first_name, last_name, etc.)
            
        Raises:
            HTTPException: If user info retrieval fails
        """
        if not access_token:
            logger.error("No access token provided for user info request")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access token is required"
            )
            
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                # First try OpenID Connect userinfo endpoint (works with 'openid profile email' scope)
                try:
                    oidc_resp = await client.get(
                        self.userinfo_oidc_url,
                        headers={"Authorization": f"Bearer {access_token}"},
                        timeout=10.0
                    )
                    if oidc_resp.status_code == 200:
                        oidc = oidc_resp.json()
                        email = oidc.get("email") or oidc.get("email_verified") and oidc.get("email")
                        first_name = oidc.get("given_name", "")
                        last_name = oidc.get("family_name", "")
                        profile_picture = oidc.get("picture")
                        oauth_id = oidc.get("sub")

                        if not email:
                            logger.warning("OIDC userinfo missing email, will fallback to legacy endpoints")
                        else:
                            return {
                                "email": email,
                                "first_name": first_name,
                                "last_name": last_name,
                                "profile_picture": profile_picture,
                                "is_verified": True,
                                "oauth_provider": "linkedin",
                                "oauth_id": oauth_id,
                            }
                except Exception as _:
                    # Fall back to legacy endpoints if OIDC userinfo fails
                    pass

                # Legacy v2 endpoints fallback (requires r_liteprofile and r_emailaddress)
                profile_response = await client.get(
                    self.user_info_url,
                    headers=headers,
                    timeout=10.0
                )
                profile_response.raise_for_status()
                profile_data = profile_response.json()

                email_response = await client.get(
                    self.email_url,
                    headers=headers,
                    timeout=10.0
                )
                email_response.raise_for_status()
                email_data = email_response.json()

                email = None
                if email_data.get("elements") and len(email_data["elements"]) > 0:
                    email = email_data["elements"][0].get("handle~", {}).get("emailAddress")

                if not email:
                    logger.error("No email found in LinkedIn profile")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email is required but not provided by LinkedIn"
                    )

                first_name = profile_data.get("localizedFirstName", "")
                last_name = profile_data.get("localizedLastName", "")

                profile_picture = None
                if "profilePicture" in profile_data and "displayImage~" in profile_data["profilePicture"]:
                    display_image = profile_data["profilePicture"]["displayImage~"]
                    if "elements" in display_image and len(display_image["elements"]) > 0:
                        profile_picture = display_image["elements"][-1].get("identifiers", [{}])[0].get("identifier")

                return {
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "profile_picture": profile_picture,
                    "is_verified": True,  # LinkedIn verifies emails
                    "oauth_provider": "linkedin",
                    "oauth_id": profile_data.get("id")
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting LinkedIn user info: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get user info from LinkedIn: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error getting LinkedIn user info: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while fetching your LinkedIn profile"
            )

    async def find_or_create_user(self, db: AsyncSession, user_info: Dict[str, Any]) -> User:
        """
        Find an existing user by email or create a new one with LinkedIn OAuth info.
        
        Args:
            db: Database session
            user_info: Dictionary containing user information from LinkedIn
            
        Returns:
            User: The found or created user
            
        Raises:
            HTTPException: If user creation fails or database error occurs
        """
        if not user_info or not user_info.get("email"):
            logger.error("No user info or email provided for user lookup/creation")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user information provided"
            )
            
        email = user_info["email"]
        oauth_id = user_info.get("oauth_id")
        
        try:
            # Try to find existing user by email
            result = await db.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()

            if user:
                # Ensure privacy policy accepted is always True
                if user.privacy_policy_accepted is not True:
                    user.privacy_policy_accepted = True
                    await db.commit()
                    await db.refresh(user)
                return user

            # No default auto-creation here. Force explicit registration.
            logger.info("LinkedIn user not found in DB during login-only flow. Prompting registration.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "User not found. Please register with LinkedIn.",
                    "register_student": "/api/auth/linkedin/register/student",
                    "register_teacher": "/api/auth/linkedin/register/teacher",
                },
            )
                
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Database error in find_or_create_user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while processing your request"
            )
        except Exception as e:
            await db.rollback()
            logger.error(f"Unexpected error in find_or_create_user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred"
            )

    async def create_user_with_role(self, db: AsyncSession, user_info: Dict[str, Any], role_name: str, status_name: str = "active") -> User:
        """
        Create a new user with a specific role and status using LinkedIn user info.
        Does NOT log the user in; just creates and returns the user.
        """
        if not user_info or not user_info.get("email"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user information provided")

        email = user_info["email"]

        try:
            # Ensure user does not already exist
            result = await db.execute(select(User).where(User.email == email))
            existing = result.scalar_one_or_none()
            if existing:
                # STRICT: resolve requested role by exact name
                role_result = await db.execute(select(Role).where(Role.name == role_name))
                desired_role = role_result.scalar_one_or_none()
                if not desired_role:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Role '{role_name}' not found")

                # If existing user has a different role, update to requested role and status
                if not existing.role or existing.role.name != desired_role.name:
                    status_result = await db.execute(select(Status).where(Status.name == status_name))
                    status_obj = status_result.scalar_one_or_none()
                    if not status_obj:
                        raise HTTPException(status_code=500, detail=f"Status '{status_name}' not found")

                    existing.role = desired_role
                    existing.status = status_obj
                    await db.commit()
                    await db.refresh(existing)
                    logger.info(f"Updated existing user {existing.email} to role={existing.role.name} status={existing.status.name}")
                return existing

            # STRICT: resolve requested role by exact name
            role_result = await db.execute(select(Role).where(Role.name == role_name))
            role = role_result.scalar_one_or_none()
            if not role:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Role '{role_name}' not found")

            # Get status
            status_result = await db.execute(select(Status).where(Status.name == status_name))
            status_obj = status_result.scalar_one_or_none()
            if not status_obj:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Status '{status_name}' not found")

            # Create user
            user = User(
                email=email,
                first_name=user_info.get("first_name", ""),
                last_name=user_info.get("last_name", ""),
                privacy_policy_accepted=True,
                role=role,
                status=status_obj,
                password=get_password_hash(secrets.token_urlsafe(16)),
            )

            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info(f"Created user {user.email} with role={user.role.name} status={user.status.name}")
            return user

        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Database error in create_user_with_role: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred while creating the user")
        except Exception as e:
            await db.rollback()
            logger.error(f"Unexpected error in create_user_with_role: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")

# Create a singleton instance of the LinkedInAuthService
linkedin_auth = LinkedInAuthService()
