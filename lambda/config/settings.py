"""
Configuracion centralizada para Doctor de Errores.

Este modulo contiene todas las configuraciones de la aplicacion,
incluyendo settings de AI, DynamoDB, logging, etc.

Las configuraciones pueden ser sobrescritas con variables de entorno.
"""

import os
from pathlib import Path
from enum import Enum

class AIProvider(Enum):
    """Providers de IA soportados."""
    BEDROCK = "bedrock"
    OPENAI = "openai"
    MOCK = "mock"  # Para testing

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv

    # Buscar .env en el directorio lambda/
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print(f"Variables de entorno cargadas desde: {env_path}")
    else:
        print(f"Archivo .env no encontrado en: {env_path}")
        print("Usando variables de entorno del sistema o valores por defecto")
except ImportError:
    print("python-dotenv no instalado. Usando variables de entorno del sistema.")
except Exception as e:
    print(f"Error cargando .env: {e}")


# ============================================================================
# CONFIGURACION GENERAL
# ============================================================================

# Entorno de ejecucion (development, staging, production)
ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')
IS_PRODUCTION = ENVIRONMENT == 'production'
IS_DEVELOPMENT = ENVIRONMENT == 'development'

# Logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')


# ============================================================================
# CONFIGURACION DE KNOWLEDGE BASE
# ============================================================================

# Umbral de confianza para match en KB (0.0 - 1.0)
KB_CONFIDENCE_THRESHOLD = float(os.getenv('KB_CONFIDENCE_THRESHOLD', '0.60'))

# Path a KB templates (relativo a este archivo)
KB_TEMPLATES_PATH = os.path.join(
    os.path.dirname(__file__),
    'kb_templates.json'
)

MAX_SOLUTIONS=5

# ============================================================================
# CONFIGURACION DE AI SERVICE
# ============================================================================

# Provider preferido (bedrock, openai, mock)
AI_PROVIDER = os.getenv('AI_PROVIDER', 'openai')

# AWS Bedrock
BEDROCK_REGION = os.getenv('BEDROCK_REGION', 'us-east-1')
BEDROCK_MODEL_ID = os.getenv(
    'BEDROCK_MODEL_ID',
    'anthropic.claude-3-haiku-20240307-v1:0'
)
BEDROCK_MAX_TOKENS = int(os.getenv('BEDROCK_MAX_TOKENS', '1000'))
BEDROCK_TEMPERATURE = float(os.getenv('BEDROCK_TEMPERATURE', '0.3'))

# OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
OPENAI_MAX_TOKENS = int(os.getenv('OPENAI_MAX_TOKENS', '350'))
OPENAI_TEMPERATURE = float(os.getenv('OPENAI_TEMPERATURE', '0.2'))


# ============================================================================
# CONFIGURACION DE STORAGE (DYNAMODB)
# ============================================================================

# DynamoDB
DYNAMODB_TABLE_NAME = os.getenv('DYNAMODB_TABLE', 'DoctorErrores_Users')
DYNAMODB_REGION = os.getenv('DYNAMODB_REGION', 'us-east-1')
DYNAMODB_ENDPOINT = os.getenv('DYNAMODB_ENDPOINT')  # Para testing local
ENABLE_STORAGE = os.getenv('ENABLE_STORAGE', 'true').lower() == 'true'


# ============================================================================
# CONFIGURACION DE RESPUESTAS
# ============================================================================

# Limites de texto
MAX_VOICE_LENGTH = int(os.getenv('MAX_VOICE_LENGTH', '300'))
MAX_CARD_LENGTH = int(os.getenv('MAX_CARD_LENGTH', '1000'))
MAX_CARD_CONTENT_LENGTH = int(os.getenv('MAX_CARD_CONTENT_LENGTH', '8000'))
MAX_VOICE_TEXT_LENGTH = MAX_VOICE_LENGTH
MAX_CARD_TEXT_LENGTH = MAX_CARD_LENGTH
MAX_CARD_TITLE_LENGTH = 100


# ============================================================================
# CONFIGURACION DE DESARROLLO
# ============================================================================

if IS_DEVELOPMENT:
    # En desarrollo, usar logs más verbosos
    LOG_LEVEL = 'DEBUG'

    # Usar mock AI por defecto en desarrollo
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'mock')


# ============================================================================
# VALIDACION DE CONFIGURACION
# ============================================================================

def validate_config() -> bool:
    """
    Valida que la configuracion sea correcta.

    Returns:
        True si la configuracion es valida
    """
    errors = []

    # Validar AI provider
    if AI_PROVIDER not in [provider.value for provider in AIProvider]:
        errors.append(f"AI_PROVIDER invalido: {AI_PROVIDER}")

    # Validar que KB templates existe
    if not os.path.exists(KB_TEMPLATES_PATH):
        errors.append(f"KB templates no encontrado: {KB_TEMPLATES_PATH}")

    # Validar OpenAI si esta configurado
    if AI_PROVIDER == 'openai' and not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY requerido cuando AI_PROVIDER=openai")

    if errors:
        print("Errores de configuracion:")
        for error in errors:
            print(f"  - {error}")
        return False

    return True


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_config_summary() -> dict:
    """
    Obtiene resumen de configuracion (para debugging).

    Returns:
        Diccionario con configuracion actual
    """
    return {
        'environment': ENVIRONMENT,
        'log_level': LOG_LEVEL,
        'ai_provider': AI_PROVIDER,
        'kb_confidence_threshold': KB_CONFIDENCE_THRESHOLD,
        'storage_enabled': ENABLE_STORAGE,
        'openai_model': OPENAI_MODEL if AI_PROVIDER == 'openai' else None,
        'openai_max_tokens': OPENAI_MAX_TOKENS if AI_PROVIDER == 'openai' else None,
        'bedrock_model': BEDROCK_MODEL_ID if AI_PROVIDER == 'bedrock' else None,
        'dynamodb_table': DYNAMODB_TABLE_NAME if ENABLE_STORAGE else None,
    }


def print_config():
    """Imprime configuracion actual."""
    print("="*60)
    print("CONFIGURACION - DOCTOR DE ERRORES")
    print("="*60)

    config = get_config_summary()
    for key, value in config.items():
        print(f"  {key}: {value}")

    print("="*60)


# Validar configuracion al importar
if not validate_config():
    raise ValueError("Configuracion invalida. Revisa los errores arriba.")
