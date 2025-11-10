"""
Paquete de intents para Doctor de Errores.

Este paquete contiene todos los intent handlers de la skill.
"""

from .diagnose_intent import DiagnoseIntentHandler
from .more_intent import MoreIntentHandler
from .send_card_intent import SendCardIntentHandler
from .why_intent import WhyIntentHandler
from .set_profile_intent import SetProfileIntentHandler

__all__ = [
    'DiagnoseIntentHandler',
    'MoreIntentHandler',
    'SendCardIntentHandler',
    'WhyIntentHandler',
    'SetProfileIntentHandler'
]
