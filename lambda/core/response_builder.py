"""
Response Builder para construccion fluida de respuestas de Alexa.

Este modulo implementa el patron Builder para construir respuestas
de Alexa de manera mas legible y mantenible.

Patterns:
- Builder: Construccion paso a paso de objetos complejos
- Fluent Interface: Encadenamiento de metodos
"""

from typing import Optional, Union
from ask_sdk_model import Response
from ask_sdk_model.ui import SimpleCard, StandardCard, Image


class AlexaResponseBuilder:
    """
    Builder para construir respuestas de Alexa con interfaz fluida.

    Proporciona una API mas limpia y expresiva que el builder
    nativo de ask_sdk.

    Example:
        >>> response = (
        ...     AlexaResponseBuilder(handler_input)
        ...     .speak("Hola mundo")
        ...     .simple_card("Titulo", "Contenido")
        ...     .ask("¿Que mas?")
        ...     .build()
        ... )
    """

    def __init__(self, handler_input):
        """
        Inicializa el builder.

        Args:
            handler_input: HandlerInput de Alexa SDK
        """
        self.handler_input = handler_input
        self._response_builder = handler_input.response_builder
        self._speech_text = None
        self._reprompt_text = None
        self._should_end_session = False

    def speak(self, text: str) -> 'AlexaResponseBuilder':
        """
        Establece el texto que Alexa dira.

        Args:
            text: Texto para que Alexa hable

        Returns:
            Self para encadenamiento
        """
        self._speech_text = text
        return self

    def ask(self, reprompt_text: str) -> 'AlexaResponseBuilder':
        """
        Establece el texto de reprompt (mantiene sesion abierta).

        Args:
            reprompt_text: Texto si el usuario no responde

        Returns:
            Self para encadenamiento
        """
        self._reprompt_text = reprompt_text
        self._should_end_session = False
        return self

    def reprompt(self, text: str) -> 'AlexaResponseBuilder':
        """
        Alias de ask() para compatibilidad.

        Args:
            text: Texto de reprompt

        Returns:
            Self para encadenamiento
        """
        return self.ask(text)

    def simple_card(self, title: str, content: str) -> 'AlexaResponseBuilder':
        """
        Agrega una card simple a la respuesta.

        Args:
            title: Titulo de la card
            content: Contenido de la card

        Returns:
            Self para encadenamiento
        """
        self._response_builder.set_card(
            SimpleCard(title=title, content=content)
        )
        return self

    def standard_card(
        self,
        title: str,
        text: str,
        small_image_url: Optional[str] = None,
        large_image_url: Optional[str] = None
    ) -> 'AlexaResponseBuilder':
        """
        Agrega una card estandar con soporte de imagenes.

        Args:
            title: Titulo de la card
            text: Texto de la card
            small_image_url: URL de imagen pequeña (720x480)
            large_image_url: URL de imagen grande (1200x800)

        Returns:
            Self para encadenamiento
        """
        image = None
        if small_image_url or large_image_url:
            image = Image(
                small_image_url=small_image_url,
                large_image_url=large_image_url
            )

        self._response_builder.set_card(
            StandardCard(
                title=title,
                text=text,
                image=image
            )
        )
        return self

    def card(
        self,
        title: str,
        content: str,
        image_url: Optional[str] = None
    ) -> 'AlexaResponseBuilder':
        """
        Agrega una card (simple o standard segun parametros).

        Args:
            title: Titulo de la card
            content: Contenido/texto de la card
            image_url: URL de imagen opcional

        Returns:
            Self para encadenamiento
        """
        if image_url:
            return self.standard_card(
                title=title,
                text=content,
                small_image_url=image_url,
                large_image_url=image_url
            )
        else:
            return self.simple_card(title=title, content=content)

    def end_session(self, should_end: bool = True) -> 'AlexaResponseBuilder':
        """
        Controla si la sesion debe terminar.

        Args:
            should_end: True para terminar sesion

        Returns:
            Self para encadenamiento
        """
        self._should_end_session = should_end
        return self

    def with_diagnostic_prompt(self) -> 'AlexaResponseBuilder':
        """
        Agrega un prompt estandar para follow-up de diagnosticos.

        Returns:
            Self para encadenamiento
        """
        prompt = (
            "¿Quieres saber por que ocurre esto, "
            "necesitas mas opciones, "
            "o prefieres que te lo envie a tu telefono?"
        )
        return self.ask(prompt)

    def with_error_prompt(self) -> 'AlexaResponseBuilder':
        """
        Agrega un prompt estandar para errores.

        Returns:
            Self para encadenamiento
        """
        return self.ask("¿Puedes intentar de nuevo?")

    def build(self) -> Response:
        """
        Construye la respuesta final de Alexa.

        Returns:
            Response de Alexa SDK
        """
        if self._speech_text:
            self._response_builder.speak(self._speech_text)

        if self._reprompt_text and not self._should_end_session:
            self._response_builder.ask(self._reprompt_text)

        if self._should_end_session:
            self._response_builder.set_should_end_session(True)

        return self._response_builder.response


