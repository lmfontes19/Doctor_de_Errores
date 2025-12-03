# Arquitectura del Sistema - Doctor de Errores

## Vision General

**Doctor de Errores** implementa una arquitectura basada en patrones de disenho que garantiza:

- **Separacion de responsabilidades**: Cada componente tiene un proposito Unico y bien definido
- **Extensibilidad**: Facil agregar nuevos tipos de errores, estrategias o servicios de IA
- **Mantenibilidad**: Codigo limpio, documentado y testeable
- **Escalabilidad**: Preparado para crecer en funcionalidad sin reescrituras mayores

---

## Arquitectura de Alto Nivel

```
┌──────────────────────────────────────────────────────────────┐
│                      Alexa Platform                          │
│                   (Voice Interaction)                        │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    Lambda Function                           │
│                  (lambda_function.py)                        │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐   │
│  │              Request Handlers                         │   │
│  │  • LaunchRequestHandler                               │   │
│  │  • DiagnoseIntentHandler (Strategy Chain)             │   │
│  │  • SetProfileIntentHandler                            │   │
│  │  • ErrorDescriptionHandler                            │   │
│  │  • MoreIntentHandler, WhyIntentHandler, etc.          │   │
│  └───────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌───────────────────────────────────────────────────────┐   │
│  │               Core Layer                              │   │
│  │  • DiagnosticStrategies (Strategy + Chain)            │   │
│  │    - KnowledgeBaseStrategy                            │   │
│  │    - CachedAIDiagnosticStrategy                       │   │
│  │    - LiveAIDiagnosticStrategy                         │   │
│  │  • ResponseBuilder (Builder Pattern)                  │   │
│  │  • ResponseFactory (Factory Method)                   │   │
│  │  • DiagnosticFactory (Factory Method)                 │   │
│  │  • Interceptors (Decorator Pattern)                   │   │
│  │  • ErrorValidation (Facade + Strategy + Composite)    │   │
│  └───────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌───────────────────────────────────────────────────────┐   │
│  │              Services Layer                           │   │
│  │  • KnowledgeBaseService (Singleton)                   │   │
│  │  • AIService (Strategy + Fallback Chain)              │   │
│  │    - OpenAIClient (Proxy + Lazy Init)                 │   │
│  │    - BedrockAIClient                                  │   │
│  │    - MockAIClient                                     │   │
│  │  • StorageService (Repository + Singleton)            │   │
│  │    - User Profiles                                    │   │
│  │    - Diagnostic History                               │   │
│  │    - AI Cache (30-day TTL)                            │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                External Services                             │
│  • DynamoDB (Profiles + History + AI Cache)                  │
│  • Amazon Bedrock (AI Fallback)                              │
│  • OpenAI API (AI Primary)                                   │
│  • CloudWatch (Logging & Monitoring)                         │
└──────────────────────────────────────────────────────────────┘
```

---

## Componentes Principales

### 1. **Entry Point** (`lambda_function.py`)

- **Responsabilidad**: Punto de entrada de la Lambda function
- **Funciones**:
  - Registro de request handlers
  - Registro de interceptors
  - Configuracion del SkillBuilder
  - Routing de requests a handlers apropiados

```python
# Estructura tipica
sb = SkillBuilder()
sb.add_request_handler(DiagnoseIntentHandler())
sb.add_request_handler(SetProfileIntentHandler())
# ... mas handlers
sb.add_request_interceptor(LoggingInterceptor())
sb.add_response_interceptor(SanitizationInterceptor())
lambda_handler = sb.lambda_handler()
```

---

### 2. **Intent Handlers** (`intents/`)

Cada handler implementa la logica de negocio de un intent especifico.

#### **DiagnoseIntentHandler** (Principal)

```python
class DiagnoseIntentHandler(BaseIntentHandler):
    """
    Handler principal: detecta el error y genera diagnostico

    Flujo mejorado con Strategy Pattern + Chain of Responsibility:
    1. Valida que la descripción del error sea específica (ErrorValidation)
    2. Extrae errorText del slot
    3. Obtiene perfil del usuario (SO, gestor, editor)
    4. Ejecuta cadena de estrategias en orden:
       a) KnowledgeBaseStrategy (rápido, gratis, preciso)
       b) CachedAIDiagnosticStrategy (rápido, gratis, reutiliza)
       c) LiveAIDiagnosticStrategy (lento, costoso, flexible)
    5. Guarda diagnóstico en sesión y en historial persistente
    6. Construye respuesta con ResponseBuilder
    7. Retorna response con voz + card
    """

    def __init__(self):
        super().__init__()
        # Cadena de estrategias (Strategy Pattern + Chain of Responsibility)
        self.strategy_chain = create_default_strategy_chain()

    def can_handle(self, handler_input):
        return is_intent_name("DiagnoseIntent")(handler_input)

    @require_profile  # Decorator que verifica perfil configurado
    def handle_intent(self, handler_input):
        # 1. Extraer y validar error
        error_text = self.get_slot_value(handler_input, "errorText")
        
        if not self._is_valid_error_description(error_text):
            return self._handle_vague_error(handler_input, error_text)

        # 2. Obtener perfil
        user_profile = self.get_user_profile(handler_input)

        # 3. Ejecutar cadena de estrategias
        diagnostic = self.strategy_chain.search_diagnostic(
            error_text,
            user_profile
        )

        # 4. Fallback si todas las estrategias fallan
        if not diagnostic:
            diagnostic = self._create_fallback_diagnostic(user_profile)

        # 5. Guardar en sesión y persistencia
        self.save_last_diagnostic(handler_input, diagnostic)
        try:
            user_id = handler_input.request_envelope.session.user.user_id
            self.storage_service.save_diagnostic_history(user_id, diagnostic)
        except Exception as e:
            self.logger.warning(f"Failed to save diagnostic: {e}")

        # 6. Construir respuesta
        return self._build_diagnostic_response(
            handler_input,
            diagnostic,
            error_text
        )

    def _is_valid_error_description(self, error_text: str) -> bool:
        """Valida descripción usando sistema basado en patrones."""
        result = ErrorValidation.is_specific_enough(error_text)
        if not result.is_valid:
            self.logger.warning(f"Error rejected: {error_text[:50]}")
        return result.is_valid
```

#### **SetProfileIntentHandler**

- Captura preferencias del usuario (SO, gestor de paquetes, editor)
- Persiste en DynamoDB
- Usado por DiagnosticFactory para personalizar soluciones

#### **MoreIntentHandler**

- Retorna opciones alternativas del diagnostico
- Usa session attributes para mantener contexto

#### **WhyIntentHandler**

- Explica las causas raiz del error
- Lee de plantillas de KB o consulta IA

---

### 3. **Core Layer** (`core/`)

Implementa los patrones de disenho principales.

#### **3.1. ResponseBuilder** (Builder Pattern)

Construye respuestas de Alexa de forma fluida y consistente.

```python
class ResponseBuilder:
    """
    Builder para respuestas de Alexa con SSML, cards y reprompts

    Ventajas:
    - Interface fluida y legible
    - Validacion centralizada
    - Generacion consistente de SSML
    - Soporte para cards con imagenes
    """

    def __init__(self):
        self._speech = None
        self._reprompt = None
        self._card = None
        self._should_end_session = False

    def set_speech(self, text: str, use_ssml: bool = True):
        """Configura el texto de voz"""
        if use_ssml:
            self._speech = f"<speak>{text}</speak>"
        else:
            self._speech = text
        return self

    def set_reprompt(self, text: str):
        """Configura el reprompt"""
        self._reprompt = text
        return self

    def set_card(self, title: str, content: str, image_url: str = None):
        """Configura una card visual"""
        self._card = {
            "type": "Standard",
            "title": title,
            "text": content
        }

        if image_url:
            self._card["image"] = {"largeImageUrl": image_url}
        return self

    def end_session(self):
        """Marca que la sesion debe terminar"""
        self._should_end_session = True
        return self

    def build(self) -> Response:
        """Construye y valida la respuesta final"""
        # Validacion y construccion
        return response_object
```

**Uso:**

```python
response = ResponseBuilder() \
    .set_speech("El error ModuleNotFoundError indica que...") \
    .set_card("ModuleNotFoundError", "Pasos para resolverlo:\n1. ...") \
    .set_reprompt("Quieres mas detalles?") \
    .build()
```

---

#### **3.2. PrototypeManager** (Prototype Pattern)

Clona plantillas predefinidas de diagnostico para personalizarlas.

```python
class DiagnosticPrototype:
    """Plantilla base de diagnostico"""
    
    def __init__(self, error_type: str, base_message: str, 
                 solutions: List[str], causes: List[str]):
        self.error_type = error_type
        self.base_message = base_message
        self.solutions = solutions
        self.causes = causes

    def clone(self):
        """Crea una copia profunda"""
        return copy.deepcopy(self)

    def customize(self, profile: UserProfile):
        """Personaliza segUn perfil del usuario"""
        # Adaptar soluciones al SO y gestor
        if profile.os == "Windows" and profile.package_manager == "conda":
            self.solutions = self._adapt_for_conda_windows()
        elif profile.os == "macOS" and profile.package_manager == "pip":
            self.solutions = self._adapt_for_pip_macos()
        # etc.
        return self


class PrototypeManager:
    """Gestiona el registro y clonacion de prototipos"""

    def __init__(self):
        self._prototypes = {}
        self._load_prototypes()

    def _load_prototypes(self):
        """Carga prototipos desde kb_templates.json"""
        with open("config/kb_templates.json") as f:
            templates = json.load(f)

        for template in templates:
            prototype = DiagnosticPrototype(**template)
            self._prototypes[template["error_type"]] = prototype

    def get_diagnostic(self, error_type: str, profile: UserProfile):
        """Clona y personaliza un prototipo"""
        prototype = self._prototypes.get(error_type)
        if not prototype:
            return None

        return prototype.clone().customize(profile)
```

**Ventajas:**
- No reconstruir diagnosticos desde cero cada vez
- Personalizacion eficiente basada en perfil
- Facil gestion de plantillas

---

#### **3.3. DiagnosticStrategies** (Strategy Pattern + Chain of Responsibility)

Cadena de estrategias de búsqueda que se ejecutan en orden de prioridad.

```python
class DiagnosticStrategy(ABC):
    """Interfaz para estrategias de búsqueda de diagnósticos."""

    @abstractmethod
    def search_diagnostic(
        self,
        error_text: str,
        user_profile: UserProfile
    ) -> Optional[Diagnostic]:
        """Busca diagnóstico usando esta estrategia."""
        pass

    @abstractmethod
    def get_priority(self) -> int:
        """Prioridad de ejecución (1 = máxima)."""
        pass


class KnowledgeBaseStrategy(DiagnosticStrategy):
    """
    Estrategia 1: Búsqueda en Knowledge Base local
    
    Prioridad: 1 (máxima)
    Ventajas: Rápido (<100ms), gratis, offline, preciso
    Desventajas: Solo errores conocidos
    """

    def __init__(self):
        super().__init__()
        self.kb_service = kb_service
        self.confidence_threshold = KB_CONFIDENCE_THRESHOLD

    def search_diagnostic(self, error_text, user_profile):
        diagnostic = self.kb_service.search_diagnostic(
            error_text,
            user_profile
        )

        if diagnostic and diagnostic.confidence >= self.confidence_threshold:
            self.logger.info(f"KB match: {diagnostic.error_type}")
            diagnostic.source = DiagnosticSource.KNOWLEDGE_BASE.value
            return diagnostic

        return None

    def get_priority(self) -> int:
        return 1


class CachedAIDiagnosticStrategy(DiagnosticStrategy):
    """
    Estrategia 2: Búsqueda en cache de diagnósticos de IA
    
    Prioridad: 2
    Ventajas: Rápido (<50ms), gratis, reutiliza diagnósticos previos
    Desventajas: Solo disponible si alguien ya pidió el mismo error
    
    Validaciones:
    - NO retorna diagnósticos de error (confidence=0, source=unknown)
    - Verifica compatibilidad de perfil (OS + package manager)
    - Incrementa contador de hits
    """

    def __init__(self):
        super().__init__()
        self.storage_service = storage_service

    def search_diagnostic(self, error_text, user_profile):
        error_hash = get_error_hash(error_text)
        
        diagnostic = self.storage_service.get_ai_diagnostic_cache(
            error_hash,
            user_profile
        )

        if diagnostic:
            # Validar que no sea un diagnóstico de error
            if diagnostic.confidence == 0.0 or diagnostic.source == 'unknown':
                self.logger.warning("Cached diagnostic is invalid, ignoring")
                return None
            
            self.logger.info(f"Cache HIT: {diagnostic.error_type}")
            return diagnostic

        return None

    def get_priority(self) -> int:
        return 2


class LiveAIDiagnosticStrategy(DiagnosticStrategy):
    """
    Estrategia 3: Consulta a IA en vivo (OpenAI/Bedrock)
    
    Prioridad: 3 (última)
    Ventajas: Flexible, maneja cualquier error
    Desventajas: Lento (~2s), costo por llamada, requiere internet
    
    Caching inteligente:
    - Solo cachea diagnósticos válidos (confidence > 0, source != unknown)
    - Evita perpetuar errores temporales
    - TTL de 30 días
    """

    def __init__(self):
        super().__init__()
        # Lazy import para evitar importación circular
        from services.ai_client import ai_service
        self.ai_service = ai_service
        self.storage_service = storage_service

    def search_diagnostic(self, error_text, user_profile):
        try:
            diagnostic = self.ai_service.generate_diagnostic(
                error_text,
                user_profile
            )

            if diagnostic:
                # Guardar en cache (solo si es válido)
                self._cache_diagnostic(error_text, diagnostic, user_profile)
                return diagnostic

        except Exception as e:
            self.logger.error(f"AI service failed: {e}")

        return None

    def _cache_diagnostic(self, error_text, diagnostic, user_profile):
        """Cachea diagnóstico si es válido."""
        # NO cachear diagnósticos de error
        if diagnostic.confidence == 0.0 or diagnostic.source == 'unknown':
            self.logger.info(
                "Skipping cache for error diagnostic (confidence=0 or source=unknown)"
            )
            return
        
        try:
            error_hash = get_error_hash(error_text)
            self.storage_service.save_ai_diagnostic_cache(
                error_hash,
                diagnostic,
                user_profile
            )
            self.logger.info("Diagnostic cached for future use")
        except Exception as e:
            self.logger.error(f"Failed to cache: {e}")

    def get_priority(self) -> int:
        return 3


def create_default_strategy_chain() -> 'StrategyChain':
    """Factory para crear cadena de estrategias por defecto."""
    strategies = [
        KnowledgeBaseStrategy(),
        CachedAIDiagnosticStrategy(),
        LiveAIDiagnosticStrategy()
    ]
    
    # Ordenar por prioridad
    strategies.sort(key=lambda s: s.get_priority())
    
    return StrategyChain(strategies)


class StrategyChain:
    """Chain of Responsibility para estrategias."""

    def __init__(self, strategies: List[DiagnosticStrategy]):
        self.strategies = strategies

    def search_diagnostic(self, error_text, user_profile) -> Optional[Diagnostic]:
        """Ejecuta estrategias en orden hasta obtener resultado."""
        for strategy in self.strategies:
            diagnostic = strategy.search_diagnostic(error_text, user_profile)
            if diagnostic:
                return diagnostic
        
        return None
```

**Ventajas:**
- **Performance**: 90% de casos resueltos por KB (<100ms)
- **Costo**: Solo paga IA cuando es necesario
- **Resiliencia**: Si KB falla, cache o IA actúan como respaldo
- **Extensibilidad**: Fácil agregar nuevas estrategias
- **Cache inteligente**: Evita perpetuar errores temporales

---

