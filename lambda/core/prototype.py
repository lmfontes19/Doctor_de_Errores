"""
Patron Prototype para clonacion de objetos complejos.

Este modulo implementa el patron Prototype para crear copias profundas
de diagnosticos y perfiles, permitiendo reutilizar templates sin modificar
los originales.

Patterns:
- Prototype: Clonacion de objetos por copia
- Template Method: Plantillas predefinidas
- Registry: Registro de prototipos
"""

from typing import Dict, Optional, List
from copy import deepcopy

from models import (
    Diagnostic,
    UserProfile,
    ErrorType,
    DiagnosticSource,
    OperatingSystem,
    PackageManager,
    Editor
)


class DiagnosticPrototype:
    """
    Prototipo de diagnostico que puede clonarse.

    Permite crear diagnosticos base que luego se personalizan
    sin afectar el template original.
    """

    def __init__(self, diagnostic: Diagnostic):
        """
        Inicializa el prototipo.

        Args:
            diagnostic: Diagnostico base para clonar
        """
        self._prototype = diagnostic

    def clone(self) -> Diagnostic:
        """
        Crea una copia profunda del diagnostico.

        Returns:
            Nuevo diagnostico independiente del original
        """
        return deepcopy(self._prototype)

    def clone_with_overrides(
        self,
        **kwargs
    ) -> Diagnostic:
        """
        Clona y sobrescribe campos especificos.

        Args:
            **kwargs: Campos a sobrescribir (error_type, voice_text, etc)

        Returns:
            Diagnostico clonado con modificaciones
        """
        cloned = self.clone()

        # Sobrescribir campos proporcionados
        for key, value in kwargs.items():
            if hasattr(cloned, key):
                setattr(cloned, key, value)

        return cloned


class UserProfilePrototype:
    """
    Prototipo de perfil de usuario que puede clonarse.

    Util para crear perfiles base (ej: perfil corporativo estandar).
    """

    def __init__(self, profile: UserProfile):
        """
        Inicializa el prototipo.

        Args:
            profile: Perfil base para clonar
        """
        self._prototype = profile

    def clone(self) -> UserProfile:
        """
        Crea una copia profunda del perfil.

        Returns:
            Nuevo perfil independiente del original
        """
        return deepcopy(self._prototype)

    def clone_with_overrides(
        self,
        **kwargs
    ) -> UserProfile:
        """
        Clona y sobrescribe campos especificos.

        Args:
            **kwargs: Campos a sobrescribir (os, package_manager, editor)

        Returns:
            Perfil clonado con modificaciones
        """
        cloned = self.clone()

        # Usar metodo update del UserProfile
        return cloned.update(**kwargs)


