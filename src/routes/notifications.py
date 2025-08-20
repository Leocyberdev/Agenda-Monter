from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from src.utils.notification_utils import get_user_notifications, mark_notification_as_read, get_unread_count

notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route('/api/notifications')
@login_required
def api_notifications():
    """API para buscar notificações do usuário"""
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    limit = int(request.args.get('limit', 10))
    
    notifications = get_user_notifications(current_user.id, unread_only=unread_only, limit=limit)
    unread_count = get_unread_count(current_user.id)
    
    return jsonify({
        'notifications': [notification.to_dict() for notification in notifications],
        'unread_count': unread_count
    })

@notifications_bp.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_as_read(notification_id):
    """API para marcar notificação como lida"""
    success = mark_notification_as_read(notification_id, current_user.id)
    
    if success:
        unread_count = get_unread_count(current_user.id)
        return jsonify({
            'success': True,
            'unread_count': unread_count
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Notificação não encontrada'
        }), 404

@notifications_bp.route('/api/notifications/unread-count')
@login_required
def api_unread_count():
    """API para buscar contagem de notificações não lidas"""
    unread_count = get_unread_count(current_user.id)
    return jsonify({'unread_count': unread_count})

