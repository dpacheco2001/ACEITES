"""Capa de dominio — entidades, value objects y servicios puros.

Esta capa NO importa nada del proyecto. Toda la lógica aquí es pura Python.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Dict, List, Optional


# =====================================================================
# Value Objects
# =====================================================================
class EstadoEquipo(str, Enum):
    """Etiqueta del modelo clasificador."""
    NORMAL = "NORMAL"
    PRECAUCION = "PRECAUCION"
    CRITICO = "CRITICO"


class Semaforo(str, Enum):
    """Semáforo operacional presentado al ingeniero."""
    VERDE = "VERDE"
    AMARILLO = "AMARILLO"
    ROJO = "ROJO"


# =====================================================================
# Entidades
# =====================================================================
@dataclass
class Muestra:
    """Una muestra de aceite en un instante determinado."""
    equipo: str
    fecha: date
    hora_producto: float
    estado: Optional[EstadoEquipo] = None
    variables: Dict[str, float] = field(default_factory=dict)


@dataclass
class Equipo:
    """Un camión y su historial ordenado por Hora_Producto."""
    id: str
    muestras: List[Muestra] = field(default_factory=list)

    @property
    def total_muestras(self) -> int:
        return len(self.muestras)

    @property
    def ultima_muestra(self) -> Optional[Muestra]:
        return self.muestras[-1] if self.muestras else None


@dataclass
class Prediccion:
    """Resultado de la inferencia para un equipo."""
    equipo: str
    semaforo: Semaforo
    estado_modelo: EstadoEquipo
    horas_actuales: float
    horas_hasta_critico: Optional[float]
    predicciones_t1: Dict[str, float]
    variables_baja_confianza: List[str]
    ultima_muestra_fecha: Optional[date]
    # Flags de confianza — ayudan al frontend a diferenciar predicciones
    # "defendibles" de las que tienen historia insuficiente o están fuera
    # del rango validado del Modelo C.
    historia_suficiente: bool = True
    horas_htc_confiable: bool = True
    advertencias: List[str] = field(default_factory=list)


# =====================================================================
# Servicios de dominio
# =====================================================================
class SemaforoService:
    """Encapsula la lógica del semáforo (Sección 5 de la guía, validada con datos reales)."""

    def __init__(
        self,
        horas_umbral_rojo: float = 400,
        horas_umbral_amarillo: float = 300,
        horas_hasta_critico_rojo: float = 50,
        horas_hasta_critico_amarillo: float = 150,
    ) -> None:
        self.horas_umbral_rojo = horas_umbral_rojo
        self.horas_umbral_amarillo = horas_umbral_amarillo
        self.horas_hasta_critico_rojo = horas_hasta_critico_rojo
        self.horas_hasta_critico_amarillo = horas_hasta_critico_amarillo

    def calcular(
        self,
        estado_modelo: EstadoEquipo,
        horas_actuales: float,
        horas_hasta_critico: Optional[float],
    ) -> Semaforo:
        # ROJO: cualquiera de estas condiciones
        if estado_modelo == EstadoEquipo.CRITICO:
            return Semaforo.ROJO
        if horas_actuales >= self.horas_umbral_rojo:
            return Semaforo.ROJO
        if (
            horas_hasta_critico is not None
            and horas_hasta_critico <= self.horas_hasta_critico_rojo
        ):
            return Semaforo.ROJO

        # AMARILLO: zona de precaución
        if estado_modelo == EstadoEquipo.PRECAUCION:
            return Semaforo.AMARILLO
        if horas_actuales >= self.horas_umbral_amarillo:
            return Semaforo.AMARILLO
        if (
            horas_hasta_critico is not None
            and horas_hasta_critico <= self.horas_hasta_critico_amarillo
        ):
            return Semaforo.AMARILLO

        return Semaforo.VERDE
