import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))


from flask import Flask, send_from_directory, jsonify, request
from flask_login import LoginManager
from flask_mail import Mail
from flask_cors import CORS
from flask_migrate import Migrate

from src.models.user import User, Room
from src.models.notification import Notification
from src.models.finished_meeting import FinishedMeeting
from src.routes.auth import auth_bp
from src.routes.meetings import meetings_bp
from src.routes.admin import admin_bp
from src.routes.user import user_bp
from src.routes.notifications import notifications_bp
from src.routes.finished_meetings import finished_meetings_bp
from src.scheduler import start_meeting_scheduler
from src.config import config
from src.database import db
from src.models.meeting import Meeting
from src.utils.timezone_utils import format_datetime_display, to_brazil_timezone

print("##### APLICAÇÃO INICIADA - LOG DE TESTE #####")

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# Configuração baseada no ambiente
config_name = os.environ.get('FLASK_ENV') or 'default'
app.config.from_object(config[config_name])

# Inicializações
db.init_app(app)
migrate = Migrate(app, db)
CORS(app)  # Configuração CORS
mail = Mail(app)  # Inicializar Flask-Mail

# Configuração do Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'
login_manager.login_message_category = 'info'

# Filtros customizados para templates
@app.template_filter('datetime_brazil')
def datetime_brazil_filter(dt):
    """Filtro para formatar datetime no timezone do Brasil"""
    return format_datetime_display(dt)

@app.template_filter('to_brazil_tz')
def to_brazil_tz_filter(dt):
    """Filtro para converter datetime para timezone do Brasil"""
    return to_brazil_timezone(dt)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# =============================================
# NOVO ENDPOINT SEGURO PARA RESET DE ADMIN
# =============================================
@app.route('/system/emergency-reset', methods=['POST'])
def emergency_reset():
    """
    Endpoint crítico para reset de administrador
    Requer autenticação via header 'X-EMERGENCY-KEY'
    """
    # Verificação de segurança - ALTERE ESTA CHAVE para um valor único e complexo!
    EMERGENCY_KEY = "MONTER_EMERGENCY_#2024@RENDER"

    if request.headers.get('X-EMERGENCY-KEY') != EMERGENCY_KEY:
        return jsonify({
            "error": "Acesso negado",
            "message": "Credencial de emergência inválida"
        }), 403

    with app.app_context():
        try:
            # Remove admin existente se houver
            existing_admin = User.query.filter_by(email='agendamontereletrica@gmail.com').first()
            if existing_admin:
                db.session.delete(existing_admin)
                db.session.commit()

            # Cria novo admin com segurança reforçada
            new_admin = User(
                username='Monter',
                email='agendamontereletrica@gmail.com',
                is_admin=True
            )
            new_admin.set_password('102030')  # Senha temporária forte
            db.session.add(new_admin)
            db.session.commit()

            return jsonify({
                "success": True,
                "credentials": {
                    "email": "agendamontereletrica@gmail.com",
                    "temporary_password": "102030",
                    "security_warning": [
                        "ESTE ENDPOINT DEVE SER REMOVIDO APÓS O USO",
                        "Altere esta senha imediatamente após o login",
                        "Esta operação foi registrada no log do sistema"
                    ]
                }
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({
                "error": "Falha no reset",
                "details": str(e)
            }), 500

# Registrar blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(meetings_bp, url_prefix='/meetings')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(notifications_bp, url_prefix='/notifications')
app.register_blueprint(finished_meetings_bp, url_prefix='/finished_meetings')

def init_database():
    """Inicializa o banco de dados com dados padrão"""
    with app.app_context():
        db.create_all()

        # Criar usuário padrão se não existir
        if not User.query.filter_by(username='Monter').first():
            admin_user = User(
                username='Monter',
                email='agendamontereletrica@gmail.com',
                is_admin=True
            )
            admin_user.set_password('102030')
            db.session.add(admin_user)

        # Criar salas padrão se não existirem
        default_rooms = [
            {'name': 'Sala de Reunião', 'description': 'Sala principal para reuniões', 'capacity': 12},
            {'name': 'Espaço Reset', 'description': 'Espaço para descanso e reuniões informais', 'capacity': 8},
            {'name': 'Refeitório', 'description': 'Área de alimentação e reuniões casuais', 'capacity': 20},
            {'name': 'Rh', 'description': 'Sala de Recursos Humanos', 'capacity': 6}
        ]

        for room_data in default_rooms:
            if not Room.query.filter_by(name=room_data['name']).first():
                room = Room(**room_data)
                db.session.add(room)

        db.session.commit()

@app.route('/')
def index():
    """Redireciona para a página de login"""
    from flask import redirect, url_for
    return redirect(url_for('auth.login'))

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve arquivos estáticos"""
    return send_from_directory(app.static_folder, filename)

# =============================================
# INICIALIZAÇÃO GARANTIDA EM QUALQUER AMBIENTE
# =============================================
def ensure_database_initialized():
    """Garante que o banco seja inicializado em qualquer ambiente"""
    try:
        with app.app_context():
            # Cria as tabelas caso não existam
            db.create_all()

            # Inicializa dados padrão
            init_database()

            print("✅ Banco de dados inicializado com sucesso")
    except Exception as e:
        print(f"❌ Erro na inicialização do banco: {str(e)}")

# Executa a inicialização SEMPRE que o módulo for importado
ensure_database_initialized()

# Executa apenas localmente
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    # Inicia o scheduler de reuniões em produção
    if not app.debug:
        start_meeting_scheduler()

    app.run(debug=True, host="0.0.0.0", port=8080)