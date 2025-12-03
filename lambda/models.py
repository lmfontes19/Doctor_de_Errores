"""
Modelos de datos para el skill Doctor de Errores.

Este modulo define las estructuras de datos principales usando dataclasses
para proporcionar type safety y validacion.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum


class ErrorType(Enum):
    """Tipos de errores soportados."""
    # Errores generales
    GENERIC_ERROR = "generic_error"
    UNKNOWN = "unknown"

    # Errores de modulos e imports
    MODULE_NOT_FOUND = "py_module_not_found"
    PY_MODULE_NOT_FOUND = "py_module_not_found"  # Alias

    # Errores de sintaxis
    SYNTAX_ERROR = "py_syntax_error"
    PY_SYNTAX_ERROR = "py_syntax_error"  # Alias

    # Errores de tipos
    TYPE_ERROR = "py_type_error"

    # Errores de indentacion
    INDENTATION_ERROR = "py_indentation_error"

    # Errores de nombres
    NAME_ERROR = "py_name_error"

    # Errores de archivos y permisos
    FILE_PERMISSION_ERROR = "file_permission_error"

    @classmethod
    def from_string(cls, value: str) -> 'ErrorType':
        """
        Convierte string a ErrorType.

        Args:
            value: String del tipo de error

        Returns:
            ErrorType correspondiente o UNKNOWN
        """
        try:
            return cls(value)
        except ValueError:
            return cls.UNKNOWN


class DiagnosticSource(Enum):
    """Fuente del diagnostico."""
    KNOWLEDGE_BASE = "kb"
    AI_SERVICE = "ai"
    UNKNOWN = "unknown"


class OperatingSystem(Enum):
    """Sistemas operativos soportados."""
    LINUX = "linux"
    WINDOWS = "windows"
    MACOS = "macos"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str) -> 'OperatingSystem':
        """Convierte string a OperatingSystem."""
        normalized = value.lower()
        mapping = {
            'linux': cls.LINUX,
            'windows': cls.WINDOWS,
            'win': cls.WINDOWS,
            'macos': cls.MACOS,
            'mac': cls.MACOS,
            'osx': cls.MACOS,
            'darwin': cls.MACOS
        }
        return mapping.get(normalized, cls.UNKNOWN)


class PackageManager(Enum):
    """Gestores de paquetes soportados."""
    PIP = "pip"
    CONDA = "conda"
    POETRY = "poetry"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str) -> 'PackageManager':
        """Convierte string a PackageManager."""
        normalized = value.lower()
        mapping = {
            'pip': cls.PIP,
            'pip3': cls.PIP,
            'conda': cls.CONDA,
            'anaconda': cls.CONDA,
            'miniconda': cls.CONDA,
            'poetry': cls.POETRY
        }
        return mapping.get(normalized, cls.UNKNOWN)


class Editor(Enum):
    """Editores soportados."""
    VSCODE = "vscode"
    PYCHARM = "pycharm"
    SUBLIME = "sublime"
    VIM = "vim"
    JUPYTER = "jupyter"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str) -> 'Editor':
        """Convierte string a Editor."""
        normalized = value.lower()
        mapping = {
            'vscode': cls.VSCODE,
            'code': cls.VSCODE,
            'visual studio code': cls.VSCODE,
            'pycharm': cls.PYCHARM,
            'charm': cls.PYCHARM,
            'sublime': cls.SUBLIME,
            'sublime text': cls.SUBLIME,
            'vim': cls.VIM,
            'vi': cls.VIM,
            'neovim': cls.VIM,
            'jupyter': cls.JUPYTER,
            'notebook': cls.JUPYTER,
            'jupyterlab': cls.JUPYTER
        }
        return mapping.get(normalized, cls.UNKNOWN)


@dataclass
class UserProfile:
    """
    Perfil tecnico del usuario.

    Contiene las preferencias del usuario para personalizar
    las soluciones de diagnostico.

    Attributes:
        os: Sistema operativo
        package_manager: Gestor de paquetes
        editor: Editor de codigo
        is_configured: True si el usuario configuro su perfil, False si es default
    """
    os: OperatingSystem = OperatingSystem.LINUX
    package_manager: PackageManager = PackageManager.PIP
    editor: Editor = Editor.VSCODE
    is_configured: bool = False

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> 'UserProfile':
        """
        Crea UserProfile desde diccionario.

        Args:
            data: Diccionario con os, pm, editor

        Returns:
            UserProfile con valores normalizados

        Example:
            >>> profile = UserProfile.from_dict({
            ...     'os': 'mac',
            ...     'pm': 'conda',
            ...     'editor': 'pycharm'
            ... })
            >>> profile.os
            <OperatingSystem.MACOS: 'macos'>
        """
        if not data:
            return cls()

        return cls(
            os=OperatingSystem.from_string(data.get('os', 'linux')),
            package_manager=PackageManager.from_string(data.get('pm', 'pip')),
            editor=Editor.from_string(data.get('editor', 'vscode')),
            is_configured=data.get('is_configured', False)
        )

    def to_dict(self) -> Dict[str, str]:
        """
        Convierte a diccionario para sesion.

        Returns:
            Dict con valores string

        Example:
            >>> profile = UserProfile()
            >>> profile.to_dict()
            {'os': 'linux', 'pm': 'pip', 'editor': 'vscode'}
        """
        return {
            'os': self.os.value,
            'pm': self.package_manager.value,
            'editor': self.editor.value,
            'is_configured': self.is_configured
        }

    def update(self, **kwargs) -> 'UserProfile':
        """
        Actualiza perfil con nuevos valores.

        Args:
            **kwargs: os, pm, editor como strings

        Returns:
            Nuevo UserProfile actualizado (marcado como configurado)

        Example:
            >>> profile = UserProfile()
            >>> updated = profile.update(os='windows')
            >>> updated.os
            <OperatingSystem.WINDOWS: 'windows'>
            >>> updated.is_configured
            True
        """
        current = self.to_dict()

        if 'os' in kwargs and kwargs['os']:
            current['os'] = kwargs['os']
        if 'pm' in kwargs and kwargs['pm']:
            current['pm'] = kwargs['pm']
        if 'editor' in kwargs and kwargs['editor']:
            current['editor'] = kwargs['editor']

        # Marcar como configurado cuando se actualiza
        current['is_configured'] = True

        return UserProfile.from_dict(current)


@dataclass
class Diagnostic:
    """
    Resultado del diagnostico de un error.

    Contiene toda la informacion generada por el proceso de diagnostico,
    incluyendo soluciones personalizadas y explicaciones tecnicas.

    Attributes:
        error_type: Tipo del error detectado
        voice_text: Texto simplificado para voz (<= 300 chars)
        card_title: Titulo de la tarjeta
        card_text: Texto de la tarjeta basica
        solutions: Lista de soluciones paso a paso
        explanation: Explicacion tecnica del error
        confidence: Nivel de confianza (0.0 - 1.0)
        source: Fuente del diagnostico
        common_causes: Causas comunes del error
        related_errors: Errores relacionados
    """
    error_type: str
    voice_text: str
    card_title: str
    card_text: str
    solutions: List[str] = field(default_factory=list)
    explanation: Optional[str] = None
    confidence: float = 0.0
    source: str = DiagnosticSource.UNKNOWN.value
    common_causes: List[str] = field(default_factory=list)
    related_errors: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Diagnostic':
        """
        Crea Diagnostic desde diccionario.

        Args:
            data: Diccionario con campos del diagnostico

        Returns:
            Instancia de Diagnostic

        Example:
            >>> diagnostic = Diagnostic.from_dict({
            ...     'error_type': 'py_module_not_found',
            ...     'voice_text': 'Error de modulo',
            ...     'card_title': 'ModuleNotFoundError',
            ...     'card_text': 'No se encontro el modulo',
            ...     'solutions': ['pip install pandas'],
            ...     'confidence': 0.95
            ... })
        """
        return cls(
            error_type=data.get('error_type', 'unknown'),
            voice_text=data.get('voice_text', ''),
            card_title=data.get('card_title', ''),
            card_text=data.get('card_text', ''),
            solutions=data.get('solutions', []),
            explanation=data.get('explanation'),
            confidence=data.get('confidence', 0.0),
            source=data.get('source', DiagnosticSource.UNKNOWN.value),
            common_causes=data.get('common_causes', []),
            related_errors=data.get('related_errors', [])
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte a diccionario para sesion.

        Returns:
            Diccionario con todos los campos
        """
        return {
            'error_type': self.error_type,
            'voice_text': self.voice_text,
            'card_title': self.card_title,
            'card_text': self.card_text,
            'solutions': self.solutions,
            'explanation': self.explanation,
            'confidence': self.confidence,
            'source': self.source,
            'common_causes': self.common_causes,
            'related_errors': self.related_errors
        }

    def get_error_type_enum(self) -> ErrorType:
        """
        Obtiene ErrorType enum del tipo de error.

        Returns:
            ErrorType correspondiente
        """
        return ErrorType.from_string(self.error_type)

    def get_source_enum(self) -> DiagnosticSource:
        """
        Obtiene DiagnosticSource enum de la fuente.

        Returns:
            DiagnosticSource correspondiente
        """
        try:
            return DiagnosticSource(self.source)
        except ValueError:
            return DiagnosticSource.UNKNOWN

    def has_solutions(self) -> bool:
        """Verifica si tiene soluciones."""
        return len(self.solutions) > 0

    def has_explanation(self) -> bool:
        """Verifica si tiene explicacion."""
        return self.explanation is not None and len(self.explanation) > 0

    def get_solution_count(self) -> int:
        """Retorna numero de soluciones."""
        return len(self.solutions)

    def get_solution(self, index: int) -> Optional[str]:
        """
        Obtiene solucion por indice.

        Args:
            index: Indice de la solucion (0-based)

        Returns:
            Solucion o None si indice invalido
        """
        if 0 <= index < len(self.solutions):
            return self.solutions[index]
        return None


