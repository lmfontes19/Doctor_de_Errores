"""
Utilidades comunes para Doctor de Errores.

Este modulo centraliza utilidades compartidas por toda la aplicacion,
incluyendo el LoggerManager Singleton para logging consistente.
"""

import logging
import sys
import os
from typing import Optional, Dict, Any
from datetime import datetime

import boto3
from botocore.exceptions import ClientError


# ============================================================================
# Singleton Logger - Patron Singleton para gestion centralizada de logging
# ============================================================================

class LoggerManager:
    """
    Singleton para gestion centralizada de logging.

    Proporciona una interfaz unificada para logging en toda la aplicacion,
    con configuracion centralizada y formateo consistente.

    Features:
    - Singleton: Una sola instancia en toda la aplicacion
    - Configuracion centralizada
    - Formateo consistente de mensajes
    - Diferentes niveles de log
    - Contexto adicional (user_id, intent_name, etc.)

    Usage:
        from utils import get_logger_manager

        logger_mgr = get_logger_manager()
        logger_mgr.info("Message")
        logger_mgr.error("Error", exc_info=True)
        logger_mgr.debug("Debug info", context={'user_id': '123'})
    """
    _instance = None

    def __new__(cls):
        """
        Implementacion del patron Singleton.

        Asegura que solo exista una instancia de LoggerManager.
        """
        if cls._instance is None:
            cls._instance = super(LoggerManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """
        Inicializa el logger manager (solo una vez).
        """
        if self._initialized:
            return

        self._initialized = True
        self._loggers = {}
        self._default_level = logging.INFO
        self._setup_root_logger()

    def _setup_root_logger(self):
        """
        Configura el logger raíz con formato y handlers.
        """
        # Formato personalizado con mas informacion
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Handler para stdout
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self._default_level)
        console_handler.setFormatter(formatter)

        # Configurar root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self._default_level)

        # Evitar duplicados
        if not root_logger.handlers:
            root_logger.addHandler(console_handler)

    def get_logger(self, name: str) -> logging.Logger:
        """
        Obtiene un logger por nombre (con cache).

        Args:
            name: Nombre del logger (típicamente __name__ del modulo)

        Returns:
            logging.Logger: Logger configurado
        """
        if name not in self._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(self._default_level)
            self._loggers[name] = logger

        return self._loggers[name]

    def set_level(self, level: int):
        """
        Establece el nivel de logging global.

        Args:
            level: Nivel de logging (logging.DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self._default_level = level
        logging.getLogger().setLevel(level)

        # Actualizar loggers existentes
        for logger in self._loggers.values():
            logger.setLevel(level)

    @classmethod
    def get_instance(cls) -> 'LoggerManager':
        """
        Obtiene la instancia única del LoggerManager.

        Returns:
            LoggerManager: Instancia única del singleton
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def info(self, message: str, context: Optional[Dict[str, Any]] = None, logger_name: str = 'default'):
        """
        Log de nivel INFO con contexto opcional.

        Args:
            message: Mensaje a registrar
            context: Contexto adicional (opcional)
            logger_name: Nombre del logger a usar
        """
        logger = self.get_logger(logger_name)
        if context:
            message = f"{message} | Context: {context}"
        logger.info(message)

    def debug(self, message: str, context: Optional[Dict[str, Any]] = None, logger_name: str = 'default'):
        """
        Log de nivel DEBUG con contexto opcional.

        Args:
            message: Mensaje a registrar
            context: Contexto adicional (opcional)
            logger_name: Nombre del logger a usar
        """
        logger = self.get_logger(logger_name)
        if context:
            message = f"{message} | Context: {context}"
        logger.debug(message)

    def warning(self, message: str, context: Optional[Dict[str, Any]] = None, logger_name: str = 'default'):
        """
        Log de nivel WARNING con contexto opcional.

        Args:
            message: Mensaje a registrar
            context: Contexto adicional (opcional)
            logger_name: Nombre del logger a usar
        """
        logger = self.get_logger(logger_name)
        if context:
            message = f"{message} | Context: {context}"
        logger.warning(message)

    def error(self, message: str, exc_info: bool = False, context: Optional[Dict[str, Any]] = None, logger_name: str = 'default'):
        """
        Log de nivel ERROR con contexto opcional y stack trace.

        Args:
            message: Mensaje a registrar
            exc_info: Si incluir informacion de excepcion
            context: Contexto adicional (opcional)
            logger_name: Nombre del logger a usar
        """
        logger = self.get_logger(logger_name)
        if context:
            message = f"{message} | Context: {context}"
        logger.error(message, exc_info=exc_info)

    def log_request(self, intent_name: str, user_id: str, locale: str, slots: Dict[str, Any]):
        """
        Log especializado para requests de Alexa.

        Args:
            intent_name: Nombre del intent
            user_id: ID del usuario (truncado para privacidad)
            locale: Locale del request
            slots: Slots del request
        """
        self.info(
            f"Alexa Request",
            context={
                'intent': intent_name,
                'user': user_id[:8] + '...' if len(user_id) > 8 else user_id,
                'locale': locale,
                'slots': slots
            },
            logger_name='alexa.requests'
        )

    def log_response(self, intent_name: str, has_card: bool, should_end: bool, duration_ms: Optional[float] = None):
        """
        Log especializado para responses de Alexa.

        Args:
            intent_name: Nombre del intent
            has_card: Si la respuesta incluye card
            should_end: Si termina la sesion
            duration_ms: Duracion del procesamiento en ms (opcional)
        """
        context = {
            'intent': intent_name,
            'has_card': has_card,
            'end_session': should_end
        }

        if duration_ms is not None:
            context['duration_ms'] = f"{duration_ms:.2f}"

        self.info(
            f"Alexa Response",
            context=context,
            logger_name='alexa.responses'
        )

    def log_diagnostic(self, error_type: str, confidence: float, source: str):
        """
        Log especializado para diagnosticos.

        Args:
            error_type: Tipo de error diagnosticado
            confidence: Score de confianza
            source: Fuente del diagnostico (kb o ai)
        """
        self.info(
            f"Diagnostic Generated",
            context={
                'error_type': error_type,
                'confidence': confidence,
                'source': source
            },
            logger_name='diagnostics'
        )


