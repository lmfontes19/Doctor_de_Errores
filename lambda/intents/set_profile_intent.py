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

from typing import Optional, Tuple
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from ask_sdk_model.ui import SimpleCard

from intents.base import BaseIntentHandler
from models import UserProfile, OperatingSystem, PackageManager, Editor


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

    def __init__(self):
        """Inicializa el handler."""
        super().__init__()

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
        Coordina el flujo de configuracion del perfil.

        Responsabilidad: Orquestar las validaciones y actualizaciones,
        delegando tareas especificas a metodos especializados.

        Args:
            handler_input: Input del request de Alexa

        Returns:
            Response: Respuesta con confirmacion de cambios o diagnostico
        """
        # 1. Extraer y validar slots
        validation_result = self._extract_and_validate_slots(handler_input)

        if validation_result.get('error_response'):
            return validation_result['error_response']

        # 2. Actualizar perfil
        current_profile = self.get_user_profile(handler_input)
        new_profile = self._update_profile(
            handler_input,
            current_profile,
            validation_result['so_value'],
            validation_result['pm_value'],
            validation_result['editor_value']
        )

        # 3. Persistir perfil (sesion + futuro DynamoDB)
        self._persist_profile(handler_input, new_profile)

        # 4. Verificar y procesar error pendiente (si existe)
        pending_error = self.get_session_attribute(
            handler_input, 'pending_error_text')

        if pending_error:
            return self._handle_pending_diagnostic(
                handler_input,
                new_profile,
                pending_error
            )

        # 5. Respuesta normal de confirmacion
        return self._build_confirmation_response(
            handler_input,
            current_profile,
            new_profile
        )

    def _extract_and_validate_slots(self, handler_input: HandlerInput) -> dict:
        """
        Extrae y valida los slots del request.

        Responsabilidad: Validacion de entrada del usuario.

        Args:
            handler_input: Input del request de Alexa

        Returns:
            dict con valores validados o error_response si hay error
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

        # Validar valores usando los métodos from_string de los Enums
        so_value, so_valid = self._validate_os(
            so_slot) if so_slot else (None, True)
        pm_value, pm_valid = self._validate_pm(
            pm_slot) if pm_slot else (None, True)
        editor_value, editor_valid = self._validate_editor(
            editor_slot) if editor_slot else (None, True)

        # Deteccion especial: editor en slot de PM
        if pm_slot and not pm_valid:
            editor_test = Editor.from_string(pm_slot)
            if editor_test != Editor.UNKNOWN:
                self.logger.warning(f"User confused editor with PM: {pm_slot}")
                return {
                    'error_response': (
                        handler_input.response_builder
                        .speak(
                            f"Veo que mencionaste '{pm_slot}', pero ese es un editor, no un gestor de paquetes. "
                            f"Los gestores de paquetes son: pip, conda o poetry. "
                            f"Por favor, dime de nuevo tu configuracion. Por ejemplo: 'uso Windows y pip'."
                        )
                        .ask("¿Que sistema operativo y gestor de paquetes usas? Por ejemplo: Windows con pip")
                        .response
                    )
                }

        self.logger.info(
            "SetProfileIntent - After validation",
            extra={
                'so_value': so_value, 'so_valid': so_valid,
                'pm_value': pm_value, 'pm_valid': pm_valid,
                'editor_value': editor_value, 'editor_valid': editor_valid
            }
        )

        # Validar que todos los slots sean validos
        if not (so_valid and pm_valid and editor_valid):
            return {'error_response': self._build_validation_error_response(
                handler_input, so_slot, pm_slot, editor_slot,
                so_valid, pm_valid, editor_valid
            )}

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
            return {'error_response': self._handle_no_slots(handler_input)}

        return {
            'so_value': so_value,
            'pm_value': pm_value,
            'editor_value': editor_value
        }

    def _build_validation_error_response(
        self,
        handler_input: HandlerInput,
        so_slot: Optional[str],
        pm_slot: Optional[str],
        editor_slot: Optional[str],
        so_valid: bool,
        pm_valid: bool,
        editor_valid: bool
    ) -> Response:
        """
        Construye respuesta de error de validacion.

        Responsabilidad: Generar mensajes de error claros para el usuario.

        Args:
            handler_input: Input del request
            so_slot, pm_slot, editor_slot: Valores de slots
            so_valid, pm_valid, editor_valid: Flags de validez

        Returns:
            Response con mensaje de error
        """
        invalid_items = []
        if not so_valid:
            invalid_items.append(
                f"'{so_slot}' no es un sistema operativo valido")
            self.logger.warning(f"Invalid OS: {so_slot}")
        if not pm_valid:
            invalid_items.append(
                f"'{pm_slot}' no es un gestor de paquetes valido como pip, conda o poetry"
            )
            self.logger.warning(f"Invalid PM: {pm_slot}")
        if not editor_valid:
            invalid_items.append(f"'{editor_slot}' no es un editor reconocido")
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

    def _update_profile(
        self,
        handler_input: HandlerInput,
        current_profile: UserProfile,
        so_value: Optional[str],
        pm_value: Optional[str],
        editor_value: Optional[str]
    ) -> UserProfile:
        """
        Actualiza el perfil con los nuevos valores.

        Responsabilidad: Logica de actualizacion del modelo de perfil.

        Args:
            handler_input: Input del request
            current_profile: Perfil actual del usuario
            so_value, pm_value, editor_value: Nuevos valores validados

        Returns:
            UserProfile actualizado
        """
        new_profile = current_profile.update(
            os=so_value if so_value else None,
            pm=pm_value if pm_value else None,
            editor=editor_value if editor_value else None
        )

        self.logger.info(
            "Profile updated",
            extra={
                'old_profile': current_profile.to_dict(),
                'new_profile': new_profile.to_dict(),
                'changed_fields': self._get_changed_fields(current_profile, new_profile)
            }
        )

        return new_profile

    def _persist_profile(self, handler_input: HandlerInput, profile: UserProfile) -> None:
        """
        Persiste el perfil en sesion y DynamoDB.

        Responsabilidad: Delega al metodo base que maneja toda la logica
        de persistencia (sesion + DynamoDB con manejo de errores).

        Args:
            handler_input: Input del request
            profile: Perfil a persistir
        """
        self.save_user_profile(handler_input, profile)

    def _handle_pending_diagnostic(
        self,
        handler_input: HandlerInput,
        new_profile: UserProfile,
        pending_error: str
    ) -> Response:
        """
        Procesa un error pendiente despues de configurar el perfil.

        Responsabilidad: Coordinacion del flujo de diagnostico post-configuracion.

        Args:
            handler_input: Input del request
            new_profile: Perfil recien configurado
            pending_error: Texto del error pendiente

        Returns:
            Response con confirmacion de perfil + diagnostico
        """
        # Limpiar el error pendiente
        self.set_session_attribute(handler_input, 'pending_error_text', None)

        self.logger.info(
            "Processing pending error after profile setup",
            extra={'error_text': pending_error[:50]}
        )

        # Generar diagnostico
        diagnostic = self._generate_diagnostic(pending_error, new_profile)

        # Guardar en sesion
        self.save_last_diagnostic(handler_input, diagnostic)

        # Construir respuesta combinada
        return self._build_profile_with_diagnostic_response(
            handler_input,
            new_profile,
            diagnostic
        )

    def _generate_diagnostic(self, error_text: str, profile: UserProfile):
        """
        Genera un diagnostico usando Strategy Pattern.

        Responsabilidad: Delegacion a cadena de estrategias de diagnostico.

        Args:
            error_text: Texto del error
            profile: Perfil del usuario

        Returns:
            Diagnostic object
        """
        from core.diagnostic_strategies import create_default_strategy_chain

        # Usar Strategy Pattern
        strategy_chain = create_default_strategy_chain()
        diagnostic = strategy_chain.search_diagnostic(error_text, profile)

        # Fallback si todas las estrategias fallan
        if not diagnostic:
            self.logger.warning("All strategies failed in profile setup flow")
            from core.factories import DiagnosticFactory
            from models import ErrorType
            diagnostic = DiagnosticFactory.create_error_diagnostic(
                error_message="No se pudo diagnosticar el error",
                error_type=ErrorType.GENERIC_ERROR.value
            )

        return diagnostic

    def _build_profile_with_diagnostic_response(
        self,
        handler_input: HandlerInput,
        profile: UserProfile,
        diagnostic
    ) -> Response:
        """
        Construye respuesta que combina confirmacion de perfil y diagnostico.

        Responsabilidad: Generacion de respuesta combinada para flujo continuo.

        Args:
            handler_input: Input del request
            profile: Perfil configurado
            diagnostic: Diagnostico generado

        Returns:
            Response combinada
        """
        from utils import sanitize_ssml_text, truncate_text
        from config.settings import MAX_VOICE_LENGTH

        profile_msg = f"Perfecto. Configure tu perfil para {profile.os.value} con {profile.package_manager.value}. "

        # Procesar mensaje de diagnostico
        diagnostic_msg = sanitize_ssml_text(
            diagnostic.voice_text or "Detecte el error.")
        diagnostic_msg = truncate_text(diagnostic_msg, max_length=200)

        speak_output = profile_msg + f"Ahora, sobre tu error: {diagnostic_msg}"
        speak_output = truncate_text(speak_output, max_length=MAX_VOICE_LENGTH)

        # Construir card
        card_content = sanitize_ssml_text(
            diagnostic.card_text or "Ver diagnostico completo")
        card_content = truncate_text(card_content, max_length=800)
        card_title = truncate_text(
            diagnostic.card_title or "Diagnostico", max_length=100)

        card = SimpleCard(title=card_title, content=card_content)

        return (
            handler_input.response_builder
            .speak(speak_output)
            .set_card(card)
            .ask("¿Quieres saber por que ocurre esto o necesitas mas soluciones?")
            .response
        )

    def _validate_os(self, value: str) -> Tuple[Optional[str], bool]:
        """
        Valida y normaliza un sistema operativo usando OperatingSystem.from_string().

        Args:
            value: Valor raw del slot

        Returns:
            Tupla (valor_normalizado, es_valido)
        """
        if not value:
            return None, True

        os_enum = OperatingSystem.from_string(value)
        if os_enum == OperatingSystem.UNKNOWN:
            self.logger.warning(f"Invalid OS value: '{value}'")
            return value.lower(), False

        return os_enum.value, True

    def _validate_pm(self, value: str) -> Tuple[Optional[str], bool]:
        """
        Valida y normaliza un gestor de paquetes usando PackageManager.from_string().

        Args:
            value: Valor raw del slot

        Returns:
            Tupla (valor_normalizado, es_valido)
        """
        if not value:
            return None, True

        pm_enum = PackageManager.from_string(value)
        if pm_enum == PackageManager.UNKNOWN:
            self.logger.warning(f"Invalid PM value: '{value}'")
            return value.lower(), False

        return pm_enum.value, True

    def _validate_editor(self, value: str) -> Tuple[Optional[str], bool]:
        """
        Valida y normaliza un editor usando Editor.from_string().

        Args:
            value: Valor raw del slot

        Returns:
            Tupla (valor_normalizado, es_valido)
        """
        if not value:
            return None, True

        editor_enum = Editor.from_string(value)
        if editor_enum == Editor.UNKNOWN:
            self.logger.warning(f"Invalid editor value: '{value}'")
            return value.lower(), False

        return editor_enum.value, True

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
        if field == 'pm':
            return profile.package_manager.value
        if field == 'editor':
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