#### **3.4. ErrorValidation** (Facade + Strategy + Composite + Value Object)

Sistema de validación de descripciones de error basado en patrones y principios SOLID.

```python
class ValidationResult:
    """
    Value Object - Encapsula resultado de validación.
    Inmutable, con semántica clara.
    """
    def __init__(self, is_valid: bool, message: Optional[str], score: float):
        self._is_valid = is_valid
        self._message = message
        self._score = score

    @property
    def is_valid(self) -> bool:
        return self._is_valid


class ErrorPattern(ABC):
    """
    Strategy Pattern - Base para detectores de patrones.
    Open/Closed Principle - Extensible sin modificar código existente.
    """
    @abstractmethod
    def matches(self, text: str) -> bool:
        pass

    @abstractmethod
    def get_confidence(self) -> float:
        pass


class PythonExceptionPattern(ErrorPattern):
    """Detecta excepciones de Python (NameError, ImportError, etc.)."""
    
    def matches(self, text: str) -> bool:
        pattern = r'\b[A-Z][a-zA-Z]*(Error|Exception)\b'
        return bool(re.search(pattern, text))
    
    def get_confidence(self) -> float:
        return 1.0


class NotFoundPattern(ErrorPattern):
    """Detecta frases 'not found'."""
    
    def matches(self, text: str) -> bool:
        patterns = [
            r'not found',
            r'no se encuentra',
            r'cannot find',
            r'no existe'
        ]
        text_lower = text.lower()
        return any(re.search(p, text_lower) for p in patterns)
    
    def get_confidence(self) -> float:
        return 0.8


class TechnicalNotationPattern(ErrorPattern):
    """Detecta notación técnica (package.module, snake_case)."""
    
    def matches(self, text: str) -> bool:
        patterns = [
            r'\b[a-z_]+\.[a-z_]+',  # package.module
            r'\b[a-z]+_[a-z_]+',     # snake_case
            r'\b[A-Z][a-z]+[A-Z]'    # CamelCase
        ]
        return any(re.search(p, text) for p in patterns)
    
    def get_confidence(self) -> float:
        return 0.6


class ErrorPatternMatcher:
    """
    Composite Pattern - Combina múltiples patrones.
    Single Responsibility - Solo coordina patrones.
    """
    
    def __init__(self, patterns: List[ErrorPattern]):
        self.patterns = patterns
    
    def has_match(self, text: str) -> bool:
        return any(p.matches(text) for p in self.patterns)
    
    def get_max_confidence(self, text: str) -> float:
        matches = [p.get_confidence() for p in self.patterns if p.matches(text)]
        return max(matches) if matches else 0.0


class ValidationRule(ABC):
    """
    Strategy Pattern - Base para reglas de validación.
    Interface Segregation - Interfaz mínima y enfocada.
    """
    @abstractmethod
    def validate(self, text: str) -> ValidationResult:
        pass


class EmptyTextRule(ValidationRule):
    """Rechaza texto vacío."""
    
    def validate(self, text: str) -> ValidationResult:
        if not text or not text.strip():
            return ValidationResult(
                is_valid=False,
                message="Necesito que me describas el error",
                score=0.0
            )
        return ValidationResult(is_valid=True, message=None, score=1.0)


class PatternBasedRule(ValidationRule):
    """Valida usando patrones y heurísticas de longitud."""
    
    def __init__(self, matcher: ErrorPatternMatcher):
        self.matcher = matcher
    
    def validate(self, text: str) -> ValidationResult:
        has_pattern = self.matcher.has_match(text)
        length = len(text.strip())
        
        # Texto muy corto sin patrones
        if length < 10 and not has_pattern:
            return ValidationResult(
                is_valid=False,
                message="Dame más detalles del error",
                score=0.2
            )
        
        # Tiene patrón técnico o es suficientemente largo
        if has_pattern or length >= 15:
            confidence = self.matcher.get_max_confidence(text)
            return ValidationResult(
                is_valid=True,
                message=None,
                score=confidence
            )
        
        # Caso edge: aceptar por defecto
        return ValidationResult(is_valid=True, message=None, score=0.5)


class ErrorValidator:
    """
    Chain of Responsibility - Ejecuta reglas en secuencia.
    Dependency Inversion - Depende de abstracciones (ValidationRule).
    """
    
    def __init__(self, rules: List[ValidationRule]):
        self.rules = rules
    
    def validate(self, text: str) -> ValidationResult:
        for rule in self.rules:
            result = rule.validate(text)
            if not result.is_valid:
                return result
        
        # Todas las reglas pasaron
        return ValidationResult(is_valid=True, message=None, score=1.0)


class ErrorValidation:
    """
    Facade Pattern - Interfaz simple para sistema complejo.
    Factory Method - Crea configuración por defecto.
    """
    
    _validator = None
    
    @classmethod
    def is_specific_enough(cls, text: str) -> Tuple[bool, Optional[str]]:
        """API pública simple."""
        validator = cls._get_validator()
        result = validator.validate(text)
        return (result.is_valid, result.message)
    
    @classmethod
    def _get_validator(cls) -> ErrorValidator:
        if cls._validator is None:
            # Factory: crear patrones
            patterns = [
                PythonExceptionPattern(),
                NotFoundPattern(),
                TechnicalNotationPattern(),
                # ... 5 patrones más
            ]
            
            matcher = ErrorPatternMatcher(patterns)
            
            # Factory: crear reglas
            rules = [
                EmptyTextRule(),
                MinimumLengthRule(),
                VaguePhraseRule(),
                PatternBasedRule(matcher)
            ]
            
            cls._validator = ErrorValidator(rules)
        
        return cls._validator
```

