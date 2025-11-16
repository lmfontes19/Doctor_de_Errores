"""
Handler para el intent SetProfileIntent.

Este intent permite al usuario configurar su perfil tecnico (sistema operativo,
gestor de paquetes, editor) para personalizar las soluciones de diagnostico.
El perfil se guarda en sesion y opcionalmente en DynamoDB para persistencia.

Flujo:
1. Extrae slots de perfil (so, pm, editor)
2. Valida los valores de los slots
3. Obtiene perfil actual de sesion/DynamoDB
4. Actualiza solo los campos proporcionados (merge)
5. Guarda perfil actualizado en sesion
6. Opcionalmente persiste en DynamoDB
7. Confirma cambios al usuario

Patterns:
- Template Method (hereda de BaseIntentHandler)
- Builder (construccion incremental de perfil)
- Strategy (persistencia en sesion vs DynamoDB)
"""

from typing import Dict, Any, Optional
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from ask_sdk_model.ui import SimpleCard

from intents.base import BaseIntentHandler
from models import UserProfile, OperatingSystem, PackageManager, Editor
from utils import get_logger

# Importaciones que se crearan despues
# from services.storage import StorageService


class SetProfileIntentHandler(BaseIntentHandler):
    """
    Handler para configurar el perfil tecnico del usuario.

    Este intent permite al usuario personalizar su entorno de desarrollo
    (OS, package manager, editor) para recibir soluciones mas relevantes
    y especificas. El perfil se puede actualizar parcialmente (solo cambiar
    uno o dos campos sin afectar los demas).

    Features:
    - Actualizacion parcial de perfil (merge inteligente)
    - Validacion de valores de slots
    - Valores por defecto para campos no especificados
    - Persistencia en sesion (temporal)
    - Persistencia en DynamoDB (opcional, persistente entre sesiones)
    - Confirmacion verbal de cambios

    Attributes:
        intent_name: "SetProfileIntent"

    Slots:
        - so: Sistema operativo (SOType: Windows, macOS, Linux, WSL)
        - pm: Package manager (PackageManagerType: pip, conda, poetry)
        - editor: Editor (EditorType: VSCode, PyCharm, Jupyter, Vim, etc.)

    Session Attributes Actualizados:
        - user_profile: Perfil completo del usuario

    Note:
        Los slots son opcionales. El usuario puede actualizar solo uno o varios
        a la vez. Por ejemplo: "cambialo a conda" solo actualiza el pm.
    """

    # Valores por defecto
    DEFAULT_PROFILE = {
        'os': 'linux',
        'pm': 'pip',
        'editor': 'vscode'
    }

    # Mapeo de aliases comunes
    OS_ALIASES = {
        'windows': 'windows',
        'win': 'windows',
        'macos': 'macos',
        'mac': 'macos',
        'osx': 'macos',
        'linux': 'linux',
        'ubuntu': 'linux',
        'debian': 'linux',
        'wsl': 'wsl',
        'subsistema': 'wsl'
    }

    PM_ALIASES = {
        'pip': 'pip',
        'conda': 'conda',
        'anaconda': 'conda',
        'miniconda': 'conda',
        'poetry': 'poetry'
    }

    EDITOR_ALIASES = {
        'vscode': 'vscode',
        'visual studio code': 'vscode',
        'code': 'vscode',
        'vs code': 'vscode',
        'pycharm': 'pycharm',
        'jupyter': 'jupyter',
        'jupyter notebook': 'jupyter',
        'vim': 'vim',
        'vi': 'vim',
        'neovim': 'vim',
        'sublime': 'sublime',
        'sublime text': 'sublime',
        'atom': 'atom',
        'notepad++': 'notepad++'
    }

    def __init__(self):
        """Inicializa el handler."""
        super().__init__()

        # Servicio de storage (inicializar despues cuando este creado)
        # self.storage_service = StorageService()

        self.logger.info("SetProfileIntentHandler initialized")

    @property
    def intent_name(self) -> str:
        """Nombre del intent."""
        return "SetProfileIntent"

    def handle_intent(self, handler_input: HandlerInput) -> Response:
        """
        Maneja la configuracion del perfil de usuario.

        Args:
            handler_input: Input del request de Alexa

        Returns:
            Response: Respuesta con confirmacion de cambios
        """
        # Extraer slots
        so_slot = self.get_slot_value(handler_input, 'so')
        pm_slot = self.get_slot_value(handler_input, 'pm')
        editor_slot = self.get_slot_value(handler_input, 'editor')

        # Normalizar valores (aplicar aliases)
        so_value = self._normalize_value(
            so_slot, self.OS_ALIASES) if so_slot else None
        pm_value = self._normalize_value(
            pm_slot, self.PM_ALIASES) if pm_slot else None
        editor_value = self._normalize_value(
            editor_slot, self.EDITOR_ALIASES) if editor_slot else None

        # Verificar que al menos un slot este presente
        if not any([so_value, pm_value, editor_value]):
            return self._handle_no_slots(handler_input)

        # Obtener perfil actual
        current_profile = self.get_user_profile(handler_input)

        # Construir nuevo perfil usando update()
        new_profile = current_profile.update(
            os=so_value if so_value else None,
            pm=pm_value if pm_value else None,
            editor=editor_value if editor_value else None
        )

        # Guardar en sesion
        self.save_user_profile(handler_input, new_profile)

        # TODO: Persistir en DynamoDB cuando StorageService este listo
        # user_id = self.get_user_id(handler_input)
        # self.storage_service.save_user_profile(user_id, new_profile.to_dict())

        self.logger.info(
            f"Profile updated",
            extra={
                'old_profile': current_profile.to_dict(),
                'new_profile': new_profile.to_dict(),
                'changed_fields': self._get_changed_fields(current_profile, new_profile)
            }
        )

        # Construir respuesta
        return self._build_confirmation_response(
            handler_input,
            current_profile,
            new_profile
        )

    def _normalize_value(self, value: str, aliases: Dict[str, str]) -> Optional[str]:
        """
        Normaliza un valor usando el diccionario de aliases.

        Args:
            value: Valor raw del slot
            aliases: Diccionario de aliases

        Returns:
            Valor normalizado o None si no se reconoce
        """
        if not value:
            return None

        # Convertir a lowercase para comparacion
        value_lower = value.lower().strip()

        # Buscar en aliases
        normalized = aliases.get(value_lower)

        if normalized:
            return normalized

        # Si no se encuentra, intentar match parcial
        for alias, canonical in aliases.items():
            if alias in value_lower or value_lower in alias:
                return canonical

        # Si no se reconoce, usar el valor original
        self.logger.warning(
            f"Unrecognized value '{value}', using as-is",
            extra={'value': value, 'aliases_checked': len(aliases)}
        )
        return value_lower

    def _get_changed_fields(
        self,
        old_profile: UserProfile,
        new_profile: UserProfile
    ) -> list:
        """
        Identifica que campos cambiaron entre perfiles.

        Args:
            old_profile: Perfil anterior
            new_profile: Perfil nuevo

        Returns:
            Lista de nombres de campos que cambiaron
        """
        changed = []

        if old_profile.os != new_profile.os:
            changed.append('os')
        if old_profile.package_manager != new_profile.package_manager:
            changed.append('pm')
        if old_profile.editor != new_profile.editor:
            changed.append('editor')

        return changed

    def _build_confirmation_response(
        self,
        handler_input: HandlerInput,
        old_profile: UserProfile,
        new_profile: UserProfile
    ) -> Response:
        """
        Construye la respuesta de confirmacion con los cambios realizados.

        Args:
            handler_input: Input del request
            old_profile: Perfil anterior
            new_profile: Perfil nuevo

        Returns:
            Response de Alexa con confirmacion
        """
        changed_fields = self._get_changed_fields(old_profile, new_profile)

        # Construir mensaje segun cambios
        if not changed_fields:
            speak_output = (
                "Tu perfil ya tenia esos valores. "
                "No se hicieron cambios."
            )
        elif len(changed_fields) == 1:
            field = changed_fields[0]
            old_val = old_profile.get(field, 'no configurado')
            new_val = new_profile.get(field, 'desconocido')
            field_name = self._get_field_name(field)

            speak_output = (
                f"Perfecto. Actualice tu {field_name} "
                f"de {old_val} a {new_val}."
            )
        else:
            # Multiple campos cambiados
            changes = []
            for field in changed_fields:
                field_name = self._get_field_name(field)
                new_val = self._get_field_value(new_profile, field)
                changes.append(f"{field_name} a {new_val}")

            changes_text = ", ".join(changes[:-1]) + f" y {changes[-1]}"
            speak_output = f"Perfecto. Actualice tu {changes_text}."

        # Agregar informacion sobre personalizacion
        speak_output += (
            " Ahora las soluciones estaran personalizadas para tu entorno. "
            "¿En que puedo ayudarte?"
        )

        # Construir card con perfil completo
        card_title = "Perfil Actualizado"
        card_content = self._build_profile_card(new_profile, changed_fields)

        card = SimpleCard(title=card_title, content=card_content)

        return (
            handler_input.response_builder
            .speak(speak_output)
            .set_card(card)
            .ask("¿Necesitas diagnosticar algun error?")
            .response
        )

    def _get_field_name(self, field: str) -> str:
        """
        Obtiene el nombre amigable de un campo.

        Args:
            field: Nombre del campo (os, pm, editor)

        Returns:
            Nombre amigable
        """
        names = {
            'os': 'sistema operativo',
            'pm': 'gestor de paquetes',
            'editor': 'editor'
        }
        return names.get(field, field)

    def _get_field_value(self, profile: UserProfile, field: str) -> str:
        """
        Obtiene el valor de un campo del perfil.

        Args:
            profile: UserProfile
            field: Nombre del campo

        Returns:
            Valor del campo
        """
        if field == 'os':
            return profile.os.value
        elif field == 'pm':
            return profile.package_manager.value
        elif field == 'editor':
            return profile.editor.value
        return 'desconocido'

    def _build_profile_card(
        self,
        profile: UserProfile,
        changed_fields: list
    ) -> str:
        """
        Construye el contenido de la card con el perfil.

        Args:
            profile: Perfil actualizado
            changed_fields: Campos que cambiaron

        Returns:
            Texto formateado para la card
        """
        lines = [
            "Tu perfil tecnico actualizado:",
            "",
            f"Sistema Operativo: {profile.os.value.upper()}",
            f"Gestor de Paquetes: {profile.package_manager.value.upper()}",
            f"Editor: {profile.editor.value.upper()}",
            ""
        ]

        if changed_fields:
            lines.append("Campos actualizados:")
            for field in changed_fields:
                field_name = self._get_field_name(field)
                new_val = self._get_field_value(profile, field)
                lines.append(f"- {field_name.capitalize()}: {new_val.upper()}")
            lines.append("")

        lines.extend([
            "Las soluciones de diagnostico ahora estaran",
            "personalizadas para tu entorno.",
            "",
            "Para cambiar tu perfil en cualquier momento,",
            "di: 'uso [sistema] y [gestor de paquetes]'"
        ])

        return "\n".join(lines)

    def _handle_no_slots(self, handler_input: HandlerInput) -> Response:
        """
        Maneja el caso donde no se proporcionaron slots.

        Args:
            handler_input: Input del request

        Returns:
            Response solicitando informacion
        """
        self.logger.warning("SetProfileIntent called without slots")

        # Obtener perfil actual para mostrarlo
        current_profile = self.get_user_profile(handler_input)

        if current_profile:
            os_val = current_profile.get('os', 'no configurado')
            pm_val = current_profile.get('pm', 'no configurado')
            editor_val = current_profile.get('editor', 'no configurado')

            speak_output = (
                f"Actualmente usas {os_val}, {pm_val} y {editor_val}. "
                "¿Que quieres cambiar? Por ejemplo, di: uso windows y conda."
            )
        else:
            speak_output = (
                "Para configurar tu perfil, dime que sistema operativo, "
                "gestor de paquetes y editor usas. "
                "Por ejemplo: uso linux y pip con vscode."
            )

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )
