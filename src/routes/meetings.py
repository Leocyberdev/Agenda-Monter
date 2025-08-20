from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from src.utils.email_utils import send_meeting_notification
from src.utils.notification_utils import create_meeting_notifications, get_user_notifications, get_unread_count
from src.utils.timezone_utils import (
    make_timezone_aware, 
    is_in_past, 
    BRAZIL_TZ, 
    format_datetime_for_input, 
    parse_datetime_from_input,
    get_brazil_now,
    ensure_timezone_aware
)
from src.models.user import db, Room, User
from src.models.meeting import Meeting
from src.models.notification import Notification
from src.forms import MeetingForm, EditMeetingForm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from zoneinfo import ZoneInfo
import pytz
import json

meetings_bp = Blueprint("meetings", __name__)


def check_room_availability(room_id, start_datetime, end_datetime, exclude_meeting_id=None):
    print(f"🔍 Checando sala {room_id} de {start_datetime} até {end_datetime}")
    query = Meeting.query.filter(
        Meeting.room_id == room_id,
        Meeting.start_datetime < end_datetime,
        Meeting.end_datetime > start_datetime
    )
    if exclude_meeting_id:
        query = query.filter(Meeting.id != exclude_meeting_id)

    conflicts = query.all()
    for conflict in conflicts:
        print(f"⚠️ Conflito com {conflict.title} de {conflict.start_datetime} até {conflict.end_datetime}")

    return len(conflicts) == 0, conflicts


def check_user_availability(participant_ids, start_datetime, end_datetime, exclude_meeting_id=None):
    """Verifica se os usuários estão disponíveis no horário especificado"""
    if not participant_ids:
        return True, []
    
    # Buscar usuários pelos IDs
    users = User.query.filter(User.id.in_(participant_ids)).all()
    usernames = [user.username for user in users]
    
    # Verificar conflitos de reuniões para esses usuários
    query = Meeting.query.filter(
        Meeting.start_datetime < end_datetime,
        Meeting.end_datetime > start_datetime
    )
    
    if exclude_meeting_id:
        query = query.filter(Meeting.id != exclude_meeting_id)
    
    conflicting_meetings = query.all()
    
    conflicting_users = []
    for meeting in conflicting_meetings:
        if meeting.participants:
            meeting_participants = [user.username for user in meeting.get_participants_list()]
            for username in usernames:
                if username in meeting_participants and username not in conflicting_users:
                    conflicting_users.append(username)
    
    return len(conflicting_users) == 0, conflicting_users


