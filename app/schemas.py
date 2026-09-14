from pydantic import BaseModel, EmailStr, ConfigDict

class UserCreate(BaseModel):
    """What the client sends us to register. """
    email: EmailStr
    password: str

class UserOut(BaseModel):
    """What we send back - notice there is no password field at all."""
    id: int
    email: EmailStr
    
    model_config = ConfigDict(from_attributes=True)
    