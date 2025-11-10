"""
Paquete de servicios para Doctor de Errores.

Este paquete contiene servicios de:
- Knowledge Base: Busqueda en base de conocimiento local
- AI Client: Diagnostico con IA (Bedrock/OpenAI)
- Storage: Persistencia en DynamoDB
"""

from services.kb_service import (
    KnowledgeBaseService,
    kb_service,
    search_diagnostic,
    get_kb_statistics
)

from services.ai_client import (
    AIService,
    BedrockAIClient,
    OpenAIClient,
    MockAIClient,
    ai_service,
    generate_ai_diagnostic,
    AIProvider,
    AIClientError,
    AIProviderUnavailable
)

from services.storage import (
    StorageService,
    storage_service,
    save_user_profile,
    get_user_profile,
    save_diagnostic_to_history,
    StorageError,
    UserNotFoundError
)

__all__ = [
    # KB Service
    'KnowledgeBaseService',
    'kb_service',
    'search_diagnostic',
    'get_kb_statistics',

    # AI Service
    'AIService',
    'BedrockAIClient',
    'OpenAIClient',
    'MockAIClient',
    'ai_service',
    'generate_ai_diagnostic',
    'AIProvider',
    'AIClientError',
    'AIProviderUnavailable',

    # Storage Service
    'StorageService',
    'storage_service',
    'save_user_profile',
    'get_user_profile',
    'save_diagnostic_to_history',
    'StorageError',
    'UserNotFoundError'
]
