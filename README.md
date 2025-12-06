# Doctor de Errores – Alexa Skill

> **Asistente tecnico de depuracion inteligente para Alexa** que ayuda a diagnosticar errores comunes de Python mediante respuestas interactivas, contextuales y personalizadas.

---

## Descripcion

**Doctor de Errores** es una skill personalizada para Alexa que actua como tu companhero de debugging, ayudandote a identificar y resolver errores comunes en Python y librerias populares (pandas, numpy, requests, etc.).

La skill implementa una **arquitectura de 3 capas con Strategy Pattern**:
1. **Knowledge Base local** (rápido, gratis, preciso) - 90% de casos
2. **Cache de IA en DynamoDB** (reutiliza diagnósticos previos) - TTL 30 días
3. **IA en vivo** (OpenAI/Bedrock) - Solo para casos nuevos o complejos

### Objetivo Principal

Reducir el tiempo de resolucion de errores en entornos de desarrollo Python mediante respuestas interactivas, breves y personalizadas, con una arquitectura basada en patrones de diseño que garantiza **performance**, **bajo costo** y **alta extensibilidad**.

---

## Caracteristicas

- **Interaccion natural por voz** para depurar errores comunes
- **3 estrategias de diagnóstico en cadena** (KB → AI Cache → Live AI)
- **Cache inteligente de diagnósticos** con validación (no cachea errores temporales)
- **Validación basada en patrones** con SOLID (8 ErrorPattern, extensible sin modificar código)
- **Explicaciones contextuales** segun SO, gestor de paquetes y editor
- **Cards visuales** con pasos detallados en la app de Alexa
- **Arquitectura basada en 11 patrones de diseño** (Strategy, Chain of Responsibility, Builder, Factory, Facade, etc.)
- **Persistencia en DynamoDB** (perfiles, historial, cache de IA)
- **Lazy initialization con Proxy** (evita importaciones circulares)
- **Soporte multilingüe** (actualmente español mexicano)

---

## Arquitectura

Este proyecto implementa multiples patrones de disenho para garantizar escalabilidad y mantenibilidad:

|       Patron                  |           Implementacion           |                   Proposito                  |
|-------------------------------|------------------------------------|----------------------------------------------|
| **Strategy**                  | 'diagnostic_strategies.py'         | Algoritmos intercambiables (KB/Cache/AI)     |
| **Chain of Responsibility**   | 'StrategyChain', 'ErrorValidator'  | Procesamiento secuencial hasta éxito         |
| **Builder**                   | 'response_builder.py'              | Construccion fluida de respuestas SSML/Cards |
| **Factory Method**            | 'factories.py'                     | Creación de objetos complejos                |
| **Singleton**                 | 'StorageService', 'KBService'      | Instancia única compartida                   |
| **Repository**                | 'StorageService'                   | Abstracción de persistencia                  |
| **Facade**                    | 'ErrorValidation', 'AIService'     | Interfaz simple para sistemas complejos      |
| **Proxy**                     | '_AIServiceProxy'                  | Control de acceso lazy                       |
| **Composite**                 | 'ErrorPatternMatcher'              | Composición de patrones                      |
| **Decorator**                 | 'interceptors.py'                  | Logging, persistencia, sanitización          |
| **Value Object**              | 'ValidationResult'                 | Encapsulación inmutable                      |

