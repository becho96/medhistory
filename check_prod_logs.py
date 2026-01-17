#!/usr/bin/env python3
"""
Скрипт для проверки логов контейнеров на production сервере
Использует тот же подход SSH подключения, что и db-viewer/app.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Загрузить .env файл если есть
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

# SSH конфигурация (из db-viewer/app.py)
SSH_CONFIG = {
    'host': os.getenv('PROD_SSH_HOST', '158.160.99.232'),
    'port': int(os.getenv('PROD_SSH_PORT', '22')),
    'username': os.getenv('PROD_SSH_USER', 'yc-user'),
    'key_path': os.path.expanduser(os.getenv('PROD_SSH_KEY', '~/.ssh/id_rsa')),
}

DOCKER_COMPOSE_PATH = '~/medhistory'
DOCKER_COMPOSE_FILES = ['docker-compose.prod.yml', 'docker-compose.yml']

def check_ssh_key():
    """Проверить наличие SSH ключа"""
    key_path = SSH_CONFIG['key_path']
    if not os.path.exists(key_path):
        print(f"❌ SSH ключ не найден: {key_path}")
        print(f"💡 Установите переменную PROD_SSH_KEY или поместите ключ в ~/.ssh/id_rsa")
        return False
    return True

def execute_ssh_command(command):
    """Выполнить команду через SSH используя paramiko"""
    try:
        import paramiko
    except ImportError:
        print("❌ Библиотека paramiko не установлена")
        print("💡 Установите: pip install paramiko")
        return None, None
    
    key_path = SSH_CONFIG['key_path']
    
    try:
        # Подключение через SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Загрузить приватный ключ
        key = paramiko.RSAKey.from_private_key_file(key_path)
        
        print(f"🔌 Подключение к {SSH_CONFIG['username']}@{SSH_CONFIG['host']}...")
        ssh.connect(
            hostname=SSH_CONFIG['host'],
            port=SSH_CONFIG['port'],
            username=SSH_CONFIG['username'],
            pkey=key,
            timeout=10
        )
        
        # Выполнить команду
        stdin, stdout, stderr = ssh.exec_command(command)
        
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        
        ssh.close()
        
        return output, error, exit_status
        
    except Exception as e:
        return None, str(e), -1

def find_docker_compose_file():
    """Найти docker-compose файл на сервере"""
    for compose_file in DOCKER_COMPOSE_FILES:
        command = f"cd {DOCKER_COMPOSE_PATH} && test -f {compose_file} && echo {compose_file} || echo ''"
        output, error, exit_status = execute_ssh_command(command)
        if output and output.strip():
            return compose_file.strip()
    return None

def check_containers_status():
    """Проверить статус контейнеров"""
    print("\n" + "="*70)
    print("📊 Статус контейнеров")
    print("="*70)
    
    # Попробовать через docker-compose
    compose_file = find_docker_compose_file()
    if compose_file:
        command = f"cd {DOCKER_COMPOSE_PATH} && docker compose -f {compose_file} ps"
        output, error, exit_status = execute_ssh_command(command)
        if exit_status == 0:
            print(output)
            return True
    
    # Если docker-compose не сработал, используем docker ps напрямую
    command = "docker ps --filter 'name=medhistory' --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
    output, error, exit_status = execute_ssh_command(command)
    if exit_status == 0:
        print(output)
        return True
    else:
        print(f"❌ Ошибка: {error}")
        return False

def get_container_logs(service=None, tail=100):
    """Получить логи контейнеров"""
    print("\n" + "="*70)
    if service:
        print(f"📋 Логи сервиса: {service}")
    else:
        print("📋 Логи всех сервисов")
    print("="*70)
    
    if service:
        command = f"cd {DOCKER_COMPOSE_PATH} && docker compose -f {DOCKER_COMPOSE_FILE} logs --tail={tail} {service}"
    else:
        command = f"cd {DOCKER_COMPOSE_PATH} && docker compose -f {DOCKER_COMPOSE_FILE} logs --tail={tail}"
    
    output, error, exit_status = execute_ssh_command(command)
    
    if exit_status == 0:
        print(output)
        if error:
            print(f"⚠️  Предупреждения:\n{error}")
        return True
    else:
        print(f"❌ Ошибка получения логов: {error}")
        return False

def get_container_names():
    """Получить имена запущенных контейнеров medhistory"""
    command = "docker ps --filter 'name=medhistory' --format '{{.Names}}'"
    output, error, exit_status = execute_ssh_command(command)
    
    if exit_status == 0 and output:
        containers = [name.strip() for name in output.strip().split('\n') if name.strip()]
        return containers
    return []

def get_startup_logs():
    """Получить логи запуска контейнеров (последние 200 строк для каждого сервиса)"""
    print("\n" + "="*70)
    print("🚀 Логи запуска контейнеров (последние 200 строк)")
    print("="*70)
    
    # Сначала попробовать через docker-compose
    compose_file = find_docker_compose_file()
    if compose_file:
        services = ['backend', 'frontend', 'postgres', 'mongodb', 'minio', 'nginx']
        
        for service in services:
            print(f"\n{'='*70}")
            print(f"📦 Сервис: {service}")
            print(f"{'='*70}")
            
            command = f"cd {DOCKER_COMPOSE_PATH} && docker compose -f {compose_file} logs --tail=200 {service} 2>&1"
            output, error, exit_status = execute_ssh_command(command)
            
            if exit_status == 0 and output and output.strip():
                print(output)
            elif error and "no such service" not in error.lower():
                print(f"⚠️  {error}")
            else:
                # Если сервис не найден в compose, попробуем найти контейнер по имени
                container_name = f"medhistory-{service}-1"
                command = f"docker logs --tail=200 {container_name} 2>&1"
                output, error, exit_status = execute_ssh_command(command)
                if exit_status == 0 and output:
                    print(output)
                else:
                    print(f"ℹ️  Сервис {service} не найден")
    else:
        # Если compose файл не найден, используем имена контейнеров напрямую
        containers = get_container_names()
        
        if not containers:
            print("⚠️  Не найдено запущенных контейнеров medhistory")
            return
        
        for container in containers:
            print(f"\n{'='*70}")
            print(f"📦 Контейнер: {container}")
            print(f"{'='*70}")
            
            command = f"docker logs --tail=200 {container} 2>&1"
            output, error, exit_status = execute_ssh_command(command)
            
            if exit_status == 0 and output:
                print(output)
            else:
                print(f"⚠️  Ошибка получения логов: {error or 'неизвестная ошибка'}")

def get_docker_ps():
    """Получить список всех Docker контейнеров"""
    print("\n" + "="*70)
    print("🐳 Все Docker контейнеры на сервере")
    print("="*70)
    
    command = "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
    output, error, exit_status = execute_ssh_command(command)
    
    if exit_status == 0:
        print(output)
    else:
        print(f"❌ Ошибка: {error}")

def get_recent_errors():
    """Получить последние ошибки из логов"""
    print("\n" + "="*70)
    print("🚨 Последние ошибки в логах контейнеров")
    print("="*70)
    
    containers = get_container_names()
    
    for container in containers:
        # Получить последние строки с ERROR, FATAL, Exception
        command = f"docker logs --tail=100 {container} 2>&1 | grep -iE '(error|fatal|exception|failed|cannot|timeout)' | tail -10"
        output, error, exit_status = execute_ssh_command(command)
        
        if output and output.strip():
            print(f"\n{'='*70}")
            print(f"📦 {container}")
            print(f"{'='*70}")
            print(output)

def main():
    """Основная функция"""
    print("="*70)
    print("🔍 Проверка логов контейнеров на Production сервере")
    print("="*70)
    print(f"Сервер: {SSH_CONFIG['username']}@{SSH_CONFIG['host']}:{SSH_CONFIG['port']}")
    print(f"SSH ключ: {SSH_CONFIG['key_path']}")
    
    # Проверить SSH ключ
    if not check_ssh_key():
        sys.exit(1)
    
    # Проверить статус контейнеров
    check_containers_status()
    
    # Получить логи запуска
    get_startup_logs()
    
    # Показать все контейнеры
    get_docker_ps()
    
    # Проверить ошибки
    get_recent_errors()
    
    print("\n" + "="*70)
    print("✅ Проверка завершена")
    print("="*70)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
