"""
Servicio de almacenamiento persistente para perfiles y diagnosticos.

Este modulo implementa la persistencia de datos del usuario en DynamoDB,
incluyendo perfiles de usuario, historial de diagnosticos y metricas.

Patterns:
- Repository: Abstraccion de acceso a datos
- Singleton: Instancia unica del servicio
- Data Mapper: Mapeo entre objetos de dominio y almacenamiento
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from decimal import Decimal

import boto3

from models import UserProfile, Diagnostic, SessionState
from utils import get_logger
from config.settings import (
    ENABLE_STORAGE,
    DYNAMODB_TABLE_NAME,
    AWS_REGION,
    EXT_AWS_ACCESS_KEY_ID,
    EXT_AWS_SECRET_ACCESS_KEY
)


class StorageError(Exception):
    """Excepcion base para errores de storage."""


class UserNotFoundError(StorageError):
    """Usuario no encontrado en storage."""


class StorageService:
    """
    Servicio de almacenamiento en DynamoDB.

    Maneja persistencia de perfiles de usuario, diagnosticos y sesiones.
    Pattern: Repository + Singleton
    """

    _instance: Optional['StorageService'] = None

    def __new__(cls):
        """Implementa Singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Inicializa el servicio."""
        self.logger = get_logger(self.__class__.__name__)
        self._dynamodb = None
        self._table = None

        self.table_name = DYNAMODB_TABLE_NAME

    def _get_table(self):
        """
        Obtiene referencia a tabla DynamoDB (lazy initialization).

        Soporta tanto credenciales IAM Role (self-hosted Lambda)
        como credenciales explicitas (Alexa-hosted con DynamoDB externa).

        Returns:
            Tabla de DynamoDB o None si no esta disponible
        """
        if self._table is None:
            try:
                # Si storage esta deshabilitado, no intentar conectar
                if not ENABLE_STORAGE:
                    self.logger.info("Storage deshabilitado por configuracion")
                    return None

                # Configurar cliente DynamoDB
                if EXT_AWS_ACCESS_KEY_ID and EXT_AWS_SECRET_ACCESS_KEY:
                    # Conexion con credenciales explicitas
                    self.logger.info(
                        "Using explicit AWS credentials for DynamoDB")
                    self._dynamodb = boto3.resource(
                        'dynamodb',
                        region_name=AWS_REGION,
                        aws_access_key_id=EXT_AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=EXT_AWS_SECRET_ACCESS_KEY
                    )
                else:
                    self.logger.info("Using IAM Role for DynamoDB")
                    self._dynamodb = boto3.resource(
                        'dynamodb', region_name=AWS_REGION)

                # Usar nombre de tabla desde settings
                self._table = self._dynamodb.Table(DYNAMODB_TABLE_NAME)

                self.logger.info(
                    f"Connected to DynamoDB table: {DYNAMODB_TABLE_NAME} in region: {AWS_REGION}")
            except Exception as e:
                self.logger.warning(f"DynamoDB no disponible: {e}")
                return None

        return self._table

    def is_available(self) -> bool:
        """
        Verifica si DynamoDB esta disponible.

        Returns:
            True si esta disponible
        """
        try:
            self._get_table()
            return True
        except Exception:
            return False

    def save_user_profile(
        self,
        user_id: str,
        profile: UserProfile
    ) -> bool:
        """
        Guarda perfil de usuario en DynamoDB.

        Args:
            user_id: ID del usuario de Alexa
            profile: Perfil a guardar

        Returns:
            True si se guardo exitosamente, False si DynamoDB no disponible
        """
        try:
            table = self._get_table()
            if table is None:
                self.logger.warning(
                    "DynamoDB no disponible, saltando guardado de perfil")
                return False

            # Convertir perfil a dict
            profile_data = profile.to_dict()

            # Item para DynamoDB
            item = {
                'userId': user_id,
                'profile': profile_data,
                'updatedAt': datetime.utcnow().isoformat(),
                'version': 1
            }

            # Guardar
            table.put_item(Item=item)

            self.logger.info(f"Profile saved for user: {user_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save profile: {e}", exc_info=True)
            return False

    def get_user_profile(
        self,
        user_id: str
    ) -> Optional[UserProfile]:
        """
        Obtiene perfil de usuario desde DynamoDB.

        Args:
            user_id: ID del usuario de Alexa

        Returns:
            UserProfile o None si no existe o DynamoDB no disponible
        """
        try:
            table = self._get_table()
            if table is None:
                self.logger.warning("DynamoDB no disponible, retornando None")
                return None

            self.logger.info(
                f"get_user_profile called with user_id={user_id!r}")

            if not user_id:
                self.logger.warning(
                    "user_id vacio o None, ignorando lookup en Dynamo")
                return None

            # Obtener item
            response = table.get_item(Key={"userId": user_id})

            if "Item" not in response:
                # Usuario nuevo, retornar None para que se use perfil por defecto
                self.logger.info(
                    f"No profile found for user: {user_id}, will use default")
                return None

            # Parsear perfil existente
            item = response["Item"]
            profile_data = item.get("profile")

            if not profile_data:
                self.logger.warning(
                    f"User item exists but has no profile: {user_id}")
                return None

            profile_data = self._deserialize_dynamodb(profile_data)

            profile = UserProfile.from_dict(profile_data)

            self.logger.info(f"Profile loaded for user: {user_id}")
            return profile

        except Exception as e:
            self.logger.error(f"Failed to get profile: {e}", exc_info=True)
            return None

    def save_diagnostic_history(
        self,
        user_id: str,
        diagnostic: Diagnostic
    ) -> bool:
        """
        Guarda diagnostico en historial del usuario.

        Args:
            user_id: ID del usuario
            diagnostic: Diagnostico a guardar

        Returns:
            True si se guardo exitosamente, False si DynamoDB no disponible
        """
        try:
            table = self._get_table()
            if table is None:
                self.logger.warning(
                    "DynamoDB no disponible, saltando guardado de historial")
                return False

            # Obtener historial actual
            response = table.get_item(Key={'userId': user_id})

            if 'Item' in response:
                item = response['Item']
                history = item.get('diagnosticHistory', [])
            else:
                history = []

            # Agregar nuevo diagnostico
            diagnostic_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'errorType': diagnostic.error_type,
                'source': diagnostic.source,
                'confidence': Decimal(str(diagnostic.confidence)),
                'solutionsCount': len(diagnostic.solutions) if diagnostic.solutions else 0
            }

            history.append(diagnostic_entry)

            # Limitar historial a ultimos 50
            if len(history) > 50:
                history = history[-50:]

            # Actualizar item
            table.update_item(
                Key={'userId': user_id},
                UpdateExpression='SET diagnosticHistory = :history, updatedAt = :timestamp',
                ExpressionAttributeValues={
                    ':history': history,
                    ':timestamp': datetime.utcnow().isoformat()
                }
            )

            self.logger.info(
                f"Diagnostic saved to history for user: {user_id}")
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to save diagnostic history: {e}", exc_info=True)
            return False

    def get_diagnostic_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Obtiene historial de diagnosticos del usuario.

        Args:
            user_id: ID del usuario
            limit: Numero maximo de diagnosticos a retornar

        Returns:
            Lista de diagnosticos (mas recientes primero)

        Raises:
            StorageError: Si falla la lectura
        """
        try:
            table = self._get_table()

            response = table.get_item(Key={'userId': user_id})

            if 'Item' not in response:
                return []

            history = response['Item'].get('diagnosticHistory', [])

            # Retornar ultimos N
            return list(reversed(history[-limit:]))

        except Exception as e:
            self.logger.error(
                f"Failed to get diagnostic history: {e}", exc_info=True)
            raise StorageError(f"History get failed: {e}")

    def save_session_state(
        self,
        user_id: str,
        session_state: SessionState
    ) -> bool:
        """
        Guarda estado de sesion temporal.

        Args:
            user_id: ID del usuario
            session_state: Estado de sesion

        Returns:
            True si se guardo exitosamente
        """
        try:
            table = self._get_table()

            # Convertir a dict
            state_data = {
                'user_profile': session_state.user_profile.to_dict() if session_state.user_profile else None,
                'last_diagnostic': self._diagnostic_to_dict(session_state.last_diagnostic) if session_state.last_diagnostic else None,
                'solution_index': session_state.solution_index
            }

            # Actualizar
            table.update_item(
                Key={'userId': user_id},
                UpdateExpression='SET sessionState = :state, sessionUpdatedAt = :timestamp',
                ExpressionAttributeValues={
                    ':state': state_data,
                    ':timestamp': datetime.utcnow().isoformat()
                }
            )

            self.logger.debug(f"Session state saved for user: {user_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save session state: {e}")
            return False

    def get_session_state(
        self,
        user_id: str
    ) -> Optional[SessionState]:
        """
        Obtiene estado de sesion guardado.

        Args:
            user_id: ID del usuario

        Returns:
            SessionState o None si no existe
        """
        try:
            table = self._get_table()

            response = table.get_item(Key={'userId': user_id})

            if 'Item' not in response:
                return None

            item = response['Item']

            # Verificar si estado de sesion existe y no esta expirado
            if 'sessionState' not in item:
                return None

            session_updated = item.get('sessionUpdatedAt')
            if session_updated:
                # Expirar sesiones mayores a 24 horas
                updated_time = datetime.fromisoformat(session_updated)
                if datetime.utcnow() - updated_time > timedelta(hours=24):
                    self.logger.info("Session state expired")
                    return None

            # Deserializar estado
            state_data = self._deserialize_dynamodb(item['sessionState'])

            # Reconstruir SessionState
            profile = UserProfile.from_dict(
                state_data['user_profile']) if state_data.get('user_profile') else None
            diagnostic = self._dict_to_diagnostic(
                state_data['last_diagnostic']) if state_data.get('last_diagnostic') else None

            return SessionState(
                user_profile=profile,
                last_diagnostic=diagnostic,
                solution_index=state_data.get('solution_index', 0)
            )

        except Exception as e:
            self.logger.error(f"Failed to get session state: {e}")
            return None

    def delete_user_data(
        self,
        user_id: str
    ) -> bool:
        """
        Elimina todos los datos de un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            True si se elimino exitosamente
        """
        try:
            table = self._get_table()
            table.delete_item(Key={'userId': user_id})
            self.logger.info(f"User data deleted: {user_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete user data: {e}")
            return False

    def get_user_statistics(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Obtiene estadisticas del usuario.

        Args:
            user_id: ID del usuario

        Returns:
            Diccionario con estadisticas
        """
        try:
            table = self._get_table()
            response = table.get_item(Key={'userId': user_id})

            if 'Item' not in response:
                return {
                    'total_diagnostics': 0,
                    'has_profile': False,
                    'last_updated': None
                }

            item = response['Item']
            history = item.get('diagnosticHistory', [])

            return {
                'total_diagnostics': len(history),
                'has_profile': 'profile' in item,
                'last_updated': item.get('updatedAt'),
                'profile_configured': item.get('profile') is not None
            }

        except Exception as e:
            self.logger.error(f"Failed to get user statistics: {e}")
            return {}

    def save_ai_diagnostic_cache(
        self,
        error_hash: str,
        diagnostic: Diagnostic,
        profile: 'UserProfile'
    ) -> bool:
        """
        Guarda un diagnostico de IA en cache para reutilizacion.

        Args:
            error_hash: Hash unico del error (basado en texto normalizado)
            diagnostic: Diagnostico completo generado por IA
            profile: Perfil del usuario (para contexto)

        Returns:
            True si se guardo exitosamente
        """
        try:
            table = self._get_table()
            if table is None:
                self.logger.warning("DynamoDB not available, skipping cache")
                return False

            ttl = int((datetime.utcnow() + timedelta(days=30)).timestamp())

            # Item de cache
            cache_item = {
                # Usar prefijo para identificar caches
                'userId': f'CACHE#{error_hash}',
                'diagnostic': self._diagnostic_to_dict(diagnostic),
                'profile_context': {
                    'os': profile.os.value,
                    'pm': profile.package_manager.value
                },
                'createdAt': datetime.utcnow().isoformat(),
                'ttl': ttl,
                'hit_count': 0
            }

            table.put_item(Item=cache_item)

            self.logger.info(
                "AI diagnostic cached",
                extra={'error_hash': error_hash[:16], 'ttl_days': 30}
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to cache AI diagnostic: {e}", exc_info=True)
            return False

    def get_ai_diagnostic_cache(
        self,
        error_hash: str,
        profile: 'UserProfile'
    ) -> Optional[Diagnostic]:
        """
        Recupera un diagnostico de IA desde cache.

        Args:
            error_hash: Hash del error
            profile: Perfil del usuario actual

        Returns:
            Diagnostic si existe en cache y es compatible, None en caso contrario
        """
        try:
            table = self._get_table()
            if table is None:
                return None

            self.logger.info(
                f"Looking up AI diagnostic cache for hash: {error_hash[:16]}..."
            )

            # Buscar en cache
            response = table.get_item(Key={'userId': f'CACHE#{error_hash}'})

            if 'Item' not in response:
                self.logger.debug(
                    f"Cache miss for error_hash: {error_hash[:16]}")
                return None

            cache_item = response['Item']

            # Verificar compatibilidad de perfil (OS y PM deben coincidir)
            cached_profile = cache_item.get('profile_context', {})
            if (cached_profile.get('os') != profile.os.value or
                    cached_profile.get('pm') != profile.package_manager.value):
                self.logger.debug(
                    "Cache profile mismatch",
                    extra={
                        'cached': cached_profile,
                        'current': {'os': profile.os.value, 'pm': profile.package_manager.value}
                    }
                )
                return None

            # Incrementar hit counter
            try:
                table.update_item(
                    Key={'userId': f'CACHE#{error_hash}'},
                    UpdateExpression='SET hit_count = hit_count + :inc',
                    ExpressionAttributeValues={':inc': 1}
                )
            except Exception:
                pass

            # Deserializar diagnostico
            diagnostic_data = self._deserialize_dynamodb(
                cache_item['diagnostic'])
            diagnostic = self._dict_to_diagnostic(diagnostic_data)

            self.logger.info(
                "Cache HIT for error",
                extra={
                    'error_hash': error_hash[:16],
                    'hit_count': cache_item.get('hit_count', 0) + 1
                }
            )

            return diagnostic

        except Exception as e:
            self.logger.error(
                f"Failed to get cached diagnostic: {e}", exc_info=True)
            return None

    def _diagnostic_to_dict(self, diagnostic: Diagnostic) -> Dict[str, Any]:
        """
        Convierte Diagnostic a diccionario para DynamoDB.

        Args:
            diagnostic: Diagnostic a convertir

        Returns:
            Diccionario serializable
        """
        return {
            'error_type': diagnostic.error_type,
            'voice_text': diagnostic.voice_text,
            'solutions': diagnostic.solutions or [],
            'explanation': diagnostic.explanation,
            'common_causes': diagnostic.common_causes or [],
            'related_errors': diagnostic.related_errors or [],
            'confidence': Decimal(str(diagnostic.confidence)),
            'source': diagnostic.source,
            'card_title': diagnostic.card_title,
            'card_text': diagnostic.card_text
        }

    def _dict_to_diagnostic(self, data: Dict[str, Any]) -> Diagnostic:
        """
        Convierte diccionario a Diagnostic.

        Args:
            data: Diccionario con datos

        Returns:
            Diagnostic reconstruido
        """
        return Diagnostic(
            error_type=data.get('error_type', ''),
            voice_text=data.get('voice_text', ''),
            solutions=data.get('solutions'),
            explanation=data.get('explanation'),
            common_causes=data.get('common_causes'),
            related_errors=data.get('related_errors'),
            confidence=float(data.get('confidence', 0.0)),
            source=data.get('source', ''),
            card_title=data.get('card_title'),
            card_text=data.get('card_text')
        )

    def _deserialize_dynamodb(self, data: Any) -> Any:
        """
        Deserializa datos de DynamoDB (Decimal -> float/int).

        DynamoDB usa Decimal para numeros, necesitamos convertir.

        Args:
            data: Datos de DynamoDB

        Returns:
            Datos deserializados
        """
        if isinstance(data, Decimal):
            if data % 1 == 0:
                return int(data)
            return float(data)

        if isinstance(data, dict):
            return {k: self._deserialize_dynamodb(v) for k, v in data.items()}

        if isinstance(data, list):
            return [self._deserialize_dynamodb(item) for item in data]

        return data


# Instancia singleton del servicio
storage_service = StorageService()


# Funciones de conveniencia
def save_user_profile(user_id: str, profile: UserProfile) -> bool:
    """
    Guarda perfil de usuario.

    Args:
        user_id: ID del usuario
        profile: Perfil a guardar

    Returns:
        True si se guardo exitosamente
    """
    return storage_service.save_user_profile(user_id, profile)


def get_user_profile(user_id: str) -> Optional[UserProfile]:
    """
    Obtiene perfil de usuario.

    Args:
        user_id: ID del usuario

    Returns:
        UserProfile o None
    """
    return storage_service.get_user_profile(user_id)


def save_diagnostic_to_history(user_id: str, diagnostic: Diagnostic) -> bool:
    """
    Guarda diagnostico en historial.

    Args:
        user_id: ID del usuario
        diagnostic: Diagnostico a guardar

    Returns:
        True si se guardo exitosamente
    """
    return storage_service.save_diagnostic_history(user_id, diagnostic)


def get_error_hash(error_text: str) -> str:
    """
    Genera hash unico para un error normalizado.

    Normaliza el texto del error (lowercase, sin espacios extra)
    y genera un hash SHA-256 para usar como clave de cache.

    Args:
        error_text: Texto del error

    Returns:
        Hash hexadecimal del error
    """
    import hashlib
    import re

    # Normalizar texto
    normalized = error_text.lower().strip()
    # Remover espacios multiples
    normalized = re.sub(r'\s+', ' ', normalized)
    # Remover caracteres especiales pero mantener espacios
    normalized = re.sub(r'[^a-z0-9\s]', '', normalized)

    # Generar hash
    hash_obj = hashlib.sha256(normalized.encode('utf-8'))
    return hash_obj.hexdigest()
