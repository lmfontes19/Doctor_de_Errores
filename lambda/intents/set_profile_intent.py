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

from typing import Dict, Any, Optional, Tuple
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
        try:
            return self._handle_profile_configuration(handler_input)
        except Exception as e:
            self.logger.error(
                f"Error in SetProfileIntent: {str(e)}", exc_info=True)
            return (
                handler_input.response_builder
                .speak(
                    "Lo siento, tuve un problema configurando tu perfil. "
                    "Por favor, intentalo de nuevo diciendo, por ejemplo: "
                    "'uso Windows y pip'."
                )
                .ask("¿Que sistema operativo y gestor de paquetes usas?")
                .response
            )

    def _handle_profile_configuration(self, handler_input: HandlerInput) -> Response:
        """
        Logica interna para configurar el perfil.

        Args:
            handler_input: Input del request de Alexa

        Returns:
            Response: Respuesta con confirmacion de cambios
        """
        # Extraer slots
        so_slot = self.get_slot_value(handler_input, 'so')
        pm_slot = self.get_slot_value(handler_input, 'pm')
        editor_slot = self.get_slot_value(handler_input, 'editor')

        self.logger.info(
            "SetProfileIntent - Slots received",
            extra={
                'so_slot': so_slot,
                'pm_slot': pm_slot,
                'editor_slot': editor_slot
            }
        )

        # Normalizar y validar valores
        so_value, so_valid = self._validate_and_normalize(
            so_slot, self.OS_ALIASES, 'sistema operativo') if so_slot else (None, True)
        pm_value, pm_valid = self._validate_and_normalize(
            pm_slot, self.PM_ALIASES, 'gestor de paquetes') if pm_slot else (None, True)
        editor_value, editor_valid = self._validate_and_normalize(
            editor_slot, self.EDITOR_ALIASES, 'editor') if editor_slot else (None, True)

        # Deteccion especial: si pm_slot contiene un editor conocido, avisar especificamente
        if pm_slot and not pm_valid:
            pm_lower = pm_slot.lower()
            if pm_lower in ['vscode', 'pycharm', 'jupyter', 'vim', 'code', 'visual studio code']:
                self.logger.warning(f"User confused editor with PM: {pm_slot}")
                error_msg = (
                    f"Veo que mencionaste '{pm_slot}', pero ese es un editor, no un gestor de paquetes. "
                    f"Los gestores de paquetes son: pip, conda o poetry. "
                    f"Por favor, dime de nuevo tu configuracion. Por ejemplo: 'uso Windows y pip'."
                )
                return (
                    handler_input.response_builder
                    .speak(error_msg)
                    .ask("¿Que sistema operativo y gestor de paquetes usas? Por ejemplo: Windows con pip")
                    .response
                )

        self.logger.info(
            "SetProfileIntent - After validation",
            extra={
                'so_value': so_value, 'so_valid': so_valid,
                'pm_value': pm_value, 'pm_valid': pm_valid,
                'editor_value': editor_value, 'editor_valid': editor_valid
            }
        )        # Si hay valores invalidos, reportar error con logging
        if not (so_valid and pm_valid and editor_valid):
            invalid_items = []
            if not so_valid:
                invalid_items.append(
                    f"'{so_slot}' no es un sistema operativo valido")
                self.logger.warning(f"Invalid OS: {so_slot}")
            if not pm_valid:
                invalid_items.append(
                    f"'{pm_slot}' no es un gestor de paquetes valido como pip, conda o poetry")
                self.logger.warning(f"Invalid PM: {pm_slot}")
            if not editor_valid:
                invalid_items.append(
                    f"'{editor_slot}' no es un editor reconocido")
                self.logger.warning(f"Invalid editor: {editor_slot}")

            error_msg = "Lo siento, " + ", ".join(invalid_items) + ". "
            error_msg += "Por favor, intentalo de nuevo. Di, por ejemplo: 'uso Windows y pip' o 'uso Linux con conda'."

            self.logger.info(f"Returning validation error: {error_msg}")

            return (
                handler_input.response_builder
                .speak(error_msg)
                .ask("¿Que sistema operativo y gestor de paquetes usas?")
                .response
            )

        # Verificar que al menos un slot valido este presente
        if not any([so_value, pm_value, editor_value]):
            self.logger.warning(
                "No valid slots provided",
                extra={
                    'so_slot': so_slot,
                    'pm_slot': pm_slot,
                    'editor_slot': editor_slot
                }
            )
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

        # Verificar si hay un error pendiente para diagnosticar
        pending_error = self.get_session_attribute(
            handler_input, 'pending_error_text')

        if pending_error:
            # Limpiar el error pendiente
            self.set_session_attribute(
                handler_input, 'pending_error_text', None)

            # Importar aqui para evitar dependencia circular
            from intents.diagnose_intent import DiagnoseIntentHandler

            # Crear un DiagnoseIntent handler y procesarlo
            diagnose_handler = DiagnoseIntentHandler()

            self.logger.info(
                f"Processing pending error after profile setup",
                extra={'error_text': pending_error[:50]}
            )

            # Simular el diagnostico directamente
            from models import Diagnostic
            from services.kb_service import kb_service
            from services.ai_client import ai_service

            # Generar diagnostico
            kb_result = kb_service.search_diagnostic(
                pending_error, new_profile)

            if kb_result and kb_result.confidence >= 0.60:
                diagnostic = kb_result
            else:
                diagnostic = ai_service.diagnose(pending_error, new_profile)

            # Guardar en sesion
            self.save_last_diagnostic(handler_input, diagnostic)

            # Construir respuesta con perfil + diagnostico (con limites de longitud)
            profile_msg = f"Perfecto. Configure tu perfil para {new_profile.os.value} con {new_profile.package_manager.value}. "

            # Sanitizar y truncar voice_text
            diagnostic_msg = diagnostic.voice_text or "Detecte el error."
            # Escapar caracteres problematicos para SSML
            diagnostic_msg = diagnostic_msg.replace(
                '&', 'y').replace('<', '').replace('>', '')
            diagnostic_msg = diagnostic_msg.replace('"', '').replace("'", '')

            if len(diagnostic_msg) > 200:
                diagnostic_msg = diagnostic_msg[:197] + "..."

            speak_output = profile_msg + \
                f"Ahora, sobre tu error: {diagnostic_msg}"

            # Asegurar que el total no exceda ~600 caracteres
            if len(speak_output) > 600:
                speak_output = speak_output[:597] + "..."

            self.logger.info(f"speak_output length: {len(speak_output)}")
            self.logger.info(f"speak_output preview: {speak_output[:100]}...")

            # Construir card con limites y sanitizacion
            card_text = diagnostic.card_text or "Ver diagnostico completo"
            # Sanitizar para card tambien
            card_text = card_text.replace('&', 'y')
            if len(card_text) > 800:
                card_text = card_text[:797] + "..."

            card_title = diagnostic.card_title[:
                                               100] if diagnostic.card_title else "Diagnostico"

            try:
                card = SimpleCard(
                    title=card_title,
                    content=card_text
                )
            except Exception as card_error:
                self.logger.error(f"Error creating card: {card_error}")
                # Fallback: card simple sin contenido problematico
                card = SimpleCard(
                    title="Diagnostico",
                    content="Configuracion guardada. Tu error ha sido diagnosticado."
                )

            return (
                handler_input.response_builder
                .speak(speak_output)
                .set_card(card)
                .ask("¿Quieres saber por que ocurre esto o necesitas mas soluciones?")
                .response
            )

        # Si no hay error pendiente, respuesta normal
        return self._build_confirmation_response(
            handler_input,
            current_profile,
            new_profile
        )

    def _validate_and_normalize(self, value: str, aliases: Dict[str, str], field_name: str) -> Tuple[Optional[str], bool]:
        """
        Valida y normaliza un valor usando el diccionario de aliases.

        Args:
            value: Valor raw del slot
            aliases: Diccionario de aliases
            field_name: Nombre del campo para logging

        Returns:
            Tupla (valor_normalizado, es_valido)
        """
        if not value:
            return None, True

        # Convertir a lowercase para comparacion
        value_lower = value.lower().strip()

        # Buscar en aliases (exact match)
        normalized = aliases.get(value_lower)
        if normalized:
            return normalized, True

        # Si no se encuentra, intentar match parcial
        for alias, canonical in aliases.items():
            if alias in value_lower or value_lower in alias:
                return canonical, True

        # No se reconoce - valor invalido
        self.logger.warning(
            f"Invalid {field_name} value: '{value}'",
            extra={'value': value, 'field': field_name}
        )
        return value_lower, False

    def _normalize_value(self, value: str, aliases: Dict[str, str]) -> Optional[str]:
        """
        Normaliza un valor usando el diccionario de aliases (sin validacion estricta).
        Mantiene compatibilidad con codigo legacy.

        Args:
            value: Valor raw del slot
            aliases: Diccionario de aliases

        Returns:
            Valor normalizado o None si no se reconoce
        """
        normalized, _ = self._validate_and_normalize(value, aliases, "field")
        return normalized

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
        is_first_config = not old_profile.is_configured

        # Construir mensaje segun cambios
        if not changed_fields and not is_first_config:
            speak_output = (
                "Tu perfil ya tenia esos valores. "
                "No se hicieron cambios."
            )
        elif is_first_config:
            # Primera configuracion
            os_val = self._get_field_value(new_profile, 'os')
            pm_val = self._get_field_value(new_profile, 'pm')

            speak_output = (
                f"Perfecto. He configurado tu perfil para {os_val} "
                f"con {pm_val}."
            )
        elif len(changed_fields) == 1:
            field = changed_fields[0]
            old_val = self._get_field_value(old_profile, field)
            new_val = self._get_field_value(new_profile, field)
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

        if current_profile and current_profile.is_configured:
            os_val = current_profile.os.value
            pm_val = current_profile.package_manager.value
            editor_val = current_profile.editor.value

            speak_output = (
                f"Actualmente usas {os_val}, {pm_val} y {editor_val}. "
                "¿Que quieres cambiar? Por ejemplo, di: uso windows y conda."
            )
        else:
            speak_output = (
                "Para configurar tu perfil, dime que sistema operativo "
                "y gestor de paquetes usas. "
                "Por ejemplo: uso Windows y pip, o uso Linux con conda."
            )

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )
