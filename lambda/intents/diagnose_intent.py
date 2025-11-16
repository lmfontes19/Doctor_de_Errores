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
from ask_sdk_model.ui import SimpleCard

from intents.base import BaseIntentHandler, require_profile
from models import Diagnostic, UserProfile, DiagnosticSource
from utils import get_logger, truncate_text
from core.response_builder import diagnostic_response
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

    # Configuracion
    CONFIDENCE_THRESHOLD = 0.70  # Umbral para KB match
    MAX_VOICE_LENGTH = 300      # Caracteres maximos para voz
    MAX_CARD_LENGTH = 1000      # Caracteres maximos para card

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

        # Obtener perfil de usuario
        user_profile = self.get_user_profile(handler_input)

        self.logger.info(
            f"Processing diagnostic request",
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
                f"KB match found",
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
            else:
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

        TODO: Usar ResponseBuilder cuando este implementado.

        Args:
            handler_input: Input del request
            diagnostic: Diagnostico generado
            original_error: Texto original del error

        Returns:
            Response de Alexa con voz y card
        """
        # Truncar texto de voz si es necesario
        voice_text = truncate_text(
            diagnostic.voice_text,
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

        # Construir respuesta
        # TODO: Usar ResponseBuilder pattern cuando este listo
        # return self.response_builder
        #     .speak(voice_text)
        #     .card(diagnostic.card_title, diagnostic.card_text)
        #     .reprompt("Necesitas algo mas?")
        #     .build()

        # Por ahora, usar el builder basico de ask_sdk
        card = SimpleCard(
            title=diagnostic.card_title,
            content=diagnostic.card_text
        )

        return (
            handler_input.response_builder
            .speak(voice_text)
            .set_card(card)
            .ask("Necesitas algo mas?")
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

        speak_output = (
            "No escuche bien el error. "
            "Por favor, dime que error estas teniendo. "
            "Por ejemplo: tengo un error module not found."
        )

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )
