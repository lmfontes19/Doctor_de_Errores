# Flujo de Testing - Doctor de Errores Skill

## Testing Básico (Handlers Principales)

### 1. LaunchRequest - Inicio de la Skill

#### Test 1a: Usuario Nuevo (Sin Perfil Configurado)
```
Usuario: "Alexa, abre doctor de errores"

Respuesta Esperada:
- "Bienvenido al Doctor de Errores. Soy tu asistente para diagnosticar errores de Python."
- "Antes de comenzar, puedes configurar tu perfil diciendo, por ejemplo: uso Windows y pip."
- "O puedes ir directamente a describir el error que estas teniendo."
- Pregunta: "¿Que sistema operativo y gestor de paquetes usas, o que error tienes?"
- Sesión queda abierta (shouldEndSession: false)
```

#### Test 1b: Usuario con Perfil Configurado
```
Usuario: "Alexa, abre doctor de errores"

Respuesta Esperada:
- "Bienvenido al Doctor de Errores. Soy tu asistente para diagnosticar errores de Python."
- "¿Que error estas teniendo?" (SIN mensaje de configuración de perfil)
- Sesión queda abierta
- Va directo al punto sin sugerir configurar perfil

Nota: El perfil se carga automáticamente desde DynamoDB al inicio de la sesión
```

### 2. HelpIntent - Solicitar Ayuda
```
Usuario: "Alexa, ayuda"
Usuario: "¿qué puedes hacer?"
Usuario: "qué sabes hacer"
Usuario: "cómo funciona esto"
Usuario: "necesito ayuda"

Respuesta Esperada:
- Explicación de comandos disponibles
- Ejemplos de uso
- Sesión queda abierta
```

### 3. DiagnoseIntent - Diagnosticar Errores

#### Test 3a: Error de Módulo
```
Usuario: "diagnostica mi error module not found"

Respuesta Esperada:
- Detecta error tipo "module"
- Proporciona 3-5 soluciones
- Menciona: pip install, entorno virtual, ortografía
- Pregunta si necesita más ayuda
- Diagnóstico se guarda en historial de DynamoDB
```

#### Test 3b: Error con Nombre de Paquete
```
Usuario: "tengo un error numpy not found"

Respuesta Esperada:
- Reconoce 'numpy' como palabras clave específicas
- Procede directamente con el diagnóstico
- Busca en Knowledge Base o usa AI según corresponda
```

#### Test 3c: Error de Sintaxis
```
Usuario: "tengo un error syntax error invalid syntax"

Respuesta Esperada:
- Detecta error de sintaxis
- Menciona: paréntesis, dos puntos, indentación
- Ofrece explicación adicional
```

#### Test 3d: Error de Nombre
```
Usuario: "tengo un error name not defined"

Respuesta Esperada:
- Detecta error de nombre no definido
- Menciona: declarar variable antes de usar, errores de escritura, scope
- Pregunta si necesita más ayuda
```

#### Test 3e: Error de Archivo
```
Usuario: "tengo un error file not found"

Respuesta Esperada:
- Detecta error de archivo
- Menciona: verificar ruta, confirmar existencia, rutas absolutas
```

#### Test 3f: Error de Permisos
```
Usuario: "tengo un permission denied"

Respuesta Esperada:
- Detecta error de permisos
- Menciona: sudo (Linux/Mac), ejecutar como admin (Windows), chmod
```

#### Test 3g: Error Genérico (Sin Especificar)
```
Usuario: "tengo un problema con mi código"
Usuario: "mi código no funciona"
Usuario: "hay un error en mi código"
Usuario: "necesito ayuda con mi código"
Usuario: "tengo un bug"

Respuesta Esperada:
- Alexa: "Claro, puedo ayudarte con tu código. ¿Qué error estás viendo?"
- Pide descripción específica del error
- Sugiere ejemplos: module not found, syntax error, etc.
- Sesión queda abierta esperando la descripción del error

Follow-up esperado:
Usuario: "module not found"
Alexa: [Diagnóstico completo]
```

### 4. WhyIntent - Explicar Causas

#### Test 4a: Con Diagnóstico Previo
```
Setup:
Usuario: "diagnostica module not found"
Alexa: [Da diagnóstico]

Test:
Usuario: "¿por qué pasa esto?"
Usuario: "explícame la causa"
Usuario: "explícame más"
Usuario: "dame más detalles"
Usuario: "detalla más"
Usuario: "explícame por qué"

Respuesta Esperada:
- Explicación técnica del error diagnosticado
- Causas comunes del error
- Card con información detallada
- Pregunta: "¿Quieres escuchar más soluciones o prefieres que te envíe todo?"
```

