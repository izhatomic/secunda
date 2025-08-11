import subprocess
import sys


def create_migration(message="Auto migration"):
    """Создание новой миграции"""
    try:
        result = subprocess.run([
            sys.executable, "-m", "alembic", "revision", "--autogenerate", "-m", message
        ], check=True, capture_output=True, text=True)
        print(f"Миграция создана: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при создании миграции: {e.stderr}")


def upgrade_database():
    """Применение миграций к базе данных"""
    try:
        result = subprocess.run([
            sys.executable, "-m", "alembic", "upgrade", "head"
        ], check=True, capture_output=True, text=True)
        print(f"Миграции применены: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при применении миграций: {e.stderr}")


def downgrade_database(revision="base"):
    """Откат миграций"""
    try:
        result = subprocess.run([
            sys.executable, "-m", "alembic", "downgrade", revision
        ], check=True, capture_output=True, text=True)
        print(f"Миграции откачены: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при откате миграций: {e.stderr}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python migrate_commands.py [create|upgrade|downgrade] [message/revision]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        message = sys.argv[2] if len(sys.argv) > 2 else "Auto migration"
        create_migration(message)
    elif command == "upgrade":
        upgrade_database()
    elif command == "downgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "base"
        downgrade_database(revision)
    else:
        print("Неизвестная команда. Используйте: create, upgrade, или downgrade")
