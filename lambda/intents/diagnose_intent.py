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

from typing import Optional
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response

from intents.base import BaseIntentHandler, require_profile
from models import Diagnostic, UserProfile, ErrorValidation
from utils import truncate_text, sanitize_ssml_text
from core.response_builder import AlexaResponseBuilder
from services.kb_service import kb_service
from services.ai_client import ai_service
from services.storage import storage_service


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
        from config.settings import MAX_VOICE_LENGTH
        return MAX_VOICE_LENGTH

    @property
    def MAX_CARD_LENGTH(self):
        """Obtiene longitud maxima de card desde settings."""
        from config.settings import MAX_CARD_LENGTH
        return MAX_CARD_LENGTH

    @property
    def CONFIDENCE_THRESHOLD(self):
        """Obtiene umbral de confianza desde settings."""
        from config.settings import KB_CONFIDENCE_THRESHOLD
        return KB_CONFIDENCE_THRESHOLD

    def __init__(self):
        """Inicializa el handler con servicios."""
        super().__init__()

        # Servicios de busqueda y almacenamiento
        self.kb_service = kb_service
        self.ai_service = ai_service
        self.storage_service = storage_service

        self.logger.info("DiagnoseIntentHandler initialized")

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
        Genera diagnostico usando KB o AI.

        Strategy Pattern: Selecciona fuente segun disponibilidad y confianza.

        Args:
            error_text: Texto del error
            user_profile: Perfil del usuario

        Returns:
            Diagnostic con informacion completa del error
        """
        self.logger.debug(f"Generating diagnostic for: {error_text[:30]}...")

        # Fase 1: Buscar en Knowledge Base local
        kb_result = self._search_knowledge_base(error_text, user_profile)

        if kb_result and kb_result.confidence >= self.CONFIDENCE_THRESHOLD:
            self.logger.info(
                "KB match found",
                extra={
                    'confidence': kb_result.confidence,
                    'error_type': kb_result.error_type
                }
            )
            return kb_result

        # Fase 2: Fallback a AI
        self.logger.info("KB confidence low, falling back to AI")
        ai_result = self._query_ai_service(error_text, user_profile)

        return ai_result

    def _search_knowledge_base(
        self,
        error_text: str,
        user_profile: UserProfile
    ) -> Optional[Diagnostic]:
        """
        Busca el error en la Knowledge Base local.

        Args:
            error_text: Texto del error
            user_profile: Perfil del usuario

        Returns:
            Diagnostico del KB o None si no hay match
        """
        self.logger.debug("Searching in Knowledge Base")

        try:
            # Buscar en KB usando el servicio
            diagnostic = self.kb_service.search_diagnostic(
                error_text, user_profile)

            if diagnostic:
                self.logger.info(
                    f"KB match found: {diagnostic.error_type} "
                    f"(confidence: {diagnostic.confidence:.2f})"
                )

            return diagnostic

        except Exception as e:
            self.logger.error(f"KB search failed: {e}", exc_info=True)
            return None

    def _query_ai_service(
        self,
        error_text: str,
        user_profile: UserProfile
    ) -> Diagnostic:
        """
        Consulta el servicio de AI (Bedrock o OpenAI).

        Args:
            error_text: Texto del error
            user_profile: Perfil del usuario

        Returns:
            Diagnostico generado por AI
        """
        self.logger.debug("Querying AI service")

        try:
            # Generar diagnostico usando AI service
            diagnostic = self.ai_service.generate_diagnostic(
                error_text, user_profile)

            if diagnostic:
                self.logger.info(
                    f"AI diagnostic generated: {diagnostic.error_type} "
                    f"(source: {diagnostic.source})"
                )
                return diagnostic

            # Fallback: diagnostico generico si AI falla
            self.logger.warning("AI service returned None, using fallback")
            return self._create_fallback_diagnostic(user_profile)

        except Exception as e:
            self.logger.error(f"AI service failed: {e}", exc_info=True)
            return self._create_fallback_diagnostic(user_profile)

    def _create_fallback_diagnostic(self, user_profile: UserProfile) -> Diagnostic:
        """
        Crea diagnostico fallback cuando KB y AI fallan.

        Args:
            user_profile: Perfil del usuario

        Returns:
            Diagnostico generico
        """
        from core.factories import DiagnosticFactory
        from models import ErrorType

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
        self.logger.info(f"Voice text length: {len(voice_text)} characters")

        # Sanitizar card content tambien
        card_content = sanitize_ssml_text(diagnostic.card_text or "")

        # Usar ResponseBuilder pattern
        response = (
            AlexaResponseBuilder(handler_input)
            .speak(voice_text)
            .simple_card(diagnostic.card_title, card_content)
            .ask("¿Quieres saber más o necesitas ayuda con algo más?")
            .build()
        )

        self.logger.info("Outgoing response for: IntentRequest")
        return response

    def _is_valid_error_description(self, error_text: str) -> bool:
        """
        Valida que el texto del error sea suficientemente descriptivo.

        Rechaza descripciones vagas como:
        - "un error muy específico y raro"
        - "un error"
        - "algo malo"
        - "no funciona"

        Args:
            error_text: Texto del error a validar

        Returns:
            bool: True si el error es suficientemente descriptivo
        """
        if not error_text or len(error_text.strip()) < 5:
            return False

        error_lower = error_text.lower().strip()

        for vague in ErrorValidation.VAGUE_PHRASES:
            if vague in error_lower:
                has_very_specific = any(
                    kw in error_lower for kw in ErrorValidation.SPECIFIC_ERROR_KEYWORDS
                )

                if not has_very_specific:
                    self.logger.warning(
                        f"Vague error description rejected: {error_text[:50]}"
                    )
                    return False

        if error_lower in ErrorValidation.TOO_VAGUE_EXACT:
            return False

        if len(error_text.strip()) < ErrorValidation.MIN_LENGTH_WITHOUT_KEYWORDS:
            has_specific = any(
                kw in error_lower for kw in ErrorValidation.SPECIFIC_ERROR_KEYWORDS
            )
            if not has_specific:
                self.logger.warning(
                    f"Too short and not specific: {error_text[:50]}"
                )
                return False

        has_specific = any(
            kw in error_lower for kw in ErrorValidation.SPECIFIC_ERROR_KEYWORDS
        )
        if not has_specific:
            self.logger.warning(
                f"No specific error keyword found: {error_text[:50]}"
            )
            return False

        return True

    def _handle_vague_error(self, handler_input: HandlerInput, error_text: str) -> Response:
        """
        Maneja descripciones de error vagas o poco útiles.

        Args:
            handler_input: Input del request
            error_text: Texto vago proporcionado

        Returns:
            Response solicitando más detalles
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
