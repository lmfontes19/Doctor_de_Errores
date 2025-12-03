"""
Handler para el intent MoreIntent.

Este intent proporciona soluciones adicionales basandose en el ultimo
diagnostico generado por DiagnoseIntent. Es un follow-up intent que
depende completamente del contexto de sesion.

Flujo:
1. Verifica que exista un diagnostico previo en sesion
2. Lee las soluciones del diagnostico
3. Mantiene un indice de cual solucion ya se mostro
4. Retorna la siguiente solucion disponible
5. Notifica cuando se agotaron las opciones

Patterns:
- Template Method (hereda de BaseIntentHandler)
- Iterator (recorre lista de soluciones)
- State (mantiene indice en sesion)
"""

from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response

from intents.base import BaseIntentHandler
from models import Diagnostic
from utils import truncate_text, sanitize_ssml_text
from core.response_builder import AlexaResponseBuilder

from config.settings import MAX_VOICE_LENGTH, MAX_SOLUTIONS


class MoreIntentHandler(BaseIntentHandler):
    """
    Handler para proporcionar soluciones adicionales.

    Este intent es un follow-up de DiagnoseIntent. Lee el ultimo diagnostico
    guardado en sesion y proporciona la siguiente solucion disponible.
    Mantiene un indice de soluciones mostradas para no repetir.

    Features:
    - Iteracion sobre lista de soluciones
    - Mantiene estado en sesion (indice actual)
    - Detecta cuando se agotaron las opciones
    - Sugiere otros intents (Why, SendCard)

    Attributes:
        intent_name: "MoreIntent"

    Session Attributes Requeridos:
        - last_diagnostic: Diagnostico previo con lista de soluciones
        - user_profile: Perfil del usuario (para personalizacion)

    Session Attributes Actualizados:
        - solution_index: Indice de la solucion actual (0-based)
    """

    # Configuracion
    @property
    def MAX_VOICE_LENGTH(self):
        """Obtiene longitud maxima de voz desde settings."""
        return MAX_VOICE_LENGTH

    @property
    def MAX_SOLUTIONS(self):
        """Obtiene maximo de soluciones desde settings."""
        return MAX_SOLUTIONS

    def __init__(self):
        """Inicializa el handler."""
        super().__init__()
        self.logger.info("MoreIntentHandler initialized")

    @property
    def intent_name(self) -> str:
        """Nombre del intent."""
        return "MoreIntent"

    def handle_intent(self, handler_input: HandlerInput) -> Response:
        """
        Maneja la solicitud de mas soluciones.

        Args:
            handler_input: Input del request de Alexa

        Returns:
            Response: Respuesta con siguiente solucion o mensaje de finalizacion
        """
        # Verificar que exista un diagnostico previo
        last_diagnostic = self.get_last_diagnostic(handler_input)

        if not last_diagnostic:
            return self._handle_no_diagnostic(handler_input)

        # Obtener indice actual de soluciones
        current_index = self.get_session_attribute(
            handler_input,
            'solution_index',
            default=0
        )

        # Obtener lista de soluciones
        solutions = last_diagnostic.solutions

        if not solutions:
            return self._handle_no_solutions(handler_input)

        # Verificar si hay mas soluciones disponibles
        if current_index >= len(solutions):
            return self._handle_no_more_solutions(handler_input, last_diagnostic)

        # Obtener la siguiente solucion
        next_solution = solutions[current_index]

        # Incrementar indice para la proxima vez
        self.set_session_attribute(
            handler_input,
            'solution_index',
            current_index + 1
        )

        self.logger.info(
            f"Providing solution {current_index + 1}/{len(solutions)}",
            extra={
                'error_type': last_diagnostic.error_type,
                'solution_index': current_index
            }
        )

        # Construir respuesta
        return self._build_solution_response(
            handler_input,
            next_solution,
            current_index + 1,
            len(solutions),
            last_diagnostic
        )

    def _build_solution_response(
        self,
        handler_input: HandlerInput,
        solution: str,
        current_number: int,
        total_solutions: int,
        diagnostic: Diagnostic
    ) -> Response:
        """
        Construye la respuesta con la siguiente solucion.

        Args:
            handler_input: Input del request
            solution: Texto de la solucion a proporcionar
            current_number: Numero de solucion actual (1-based)
            total_solutions: Total de soluciones disponibles
            diagnostic: Diagnostico completo

        Returns:
            Response de Alexa con la solucion
        """
        error_type = diagnostic.error_type

        # Sanitizar y construir texto de voz
        safe_solution = sanitize_ssml_text(solution or "")
        voice_text = f"Solucion {current_number} de {total_solutions}. {safe_solution}"

        # Agregar prompt contextual
        remaining = total_solutions - current_number
        if remaining > 0:
            voice_text += f" Quieres escuchar otra opcion? Hay {remaining} mas disponibles."
        else:
            voice_text += " Esas son todas las soluciones que tengo. Quieres saber por que ocurre esto?"

        # Truncar si es necesario
        voice_text = truncate_text(
            voice_text, max_length=self.MAX_VOICE_LENGTH)

        # Construir texto de card
        card_title = f"Solucion {current_number}: {error_type}"
        card_text = self._build_card_text(
            solution,
            current_number,
            total_solutions,
            diagnostic
        )

        # Log
        self.logger.debug(
            "Built solution response",
            extra={
                'solution_number': current_number,
                'total': total_solutions,
                'has_more': remaining > 0
            }
        )

        # Construir respuesta con ResponseBuilder
        return (
            AlexaResponseBuilder(handler_input)
            .speak(voice_text)
            .simple_card(card_title, card_text)
            .ask("Necesitas algo mas?")
            .build()
        )

    def _build_card_text(
        self,
        solution: str,
        current_number: int,
        total_solutions: int,
        diagnostic: Diagnostic
    ) -> str:
        """
        Construye el texto completo de la card.

        Args:
            solution: Solucion a mostrar
            current_number: Numero actual
            total_solutions: Total de soluciones
            diagnostic: Diagnostico completo

        Returns:
            Texto formateado para la card
        """
        error_type = diagnostic.error_type

        card_lines = [
            f"**Diagnostico**: {error_type}",
            "",
            f"**Solucion {current_number} de {total_solutions}**:",
            solution,
            ""
        ]

        # Agregar hint sobre otras opciones
        remaining = total_solutions - current_number
        if remaining > 0:
            card_lines.append(
                f"_Quedan {remaining} soluciones mas. Di 'dame otra opcion'._")
        else:
            card_lines.append(
                "_Todas las soluciones mostradas. Di 'por que pasa esto' para mas detalles._")

        # Agregar link a explicacion completa si esta disponible
        if diagnostic.has_explanation():
            card_lines.append("")
            card_lines.append(
                "**Mas informacion**: Di 'por que pasa esto' para entender la causa raiz.")

        return "\n".join(card_lines)

    def _handle_no_diagnostic(self, handler_input: HandlerInput) -> Response:
        """
        Maneja el caso donde no hay diagnostico previo en sesion.

        Este caso ocurre cuando el usuario dice 'dame mas opciones' sin
        haber usado DiagnoseIntent primero.

        Args:
            handler_input: Input del request

        Returns:
            Response solicitando un diagnostico primero
        """
        self.logger.warning("MoreIntent called without previous diagnostic")

        speak_output = (
            "Primero necesito diagnosticar un error para darte soluciones. "
            "¿Que error estas teniendo? "
            "Por ejemplo, puedes decir: tengo un error module not found."
        )

        reprompt = "Describe el error que estas viendo en tu codigo."

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(reprompt)
            .response
        )

    def _handle_no_solutions(self, handler_input: HandlerInput) -> Response:
        """
        Maneja el caso donde el diagnostico no tiene soluciones.

        Args:
            handler_input: Input del request

        Returns:
            Response explicando que no hay soluciones
        """
        self.logger.warning("Diagnostic has no solutions")

        speak_output = (
            "El diagnostico anterior no incluye soluciones adicionales. "
            "Quieres saber por que ocurre el error o prefieres diagnosticar otro problema?"
        )

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )

    def _handle_no_more_solutions(
        self,
        handler_input: HandlerInput,
        diagnostic: Diagnostic
    ) -> Response:
        """
        Maneja el caso donde ya se mostraron todas las soluciones.

        Args:
            handler_input: Input del request
            diagnostic: Diagnostico con todas las soluciones ya mostradas

        Returns:
            Response indicando que se agotaron las opciones
        """
        error_type = diagnostic.error_type
        total_solutions = diagnostic.get_solution_count()

        self.logger.info(
            "All solutions exhausted",
            extra={
                'error_type': error_type,
                'total_shown': total_solutions
            }
        )

        # Resetear indice para permitir reiniciar
        self.set_session_attribute(handler_input, 'solution_index', 0)

        speak_output = (
            f"Ya te mostre las {total_solutions} soluciones disponibles para {error_type}. "
            "Quieres que te explique por que ocurre el error o prefieres diagnosticar otro problema?"
        )

        card_title = f"Soluciones para {error_type}"
        card_text = self._build_summary_card(diagnostic)

        return (
            AlexaResponseBuilder(handler_input)
            .speak(speak_output)
            .simple_card(card_title, card_text)
            .ask("Necesitas algo mas?")
            .build()
        )

    def _build_summary_card(self, diagnostic: Diagnostic) -> str:
        """
        Construye una card resumen con todas las soluciones.

        Args:
            diagnostic: Diagnostico completo

        Returns:
            Texto formateado con resumen de soluciones
        """
        error_type = diagnostic.error_type
        solutions = diagnostic.solutions

        lines = [
            f"**Diagnostico**: {error_type}",
            "",
            "**Todas las soluciones**:",
            ""
        ]

        for i, solution in enumerate(solutions, 1):
            lines.append(f"{i}. {solution}")

        lines.extend([
            "",
            "**Siguientes pasos**:",
            "- Di 'por que pasa esto' para entender la causa",
            "- Di 'envialo a mi telefono' para guardar estas soluciones",
            "- Di 'tengo un error...' para diagnosticar otro problema"
        ])

        return "\n".join(lines)
