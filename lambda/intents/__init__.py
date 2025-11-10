"""
Paquete de intents para Doctor de Errores.

Este paquete contiene todos los intent handlers de la skill.
"""

from intents.diagnose_intent import DiagnoseIntentHandler
from intents.more_intent import MoreIntentHandler
from intents.send_card_intent import SendCardIntentHandler
from intents.why_intent import WhyIntentHandler
from intents.set_profile_intent import SetProfileIntentHandler

__all__ = [
    'DiagnoseIntentHandler',
    'MoreIntentHandler',
    'SendCardIntentHandler',
    'WhyIntentHandler',
    'SetProfileIntentHandler'
]