**Principios SOLID Aplicados:**
- **S**ingle Responsibility: Cada clase tiene una responsabilidad
- **O**pen/Closed: Extensible agregando patrones/reglas sin modificar existentes
- **L**iskov Substitution: Todos los ErrorPattern/ValidationRule son intercambiables
- **I**nterface Segregation: Interfaces mínimas (matches, validate)
- **D**ependency Inversion: PatternBasedRule depende de ErrorPatternMatcher (abstracción)

**Ventajas:**
- Sin listas estáticas de keywords
- Extensible con nuevos patrones
- Testeable independientemente
- Código profesional y mantenible

---

#### **3.5. Interceptors** (Decorator Pattern)

Anhaden funcionalidades transversales sin modificar la logica principal.

```python
class LoggingInterceptor(AbstractRequestInterceptor):
    """Interceptor para logging de requests"""

    def process(self, handler_input):
        logger.info(f"Request: {handler_input.request_envelope.request}")
        logger.info(f"Session: {handler_input.request_envelope.session}")


class SanitizationInterceptor(AbstractResponseInterceptor):
    """Interceptor para sanitizar informacion sensible"""

    def process(self, handler_input, response):
        # Remover tokens, passwords, etc.
        sanitized = self._sanitize(response.output_speech.ssml)
        response.output_speech.ssml = sanitized


class CacheInterceptor(AbstractRequestInterceptor):
    """Interceptor para cache de respuestas"""

    def process(self, handler_input):
        cache_key = self._generate_cache_key(handler_input)
        cached_response = cache.get(cache_key)

        if cached_response:
            handler_input.attributes_manager.request_attributes["cached"] = True
            return cached_response


class TelemetryInterceptor(AbstractResponseInterceptor):
    """Interceptor para metricas y analytics"""

    def process(self, handler_input, response):
        # Enviar metricas a CloudWatch
        metrics.put_metric("ResponseTime", response_time)
        metrics.put_metric("ErrorType", error_type)
```

**Registro:**

```python
sb.add_request_interceptor(LoggingInterceptor())
sb.add_request_interceptor(CacheInterceptor())
sb.add_response_interceptor(SanitizationInterceptor())
sb.add_response_interceptor(TelemetryInterceptor())
```

---

### 4. **Services Layer** (`services/`)

#### **4.1. KnowledgeBaseService** (`kb_service.py`)

Gestiona la base de conocimiento local.

```python
class KnowledgeBaseService:
    """
    Servicio de base de conocimiento local

    Responsabilidades:
    - Cargar plantillas desde kb_templates.json
    - Buscar diagnosticos por tipo de error
    - Matching con fuzzy search
    - Scoring de confianza
    """

    def __init__(self, templates_path: str):
        self.templates = self._load_templates(templates_path)
        self.prototype_manager = PrototypeManager()

    def find_diagnostic(self, error_text: str, 
                       profile: UserProfile) -> Optional[Diagnostic]:
        """
        Busca un diagnostico en la KB

        Algoritmo:
        1. Identificar tipo de error (regex patterns)
        2. Calcular score de confianza
        3. Si score > threshold, retornar diagnostico
        4. Si score < threshold, retornar None (fallback a IA)
        """
        matches = self._fuzzy_match(error_text)

        if not matches or matches[0].score < CONFIDENCE_THRESHOLD:
            return None

        best_match = matches[0]
        return self.prototype_manager.get_diagnostic(
            best_match.error_type, 
            profile
        )

    def _fuzzy_match(self, error_text: str) -> List[Match]:
        """Fuzzy matching con scoring"""
        # Implementacion de matching
        pass
```

---

#### **4.2. AIService** (`ai_client.py`)

Servicio de IA con múltiples providers y fallback chain.