class PrototypeRegistry:
    """
    Registro centralizado de prototipos.

    Permite almacenar y recuperar prototipos por nombre.
    Pattern: Registry + Singleton
    """

    _instance: Optional['PrototypeRegistry'] = None

    def __new__(cls):
        """Implementa Singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Inicializa registros."""
        self._diagnostic_prototypes: Dict[str, DiagnosticPrototype] = {}
        self._profile_prototypes: Dict[str, UserProfilePrototype] = {}

        # Registrar prototipos predefinidos
        self._register_default_diagnostics()
        self._register_default_profiles()

    def _register_default_diagnostics(self):
        """Registra diagnosticos template comunes."""

        # Template: Error generico
        generic_error = DiagnosticPrototype(
            Diagnostic(
                error_type=ErrorType.GENERIC_ERROR.value,
                voice_text="Error generico detectado",
                solutions=["Verifica los logs", "Revisa la documentacion"],
                explanation="Error general sin clasificar",
                common_causes=["Configuracion incorrecta",
                               "Permisos insuficientes"],
                related_errors=["Error de sistema"],
                confidence=0.5,
                source=DiagnosticSource.KNOWLEDGE_BASE.value,
                card_title="Error Generico",
                card_text="Se detecto un error general."
            )
        )
        self.register_diagnostic('generic_error', generic_error)

        # Template: Modulo no encontrado
        module_not_found = DiagnosticPrototype(
            Diagnostic(
                error_type=ErrorType.PY_MODULE_NOT_FOUND.value,
                voice_text="No se encontro el modulo Python",
                solutions=[
                    "Instala el paquete con {pm} install nombre-paquete",
                    "Verifica que el nombre este escrito correctamente",
                    "Revisa tu entorno virtual"
                ],
                explanation="Python no puede encontrar el modulo especificado",
                common_causes=[
                    "Paquete no instalado",
                    "Entorno virtual no activado",
                    "Error en el nombre del modulo"
                ],
                related_errors=["ImportError", "ModuleNotFoundError"],
                confidence=0.9,
                source=DiagnosticSource.KNOWLEDGE_BASE.value,
                card_title="Modulo No Encontrado",
                card_text="Python no encuentra el modulo."
            )
        )
        self.register_diagnostic('module_not_found', module_not_found)

        # Template: Error de sintaxis
        syntax_error = DiagnosticPrototype(
            Diagnostic(
                error_type=ErrorType.PY_SYNTAX_ERROR.value,
                voice_text="Hay un error de sintaxis en tu codigo",
                solutions=[
                    "Revisa la linea indicada en el error",
                    "Verifica parentesis, corchetes y comillas",
                    "Usa {editor} para resaltar errores de sintaxis"
                ],
                explanation="El codigo tiene errores de sintaxis que impiden su ejecucion",
                common_causes=[
                    "Parentesis no cerrados",
                    "Falta dos puntos",
                    "Indentacion incorrecta"
                ],
                related_errors=["IndentationError", "TabError"],
                confidence=0.95,
                source=DiagnosticSource.KNOWLEDGE_BASE.value,
                card_title="Error de Sintaxis",
                card_text="El codigo tiene errores de sintaxis."
            )
        )
        self.register_diagnostic('syntax_error', syntax_error)

        # Template: Error de permisos
        permission_error = DiagnosticPrototype(
            Diagnostic(
                error_type=ErrorType.FILE_PERMISSION_ERROR.value,
                voice_text="No tienes permisos suficientes",
                solutions=[
                    "Ejecuta con sudo en {os}" if "{os}" in [
                        "linux", "macos"] else "Ejecuta como administrador",
                    "Verifica los permisos del archivo",
                    "Cambia el propietario del archivo"
                ],
                explanation="El sistema operativo bloquea el acceso al recurso",
                common_causes=[
                    "Archivo protegido",
                    "Usuario sin privilegios",
                    "Permisos incorrectos"
                ],
                related_errors=["PermissionError", "OSError"],
                confidence=0.85,
                source=DiagnosticSource.KNOWLEDGE_BASE.value,
                card_title="Error de Permisos",
                card_text="Permisos insuficientes."
            )
        )
        self.register_diagnostic('permission_error', permission_error)

    def _register_default_profiles(self):
        """Registra perfiles template comunes."""

        # Profile: Desarrollador Linux
        linux_dev = UserProfilePrototype(
            UserProfile(
                os=OperatingSystem.LINUX.value,
                package_manager=PackageManager.PIP.value,
                editor=Editor.VSCODE.value
            )
        )
        self.register_profile('linux_dev', linux_dev)

        # Profile: Desarrollador Windows
        windows_dev = UserProfilePrototype(
            UserProfile(
                os=OperatingSystem.WINDOWS.value,
                package_manager=PackageManager.PIP.value,
                editor=Editor.VSCODE.value
            )
        )
        self.register_profile('windows_dev', windows_dev)

        # Profile: Data Scientist
        data_scientist = UserProfilePrototype(
            UserProfile(
                os=OperatingSystem.LINUX.value,
                package_manager=PackageManager.CONDA.value,
                editor=Editor.JUPYTER.value
            )
        )
        self.register_profile('data_scientist', data_scientist)

        # Profile: Mac Developer
        mac_dev = UserProfilePrototype(
            UserProfile(
                os=OperatingSystem.MACOS.value,
                package_manager=PackageManager.PIP.value,
                editor=Editor.VSCODE.value
            )
        )
        self.register_profile('mac_dev', mac_dev)

    def register_diagnostic(
        self,
        name: str,
        prototype: DiagnosticPrototype
    ):
        """
        Registra un prototipo de diagnostico.

        Args:
            name: Nombre unico del prototipo
            prototype: Prototipo a registrar
        """
        self._diagnostic_prototypes[name] = prototype

    def register_profile(
        self,
        name: str,
        prototype: UserProfilePrototype
    ):
        """
        Registra un prototipo de perfil.

        Args:
            name: Nombre unico del prototipo
            prototype: Prototipo a registrar
        """
        self._profile_prototypes[name] = prototype

    def get_diagnostic(self, name: str) -> Optional[Diagnostic]:
        """
        Obtiene una copia del diagnostico prototipo.

        Args:
            name: Nombre del prototipo

        Returns:
            Copia del diagnostico o None si no existe
        """
        prototype = self._diagnostic_prototypes.get(name)
        return prototype.clone() if prototype else None

    def get_profile(self, name: str) -> Optional[UserProfile]:
        """
        Obtiene una copia del perfil prototipo.

        Args:
            name: Nombre del prototipo

        Returns:
            Copia del perfil o None si no existe
        """
        prototype = self._profile_prototypes.get(name)
        return prototype.clone() if prototype else None

    def get_diagnostic_with_overrides(
        self,
        name: str,
        **kwargs
    ) -> Optional[Diagnostic]:
        """
        Obtiene diagnostico con modificaciones.

        Args:
            name: Nombre del prototipo
            **kwargs: Campos a sobrescribir

        Returns:
            Diagnostico modificado o None si no existe
        """
        prototype = self._diagnostic_prototypes.get(name)
        return prototype.clone_with_overrides(**kwargs) if prototype else None

    def get_profile_with_overrides(
        self,
        name: str,
        **kwargs
    ) -> Optional[UserProfile]:
        """
        Obtiene perfil con modificaciones.

        Args:
            name: Nombre del prototipo
            **kwargs: Campos a sobrescribir

        Returns:
            Perfil modificado o None si no existe
        """
        prototype = self._profile_prototypes.get(name)
        return prototype.clone_with_overrides(**kwargs) if prototype else None

    def list_diagnostics(self) -> List[str]:
        """
        Lista nombres de diagnosticos registrados.

        Returns:
            Lista de nombres
        """
        return list(self._diagnostic_prototypes.keys())

    def list_profiles(self) -> List[str]:
        """
        Lista nombres de perfiles registrados.

        Returns:
            Lista de nombres
        """
        return list(self._profile_prototypes.keys())