class DiagnosticResponseBuilder:
    """
    Builder especializado para respuestas de diagnostico.

    Extiende AlexaResponseBuilder con funcionalidad especifica
    para diagnosticos de errores.
    """

    def __init__(self, handler_input):
        """
        Inicializa el builder de diagnosticos.

        Args:
            handler_input: HandlerInput de Alexa SDK
        """
        self.base_builder = AlexaResponseBuilder(handler_input)
        self.handler_input = handler_input

    def with_diagnostic(
        self,
        diagnostic,
        include_card: bool = True,
        max_voice_length: int = 300
    ) -> 'DiagnosticResponseBuilder':
        """
        Configura respuesta con un diagnostico completo.

        Args:
            diagnostic: Instancia de Diagnostic
            include_card: Si debe incluir card
            max_voice_length: Longitud maxima del texto de voz

        Returns:
            Self para encadenamiento
        """
        from utils import truncate_text

        # Configurar voz
        voice_text = truncate_text(
            diagnostic.voice_text,
            max_length=max_voice_length
        )
        self.base_builder.speak(voice_text)

        # Configurar card si se solicita
        if include_card:
            self.base_builder.simple_card(
                title=diagnostic.card_title,
                content=diagnostic.card_text
            )

        return self

    def with_solution(
        self,
        solution: str,
        solution_number: int,
        total_solutions: int,
        error_type: str
    ) -> 'DiagnosticResponseBuilder':
        """
        Configura respuesta con una solucion especifica.

        Args:
            solution: Texto de la solucion
            solution_number: Numero de solucion (1-based)
            total_solutions: Total de soluciones disponibles
            error_type: Tipo de error

        Returns:
            Self para encadenamiento
        """
        voice_text = (
            f"Solucion {solution_number} de {total_solutions}. "
            f"{solution}"
        )

        remaining = total_solutions - solution_number
        if remaining > 0:
            voice_text += f" Hay {remaining} soluciones mas disponibles."

        self.base_builder.speak(voice_text)

        # Card con la solucion
        card_title = f"Solucion {solution_number}: {error_type}"
        card_text = (
            f"**Solucion {solution_number} de {total_solutions}**\n\n"
            f"{solution}\n\n"
            f"**Siguientes pasos:**\n"
            f"- Di 'dame mas opciones' para ver otras soluciones\n"
            f"- Di 'por que pasa esto' para entender la causa"
        )

        self.base_builder.simple_card(card_title, card_text)

        return self

    def with_explanation(
        self,
        error_type: str,
        explanation: str,
        common_causes: Optional[list] = None,
        max_voice_length: int = 300
    ) -> 'DiagnosticResponseBuilder':
        """
        Configura respuesta con explicacion tecnica.

        Args:
            error_type: Tipo de error
            explanation: Explicacion tecnica
            common_causes: Lista de causas comunes
            max_voice_length: Longitud maxima de voz

        Returns:
            Self para encadenamiento
        """
        from utils import truncate_text

        # Voz simplificada
        voice_text = truncate_text(
            f"{error_type} ocurre porque: {explanation}",
            max_length=max_voice_length
        )
        self.base_builder.speak(voice_text)

        # Card detallada
        card_lines = [
            f"**Por que ocurre {error_type}:**\n",
            explanation,
            ""
        ]

        if common_causes:
            card_lines.append("\n**Causas comunes:**")
            for i, cause in enumerate(common_causes, 1):
                card_lines.append(f"{i}. {cause}")

        card_text = "\n".join(card_lines)
        self.base_builder.simple_card(
            f"Explicacion: {error_type}",
            card_text
        )

        return self

    def add_follow_up_prompt(self) -> 'DiagnosticResponseBuilder':
        """
        Agrega prompt de follow-up para diagnosticos.

        Returns:
            Self para encadenamiento
        """
        self.base_builder.with_diagnostic_prompt()
        return self

    def build(self) -> Response:
        """
        Construye la respuesta final.

        Returns:
            Response de Alexa SDK
        """
        return self.base_builder.build()


