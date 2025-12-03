"""
Interceptors para request y response de Alexa.

Este modulo implementa interceptores que se ejecutan antes y despues
de cada request para agregar funcionalidad transversal como logging,
metricas, validacion, etc.

Patterns:
- Interceptor/Middleware: Procesamiento pre/post request
- Chain of Responsibility: Cadena de interceptores
"""

from typing import Optional
import time
from datetime import datetime

from ask_sdk_core.dispatch_components import (
    AbstractRequestInterceptor,
    AbstractResponseInterceptor
)
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response

from utils import get_logger
from services.storage import storage_service
from models import UserProfile


class LoggingRequestInterceptor(AbstractRequestInterceptor):
    """
    Interceptor que loguea todos los requests entrantes.

    Registra informacion util para debugging como:
    - Tipo de request
    - Usuario ID
    - Session ID
    - Timestamp
    - Locale
    """

    def __init__(self):
        """Inicializa el interceptor."""
        self.logger = get_logger(self.__class__.__name__)

    def process(self, handler_input: HandlerInput) -> None:
        """
        Procesa el request antes de manejarlo.

        Args:
            handler_input: Input del request
        """
        request_envelope = handler_input.request_envelope
        request = request_envelope.request
        session = request_envelope.session

        # Extraer informacion
        request_type = request.object_type
        request_id = request.request_id
        user_id = None
        session_id = None

        if session:
            session_id = session.session_id
            if session.user:
                user_id = session.user.user_id

        locale = request.locale if hasattr(request, 'locale') else 'unknown'

        # Log estructurado
        self.logger.info(
            f"Incoming request: {request_type}",
            extra={
                'request_type': request_type,
                'request_id': request_id,
                'user_id': user_id,
                'session_id': session_id,
                'locale': locale,
                'timestamp': datetime.utcnow().isoformat()
            }
        )

        # Guardar timestamp para calcular duracion
        handler_input.request_envelope.context.timestamp_start = time.time()


class LoggingResponseInterceptor(AbstractResponseInterceptor):
    """
    Interceptor que loguea todas las respuestas salientes.

    Registra informacion de la respuesta y metricas de performance.
    """

    def __init__(self):
        """Inicializa el interceptor."""
        self.logger = get_logger(self.__class__.__name__)

    def process(
        self,
        handler_input: HandlerInput,
        response: Optional[Response]
    ) -> None:
        """
        Procesa la respuesta antes de enviarla.

        Args:
            handler_input: Input del request
            response: Response generada
        """
        request = handler_input.request_envelope.request
        request_type = request.object_type

        # Calcular duracion si timestamp_start existe
        duration_ms = None
        if hasattr(handler_input.request_envelope.context, 'timestamp_start'):
            start_time = handler_input.request_envelope.context.timestamp_start
            duration_ms = (time.time() - start_time) * 1000

        # Extraer informacion de la respuesta
        has_speech = False
        has_card = False
        should_end_session = False

        if response:
            if response.output_speech:
                has_speech = True
            if response.card:
                has_card = True
            if response.should_end_session is not None:
                should_end_session = response.should_end_session

        # Log estructurado
        self.logger.info(
            f"Outgoing response for: {request_type}",
            extra={
                'request_type': request_type,
                'has_speech': has_speech,
                'has_card': has_card,
                'should_end_session': should_end_session,
                'duration_ms': duration_ms,
                'timestamp': datetime.utcnow().isoformat()
            }
        )


class SessionAttributesInterceptor(AbstractRequestInterceptor):
    """
    Interceptor que loguea atributos de sesion.

    Util para debugging de estado de sesion.
    """

    def __init__(self):
        """Inicializa el interceptor."""
        self.logger = get_logger(self.__class__.__name__)

    def process(self, handler_input: HandlerInput) -> None:
        """
        Procesa atributos de sesion.

        Args:
            handler_input: Input del request
        """
        session_attrs = handler_input.attributes_manager.session_attributes

        if session_attrs:
            # Loguear claves sin valores sensibles
            attrs_summary = {
                'has_user_profile': 'user_profile' in session_attrs,
                'has_last_diagnostic': 'last_diagnostic' in session_attrs,
                'solution_index': session_attrs.get('solution_index', 0),
                'num_attributes': len(session_attrs)
            }

            self.logger.debug(
                "Session attributes",
                extra=attrs_summary
            )


class ErrorHandlingInterceptor(AbstractRequestInterceptor):
    """
    Interceptor que inicializa manejo de errores.

    Configura contexto para captura de errores.
    """

    def __init__(self):
        """Inicializa el interceptor."""
        self.logger = get_logger(self.__class__.__name__)

    def process(self, handler_input: HandlerInput) -> None:
        """
        Inicializa contexto de error.

        Args:
            handler_input: Input del request
        """
        # Inicializar flag de error en contexto
        if not hasattr(handler_input.request_envelope.context, 'error_occurred'):
            handler_input.request_envelope.context.error_occurred = False