```python
class AIService:
    """
    Servicio principal de IA con fallback chain.
    
    Patterns:
    - Strategy: Diferentes providers intercambiables
    - Chain of Responsibility: Intenta providers en orden
    - Facade: Interfaz simple para sistema complejo
    - Proxy + Lazy Init: Evita importaciones circulares
    
    Providers soportados:
    - OpenAI (primario): GPT-4o, GPT-3.5
    - Bedrock (alternativo): Claude, Llama
    - Mock (fallback): Respuestas genéricas
    """

    def __init__(self, providers: Optional[List[BaseAIClient]] = None):
        self.logger = get_logger(self.__class__.__name__)
        
        if providers:
            self.providers = providers
        else:
            # Configuración por defecto
            self.providers = [
                OpenAIClient(api_key=OPENAI_API_KEY, model=OPENAI_MODEL),
                MockAIClient()
            ]

    def generate_diagnostic(
        self,
        error_text: str,
        user_profile: UserProfile
    ) -> Optional[Diagnostic]:
        """
        Obtiene diagnostico de IA con fallback

        Flujo:
        1. Construir prompt contextual
        2. Intentar con Bedrock (si habilitado)
        3. Fallback a OpenAI si Bedrock falla
        4. Parsear respuesta y convertir a Diagnostic
        5. Optimizar para voz (max 300 chars)
        """
        prompt = self._build_prompt(error_text, profile)

        try:
            if self.config.enable_bedrock:
                response = self._call_bedrock(prompt)
            else:
                response = self._call_openai(prompt)
        except Exception as e:
            logger.error(f"AI fallback failed: {e}")
            return self._get_generic_response()

        return self._parse_response(response)

    def _build_prompt(self, error_text: str, profile: UserProfile) -> str:
        """Construye prompt contextual"""
        return f"""
        Eres un asistente de debugging para Python.

        Error: {error_text}
        SO: {profile.os}
        Gestor: {profile.package_manager}

        Proporciona:
        1. Explicacion breve (max 100 palabras)
        2. Solucion especifica para {profile.os} + {profile.package_manager}
        3. Comando exacto a ejecutar

        Respuesta optimizada para voz, clara y concisa.
        """

    def _call_bedrock(self, prompt: str) -> str:
        """Llamada a Bedrock"""
        response = self.bedrock_client.invoke_model(
            modelId=self.config.bedrock_model_id,
            body=json.dumps({
                "prompt": prompt,
                "max_tokens": 500,
                "temperature": 0.7
            })
        )
        return json.loads(response['body'].read())['completion']

    def _call_openai(self, prompt: str) -> str:
        """Llamada a OpenAI"""
        response = self.openai_client.chat.completions.create(
            model=self.config.openai_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7
        )
        return response.choices[0].message.content


# Decoradores
def cached(ttl: int):
    """Decorator para cache con TTL"""
    def decorator(func):
        cache = {}

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = _generate_cache_key(args, kwargs)

            if key in cache:
                entry = cache[key]
                if time.time() - entry['timestamp'] < ttl:
                    return entry['value']

            result = func(*args, **kwargs)
            cache[key] = {'value': result, 'timestamp': time.time()}
            return result

        return wrapper
    return decorator


def rate_limited(max_per_minute: int):
    """Decorator para rate limiting"""
    def decorator(func):
        calls = []

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            calls[:] = [c for c in calls if now - c < 60]

            if len(calls) >= max_per_minute:
                raise RateLimitExceeded("Too many AI requests")

            calls.append(now)
            return func(*args, **kwargs)

        return wrapper
    return decorator


def sanitized(func):
    """Decorator para sanitizar respuestas"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        # Remover informacion sensible
        result = _sanitize(result)
        return result
    return wrapper
```

---

#### **4.3. StorageService** (`storage.py`)

Gestiona persistencia de perfiles, historial y cache de IA en DynamoDB.

```python
class StorageService:
    """
    Servicio de persistencia en DynamoDB
    
    Patterns:
    - Repository: Abstracción de acceso a datos
    - Singleton: Instancia única del servicio
    - Data Mapper: Mapeo entre objetos y DynamoDB

    Tabla: DoctorErrores_Users
    Key: userId (partition key)
    
    Tipos de datos almacenados:
    1. Perfiles de usuario (userId)
    2. Historial de diagnósticos (userId#HISTORY#timestamp)
    3. Cache de diagnósticos de IA (CACHE#error_hash)
       - TTL: 30 días
       - Incluye contador de hits
       - Validación de perfil (OS + package manager)
    """

    def __init__(self, table_name: str):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Obtiene perfil del usuario"""
        try:
            response = self.table.get_item(Key={'userId': user_id})
            if 'Item' in response:
                return UserProfile(**response['Item'])
        except Exception as e:
            logger.error(f"Error getting profile: {e}")

        return self._get_default_profile()

    def save_profile(self, user_id: str, profile: UserProfile):
        """Guarda perfil del usuario."""
        self.table.put_item(
            Item={
                'userId': user_id,
                'os': profile.os,
                'package_manager': profile.package_manager,
                'editor': profile.editor,
                'timestamp': int(time.time())
            }
        )

    def save_ai_diagnostic_cache(
        self,
        error_hash: str,
        diagnostic: Diagnostic,
        profile: UserProfile
    ) -> bool:
        """
        Guarda diagnóstico de IA en cache con TTL de 30 días.
        
        NO cachea diagnósticos de error (confidence=0, source=unknown)
        para evitar perpetuar errores temporales.
        """
        try:
            # TTL: 30 días desde ahora
            ttl = int((datetime.utcnow() + timedelta(days=30)).timestamp())
            
            cache_item = {
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
            
            self.table.put_item(Item=cache_item)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cache diagnostic: {e}")
            return False

    def get_ai_diagnostic_cache(
        self,
        error_hash: str,
        profile: UserProfile
    ) -> Optional[Diagnostic]:
        """
        Recupera diagnóstico de IA desde cache.
        
        Validaciones:
        - Verifica compatibilidad de perfil (OS + package manager)
        - NO retorna diagnósticos de error (confidence=0)
        - Incrementa contador de hits
        """
        try:
            response = self.table.get_item(Key={'userId': f'CACHE#{error_hash}'})
            
            if 'Item' not in response:
                return None
            
            cache_item = response['Item']
            
            # Verificar compatibilidad de perfil
            cached_profile = cache_item.get('profile_context', {})
            if (cached_profile.get('os') != profile.os.value or
                cached_profile.get('pm') != profile.package_manager.value):
                self.logger.debug("Cache profile mismatch")
                return None
            
            # Incrementar hit counter
            self.table.update_item(
                Key={'userId': f'CACHE#{error_hash}'},
                UpdateExpression='SET hit_count = hit_count + :inc',
                ExpressionAttributeValues={':inc': 1}
            )
            
            # Deserializar y retornar
            diagnostic_data = self._deserialize_dynamodb(cache_item['diagnostic'])
            return self._dict_to_diagnostic(diagnostic_data)
            
        except Exception as e:
            self.logger.error(f"Failed to get cache: {e}")
            return None

    def delete_ai_diagnostic_cache(self, error_hash: str) -> bool:
        """
        Elimina un diagnóstico del cache.
        Útil para limpiar diagnósticos de error.
        """
        try:
            self.table.delete_item(Key={'userId': f'CACHE#{error_hash}'})
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete cache: {e}")
            return False

    def _get_default_profile(self) -> UserProfile:
        """Perfil por defecto."""
        return UserProfile(
            os="Windows",
            package_manager="pip",
            editor="VSCode"
        )

    def _diagnostic_to_dict(self, diagnostic: Diagnostic) -> dict:
        """Convierte Diagnostic a dict para DynamoDB."""
        return {
            'error_type': diagnostic.error_type,
            'voice_text': diagnostic.voice_text,
            'card_title': diagnostic.card_title,
            'card_text': diagnostic.card_text,
            'solutions': diagnostic.solutions,
            'confidence': Decimal(str(diagnostic.confidence)),  # Float → Decimal
            'source': diagnostic.source,
            # ... más campos
        }
```

