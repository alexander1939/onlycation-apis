import re
import os
import ast
from typing import List


def check_class_naming_convention(code: str, file_path: str) -> List[str]:
    """
    Verifica que las clases sigan CamelCase y estén en singular.
    
    Args:
        code (str): Código fuente a verificar
        file_path (str): Ruta del archivo para reportes
        
    Returns:
        List[str]: Lista de errores encontrados
    """
    errors = []
    class_pattern = re.compile(r'^\s*class\s+([A-Za-z0-9]+)(\(|:)')
    
    for line_no, line in enumerate(code.split('\n'), 1):
        match = class_pattern.match(line)
        if match:
            class_name = match.group(1)
            
            # Verificar CamelCase
            if not re.fullmatch(r'([A-Z][a-z0-9]*)+', class_name):
                msg = f"{file_path}:{line_no} - Clase '{class_name}' no está en CamelCase"
                errors.append(msg)
                
            # Verificar singular (chequeo básico)
            if class_name.endswith('s') and len(class_name) > 3:
                msg = f"{file_path}:{line_no} - Clase '{class_name}' parece estar en plural"
                errors.append(msg)
    
    return errors


def check_snake_case_naming(code: str, file_path: str) -> List[str]:
    """
    Verifica snake_case para variables y funciones, excluyendo constantes.
    
    Args:
        code (str): Código fuente a verificar
        file_path (str): Ruta del archivo para reportes
        
    Returns:
        List[str]: Lista de errores encontrados
    """
    errors = []
    patterns = {
        'function': re.compile(r'def\s+([a-z0-9_]+)\('),
        'variable': re.compile(r'\b([A-Za-z0-9_]+)\s*=\s*[^#]*')
    }
    
    for line_no, line in enumerate(code.split('\n'), 1):
        # Ignorar comentarios
        clean_line = re.sub(r'#.*', '', line)
        
        # Verificar funciones
        for match in patterns['function'].finditer(clean_line):
            name = match.group(1)
            if name != name.lower() or '__' in name:
                msg = f"{file_path}:{line_no} - Función '{name}' no está en snake_case válido"
                errors.append(msg)
        
        # Verificar variables
        for match in patterns['variable'].finditer(clean_line):
            name = match.group(1)
            if name.isupper():
                continue  # Ignorar constantes
            if not re.fullmatch(r'[a-z][a-z0-9_]*', name):
                msg = f"{file_path}:{line_no} - Variable '{name}' no está en snake_case válido"
                errors.append(msg)
    
    return errors


def check_function_verbs(code: str, file_path: str) -> List[str]:
    """
    Verifica que las funciones empiecen con verbos en infinitivo.
    
    Args:
        code (str): Código fuente a verificar
        file_path (str): Ruta del archivo para reportes
        
    Returns:
        List[str]: Lista de errores encontrados
    """
    errors = []
    common_verbs = {
        'get', 'set', 'create', 'update', 'delete', 'validate',
        'check', 'process', 'handle', 'generate', 'send', 'receive'
    }
    
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_name = node.name
            if func_name.startswith('_'):
                continue  # Ignorar métodos privados/mágicos
                
            first_part = func_name.split('_')[0]
            if first_part not in common_verbs:
                verb_examples = ', '.join(sorted(common_verbs))
                errors.append(
                    f"{file_path}:{node.lineno} - "
                    f"Función '{func_name}' no comienza con verbo común "
                    f"(ej: {verb_examples})"
                )
    
    return errors


def test_naming_conventions_on_services():
    """
    Ejecuta todas las verificaciones de convenciones de código en el directorio de servicios.
    """
    base_dir = "app/services/"
    total_errors = 0
    
    for root, _, files in os.walk(base_dir):
        for file in files:
            if not file.endswith(".py") or file == "__init__.py":
                continue
                
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                code = f.read()
                
            errors = []
            errors += check_class_naming_convention(code, path)
            errors += check_snake_case_naming(code, path)
            errors += check_function_verbs(code, path)
            
            if errors:
                total_errors += len(errors)
                print(f"\nErrores en {path}:")
                for error in errors:
                    print(f"  • {error}")
    
    error_msg = f"Se encontraron {total_errors} violaciones de convenciones de código"
    assert total_errors == 0, error_msg
