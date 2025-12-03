"""
Handler para el intent WhyIntent.

Este intent proporciona la explicacion tecnica detallada de por que ocurre
un error, basandose en el ultimo diagnostico. Es un follow-up intent
educativo que ayuda al usuario a entender la causa raiz del problema.

Flujo:
1. Verifica que exista un diagnostico previo en sesion
2. Lee la explicacion tecnica del diagnostico
3. Formatea la explicacion para voz (simplificada)
4. Envia card con explicacion completa y causas comunes
5. Sugiere siguiente paso (mas soluciones, enviar card)

Patterns:
- Template Method (hereda de BaseIntentHandler)
- Decorator (enriquece diagnostico con contexto educativo)
"""

from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response

from intents.base import BaseIntentHandler
from models import Diagnostic
from utils import truncate_text, sanitize_ssml_text
from core.response_builder import AlexaResponseBuilder

from config.settings import MAX_VOICE_LENGTH


class WhyIntentHandler(BaseIntentHandler):
    """
    Handler para explicar la causa raiz de un error.

    Este intent es un follow-up de DiagnoseIntent. Proporciona una explicacion
    tecnica detallada de por que ocurre el error diagnosticado, ayudando al
    usuario a entender el problema mas alla de solo solucionarlo.

    Features:
    - Explicacion tecnica simplificada para voz
    - Card detallada con causas comunes
    - Contexto educativo sobre el error
    - Enlaces conceptuales (relacionado con X, Y, Z)
    - Sugerencias de prevencion

    Attributes:
        intent_name: "WhyIntent"

    Session Attributes Requeridos:
        - last_diagnostic: Diagnostico previo con campo 'explanation'

    Note:
        Este intent es puramente educativo. No proporciona soluciones
        directas (para eso esta MoreIntent), sino que ayuda a comprender
        el problema desde una perspectiva tecnica.
    """

    # Configuracion
    @property
    def MAX_VOICE_LENGTH(self):
        """Obtiene longitud maxima de voz desde settings."""
        return MAX_VOICE_LENGTH

    def __init__(self):
        """Inicializa el handler."""
        super().__init__()
        self.logger.info("WhyIntentHandler initialized")

    @property
    def intent_name(self) -> str:
        """Nombre del intent."""
        return "WhyIntent"

    def handle_intent(self, handler_input: HandlerInput) -> Response:
        """
        Maneja la solicitud de explicacion.

        Args:
            handler_input: Input del request de Alexa

        Returns:
            Response: Respuesta con explicacion tecnica
        """
        # Verificar que exista un diagnostico previo
        last_diagnostic = self.get_last_diagnostic(handler_input)

        if not last_diagnostic:
            return self._handle_no_diagnostic(handler_input)

        # Verificar que tenga explicacion
        if not last_diagnostic.has_explanation():
            return self._handle_no_explanation(handler_input, last_diagnostic)

        self.logger.info(
            "Providing explanation",
            extra={
                'error_type': last_diagnostic.error_type,
                'has_explanation': True
            }
        )

        # Construir respuesta
        return self._build_explanation_response(
            handler_input,
            last_diagnostic
        )

    def _build_explanation_response(
        self,
        handler_input: HandlerInput,
        diagnostic: Diagnostic
    ) -> Response:
        """
        Construye la respuesta con la explicacion.

        Args:
            handler_input: Input del request
            diagnostic: Diagnostico completo con explicacion

        Returns:
            Response de Alexa con explicacion
        """
        error_type = diagnostic.error_type
        explanation = diagnostic.explanation

        # Sanitizar y construir texto de voz (simplificado)
        safe_explanation = sanitize_ssml_text(explanation or "")
        voice_text = self._build_voice_explanation(
            error_type, safe_explanation)

        # Agregar prompt para siguiente accion
        voice_text += (
            " ¿Quieres escuchar mas soluciones o prefieres que "
            "te envie todo a tu telefono?"
        )

        # Construir card detallada
        card_title = f"Por que ocurre: {error_type}"
        card_text = self._build_detailed_card(diagnostic)

        return (
            AlexaResponseBuilder(handler_input)
            .speak(voice_text)
            .simple_card(card_title, card_text)
            .ask("¿Necesitas algo mas?")
            .build()
        )

    def _build_voice_explanation(
        self,
        error_type: str,
        explanation: str
    ) -> str:
        """
        Construye la explicacion simplificada para voz.

        La explicacion de voz es mas corta y directa que la de la card,
        adaptada para ser escuchada en lugar de leida.

        Args:
            error_type: Tipo de error
            explanation: Explicacion completa

        Returns:
            Texto simplificado para voz
        """
        # Introduccion
        voice_text = f"{error_type} ocurre porque: {explanation}"

        # Truncar si es muy largo
        voice_text = truncate_text(
            voice_text, max_length=self.MAX_VOICE_LENGTH)

        return voice_text

    def _build_detailed_card(self, diagnostic: Diagnostic) -> str:
        """
        Construye la card detallada con toda la explicacion.

        Args:
            diagnostic: Diagnostico completo

        Returns:
            Texto formateado para la card
        """
        error_type = diagnostic.error_type
        explanation = diagnostic.explanation

        lines = [
            f"ERROR: {error_type}",
            "",
            "=" * 50,
            "POR QUE OCURRE:",
            "=" * 50,
            "",
            explanation,
            ""
        ]

        # Agregar causas comunes si estan disponibles
        if diagnostic.common_causes:
            lines.append("-" * 50)
            lines.append("CAUSAS COMUNES:")
            lines.append("-" * 50)
            lines.append("")

            for i, cause in enumerate(diagnostic.common_causes, 1):
                lines.append(f"{i}. {cause}")

            lines.append("")

        # Agregar informacion de fuente
        source = diagnostic.source
        confidence = diagnostic.confidence

        lines.append("-" * 50)
        lines.append("INFORMACION:")
        lines.append("-" * 50)
        lines.append("")
        lines.append(f"Fuente del diagnostico: {source.upper()}")
        lines.append(f"Confianza: {confidence * 100:.0f}%")
        lines.append("")

        # Agregar errores relacionados si estan disponibles
        if diagnostic.related_errors:
            lines.append("-" * 50)
            lines.append("ERRORES RELACIONADOS:")
            lines.append("-" * 50)
            lines.append("")

            for error in diagnostic.related_errors:
                lines.append(f"- {error}")

            lines.append("")

        # Footer con sugerencias
        lines.append("-" * 50)
        lines.append("SIGUIENTES PASOS:")
        lines.append("-" * 50)
        lines.append("")
        lines.append("- Di 'dame otra opcion' para mas soluciones")
        lines.append("- Di 'envialo a mi telefono' para guardar todo")
        lines.append(
            "- Di 'tengo un error...' para diagnosticar otro problema")

        return "\n".join(lines)

    def _handle_no_diagnostic(self, handler_input: HandlerInput) -> Response:
        """
        Maneja el caso donde no hay diagnostico previo en sesion.

        Args:
            handler_input: Input del request

        Returns:
            Response solicitando un diagnostico primero
        """
        self.logger.warning("WhyIntent called without previous diagnostic")

        speak_output = (
            "Primero necesito diagnosticar un error para explicarte por que ocurre. "
            "¿Que error estas teniendo? "
            "Por ejemplo: tengo un error syntax error, o module not found."
        )

        reprompt = "Dime que mensaje de error estas viendo."

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(reprompt)
            .response
        )

    def _handle_no_explanation(
        self,
        handler_input: HandlerInput,
        diagnostic: Diagnostic
    ) -> Response:
        """
        Maneja el caso donde el diagnostico no tiene explicacion.

        Args:
            handler_input: Input del request
            diagnostic: Diagnostico sin campo explanation

        Returns:
            Response indicando que no hay explicacion disponible
        """
        error_type = diagnostic.error_type

        self.logger.warning(
            "Diagnostic has no explanation",
            extra={'error_type': error_type}
        )

        speak_output = (
            f"No tengo una explicacion detallada disponible para {error_type}. "
            "¿Quieres escuchar mas soluciones o prefieres diagnosticar otro error?"
        )

        # Construir card basica
        card_title = f"Explicacion no disponible: {error_type}"
        card_text = (
            f"ERROR: {error_type}\n\n"
            "Lo siento, no tengo una explicacion tecnica detallada "
            "para este error en este momento.\n\n"
            "ALTERNATIVAS:\n"
            "- Di 'dame otra opcion' para mas soluciones\n"
            "- Di 'tengo un error...' para diagnosticar otro problema"
        )

        return (
            AlexaResponseBuilder(handler_input)
            .speak(speak_output)
            .simple_card(card_title, card_text)
            .ask("¿Necesitas algo mas?")
            .build()
        )