---

## Flujo de Ejecucion Completo

### Ejemplo: Usuario dice "Tengo un error ModuleNotFoundError numpy"

1. **Alexa Platform** → Transcribe voz y envía request a Lambda

2. **Lambda Entry Point** → Routing a `DiagnoseIntentHandler`

3. **DiagnoseIntentHandler**:
   - Extrae `errorText = "ModuleNotFoundError numpy"`
   - Valida con `ErrorValidation.is_specific_enough()`
   - Obtiene `userId` del request

4. **StorageService** → Recupera perfil:
   ```python
   profile = UserProfile(os="Windows", package_manager="conda", editor="PyCharm")
   ```

5. **Strategy Chain** → Ejecuta estrategias en orden:

   **5a. KnowledgeBaseStrategy** (Prioridad 1):
   - Busca en KB local
   - Identifica: `ModuleNotFoundError`
   - Confidence: 0.95 (> 0.75 threshold)
   - **MATCH ENCONTRADO** → Retorna diagnóstico
   - Source: `knowledge_base`
   - Tiempo: ~50ms

   **5b. CachedAIDiagnosticStrategy** (Prioridad 2):
   - No se ejecuta (KB ya encontró match)

   **5c. LiveAIDiagnosticStrategy** (Prioridad 3):
   - No se ejecuta (KB ya encontró match)

6. **DiagnosticFactory** → Personaliza diagnóstico:
   - Aplica contexto del perfil
   - Adapta para `Windows + conda`:
     ```python
     solution = "conda install numpy"
     explanation = "Como usas conda en Windows..."
     ```

7. **ResponseFactory** → Construye respuesta:
   ```python
   response = ResponseBuilder()
       .speak("El error Module Not Found indica que numpy no está instalado. 
               Como usas conda en Windows, ejecuta: conda install numpy")
       .simple_card(
           title="ModuleNotFoundError: numpy",
           content="Paso 1: Abre Anaconda Prompt\nPaso 2: conda install numpy\n..."
       )
       .ask("¿Necesitas más ayuda con este error?")
       .build()
   ```

8. **StorageService** → Guarda diagnóstico:
   - Session attributes (para follow-ups)
   - Historial persistente en DynamoDB

9. **Interceptors** → Procesan respuesta:
   - `LoggingInterceptor`: Registra request/response
   - `SanitizationInterceptor`: Valida SSML
   - `PersistenceInterceptor`: Guarda atributos

10. **Lambda** → Retorna response a Alexa Platform

11. **Alexa** → Reproduce voz y muestra card en la app

---

### Ejemplo con AI Cache Hit

Segundo usuario pregunta el mismo error:

```
User: "Tengo un error OSError errno 24 too many open files"

1-4. [Mismos pasos iniciales]

5. Strategy Chain:

   5a. KnowledgeBaseStrategy:
   - No encuentra match (error no común)
   - Confidence: 0.3 (< 0.75 threshold)
   - No retorna diagnóstico

   5b. CachedAIDiagnosticStrategy:
   - Calcula error_hash = sha256("oserror errno 24 too many open files")
   - Busca en DynamoDB: CACHE#{error_hash}
   - **CACHE HIT** → Diagnóstico encontrado
   - Valida perfil compatible (Windows + pip)
   - Incrementa hit_count: 1 → 2
   - Source: `ai_cache`
   - Tiempo: ~30ms
   - **Ahorro: $0.001 + 2s de latencia**

   5c. LiveAIDiagnosticStrategy:
   - No se ejecuta (cache hit)

6-11. [Mismos pasos finales]
```

### Ejemplo con Live AI + Caching

Primer usuario con error raro:

