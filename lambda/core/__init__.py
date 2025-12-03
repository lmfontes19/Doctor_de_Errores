"""
Paquete core para patrones de diseño y utilidades.

Este paquete contiene:
- Factories para crear objetos complejos
- Builders para construccion fluida de respuestas
- Interceptors para procesamiento transversal
- Prototype registry para templates
- Strategies para diagnosticos
"""

from .factories import (
    DiagnosticFactory,
    UserProfileFactory,
    ResponseFactory,
    SessionStateFactory
)

from .response_builder import (
    AlexaResponseBuilder,
    DiagnosticResponseBuilder,
    ProfileResponseBuilder,
    response_builder,
    diagnostic_response,
    profile_response
)

from .prototype import (
    DiagnosticPrototype,
    UserProfilePrototype,
    PrototypeRegistry,
    registry,
    get_diagnostic_template,
    get_profile_template
)

from .interceptors import (
    RECOMMENDED_REQUEST_INTERCEPTORS,
    RECOMMENDED_RESPONSE_INTERCEPTORS
)

from .diagnostic_strategies import (
    DiagnosticStrategy,
    KnowledgeBaseStrategy,
    CachedAIDiagnosticStrategy,
    LiveAIDiagnosticStrategy,
    DiagnosticStrategyChain,
    create_default_strategy_chain
)

__all__ = [
    # Factories
    'DiagnosticFactory',
    'UserProfileFactory',
    'ResponseFactory',
    'SessionStateFactory',

    # Builders
    'AlexaResponseBuilder',
    'DiagnosticResponseBuilder',
    'ProfileResponseBuilder',
    'response_builder',
    'diagnostic_response',
    'profile_response',

    # Prototype
    'DiagnosticPrototype',
    'UserProfilePrototype',
    'PrototypeRegistry',
    'registry',
    'get_diagnostic_template',
    'get_profile_template',

    # Interceptors
    'RECOMMENDED_REQUEST_INTERCEPTORS',
    'RECOMMENDED_RESPONSE_INTERCEPTORS',

    # Strategies
    'DiagnosticStrategy',
    'KnowledgeBaseStrategy',
    'CachedAIDiagnosticStrategy',
    'LiveAIDiagnosticStrategy',
    'DiagnosticStrategyChain',
    'create_default_strategy_chain'
]
