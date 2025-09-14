from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.cores.db import async_session
from app.models.foro.category import Category


async def create_categories():
    db: AsyncSession = async_session()
    
    try:
        result = await db.execute(select(Category))
        categories = result.scalars().all()
        
        if not categories:
            # Lista de materias escolares
            categories_list = [
                Category(name="Español"),
                Category(name="Matemáticas"),
                Category(name="Ciencias Naturales"),
                Category(name="Historia"),
                Category(name="Geografía"),
                Category(name="Inglés"),
                Category(name="Educación Física"),
                Category(name="Artes"),
                Category(name="Tecnología"),
                Category(name="Física"),
                Category(name="Química"),
                Category(name="Biología"),
                Category(name="Cívica y Ética"),
                Category(name="Literatura"),
                Category(name="Informática"),
                Category(name="Ayuda con Tareas"),
                Category(name="Lenguas"),
                Category(name="Cómo estudiar mejor"),
                Category(name="Explicación de un tema"),
                Category(name="Apoyo en Proyectos"),
                Category(name="Resolver Ejercicios"),
                Category(name="Qué carrera elegir"),
                Category(name="Consejos para la escuela"),
                Category(name="Organización y hábitos"),
                Category(name="Recursos y material de apoyo"),
                Category(name="Uso de plataformas"),
                Category(name="Trucos de Computadora"),
                Category(name="Aplicaciones útiles para estudiar"),
                Category(name="Dudas rápidas"),
                Category(name="Foro libre"),
                Category(name="Tips de vida"),
            ]
            
            db.add_all(categories_list)
            await db.commit()
            print("✅ Categorías creadas exitosamente en la base de datos.")
        else:
            print("ℹ️ Las categorías ya existen en la base de datos.")
            
    except Exception as e:
        await db.rollback()
        print(f"❌ Error creando categorías: {str(e)}")
        
    finally:
        await db.close()