#### Test 4b: Sin Diagnóstico Previo
```
Usuario: "explícame por qué ocurre"  (sin diagnóstico previo)

Respuesta Esperada:
- "Primero necesito diagnosticar un error para explicarte por qué ocurre."
- "¿Qué error estás teniendo?"
- Ejemplos: syntax error, module not found
- Sesión queda abierta esperando descripción del error
```

### 5. MoreIntent - Más Soluciones

#### Test 5a: Con Diagnóstico Previo
```
Setup:
Usuario: "diagnostica syntax error"
Alexa: [Da primera solución]

Test:
Usuario: "dame más soluciones"
Usuario: "siguiente"
Usuario: "más opciones"
Usuario: "qué más puedo hacer"
Usuario: "continúa"
Usuario: "dame otra"

Respuesta Esperada:
- Siguiente solución del diagnóstico
- "Solución 2 de X: [solución]"
- Card con la solución completa
- Si hay más: "¿Quieres otra solución?"
- Si no hay más: "Esas eran todas las soluciones. ¿Quieres saber por qué ocurre?"
```

#### Test 5b: Sin Diagnóstico Previo
```
Usuario: "dame más soluciones"  (sin diagnóstico previo)

Respuesta Esperada:
- "Primero necesito diagnosticar un error para darte soluciones."
- "¿Qué error estás teniendo?"
- Ejemplos de errores comunes
- Sesión queda abierta esperando descripción
```

#### Test 5c: Todas las Soluciones Agotadas
```
Setup:
Usuario: "diagnostica module not found"
Usuario: "dame más" (repite hasta agotar todas)

Test:
Usuario: "dame más"  (cuando ya no hay más)

Respuesta Esperada:
- "Ya te mostré todas las soluciones disponibles."
- "¿Quieres saber por qué ocurre este error?"
- Resetea índice para permitir reiniciar
```

### 6. Stop/Cancel - Terminar Sesión
```
Usuario: "cancela"
Usuario: "detente"
Usuario: "adiós"

Respuesta Esperada:
- Mensaje de despedida
- Sesión termina (shouldEndSession: true)
```

### 7. FallbackIntent - Entrada No Reconocida
```
Usuario: "haz algo random"
Usuario: "banana"

Respuesta Esperada:
- Mensaje de "no entendí"
- Lista de comandos disponibles
- Sesión queda abierta
```

---

## Flujos de Conversación Completos

### Flujo 1: Usuario Nuevo - Primera Vez
```
1. "Alexa, abre doctor de errores"
   → Bienvenida CON sugerencia de configurar perfil
   → "Antes de comenzar, puedes configurar tu perfil..."

2. "uso Windows y pip"
   → Confirmación: "Perfecto. He configurado tu perfil para windows con pip."
   → Perfil guardado en DynamoDB

3. "diagnostica module not found"
   → Diagnóstico con soluciones adaptadas a Windows/pip

4. "adiós"
   → Despedida

[Segunda sesión - mismo usuario]
5. "Alexa, abre doctor de errores"
   → Bienvenida SIN sugerencia de perfil
   → "¿Qué error estas teniendo?" (directo al punto)
   → Perfil cargado automáticamente desde DynamoDB
```

### Flujo 2: Usuario Existente - Diagnóstico Simple
```
1. "Alexa, abre doctor de errores"
   → Bienvenida sin mensaje de perfil (ya configurado)

2. "diagnostica mi error module not found"
   → Diagnóstico con soluciones
   → Guardado en historial de DynamoDB

3. "adiós"
   → Despedida
```

### Flujo 3: Diagnóstico con Follow-up (Conversación en Dos Pasos)
```
1. "Alexa, abre doctor de errores"
   → Bienvenida: "Bienvenido al Doctor de Errores..."

2. "tengo un problema con mi código"
   → Alexa pregunta: "Claro, puedo ayudarte con tu código. ¿Qué error estás viendo?"
   → Estado: awaiting_error_description = True

3. "tengo un error syntax error"
   → Diagnóstico completo de sintaxis con soluciones
   → Card con detalles del error
   → Diagnóstico guardado en DynamoDB

4. "explícame más"
   → Explicación técnica detallada de por qué ocurre

5. "dame más soluciones"
   → Segunda solución

6. "dame otra"
   → Tercera solución

7. "gracias, adiós"
   → Despedida
   → Perfil actualizado en DynamoDB si hubo cambios
```