@dataclass
class SessionState:
    """
    Estado de la sesion del usuario.

    Mantiene el contexto de la conversacion entre intents.

    Attributes:
        user_profile: Perfil del usuario
        last_diagnostic: ultimo diagnostico generado
        solution_index: Indice de solucion actual (para MoreIntent)
    """
    user_profile: Optional[UserProfile] = None
    last_diagnostic: Optional[Diagnostic] = None
    solution_index: int = 0

    @classmethod
    def from_handler_input(cls, handler_input) -> 'SessionState':
        """
        Crea SessionState desde HandlerInput.

        Args:
            handler_input: HandlerInput de Alexa SDK

        Returns:
            SessionState con datos de sesion
        """
        attrs = handler_input.attributes_manager.session_attributes

        # Cargar user profile
        profile_data = attrs.get('user_profile')
        profile = UserProfile.from_dict(profile_data) if profile_data else None

        # Cargar diagnostic
        diagnostic_data = attrs.get('last_diagnostic')
        diagnostic = Diagnostic.from_dict(
            diagnostic_data) if diagnostic_data else None

        # Cargar solution index
        solution_index = attrs.get('solution_index', 0)

        return cls(
            user_profile=profile,
            last_diagnostic=diagnostic,
            solution_index=solution_index
        )

    def save_to_handler_input(self, handler_input) -> None:
        """
        Guarda SessionState en HandlerInput.

        Args:
            handler_input: HandlerInput de Alexa SDK
        """
        attrs = handler_input.attributes_manager.session_attributes

        if self.user_profile:
            attrs['user_profile'] = self.user_profile.to_dict()

        if self.last_diagnostic:
            attrs['last_diagnostic'] = self.last_diagnostic.to_dict()

        attrs['solution_index'] = self.solution_index


