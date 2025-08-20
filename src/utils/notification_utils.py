from src.models.user import User
from src.models.notification import Notification, db
import logging

def create_meeting_notifications(meeting, action='created', participants_only=True):
    """
    Cria notificações para os participantes de uma reunião
    
    Args:
        meeting: Objeto Meeting
        action (str): Tipo de ação ('created', 'updated', 'cancelled')
        participants_only (bool): Se True, notifica apenas participantes. Se False, notifica todos os usuários.
    
    Returns:
        int: Número de notificações criadas
    """
    try:
        notifications_created = 0
        
        if participants_only and meeting.participants:
            # Buscar usuários participantes
            participant_names = meeting.get_participants_list()
            users = User.query.filter(User.username.in_(participant_names)).all()
        else:
            # Buscar todos os usuários
            users = User.query.all()
        
        # Definir título e mensagem baseado na ação
        if action == 'created':
            title = f'Nova reunião: {meeting.title}'
            # Garantir que start_datetime seja timezone-aware para formatação
            from src.utils.timezone_utils import ensure_timezone_aware
            start_dt = ensure_timezone_aware(meeting.start_datetime)
            message = f'Você foi convidado para a reunião "{meeting.title}" na sala {meeting.room.name} em {start_dt.strftime("%d/%m/%Y às %H:%M")}.'
            notification_type = 'meeting_created'
        elif action == 'updated':
            title = f'Reunião atualizada: {meeting.title}'
            message = f'A reunião "{meeting.title}" foi atualizada. Verifique os novos detalhes.'
            notification_type = 'meeting_updated'
        elif action == 'cancelled':
            title = f'Reunião cancelada: {meeting.title}'
            message = f'A reunião "{meeting.title}" foi cancelada.'
            notification_type = 'meeting_cancelled'
        else:
            title = f'Reunião: {meeting.title}'
            message = f'Há uma atualização sobre a reunião "{meeting.title}".'
            notification_type = 'meeting_updated'
        
        # Criar notificações para cada usuário
        for user in users:
            # Não criar notificação para o próprio criador da reunião
            if user.id != meeting.created_by:
                notification = Notification(
                    user_id=user.id,
                    meeting_id=meeting.id,
                    title=title,
                    message=message,
                    notification_type=notification_type
                )
                db.session.add(notification)
                notifications_created += 1
        
        db.session.commit()
        logging.info(f"{notifications_created} notificações criadas para a reunião {meeting.title}")
        return notifications_created
        
    except Exception as e:
        logging.error(f"Erro ao criar notificações: {str(e)}")
        db.session.rollback()
        return 0

def get_user_notifications(user_id, unread_only=False, limit=10):
    """
    Busca notificações de um usuário
    
    Args:
        user_id (int): ID do usuário
        unread_only (bool): Se True, retorna apenas não lidas
        limit (int): Limite de notificações
    
    Returns:
        list: Lista de notificações
    """
    try:
        query = Notification.query.filter_by(user_id=user_id)
        
        if unread_only:
            query = query.filter_by(is_read=False)
        
        notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
        return notifications
        
    except Exception as e:
        logging.error(f"Erro ao buscar notificações: {str(e)}")
        return []

def mark_notification_as_read(notification_id, user_id):
    """
    Marca uma notificação como lida
    
    Args:
        notification_id (int): ID da notificação
        user_id (int): ID do usuário (para verificação de segurança)
    
    Returns:
        bool: True se marcada com sucesso, False caso contrário
    """
    try:
        notification = Notification.query.filter_by(
            id=notification_id, 
            user_id=user_id
        ).first()
        
        if notification:
            notification.is_read = True
            db.session.commit()
            return True
        
        return False
        
    except Exception as e:
        logging.error(f"Erro ao marcar notificação como lida: {str(e)}")
        return False

def get_unread_count(user_id):
    """
    Retorna o número de notificações não lidas de um usuário
    
    Args:
        user_id (int): ID do usuário
    
    Returns:
        int: Número de notificações não lidas
    """
    try:
        count = Notification.query.filter_by(
            user_id=user_id, 
            is_read=False
        ).count()
        return count
        
    except Exception as e:
        logging.error(f"Erro ao contar notificações não lidas: {str(e)}")
        return 0

