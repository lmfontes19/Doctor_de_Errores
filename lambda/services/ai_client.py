"""
Cliente de servicios de IA para diagnostico de errores.

Este modulo implementa clientes para servicios de IA (AWS Bedrock, OpenAI)
que generan diagnosticos cuando la KB local no encuentra coincidencias.

Patterns:
- Strategy: Diferentes providers de IA intercambiables
- Factory Method: Creacion de clientes especificos
- Adapter: Adaptacion de APIs diferentes a interfaz comun
- Fallback Chain: Intentar providers en orden hasta conseguir respuesta
"""

import json
from typing import Optional, Dict, Any, List
from enum import Enum
from abc import ABC, abstractmethod

from models import Diagnostic, UserProfile, ErrorType, DiagnosticSource
from core.factories import DiagnosticFactory
from utils import get_logger


class AIProvider(Enum):
    """Providers de IA soportados."""
    BEDROCK = "bedrock"
    OPENAI = "openai"
    MOCK = "mock"  # Para testing


class AIClientError(Exception):
    """Excepcion base para errores de cliente AI."""
    pass


class AIProviderUnavailable(AIClientError):
    """Provider de IA no disponible."""
    pass


class AIResponseParseError(AIClientError):
    """Error parseando respuesta de IA."""
    pass


class BaseAIClient(ABC):
    """
    Cliente base para servicios de IA.

    Define interfaz comun para todos los providers.
    Pattern: Strategy + Template Method
    """

    def __init__(self):
        """Inicializa el cliente."""
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def generate_diagnostic(
        self,
        error_text: str,
        user_profile: UserProfile
    ) -> Optional[Diagnostic]:
        """
        Genera diagnostico usando IA.

        Args:
            error_text: Texto del error a diagnosticar
            user_profile: Perfil del usuario

        Returns:
            Diagnostic generado o None si falla
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Verifica si el provider esta disponible.

        Returns:
            True si esta disponible
        """
        pass

    def _build_prompt(
        self,
        error_text: str,
        user_profile: UserProfile
    ) -> str:
        """
        Construye prompt para el modelo de IA.

        Args:
            error_text: Texto del error
            user_profile: Perfil del usuario

        Returns:
            Prompt formateado
        """
        return f"""Eres un asistente experto en Python que diagnostica errores de programacion.

Error reportado por el usuario:
{error_text}

Contexto del usuario:
- Sistema operativo: {user_profile.os}
- Gestor de paquetes: {user_profile.package_manager}
- Editor: {user_profile.editor}

Proporciona un diagnostico estructurado en JSON con el siguiente formato:
{{
    "error_type": "tipo de error (ej: ModuleNotFoundError, SyntaxError)",
    "voice_text": "Explicacion breve para voz (2-3 oraciones)",
    "solutions": [
        "Solucion 1 especifica para {user_profile.os} y {user_profile.package_manager}",
        "Solucion 2",
        "Solucion 3"
    ],
    "explanation": "Explicacion tecnica detallada del error",
    "common_causes": [
        "Causa comun 1",
        "Causa comun 2"
    ]
}}

Importante:
- Las soluciones deben ser especificas para {user_profile.os} con {user_profile.package_manager}
- Usa comandos reales y exactos
- Se claro y conciso
- Responde SOLO con el JSON, sin texto adicional
"""

    def _parse_ai_response(
        self,
        response_text: str
    ) -> Dict[str, Any]:
        """
        Parsea respuesta de IA a diccionario.

        Args:
            response_text: Texto de respuesta del modelo

        Returns:
            Diccionario con datos estructurados

        Raises:
            AIResponseParseError: Si no se puede parsear
        """
        try:
            # Intentar extraer JSON de la respuesta
            # Algunos modelos añaden texto antes/despues del JSON
            start = response_text.find('{')
            end = response_text.rfind('}') + 1

            if start == -1 or end == 0:
                raise AIResponseParseError("No JSON found in response")

            json_text = response_text[start:end]
            data = json.loads(json_text)

            # Validar campos requeridos
            required_fields = ['error_type', 'voice_text', 'solutions']
            for field in required_fields:
                if field not in data:
                    raise AIResponseParseError(
                        f"Missing required field: {field}")

            return data

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            raise AIResponseParseError(f"Invalid JSON: {e}")


class BedrockAIClient(BaseAIClient):
    """
    Cliente para AWS Bedrock.

    Usa modelos como Claude de Anthropic via Bedrock.
    """

    def __init__(
        self,
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
        region: str = "us-east-1"
    ):
        """
        Inicializa cliente Bedrock.

        Args:
            model_id: ID del modelo en Bedrock
            region: Region de AWS
        """
        super().__init__()
        self.model_id = model_id
        self.region = region
        self._client = None

    def _get_client(self):
        """
        Obtiene cliente de Bedrock (lazy initialization).

        Returns:
            Cliente boto3 de Bedrock
        """
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    service_name='bedrock-runtime',
                    region_name=self.region
                )
            except Exception as e:
                self.logger.error(f"Failed to create Bedrock client: {e}")
                raise AIProviderUnavailable("Bedrock not available")

        return self._client

    def is_available(self) -> bool:
        """Verifica disponibilidad de Bedrock."""
        try:
            self._get_client()
            return True
        except Exception:
            return False

    def generate_diagnostic(
        self,
        error_text: str,
        user_profile: UserProfile
    ) -> Optional[Diagnostic]:
        """Genera diagnostico usando Bedrock."""
        try:
            client = self._get_client()
            prompt = self._build_prompt(error_text, user_profile)

            # Construir request para Claude
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }

            # Invocar modelo
            response = client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )

            # Parsear respuesta
            response_body = json.loads(response['body'].read())
            ai_text = response_body['content'][0]['text']

            # Parsear y crear Diagnostic
            data = self._parse_ai_response(ai_text)
            diagnostic = DiagnosticFactory.from_ai_result(data, user_profile)

            self.logger.info("Diagnostic generated via Bedrock")
            return diagnostic

        except AIClientError:
            raise
        except Exception as e:
            self.logger.error(f"Bedrock error: {e}", exc_info=True)
            raise AIProviderUnavailable(f"Bedrock failed: {e}")


