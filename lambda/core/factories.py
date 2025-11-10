"""
Factories para crear instancias de modelos y objetos complejos.

Este modulo implementa el patron Factory para centralizar la creacion
de objetos complejos como Diagnosticos, UserProfiles, y responses de Alexa.

Patterns:
- Factory Method: Creacion de objetos con logica compleja
- Builder: Construccion paso a paso de objetos
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from models import (
    Diagnostic,
    UserProfile,
    ErrorType,
    DiagnosticSource,
    OperatingSystem,
    PackageManager,
    Editor
)


class DiagnosticFactory:
    """
    Factory para crear instancias de Diagnostic.

    Proporciona metodos estaticos para crear diagnosticos desde
    diferentes fuentes (Knowledge Base, AI, error directo).
    """

    @staticmethod
    def from_kb_result(
        kb_result: Dict[str, Any],
        user_profile: UserProfile
    ) -> Diagnostic:
        """
        Crea un Diagnostic desde resultado de Knowledge Base.

        Args:
            kb_result: Resultado del KB con error_type, solutions, etc.
            user_profile: Perfil del usuario para personalizacion

        Returns:
            Diagnostic completo

        Example:
            >>> kb_result = {
            ...     'error_type': 'py_module_not_found',
            ...     'solutions': ['pip install pandas'],
            ...     'confidence': 0.95
            ... }
            >>> diagnostic = DiagnosticFactory.from_kb_result(kb_result, profile)
        """
        error_type = kb_result.get('error_type', 'unknown')
        solutions = kb_result.get('solutions', [])

        # Personalizar soluciones segun perfil
        personalized_solutions = DiagnosticFactory._personalize_solutions(
            solutions, user_profile
        )

        # Construir texto de voz
        voice_text = DiagnosticFactory._build_voice_text(
            error_type,
            personalized_solutions
        )

        # Construir titulo y texto de card
        card_title = DiagnosticFactory._build_card_title(error_type)
        card_text = DiagnosticFactory._build_card_text(
            error_type,
            personalized_solutions,
            kb_result.get('explanation', '')
        )

        return Diagnostic(
            error_type=error_type,
            voice_text=voice_text,
            card_title=card_title,
            card_text=card_text,
            solutions=personalized_solutions,
            explanation=kb_result.get('explanation'),
            confidence=kb_result.get('confidence', 0.0),
            source=DiagnosticSource.KNOWLEDGE_BASE.value,
            common_causes=kb_result.get('common_causes', []),
            related_errors=kb_result.get('related_errors', [])
        )

    @staticmethod
    def from_ai_result(
        ai_result: Dict[str, Any],
        user_profile: UserProfile
    ) -> Diagnostic:
        """
        Crea un Diagnostic desde resultado de AI.

        Args:
            ai_result: Resultado del AI con diagnostico generado
            user_profile: Perfil del usuario

        Returns:
            Diagnostic completo
        """
        error_type = ai_result.get('error_type', 'unknown')
        solutions = ai_result.get('solutions', [])

        # AI ya personaliza, pero validamos formato
        personalized_solutions = DiagnosticFactory._personalize_solutions(
            solutions, user_profile
        )

        voice_text = ai_result.get('voice_text', '')
        if not voice_text:
            voice_text = DiagnosticFactory._build_voice_text(
                error_type, personalized_solutions
            )

        card_title = ai_result.get('card_title', '')
        if not card_title:
            card_title = DiagnosticFactory._build_card_title(error_type)

        card_text = ai_result.get('card_text', '')
        if not card_text:
            card_text = DiagnosticFactory._build_card_text(
                error_type,
                personalized_solutions,
                ai_result.get('explanation', '')
            )

        return Diagnostic(
            error_type=error_type,
            voice_text=voice_text,
            card_title=card_title,
            card_text=card_text,
            solutions=personalized_solutions,
            explanation=ai_result.get('explanation'),
            confidence=ai_result.get('confidence', 0.8),
            source=DiagnosticSource.AI_SERVICE.value,
            common_causes=ai_result.get('common_causes', []),
            related_errors=ai_result.get('related_errors', [])
        )

    @staticmethod
    def create_error_diagnostic(
        error_message: str,
        error_type: str = "unknown"
    ) -> Diagnostic:
        """
        Crea un diagnostic basico para errores internos.

        Args:
            error_message: Mensaje de error
            error_type: Tipo de error

        Returns:
            Diagnostic con informacion minima
        """
        return Diagnostic(
            error_type=error_type,
            voice_text=(
                "Lo siento, tuve un problema al procesar tu solicitud. "
                "Por favor intenta de nuevo."
            ),
            card_title="Error",
            card_text=f"Error: {error_message}",
            solutions=[
                "Intenta describir el error de otra manera",
                "Verifica tu conexion a internet",
                "Intenta mas tarde"
            ],
            confidence=0.0,
            source=DiagnosticSource.UNKNOWN.value
        )

    @staticmethod
    def _personalize_solutions(
        solutions: List[str],
        user_profile: UserProfile
    ) -> List[str]:
        """
        Personaliza soluciones segun el perfil del usuario.

        Reemplaza placeholders como {pm}, {os}, {editor} con valores
        del perfil del usuario.

        Args:
            solutions: Lista de soluciones con placeholders
            user_profile: Perfil del usuario

        Returns:
            Lista de soluciones personalizadas
        """
        personalized = []

        for solution in solutions:
            # Reemplazar placeholders
            personalized_solution = solution.replace(
                '{pm}', user_profile.package_manager.value
            ).replace(
                '{os}', user_profile.os.value
            ).replace(
                '{editor}', user_profile.editor.value
            )
            personalized.append(personalized_solution)

        return personalized

    @staticmethod
    def _build_voice_text(error_type: str, solutions: List[str]) -> str:
        """
        Construye el texto de voz simplificado.

        Args:
            error_type: Tipo de error
            solutions: Lista de soluciones

        Returns:
            Texto para voz (max 300 chars)
        """
        if not solutions:
            return f"Detecte un error de tipo {error_type}. No tengo soluciones especificas disponibles."

        # Primera solucion simplificada
        first_solution = solutions[0]
        if len(first_solution) > 150:
            first_solution = first_solution[:147] + "..."

        num_more = len(solutions) - 1
        if num_more > 0:
            return (
                f"Detecte un {error_type}. "
                f"Solucion: {first_solution} "
                f"Tengo {num_more} soluciones mas disponibles."
            )
        else:
            return f"Detecte un {error_type}. Solucion: {first_solution}"

    @staticmethod
    def _build_card_title(error_type: str) -> str:
        """Construye el titulo de la card."""
        return f"Diagnostico: {error_type}"

    @staticmethod
    def _build_card_text(
        error_type: str,
        solutions: List[str],
        explanation: str
    ) -> str:
        """
        Construye el texto completo de la card.

        Args:
            error_type: Tipo de error
            solutions: Lista de soluciones
            explanation: Explicacion tecnica

        Returns:
            Texto formateado para card
        """
        lines = [
            f"**Error**: {error_type}",
            ""
        ]

        if solutions:
            lines.append("**Soluciones**:")
            for i, sol in enumerate(solutions, 1):
                lines.append(f"{i}. {sol}")
            lines.append("")

        if explanation:
            lines.append("**Explicacion**:")
            lines.append(explanation)
            lines.append("")

        lines.extend([
            "**Mas ayuda**:",
            "- Di 'por que pasa esto' para entender la causa",
            "- Di 'dame mas opciones' para ver otras soluciones",
            "- Di 'envialo a mi telefono' para guardar esta informacion"
        ])

        return "\n".join(lines)


class UserProfileFactory:
    """
    Factory para crear instancias de UserProfile.

    Proporciona metodos para crear perfiles desde slots de Alexa,
    datos de DynamoDB, o valores por defecto.
    """

    @staticmethod
    def from_slots(
        so_slot: Optional[str] = None,
        pm_slot: Optional[str] = None,
        editor_slot: Optional[str] = None
    ) -> UserProfile:
        """
        Crea UserProfile desde slots de Alexa.

        Args:
            so_slot: Slot de sistema operativo
            pm_slot: Slot de package manager
            editor_slot: Slot de editor

        Returns:
            UserProfile con valores normalizados

        Example:
            >>> profile = UserProfileFactory.from_slots(
            ...     so_slot="mac",
            ...     pm_slot="conda",
            ...     editor_slot="pycharm"
            ... )
            >>> profile.os
            <OperatingSystem.MACOS: 'macos'>
        """
        # Crear perfil base
        profile = UserProfile()

        # Actualizar con slots proporcionados
        kwargs = {}
        if so_slot:
            kwargs['os'] = so_slot
        if pm_slot:
            kwargs['pm'] = pm_slot
        if editor_slot:
            kwargs['editor'] = editor_slot

        if kwargs:
            profile = profile.update(**kwargs)

        return profile

    @staticmethod
    def from_dynamodb(data: Dict[str, Any]) -> UserProfile:
        """
        Crea UserProfile desde datos de DynamoDB.

        Args:
            data: Diccionario con datos de DynamoDB

        Returns:
            UserProfile
        """
        return UserProfile.from_dict(data)

    @staticmethod
    def get_default() -> UserProfile:
        """
        Retorna perfil por defecto.

        Returns:
            UserProfile con valores default (linux, pip, vscode)
        """
        return UserProfile()

    @staticmethod
    def merge(
        current: UserProfile,
        updates: Dict[str, Any]
    ) -> UserProfile:
        """
        Hace merge de perfil actual con actualizaciones.

        Args:
            current: Perfil actual
            updates: Diccionario con campos a actualizar

        Returns:
            Nuevo UserProfile con cambios aplicados

        Example:
            >>> current = UserProfile()
            >>> updated = UserProfileFactory.merge(
            ...     current,
            ...     {'os': 'windows', 'pm': 'poetry'}
            ... )
        """
        return current.update(**updates)


class ResponseFactory:
    """
    Factory para crear respuestas de Alexa estandarizadas.

    Proporciona metodos para crear respuestas comunes como
    errores, confirmaciones, ayuda, etc.
    """

    @staticmethod
    def create_error_response(
        handler_input,
        error_message: str,
        should_end_session: bool = False
    ):
        """
        Crea respuesta de error estandarizada.

        Args:
            handler_input: HandlerInput de Alexa
            error_message: Mensaje de error para el usuario
            should_end_session: Si debe terminar la sesion

        Returns:
            Response de Alexa
        """
        builder = handler_input.response_builder

        speak_output = (
            f"Lo siento, {error_message}. "
            "¿Puedes intentar de nuevo?"
        )

        if should_end_session:
            return builder.speak(speak_output).response
        else:
            return builder.speak(speak_output).ask(speak_output).response

    @staticmethod
    def create_confirmation_response(
        handler_input,
        message: str,
        card_title: Optional[str] = None,
        card_content: Optional[str] = None
    ):
        """
        Crea respuesta de confirmacion.

        Args:
            handler_input: HandlerInput de Alexa
            message: Mensaje de confirmacion
            card_title: Titulo de card opcional
            card_content: Contenido de card opcional

        Returns:
            Response de Alexa
        """
        builder = handler_input.response_builder.speak(message)

        if card_title and card_content:
            builder.set_card(title=card_title, content=card_content)

        return builder.ask("¿Necesitas algo mas?").response

    @staticmethod
    def create_help_response(handler_input):
        """
        Crea respuesta de ayuda estandarizada.

        Args:
            handler_input: HandlerInput de Alexa

        Returns:
            Response de Alexa
        """
        speak_output = (
            "Soy el Doctor de Errores, tu asistente para diagnosticar "
            "problemas de programacion en Python. "
            "Puedes decir: tengo un error module not found, "
            "o describir cualquier error que tengas. "
            "Tambien puedes configurar tu perfil diciendo: "
            "uso Windows y pip. "
            "¿Que error necesitas diagnosticar?"
        )

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask("¿Que error tienes?")
            .response
        )

    @staticmethod
    def create_welcome_response(handler_input):
        """
        Crea respuesta de bienvenida.

        Args:
            handler_input: HandlerInput de Alexa

        Returns:
            Response de Alexa
        """
        speak_output = (
            "Bienvenido al Doctor de Errores. "
            "Soy tu asistente para diagnosticar errores de Python. "
            "Describe el error que estas teniendo y te ayudare a solucionarlo."
        )

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask("¿Que error tienes?")
            .response
        )

    @staticmethod
    def create_goodbye_response(handler_input):
        """
        Crea respuesta de despedida.

        Args:
            handler_input: HandlerInput de Alexa

        Returns:
            Response de Alexa
        """
        speak_output = (
            "Hasta luego. "
            "Espero haber sido de ayuda. "
            "Vuelve cuando necesites diagnosticar otro error."
        )

        return handler_input.response_builder.speak(speak_output).response


class SessionStateFactory:
    """
    Factory para crear y gestionar estado de sesion.

    Centraliza la creacion de estructuras de estado de sesion.
    """

    @staticmethod
    def create_empty() -> Dict[str, Any]:
        """
        Crea un estado de sesion vacio.

        Returns:
            Diccionario con estructura base de sesion
        """
        return {
            'user_profile': None,
            'last_diagnostic': None,
            'solution_index': 0,
            'session_start': datetime.utcnow().isoformat()
        }

    @staticmethod
    def initialize_from_storage(
        user_id: str,
        stored_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Inicializa sesion desde datos almacenados.

        Args:
            user_id: ID del usuario
            stored_profile: Perfil almacenado en DynamoDB

        Returns:
            Diccionario de sesion inicializado
        """
        state = SessionStateFactory.create_empty()

        if stored_profile:
            state['user_profile'] = stored_profile
        else:
            state['user_profile'] = UserProfileFactory.get_default().to_dict()

        return state

    @staticmethod
    def reset_diagnostic_context(session_attrs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resetea el contexto de diagnostico manteniendo perfil.

        Args:
            session_attrs: Atributos de sesion actuales

        Returns:
            Atributos con diagnostico reseteado
        """
        new_attrs = session_attrs.copy()
        new_attrs['last_diagnostic'] = None
        new_attrs['solution_index'] = 0
        return new_attrs
