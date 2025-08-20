#!/usr/bin/env python3
"""
Script de Reset do Administrador - AgendaMonter
Uso: python reset_admin.py
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.main import app
from src.models.user import User, db

def reset_admin():
    """Reset completo do usuário administrador"""
    with app.app_context():
        try:
            print("🔄 Iniciando reset do administrador...")
            
            # Busca admin existente
            existing_admin = User.query.filter_by(email='agendamontereletrica@gmail.com').first()
            if existing_admin:
                print(f"🗑️ Removendo admin existente: {existing_admin.username}")
                
                # Remove reuniões criadas pelo admin para evitar erro de integridade
                from src.models.meeting import Meeting
                meetings_to_delete = Meeting.query.filter_by(created_by=existing_admin.id).all()
                for meeting in meetings_to_delete:
                    print(f"   Removendo reunião: {meeting.title}")
                    db.session.delete(meeting)
                
                # Remove o admin
                db.session.delete(existing_admin)
                db.session.commit()

            # Cria novo admin
            new_admin = User(
                username='Monter',
                email='agendamontereletrica@gmail.com',
                is_admin=True
            )
            new_admin.set_password('102030')
            db.session.add(new_admin)
            db.session.commit()

            print("✅ Administrador resetado com sucesso!")
            print("📋 Credenciais:")
            print("   Usuário: Monter")
            print("   Email: agendamontereletrica@gmail.com")
            print("   Senha: 102030")
            print("⚠️ IMPORTANTE: Altere a senha após o primeiro login!")

        except Exception as e:
            print(f"❌ Erro no reset: {str(e)}")
            db.session.rollback()
            return False
        
        return True

if __name__ == '__main__':
    success = reset_admin()
    sys.exit(0 if success else 1)