# --- FUNÇÃO CORRIGIDA COM PYTZ ---
def create_recurring_meetings(base_meeting, fixed_start_time, fixed_end_time):
    if not base_meeting.is_recurring or not base_meeting.recurrence_type:
        return []

    if not base_meeting.recurrence_end:
        print("⚠️ Erro: recurrence_end está vazio para uma reunião recorrente.")
        return []

    created_meetings = []

    # Garantir que estamos trabalhando com timezone do Brasil
    brazil_tz = pytz.timezone('America/Sao_Paulo')
    
    # Converter para timezone do Brasil se necessário
    if base_meeting.start_datetime.tzinfo is None:
        base_start = brazil_tz.localize(base_meeting.start_datetime)
    else:
        base_start = base_meeting.start_datetime.astimezone(brazil_tz)
    
    current_date = base_start.date()
    start_hour, start_minute, start_second = fixed_start_time.hour, fixed_start_time.minute, fixed_start_time.second
    end_hour, end_minute, end_second = fixed_end_time.hour, fixed_end_time.minute, fixed_end_time.second

    try:
        # Garantir que a data de fim está no timezone correto
        if isinstance(base_meeting.recurrence_end, datetime):
            if base_meeting.recurrence_end.tzinfo is None:
                end_date = brazil_tz.localize(base_meeting.recurrence_end)
            else:
                end_date = base_meeting.recurrence_end.astimezone(brazil_tz)
        else:
            # Se for apenas uma data, combinar com horário mínimo
            end_date = brazil_tz.localize(datetime.combine(
                base_meeting.recurrence_end,
                datetime.min.time()
            ))
    except Exception as e:
        print(f"❌ Erro ao processar data de fim da recorrência: {e}")
        return []

    max_iterations = 100
    iteration_count = 0

    while iteration_count < max_iterations:
        iteration_count += 1

        try:
            if base_meeting.recurrence_type == 'daily':
                current_date += timedelta(days=1)
            elif base_meeting.recurrence_type == 'weekly':
                current_date += timedelta(weeks=1)
            elif base_meeting.recurrence_type == 'monthly':
                current_date += relativedelta(months=1)

            if current_date > end_date.date():
                break

            if base_meeting.recurrence_type == 'daily':
                if current_date.weekday() >= 5:  # pula sábado e domingo
                    continue

            # Criar datetime com timezone correto
            new_start_datetime = brazil_tz.localize(datetime(
                current_date.year, current_date.month, current_date.day,
                start_hour, start_minute, start_second
            ))
            new_end_datetime = brazil_tz.localize(datetime(
                current_date.year, current_date.month, current_date.day,
                end_hour, end_minute, end_second
            ))

            is_available, _ = check_room_availability(
                base_meeting.room_id, new_start_datetime, new_end_datetime
            )

            if is_available:
                new_meeting = Meeting(
                    title=base_meeting.title,
                    description=base_meeting.description,
                    start_datetime=new_start_datetime,
                    end_datetime=new_end_datetime,
                    participants=base_meeting.participants,
                    room_id=base_meeting.room_id,
                    created_by=base_meeting.created_by,
                    parent_meeting_id=base_meeting.id,
                    is_recurring=False,
                    created_at=get_brazil_now()
                )
                db.session.add(new_meeting)
                created_meetings.append(new_meeting)

        except Exception as e:
            print(f"❌ Erro ao criar reunião recorrente para {current_date}: {e}")
            continue

    print(f"📅 Criando reuniões recorrentes...")
    print(f"✅ Processadas {iteration_count} iterações, criadas {len(created_meetings)} reuniões")
    return created_meetings
# --- FIM DA FUNÇÃO CORRIGIDA ---


def format_datetime_brazil(dt):
    """Função auxiliar para formatar datetime com timezone do Brasil"""
    if dt is None:
        return ""
    
    brazil_tz = pytz.timezone('America/Sao_Paulo')
    
    # Garantir que o datetime tem timezone
    if dt.tzinfo is None:
        dt = brazil_tz.localize(dt)
    else:
        dt = dt.astimezone(brazil_tz)
    
    return dt


@meetings_bp.route('/dashboard')
@login_required
def dashboard():
    # Verificar e mover reuniões finalizadas automaticamente
    from src.utils.meeting_utils import check_and_move_finished_meetings
    try:
        moved_count = check_and_move_finished_meetings()
        if moved_count > 0:
            print(f"✅ {moved_count} reuniões foram automaticamente movidas para finalizadas.")
    except Exception as e:
        print(f"❌ Erro ao verificar reuniões finalizadas: {e}")
    
    now_brazil = get_brazil_now()

    upcoming_meetings_raw = Meeting.query.filter(
        Meeting.start_datetime >= now_brazil,
        (Meeting.created_by == current_user.id) | (Meeting.participants.like(f'%{current_user.username}%'))
    ).order_by(Meeting.start_datetime).limit(5).all()

    upcoming_meetings = []
    for meeting in upcoming_meetings_raw:
        meeting.start_datetime = format_datetime_brazil(meeting.start_datetime)
        meeting.end_datetime = format_datetime_brazil(meeting.end_datetime)
        upcoming_meetings.append(meeting)

    today = now_brazil.date()
    today_meetings_raw = Meeting.query.filter(
        db.func.date(Meeting.start_datetime) == today,
        (Meeting.created_by == current_user.id) | (Meeting.participants.like(f'%{current_user.username}%'))
    ).order_by(Meeting.start_datetime).all()

    today_meetings = []
    for meeting in today_meetings_raw:
        meeting.start_datetime = format_datetime_brazil(meeting.start_datetime)
        meeting.end_datetime = format_datetime_brazil(meeting.end_datetime)
        today_meetings.append(meeting)

    notifications = get_user_notifications(current_user.id, unread_only=False, limit=5)
    unread_count = get_unread_count(current_user.id)

    return render_template('meetings/dashboard.html',
                           upcoming_meetings=upcoming_meetings,
                           today_meetings=today_meetings,
                           notifications=notifications,
                           unread_count=unread_count)


