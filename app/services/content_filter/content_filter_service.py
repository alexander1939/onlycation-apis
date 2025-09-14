"""
Servicio de filtrado de contenido para mensajes del chat.
Detecta y bloquea mensajes inapropiados, ofensivos o irrespetuosos.
"""

import re
from typing import Dict, List, Optional
from enum import Enum
from better_profanity import profanity


class ContentSeverity(Enum):
    """Niveles de severidad del contenido detectado."""
    LOW = "low"           # Advertencia leve
    MEDIUM = "medium"     # Advertencia media
    HIGH = "high"         # Bloqueo automático
    CRITICAL = "critical" # Bloqueo inmediato


class ContentFilterService:
    """Servicio para filtrar contenido inapropiado en mensajes."""
    
    def __init__(self):
        """Inicializa el servicio de filtrado."""
        # Configurar better-profanity
        profanity.load_censor_words()
        
        # Agregar palabras personalizadas en español
        self._setup_spanish_words()
        
        # Configurar patrones sospechosos
        self.suspicious_patterns = [
            r'\b\d{4,}\b',  # Números largos (posibles números de teléfono)
            r'@\w+',        # Menciones de usuarios
            r'http[s]?://', # URLs
            r'www\.',       # URLs sin protocolo
            r'\b[A-Z]{3,}\b', # Texto en mayúsculas excesivas
            r'[!]{3,}',     # Múltiples signos de exclamación
            r'[?]{3,}',     # Múltiples signos de interrogación
            r'[.]{3,}',     # Múltiples puntos
        ]
        
        # Palabras de contexto educativo que pueden ser falsos positivos
        self.educational_context = [
            "estudio", "estudiar", "aprender", "enseñar", "profesor", "profesora",
            "alumno", "alumna", "estudiante", "clase", "curso", "materia",
            "examen", "tarea", "proyecto", "investigación", "trabajo", "trabajar",
            "investigar", "investigación", "estudiar", "estudio", "estudios"
        ]
    
    def _setup_spanish_words(self):
        """Configura palabras personalizadas en español."""
        spanish_words = [
            # Insultos comunes
            "idiota", "estúpido", "imbécil", "tonto", "burro", "animal",
            "basura", "mierda", "puto", "puta", "hijo de puta", "hija de puta",
            "cabrón", "cabrona", "pendejo", "pendeja", "culero", "culera",
            "hijo de perra", "hija de perra", "malparido", "malparida",
            "desgraciado", "desgraciada", "maldito", "maldita", "mampo", "gei",
            "careverga", "chupapija", "retrasado", "retrasada", "mongol", "mongola",
            "subnormal", "tarado", "tarada", "zopenco", "zopenca", "patán", "patana",
            "cretino", "cretina", "estúpida", "idiot", "douche", "mierdoso", "mierdosa",
            "baboso", "babosa", "gilipollas", "jodido", "jodida", "pinche", "chingado",
            "chingada", "verga", "carepicha", "mamón", "mamona", "panocha", "cagado",
            "cagada", "pelotudo", "pelotuda", "boludo", "boluda",
            # Variaciones con números y símbolos
            "1d10t4", "1di0t4", "3stup1d0", "3stupid0", "1mb3c1l", "t0nt0",
            "bur0", "m13rd4", "pvt0", "pvt4", "h1j0 de puta", "h1j4 de puta",
            "c4br0n", "c4br0na", "p3nd3j0", "p3nd3j4", "cul3r0", "cul3r4",
            "m4lp4r1d0", "m4lp4r1d4", "g1l1p0ll4s", "j0d1d0", "j0d1d4",
            "p1nch3", "ch1ng4d0", "ch1ng4d4", "v3rg4", "m4m0n", "m4m0n4",

            # Amenazas
            "te voy a matar", "te voy a golpear", "te voy a lastimar",
            "te voy a hacer daño", "te voy a joder", "te voy a arruinar",
            "te voy a destruir", "te voy a acabar", "te voy a eliminar",
            "te voy a romper", "te voy a partir", "te voy a quebrar",
            "te voy a dar una paliza", "te voy a hacer pedazos", "te voy a machacar",
            "te voy a reventar", "te voy a cagar", "te voy a chingar", "te voy a putear",
            "te voy a dar duro", "voy a matarte", "voy a romperte la cara",
            # Variaciones con números y símbolos
            "t3 v0y a m4t4r", "t3 v0y a g0lp34r", "t3 v0y a l4st1m4r",
            "t3 v0y a h4c3r d4ñ0", "t3 v0y a j0d3r", "t3 v0y a 4rru1n4r",
            "t3 v0y a d3stru1r", "v0y a m4t4rt3", "v0y a r0mp3rt3 l4 c4r4",

            # Acoso
            "acoso", "acosar", "molestar", "fastidiar", "joder", "burlarse",
            "burlar", "ridiculizar", "humillar", "avergonzar", "intimidar",
            "intimidación", "hostigar", "hostigamiento", "molestoso", "molestosa",
            "acosador", "acosadora", "perturbar", "molestia", "provocar",
            "provocación", "despreciar", "desprecio", "insultar", "insulto",
            "denigrar", "denigración", "ofender", "ofensa",
            # Variaciones con números y símbolos
            "4c0s0", "4c0s4r", "m0l3st4r", "f4st1d14r", "j0d3r", "1nsult4r",

            # Contenido inapropiado
            "sexo", "sexual", "pornografía", "porno", "nudez", "desnudo",
            "prostitución", "prostituta", "escort", "acompañante", "follar",
            "coger", "joder", "chingar", "fuck", "fucking", "pija", "chota",
            "chupapija", "coño", "vagina", "pene", "nalgas", "culo", "tetas",
            "mamada", "mamadas", "pito", "pichula", "polla", "orgía", "erótico",
            "erótica", "xxx", "nsfw", "desnuda", "pornogrático", "pornográfica",
            "cachondo", "cachonda",
            # Variaciones con números y símbolos
            "s3x0", "s3xu4l", "p0rn0", "p0rn0gr4f14", "nud3z", "d3snud0",
            "pr0st1tuc10n", "pr0st1tut4", "f0ll4r", "c0g3r", "ch1ng4r",
            "f4ck", "fvck", "p1j4", "ch0t4", "chup4p1j4", "c0ñ0", "v4g1n4",
            "p3n3", "n4lg4s", "cul0", "t3t4s", "m4m4d4", "p1t0", "p1chul4",
            "p0ll4", "0rg14", "3r0t1c0", "3r0t1c4", "xxx", "n5fw", "d3snud4",
            "c4ch0nd0", "c4ch0nd4",

            # Discriminación
            "racista", "racismo", "discriminar", "discriminación", "homofóbico",
            "homofobia", "machista", "machismo", "sexista", "sexismo", "clasista",
            "clasismo", "gay", "lesbiana", "trans", "transexual", "bisexual",
            "negro", "negra", "blanco", "blanca", "indio", "india", "chino",
            "china", "japonés", "japonesa", "coreano", "coreana", "xenófobo",
            "xenofobia", "antisemita", "antisemitismo", "fascista", "fascismo",
            "nazi", "nazismo", "misógino", "misoginia", "homosexual", "maricón",
            "marica", "joto", "jota", "travesti", "transex", "inmigrante",
            "extranjero", "extranjera", "gringo", "gringa",
            # Variaciones con números y símbolos
            "r4c1st4", "r4c1sm0", "d1scr1m1n4r", "d1scr1m1n4c10n", "h0m0f0b1c0",
            "h0m0f0b14", "m4ch1st4", "m4ch1sm0", "s3x1st4", "s3x1sm0",
            "cl4s1st4", "cl4s1sm0", "g4y", "l3sb14n4", "tr4ns", "tr4ns3xu4l",
            "b1s3xu4l", "n3gr0", "n3gr4", "1nd10", "1nd14", "ch1n0", "ch1n4",
            "x3n0f0b0", "x3n0f0b14", "4nt1s3m1t4", "m1s0g1n0", "m1s0g1n14",
            "h0m0s3xu4l", "m4r1c0n", "m4r1c4", "j0t0", "j0t4", "tr4v3st1",
            "tr4ns3x", "1nm1gr4nt3", "3xtr4nj3r0", "3xtr4nj3r4", "gr1ng0",
            "gr1ng4",

            # Odio y violencia
            "odio", "odiar", "matar", "asesinar", "asesino", "asesina",
            "violencia", "violento", "violenta", "agredir", "agresión",
            "golpear", "golpe", "torturar", "tortura", "masacre", "exterminar",
            "exterminio", "genocidio",
            # Variaciones con números y símbolos
            "0d10", "0d14r", "m4t4r", "4s3s1n4r", "4s3s1n0", "4s3s1n4",
            "v10l3nc14", "v10l3nt0", "v10l3nt4", "4gr3d1r", "4gr3s10n",
            "g0lp34r", "g0lp3", "t0rtur4r", "t0rtur4", "m4s4cr3", "3xt3rm1n4r",
            "3xt3rm1n10", "g3n0c1d10",

            # Lenguaje subido de tono o grosero
            "carajo", "cagarla", "cagar", "me cago", "cojones", "huevos",
            "guevo", "guevón", "guevona", "mierdero", "chingadera", "chingón",
            "chingona", "putada", "putazo",
            # Variaciones con números y símbolos
            "c4r4j0", "c4g4rl4", "c4g4r", "m3 c4g0", "c0j0n3s", "hu3v0s",
            "gu3v0", "gu3v0n", "gu3v0n4", "m13rd3r0", "ch1ng4d3r4", "ch1ng0n",
            "ch1ng0n4", "put4d4", "put4z0",

            # Términos relacionados con drogas o actividades ilegales
            "droga", "drogas", "narcotráfico", "narco", "marihuana", "cocaína",
            "coca", "crack", "metanfetamina", "heroína", "traficar", "tráfico",
            "dealer", "vender drogas",
            # Variaciones con números y símbolos
            "dr0g4", "dr0g4s", "n4rc0tr4f1c0", "n4rc0", "m4r1hu4n4", "c0c41n4",
            "c0c4", "cr4ck", "m3t4nf3t4m1n4", "h3r01n4", "tr4f1c4r", "tr4f1c0",
            "d34l3r", "v3nd3r dr0g4s"
        ]
        
        # Agregar palabras al filtro
        profanity.add_censor_words(spanish_words)
    
    def filter_message(self, content: str, user_role: str = "student") -> Dict:
        """
        Filtra un mensaje y determina si es apropiado.
        
        Args:
            content: Contenido del mensaje a filtrar
            user_role: Rol del usuario (student/teacher)
            
        Returns:
            Dict con el resultado del filtrado:
            {
                "is_appropriate": bool,
                "severity": ContentSeverity,
                "blocked_reasons": List[str],
                "suggestions": List[str],
                "filtered_content": str,
                "original_content": str
            }
        """
        if not content or not content.strip():
            return {
                "is_appropriate": False,
                "severity": ContentSeverity.LOW,
                "blocked_reasons": ["El mensaje está vacío"],
                "suggestions": ["Por favor, escribe un mensaje válido"],
                "filtered_content": "",
                "original_content": content
            }
        
        # Normalizar contenido
        normalized_content = self._normalize_text(content)
        
        # Verificar contenido inapropiado con better-profanity
        is_profane = profanity.contains_profanity(content)
        
        # Verificar patrones sospechosos
        suspicious_matches = self._check_suspicious_patterns(normalized_content)
        
        # Verificar contexto educativo
        educational_context = self._check_educational_context(normalized_content)
        
        # Determinar severidad
        severity = self._determine_severity(is_profane, suspicious_matches, educational_context)
        
        # Generar razones de bloqueo
        blocked_reasons = self._generate_blocked_reasons(is_profane, suspicious_matches)
        
        # Generar sugerencias
        suggestions = self._generate_suggestions(is_profane, suspicious_matches, educational_context)
        
        # Determinar si el mensaje es apropiado
        is_appropriate = severity in [ContentSeverity.LOW] or (
            severity == ContentSeverity.MEDIUM and educational_context
        )
        
        # Sanitizar contenido si es necesario
        filtered_content = content if is_appropriate else profanity.censor(content)
        
        return {
            "is_appropriate": is_appropriate,
            "severity": severity,
            "blocked_reasons": blocked_reasons,
            "suggestions": suggestions,
            "filtered_content": filtered_content,
            "original_content": content
        }
    
    def _normalize_text(self, text: str) -> str:
        """Normaliza el texto para análisis."""
        # Convertir a minúsculas
        text = text.lower()
        
        # Remover acentos y caracteres especiales
        replacements = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ñ': 'n', 'ü': 'u', 'ç': 'c', 'ü': 'u'
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Remover caracteres especiales excepto espacios
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Normalizar espacios
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _check_suspicious_patterns(self, text: str) -> List[str]:
        """Verifica patrones sospechosos en el texto."""
        matches = []
        
        for pattern in self.suspicious_patterns:
            if re.search(pattern, text):
                matches.append(pattern)
        
        return matches
    
    def _check_educational_context(self, text: str) -> bool:
        """Verifica si el texto tiene contexto educativo."""
        educational_words = [word.lower() for word in self.educational_context]
        return any(word in text for word in educational_words)
    
    def _determine_severity(self, is_profane: bool, suspicious_matches: List, educational_context: bool) -> ContentSeverity:
        """Determina la severidad del contenido detectado."""
        if not is_profane and not suspicious_matches:
            return ContentSeverity.LOW
        
        # Si hay contenido inapropiado
        if is_profane:
            if educational_context:
                return ContentSeverity.MEDIUM
            else:
                return ContentSeverity.HIGH
        
        # Si hay patrones sospechosos
        if suspicious_matches:
            if educational_context:
                return ContentSeverity.MEDIUM
            else:
                return ContentSeverity.HIGH
        
        return ContentSeverity.MEDIUM
    
    def _generate_blocked_reasons(self, is_profane: bool, suspicious_matches: List) -> List[str]:
        """Genera razones de bloqueo del mensaje."""
        reasons = []
        
        if is_profane:
            reasons.append("El mensaje contiene lenguaje inapropiado, insultos o palabras ofensivas")
        
        if suspicious_matches:
            reasons.append("El mensaje contiene patrones sospechosos (URLs, menciones, información personal, etc.)")
        
        return reasons
    
    def _generate_suggestions(self, is_profane: bool, suspicious_matches: List, educational_context: bool) -> List[str]:
        """Genera sugerencias para mejorar el mensaje."""
        suggestions = []
        
        if is_profane:
            suggestions.append("Por favor, mantén un lenguaje respetuoso y profesional")
            suggestions.append("Evita usar insultos, amenazas o contenido inapropiado")
        
        if suspicious_matches:
            suggestions.append("Evita incluir URLs, menciones de usuarios o información personal")
        
        if educational_context:
            suggestions.append("Recuerda que estás en un ambiente educativo, mantén el respeto mutuo")
        
        if not suggestions:
            suggestions.append("Mantén un tono profesional y respetuoso en tus mensajes")
        
        return suggestions
    
    def get_filter_stats(self) -> Dict:
        """Obtiene estadísticas del filtro de contenido."""
        return {
            "total_suspicious_patterns": len(self.suspicious_patterns),
            "educational_context_words": len(self.educational_context),
            "supported_languages": ["español", "inglés"],
            "filter_version": "1.0.0"
        }
    
    def test_filter(self, test_message: str) -> Dict:
        """Método de prueba para el filtro."""
        return self.filter_message(test_message)
