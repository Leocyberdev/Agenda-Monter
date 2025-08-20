from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from src.models.user import db
from src.models.finished_meeting import FinishedMeeting
from src.utils.timezone_utils import get_brazil_now, ensure_timezone_aware

finished_meetings_bp = Blueprint("finished_meetings", __name__)

@finished_meetings_bp.route('/finished')
@login_required
def finished_meetings():
    """Página para visualizar reuniões finalizadas"""
    # Buscar reuniões finalizadas do usuário atual ou onde ele é participante
    finished_meetings = FinishedMeeting.query.filter(
        (FinishedMeeting.created_by == current_user.id) | 
        (FinishedMeeting.participants.like(f'%{current_user.username}%'))
    ).order_by(FinishedMeeting.finished_at.desc()).all()

    # Adicionar log de debug
    print(f"DEBUG: Página de Reuniões Finalizadas acessada por {current_user.username}")
    print(f"DEBUG: {len(finished_meetings)} reuniões finalizadas encontradas para {current_user.username}")
    for fm in finished_meetings:
        print(f"DEBUG:   - ID Original: {fm.original_meeting_id} | Título: {fm.title} | Finalizada em: {fm.finished_at}")

    # Garantir timezone correto
    for meeting in finished_meetings:
        meeting.start_datetime = ensure_timezone_aware(meeting.start_datetime)
        meeting.end_datetime = ensure_timezone_aware(meeting.end_datetime)
        meeting.finished_at = ensure_timezone_aware(meeting.finished_at)
        if meeting.created_at:
            meeting.created_at = ensure_timezone_aware(meeting.created_at)

    return render_template(
        'meetings/finished_meetings.html',
        finished_meetings=finished_meetings
    )

@finished_meetings_bp.route('/delete/<int:finished_meeting_id>', methods=['POST'])
@login_required
def delete_finished_meeting(finished_meeting_id):
    """Excluir uma reunião finalizada"""
    finished_meeting = FinishedMeeting.query.get_or_404(finished_meeting_id)
    
    # Verificar se o usuário tem permissão para excluir
    if finished_meeting.created_by != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para excluir esta reunião finalizada.', 'error')
        return redirect(url_for('finished_meetings.finished_meetings'))
    
    meeting_title = finished_meeting.title
    db.session.delete(finished_meeting)
    db.session.commit()
    
    flash(f'Reunião finalizada "{meeting_title}" foi excluída com sucesso!', 'success')
    return redirect(url_for('finished_meetings.finished_meetings'))

@finished_meetings_bp.route('/delete_all', methods=['POST'])
@login_required
def delete_all_finished_meetings():
    """Excluir todas as reuniões finalizadas do usuário"""
    if current_user.is_admin:
        # Admin pode excluir todas as reuniões finalizadas
        count = FinishedMeeting.query.count()
        FinishedMeeting.query.delete()
    else:
        # Usuário comum só pode excluir suas próprias reuniões finalizadas
        count = FinishedMeeting.query.filter(
            (FinishedMeeting.created_by == current_user.id) | 
            (FinishedMeeting.participants.like(f'%{current_user.username}%'))
        ).count()
        FinishedMeeting.query.filter(
            (FinishedMeeting.created_by == current_user.id) | 
            (FinishedMeeting.participants.like(f'%{current_user.username}%'))
        ).delete(synchronize_session=False)
    
    db.session.commit()
    
    flash(f'{count} reuniões finalizadas foram excluídas com sucesso!', 'success')
    return redirect(url_for('finished_meetings.finished_meetings'))

