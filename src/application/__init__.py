"""Capa de aplicación — puertos (ABCs) y casos de uso.

Depende solo de la capa de dominio. Define qué puede hacer el sistema
sin comprometerse con tecnologías concretas (Excel, pandas, ML, etc.).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

from src.domain import (
    Equipo,
    EstadoEquipo,
    Muestra,
    Prediccion,
    Semaforo,
    SemaforoService,
)


# =====================================================================
# Puertos (interfaces)
# =====================================================================
class IEquipoRepository(ABC):
    """Acceso a equipos e historiales."""

    @abstractmethod
    def listar_ids(self) -> List[str]: ...

    @abstractmethod
    def obtener(self, equipo_id: str) -> Equipo: ...

    @abstractmethod
    def obtener_todos(self) -> List[Equipo]: ...


class IMuestraRepository(ABC):
    """Registro de nuevas muestras."""

    @abstractmethod
    def registrar(self, muestra: Muestra) -> None: ...


class IPredictor(ABC):
    """Dado un equipo (con su historial) devuelve una Prediccion completa."""

    @abstractmethod
    def predecir(self, equipo: Equipo) -> Prediccion: ...


# =====================================================================
# DTOs de aplicación
# =====================================================================
@dataclass
class ResumenEquipo:
    equipo: str
    semaforo: Semaforo
    estado_modelo: EstadoEquipo
    horas_actuales: float
    horas_hasta_critico: Optional[float]
    ultima_muestra_fecha: Optional[date]
    total_muestras: int
    historia_suficiente: bool = True
    horas_htc_confiable: bool = True


@dataclass
class ResumenFlota:
    total_equipos: int
    criticos: int
    precaucion: int
    normales: int
    equipos: List[ResumenEquipo]


@dataclass
class NuevaMuestraDTO:
    fecha: date
    hora_producto: float
    valores: Dict[str, float]           # {nombre_variable: valor}
    estado: Optional[EstadoEquipo] = None


# =====================================================================
# Casos de uso
# =====================================================================
class PredecirEquipoUseCase:
    def __init__(self, repo: IEquipoRepository, predictor: IPredictor) -> None:
        self.repo = repo
        self.predictor = predictor

    def execute(self, equipo_id: str) -> Prediccion:
        equipo = self.repo.obtener(equipo_id)
        return self.predictor.predecir(equipo)


class ObtenerHistorialUseCase:
    def __init__(self, repo: IEquipoRepository) -> None:
        self.repo = repo

    def execute(self, equipo_id: str) -> Equipo:
        return self.repo.obtener(equipo_id)


class ListarEquiposUseCase:
    def __init__(self, repo: IEquipoRepository) -> None:
        self.repo = repo

    def execute(self) -> List[str]:
        return self.repo.listar_ids()


class ObtenerResumenFlotaUseCase:
    """Agrega el estado actual de cada equipo en una sola foto de la flota."""

    def __init__(self, repo: IEquipoRepository, predictor: IPredictor) -> None:
        self.repo = repo
        self.predictor = predictor

    def execute(self) -> ResumenFlota:
        equipos = self.repo.obtener_todos()
        resumenes: List[ResumenEquipo] = []
        c = p = n = 0

        for equipo in equipos:
            try:
                pred = self.predictor.predecir(equipo)
            except Exception:
                # Historial insuficiente → saltar sin romper la flota
                continue

            resumenes.append(
                ResumenEquipo(
                    equipo=equipo.id,
                    semaforo=pred.semaforo,
                    estado_modelo=pred.estado_modelo,
                    horas_actuales=pred.horas_actuales,
                    horas_hasta_critico=pred.horas_hasta_critico,
                    ultima_muestra_fecha=pred.ultima_muestra_fecha,
                    total_muestras=equipo.total_muestras,
                    historia_suficiente=pred.historia_suficiente,
                    horas_htc_confiable=pred.horas_htc_confiable,
                )
            )
            if pred.semaforo == Semaforo.ROJO:
                c += 1
            elif pred.semaforo == Semaforo.AMARILLO:
                p += 1
            else:
                n += 1

        # Ordenar: ROJO → AMARILLO → VERDE, luego por horas_actuales desc
        orden = {Semaforo.ROJO: 0, Semaforo.AMARILLO: 1, Semaforo.VERDE: 2}
        resumenes.sort(key=lambda r: (orden[r.semaforo], -r.horas_actuales))

        return ResumenFlota(
            total_equipos=len(resumenes),
            criticos=c,
            precaucion=p,
            normales=n,
            equipos=resumenes,
        )


class RegistrarMuestraUseCase:
    """Graba una nueva muestra en el Excel y devuelve la predicción inmediata."""

    def __init__(
        self,
        equipo_repo: IEquipoRepository,
        muestra_repo: IMuestraRepository,
        predictor: IPredictor,
    ) -> None:
        self.equipo_repo = equipo_repo
        self.muestra_repo = muestra_repo
        self.predictor = predictor

    def execute(self, equipo_id: str, nueva: NuevaMuestraDTO) -> Prediccion:
        muestra = Muestra(
            equipo=equipo_id,
            fecha=nueva.fecha,
            hora_producto=nueva.hora_producto,
            estado=nueva.estado,
            variables=dict(nueva.valores),
        )
        self.muestra_repo.registrar(muestra)
        equipo = self.equipo_repo.obtener(equipo_id)
        return self.predictor.predecir(equipo)