class OpenAIClient(BaseAIClient):
    """
    Cliente para OpenAI API.

    Usa modelos como GPT-4 o GPT-3.5.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-3.5-turbo"
    ):
        """
        Inicializa cliente OpenAI.

        Args:
            api_key: API key de OpenAI (si None, busca en env)
            model: Modelo a usar
        """
        super().__init__()
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        """Obtiene cliente de OpenAI (lazy initialization)."""
        if self._client is None:
            try:
                import openai
                if self.api_key:
                    openai.api_key = self.api_key
                self._client = openai
            except Exception as e:
                self.logger.error(f"Failed to create OpenAI client: {e}")
                raise AIProviderUnavailable("OpenAI not available")

        return self._client

    def is_available(self) -> bool:
        """Verifica disponibilidad de OpenAI."""
        try:
            self._get_client()
            return True
        except Exception:
            return False

    def generate_diagnostic(
        self,
        error_text: str,
        user_profile: UserProfile
    ) -> Optional[Diagnostic]:
        """Genera diagnostico usando OpenAI."""
        try:
            client = self._get_client()
            prompt = self._build_prompt(error_text, user_profile)

            # Invocar modelo
            response = client.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system",
                        "content": "Eres un experto en Python que diagnostica errores."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )

            # Extraer respuesta
            ai_text = response.choices[0].message.content

            # Parsear y crear Diagnostic
            data = self._parse_ai_response(ai_text)
            diagnostic = DiagnosticFactory.from_ai_result(data, user_profile)

            self.logger.info("Diagnostic generated via OpenAI")
            return diagnostic

        except AIClientError:
            raise
        except Exception as e:
            self.logger.error(f"OpenAI error: {e}", exc_info=True)
            raise AIProviderUnavailable(f"OpenAI failed: {e}")


class MockAIClient(BaseAIClient):
    """
    Cliente mock para testing.

    Retorna respuestas predefinidas sin llamar a servicios reales.
    """

    def __init__(self):
        """Inicializa cliente mock."""
        super().__init__()

    def is_available(self) -> bool:
        """Mock siempre esta disponible."""
        return True

    def generate_diagnostic(
        self,
        error_text: str,
        user_profile: UserProfile
    ) -> Optional[Diagnostic]:
        """Genera diagnostico mock."""
        self.logger.info("Using mock AI client")

        # Diagnostico generico
        return DiagnosticFactory.create_error_diagnostic(
            error_message="Diagnostico generado por mock AI",
            error_type=ErrorType.GENERIC_ERROR.value
        )


class AIService:
    """
    Servicio principal de IA con fallback chain.

    Intenta providers en orden hasta obtener respuesta exitosa.
    Pattern: Chain of Responsibility + Facade
    """

    def __init__(
        self,
        providers: Optional[List[BaseAIClient]] = None
    ):
        """
        Inicializa servicio de IA.

        Args:
            providers: Lista de providers en orden de preferencia
        """
        self.logger = get_logger(self.__class__.__name__)

        if providers:
            self.providers = providers
        else:
            # Configuracion por defecto: intentar Bedrock, luego mock
            self.providers = [
                BedrockAIClient(),
                MockAIClient()
            ]

    def generate_diagnostic(
        self,
        error_text: str,
        user_profile: UserProfile
    ) -> Optional[Diagnostic]:
        """
        Genera diagnostico intentando providers en orden.

        Args:
            error_text: Texto del error
            user_profile: Perfil del usuario

        Returns:
            Diagnostic o None si todos fallan
        """
        self.logger.info(
            f"Generating AI diagnostic with {len(self.providers)} providers")

        for provider in self.providers:
            provider_name = provider.__class__.__name__

            # Verificar disponibilidad
            if not provider.is_available():
                self.logger.warning(f"{provider_name} not available, skipping")
                continue

            try:
                diagnostic = provider.generate_diagnostic(
                    error_text, user_profile)
                if diagnostic:
                    self.logger.info(
                        f"Diagnostic generated via {provider_name}")
                    return diagnostic

            except AIProviderUnavailable as e:
                self.logger.warning(f"{provider_name} unavailable: {e}")
                continue
            except AIClientError as e:
                self.logger.error(f"{provider_name} error: {e}")
                continue
            except Exception as e:
                self.logger.error(
                    f"Unexpected error with {provider_name}: {e}", exc_info=True)
                continue

        self.logger.error("All AI providers failed")
        return None

    def get_available_providers(self) -> List[str]:
        """
        Lista providers disponibles.

        Returns:
            Lista de nombres de providers disponibles
        """
        available = []
        for provider in self.providers:
            if provider.is_available():
                available.append(provider.__class__.__name__)
        return available


# Instancia por defecto del servicio
ai_service = AIService()


# Funciones de conveniencia
def generate_ai_diagnostic(
    error_text: str,
    user_profile: UserProfile
) -> Optional[Diagnostic]:
    """
    Genera diagnostico usando IA.

    Args:
        error_text: Texto del error
        user_profile: Perfil del usuario

    Returns:
        Diagnostic o None
    """
    return ai_service.generate_diagnostic(error_text, user_profile)
