"""
Este modulo proporciona clases base y utilidades comunes para todos los
handlers de intents de la skill Doctor de Errores.

Note:
    LoggerManager ahora esta centralizado en utils.py para ser accesible
    por todos los modulos sin riesgo de dependencias circulares.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

# Importar LoggerManager desde utils centralizado
from utils import get_logger_manager, get_logger

from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from ask_sdk_core.utils import is_intent_name, get_slot_value

# Importaciones de modelos
from models import UserProfile, Diagnostic

# Importaciones de servicios
from services.storage import storage_service


# ============================================================================
# Funciones Helper Independientes
# ============================================================================

def get_user_profile_from_session(handler_input: HandlerInput) -> UserProfile:
    """
    Funcion helper para obtener perfil del usuario desde session attributes.

    Esta funcion estatica puede ser usada por cualquier handler sin necesidad
    de instanciar BaseIntentHandler.

    Args:
        handler_input: Input del request

    Returns:
        UserProfile: Perfil del usuario (usa default si no existe)
    """
    logger = get_logger(__name__)

    # Intentar obtener de session attributes (cache)
    session_attr = handler_input.attributes_manager.session_attributes
    profile_dict = session_attr.get('user_profile')

    if profile_dict:
        logger.info("Profile loaded from session cache")
        return UserProfile.from_dict(profile_dict)

    # Intentar cargar desde DynamoDB
    try:
        user_id = handler_input.request_envelope.session.user.user_id
        profile = storage_service.get_user_profile(user_id)

        if profile:
            logger.info("Profile loaded from DynamoDB")
            # Cachear en session para requests subsecuentes
            session_attr['user_profile'] = profile.to_dict()
            return profile
    except Exception as e:
        logger.warning(f"Failed to load profile from DynamoDB: {e}")

    # Retornar perfil por defecto
    logger.info("Using default profile")
    return UserProfile()  # Usa defaults: linux, pip, vscode


# ============================================================================
# Base Intent Handler - Template Method Pattern
# ============================================================================

class BaseIntentHandler(AbstractRequestHandler, ABC):
    """
    Clase base abstracta para todos los handlers de intents.

    Proporciona funcionalidades comunes como:
    - Extraccion de datos del usuario
    - Gestion de session attributes
    - Logging consistente mediante Singleton
    - Manejo de errores
    - Helpers para slots y perfiles

    Todos los handlers especificos deben heredar de esta clase.
    """

    def __init__(self):
        """Inicializa el handler base con logger singleton."""
        # Usar el singleton LoggerManager desde utils
        self.logger_manager = get_logger_manager()
        self.logger = get_logger(self.__class__.__name__)
        self.storage_service = storage_service

    @property
    @abstractmethod
    def intent_name(self) -> str:
        """
        Nombre del intent que este handler maneja.

        Returns:
            str: Nombre del intent (ej: "DiagnoseIntent")
        """

    def can_handle(self, handler_input: HandlerInput) -> bool:
        """
        Determina si este handler puede manejar el request.

        Args:
            handler_input: Input del request de Alexa

        Returns:
            bool: True si este handler puede manejar el request
        """
        return is_intent_name(self.intent_name)(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        """
        Maneja el request del intent.

        Este metodo implementa un template method pattern, ejecutando:
        1. Logging del request
        2. Extraccion de datos del usuario
        3. Ejecucion de la logica especifica (handle_intent)
        4. Logging de la respuesta
        5. Manejo de errores

        Args:
            handler_input: Input del request de Alexa

        Returns:
            Response: Respuesta para Alexa
        """
        try:
            # Log del request
            self._log_request(handler_input)

            # Ejecutar logica especifica del intent
            response = self.handle_intent(handler_input)

            # Log de la respuesta
            self._log_response(response)

            return response

        except Exception as e:
            self.logger.error(
                f"Error handling intent {self.intent_name}: {str(e)}", exc_info=True)
            return self._build_error_response(handler_input, e)

    @abstractmethod
    def handle_intent(self, handler_input: HandlerInput) -> Response:
        """
        Logica especifica para manejar el intent.

        Este metodo debe ser implementado por las clases hijas.

        Args:
            handler_input: Input del request de Alexa

        Returns:
            Response: Respuesta para Alexa
        """

    # ========================================================================
    # Metodos de Utilidad para Slots
    # ========================================================================

    def get_slot_value(self, handler_input: HandlerInput, slot_name: str) -> Optional[str]:
        """
        Obtiene el valor de un slot de forma segura.

        Args:
            handler_input: Input del request
            slot_name: Nombre del slot a obtener

        Returns:
            Optional[str]: Valor del slot o None si no existe
        """
        try:
            return get_slot_value(handler_input, slot_name)
        except Exception as e:
            self.logger.warning(f"Error getting slot '{slot_name}': {str(e)}")
            return None

    def get_all_slots(self, handler_input: HandlerInput) -> Dict[str, Any]:
        """
        Obtiene todos los slots del request.

        Args:
            handler_input: Input del request

        Returns:
            Dict[str, Any]: Diccionario con todos los slots
        """
        try:
            request = handler_input.request_envelope.request
            if hasattr(request, 'intent') and hasattr(request.intent, 'slots'):
                return {
                    name: slot.value
                    for name, slot in request.intent.slots.items()
                    if slot.value
                }
        except Exception as e:
            self.logger.warning(f"Error getting all slots: {str(e)}")

        return {}

    # ========================================================================
    # Metodos de Utilidad para Session Attributes
    # ========================================================================

    def get_session_attribute(
        self,
        handler_input: HandlerInput,
        key: str,
        default: Any = None
    ) -> Any:
        """
        Obtiene un atributo de sesion.

        Args:
            handler_input: Input del request
            key: Clave del atributo
            default: Valor por defecto si no existe

        Returns:
            Any: Valor del atributo o default
        """
        session_attr = handler_input.attributes_manager.session_attributes
        return session_attr.get(key, default)

    def set_session_attribute(
        self,
        handler_input: HandlerInput,
        key: str,
        value: Any
    ) -> None:
        """
        Establece un atributo de sesion.

        Args:
            handler_input: Input del request
            key: Clave del atributo
            value: Valor a establecer
        """
        session_attr = handler_input.attributes_manager.session_attributes
        session_attr[key] = value

    def clear_session_attributes(self, handler_input: HandlerInput) -> None:
        """
        Limpia todos los atributos de sesion.

        Args:
            handler_input: Input del request
        """
        handler_input.attributes_manager.session_attributes.clear()

    # ========================================================================
    # Metodos de Utilidad para Usuario
    # ========================================================================

    def get_user_id(self, handler_input: HandlerInput) -> str:
        """
        Obtiene el ID del usuario.

        Args:
            handler_input: Input del request

        Returns:
            str: ID del usuario
        """
        return handler_input.request_envelope.session.user.user_id

    def get_device_id(self, handler_input: HandlerInput) -> Optional[str]:
        """
        Obtiene el ID del dispositivo.

        Args:
            handler_input: Input del request

        Returns:
            Optional[str]: ID del dispositivo o None
        """
        try:
            return handler_input.request_envelope.context.system.device.device_id
        except AttributeError:
            return None

    def get_locale(self, handler_input: HandlerInput) -> str:
        """
        Obtiene el locale del usuario.

        Args:
            handler_input: Input del request

        Returns:
            str: Locale (ej: "es-MX")
        """
        return handler_input.request_envelope.request.locale

    # ========================================================================
    # Metodos de Utilidad para Perfil de Usuario
    # ========================================================================

    def get_user_profile(self, handler_input: HandlerInput) -> UserProfile:
        """
        Obtiene el perfil del usuario desde session attributes o storage.

        Primero intenta obtenerlo de session attributes (cache de sesion).
        Si no existe, intenta cargarlo desde DynamoDB.

        Args:
            handler_input: Input del request

        Returns:
            UserProfile: Perfil del usuario (nunca None, usa default si no existe)
        """
        return get_user_profile_from_session(handler_input)

    def save_user_profile(
        self,
        handler_input: HandlerInput,
        profile: UserProfile
    ) -> None:
        """
        Guarda el perfil del usuario en session y DynamoDB.

        Args:
            handler_input: Input del request
            profile: Perfil a guardar
        """
        # Guardar en session (cache)
        self.set_session_attribute(
            handler_input, 'user_profile', profile.to_dict())

        # Guardar en DynamoDB (mejor esfuerzo)
        try:
            user_id = self.get_user_id(handler_input)
            success = storage_service.save_user_profile(user_id, profile)

            if success:
                self.logger.info(
                    "Profile saved to DynamoDB",
                    extra={'user_id': user_id}
                )
            else:
                self.logger.warning(
                    "DynamoDB not available, profile saved only in session",
                    extra={'user_id': user_id}
                )
        except Exception as e:
            self.logger.error(
                f"Failed to save profile to DynamoDB: {e}",
                exc_info=True
            )

    def _get_default_profile(self) -> UserProfile:
        """
        Retorna un perfil por defecto.

        Returns:
            UserProfile: Perfil por defecto
        """
        return UserProfile()  # Usa defaults: linux, pip, vscode

    # ========================================================================
    # Metodos de Utilidad para Contexto de Diagnostico
    # ========================================================================

    def get_last_diagnostic(self, handler_input: HandlerInput) -> Optional[Diagnostic]:
        """
        Obtiene el ultimo diagnostico de la sesion.

        Util para intents como MoreIntent, WhyIntent que necesitan
        contexto del diagnostico anterior.

        Args:
            handler_input: Input del request

        Returns:
            Optional[Diagnostic]: ultimo diagnostico o None
        """
        diagnostic_dict = self.get_session_attribute(
            handler_input, 'last_diagnostic')
        if diagnostic_dict:
            return Diagnostic.from_dict(diagnostic_dict)
        return None

    def save_last_diagnostic(
        self,
        handler_input: HandlerInput,
        diagnostic: Diagnostic
    ) -> None:
        """
        Guarda el diagnostico actual para referencia futura.

        Args:
            handler_input: Input del request
            diagnostic: Diagnostico a guardar
        """
        self.set_session_attribute(
            handler_input, 'last_diagnostic', diagnostic.to_dict())

    # ========================================================================
    # Metodos de Logging
    # ========================================================================

    def _log_request(self, handler_input: HandlerInput) -> None:
        """
        Registra informacion del request usando el singleton logger.

        Args:
            handler_input: Input del request
        """
        try:
            user_id = self.get_user_id(handler_input)
            locale = self.get_locale(handler_input)
            slots = self.get_all_slots(handler_input)

            # Usar el metodo especializado del singleton
            self.logger_manager.log_request(
                intent_name=self.intent_name,
                user_id=user_id,
                locale=locale,
                slots=slots
            )
        except Exception as e:
            self.logger.warning(f"Error logging request: {str(e)}")

    def _log_response(self, response: Response) -> None:
        """
        Registra informacion de la respuesta usando el singleton logger.

        Args:
            response: Respuesta generada
        """
        try:
            has_card = hasattr(response, 'card') and response.card is not None
            should_end = response.should_end_session

            # Usar el metodo especializado del singleton
            self.logger_manager.log_response(
                intent_name=self.intent_name,
                has_card=has_card,
                should_end=should_end
            )
        except Exception as e:
            self.logger.warning(f"Error logging response: {str(e)}")

    # ========================================================================
    # Manejo de Errores
    # ========================================================================

    def _build_error_response(
        self,
        handler_input: HandlerInput,
        error: Exception
    ) -> Response:
        """
        Construye una respuesta de error amigable para el usuario.

        Args:
            handler_input: Input del request
            error: Excepcion capturada

        Returns:
            Response: Respuesta de error
        """
        speak_output = (
            "Lo siento, tuve un problema procesando tu solicitud. "
            "Por favor, intenta de nuevo."
        )

        reprompt = "En que más puedo ayudarte?"

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(reprompt)
            .response
        )


# ============================================================================
# Clases de Utilidad
# ============================================================================

class IntentValidator:
    """
    Validador de datos para intents.

    Proporciona metodos estáticos para validar slots y otros datos
    antes de procesarlos.
    """

    @staticmethod
    def is_valid_slot(slot_value: Optional[str]) -> bool:
        """
        Valida que un slot tenga un valor válido.

        Args:
            slot_value: Valor del slot

        Returns:
            bool: True si el slot es válido
        """
        return slot_value is not None and len(slot_value.strip()) > 0

    @staticmethod
    def is_valid_error_text(error_text: Optional[str]) -> bool:
        """
        Valida que el texto de error sea válido.

        Args:
            error_text: Texto del error

        Returns:
            bool: True si el texto es válido
        """
        if not error_text or len(error_text.strip()) < 3:
            return False

        # El texto debe contener al menos una palabra significativa
        words = error_text.strip().split()
        return len(words) >= 1

    @staticmethod
    def validate_profile_field(field: str, value: str) -> bool:
        """
        Valida un campo del perfil de usuario.

        Args:
            field: Nombre del campo (os, package_manager, editor)
            value: Valor a validar

        Returns:
            bool: True si el valor es válido
        """
        valid_values = {
            'os': ['Windows', 'macOS', 'Linux', 'WSL'],
            'package_manager': ['pip', 'conda', 'poetry'],
            'editor': ['VSCode', 'PyCharm', 'Jupyter']
        }

        return field in valid_values and value in valid_values[field]


class SessionHelper:
    """
    Helper para gestion avanzada de session attributes.

    Proporciona metodos para gestionar estado complejo en la sesion.
    """

    @staticmethod
    def increment_counter(
        handler_input: HandlerInput,
        counter_name: str
    ) -> int:
        """
        Incrementa un contador en session attributes.

        util para tracking de interacciones (ej: numero de diagnosticos en sesion).

        Args:
            handler_input: Input del request
            counter_name: Nombre del contador

        Returns:
            int: Valor actualizado del contador
        """
        session_attr = handler_input.attributes_manager.session_attributes
        current_value = session_attr.get(counter_name, 0)
        new_value = current_value + 1
        session_attr[counter_name] = new_value
        return new_value

    @staticmethod
    def add_to_history(
        handler_input: HandlerInput,
        history_key: str,
        item: Any,
        max_items: int = 5
    ) -> None:
        """
        Anhade un item al historial en session attributes.

        Mantiene solo los ultimos max_items items.

        Args:
            handler_input: Input del request
            history_key: Clave del historial
            item: Item a anhadir
            max_items: Numero máximo de items a mantener
        """
        session_attr = handler_input.attributes_manager.session_attributes
        history = session_attr.get(history_key, [])

        history.append(item)

        # Mantener solo los ultimos max_items
        if len(history) > max_items:
            history = history[-max_items:]

        session_attr[history_key] = history

    @staticmethod
    def get_history(
        handler_input: HandlerInput,
        history_key: str
    ) -> list:
        """
        Obtiene el historial desde session attributes.

        Args:
            handler_input: Input del request
            history_key: Clave del historial

        Returns:
            list: Historial de items
        """
        session_attr = handler_input.attributes_manager.session_attributes
        return session_attr.get(history_key, [])


# ============================================================================
# Decoradores de Utilidad
# ============================================================================

def require_profile(func):
    """
    Decorador que asegura que el usuario tenga un perfil configurado.

    Si no tiene perfil, solicita al usuario que lo configure.
    """

    def wrapper(self, handler_input: HandlerInput) -> Response:
        profile = self.get_user_profile(handler_input)

        if not profile.is_configured:
            # Guardar errorText pendiente si existe (para DiagnoseIntent)
            error_text = None
            try:
                slots = handler_input.request_envelope.request.intent.slots
                if slots and 'errorText' in slots and slots['errorText'].value:
                    error_text = slots['errorText'].value
                    # Guardar en sesión para procesarlo después
                    self.set_session_attribute(
                        handler_input, 'pending_error_text', error_text)
            except Exception as e:
                self.logger.warning(
                    f"Error getting pending error text: {str(e)}")

            speak_output = (
                "Primero necesito que configures tu perfil. "
                "Dime, que sistema operativo usas? "
                "Por ejemplo: 'uso Windows y conda'."
            )

            return (
                handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
            )

        return func(self, handler_input)

    return wrapper


def log_execution_time(func):
    """
    Decorador que registra el tiempo de ejecucion de un handler.

    Usa el singleton LoggerManager para logging consistente.
    """
    import time

    def wrapper(self, handler_input: HandlerInput) -> Response:
        start_time = time.time()

        response = func(self, handler_input)

        duration = time.time() - start_time
        duration_ms = duration * 1000

        # Usar singleton centralizado para logging
        logger_mgr = get_logger_manager()
        logger_mgr.info(
            f"Execution completed",
            context={
                'handler': self.__class__.__name__,
                'duration_ms': f"{duration_ms:.2f}"
            },
            logger_name='performance'
        )

        # Actualizar log de response con duration
        try:
            has_card = hasattr(response, 'card') and response.card is not None
            should_end = response.should_end_session
            logger_mgr.log_response(
                intent_name=self.intent_name,
                has_card=has_card,
                should_end=should_end,
                duration_ms=duration_ms
            )
        except:
            pass

        return response

    return wrapper