```
User: "Tengo un error OSError errno 24 too many open files"

1-4. [Mismos pasos iniciales]

5. Strategy Chain:

   5a. KnowledgeBaseStrategy:
   - No encuentra match

   5b. CachedAIDiagnosticStrategy:
   - Cache miss (nadie ha preguntado esto antes)

   5c. LiveAIDiagnosticStrategy:
   - Construye prompt contextual con perfil
   - Llama a OpenAI GPT-4o
   - Recibe respuesta en ~2s
   - Parsea JSON response
   - Optimiza para voz (<300 chars)
   - **CACHEA RESULTADO** en DynamoDB:
     * Key: CACHE#{error_hash}
     * TTL: 30 días
     * Profile context: {os: Windows, pm: pip}
   - Source: `openai`
   - Costo: ~$0.001

6-11. [Mismos pasos finales]
```

### Ejemplo: Error en Diagnóstico NO se Cachea

Si la IA falla temporalmente:

```
5c. LiveAIDiagnosticStrategy:
   - Llama a OpenAI
   - Timeout / Error de API
   - Retorna error diagnostic:
     * confidence: 0.0
     * source: "unknown"
     * message: "Lo siento, tuve un problema..."

   - _cache_diagnostic():
     * Detecta confidence=0.0
     * **NO CACHEA** (evita perpetuar error)
     * Log: "Skipping cache for error diagnostic"

6. Próximo usuario:
   - CachedAIDiagnosticStrategy: Cache miss
   - LiveAIDiagnosticStrategy: Reintenta (API ya funcionando)
   - Obtiene diagnóstico válido y lo cachea
```

---

## Modelo de Datos

### UserProfile

```python
@dataclass
class UserProfile:
    user_id: str
    os: str  # Windows, macOS, Linux, WSL
    package_manager: str  # pip, conda, poetry
    editor: str  # VSCode, PyCharm, Jupyter
    timestamp: int
```

### Diagnostic

```python
@dataclass
class Diagnostic:
    error_type: str
    voice_text: str  # Optimizado para voz (max 300 chars)
    card_title: str
    card_text: str  # Detallado (max 1000 chars)
    solutions: List[str]
    common_causes: List[str]
    related_errors: List[str]
    explanation: Optional[str]
    confidence: float  # 0.0 - 1.0
    source: str  # "knowledge_base", "ai_cache", "openai", "bedrock", "unknown"
    timestamp: Optional[str]


class DiagnosticSource(Enum):
    """Fuentes posibles de diagnósticos."""
    KNOWLEDGE_BASE = "knowledge_base"
    AI_CACHE = "ai_cache"
    AI_SERVICE = "openai"
    BEDROCK = "bedrock"
    UNKNOWN = "unknown"
```

---

## Patrones de Diseño Implementados - Resumen

| Patrón                      | Ubicación                                              | Propósito                               |
| --------------------------- | ------------------------------------------------------ | --------------------------------------- |
| **Strategy**                | `DiagnosticStrategy`, `ErrorPattern`, `ValidationRule` | Algoritmos intercambiables              |
| **Chain of Responsibility** | `StrategyChain`, `ErrorValidator`                      | Procesamiento secuencial hasta éxito    |
| **Builder**                 | `AlexaResponseBuilder`                                 | Construcción fluida de respuestas       |
| **Factory Method**          | `DiagnosticFactory`, `ResponseFactory`                 | Creación de objetos complejos           |
| **Singleton**               | `StorageService`, `KnowledgeBaseService`               | Instancia única compartida              |
| **Repository**              | `StorageService`                                       | Abstracción de persistencia             |
| **Facade**                  | `ErrorValidation`, `AIService`                         | Interfaz simple para sistemas complejos |
| **Proxy**                   | `_AIServiceProxy`                                      | Control de acceso lazy                  |
| **Composite**               | `ErrorPatternMatcher`                                  | Composición de patrones                 |
| **Decorator**               | `Interceptors`                                         | Funcionalidad transversal               |
| **Value Object**            | `ValidationResult`                                     | Encapsulación inmutable                 |

---

## Decisiones Técnicas Clave

### 1. Strategy Pattern con Chain of Responsibility
**Problema**: Balance entre performance, costo y cobertura  
**Solución**: 3 estrategias en cadena (KB → Cache → IA)  
**Resultado**: 90% casos <100ms, 10% casos ~2s, costo <$10/mes para 10K usuarios

### 2. AI Cache con TTL y Validación
**Problema**: Diagnósticos de error se perpetuaban en cache  
**Solución**: No cachear si confidence=0 o source=unknown, validar al recuperar  
**Resultado**: Cache hit rate ~40%, sin errores perpetuados

### 3. Pattern-Based Validation con SOLID
**Problema**: Listas estáticas de 40+ keywords, difícil mantener  
**Solución**: 8 ErrorPattern con regex, extensible sin modificar código  
**Resultado**: Acepta "numpy not found" automáticamente, rechaza solo extremadamente vago

### 4. Lazy Initialization con Proxy
**Problema**: Importación circular entre ai_client y core.factories  
**Solución**: Proxy que inicializa ai_service solo cuando se usa  
**Resultado**: Módulo carga correctamente, sin cambios en API

### 5. DynamoDB para Perfiles + Cache
**Problema**: Necesidad de persistencia rápida y económica  
**Solución**: DynamoDB con partition key flexible (userId, CACHE#{hash})  
**Resultado**: <10ms latency, <$1/mes para 10K usuarios

---

**Última actualización**: 2025-12-03  
**Versión**: 2.0 (Strategy Pattern + AI Cache + Pattern-based Validation)
