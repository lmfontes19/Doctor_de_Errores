"""
Handler para capturar descripciones de errores cuando se solicitan.

Este handler intercepta respuestas del usuario cuando Alexa ha preguntado
"¿Que error estas viendo?" y el usuario responde con texto libre.

Patterns:
- State Machine: maneja transiciones basadas en session state
- Strategy: multiples estrategias para extraer texto de error
- Chain of Responsibility: prueba extractores en secuencia
"""

import re
from abc import ABC, abstractmethod
from typing import Optional

from ask_sdk_model import Slot, Intent as AlexaIntent, Response
from ask_sdk_model.intent import Intent
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.utils import is_request_type

from intents.base import BaseIntentHandler
from intents.diagnose_intent import DiagnoseIntentHandler


# Strategy Pattern: Extractores de Texto de Error
class ErrorTextExtractor(ABC):
    """
    Interfaz base para estrategias de extraccion de texto de error.

    Pattern: Strategy - define una familia de algoritmos intercambiables
    """

    @abstractmethod
    def extract(self, intent: Intent) -> Optional[str]:
        """
        Intenta extraer el texto del error del intent.

        Args:
            intent: Intent de Alexa con slots

        Returns:
            Texto del error si se encuentra, None si no
        """

    @abstractmethod
    def get_priority(self) -> int:
        """
        Retorna la prioridad del extractor (menor = mayor prioridad).

        Returns:
            Numero de prioridad
        """


class SpecificSlotsExtractor(ErrorTextExtractor):
    """Extrae texto de slots especificos conocidos."""

    SLOT_NAMES = ['errorText', 'query', 'phrase', 'message']

    def extract(self, intent: Intent) -> Optional[str]:
        """Busca en slots especificos por nombre."""
        if not intent.slots:
            return None

        for slot_name in self.SLOT_NAMES:
            if slot_name in intent.slots:
                slot = intent.slots[slot_name]
                if slot and slot.value:
                    return slot.value
        return None

    def get_priority(self) -> int:
        return 1


class FirstAvailableSlotExtractor(ErrorTextExtractor):
    """Extrae el primer slot con valor disponible."""

    def extract(self, intent: Intent) -> Optional[str]:
        """Itera todos los slots y retorna el primero con valor."""
        if not intent.slots:
            return None

        for slot in intent.slots.values():
            if slot and slot.value:
                return slot.value
        return None

    def get_priority(self) -> int:
        return 2


class IntentNameExtractor(ErrorTextExtractor):
    """Extrae informacion del nombre del intent como ultimo recurso."""

    IGNORED_INTENTS = ['DiagnoseIntent', 'AMAZON.FallbackIntent']

    def extract(self, intent: Intent) -> Optional[str]:
        """Convierte el nombre del intent a texto legible."""
        if not intent.name or intent.name in self.IGNORED_INTENTS:
            return None

        words = re.findall('[A-Z][a-z]*', intent.name)
        if words:
            return ' '.join(words).lower()

        return None

    def get_priority(self) -> int:
        return 3


class RawTranscriptionExtractor(ErrorTextExtractor):
    """
    Extrae texto directamente de AMAZON.FallbackIntent cuando el usuario
    dice texto libre que no mapea a ningun intent especifico.
    """

    def __init__(self, handler_input: HandlerInput):
        """
        Inicializa con handler_input para acceder al request completo.

        Args:
            handler_input: Input completo del handler
        """
        self.handler_input = handler_input

    def extract(self, intent: Intent) -> Optional[str]:
        """
        Extrae de slots de FallbackIntent o DiagnoseIntent.

        Para FallbackIntent, busca el slot con el texto transcrito.
        """
        if not intent or not intent.slots:
            return None

        if intent.name == 'AMAZON.FallbackIntent':
            for slot in intent.slots.values():
                if slot and slot.value:
                    return slot.value

        return None

    def get_priority(self) -> int:
        return 0


class ErrorTextExtractionStrategy:
    """
    Context del Strategy Pattern que coordina multiples extractores.

    Pattern: Chain of Responsibility - prueba extractores en secuencia
    hasta encontrar uno exitoso.
    """

    def __init__(self, handler_input: HandlerInput):
        """
        Inicializa con extractores ordenados por prioridad.

        Args:
            handler_input: Input del handler para acceso al request completo
        """
        self.extractors = [
            RawTranscriptionExtractor(handler_input),
            SpecificSlotsExtractor(),
            FirstAvailableSlotExtractor(),
            IntentNameExtractor()
        ]

        self.extractors.sort(key=lambda e: e.get_priority())

    def extract_error_text(self, intent: Intent) -> Optional[str]:
        """
        Intenta extraer texto usando multiples estrategias.

        Args:
            intent: Intent de Alexa

        Returns:
            Texto del error o None
        """
        for extractor in self.extractors:
            result = extractor.extract(intent)
            if result:
                return result
        return None


# Handler Principal
class ErrorDescriptionHandler(BaseIntentHandler):
    """
    Captura descripciones de errores en respuestas a preguntas abiertas.

    Este handler se activa cuando:
    1. El request es tipo IntentRequest
    2. Hay una flag 'awaiting_error_description' en session
    3. El usuario responde con texto libre

    Patterns:
    - State Machine: gestion de estado conversacional
    - Strategy: multiples estrategias de extraccion de texto

    Note:
        Este handler NO usa intent_name property porque maneja multiples intents
        dinamicamente (cualquier intent cuando awaiting_error_description=True).
        Por lo tanto, override can_handle() directamente.
    """

    def __init__(self):
        super().__init__()
        self.logger.info("ErrorDescriptionHandler initialized")

    @property
    def intent_name(self) -> str:
        """
        No aplica - este handler maneja multiples intents dinamicamente.
        Se mantiene por compatibilidad con BaseIntentHandler.
        """
        return "ErrorDescriptionHandler"

    def can_handle(self, handler_input: HandlerInput) -> bool:
        """
        Verifica si debe manejar este request.

        Override del metodo base porque este handler no se basa en un intent
        especifico sino en el estado de la sesion.
        """
        awaiting_error = self.get_session_attribute(
            handler_input, 'awaiting_error_description', False
        )

        # Log para debugging
        if awaiting_error:
            request = handler_input.request_envelope.request
            intent_name = request.intent.name if hasattr(
                request, 'intent') else 'N/A'
            self.logger.info(
                f"ErrorDescriptionHandler active - Intent: {intent_name}"
            )

        if not awaiting_error:
            return False

        return is_request_type("IntentRequest")(handler_input)

    def handle_intent(self, handler_input: HandlerInput) -> Response:
        """
        Implementacion requerida por BaseIntentHandler.
        Coordina la extraccion de texto de error y delegacion.
        """
        return self._process_error_description(handler_input)

    def _process_error_description(self, handler_input: HandlerInput) -> Response:
        """
        Procesa la descripcion del error usando Strategy Pattern.

        Responsabilidad: Coordinar extraccion de texto y delegacion a DiagnoseIntent.
        """
        self.logger.info("Capturing error description from user response")

        # Limpiar flag de estado
        self.set_session_attribute(
            handler_input, 'awaiting_error_description', False)

        request = handler_input.request_envelope.request
        intent = request.intent if hasattr(request, 'intent') else None

        error_text = None
        if intent:
            # Crear strategy con handler_input para acceder al request completo
            extraction_strategy = ErrorTextExtractionStrategy(handler_input)
            error_text = extraction_strategy.extract_error_text(intent)

            slot_info = list(intent.slots.keys()) if (
                intent.slots and hasattr(intent.slots, 'keys')) else []
            self.logger.info(
                f"Intent name: {intent.name}, Slots: {slot_info}"
            )

        if not error_text:
            self.logger.warning(
                "Could not extract error text, requesting clarification"
            )
            return self._request_clarification(handler_input)

        self.logger.info(f"Extracted error description: {error_text[:50]}")

        # Delegar a DiagnoseIntent
        return self._delegate_to_diagnose_intent(handler_input, intent, error_text)

    def _delegate_to_diagnose_intent(
        self,
        handler_input: HandlerInput,
        original_intent: Optional[Intent],
        error_text: str
    ) -> Response:
        """
        Crea un DiagnoseIntent sintetico y delega el procesamiento.

        Responsabilidad: Transformacion de intent y delegacion.

        Args:
            handler_input: Input del request
            original_intent: Intent original capturado
            error_text: Texto del error extraido

        Returns:
            Response del DiagnoseIntentHandler
        """
        # Crear intent sintetico para DiagnoseIntent
        new_intent = AlexaIntent(
            name='DiagnoseIntent',
            confirmation_status=original_intent.confirmation_status if original_intent else None,
            slots={
                'errorText': Slot(
                    name='errorText',
                    value=error_text,
                    confirmation_status='NONE'
                )
            }
        )

        # Reemplazar intent en el request
        request = handler_input.request_envelope.request
        request.intent = new_intent

        # Delegar al handler de diagnostico
        diagnose_handler = DiagnoseIntentHandler()
        return diagnose_handler.handle(handler_input)

    def _request_clarification(self, handler_input: HandlerInput) -> Response:
        """
        Solicita aclaracion cuando no se pudo extraer el error.

        Responsabilidad: Construccion de respuesta de aclaracion.

        Args:
            handler_input: Input del request

        Returns:
            Response pidiendo mas informacion
        """
        speak_output = (
            "Lo siento, no pude entender el tipo de error. "
            "Por favor describe el error mas especificamente. "
            "Por ejemplo: module not found, syntax error, "
            "o file not found."
        )

        reprompt = "¿Que mensaje de error ves?"

        # Mantener flag activa para siguiente intento
        self.set_session_attribute(
            handler_input, 'awaiting_error_description', True)

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(reprompt)
            .response
        )
