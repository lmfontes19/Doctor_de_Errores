"""
Extractores de soluciones usando Strategy Pattern.

Este modulo implementa el patron Strategy para extraer soluciones
de diferentes formatos de datos del Knowledge Base, eliminando
la necesidad de multiples if/else anidados.
"""

from typing import List, Dict, Any
from abc import ABC, abstractmethod
from models import UserProfile


class SolutionExtractor(ABC):
    """
    Interfaz base para extractores de soluciones.

    Implementa el patron Strategy para diferentes formatos
    de datos de soluciones.
    """

    @abstractmethod
    def can_extract(self, solutions_data: Any) -> bool:
        """
        Verifica si este extractor puede manejar el formato de datos.

        Args:
            solutions_data: Datos de soluciones del KB

        Returns:
            True si puede extraer, False si no
        """

    @abstractmethod
    def extract(
        self,
        solutions_data: Any,
        user_profile: UserProfile
    ) -> List[str]:
        """
        Extrae las soluciones del formato de datos.

        Args:
            solutions_data: Datos de soluciones del KB
            user_profile: Perfil del usuario para personalizacion

        Returns:
            Lista de soluciones extraídas
        """


class NestedDictExtractor(SolutionExtractor):
    """
    Extractor para formato anidado: solutions[os][pm].

    Maneja estructuras como:
    {
        "linux": {"pip": [...], "conda": [...]},
        "windows": {"pip": [...], "conda": [...]}
    }
    """

    def can_extract(self, solutions_data: Any) -> bool:
        """Verifica si es un diccionario anidado."""
        if not isinstance(solutions_data, dict):
            return False

        return any(
            isinstance(v, dict)
            for v in solutions_data.values()
        )

    def extract(
        self,
        solutions_data: Dict[str, Any],
        user_profile: UserProfile
    ) -> List[str]:
        """Extrae soluciones del diccionario anidado."""
        os_key = user_profile.os.value
        pm_key = user_profile.package_manager.value

        os_solutions = solutions_data.get(os_key, {})

        if isinstance(os_solutions, dict):
            solutions = os_solutions.get(pm_key, [])

            if not solutions and os_solutions:
                solutions = next(iter(os_solutions.values()), [])
        else:
            solutions = os_solutions if isinstance(os_solutions, list) else []

        if not solutions and 'linux' in solutions_data:
            linux_solutions = solutions_data['linux']
            if isinstance(linux_solutions, dict):
                solutions = linux_solutions.get(pm_key, [])
                if not solutions:
                    solutions = next(iter(linux_solutions.values()), [])

        return solutions if isinstance(solutions, list) else []


class FlatDictExtractor(SolutionExtractor):
    """
    Extractor para formato plano: solutions[os] -> lista.

    Maneja estructuras como:
    {
        "linux": [...],
        "windows": [...],
        "macos": [...]
    }
    """

    def can_extract(self, solutions_data: Any) -> bool:
        """Verifica si es un diccionario plano con listas."""
        if not isinstance(solutions_data, dict):
            return False

        return any(
            isinstance(v, list)
            for v in solutions_data.values()
        )

    def extract(
        self,
        solutions_data: Dict[str, Any],
        user_profile: UserProfile
    ) -> List[str]:
        """Extrae soluciones del diccionario plano."""
        os_key = user_profile.os.value

        # Intentar obtener soluciones para el OS específico
        solutions = solutions_data.get(os_key, [])

        if not solutions and 'linux' in solutions_data:
            solutions = solutions_data['linux']

        if not solutions and solutions_data:
            solutions = next(iter(solutions_data.values()), [])

        return solutions if isinstance(solutions, list) else []


class ListExtractor(SolutionExtractor):
    """
    Extractor para formato simple: lista directa.

    Maneja estructuras como:
    ["solucion 1", "solucion 2", ...]
    """

    def can_extract(self, solutions_data: Any) -> bool:
        """Verifica si es una lista directa."""
        return isinstance(solutions_data, list)

    def extract(
        self,
        solutions_data: List[str],
        user_profile: UserProfile
    ) -> List[str]:
        """Retorna la lista directamente."""
        return solutions_data


class EmptyExtractor(SolutionExtractor):
    """
    Extractor fallback para datos vacíos o inválidos.
    """

    def can_extract(self, solutions_data: Any) -> bool:
        """Siempre puede "extraer" (retornando lista vacía)."""
        return True

    def extract(
        self,
        solutions_data: Any,
        user_profile: UserProfile
    ) -> List[str]:
        """Retorna lista vacía."""
        return []


class SolutionExtractionStrategy:
    """
    Contexto que usa diferentes estrategias de extraccion.

    Implementa Chain of Responsibility para intentar extractores
    en orden hasta encontrar uno compatible.
    """

    def __init__(self):
        """Inicializa con extractores en orden de prioridad."""
        self.extractors: List[SolutionExtractor] = [
            NestedDictExtractor(),
            FlatDictExtractor(),
            ListExtractor(),
            EmptyExtractor()  # Siempre al final como fallback
        ]

    def extract_solutions(
        self,
        solutions_data: Any,
        user_profile: UserProfile
    ) -> List[str]:
        """
        Extrae soluciones usando el primer extractor compatible.

        Args:
            solutions_data: Datos de soluciones en cualquier formato
            user_profile: Perfil del usuario

        Returns:
            Lista de soluciones extraídas

        Example:
            >>> strategy = SolutionExtractionStrategy()
            >>> solutions = strategy.extract_solutions(kb_data, profile)
        """
        for extractor in self.extractors:
            if extractor.can_extract(solutions_data):
                return extractor.extract(solutions_data, user_profile)

        return []

    def add_extractor(
        self,
        extractor: SolutionExtractor,
        priority: int = -1
    ) -> None:
        """
        Añade un extractor personalizado.

        Args:
            extractor: Instancia del extractor
            priority: Posicion en la cadena (-1 = antes del EmptyExtractor)
        """
        if priority == -1:
            self.extractors.insert(-1, extractor)
        else:
            self.extractors.insert(priority, extractor)