# ============================================================================
# Error Validation Rules
# ============================================================================


class ValidationResult:
    """
    Encapsula el resultado de una validacion.

    Value Object pattern - inmutable y con semantica clara.
    """

    def __init__(self, is_valid: bool, message: Optional[str] = None, score: float = 0.0):
        self._is_valid = is_valid
        self._message = message
        self._score = score

    @property
    def is_valid(self) -> bool:
        return self._is_valid

    @property
    def message(self) -> Optional[str]:
        return self._message

    @property
    def score(self) -> float:
        return self._score

    def __bool__(self) -> bool:
        """Permite usar en contextos booleanos: if result: ..."""
        return self._is_valid


class ErrorPattern(ABC):
    """
    Interfaz para detectores de patrones de error.

    Strategy Pattern - cada patron es una estrategia intercambiable.
    Open/Closed Principle - abierto para extension, cerrado para modificacion.
    """

    @abstractmethod
    def matches(self, text: str) -> bool:
        """
        Verifica si el texto coincide con este patron.

        Args:
            text: Texto a analizar

        Returns:
            True si coincide con el patron
        """

    @abstractmethod
    def get_confidence(self) -> float:
        """
        Retorna el nivel de confianza que aporta este patron (0.0 - 1.0).

        Returns:
            Confianza del patron
        """


