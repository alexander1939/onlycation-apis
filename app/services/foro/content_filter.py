from better_profanity import profanity
from fastapi import HTTPException
import logging
import unicodedata
import re

def normalize_text(text: str) -> str:
    """Normaliza texto: minúsculas, sin acentos, sin caracteres especiales"""
    if not text:
        return ""
    
    # Convertir a minúsculas
    text = text.lower()
    
    # Remover acentos
    text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )
    
    # Remover caracteres especiales y números que podrían usarse para evadir el filtro
    # Ejemplo: p3nd3j0 -> pendejo, p@to -> pato
    replacements = {
        '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', 
        '7': 't', '8': 'b', '@': 'a', '$': 's', '!': 'i'
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Remover espacios extra y caracteres especiales
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

class ContentFilterService:
    def __init__(self):
        # Diccionario personalizado en español (más completo)
        custom_bad_words = [
            # Palabras básicas (de tu lista original)
            "puto", "puta", "verga", "pendejo", "pendeja", "cabron", "cabrona",
            "chingar", "chinga", "carajo", "coño", "malparido", "malparida",
            "hijueputa", "culero", "culera", "maricon", "marica", "boludo", "boluda",
            "pelotudo", "pelotuda", "concha", "picha", "pija", "poronga",
            "mierda", "estupido", "estupida", "idiota", "imbecil", "mrda", "mrdas",
            "pdj", "pdja", "putas", "putos", "ctmd",
    
            # Variaciones y palabras adicionales (de tu lista original)
            "joder", "jodido", "jodida", "putear", "puteo", "mamada", "mamadas",
            "pinche", "pinches", "ojete", "ojetes", "nalga", "nalgas",
            "teta", "tetas", "culo", "culos", "ano", "pene", "vagina",
            "perra", "perro", "zorra", "zorras", "gay", "lesbiana",
            "retrasado", "retrasada", "mongolico", "mongolica",
    
            # Insultos regionales (de tu lista original)
            "weon", "weona", "huevon", "huevona", "gonorrea", "malandro",
            "mamagallista", "berraco", "verraco", "chimba", "parcero",
            
            # Evasiones comunes (de tu lista original)
            "p3nd3jo", "p3nd3ja", "put0", "put4", "v3rga", "m13rd4",
            "3stup1do", "1d10ta", "1mb3c1l", "c4br0n",
            
            # Nuevas groserías y variaciones (de la lista ampliada anterior)
            "cagada", "cagar", "cagado", "cagada", "cagón", "cagona",
            "mierdoso", "mierdosa", "culiado", "culiada", "chupar", "chupa",
            "mamón", "mamona", "chingadera", "chingado", "chingada",
            "pito", "pitos", "huevada", "huevadas", "gil", "gila",
            "pelado", "pelada", "tarado", "tarada", "baboso", "babosa",
            "pendejada", "pendejadas", "joto", "jotos", "putazo",
            "putada", "putadas", "vergaso", "vergasos", "culazo",
            
            # Más insultos regionales (de la lista ampliada anterior)
            "carechimba", "caremonda", "careculo", "careverga", "culicagado",
            "culicagada", "sapazo", "sapo", "sapa", "fregón", "fregona",
            "jodón", "jodona", "guey", "güey", "gueyes", "cholo", "chola",
            "naco", "naca", "chafa", "chafas", "choto", "chota",
            
            # Más evasiones comunes (de la lista ampliada anterior)
            "c4g4d4", "ch1ng4", "p1t0", "cul14d0", "m4m0n", "m4m4d4",
            "h4v4d4", "j0t0", "p3nd3j4d4", "t4r4d0", "b4b0s0",
            "gu3y", "n4c0", "ch4f4",
            
            # Nuevas siglas y variaciones relacionadas con ctm, pdj, ptm
            "ctm", "ptm", "hpm", "hptm", "hpt", "hijoputa", "hijoeputa",
            "chingatumadre", "putamadre", "hijoputamadre", "hpmadre",
            "ctmadre", "ptmadre", "pndj", "pndjo", "pndejo", "pndeja",
            "c.t.m", "p.t.m", "h.p.m", "ctm4dre", "put4madre", "h1j0put4",
            "ch1ng4tum4dre", "p3nd3j0", "p3nd3j4", "hpt4", "h1j0put4m4dre",
            "ctmadr3", "ptmadr3"
        ]
        
        # Normalizar todas las palabras del diccionario
        normalized_bad_words = list(set([normalize_text(w) for w in custom_bad_words if w]))
        
        # Configurar better-profanity
        profanity.load_censor_words(normalized_bad_words)
        
        # También mantener una lista propia para verificación adicional
        self.bad_words = normalized_bad_words
        
        # Log para debug
        logging.info(f"Filtro de contenido inicializado con {len(self.bad_words)} palabras prohibidas")
    
    def contains_profanity(self, text: str) -> tuple[bool, str]:
        """
        Verifica si el texto contiene lenguaje inapropiado
        Retorna: (tiene_groseria, palabra_encontrada)
        """
        if not text or not text.strip():
            return False, ""
        
        normalized_text = normalize_text(text)
        
        # Método 1: Usar better-profanity
        if profanity.contains_profanity(normalized_text):
            # Intentar encontrar qué palabra específica fue detectada
            for word in self.bad_words:
                if word in normalized_text:
                    return True, word
            return True, "palabra no identificada"
        
        # Método 2: Verificación manual adicional
        words_in_text = normalized_text.split()
        for word in words_in_text:
            if word in self.bad_words:
                return True, word
            
            # Verificar si alguna palabra prohibida está contenida en la palabra actual
            for bad_word in self.bad_words:
                if len(bad_word) > 3 and bad_word in word:
                    return True, bad_word
        
        return False, ""
    
    def validate_content(self, text: str, field_name: str = "contenido") -> None:
        """Valida el contenido y lanza excepción si es inapropiado"""
        if not text or not text.strip():
            return
        
        has_profanity, found_word = self.contains_profanity(text)
        
        if has_profanity:
            logging.warning(f"Contenido inapropiado detectado en {field_name}: '{text}' - Palabra: '{found_word}'")
            raise HTTPException(
                status_code=400,
                detail=f"El {field_name} contiene lenguaje inapropiado ('{found_word}'). Por favor, modifica tu mensaje."
            )
    
    def debug_text(self, text: str) -> dict:
        """Método para debugging - muestra cómo se procesa el texto"""
        original = text
        normalized = normalize_text(text)
        has_profanity, found_word = self.contains_profanity(text)
        
        return {
            "original": original,
            "normalized": normalized,
            "has_profanity": has_profanity,
            "found_word": found_word,
            "words_in_text": normalized.split()
        }

# Instancia global
content_filter = ContentFilterService()

# # Función helper para testing
# def test_content_filter():
#     """Función para probar el filtro de contenido"""
#     test_cases = [
#         "Este es mi primer foro",
#         "Eres un pendejo",
#         "P3nd3jo con números", 
#         "Qué p@to eres",
#         "Esto es una mierda",
#         "M13rd4 con números",
#         "Texto normal sin problemas"
#     ]
    
#     print("=== PRUEBAS DEL FILTRO DE CONTENIDO ===")
#     for test in test_cases:
#         result = content_filter.debug_text(test)
#         print(f"\nTexto: '{test}'")
#         print(f"Normalizado: '{result['normalized']}'")
#         print(f"Tiene grosería: {result['has_profanity']}")
#         if result['has_profanity']:
#             print(f"Palabra encontrada: '{result['found_word']}'")
#         print("-" * 50)

# if __name__ == "__main__":
#     test_content_filter()