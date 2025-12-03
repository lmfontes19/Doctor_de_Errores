"""
Servicio de Knowledge Base para busqueda de diagnosticos.

Este modulo implementa el servicio de busqueda en la base de conocimiento
local (kb_templates.json). Usa regex para matching y calcula confidence
scores basados en coincidencias.

Patterns:
- Service Layer: Abstraccion de logica de negocio
- Strategy: Diferentes estrategias de scoring
- Singleton: Instancia unica del servicio
"""

import json
import re
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

from models import Diagnostic, UserProfile
from core.factories import DiagnosticFactory
from utils import get_logger


class KnowledgeBaseService:
    """
    Servicio para buscar diagnosticos en la base de conocimiento local.

    Implementa busqueda por patrones regex y calculo de confidence scores.
    Pattern: Singleton + Service Layer
    """

    _instance: Optional['KnowledgeBaseService'] = None

    def __new__(cls):
        """Implementa Singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Inicializa el servicio."""
        self.logger = get_logger(self.__class__.__name__)
        self._kb_data: Optional[Dict[str, Any]] = None
        self._load_knowledge_base()

    def _load_knowledge_base(self):
        """
        Carga la base de conocimiento desde JSON.

        Raises:
            FileNotFoundError: Si kb_templates.json no existe
            json.JSONDecodeError: Si el JSON es invalido
        """
        try:
            kb_path = Path(__file__).parent.parent / \
                'config' / 'kb_templates.json'

            with open(kb_path, 'r', encoding='utf-8') as f:
                self._kb_data = json.load(f)

            error_count = len(self._kb_data.get('errors', []))
            self.logger.info(
                f"Knowledge base loaded: {error_count} error templates")

        except FileNotFoundError:
            self.logger.error(f"KB file not found: {kb_path}")
            self._kb_data = {'errors': []}
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in KB file: {e}")
            self._kb_data = {'errors': []}

    def search_diagnostic(
        self,
        error_text: str,
        user_profile: UserProfile
    ) -> Optional[Diagnostic]:
        """
        Busca diagnostico que coincida con el texto de error.

        Args:
            error_text: Texto del error a diagnosticar
            user_profile: Perfil del usuario para personalizar soluciones

        Returns:
            Diagnostic si se encuentra coincidencia, None si no
        """
        if not self._kb_data or not error_text:
            return None

        self.logger.info(f"Searching diagnostic for: {error_text[:100]}...")

        # Buscar mejor coincidencia
        best_match = self._find_best_match(error_text)

        if not best_match:
            self.logger.info("No match found in KB")
            return None

        template, confidence = best_match

        self.logger.info(
            f"Match found: {template['id']} (confidence: {confidence:.2f})"
        )

        # Crear Diagnostic desde template usando factory
        diagnostic = DiagnosticFactory.from_kb_result(template, user_profile)

        # Actualizar confidence calculado
        diagnostic.confidence = confidence

        return diagnostic

    def _find_best_match(
        self,
        error_text: str
    ) -> Optional[Tuple[Dict[str, Any], float]]:
        """
        Encuentra la mejor coincidencia en la KB.

        Args:
            error_text: Texto del error

        Returns:
            Tupla (template, confidence) o None si no hay match
        """
        error_text_lower = error_text.lower()
        best_match = None
        best_confidence = 0.0

        for template in self._kb_data.get('errors', []):
            confidence = self._calculate_confidence(template, error_text_lower)

            if confidence > best_confidence:
                best_confidence = confidence
                best_match = template

        # Solo retornar si confidence es suficiente (umbral bajo para capturar mas)
        if best_confidence >= 0.25:  # Umbral minimo reducido
            self.logger.info(f"Best match confidence: {best_confidence:.2f}")
            return (best_match, best_confidence)

        self.logger.info(
            f"No match above threshold (best: {best_confidence:.2f})")
        return None

    def _calculate_confidence(
        self,
        template: Dict[str, Any],
        error_text: str
    ) -> float:
        """
        Calcula confidence score para un template.

        Estrategia de scoring:
        - Error type match exacto: +0.8 si el error_type esta en el texto
        - Pattern match: +0.7 por cada pattern que coincida (max 1.0)
        - Keyword match: +0.1 por cada keyword encontrado (max 0.4)
        - Boost del template: bonus adicional (0.1-0.3 tipicamente)

        Args:
            template: Template de error de la KB
            error_text: Texto del error (lowercase)

        Returns:
            Confidence score entre 0.0 y 1.0
        """
        score = 0.0
        error_text_normalized = error_text.replace(' ', '').replace('_', '')

        # 0. Buscar error_type directamente (alta prioridad)
        error_type = template.get('error_type', '')
        if error_type:
            error_type_lower = error_type.lower()
            error_type_normalized = error_type_lower.replace(
                ' ', '').replace('_', '')

            error_base = error_type_lower.replace('error', '').strip()

            if (error_type_lower in error_text or
                error_type_normalized in error_text_normalized or
                    (error_base and error_base in error_text)):
                score += 0.8
                self.logger.debug(f"Error type match: {error_type}")

        # 1. Buscar patterns (regex)
        patterns = template.get('patterns', [])
        pattern_matches = 0

        for pattern in patterns:
            try:
                if re.search(pattern, error_text, re.IGNORECASE):
                    pattern_matches += 1
                    self.logger.debug(f"Pattern match: {pattern}")
            except re.error:
                self.logger.warning(f"Invalid regex pattern: {pattern}")

        # Cada pattern da mas peso (0.7 puntos, maximo 1.0 con 2+ patterns)
        if patterns and pattern_matches > 0:
            score += min(1.0, (pattern_matches / len(patterns)) * 0.7 * 2)

        # 2. Buscar keywords
        keywords = template.get('keywords', [])
        keyword_matches = 0

        for keyword in keywords:
            if keyword.lower() in error_text:
                keyword_matches += 1
                self.logger.debug(f"Keyword match: {keyword}")

        # Cada keyword da 0.1 puntos (maximo 0.4 con 4+ keywords)
        if keywords and keyword_matches > 0:
            score += min(0.4, (keyword_matches / len(keywords)) * 0.1 * 4)

        # 3. Boost del template
        confidence_boost = template.get('confidence_boost', 0.0)
        score += confidence_boost

        # Normalizar a [0.0, 1.0]
        final_score = min(1.0, score)

        if final_score > 0.3:
            self.logger.debug(
                f"Template {template.get('id')} confidence: {final_score:.2f} "
                f"(error_type: {error_type.lower() in error_text}, "
                f"patterns: {pattern_matches}/{len(patterns)}, "
                f"keywords: {keyword_matches}/{len(keywords)})"
            )

        return final_score

    def get_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un template especifico por ID.

        Args:
            template_id: ID del template

        Returns:
            Template o None si no existe
        """
        if not self._kb_data:
            return None

        for template in self._kb_data.get('errors', []):
            if template.get('id') == template_id:
                return template

        return None

    def list_error_types(self) -> List[str]:
        """
        Lista todos los tipos de error en la KB.

        Returns:
            Lista de IDs de error
        """
        if not self._kb_data:
            return []

        return [
            template.get('id')
            for template in self._kb_data.get('errors', [])
            if template.get('id')
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadisticas de la KB.

        Returns:
            Diccionario con estadisticas
        """
        if not self._kb_data:
            return {
                'total_errors': 0,
                'categories': [],
                'severity_levels': []
            }

        errors = self._kb_data.get('errors', [])

        categories = set()
        severities = set()

        for error in errors:
            if 'category' in error:
                categories.add(error['category'])
            if 'severity' in error:
                severities.add(error['severity'])

        return {
            'total_errors': len(errors),
            'categories': list(categories),
            'severity_levels': list(severities),
            'version': self._kb_data.get('version', 'unknown')
        }

    def search_by_category(
        self,
        category: str
    ) -> List[Dict[str, Any]]:
        """
        Busca templates por categoria.

        Args:
            category: Categoria a buscar (ej: "dependencies", "syntax")

        Returns:
            Lista de templates que coinciden
        """
        if not self._kb_data:
            return []

        return [
            template
            for template in self._kb_data.get('errors', [])
            if template.get('category') == category
        ]

    def search_by_severity(
        self,
        severity: str
    ) -> List[Dict[str, Any]]:
        """
        Busca templates por severidad.

        Args:
            severity: Severidad a buscar (ej: "high", "medium", "low")

        Returns:
            Lista de templates que coinciden
        """
        if not self._kb_data:
            return []

        return [
            template
            for template in self._kb_data.get('errors', [])
            if template.get('severity') == severity
        ]

    def reload_knowledge_base(self):
        """
        Recarga la base de conocimiento desde disco.

        Util para actualizar la KB sin reiniciar el servicio.
        """
        self.logger.info("Reloading knowledge base...")
        self._load_knowledge_base()


# Instancia singleton del servicio
kb_service = KnowledgeBaseService()


# Funciones de conveniencia
def search_diagnostic(
    error_text: str,
    user_profile: UserProfile
) -> Optional[Diagnostic]:
    """
    Busca diagnostico en la KB.

    Args:
        error_text: Texto del error
        user_profile: Perfil del usuario

    Returns:
        Diagnostic o None
    """
    return kb_service.search_diagnostic(error_text, user_profile)


def get_kb_statistics() -> Dict[str, Any]:
    """
    Obtiene estadisticas de la KB.

    Returns:
        Diccionario con estadisticas
    """
    return kb_service.get_statistics()