class PythonExceptionPattern(ErrorPattern):
    """Detecta nombres de excepciones Python estandar (NombreError, NombreException)."""

    def matches(self, text: str) -> bool:
        # CamelCase terminando en Error o Exception
        return bool(re.search(r'[A-Z][a-z]+(?:Error|Exception)', text))

    def get_confidence(self) -> float:
        return 0.3


class NotFoundPattern(ErrorPattern):
    """Detecta frases 'not found' comunes en errores."""

    def matches(self, text: str) -> bool:
        return bool(re.search(r'\bnot found\b', text, re.IGNORECASE))

    def get_confidence(self) -> float:
        return 0.2


class CannotActionPattern(ErrorPattern):
    """Detecta frases 'cannot do_something'."""

    def matches(self, text: str) -> bool:
        return bool(re.search(r'\bcannot \w+', text, re.IGNORECASE))

    def get_confidence(self) -> float:
        return 0.2


class ModuleImportPattern(ErrorPattern):
    """Detecta errores relacionados con imports/modulos."""

    def matches(self, text: str) -> bool:
        patterns = [
            r'\bno module named\b',
            r'\bimport\b',
            r'\bmodule\b.*\berror\b'
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)

    def get_confidence(self) -> float:
        return 0.25


class SyntaxRelatedPattern(ErrorPattern):
    """Detecta errores de sintaxis."""

    def matches(self, text: str) -> bool:
        patterns = [
            r'\binvalid syntax\b',
            r'\bsyntax error\b',
            r'\bexpected.*but found\b'
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)

    def get_confidence(self) -> float:
        return 0.25


class AttributeAccessPattern(ErrorPattern):
    """Detecta errores de atributos."""

    def matches(self, text: str) -> bool:
        patterns = [
            r'\bhas no attribute\b',
            r'\bnot defined\b',
            r'\bundefined\b'
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)

    def get_confidence(self) -> float:
        return 0.2


class TechnicalNotationPattern(ErrorPattern):
    """Detecta notacion tecnica (package.module, snake_case, etc.)."""

    def matches(self, text: str) -> bool:
        patterns = [
            r'\w+\.\w+',           # package.module
            r'[a-z]+_[a-z]+',      # snake_case
            r'[a-z]+-[a-z]+',      # kebab-case
            r'\w+\d+',             # con numeros
        ]
        return any(re.search(p, text.lower()) for p in patterns)

    def get_confidence(self) -> float:
        return 0.15


class TracebackPattern(ErrorPattern):
    """Detecta menciones de traceback o lineas de codigo."""

    def matches(self, text: str) -> bool:
        patterns = [
            r'\btraceback\b',
            r'\bline \d+\b',
            r'\bfile ".*", line \d+\b'
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)

    def get_confidence(self) -> float:
        return 0.2


