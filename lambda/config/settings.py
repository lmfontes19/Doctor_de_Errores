"""
Configuracion centralizada para Doctor de Errores.

Este modulo contiene todas las configuraciones de la aplicacion,
incluyendo settings de AI, DynamoDB, logging, etc.

Las configuraciones pueden ser sobrescritas con variables de entorno.
"""

import os
from typing import Optional


# ============================================================================
# CONFIGURACION GENERAL
# ============================================================================

# Entorno de ejecucion
ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')  # development, staging, production
IS_PRODUCTION = ENVIRONMENT == 'production'
IS_DEVELOPMENT = ENVIRONMENT == 'development'

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')  # DEBUG, INFO, WARNING, ERROR, CRITICAL


# ============================================================================
# CONFIGURACION DE ALEXA
# ============================================================================

# Skill ID (para validacion)
SKILL_ID = os.getenv('SKILL_ID', '')

# Timeouts
RESPONSE_TIMEOUT = 30  # segundos


# ============================================================================
# CONFIGURACION DE KNOWLEDGE BASE
# ============================================================================

# Umbrales de confianza
KB_CONFIDENCE_THRESHOLD = float(os.getenv('KB_CONFIDENCE_THRESHOLD', '0.70'))
KB_MIN_CONFIDENCE = 0.3

# Path a KB templates (relativo a este archivo)
KB_TEMPLATES_PATH = os.path.join(
    os.path.dirname(__file__),
    'kb_templates.json'
)


# ============================================================================
# CONFIGURACION DE AI SERVICE
# ============================================================================

# Provider preferido
AI_PROVIDER = os.getenv('AI_PROVIDER', 'bedrock')  # bedrock, openai, mock

# AWS Bedrock
BEDROCK_REGION = os.getenv('BEDROCK_REGION', 'us-east-1')
BEDROCK_MODEL_ID = os.getenv(
    'BEDROCK_MODEL_ID',
    'anthropic.claude-3-haiku-20240307-v1:0'
)
BEDROCK_MAX_TOKENS = int(os.getenv('BEDROCK_MAX_TOKENS', '1000'))
BEDROCK_TEMPERATURE = float(os.getenv('BEDROCK_TEMPERATURE', '0.3'))

# OpenAI (opcional)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
OPENAI_MAX_TOKENS = int(os.getenv('OPENAI_MAX_TOKENS', '1000'))
OPENAI_TEMPERATURE = float(os.getenv('OPENAI_TEMPERATURE', '0.3'))

# Fallback
AI_USE_FALLBACK = True  # Usar mock si AI falla


# ============================================================================
# CONFIGURACION DE STORAGE (DYNAMODB)
# ============================================================================

# DynamoDB
DYNAMODB_TABLE_NAME = os.getenv('DYNAMODB_TABLE', 'DoctorErrores_Users')
DYNAMODB_REGION = os.getenv('DYNAMODB_REGION', 'us-east-1')
DYNAMODB_ENDPOINT = os.getenv('DYNAMODB_ENDPOINT')  # Para testing local

# Cache
SESSION_CACHE_TTL = 86400  # 24 horas en segundos
DIAGNOSTIC_HISTORY_LIMIT = 50  # Maximo de diagnosticos en historial


# ============================================================================
# CONFIGURACION DE RESPUESTAS
# ============================================================================

# Limites de texto
MAX_VOICE_TEXT_LENGTH = 300  # caracteres
MAX_CARD_TEXT_LENGTH = 1000  # caracteres
MAX_CARD_TITLE_LENGTH = 100  # caracteres

# Personalizacion
DEFAULT_OS = 'linux'
DEFAULT_PACKAGE_MANAGER = 'pip'
DEFAULT_EDITOR = 'vscode'


# ============================================================================
# CONFIGURACION DE FEATURES
# ============================================================================

# Features flags
ENABLE_AI_DIAGNOSTICS = os.getenv('ENABLE_AI_DIAGNOSTICS', 'true').lower() == 'true'
ENABLE_STORAGE = os.getenv('ENABLE_STORAGE', 'true').lower() == 'true'
ENABLE_METRICS = os.getenv('ENABLE_METRICS', 'true').lower() == 'true'
ENABLE_DETAILED_LOGS = os.getenv('ENABLE_DETAILED_LOGS', 'false').lower() == 'true'


# ============================================================================
# CONFIGURACION DE INTERCEPTORS
# ============================================================================

# Logging interceptors
ENABLE_REQUEST_LOGGING = True
ENABLE_RESPONSE_LOGGING = True
ENABLE_SESSION_LOGGING = IS_DEVELOPMENT

# Metrics interceptors
ENABLE_PERFORMANCE_METRICS = True
ENABLE_USER_METRICS = True


# ============================================================================
# CONFIGURACION DE DESARROLLO
# ============================================================================

if IS_DEVELOPMENT:
    # En desarrollo, usar logs más verbosos
    LOG_LEVEL = 'DEBUG'
    ENABLE_DETAILED_LOGS = True
    
    # Usar mock AI por defecto en desarrollo
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'mock')
    
    # DynamoDB local si está configurado
    if not DYNAMODB_ENDPOINT:
        DYNAMODB_ENDPOINT = 'http://localhost:8000'


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
    if AI_PROVIDER not in ['bedrock', 'openai', 'mock']:
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
        'ai_enabled': ENABLE_AI_DIAGNOSTICS,
        'dynamodb_table': DYNAMODB_TABLE_NAME if ENABLE_STORAGE else None,
        'bedrock_model': BEDROCK_MODEL_ID if AI_PROVIDER == 'bedrock' else None
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
