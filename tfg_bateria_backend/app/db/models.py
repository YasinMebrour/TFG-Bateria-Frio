# db/models.py
from sqlalchemy import Column, Integer, ForeignKey, String, Float, DateTime, Date,  Boolean, UniqueConstraint, Enum as SqEnum
from sqlalchemy import Column, Integer, SmallInteger, Float, Boolean, JSON
from .database import Base
from sqlalchemy import Enum as SqEnum
from enum import Enum as PyEnum
from sqlalchemy.orm import relationship
from sqlalchemy.types import Time
from datetime import datetime

class ConsumoReal(Base):
    __tablename__ = "consumo_real"
    id = Column(Integer, primary_key=True, index=True)
    hora = Column(DateTime, index=True, nullable=False)
    consumo = Column(Float, nullable=False)

class PrediccionMean(Base):
    __tablename__ = "prediccion_mean"
    id = Column(Integer, primary_key=True, index=True)
    hora = Column(DateTime, index=True, nullable=False)
    coste_eur = Column(Float, nullable=False)

class PrediccionXGBoost(Base):
    __tablename__ = "prediccion_xgboost"
    id = Column(Integer, primary_key=True, index=True)
    hora = Column(DateTime, index=True, nullable=False)
    consumo = Column(Float, nullable=False)

class PrediccionInteligente(Base):
    __tablename__ = "prediccion_inteligente"
    id = Column(Integer, primary_key=True, index=True)
    hora = Column(DateTime, index=True, nullable=False)
    coste_eur = Column(Float, nullable=False)

#################################################
# Peajes Configuracion

class ConfigTarifa(Base):
    __tablename__ = "tarifa_config"
    id       = Column(Integer, primary_key=True)
    month    = Column(Integer, nullable=True)     
    day_type = Column(String,  nullable=False)     
    hour     = Column(Integer, nullable=False)     
    tarifa   = Column(String,  nullable=False)     

class Festivo(Base):
    __tablename__ = "festivos"
    fecha = Column(Date, primary_key=True)
    nombre = Column(String, nullable=True)

class Peaje(Base):
    __tablename__ = "peajes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String, nullable=False)
    peaje = Column(Float, nullable=False)

#################################################
# Configuración Usuarios

class RoleEnum(PyEnum):
    visualizar = "visualizar"
    editar = "editar"

class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        UniqueConstraint("nombre", name="uq_usuario_nombre"),
        UniqueConstraint("email",  name="uq_usuario_email"),
    )

    id            = Column(Integer, primary_key=True, autoincrement=True)
    nombre        = Column(String(150), nullable=False)
    email         = Column(String(150), nullable=False, unique=True)
    password_hash = Column(String(128), nullable=False)
    is_editor     = Column(Boolean, nullable=False, default=False)
    telegram_chat_id = Column(String(50), nullable=True)
    telegram_notify  = Column(Boolean, nullable=False, default=False)
    telegram_bot_token = Column(String(120), nullable=True)

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    token      = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("Usuario", back_populates="reset_tokens")

# añade en Usuario:
Usuario.reset_tokens = relationship(
    "PasswordResetToken",
    back_populates="user",
    cascade="all, delete-orphan",
)


#################################################
#  Planificaciones
#################################################

class OrigenPlan(PyEnum):
    real = "real"       
    opt  = "opt"  
    establecida = "establecida"   

class PlanificacionSemanal(Base):
    __tablename__ = "planificacion_semanal"

    id          = Column(Integer, primary_key=True)
    dia_semana  = Column(SmallInteger, nullable=False)        
    hora_inicio = Column(Time,        nullable=True)
    hora_fin    = Column(Time,        nullable=True)
    modo_ahorro = Column(Boolean, nullable=False, default=False)  

    __table_args__ = (
        UniqueConstraint(
            "dia_semana", "hora_inicio", "hora_fin", "modo_ahorro",
            name="uq_semana_dia_intervalo_modo"
        ),
    )

class UltimoEstado(Base):
    __tablename__ = "ultimo_estado"

    id = Column(Integer, primary_key=True)

    modo_planif = Column(
        SqEnum("Optimizado", "Camara", "Gemelo", name="modo_planificacion"),
        nullable=False
    )

    actualizado_en = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )



class PlanificacionDiaria(Base):
    __tablename__ = "planificacion_diaria"

    id          = Column(Integer, primary_key=True)
    fecha       = Column(Date,  index=True, nullable=False)
    hora_inicio = Column(Time,  nullable=True)
    hora_fin    = Column(Time,  nullable=True)
    origen      = Column(SqEnum(OrigenPlan), nullable=False, default=OrigenPlan.real)
    modo_ahorro = Column(Boolean, nullable=False, default=False)  

    __table_args__ = (
        UniqueConstraint(
            "fecha", "hora_inicio", "hora_fin", "origen", "modo_ahorro",
            name="uq_diaria_fecha_intervalo_origen_modo"
        ),
    )



#################################################

class ConfigModoAhorro(Base):
    __tablename__ = "modo_ahorro_activo"

    id = Column(Integer, primary_key=True)
    modo_ahorro_activo = Column(String(150), nullable=False)

class Config(Base):
    __tablename__ = "config"

    id = Column(Integer, primary_key=True)
    banda_seguridad_temperatura = Column(Float, nullable=True, default=0.0)
    banda_seguridad_humedad = Column(Float, nullable=True, default=0.0)
    banda_condiciones_optimas = Column(Float, nullable=True, default=0.0)
    ahorro_energia_habilitado = Column(Boolean, default=True)
    rangos_ahorro = Column(Integer, nullable=True)
    horas_modo_ahorro = Column(Float, nullable=True)
    horas_max_ahorro = Column(Integer, nullable=True)
    horas_max_entre_ahorro = Column(Float, nullable=True)
    hora_envio_planificacion = Column(Time, nullable=True) 

    dias_ahorro = Column(
        JSON, 
        nullable=False, 
        default=lambda: {
            "lunes": True, "martes": True, "miercoles": True,
            "jueves": True, "viernes": True, "sabado": False, "domingo": False
        }
    )
   

class EventoCritico(Base):
    __tablename__ = "eventos_criticos"

    id           = Column(Integer, primary_key=True)
    fecha        = Column(DateTime, nullable=False)
    tipo         = Column(String(50), nullable=False)      # “crítico”, “alto”, etc.
    descripcion  = Column(String(255), nullable=True)


class EventRule(Base):
    """Reglas para generar eventos automáticamente."""

    __tablename__ = "event_rules"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(String(255), nullable=True)
    measurement = Column(String(100), nullable=False)
    field = Column(String(100), nullable=False)
    operador = Column(String(20), nullable=False)
    valor_derecho = Column(String(100), nullable=False)
    tipo_condicion = Column(String(50), nullable=False)
    ventana_segundos = Column(Integer, nullable=False)
    frecuencia_segundos = Column(Integer, nullable=False)
    habilitada = Column(Boolean, default=True)


# Al final del fichero:
__all__ = [
    "ConsumoReal",
    "PrediccionMean",
    "PrediccionXGBoost",
    "PrediccionInteligente",
    "PreciosLuz",
    "Humedad",
    "Temperatura",
    "Consumo",
    "ModoAhorro",
    "Festivo",
    "ConfigTarifa",
    "Peaje",
    "Usuario",
    "ConfigModoAhorro",
    "EventoCritico",
    "EventRule",
    "Config",
    "PlanificacionSemanal",
    "PlanificacionDiaria",
    "UltimoEstado",
]

