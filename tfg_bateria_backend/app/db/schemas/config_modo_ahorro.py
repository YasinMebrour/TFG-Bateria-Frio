# schemas/config_modo_ahorro.py
from pydantic import BaseModel, ConfigDict

class ConfigModoAhorroBase(BaseModel):
    modo_ahorro_activo: str  # 'manual' | 'optimizado'

class ConfigModoAhorroCreate(ConfigModoAhorroBase):
    pass

class ConfigModoAhorroRead(ConfigModoAhorroBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
