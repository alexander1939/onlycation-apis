#!/usr/bin/env python3
"""
Script de prueba para el ContentFilterService
Permite probar el filtrado de contenido sin necesidad de la API completa
"""

import sys
import os

# Agregar el directorio raíz al path para importar los módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.content_filter.content_filter_service import ContentFilterService, ContentSeverity

def test_content_filter():
    """Prueba el servicio de filtrado de contenido con diferentes casos"""
    
    print("🧪 Iniciando pruebas del ContentFilterService...")
    print("=" * 60)
    
    # Inicializar el servicio
    filter_service = ContentFilterService()
    
    # Casos de prueba
    test_cases = [
        # Mensajes apropiados
        ("Hola profesor, ¿cómo está?", "student", "✅ Apropiado"),
        ("Necesito ayuda con matemáticas", "student", "✅ Apropiado"),
        ("Excelente clase de hoy", "student", "✅ Apropiado"),
        
        # Mensajes con contenido educativo
        ("Estoy estudiando para el examen", "student", "✅ Contexto educativo"),
        ("¿Puede explicar la tarea?", "student", "✅ Contexto educativo"),
        
        # Mensajes inapropiados leves
        ("Esto es una mierda", "student", "❌ Lenguaje inapropiado"),
        ("Qué estúpida pregunta", "student", "❌ Insulto"),
        
        # Mensajes inapropiados graves
        ("Eres un idiota", "student", "❌ Insulto directo"),
        ("Te voy a matar", "student", "❌ Amenaza"),
        ("Hijo de puta", "student", "❌ Insulto grave"),
        
        # Patrones sospechosos
        ("Mi número es 123456789", "student", "⚠️ Información personal"),
        ("Visita www.ejemplo.com", "student", "⚠️ URL sospechosa"),
        ("ESTO ES SPAM!!!", "student", "⚠️ Mayúsculas excesivas"),
        
        # Mensajes vacíos o inválidos
        ("", "student", "❌ Mensaje vacío"),
        ("   ", "student", "❌ Solo espacios"),
        
        # Contexto de profesor vs estudiante
        ("Necesito explicar esta mierda", "teacher", "⚠️ Profesor - contexto educativo"),
        ("Necesito explicar esta mierda", "student", "❌ Estudiante - inapropiado"),
    ]
    
    print(f"📝 Ejecutando {len(test_cases)} casos de prueba...\n")
    
    for i, (message, role, expected) in enumerate(test_cases, 1):
        print(f"Caso {i:2d}: {expected}")
        print(f"Mensaje: '{message}'")
        print(f"Rol: {role}")
        
        try:
            result = filter_service.filter_message(message, role)
            
            print(f"Resultado: {'✅ APROPIADO' if result['is_appropriate'] else '❌ BLOQUEADO'}")
            print(f"Severidad: {result['severity'].value}")
            
            if result['blocked_reasons']:
                print(f"Razones: {', '.join(result['blocked_reasons'])}")
            
            if result['suggestions']:
                print(f"Sugerencias: {', '.join(result['suggestions'])}")
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
        
        print("-" * 50)
    
    # Estadísticas del filtro
    print("\n📊 Estadísticas del filtro:")
    stats = filter_service.get_filter_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n🎯 Pruebas completadas!")

def test_interactive():
    """Modo interactivo para probar mensajes personalizados"""
    
    print("\n🎮 Modo interactivo - Prueba tus propios mensajes")
    print("Escribe 'quit' para salir")
    print("=" * 50)
    
    filter_service = ContentFilterService()
    
    while True:
        try:
            message = input("\n💬 Escribe un mensaje: ").strip()
            
            if message.lower() in ['quit', 'exit', 'salir']:
                print("👋 ¡Hasta luego!")
                break
            
            if not message:
                print("⚠️ Por favor escribe un mensaje válido")
                continue
            
            role = input("👤 Rol (student/teacher) [student]: ").strip() or "student"
            
            if role not in ['student', 'teacher']:
                print("⚠️ Rol inválido, usando 'student'")
                role = "student"
            
            print(f"\n🔍 Analizando mensaje...")
            result = filter_service.filter_message(message, role)
            
            print(f"\n{'✅ MENSAJE APROPIADO' if result['is_appropriate'] else '❌ MENSAJE BLOQUEADO'}")
            print(f"Severidad: {result['severity'].value.upper()}")
            
            if result['blocked_reasons']:
                print(f"\n🚫 Razones de bloqueo:")
                for reason in result['blocked_reasons']:
                    print(f"  • {reason}")
            
            if result['suggestions']:
                print(f"\n💡 Sugerencias:")
                for suggestion in result['suggestions']:
                    print(f"  • {suggestion}")
            
            if result['filtered_content'] != message:
                print(f"\n🔄 Contenido filtrado: '{result['filtered_content']}'")
                
        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    print("🛡️ ContentFilterService - Herramienta de Prueba")
    print("=" * 60)
    
    # Verificar que better-profanity esté instalado
    try:
        from better_profanity import profanity
        print("✅ better-profanity está disponible")
    except ImportError:
        print("❌ ERROR: better-profanity no está instalado")
        print("Ejecuta: pip install better-profanity>=0.7.0")
        sys.exit(1)
    
    # Ejecutar pruebas automáticas
    test_content_filter()
    
    # Preguntar si quiere modo interactivo
    response = input("\n¿Quieres probar el modo interactivo? (s/n): ").strip().lower()
    if response in ['s', 'si', 'sí', 'y', 'yes']:
        test_interactive()