Para mas detalles, consulta [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Estructura del Proyecto

```
skill/
├─ lambda/
│  ├─ lambda_function.py              # Entry point y registro de handlers
│  ├─ requirements.txt
│  ├─ utils.py                        # Utilidades y logging
│  ├─ models.py                       # Modelos de datos + ErrorValidation (SOLID)
│  ├─ clean_error_cache.py            # Script para limpiar cache corrupto
│  ├─ core/
│  │  ├─ diagnostic_strategies.py     # Strategy + Chain of Responsibility
│  │  ├─ response_builder.py          # Builder pattern
│  │  ├─ factories.py                 # Factory Method pattern
│  │  ├─ interceptors.py              # Decorator pattern
│  │  ├─ prototype.py                 # Prototype pattern
│  │  └─ solution_extractors.py       # Extracción de soluciones
│  ├─ services/
│  │  ├─ kb_service.py                # Knowledge Base (Singleton)
│  │  ├─ ai_client.py                 # AI Service (Proxy + Lazy Init)
│  │  └─ storage.py                   # Repository pattern (DynamoDB)
│  ├─ intents/
│  │  ├─ base.py                      # Template pattern
│  │  ├─ diagnose_intent.py           # Handler principal con Strategy Chain
│  │  ├─ set_profile_intent.py        # Configuracion de perfil
│  │  ├─ error_description_handler.py # State Machine pattern
│  │  ├─ more_intent.py               # Mas opciones
│  │  ├─ why_intent.py                # Explicacion de causas
│  │  └─ send_card_intent.py          # Envio de cards
│  └─ config/
│     ├─ settings.py                  # Configuracion global
│     └─ kb_templates.json            # Base de conocimiento (5 templates)
├─ docs/
│  ├─ ARCHITECTURE.md                 # Documentación de arquitectura
│  └─ TESTING_GUIDE.md                # Guía de testing
├─ interactionModels/
│  └─ custom/
│     └─ es-MX.json                   # Modelo de interaccion
└─ skill.json                          # Manifest de la skill
```

---

## Inicio Rapido

### Prerequisitos

- Cuenta de desarrollador de Alexa (https://developer.amazon.com/alexa)
- Cuenta de AWS con permisos de DynamoDB
- AWS CLI configurado (opcional, para gestión de recursos)
- Python 3.8+

### Instalacion

1. **Crear la skill en Amazon Developer Console**
   - Ve a https://developer.amazon.com/alexa/console/ask
   - Crea una nueva skill personalizada con backend "Alexa-Hosted (Python)"
   - Importa el código desde este repositorio

2. **Configurar DynamoDB**
   - Crea una tabla en AWS DynamoDB llamada `DoctorErrores_Users`
   - Clave de partición: `userId` (String)
   - Configurar TTL en el atributo `ttl` (opcional, para cache)

3. **Configurar permisos IAM**
   
   Crea un usuario IAM o rol con la siguiente política para acceso a DynamoDB:
   
   ```json
   {
       "Version": "2012-10-17",
       "Statement": [
           {
               "Sid": "DoctorErroresDynamoDBAccess",
               "Effect": "Allow",
               "Action": [
                   "dynamodb:PutItem",
                   "dynamodb:GetItem",
                   "dynamodb:UpdateItem",
                   "dynamodb:Query",
                   "dynamodb:Scan",
                   "dynamodb:DescribeTable"
               ],
               "Resource": "arn:aws:dynamodb:us-east-1:575734508443:table/DoctorErrores_Users"
           }
       ]
   }
   ```
   
   **Nota**: Reemplaza el ARN con el de tu tabla DynamoDB.

4. **Configurar variables de entorno**
   
   En el IDE de Amazon Developer Console (pestaña "Code" de Alexa-Hosted):
   - Crea un archivo `.env` en la raíz del proyecto Lambda
   - Configura las siguientes variables (ver sección de Configuración más abajo):
     - `AWS_REGION`: `us-east-1`
     - `DYNAMODB_TABLE_NAME`: `DoctorErrores_Users`
     - `OPENAI_API_KEY`: Tu clave de OpenAI (requerido para diagnósticos con IA)
     - `OPENAI_MODEL`: `gpt-4o-mini` (opcional)

5. **Configurar el modelo de interacción**
   - En la consola de Alexa Developer, ve a "Build" > "Interaction Model"
   - Importa el contenido de `interactionModels/custom/es-MX.json`
   - Guarda y construye el modelo

6. **Desplegar y probar**
   - Despliega la skill desde la consola
   - Usa el simulador de Alexa para probar: "Alexa, abre Doctor de Errores"

### Uso

1. Abre la skill: *"Alexa, abre Doctor de Errores"*
2. Diagnostica un error: *"Tengo un error ModuleNotFoundError"*
3. Configura tu perfil: *"Uso Windows y conda"*
4. Pide mas detalles: *"Dame otra opcion"*
5. Explora causas: *"Por que pasa esto?"*
6. Recibe los pasos en tu app: *"Envialo a mi telefono"*

**Nota sobre acentos**: Alexa puede ser sensible a los acentos en algunas frases. Si una frase con acento no es reconocida (ej: "explícame más"), intenta la versión sin acento ("explicame mas").

---

## Flujo de Conversación

### Flujo Básico (Una Paso)
```
Usuario: "Alexa, abre doctor de errores"
Alexa:   "Bienvenido al Doctor de Errores..."

Usuario: "diagnostica module not found"
Alexa:   [Diagnóstico completo con soluciones]
```

### Flujo Conversacional (Dos Pasos)
```
Usuario: "tengo un problema con mi código"
Alexa:   "¿Qué error estás viendo?"

Usuario: "syntax error"
Alexa:   [Diagnóstico completo]
```

**Implementación**: Usa un `ErrorDescriptionHandler` que intercepta respuestas cuando `awaiting_error_description=True` en session attributes, implementando un **State Machine Pattern** para gestionar el diálogo.

### Flujo con Follow-ups
```
Usuario: "diagnostica syntax error"
Alexa:   [Primera solución]

Usuario: "explícame más"
Alexa:   [Explicación técnica detallada]

Usuario: "dame más soluciones"
Alexa:   [Segunda solución]
```

---

## Intents Disponibles

|       Intent       |     Utterances de Ejemplo    |         Proposito        |
|--------------------|------------------------------|--------------------------|
| 'DiagnoseIntent'   | "tengo un error {errorText}" | Diagnostico principal    |
| 'SetProfileIntent' | "uso Windows y conda"        | Configurar entorno       |
| 'MoreIntent'       | "dame otra opcion"           | Mostrar mas soluciones   |
| 'WhyIntent'        | "por que pasa esto?"         | Explicar causas          |
| 'SendCardIntent'   | "envialo a mi telefono"      | Enviar card detallada    |
| 'RepeatIntent'     | "repite"                     | Repetir ultima respuesta |

---

## Base de Conocimiento

La skill incluye diagnosticos predefinidos para errores comunes:

- **ImportError / ModuleNotFoundError**
- **AttributeError**
- **KeyError / IndexError**
- **TypeError / ValueError**
- **SyntaxError**
- **IndentationError**
- Errores especificos de pandas, numpy, requests, scikit-learn

---

## Arquitectura de Diagnóstico - Strategy Pattern

La skill implementa una **cadena de estrategias** que se ejecutan en orden de prioridad:

### 1. KnowledgeBaseStrategy (Prioridad 1)
- **Performance**: <100ms
- **Costo**: $0 (gratis)
- **Hit Rate**: ~60%
- **Uso**: Errores comunes predefinidos

### 2. CachedAIDiagnosticStrategy (Prioridad 2)
- **Performance**: <50ms
- **Costo**: $0 (gratis)
- **Hit Rate**: ~30% (de los que fallan KB)
- **Uso**: Reutiliza diagnósticos de IA previos
- **Validaciones**:
  - Solo cachea diagnósticos válidos (confidence > 0)
  - Verifica compatibilidad de perfil (OS + package manager)
  - TTL de 30 días
  - NO cachea errores temporales (evita perpetuar problemas)

### 3. LiveAIDiagnosticStrategy (Prioridad 3)
- **Performance**: ~2s
- **Costo**: ~$0.001 por request
- **Hit Rate**: ~10% (casos nuevos/complejos)
- **Providers**:
  1. **OpenAI GPT-4o-mini** (primario)
  2. **Amazon Bedrock** (alternativo - Claude, Llama)
  3. **MockAIClient** (fallback para testing)

Las respuestas de IA son:
- Optimizadas para voz (<300 caracteres)
- Filtradas para remover información sensible
- Cacheadas automáticamente para futuros usuarios
- Validadas antes de cachear (evita perpetuar errores)

---

## Configuracion

### Variables de Entorno

Configura las siguientes variables de entorno en archivo .env dentro del IDE de Developers Amazon:

```env
# AWS
AWS_REGION=us-east-1
DYNAMODB_TABLE_NAME=DoctorErrores_Users

# AI Services
OPENAI_API_KEY=sk-...                    # Requerido para IA en vivo
OPENAI_MODEL=gpt-4o-mini                 # Modelo de OpenAI (opcional)
BEDROCK_MODEL_ID=anthropic.claude-v2     # Opcional (alternativo a OpenAI)

# Knowledge Base
KB_CONFIDENCE_THRESHOLD=0.75             # Umbral para aceptar match de KB

# Response Setting
MAX_VOICE_LENGTH=300                     # Máximo caracteres para voz
MAX_CARD_LENGTH=1000                     # Máximo caracteres para card

# Storage (Opcional)
ENABLE_STORAGE=true                      # Habilitar DynamoDB
```

### Permisos IAM Requeridos

La función Lambda debe tener permisos para acceder a DynamoDB. Adjunta la siguiente política IAM al rol de ejecución de Lambda:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "DoctorErroresDynamoDBAccess",
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem",
                "dynamodb:Query",
                "dynamodb:Scan",
                "dynamodb:DescribeTable"
            ],
            "Resource": "arn:aws:dynamodb:us-east-1:575734508443:table/DoctorErrores_Users"
        }
    ]
}
```

**Nota**: Reemplaza el ARN con el de tu tabla DynamoDB específica.

---

## Testing

Consulta [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md) para:
- Procedimientos de testing completos
- Casos de prueba para cada componente
- Verificación de DynamoDB
- Testing de Strategy Pattern
- Validación de cache
- Troubleshooting de problemas comunes

---

## Documentación

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Arquitectura detallada del sistema
- **[TESTING_GUIDE.md](docs/TESTING_GUIDE.md)** - Guía completa de testing
- **[kb_templates.json](lambda/config/kb_templates.json)** - Base de conocimiento

### Diagramas C4

- **[C1 - Context Diagram](diagrams/c1-context.puml)** - Sistema en contexto (Desarrollador, Alexa, Servicios externos)
- **[C2 - Container Diagram](diagrams/c2-container.puml)** - Contenedores (Interaction Model, Backend Lambda, DynamoDB, etc.)
- **[C3 - Component Diagram](diagrams/c3-component.puml)** - Componentes internos (Strategies, Services, Handlers, Patterns)

**Visualizar**: http://www.plantuml.com/plantuml/uml/

---

## Autores

- **Luis Miguel Fontes** - [@lmfontes19](https://github.com/lmfontes19)

---

**Versión**: 2.0  
**Última actualización**: 2025-12-03  
**Python**: 3.8+ (AWS Lambda)  
**Patterns**: 11 patrones de diseño implementados
