"""
Handler para el intent DiagnoseIntent.

Este intent es el corazon de la skill Doctor de Errores. Recibe un mensaje
de error del usuario y proporciona un diagnostico con soluciones.

Flujo:
1. Extrae el texto de error del slot "errorText"
2. Busca en la Knowledge Base local primero
3. Si no encuentra match (confianza < umbral), consulta AI (Bedrock/OpenAI)
4. Retorna diagnostico con voz + card
5. Guarda el diagnostico en sesion para intents subsecuentes (Why, More)

Patterns:
- Template Method (hereda de BaseIntentHandler)
- Strategy (seleccion de fuente: KB vs AI)
- Builder (construccion de respuesta)
"""

from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response

from intents.base import BaseIntentHandler, require_profile
from models import Diagnostic, UserProfile, ErrorValidation, ErrorType
from utils import truncate_text, sanitize_ssml_text

from core.response_builder import AlexaResponseBuilder
from core.diagnostic_strategies import create_default_strategy_chain
from core.factories import DiagnosticFactory

from config.settings import MAX_VOICE_LENGTH, KB_CONFIDENCE_THRESHOLD, MAX_CARD_LENGTH


class DiagnoseIntentHandler(BaseIntentHandler):
    """
    Handler para diagnosticar errores de programacion.

    Este es el intent principal de la skill. Recibe descripciones de errores
    y proporciona diagnosticos con soluciones personalizadas segun el perfil
    del usuario (OS, package manager, editor).

    Features:
    - Busqueda en Knowledge Base local (rapido, offline)
    - Fallback a AI (Bedrock/OpenAI) si KB no tiene match
    - Respuestas personalizadas segun perfil de usuario
    - Cache de diagnostico en sesion para follow-ups

    Attributes:
        intent_name: "DiagnoseIntent"

    Session Attributes Usados:
        - user_profile: Perfil del usuario (os, pm, editor)
        - last_diagnostic: ultimo diagnostico generado
        - diagnostic_source: Fuente del diagnostico (kb o ai)

    Slot Required:
        - errorText: Descripcion del error (AMAZON.SearchQuery)
    """

    @property
    def MAX_VOICE_LENGTH(self):
        """Obtiene longitud maxima de voz desde settings."""
        return MAX_VOICE_LENGTH

    @property
    def MAX_CARD_LENGTH(self):
        """Obtiene longitud maxima de card desde settings."""
        return MAX_CARD_LENGTH

    @property
    def CONFIDENCE_THRESHOLD(self):
        """Obtiene umbral de confianza desde settings."""
        return KB_CONFIDENCE_THRESHOLD

    def __init__(self):
        """Inicializa el handler con cadena de estrategias."""
        super().__init__()

        # Strategy Pattern: Cadena de estrategias de diagnostico
        self.strategy_chain = create_default_strategy_chain()

        self.logger.info(
            "DiagnoseIntentHandler initialized")

    @property
    def intent_name(self) -> str:
        """Nombre del intent."""
        return "DiagnoseIntent"

    @require_profile
    def handle_intent(self, handler_input: HandlerInput) -> Response:
        """
        Maneja el diagnostico de errores.

        Args:
            handler_input: Input del request de Alexa

        Returns:
            Response: Respuesta con diagnostico
        """
        # Extraer slot de error
        error_text = self.get_slot_value(handler_input, "errorText")

        if not error_text:
            return self._handle_missing_error(handler_input)

        # Validar que el texto del error sea descriptivo
        if not self._is_valid_error_description(error_text):
            return self._handle_vague_error(handler_input, error_text)

        # Obtener perfil de usuario
        user_profile = self.get_user_profile(handler_input)

        self.logger.info(
            "Processing diagnostic request",
            extra={
                'error_text': error_text[:50],
                'user_os': user_profile.os.value
            }
        )

        # Generar diagnostico
        diagnostic = self._generate_diagnostic(error_text, user_profile)

        # Guardar en sesion para follow-ups
        self.save_last_diagnostic(handler_input, diagnostic)

        # Guardar en historial persistente (mejor esfuerzo)
        try:
            user_id = handler_input.request_envelope.session.user.user_id
            self.storage_service.save_diagnostic_history(user_id, diagnostic)
        except Exception as e:
            self.logger.warning(f"Failed to save diagnostic to history: {e}")

        # Construir respuesta
        return self._build_diagnostic_response(
            handler_input,
            diagnostic,
            error_text
        )

    def _generate_diagnostic(
        self,
        error_text: str,
        user_profile: UserProfile
    ) -> Diagnostic:
        """
        Genera diagnostico usando Strategy Pattern con Chain of Responsibility.

        Delega la busqueda a la cadena de estrategias que ejecuta:
        1. KnowledgeBaseStrategy (rapido, gratis, preciso)
        2. CachedAIDiagnosticStrategy (rapido, gratis, reutiliza)
        3. LiveAIDiagnosticStrategy (lento, costoso, flexible + cache)

        Args:
            error_text: Texto del error
            user_profile: Perfil del usuario

        Returns:
            Diagnostic con informacion completa del error
        """
        self.logger.debug(f"Generating diagnostic for: {error_text[:30]}...")

        # Ejecutar cadena de estrategias
        diagnostic = self.strategy_chain.search_diagnostic(
            error_text,
            user_profile
        )

        # Fallback si todas las estrategias fallan
        if not diagnostic:
            self.logger.warning("All strategies failed, using fallback")
            diagnostic = self._create_fallback_diagnostic(user_profile)

        return diagnostic

    def _create_fallback_diagnostic(self, user_profile: UserProfile) -> Diagnostic:
        """
        Crea diagnostico fallback cuando KB y AI fallan.

        Args:
            user_profile: Perfil del usuario

        Returns:
            Diagnostico generico
        """
        return DiagnosticFactory.create_error_diagnostic(
            error_message="No se pudo diagnosticar el error especifico",
            error_type=ErrorType.GENERIC_ERROR.value
        )

    def _build_diagnostic_response(
        self,
        handler_input: HandlerInput,
        diagnostic: Diagnostic,
        original_error: str
    ) -> Response:
        """
        Construye la respuesta de Alexa con el diagnostico.

        Args:
            handler_input: Input del request
            diagnostic: Diagnostico generado
            original_error: Texto original del error

        Returns:
            Response de Alexa con voz y card
        """
        # Sanitizar y truncar texto de voz
        voice_text = sanitize_ssml_text(diagnostic.voice_text or "")
        voice_text = truncate_text(
            voice_text,
            max_length=self.MAX_VOICE_LENGTH
        )

        # Anhadir prompt para follow-up
        voice_text += (
            " Quieres saber por que ocurre esto o necesitas mas opciones?"
        )

        # Log del diagnostico
        self.logger_manager.log_diagnostic(
            error_type=diagnostic.error_type,
            confidence=diagnostic.confidence,
            source=diagnostic.source
        )

        self.logger.info(f"Voice text to speak: '{voice_text[:100]}...'")
        self.logger.info(
            f"Voice text length: {len(voice_text)} characters")

        # Sanitizar card content tambien
        card_content = sanitize_ssml_text(diagnostic.card_text or "")

        # Usar ResponseBuilder pattern
        response = (
            AlexaResponseBuilder(handler_input)
            .speak(voice_text)
            .simple_card(diagnostic.card_title, card_content)
            .ask("¿Quieres saber mas o necesitas ayuda con algo mas?")
            .build()
        )

        self.logger.info("Outgoing response for: IntentRequest")
        return response

    def _is_valid_error_description(self, error_text: str) -> bool:
        """
        Valida que el texto del error sea suficientemente descriptivo.

        Usa el nuevo sistema de validacion basado en patrones que detecta:
        - Excepciones de Python (NameError, ImportError, etc.)
        - Frases "not found", "cannot do"
        - Imports de modulos
        - Errores de sintaxis
        - Acceso a atributos
        - Notacion tecnica (package.module, snake_case)
        - Tracebacks

        Rechaza solo descripciones EXTREMADAMENTE vagas:
        - Textos muy cortos (< 5 chars)
        - Frases exactas como "error", "no funciona", "ayuda"

        Args:
            error_text: Texto del error a validar

        Returns:
            bool: True si el error es suficientemente descriptivo
        """
        is_valid, message = ErrorValidation.is_specific_enough(error_text)

        if not is_valid:
            self.logger.warning(
                f"Error description rejected: {error_text[:50]} - Reason: {message}"
            )

        return is_valid

    def _handle_vague_error(self, handler_input: HandlerInput, error_text: str) -> Response:
        """
        Maneja descripciones de error vagas o poco utiles.

        Args:
            handler_input: Input del request
            error_text: Texto vago proporcionado

        Returns:
            Response solicitando mas detalles
        """
        self.logger.info(
            "Vague error description provided",
            extra={'error_text': error_text[:50]}
        )

        speak_output = (
            "Entiendo que tienes un error, pero necesito mas detalles especificos. "
            "¿Que mensaje de error exacto ves? "
            "Por ejemplo: module not found error, syntax error en la linea 10, "
            "name error nombre no definido, o file not found."
        )

        reprompt = (
            "¿Cual es el mensaje de error especifico que aparece?"
        )

        # Mantener flag para capturar la respuesta
        session_attr = handler_input.attributes_manager.session_attributes
        session_attr['awaiting_error_description'] = True

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(reprompt)
            .response
        )

    def _handle_missing_error(self, handler_input: HandlerInput) -> Response:
        """
        Maneja el caso donde no se proporciona texto de error.

        Args:
            handler_input: Input del request

        Returns:
            Response solicitando el error
        """
        self.logger.warning("DiagnoseIntent called without errorText slot")

        session_attr = handler_input.attributes_manager.session_attributes
        session_attr['awaiting_error_description'] = True

        speak_output = (
            "Claro, puedo ayudarte con tu codigo. "
            "¿Que error estas viendo? "
            "Por ejemplo, puedes decir: tengo un error module not found, "
            "o syntax error, o mi codigo no compila."
        )

        reprompt = (
            "¿Que mensaje de error aparece cuando ejecutas tu codigo?"
        )

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(reprompt)
            .response
        )