### Flujo 4: Múltiples Errores con Cache AI
```
1. "Alexa, abre doctor de errores"
   → Bienvenida

2. "diagnostica un error muy específico y raro de importación de pandas"
   → KB no encuentra match (confianza < 0.70)
   → Cache vacío para este error
   → Llama a OpenAI API ($$$ costo)
   → Respuesta: "Según mi análisis..."
   → Guarda en cache DynamoDB con TTL de 30 días

3. Cierra sesión

4. "Alexa, abre doctor de errores"
   → Bienvenida (perfil cargado automáticamente)

5. "diagnostica un error muy específico y raro de importación de pandas"
   → KB no encuentra match
   → CACHE HIT en DynamoDB
   → Devuelve diagnóstico cacheado (gratis, rápido)
   → Incrementa hit_count en cache
   → NO llama a OpenAI

6. "cancela"
   → Despedida

Verificación en DynamoDB:
- Item con userId="CACHE#{hash_sha256}"
- Atributo diagnostic con el diagnóstico completo
- Atributo profile_context: {os: "windows", pm: "pip"}
- Atributo ttl: [timestamp + 30 días]
- Atributo hit_count: 1 (incrementado)
```

### Flujo 5: Usuario Pide Follow-up Sin Contexto
```
1. "Alexa, abre doctor de errores"
   → Bienvenida

2. "dame más soluciones"  (sin diagnóstico previo)
   → "Primero necesito diagnosticar un error. ¿Qué error tienes?"

3. "diagnostica module not found"
   → Diagnóstico correcto con soluciones

4. "dame más"
   → Segunda solución

5. "explícame por qué"
   → Explicación técnica

6. "adiós"
   → Despedida
```

### Flujo 6: Usuario Confundido
```
1. "Alexa, abre doctor de errores"
   → Bienvenida

2. "no sé qué hacer"
   → Fallback: "Lo siento, no entendí..."

3. "ayuda"
   → Explicación de comandos disponibles

4. "tengo un problema con mi código"
   → "Claro, ¿qué error estás viendo?"

5. "diagnsotica un module not found"
   → Diagnóstico correcto

6. "adiós"
   → Despedida
```

### Flujo 6: Usuario Confundido
```
1. "Alexa, abre doctor de errores"
   → Bienvenida

2. "no sé qué hacer"
   → Fallback: "Lo siento, no entendí..."

3. "ayuda"
   → Explicación de comandos disponibles

4. "tengo un problema con mi código"
   → "Claro, ¿qué error estás viendo?"

5. "tengo un error module not found"
   → Diagnóstico correcto

6. "adiós"
   → Despedida
```

---

### SendCardIntent - Enviar Tarjeta
```
Usuario: "envíalo a mi teléfono"
Usuario: "mándame el resumen"

Respuesta Esperada:
- Confirmación de tarjeta enviada
- Mensaje indicando que puede ver detalles en app Alexa
```

## Testing Avanzado - Servicios Externos

### Con Knowledge Base
```
1. "diagnostica ImportError"
   → Debe buscar en KB y devolver resultado con alta confianza
   → Verificar: source = "knowledge_base"

2. "diagnostica ModuleNotFoundError"
   → Debe encontrar match exacto en KB
   → Verificar: confidence >= 0.90
```

### Con AI Service (OpenAI)
```
1. "diagnostica un error muy específico y raro de asyncio event loop already running"
   → Si KB no encuentra (confianza < 0.70), debe llamar a AI
   → Respuesta debe indicar "según mi análisis..."
   → Verificar en CloudWatch: "Calling OpenAI API"
   → Verificar cache creado en DynamoDB

2. [Repetir mismo error]
   → Debe usar cache, NO llamar a OpenAI
   → Verificar en CloudWatch: "Cache HIT"
```

### Con Storage Service (DynamoDB)
```
1. Configura perfil: "uso Windows y pip"
   → Verificar guardado en DynamoDB

2. Diagnostica 3-4 errores diferentes
   → Verificar que se guarda en diagnosticHistory
   → Verificar límite de 50 items

3. Cierra y reabre skill
   → Verificar que perfil se carga automáticamente
   → Verificar que NO muestra mensaje de configuración

4. Consulta mismo error que ya diagnosticó con AI
   → Verificar que usa cache
   → Verificar que hit_count se incrementa
```

---
