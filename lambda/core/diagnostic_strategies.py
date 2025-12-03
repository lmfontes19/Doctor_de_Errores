"""
Estrategias de busqueda de diagnosticos.

Implementa el patron Strategy para desacoplar las diferentes fuentes
de diagnostico (Knowledge Base, Cache de IA, IA en vivo).

Patterns:
- Strategy: Cada estrategia es intercambiable
- Chain of Responsibility: Se pueden encadenar estrategias
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from models import Diagnostic, UserProfile
from utils import get_logger

from config.settings import KB_CONFIDENCE_THRESHOLD

from services.kb_service import kb_service
from services.ai_client import ai_service
from services.storage import storage_service, get_error_hash


class DiagnosticStrategy(ABC):
    """
    Interfaz abstracta para estrategias de diagnostico.

    Cada estrategia implementa una forma diferente de obtener
    diagnosticos (KB local, cache, IA, etc.).
    """

    def __init__(self):
        """Inicializa la estrategia."""
        self.logger = get_logger(self.__class__.__name__)
        self.storage_service = None  # Para estrategias que usen storage

    @abstractmethod
    def search_diagnostic(
        self,
        error_text: str,
        user_profile: UserProfile
    ) -> Optional[Diagnostic]:
        """
        Busca un diagnostico usando esta estrategia.

        Args:
            error_text: Texto del error a diagnosticar
            user_profile: Perfil del usuario

        Returns:
            Diagnostic si se encuentra, None si no
        """

    @abstractmethod
    def get_priority(self) -> int:
        """
        Obtiene la prioridad de esta estrategia.

        Menor numero = mayor prioridad.

        Returns:
            Prioridad (1 = maxima, 999 = minima)
        """

    @abstractmethod
    def get_name(self) -> str:
        """
        Obtiene el nombre de esta estrategia.

        Returns:
            Nombre legible de la estrategia
        """


class KnowledgeBaseStrategy(DiagnosticStrategy):
    """
    Estrategia de busqueda en Knowledge Base local.

    Prioridad: 1 (maxima)
    Ventajas: Rapido, offline, gratis, preciso
    Desventajas: Limitado a errores conocidos
    """

    def __init__(self):
        """Inicializa con referencia al servicio KB."""
        super().__init__()
        self.kb_service = kb_service
        self.confidence_threshold = KB_CONFIDENCE_THRESHOLD

    def search_diagnostic(
        self,
        error_text: str,
        user_profile: UserProfile
    ) -> Optional[Diagnostic]:
        """
        Busca en Knowledge Base local.

        Args:
            error_text: Texto del error
            user_profile: Perfil del usuario

        Returns:
            Diagnostic si confianza >= umbral, None si no
        """
        try:
            self.logger.debug(f"Searching KB for: {error_text[:30]}...")

            diagnostic = self.kb_service.search_diagnostic(
                error_text,
                user_profile
            )

            if diagnostic and diagnostic.confidence >= self.confidence_threshold:
                self.logger.info(
                    f"KB match found: {diagnostic.error_type}",
                    extra={'confidence': diagnostic.confidence}
                )
                return diagnostic

            self.logger.debug(
                "KB confidence too low or no match",
                extra={
                    'confidence': diagnostic.confidence if diagnostic else 0,
                    'threshold': self.confidence_threshold
                }
            )
            return None

        except Exception as e:
            self.logger.error(f"KB search failed: {e}", exc_info=True)
            return None

    def get_priority(self) -> int:
        """Maxima prioridad."""
        return 1

    def get_name(self) -> str:
        """Nombre de la estrategia."""
        return "Knowledge Base"


class CachedAIDiagnosticStrategy(DiagnosticStrategy):
    """
    Estrategia de busqueda en cache de diagnosticos de IA.

    Prioridad: 2
    Ventajas: Rapido, gratis, reutiliza diagnosticos completos
    Desventajas: Solo funciona si alguien ya pidio el mismo error
    """

    def __init__(self):
        """Inicializa con referencia al servicio de storage."""
        super().__init__()
        self.storage_service = storage_service

    def search_diagnostic(
        self,
        error_text: str,
        user_profile: UserProfile
    ) -> Optional[Diagnostic]:
        """
        Busca en cache de diagnosticos de IA.

        Args:
            error_text: Texto del error
            user_profile: Perfil del usuario

        Returns:
            Diagnostic cacheado si existe y es compatible, None si no
        """
        try:
            error_hash = get_error_hash(error_text)

            self.logger.info(
                f"Searching cache for hash: {error_hash[:16]}..."
            )

            diagnostic = self.storage_service.get_ai_diagnostic_cache(
                error_hash,
                user_profile
            )

            if diagnostic:
                if diagnostic.confidence == 0.0 or diagnostic.source == 'unknown':
                    self.logger.warning(
                        "Cached diagnostic is invalid (error diagnostic), ignoring",
                        extra={'error_hash': error_hash[:16]}
                    )
                    return None

                self.logger.info(
                    f"Cache HIT: {diagnostic.error_type}",
                    extra={'error_hash': error_hash[:16]}
                )
                return diagnostic

            self.logger.debug("Cache MISS")
            return None

        except Exception as e:
            self.logger.error(f"Cache search failed: {e}", exc_info=True)
            return None

    def get_priority(self) -> int:
        """Segunda prioridad."""
        return 2

    def get_name(self) -> str:
        """Nombre de la estrategia."""
        return "AI Cache"


class LiveAIDiagnosticStrategy(DiagnosticStrategy):
    """
    Estrategia de consulta a IA en vivo (OpenAI/Bedrock).

    Prioridad: 3 (ultima)
    Ventajas: Puede diagnosticar cualquier error, flexible
    Desventajas: Lento (~2s), costo por llamada

    Esta estrategia tambien guarda el resultado en cache para futuros usos.
    """

    def __init__(self):
        """Inicializa con referencia a servicios de IA y storage."""
        super().__init__()
        self.ai_service = ai_service
        self.storage_service = storage_service

    def search_diagnostic(
        self,
        error_text: str,
        user_profile: UserProfile
    ) -> Optional[Diagnostic]:
        """
        Consulta IA en vivo y cachea el resultado.

        Args:
            error_text: Texto del error
            user_profile: Perfil del usuario

        Returns:
            Diagnostic generado por IA
        """
        try:
            self.logger.info("Calling live AI service")

            diagnostic = self.ai_service.generate_diagnostic(
                error_text,
                user_profile
            )

            if diagnostic:
                self.logger.info(
                    f"AI diagnostic generated: {diagnostic.error_type}",
                    extra={'source': diagnostic.source}
                )

                # Guardar en cache para futuros usos
                self._cache_diagnostic(error_text, diagnostic, user_profile)

                return diagnostic

            self.logger.warning("AI service returned None")
            return None

        except Exception as e:
            self.logger.error(f"AI service failed: {e}", exc_info=True)
            return None

    def _cache_diagnostic(
        self,
        error_text: str,
        diagnostic: Diagnostic,
        user_profile: UserProfile
    ) -> None:
        """
        Guarda el diagnostico en cache (mejor esfuerzo).

        NO cachea diagnosticos de error (confidence=0 o source=unknown)
        para evitar que errores temporales se perpetuen en cache.

        Args:
            error_text: Texto del error
            diagnostic: Diagnostico a cachear
            user_profile: Perfil del usuario
        """
        try:
            if diagnostic.confidence == 0.0 or diagnostic.source == 'unknown':
                self.logger.info(
                    "Skipping cache for error diagnostic (confidence=0 or source=unknown)"
                )
                return

            error_hash = get_error_hash(error_text)

            success = self.storage_service.save_ai_diagnostic_cache(
                error_hash,
                diagnostic,
                user_profile
            )

            if success:
                self.logger.info(
                    "Diagnostic cached for future use",
                    extra={'error_hash': error_hash[:16]}
                )
            else:
                self.logger.warning(
                    "Failed to cache diagnostic (DynamoDB unavailable)")

        except Exception as e:
            self.logger.error(
                f"Failed to cache diagnostic: {e}", exc_info=True)

    def get_priority(self) -> int:
        """Minima prioridad (mas costoso)."""
        return 3

    def get_name(self) -> str:
        """Nombre de la estrategia."""
        return "Live AI"


class DiagnosticStrategyChain:
    """
    Chain of Responsibility para ejecutar estrategias en orden de prioridad.

    Ejecuta cada estrategia hasta que una retorne un diagnostico valido.
    """

    def __init__(self, strategies: List[DiagnosticStrategy]):
        """
        Inicializa la cadena con estrategias.

        Args:
            strategies: Lista de estrategias a ejecutar
        """
        self.logger = get_logger(self.__class__.__name__)

        # Ordenar por prioridad (menor numero = mayor prioridad)
        self.strategies = sorted(strategies, key=lambda s: s.get_priority())

        self.logger.info(
            f"Strategy chain initialized with {len(self.strategies)} strategies",
            extra={
                'order': [s.get_name() for s in self.strategies]
            }
        )

    def search_diagnostic(
        self,
        error_text: str,
        user_profile: UserProfile
    ) -> Optional[Diagnostic]:
        """
        Ejecuta estrategias en orden hasta encontrar un diagnostico.

        Args:
            error_text: Texto del error
            user_profile: Perfil del usuario

        Returns:
            Diagnostic de la primera estrategia exitosa, None si todas fallan
        """
        self.logger.info(
            f"Starting strategy chain for error: {error_text[:30]}..."
        )

        for strategy in self.strategies:
            self.logger.debug(
                f"Trying strategy: {strategy.get_name()} "
                f"(priority: {strategy.get_priority()})"
            )

            diagnostic = strategy.search_diagnostic(error_text, user_profile)

            if diagnostic:
                self.logger.info(
                    f"Strategy SUCCESS: {strategy.get_name()}",
                    extra={
                        'error_type': diagnostic.error_type,
                        'confidence': diagnostic.confidence
                    }
                )
                return diagnostic

            self.logger.debug(f"Strategy {strategy.get_name()} returned None")

        self.logger.warning("All strategies failed to find diagnostic")
        return None


def create_default_strategy_chain() -> DiagnosticStrategyChain:
    """
    Crea la cadena de estrategias por defecto.

    Orden de ejecucion:
    1. Knowledge Base (rapido, gratis, preciso)
    2. AI Cache (rapido, gratis, reutiliza)
    3. Live AI (lento, costoso, flexible)

    Returns:
        DiagnosticStrategyChain configurada
    """
    strategies = [
        KnowledgeBaseStrategy(),
        CachedAIDiagnosticStrategy(),
        LiveAIDiagnosticStrategy()
    ]

    return DiagnosticStrategyChain(strategies)