class ErrorPatternMatcher:
    """
    Coordina multiples patrones para determinar especificidad.

    Composite Pattern - compone multiples estrategias.
    Single Responsibility - solo se encarga de coordinar patrones.
    """

    def __init__(self, patterns: Optional[List[ErrorPattern]] = None):
        """
        Args:
            patterns: Lista de patrones a usar. Si None, usa patrones por defecto.
        """
        self._patterns = patterns or self._get_default_patterns()

    @staticmethod
    def _get_default_patterns() -> List[ErrorPattern]:
        """Factory Method - crea conjunto por defecto de patrones."""
        return [
            PythonExceptionPattern(),
            NotFoundPattern(),
            CannotActionPattern(),
            ModuleImportPattern(),
            SyntaxRelatedPattern(),
            AttributeAccessPattern(),
            TechnicalNotationPattern(),
            TracebackPattern(),
        ]

    def has_specific_patterns(self, text: str) -> bool:
        """
        Verifica si el texto contiene patrones especificos.

        Args:
            text: Texto a analizar

        Returns:
            True si al menos un patron coincide
        """
        return any(pattern.matches(text) for pattern in self._patterns)

    def calculate_confidence_score(self, text: str) -> float:
        """
        Calcula score de confianza basado en patrones encontrados.

        Args:
            text: Texto a analizar

        Returns:
            Score entre 0.0 y 1.0
        """
        score = 0.3

        for pattern in self._patterns:
            if pattern.matches(text):
                score += pattern.get_confidence()

        # Bonus por longitud
        if len(text) > 30:
            score += 0.15
        elif len(text) > 15:
            score += 0.05

        return min(score, 1.0)


class ValidationRule(ABC):
    """
    Interfaz para reglas de validacion.

    Strategy Pattern - cada regla es una estrategia.
    Interface Segregation - interfaz minima y especifica.
    """

    @abstractmethod
    def validate(self, text: str) -> ValidationResult:
        """
        Valida el texto segun esta regla.

        Args:
            text: Texto a validar

        Returns:
            ValidationResult con el resultado
        """


class EmptyTextRule(ValidationRule):
    """Regla: El texto no debe estar vacio."""

    def validate(self, text: str) -> ValidationResult:
        if not text or not text.strip():
            return ValidationResult(
                is_valid=False,
                message="No recibi una descripcion del error. ¿Que error tienes?"
            )
        return ValidationResult(is_valid=True)


class MinimumLengthRule(ValidationRule):
    """Regla: El texto debe tener una longitud minima."""

    def __init__(self, min_length: int = 5):
        self._min_length = min_length

    def validate(self, text: str) -> ValidationResult:
        if len(text.strip()) < self._min_length:
            return ValidationResult(
                is_valid=False,
                message="La descripcion es muy corta. ¿Puedes dar mas detalles del error?"
            )
        return ValidationResult(is_valid=True)


class VaguePhraseRule(ValidationRule):
    """Regla: El texto no debe ser exactamente una frase vaga conocida."""

    VAGUE_PHRASES = {
        'error', 'un error', '1 error',
        'tengo error', 'hay error', 'problema',
        'bug', 'falla', 'no funciona'
    }

    def validate(self, text: str) -> ValidationResult:
        if text.lower().strip() in self.VAGUE_PHRASES:
            return ValidationResult(
                is_valid=False,
                message="Necesito mas detalles. ¿Que tipo de error exactamente? Por ejemplo: module not found, syntax error, etcetera."
            )
        return ValidationResult(is_valid=True)


