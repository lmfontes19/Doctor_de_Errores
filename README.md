# Doctor de Errores – Alexa Skill

> **Asistente tecnico de depuracion inteligente para Alexa** que ayuda a diagnosticar errores comunes de Python mediante respuestas interactivas, contextuales y personalizadas.

---

## Descripcion

**Doctor de Errores** es una skill personalizada para Alexa que actua como tu companhero de debugging, ayudandote a identificar y resolver errores comunes en Python y librerias populares (pandas, numpy, requests, scikit-learn, etc.).

La skill analiza el mensaje de error que dictas, identifica posibles causas, propone soluciones paso a paso y puede consultar una IA de respaldo (Amazon Bedrock o OpenAI) cuando no encuentra una respuesta en su base de conocimiento local.

### Objetivo Principal

Reducir el tiempo de resolucion de errores en entornos de desarrollo Python mediante respuestas interactivas, breves y personalizadas, aprovechando patrones de disenho para lograr una arquitectura limpia, extensible y mantenible.

---

## Caracteristicas

- **Interaccion natural por voz** para depurar errores comunes
- **Explicaciones contextuales** segun SO, gestor de paquetes y editor
- **Fallback inteligente con IA** (Bedrock/OpenAI) cuando no hay match en KB
- **Cards visuales** con pasos detallados en la app de Alexa
- **Arquitectura basada en patrones de disenho** (Builder, Prototype, Factory, Decorator)
- **Soporte multilingüe** (actualmente espanhol mexicano)
- **Persistencia de perfil** (SO, gestor, editor preferidos)

---

## Arquitectura

Este proyecto implementa multiples patrones de disenho para garantizar escalabilidad y mantenibilidad:

|       Patron      |           Implementacion           |                   Proposito                  |
|-------------------|------------------------------------|----------------------------------------------|
| **Builder**       | 'response_builder.py'              | Construccion fluida de respuestas SSML/Cards |
| **Prototype**     | 'prototype.py'                     | Clonacion de plantillas de diagnostico       |
| **Factory**       | 'factories.py'                     | Estrategias segun tipo de error y entorno    |
| **Decorator**     | 'interceptors.py'                  | Logging, cache, sanitizacion                 |
| **Strategy**      | 'solution_extractors.py'           | Extraccion de soluciones de KB               |
| **State Machine** | 'error_description_handler.py'     | Gestion de dialogo en multiples pasos        |
| **Template**      | 'intents/base.py'                  | Estructura comun para handlers               |

Para mas detalles, consulta [docs/arquitectura.md](docs/arquitectura.md).

---

## Estructura del Proyecto

```
skill/
├─ lambda/
│  ├─ lambda_function.py          # Entry point y registro de handlers
│  ├─ requirements.txt
│  ├─ utils.py
│  ├─ core/
│  │  ├─ response_builder.py      # Builder pattern
│  │  ├─ prototype.py             # Prototype pattern
│  │  ├─ factories.py             # Factory / Abstract Factory
│  │  └─ interceptors.py          # Decorator pattern
│  ├─ services/
│  │  ├─ kb_service.py            # Servicio de conocimiento
│  │  ├─ ai_client.py             # Cliente IA con decoradores
│  │  └─ storage.py               # Persistencia (DynamoDB/S3)
│  ├─ intents/
│  │  ├─ base.py
│  │  ├─ diagnose_intent.py       # Handler principal
│  │  ├─ set_profile_intent.py    # Configuracion de perfil
│  │  ├─ more_intent.py           # Mas opciones
│  │  ├─ why_intent.py            # Explicacion de causas
│  │  └─ send_card_intent.py      # Envio de cards
│  └─ config/
│     ├─ settings.py              # Configuracion global
│     └─ kb_templates.json        # Base de conocimiento
├─ interactionModels/
│  └─ custom/
│     └─ es-MX.json               # Modelo de interaccion
└─ skill.json                      # Manifest de la skill
```

---

## Inicio Rapido

### Prerequisitos

- Python 3.9+
- AWS CLI configurado
- ASK CLI (Alexa Skills Kit CLI)
- Cuenta de desarrollador de Alexa

### Instalacion

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/lmfontes19/Doctor_de_Errores.git
   cd Doctor_de_Errores/skill
   ```

2. **Instalar dependencias**
   ```bash
   cd lambda
   pip install -r requirements.txt
   ```

3. **Configurar variables de entorno**
   ```bash
   cp .env.example .env
   # Editar .env con tus credenciales
   ```

4. **Desplegar la skill**
   ```bash
   ask deploy
   ```

### Uso

1. Abre la skill: *"Alexa, abre Doctor de Errores"*
2. Diagnostica un error: *"Tengo un error ModuleNotFoundError"*
3. Configura tu perfil: *"Uso Windows y conda"*
4. Pide mas detalles: *"Dame otra opcion"*
5. Explora causas: *"Por que pasa esto?"*
6. Recibe los pasos en tu app: *"Envialo a mi telefono"*

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

## Integracion con IA

Cuando la base de conocimiento local no tiene una respuesta adecuada, la skill activa un fallback inteligente:

1. **Amazon Bedrock** (Claude, Llama, etc.)
2. **OpenAI GPT-4o-mini**

Las respuestas de IA son:
- Optimizadas para voz (breves y claras)
- Filtradas para remover informacion sensible
- Cacheadas para mejorar rendimiento

---

## Configuracion

### Variables de Entorno

Crea un archivo `.env` basado en `.env.example`:

```env
# AWS
AWS_REGION=us-east-1
DYNAMODB_TABLE_NAME=doctor-errores-profiles

# AI Services (opcional)
BEDROCK_MODEL_ID=anthropic.claude-v2
OPENAI_API_KEY=sk-...

# Settings
ENABLE_AI_FALLBACK=true
MAX_RESPONSE_LENGTH=300
CACHE_TTL_SECONDS=3600
```

---

## Decisiones de Disenho

Consulta [docs/decisiones.md](docs/decisiones.md) para entender las decisiones arquitectonicas clave:

- Por que patrones de disenho?
- Por que una base de conocimiento local + IA?
- Como se estructura el sistema de respuestas?
- Que trade-offs se consideraron?

---

## Autores

- **Luis Miguel Fontes** - [@lmfontes19](https://github.com/lmfontes19)

---
