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
from models import Diagnostic, UserProfile, DiagnosticSource
from utils import get_logger, truncate_text

# Importaciones que se crearan despues
# from services.kb_service import KnowledgeBaseService
# from services.ai_client import AIClient
# from core.response_builder import ResponseBuilder


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

        # Servicios (inicializar despues cuando esten creados)
        # self.kb_service = KnowledgeBaseService()
        # self.ai_client = AIClient()
        # self.response_builder = ResponseBuilder()

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

        TODO: Implementar cuando KnowledgeBaseService este listo.

        Args:
            error_text: Texto del error
            user_profile: Perfil del usuario

        Returns:
            Diagnostico del KB o None si no hay match
        """
        # Stub: Retornar un diagnostico de ejemplo
        # En produccion, esto llamara a self.kb_service.search()

        self.logger.debug("Searching in Knowledge Base (stub)")

        # Simulacion de KB search
        # TODO: Reemplazar con: return self.kb_service.search(error_text, user_profile)

        # Por ahora, retornar None para forzar AI fallback
        return None

    def _query_ai_service(
        self,
        error_text: str,
        user_profile: UserProfile
    ) -> Diagnostic:
        """
        Consulta el servicio de AI (Bedrock o OpenAI).

        TODO: Implementar cuando AIClient este listo.

        Args:
            error_text: Texto del error
            user_profile: Perfil del usuario

        Returns:
            Diagnostico generado por AI
        """
        self.logger.debug("Querying AI service (stub)")

        # Stub: Retornar un diagnostico de ejemplo
        # En produccion: return self.ai_client.diagnose(error_text, user_profile)

        # Diagnostico de ejemplo para desarrollo
        return Diagnostic(
            error_type='ModuleNotFoundError',
            voice_text=(
                "Parece ser un error de modulo no encontrado. "
                "Esto ocurre cuando Python no puede importar un paquete. "
                "Instalalo con tu gestor de paquetes."
            ),
            card_title='Error: Modulo no encontrado',
            card_text=(
                f"**Diagnostico**: ModuleNotFoundError\n\n"
                f"**Causa**: El paquete no esta instalado en tu entorno.\n\n"
                f"**Solucion para {user_profile.os.value}**:\n"
                f"1. Instala el paquete con: '{user_profile.package_manager.value} install <paquete>'\n"
                f"2. Verifica que estes en el entorno virtual correcto\n"
                f"3. Revisa el archivo requirements.txt\n\n"
                f"**Mas ayuda**: Di 'por que pasa esto' para mas detalles."
            ),
            confidence=0.85,
            source=DiagnosticSource.AI_SERVICE.value,
            solutions=[
                f"Ejecuta: {user_profile.package_manager.value} install <nombre_paquete>",
                "Verifica que el entorno virtual este activado",
                "Revisa requirements.txt y sincroniza dependencias"
            ],
            explanation=(
                "Python busca modulos en sys.path. Si el paquete no esta "
                "instalado o el entorno es incorrecto, lanza ModuleNotFoundError."
            )
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
        return (
            handler_input.response_builder
            .speak(voice_text)
            .set_card(
                title=diagnostic.card_title,
                content=diagnostic.card_text
            )
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
