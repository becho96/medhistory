#!/usr/bin/env python3
"""Показывает канонические названия анализов в продакшн БД"""

import os
import sys
import asyncio
from pathlib import Path
import subprocess
import time
import signal
import asyncpg
from dotenv import load_dotenv

class SSHTunnel:
    def __init__(self, ssh_host, ssh_user, remote_port, local_port):
        self.ssh_host = ssh_host
        self.ssh_user = ssh_user
        self.remote_port = remote_port
        self.local_port = local_port
        self.process = None
    
    def start(self):
        cmd = ['ssh', '-N', '-L', f'{self.local_port}:localhost:{self.remote_port}',
               f'{self.ssh_user}@{self.ssh_host}', '-o', 'StrictHostKeyChecking=no']
        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(2)
    
    def stop(self):
        if self.process:
            self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(timeout=5)
            except:
                self.process.kill()

async def main():
    project_root = Path(__file__).parent.parent
    load_dotenv(project_root / '.env.production')
    
    tunnel = SSHTunnel('158.160.99.232', 'yc-user', 5432, 15432)
    
    try:
        tunnel.start()
        
        user = os.getenv('POSTGRES_USER')
        password = os.getenv('POSTGRES_PASSWORD')
        db = os.getenv('POSTGRES_DB', 'medhistory')
        url = f"postgresql://{user}:{password}@localhost:15432/{db}"
        
        conn = await asyncpg.connect(url)
        
        rows = await conn.fetch("""
            SELECT a.canonical_name, c.name as category
            FROM analyte_standards a
            JOIN analyte_categories c ON c.id = a.category_id
            WHERE a.is_active = TRUE
            ORDER BY c.sort_order, a.sort_order
        """)
        
        print("\n📋 Канонические названия в продакшн БД:\n")
        
        current_category = None
        for row in rows:
            category = row['category']
            name = row['canonical_name']
            
            if category != current_category:
                print(f"\n{category}:")
                current_category = category
            
            print(f"  • {name}")
        
        await conn.close()
        
    finally:
        tunnel.stop()

if __name__ == "__main__":
    asyncio.run(main())
