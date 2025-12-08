from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    username: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class UserInput(UserBase):
    password: str


class UserOut(UserBase):
    id: int
    is_admin: bool = False
