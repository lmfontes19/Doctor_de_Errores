"""
Paquete core para patrones de diseño y utilidades.

Este paquete contiene:
- Factories para crear objetos complejos
- Builders para construccion fluida de respuestas
- Interceptors para procesamiento transversal
- Prototype registry para templates
"""

from core.factories import (
    DiagnosticFactory,
    UserProfileFactory,
    ResponseFactory,
    SessionStateFactory
)

from core.response_builder import (
    AlexaResponseBuilder,
    DiagnosticResponseBuilder,
    ProfileResponseBuilder,
    response_builder,
    diagnostic_response,
    profile_response
)

from core.prototype import (
    DiagnosticPrototype,
    UserProfilePrototype,
    PrototypeRegistry,
    registry,
    get_diagnostic_template,
    get_profile_template
)

from core.interceptors import (
    RECOMMENDED_REQUEST_INTERCEPTORS,
    RECOMMENDED_RESPONSE_INTERCEPTORS
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
    'RECOMMENDED_RESPONSE_INTERCEPTORS'
]