@meetings_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_meeting():
    user = current_user
    form = MeetingForm()

    if form.validate_on_submit():
        # Guardar os horários originais do formulário antes de aplicar timezone
        original_start = form.start_datetime.data
        original_end = form.end_datetime.data

        start_time = make_timezone_aware(original_start, BRAZIL_TZ)
        end_time = make_timezone_aware(original_end, BRAZIL_TZ)
        room_id = form.room_id.data

        if is_in_past(start_time):
            flash("A data e hora de início não pode ser no passado.", "danger")
            return redirect(url_for("meetings.create_meeting"))

        if end_time <= start_time:
            flash("A data e hora de término deve ser depois da data e hora de início.", "danger")
            return redirect(url_for("meetings.create_meeting"))

        existing_meetings = Meeting.query.filter(
            Meeting.room_id == room_id,
            Meeting.start_datetime < end_time,
            Meeting.end_datetime > start_time
        ).all()

        if existing_meetings:
            flash("A sala selecionada não está disponível neste horário.", "danger")
            return redirect(url_for("meetings.create_meeting"))

        participant_ids = form.participants.data
        is_users_available, conflicting_users = check_user_availability(participant_ids, start_time, end_time)

        if not is_users_available:
            flash(f"Os seguintes usuários já possuem reuniões agendadas neste horário: {', '.join(conflicting_users)}.", "danger")
            return redirect(url_for("meetings.create_meeting"))

        new_meeting = Meeting(
            title=form.title.data,
            description=form.description.data,
            room_id=form.room_id.data,
            start_datetime=start_time,
            end_datetime=end_time,
            is_recurring=form.is_recurring.data,
            recurrence_type=form.recurrence_type.data if form.is_recurring.data else None,
            recurrence_end=form.recurrence_end.data if form.is_recurring.data else None,
            created_by=current_user.id,
            created_at=get_brazil_now()
        )

        participant_names = []
        for participant_id in form.participants.data:
            participant = User.query.get(participant_id)
            if participant:
                participant_names.append(participant.username)

        new_meeting.participants = ", ".join(participant_names) if participant_names else None

        db.session.add(new_meeting)
        db.session.commit()

        all_meetings = [new_meeting]

        if new_meeting.is_recurring:
            try:
                recurring_meetings = create_recurring_meetings(new_meeting, original_start.time(), original_end.time())
                if recurring_meetings:
                    db.session.commit()
                    all_meetings.extend(recurring_meetings)
                    print(f"✅ Criadas {len(recurring_meetings)} reuniões recorrentes")
            except Exception as e:
                print(f"❌ Erro ao criar reuniões recorrentes: {e}")
                db.session.rollback()
                db.session.commit()

        if participant_names:
            participant_emails = []
            for participant_id in form.participants.data:
                participant = User.query.get(participant_id)
                if participant and participant.email:
                    participant_emails.append(participant.email)

            if participant_emails:
                try:
                    # CORREÇÃO: Usar datetime com pytz ao invés de strftime
                    start_dt_brazil = format_datetime_brazil(new_meeting.start_datetime)
                    end_dt_brazil = format_datetime_brazil(new_meeting.end_datetime)
                    
                    if new_meeting.is_recurring:
                        recurrence_end_brazil = format_datetime_brazil(
                            datetime.combine(new_meeting.recurrence_end, datetime.min.time()) 
                            if isinstance(new_meeting.recurrence_end, type(datetime.now().date())) 
                            else new_meeting.recurrence_end
                        )
                        subject_suffix = f" (Recorrente até {recurrence_end_brazil.strftime('%d/%m/%Y')})"
                        body_suffix = f"Esta é uma reunião recorrente que se repete {new_meeting.recurrence_type} até {recurrence_end_brazil.strftime('%d/%m/%Y')}."
                    else:
                        subject_suffix = ""
                        body_suffix = ""

                    message_body = f"""
Uma nova reunião foi agendada:

Título: {new_meeting.title}{subject_suffix}
Data: {start_dt_brazil.strftime('%d/%m/%Y')}
Horário: {start_dt_brazil.strftime('%H:%M')} - {end_dt_brazil.strftime('%H:%M')}
Local: {new_meeting.room.name}
Organizador: {new_meeting.creator.username}

{f'Descrição: {new_meeting.description}' if new_meeting.description else ''}
{body_suffix}

Sistema de Reuniões - Monter Elétrica
                    """.strip()

                    send_meeting_notification(
                        new_meeting, 
                        action='created', 
                        recipients=participant_emails + [new_meeting.creator.email],
                        custom_message=message_body
                    )
                    create_meeting_notifications(new_meeting, 'created', participants_only=True)
                    print(f"✅ E-mail enviado para a reunião principal e notificações criadas.")
                except Exception as e:
                    print(f"❌ Erro ao enviar e-mails ou criar notificações: {e}")

        flash("Reunião agendada com sucesso!", "success")
        return redirect(url_for("meetings.dashboard"))

    users = User.query.all()
    rooms = Room.query.all()
    return render_template('meetings/create.html', user=user, rooms=rooms, form=form)