class MetricsInterceptor(AbstractResponseInterceptor):
    """
    Interceptor que colecta metricas.

    Registra metricas de uso para analytics.
    """

    def __init__(self):
        """Inicializa el interceptor."""
        self.logger = get_logger(self.__class__.__name__)

    def process(
        self,
        handler_input: HandlerInput,
        response: Optional[Response]
    ) -> None:
        """
        Colecta metricas del request.

        Args:
            handler_input: Input del request
            response: Response generada
        """
        request = handler_input.request_envelope.request
        request_type = request.object_type

        # Metricas basicas
        metrics = {
            'request_type': request_type,
            'locale': getattr(request, 'locale', 'unknown'),
            'timestamp': datetime.utcnow().isoformat()
        }

        # Agregar metricas de intent si aplica
        if request_type == 'IntentRequest':
            intent_name = request.intent.name
            metrics['intent_name'] = intent_name

            # Contar slots proporcionados
            if request.intent.slots:
                filled_slots = sum(
                    1 for slot in request.intent.slots.values()
                    if slot.value is not None
                )
                metrics['filled_slots'] = filled_slots

        # Agregar duracion si esta disponible
        if hasattr(handler_input.request_envelope.context, 'timestamp_start'):
            start_time = handler_input.request_envelope.context.timestamp_start
            metrics['duration_ms'] = (time.time() - start_time) * 1000

        # Log de metricas (en produccion, enviar a servicio de metricas)
        self.logger.info(
            "Metrics collected",
            extra=metrics
        )


class UserContextInterceptor(AbstractRequestInterceptor):
    """
    Interceptor que enriquece contexto con informacion del usuario.

    Carga perfil de usuario si existe y lo hace disponible.
    """

    def __init__(self):
        """Inicializa el interceptor."""
        self.logger = get_logger(self.__class__.__name__)

    def process(self, handler_input: HandlerInput) -> None:
        """
        Carga contexto de usuario.

        Args:
            handler_input: Input del request
        """
        session_attrs = handler_input.attributes_manager.session_attributes

        # Verificar si ya existe perfil en sesion
        if 'user_profile' in session_attrs:
            self.logger.debug("User profile found in session")
        else:
            # Cargar de DynamoDB si existe
            try:
                user_id = handler_input.request_envelope.session.user.user_id
                profile = storage_service.get_user_profile(user_id)

                if profile:
                    self.logger.info(
                        "User profile loaded from DynamoDB",
                        extra={'user_id': user_id}
                    )
                    # Cachear en o
                    session_attrs['user_profile'] = profile.to_dict()
                else:
                    self.logger.debug(
                        "No user profile in DynamoDB",
                        extra={'user_id': user_id}
                    )
            except Exception as e:
                self.logger.warning(
                    f"Failed to load user profile from DynamoDB: {e}",
                    exc_info=True
                )


class LocalizationInterceptor(AbstractRequestInterceptor):
    """
    Interceptor que maneja localizacion.

    Configura locale para respuestas internacionalizadas.
    """

    def __init__(self):
        """Inicializa el interceptor."""
        self.logger = get_logger(self.__class__.__name__)

    def process(self, handler_input: HandlerInput) -> None:
        """
        Configura locale.

        Args:
            handler_input: Input del request
        """
        request = handler_input.request_envelope.request
        locale = getattr(request, 'locale', 'es-MX')

        # Guardar locale en contexto para uso posterior
        handler_input.request_envelope.context.locale = locale

        self.logger.debug(f"Locale set to: {locale}")


class SessionPersistenceInterceptor(AbstractResponseInterceptor):
    """
    Interceptor que persiste atributos de sesion.

    Guarda datos importantes en almacenamiento persistente.
    """

    def __init__(self):
        """Inicializa el interceptor."""
        self.logger = get_logger(self.__class__.__name__)

    def process(
        self,
        handler_input: HandlerInput,
        response: Optional[Response]
    ) -> None:
        """
        Persiste datos de sesion si es necesario.

        Args:
            handler_input: Input del request
            response: Response generada
        """
        session_attrs = handler_input.attributes_manager.session_attributes

        # Si hay perfil de usuario y la o termina, persistir
        if 'user_profile' in session_attrs:
            should_persist = (
                response and response.should_end_session
            ) or session_attrs.get('profile_updated', False)

            if should_persist:
                try:
                    user_id = handler_input.request_envelope.session.user.user_id
                    profile_dict = session_attrs['user_profile']
                    profile = UserProfile.from_dict(profile_dict)

                    success = storage_service.save_user_profile(
                        user_id, profile)

                    if success:
                        self.logger.info(
                            "User profile persisted to DynamoDB",
                            extra={'user_id': user_id}
                        )
                        session_attrs.pop('profile_updated', None)
                    else:
                        self.logger.warning(
                            "DynamoDB not available, profile not persisted",
                            extra={'user_id': user_id}
                        )
                except Exception as e:
                    self.logger.error(
                        f"Failed to persist user profile: {e}",
                        exc_info=True
                    )


# Lista de interceptores recomendados para registro
RECOMMENDED_REQUEST_INTERCEPTORS = [
    LoggingRequestInterceptor(),
    SessionAttributesInterceptor(),
    ErrorHandlingInterceptor(),
    UserContextInterceptor(),
    LocalizationInterceptor()
]

RECOMMENDED_RESPONSE_INTERCEPTORS = [
    LoggingResponseInterceptor(),
    MetricsInterceptor(),
    SessionPersistenceInterceptor()
]