class PatternBasedRule(ValidationRule):
    """
    Regla: El texto debe tener patrones tecnicos o longitud suficiente.

    Dependency Inversion - depende de abstraccion (ErrorPatternMatcher).
    """

    def __init__(self, pattern_matcher: Optional[ErrorPatternMatcher] = None):
        self._pattern_matcher = pattern_matcher or ErrorPatternMatcher()

    def validate(self, text: str) -> ValidationResult:
        text_clean = text.strip()

        if self._pattern_matcher.has_specific_patterns(text_clean):
            score = self._pattern_matcher.calculate_confidence_score(
                text_clean)
            return ValidationResult(is_valid=True, score=score)

        if len(text_clean) >= 15:
            return ValidationResult(is_valid=True, score=0.5)

        if len(text_clean) < 10:
            return ValidationResult(
                is_valid=False,
                message="¿Podrias ser mas especifico sobre el error? Por ejemplo, menciona el tipo de error o el mensaje que ves."
            )

        return ValidationResult(is_valid=True, score=0.4)


class ErrorValidator:
    """
    Validador principal que coordina multiples reglas.

    Chain of Responsibility Pattern - ejecuta reglas en cadena.
    Single Responsibility - solo coordina reglas.
    Open/Closed - agregar reglas sin modificar esta clase.
    """

    def __init__(self, rules: Optional[List[ValidationRule]] = None):
        """
        Args:
            rules: Lista de reglas a aplicar. Si None, usa reglas por defecto.
        """
        self._rules = rules or self._get_default_rules()

    @staticmethod
    def _get_default_rules() -> List[ValidationRule]:
        """Factory Method - crea conjunto por defecto de reglas."""
        return [
            EmptyTextRule(),
            MinimumLengthRule(min_length=5),
            VaguePhraseRule(),
            PatternBasedRule(),
        ]

    def validate(self, text: str) -> ValidationResult:
        """
        Valida el texto aplicando todas las reglas en orden.

        Args:
            text: Descripcion del error a validar

        Returns:
            ValidationResult con el resultado de la primera regla que falle,
            o ValidationResult valido si todas pasan.
        """
        for rule in self._rules:
            result = rule.validate(text)
            if not result.is_valid:
                return result

        # Todas las reglas pasaron - calcular score final
        pattern_matcher = ErrorPatternMatcher()
        score = pattern_matcher.calculate_confidence_score(text)
        return ValidationResult(is_valid=True, score=score)


class ErrorValidation:
    """
    Facade para validacion de errores.

    Facade Pattern - interfaz simplificada para el subsistema de validacion.
    Mantiene compatibilidad con codigo existente.
    """

    _validator: Optional[ErrorValidator] = None

    @classmethod
    def _get_validator(cls) -> ErrorValidator:
        """Lazy initialization del validador."""
        if cls._validator is None:
            cls._validator = ErrorValidator()
        return cls._validator

    @classmethod
    def is_specific_enough(cls, text: str) -> Tuple[bool, Optional[str]]:
        """
        Valida si la descripcion del error es suficientemente especifica.

        Mantiene la interfaz original para compatibilidad.

        Args:
            text: Descripcion del error

        Returns:
            (is_valid, message_if_invalid)

        Examples:
            >>> ErrorValidation.is_specific_enough("error")
            (False, "Necesito mas detalles...")

            >>> ErrorValidation.is_specific_enough("numpy not found")
            (True, None)
        """
        validator = cls._get_validator()
        result = validator.validate(text)
        return (result.is_valid, result.message)

    @classmethod
    def get_specificity_score(cls, text: str) -> float:
        """
        Calcula un score de especificidad de 0.0 (muy vago) a 1.0 (muy especifico).

        util para logging y metricas.

        Args:
            text: Descripcion del error

        Returns:
            Score entre 0.0 y 1.0
        """
        validator = cls._get_validator()
        result = validator.validate(text)
        return result.score


# Funciones de utilidad para backwards compatibility
def user_profile_from_dict(data: Optional[Dict[str, Any]]) -> UserProfile:
    """Helper para crear UserProfile desde dict."""
    return UserProfile.from_dict(data)


def diagnostic_from_dict(data: Dict[str, Any]) -> Diagnostic:
    """Helper para crear Diagnostic desde dict."""
    return Diagnostic.from_dict(data)