@meetings_bp.route('/my_meetings')
@login_required
def my_meetings():
    # Verificar e mover reuniões finalizadas automaticamente
    from src.utils.meeting_utils import check_and_move_finished_meetings
    try:
        moved_count = check_and_move_finished_meetings()
        if moved_count > 0:
            print(f"✅ {moved_count} reuniões foram automaticamente movidas para finalizadas.")
    except Exception as e:
        print(f"❌ Erro ao verificar reuniões finalizadas: {e}")
    
    my_meetings = Meeting.query.filter_by(
        created_by=current_user.id
    ).order_by(Meeting.created_at.desc(), Meeting.id.desc()).all()

    current_time = get_brazil_now()

    for meeting in my_meetings:
        meeting.start_datetime = ensure_timezone_aware(meeting.start_datetime)
        meeting.end_datetime = ensure_timezone_aware(meeting.end_datetime)
        if meeting.created_at:
            meeting.created_at = ensure_timezone_aware(meeting.created_at)

    return render_template(
        'meetings/my_meetings.html',
        meetings=my_meetings,
        current_time=current_time
    )


@meetings_bp.route('/calendar')
@login_required
def calendar():
    meetings = Meeting.query.order_by(Meeting.start_datetime).all()
    calendar_events = [{
        'id': m.id,
        'title': m.title,
        'start': m.start_datetime.isoformat(),
        'end': m.end_datetime.isoformat(),
        'room': m.room.name,
        'creator': m.creator.username
    } for m in meetings]

    return render_template('meetings/calendar.html', events=json.dumps(calendar_events))