# Instancia singleton del registro
registry = PrototypeRegistry()


# Funciones de conveniencia
def get_diagnostic_template(name: str) -> Optional[Diagnostic]:
    """
    Obtiene template de diagnostico.

    Args:
        name: Nombre del template

    Returns:
        Copia del diagnostico template
    """
    return registry.get_diagnostic(name)


def get_profile_template(name: str) -> Optional[UserProfile]:
    """
    Obtiene template de perfil.

    Args:
        name: Nombre del template

    Returns:
        Copia del perfil template
    """
    return registry.get_profile(name)


def create_custom_diagnostic(
    base_template: str,
    **overrides
) -> Optional[Diagnostic]:
    """
    Crea diagnostico personalizado desde template.

    Args:
        base_template: Nombre del template base
        **overrides: Campos a personalizar

    Returns:
        Diagnostico personalizado o None si template no existe
    """
    return registry.get_diagnostic_with_overrides(base_template, **overrides)


def create_custom_profile(
    base_template: str,
    **overrides
) -> Optional[UserProfile]:
    """
    Crea perfil personalizado desde template.

    Args:
        base_template: Nombre del template base
        **overrides: Campos a personalizar

    Returns:
        Perfil personalizado o None si template no existe
    """
    return registry.get_profile_with_overrides(base_template, **overrides)