# ============================================================================
# Funciones de Acceso al Singleton
# ============================================================================

def get_logger_manager() -> LoggerManager:
    """
    Funcion de conveniencia para obtener la instancia del LoggerManager.

    Returns:
        LoggerManager: Instancia única del singleton

    Usage:
        from utils import get_logger_manager

        logger_mgr = get_logger_manager()
        logger_mgr.info("Message")
    """
    return LoggerManager.get_instance()


def get_logger(name: str) -> logging.Logger:
    """
    Funcion de conveniencia para obtener un logger.

    Args:
        name: Nombre del logger (típicamente __name__)

    Returns:
        logging.Logger: Logger configurado

    Usage:
        from utils import get_logger

        logger = get_logger(__name__)
        logger.info("Message")
    """
    return LoggerManager.get_instance().get_logger(name)


# ============================================================================
# Utilidades de AWS S3
# ============================================================================

def create_presigned_url(object_name: str, expiration: int = 60) -> Optional[str]:
    """
    Genera una URL pre-firmada para compartir un objeto S3.

    Args:
        object_name: Nombre del objeto en S3
        expiration: Tiempo de expiracion en segundos (default: 60)

    Returns:
        Optional[str]: URL pre-firmada o None si hay error

    Usage:
        url = create_presigned_url('myfile.txt', expiration=120)
    """
    logger_mgr = get_logger_manager()

    try:
        s3_client = boto3.client(
            's3',
            region_name=os.environ.get('S3_PERSISTENCE_REGION'),
            config=boto3.session.Config(
                signature_version='s3v4',
                s3={'addressing_style': 'path'}
            )
        )

        bucket_name = os.environ.get('S3_PERSISTENCE_BUCKET')

        response = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_name
            },
            ExpiresIn=expiration
        )

        logger_mgr.debug(
            "Presigned URL generated",
            context={'object': object_name, 'expiration': expiration},
            logger_name='s3'
        )

        return response

    except ClientError as e:
        logger_mgr.error(
            f"Error generating presigned URL: {str(e)}",
            exc_info=True,
            context={'object': object_name},
            logger_name='s3'
        )
        return None


# ============================================================================
# Utilidades Generales
# ============================================================================

def truncate_text(text: str, max_length: int = 300, suffix: str = "...") -> str:
    """
    Trunca texto a una longitud maxima.

    Args:
        text: Texto a truncar
        max_length: Longitud maxima
        suffix: Sufijo a anhadir si se trunca (default: "...")

    Returns:
        str: Texto truncado

    Usage:
        short_text = truncate_text(long_text, max_length=100)
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def sanitize_user_data(text: str, keywords: list = None) -> str:
    """
    Sanitiza texto removiendo informacion potencialmente sensible.

    Args:
        text: Texto a sanitizar
        keywords: Lista de keywords a redactar (opcional)

    Returns:
        str: Texto sanitizado

    Usage:
        clean = sanitize_user_data(user_input, ['password', 'token'])
    """
    if keywords is None:
        keywords = ['password', 'token', 'secret',
                    'key', 'credential', 'api_key']

    sanitized = text
    for keyword in keywords:
        if keyword.lower() in sanitized.lower():
            sanitized = sanitized.replace(keyword, '[REDACTED]')

    return sanitized


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """
    Formatea un timestamp de forma consistente.

    Args:
        dt: datetime object (default: now)

    Returns:
        str: Timestamp formateado

    Usage:
        timestamp = format_timestamp()
    """
    if dt is None:
        dt = datetime.now()

    return dt.strftime('%Y-%m-%d %H:%M:%S')


# ============================================================================
# Inicializacion del Logger Manager al importar el modulo
# ============================================================================

# Inicializar el singleton al importar
_logger_manager = LoggerManager.get_instance()
_module_logger = _logger_manager.get_logger(__name__)

_module_logger.info("Utils module loaded - LoggerManager initialized")