@meetings_bp.route('/edit/<int:meeting_id>', methods=['GET', 'POST'])
@login_required
def edit_meeting(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    if meeting.created_by != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para editar esta reunião.', 'error')
        return redirect(url_for('meetings.my_meetings'))

    form = EditMeetingForm(obj=meeting)
    if form.validate_on_submit():
        start_time = make_timezone_aware(form.start_datetime.data, BRAZIL_TZ)
        end_time = make_timezone_aware(form.end_datetime.data, BRAZIL_TZ)

        is_available, conflicts = check_room_availability(
            form.room_id.data, start_time, end_time, exclude_meeting_id=meeting.id
        )
        if not is_available:
            # CORREÇÃO: Usar datetime com pytz ao invés de strftime
            conflict_info = []
            for c in conflicts:
                start_brazil = format_datetime_brazil(c.start_datetime)
                end_brazil = format_datetime_brazil(c.end_datetime)
                conflict_info.append(f"{c.title} ({start_brazil.strftime('%H:%M')} - {end_brazil.strftime('%H:%M')})")
            
            flash(f"Sala não disponível. Conflitos: {', '.join(conflict_info)}", "error")
            return render_template("meetings/edit.html", form=form, meeting=meeting)

        participant_ids = form.participants.data
        is_users_available, conflicting_users = check_user_availability(participant_ids, start_time, end_time, exclude_meeting_id=meeting.id)

        if not is_users_available:
            flash(f"Os seguintes usuários já possuem reuniões agendadas neste horário: {', '.join(conflicting_users)}.", "danger")
            return render_template("meetings/edit.html", form=form, meeting=meeting)

        participant_ids = form.participants.data
        selected_users = User.query.filter(User.id.in_(participant_ids)).all()
        participant_names = ", ".join([user.username for user in selected_users])
        
        # Armazenar os valores antigos antes de alterar
        old_start_datetime = meeting.start_datetime
        old_end_datetime = meeting.end_datetime

        meeting.title = form.title.data
        meeting.description = form.description.data
        meeting.start_datetime = start_time
        meeting.end_datetime = end_time
        meeting.participants = participant_names
        meeting.room_id = form.room_id.data
        meeting.updated_at = get_brazil_now()

        db.session.commit()

        # Se a reunião editada for uma reunião-mãe recorrente, verificar se deve atualizar as filhas
        if meeting.is_recurring and not meeting.parent_meeting_id:
            # Verificar se o usuário escolheu atualizar todas as reuniões recorrentes
            update_all_recurring = request.form.get('update_all_recurring') == 'true'
            
            if update_all_recurring:
                # Obter todas as reuniões filhas associadas a esta reunião-mãe
                child_meetings = Meeting.query.filter_by(parent_meeting_id=meeting.id).all()
                for child in child_meetings:
                    # Atualizar todas as reuniões filhas para o mesmo horário da mãe
                    child.start_datetime = start_time
                    child.end_datetime = end_time
                    child.title = meeting.title
                    child.description = meeting.description
                    child.room_id = meeting.room_id
                    child.participants = meeting.participants
                    
                db.session.commit()
                flash(f"Reunião \"{meeting.title}\" e todas as reuniões recorrentes foram atualizadas com sucesso!", "success")
            else:
                flash(f"Apenas a reunião principal \"{meeting.title}\" foi atualizada!", "success")
        else:
            flash(f"Reunião \"{meeting.title}\" atualizada com sucesso!", "success")
            
        return redirect(url_for("meetings.my_meetings"))

    return render_template("meetings/edit.html", form=form, meeting=meeting)


@meetings_bp.route("/delete/<int:meeting_id>", methods=["POST"])
@login_required
def delete_meeting(meeting_id):
    meeting = db.session.get(Meeting, meeting_id)
    if not meeting:
        abort(404)

    if meeting.created_by != current_user.id and not current_user.is_admin:
        flash("Você não tem permissão para deletar esta reunião.", "error")
        return redirect(url_for("meetings.my_meetings"))

    # Preparar dados para notificações antes de qualquer modificação
    recipients = [
        user.email
        for user in db.session.query(User).filter(User.username.in_(meeting.get_participants_list())).all()
        if user.email
    ]
    
    # Verificar se é uma reunião recorrente mãe e se deve cancelar todas as filhas
    delete_all_recurring = request.form.get('delete_all_recurring') == 'true'
    
    if meeting.is_recurring and not meeting.parent_meeting_id and delete_all_recurring:
        # Cancelar todas as reuniões filhas e a mãe
        child_meetings = db.session.query(Meeting).filter_by(parent_meeting_id=meeting.id).all()
        for child in child_meetings:
            db.session.delete(child)
        
        # Enviar notificações antes de deletar
        send_meeting_notification(meeting, "cancelled", recipients=recipients)
        create_meeting_notifications(meeting, "cancelled", participants_only=True)
        
        db.session.delete(meeting) # Deleta a reunião mãe também
        flash(f"Reunião \"{meeting.title}\" e todas as reuniões recorrentes foram canceladas com sucesso!", "success")
    elif meeting.is_recurring and not meeting.parent_meeting_id and not delete_all_recurring:
        # Se for uma reunião recorrente mãe mas não for para deletar todas, apenas desative a recorrência
        meeting.is_recurring = False
        meeting.recurrence_type = None
        meeting.recurrence_end = None
        
        # Enviar notificações antes de modificar
        send_meeting_notification(meeting, "cancelled", recipients=recipients)
        create_meeting_notifications(meeting, "cancelled", participants_only=True)
        
        db.session.add(meeting)
        flash('A reunião principal foi atualizada para não ser mais recorrente.', 'success')
    else:
        # Se não for uma reunião recorrente mãe, ou se for uma filha, delete-a normalmente
        # Enviar notificações antes de deletar
        send_meeting_notification(meeting, "cancelled", recipients=recipients)
        create_meeting_notifications(meeting, "cancelled", participants_only=True)
        
        db.session.delete(meeting)
        flash(f"Reunião \"{meeting.title}\" cancelada com sucesso!", "success")

    db.session.commit()

    return redirect(url_for("meetings.my_meetings"))


@meetings_bp.route('/api/check_availability')
@login_required
def check_availability():
    room_id = request.args.get('room_id', type=int)
    start_datetime = request.args.get('start_datetime')
    end_datetime = request.args.get('end_datetime')
    exclude_meeting_id = request.args.get('exclude_meeting_id', type=int)

    if not all([room_id, start_datetime, end_datetime]):
        return jsonify({'available': False, 'error': 'Parâmetros obrigatórios não fornecidos'})

    try:
        start_dt = parse_datetime_from_input(start_datetime)
        end_dt = parse_datetime_from_input(end_datetime)
        
        is_available, conflicts = check_room_availability(room_id, start_dt, end_dt, exclude_meeting_id)
        
        conflict_details = []
        for conflict in conflicts:
            conflict_details.append({
                'title': conflict.title,
                'start': conflict.start_datetime.strftime('%H:%M'),
                'end': conflict.end_datetime.strftime('%H:%M')
            })
        
        return jsonify({
            'available': is_available,
            'conflicts': conflict_details
        })
    except Exception as e:
        return jsonify({'available': False, 'error': str(e)})


@meetings_bp.route('/api/user_availability')
@login_required
def user_availability():
    participant_ids = request.args.getlist('participant_ids', type=int)
    start_datetime = request.args.get('start_datetime')
    end_datetime = request.args.get('end_datetime')
    exclude_meeting_id = request.args.get('exclude_meeting_id', type=int)

    if not all([participant_ids, start_datetime, end_datetime]):
        return jsonify({'available': False, 'error': 'Parâmetros obrigatórios não fornecidos'})

    try:
        start_dt = parse_datetime_from_input(start_datetime)
        end_dt = parse_datetime_from_input(end_datetime)
        
        is_available, conflicting_users = check_user_availability(participant_ids, start_dt, end_dt, exclude_meeting_id)
        
        return jsonify({
            'available': is_available,
            'conflicting_users': conflicting_users
        })
    except Exception as e:
        return jsonify({'available': False, 'error': str(e)})