class ProfileResponseBuilder:
    """
    Builder especializado para respuestas de perfil.

    Maneja confirmaciones de cambios de perfil y visualizacion.
    """

    def __init__(self, handler_input):
        """
        Inicializa el builder de perfil.

        Args:
            handler_input: HandlerInput de Alexa SDK
        """
        self.base_builder = AlexaResponseBuilder(handler_input)

    def with_profile_update(
        self,
        old_profile,
        new_profile,
        changed_fields: list
    ) -> 'ProfileResponseBuilder':
        """
        Configura respuesta de actualizacion de perfil.

        Args:
            old_profile: Perfil anterior
            new_profile: Perfil nuevo
            changed_fields: Lista de campos que cambiaron

        Returns:
            Self para encadenamiento
        """
        # Construir mensaje de voz
        if len(changed_fields) == 1:
            field = changed_fields[0]
            field_name = self._get_field_name(field)
            new_value = self._get_field_value(new_profile, field)
            speak_text = f"Perfecto. Actualice tu {field_name} a {new_value}."
        else:
            changes = []
            for field in changed_fields:
                field_name = self._get_field_name(field)
                new_value = self._get_field_value(new_profile, field)
                changes.append(f"{field_name} a {new_value}")

            changes_text = ", ".join(changes[:-1]) + f" y {changes[-1]}"
            speak_text = f"Perfecto. Actualice tu {changes_text}."

        speak_text += (
            " Ahora las soluciones estaran personalizadas para tu entorno."
        )

        self.base_builder.speak(speak_text)

        # Card con perfil completo
        card_text = self._build_profile_card(new_profile, changed_fields)
        self.base_builder.simple_card("Perfil Actualizado", card_text)

        return self

    def _get_field_name(self, field: str) -> str:
        """Obtiene nombre amigable del campo."""
        names = {
            'os': 'sistema operativo',
            'pm': 'gestor de paquetes',
            'editor': 'editor'
        }
        return names.get(field, field)

    def _get_field_value(self, profile, field: str) -> str:
        """Obtiene valor del campo."""
        if field == 'os':
            return profile.os.value
        elif field == 'pm':
            return profile.package_manager.value
        elif field == 'editor':
            return profile.editor.value
        return 'desconocido'

    def _build_profile_card(self, profile, changed_fields: list) -> str:
        """Construye texto de card con perfil."""
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
                lines.append(f"- {field_name.capitalize()}")
            lines.append("")

        lines.extend([
            "Las soluciones de diagnostico ahora estaran",
            "personalizadas para tu entorno."
        ])

        return "\n".join(lines)

    def build(self) -> Response:
        """
        Construye la respuesta final.

        Returns:
            Response de Alexa SDK
        """
        return self.base_builder.build()


# Funciones helper para crear builders rapidamente
def response_builder(handler_input) -> AlexaResponseBuilder:
    """
    Crea un AlexaResponseBuilder.

    Args:
        handler_input: HandlerInput de Alexa

    Returns:
        AlexaResponseBuilder
    """
    return AlexaResponseBuilder(handler_input)


def diagnostic_response(handler_input) -> DiagnosticResponseBuilder:
    """
    Crea un DiagnosticResponseBuilder.

    Args:
        handler_input: HandlerInput de Alexa

    Returns:
        DiagnosticResponseBuilder
    """
    return DiagnosticResponseBuilder(handler_input)


def profile_response(handler_input) -> ProfileResponseBuilder:
    """
    Crea un ProfileResponseBuilder.

    Args:
        handler_input: HandlerInput de Alexa

    Returns:
        ProfileResponseBuilder
    """
    return ProfileResponseBuilder(handler_input)
