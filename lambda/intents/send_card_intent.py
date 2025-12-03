"""
Handler para el intent SendCardIntent.

Este intent envia una card detallada a la app de Alexa con el resumen
completo del ultimo diagnostico. Es util cuando el usuario quiere guardar
la informacion para consultarla despues en su dispositivo movil.

Flujo:
1. Verifica que exista un diagnostico previo en sesion
2. Lee el diagnostico completo
3. Construye una card detallada con toda la informacion
4. Envia la card a la app de Alexa
5. Confirma el envio al usuario

Patterns:
- Template Method (hereda de BaseIntentHandler)
- Builder (construccion de card compleja)
"""

from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from ask_sdk_model.ui import SimpleCard

from intents.base import BaseIntentHandler
from models import Diagnostic, UserProfile
from utils import format_timestamp

from config.settings import MAX_CARD_CONTENT_LENGTH


class SendCardIntentHandler(BaseIntentHandler):
    """
    Handler para enviar cards detalladas a la app de Alexa.

    Este intent es un follow-up de DiagnoseIntent. Toma el ultimo diagnostico
    guardado en sesion y lo envia como una card completa a la app de Alexa
    en el dispositivo del usuario (telefono/tablet).

    Features:
    - Envia card rica con toda la informacion del diagnostico
    - Incluye todas las soluciones disponibles
    - Formatea el contenido de forma legible
    - Agrega timestamp para referencia
    - Opcionalmente incluye imagenes (logo, iconos)

    Attributes:
        intent_name: "SendCardIntent"

    Session Attributes Requeridos:
        - last_diagnostic: Diagnostico previo con toda la informacion
        - user_profile: Perfil del usuario (opcional, para personalizacion)

    Note:
        Las cards solo aparecen en dispositivos con pantalla (app movil,
        Echo Show, etc.). En dispositivos solo de voz no tendran efecto
        visual pero Alexa confirmara el envio verbalmente.
    """

    # Configuracion
    @property
    def MAX_CARD_CONTENT_LENGTH(self):
        """Obtiene longitud maxima de card desde settings."""
        return MAX_CARD_CONTENT_LENGTH

    def __init__(self):
        """Inicializa el handler."""
        super().__init__()
        self.logger.info("SendCardIntentHandler initialized")

    @property
    def intent_name(self) -> str:
        """Nombre del intent."""
        return "SendCardIntent"

    def handle_intent(self, handler_input: HandlerInput) -> Response:
        """
        Maneja la solicitud de enviar card.

        Args:
            handler_input: Input del request de Alexa

        Returns:
            Response: Respuesta con card detallada y confirmacion verbal
        """
        # Verificar que exista un diagnostico previo
        last_diagnostic = self.get_last_diagnostic(handler_input)

        if not last_diagnostic:
            return self._handle_no_diagnostic(handler_input)

        # Obtener perfil de usuario
        user_profile = self.get_user_profile(handler_input)

        self.logger.info(
            "Sending card to app",
            extra={
                'error_type': last_diagnostic.error_type,
                'has_solutions': last_diagnostic.has_solutions()
            }
        )

        # Construir card completa
        card_title, card_content = self._build_detailed_card(
            last_diagnostic,
            user_profile
        )

        # Construir respuesta verbal
        speak_output = self._build_voice_confirmation(last_diagnostic)

        # Construir respuesta de Alexa con card
        return self._build_response_with_card(
            handler_input,
            speak_output,
            card_title,
            card_content
        )

    def _build_detailed_card(
        self,
        diagnostic: Diagnostic,
        user_profile: UserProfile
    ) -> tuple:
        """
        Construye una card detallada con toda la informacion del diagnostico.

        Args:
            diagnostic: Diagnostico completo
            user_profile: Perfil del usuario

        Returns:
            tuple: (card_title, card_content)
        """
        error_type = diagnostic.error_type
        confidence = diagnostic.confidence
        source = diagnostic.source

        # Construir titulo
        card_title = f"Doctor de Errores: {error_type}"

        # Construir contenido
        sections = []

        # Seccion 1: Informacion general
        sections.append("=" * 50)
        sections.append(f"DIAGNOSTICO: {error_type}")
        sections.append("=" * 50)
        sections.append("")

        # Seccion 2: Descripcion breve
        if diagnostic.voice_text:
            sections.append("DESCRIPCION:")
            sections.append(diagnostic.voice_text)
            sections.append("")

        # Seccion 3: Todas las soluciones
        if diagnostic.has_solutions():
            sections.append("-" * 50)
            sections.append("SOLUCIONES:")
            sections.append("-" * 50)
            sections.append("")

            for i, solution in enumerate(diagnostic.solutions, 1):
                sections.append(f"{i}. {solution}")
                sections.append("")

        # Seccion 4: Explicacion tecnica
        if diagnostic.has_explanation():
            sections.append("-" * 50)
            sections.append("POR QUE OCURRE:")
            sections.append("-" * 50)
            sections.append("")
            sections.append(diagnostic.explanation)
            sections.append("")

        # Seccion 5: Informacion adicional
        sections.append("-" * 50)
        sections.append("INFORMACION ADICIONAL:")
        sections.append("-" * 50)
        sections.append("")
        sections.append(f"Confianza del diagnostico: {confidence * 100:.0f}%")
        sections.append(f"Fuente: {source.upper()}")

        # Agregar informacion del perfil
        sections.append(f"Sistema operativo: {user_profile.os.value}")
        sections.append(
            f"Gestor de paquetes: {user_profile.package_manager.value}")
        sections.append(f"Editor: {user_profile.editor.value}")

        # Timestamp
        sections.append(f"Fecha: {format_timestamp()}")
        sections.append("")

        # Footer
        sections.append("-" * 50)
        sections.append("Powered by Doctor de Errores")
        sections.append("Di 'Alexa, abre Doctor de Errores' para mas ayuda")
        sections.append("-" * 50)

        # Unir todo el contenido
        card_content = "\n".join(sections)

        # Verificar limite de longitud
        if len(card_content) > self.MAX_CARD_CONTENT_LENGTH:
            self.logger.warning(
                f"Card content too long ({len(card_content)} chars), truncating"
            )
            card_content = card_content[:self.MAX_CARD_CONTENT_LENGTH - 100]
            card_content += "\n\n... (contenido truncado por longitud)"

        return card_title, card_content

    def _build_voice_confirmation(self, diagnostic: Diagnostic) -> str:
        """
        Construye el mensaje de voz confirmando el envio.

        Args:
            diagnostic: Diagnostico enviado

        Returns:
            str: Mensaje de confirmacion
        """
        error_type = diagnostic.error_type
        num_solutions = diagnostic.get_solution_count()

        if num_solutions > 0:
            speak_output = (
                f"He enviado el diagnostico completo de {error_type} "
                f"con {num_solutions} soluciones a tu app de Alexa. "
                "Puedes consultarlo cuando quieras en tu telefono. "
                "¿Necesitas ayuda con otro error?"
            )
        else:
            speak_output = (
                f"He enviado el diagnostico de {error_type} a tu app de Alexa. "
                "¿Necesitas ayuda con otro error?"
            )

        return speak_output

    def _build_response_with_card(
        self,
        handler_input: HandlerInput,
        speak_output: str,
        card_title: str,
        card_content: str
    ) -> Response:
        """
        Construye la respuesta de Alexa con la card.

        Args:
            handler_input: Input del request
            speak_output: Mensaje de voz
            card_title: Titulo de la card
            card_content: Contenido de la card

        Returns:
            Response de Alexa con card adjunta
        """
        # SimpleCard sin imagen
        simple_card = SimpleCard(title=card_title, content=card_content)

        return (
            handler_input.response_builder
            .speak(speak_output)
            .set_card(simple_card)
            .ask("¿Puedo ayudarte con algo mas?")
            .response
        )

    def _handle_no_diagnostic(self, handler_input: HandlerInput) -> Response:
        """
        Maneja el caso donde no hay diagnostico previo en sesion.

        Args:
            handler_input: Input del request

        Returns:
            Response solicitando un diagnostico primero
        """
        self.logger.warning(
            "SendCardIntent called without previous diagnostic")

        speak_output = (
            "No tengo ningun diagnostico para enviar. "
            "Primero dime que error estas teniendo. "
            "Por ejemplo: tengo un error module not found."
        )

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )
