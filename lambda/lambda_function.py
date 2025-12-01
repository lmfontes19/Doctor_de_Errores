# -*- coding: utf-8 -*-

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.

import logging

# Importaciones de Alexa SDK
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response

# Importar LoggerManager centralizado desde utils
from utils import get_logger_manager, get_logger

# Importar nuevos componentes
from core.response_builder import response_builder
from core.factories import ResponseFactory
from core.interceptors import (
    RECOMMENDED_REQUEST_INTERCEPTORS,
    RECOMMENDED_RESPONSE_INTERCEPTORS
)

# Importar intents personalizados
from intents.diagnose_intent import DiagnoseIntentHandler
from intents.more_intent import MoreIntentHandler
from intents.send_card_intent import SendCardIntentHandler
from intents.why_intent import WhyIntentHandler
from intents.set_profile_intent import SetProfileIntentHandler

# ============================================================================
# Inicialización del Logger Centralizado
# ============================================================================
# Inicializar el singleton al cargar el módulo
logger_manager = get_logger_manager()
logger = get_logger(__name__)

# Configurar nivel de logging (ajustar según environment)
logger_manager.set_level(logging.INFO)

logger.info("Doctor de Errores Skill - Lambda Function loaded")


class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("LaunchRequest received")

        # Usar ResponseFactory para mensaje de bienvenida
        return ResponseFactory.create_welcome_response(handler_input)


class HelloWorldIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("HelloWorldIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Hello World!"

        return (
            handler_input.response_builder
            .speak(speak_output)
            # .ask("add a reprompt if you want to keep the session open for the user to respond")
            .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("HelpIntent received")

        # Usar ResponseFactory para mensaje de ayuda
        return ResponseFactory.create_help_response(handler_input)


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("CancelOrStopIntent received")

        # Usar ResponseFactory para mensaje de despedida
        return ResponseFactory.create_goodbye_response(handler_input)


class FallbackIntentHandler(AbstractRequestHandler):
    """Single handler for Fallback Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("FallbackIntentHandler received")

        # Usar response_builder con mensaje de fallback
        speech = (
            "Lo siento, no entendi tu solicitud. "
            "Puedes decir cosas como: diagnostica mi error, "
            "dame mas soluciones, o explicame por que. "
            "Que te gustaria hacer?"
        )
        reprompt = "No logre entender. Como puedo ayudarte?"

        return (
            response_builder(handler_input)
            .speak(speech)
            .ask(reprompt)
            .simple_card(
                "Doctor de Errores",
                "Comandos disponibles: diagnostica, mas soluciones, explicame, configura perfil"
            )
            .build()
        )


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."

        return (
            handler_input.response_builder
            .speak(speak_output)
            # .ask("add a reprompt if you want to keep the session open for the user to respond")
            .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """

    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(f"Error handling request: {exception}", exc_info=True)

        # Usar ResponseFactory para respuesta de error estandarizada
        return ResponseFactory.create_error_response(
            handler_input,
            "Ocurrio un error al procesar tu solicitud. Por favor intenta de nuevo."
        )

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


sb = SkillBuilder()

# Registrar interceptors de request
for interceptor in RECOMMENDED_REQUEST_INTERCEPTORS:
    sb.add_global_request_interceptor(interceptor)

# Registrar handlers de intents personalizados
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(DiagnoseIntentHandler())
sb.add_request_handler(MoreIntentHandler())
sb.add_request_handler(SendCardIntentHandler())
sb.add_request_handler(WhyIntentHandler())
sb.add_request_handler(SetProfileIntentHandler())

# Registrar handlers estandar de Alexa
sb.add_request_handler(HelloWorldIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())

# IntentReflectorHandler va ultimo para no sobrescribir intents personalizados
sb.add_request_handler(IntentReflectorHandler())

# Registrar exception handler
sb.add_exception_handler(CatchAllExceptionHandler())

# Registrar interceptors de response
for interceptor in RECOMMENDED_RESPONSE_INTERCEPTORS:
    sb.add_global_response_interceptor(interceptor)

lambda_handler = sb.lambda_handler()
