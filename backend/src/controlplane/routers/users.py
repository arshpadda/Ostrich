import uuid

from fastapi import APIRouter, Depends, HTTPException

from ..core.auth import get_current_user
from ..database.models import User
from ..database.schemas import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserRead, status_code=201)
async def create_user(user: UserCreate, current_user: dict = Depends(get_current_user)):
    firebase_uid = current_user.get("uid")

    # Check if a user with this firebase_uid already exists
    existing_user = await User.get_or_none(firebase_uid=firebase_uid)
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists for this Firebase identity")

    user_data = user.model_dump(exclude_unset=True)
    # Force the email to match the authenticated token if it's available
    if current_user.get("email"):
        user_data["email"] = current_user["email"]

    user_obj = await User.create(firebase_uid=firebase_uid, **user_data)
    return await UserRead.from_tortoise_orm(user_obj)


@router.get("/me", response_model=UserRead)
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """Convenience endpoint to get the authenticated user's profile."""
    user_obj = await User.get_or_none(firebase_uid=current_user.get("uid"))
    if not user_obj:
        raise HTTPException(status_code=404, detail="User profile not found")
    return await UserRead.from_tortoise_orm(user_obj)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: uuid.UUID, current_user: dict = Depends(get_current_user)):
    user_obj = await User.get_or_none(id=user_id)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")

    # Authorization check
    if user_obj.firebase_uid != current_user.get("uid"):
        raise HTTPException(status_code=403, detail="Not authorized to view this record")

    return await UserRead.from_tortoise_orm(user_obj)


@router.put("/{user_id}", response_model=UserRead)
async def update_user(user_id: uuid.UUID, user: UserUpdate, current_user: dict = Depends(get_current_user)):
    user_obj = await User.get_or_none(id=user_id)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")

    # Authorization check
    if user_obj.firebase_uid != current_user.get("uid"):
        raise HTTPException(status_code=403, detail="Not authorized to update this record")

    await user_obj.update_from_dict(user.model_dump(exclude_unset=True))
    await user_obj.save()
    return await UserRead.from_tortoise_orm(user_obj)


@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: uuid.UUID, current_user: dict = Depends(get_current_user)):
    user_obj = await User.get_or_none(id=user_id)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")

    # Authorization check
    if user_obj.firebase_uid != current_user.get("uid"):
        raise HTTPException(status_code=403, detail="Not authorized to delete this record")

    await user_obj.delete()
