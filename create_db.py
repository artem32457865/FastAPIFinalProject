"""
Скрипт для ініціалізації бази даних за допомогою міграцій Alembic.
"""

from alembic.config import Config
from alembic import command

def create_database_with_alembic():
    """
    Створюйте таблиці баз даних за допомогою міграцій Alembic.
    """
    print("Ініціалізація бази даних за допомогою Alembic...")
    
    # Configure Alembic
    alembic_cfg = Config("alembic.ini")
    
    # Run migrations
    try:
        command.upgrade(alembic_cfg, "head")
        print("База даних успішно оновлена до останньої версії!")
    except Exception as e:
        print(f"Помилка при оновленні бази данних: {e}")
        raise e

if __name__ == "__main__":
    create_database_with_alembic()