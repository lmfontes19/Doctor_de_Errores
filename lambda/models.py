"""
Modelos de datos para el skill Doctor de Errores.

Este modulo define las estructuras de datos principales usando dataclasses
para proporcionar type safety y validacion.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from enum import Enum


class ErrorType(Enum):
    """Tipos de errores soportados."""
    MODULE_NOT_FOUND = "py_module_not_found"
    SYNTAX_ERROR = "py_syntax_error"
    TYPE_ERROR = "py_type_error"
    INDENTATION_ERROR = "py_indentation_error"
    NAME_ERROR = "py_name_error"
    UNKNOWN = "unknown"

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
    """
    os: OperatingSystem = OperatingSystem.LINUX
    package_manager: PackageManager = PackageManager.PIP
    editor: Editor = Editor.VSCODE

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
            editor=Editor.from_string(data.get('editor', 'vscode'))
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
            'editor': self.editor.value
        }

    def update(self, **kwargs) -> 'UserProfile':
        """
        Actualiza perfil con nuevos valores.

        Args:
            **kwargs: os, pm, editor como strings

        Returns:
            Nuevo UserProfile actualizado

        Example:
            >>> profile = UserProfile()
            >>> updated = profile.update(os='windows')
            >>> updated.os
            <OperatingSystem.WINDOWS: 'windows'>
        """
        current = self.to_dict()

        if 'os' in kwargs:
            current['os'] = kwargs['os']
        if 'pm' in kwargs:
            current['pm'] = kwargs['pm']
        if 'editor' in kwargs:
            current['editor'] = kwargs['editor']

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


# Funciones de utilidad para backwards compatibility
def user_profile_from_dict(data: Optional[Dict[str, Any]]) -> UserProfile:
    """Helper para crear UserProfile desde dict."""
    return UserProfile.from_dict(data)


def diagnostic_from_dict(data: Dict[str, Any]) -> Diagnostic:
    """Helper para crear Diagnostic desde dict."""
    return Diagnostic.from_dict(data)
