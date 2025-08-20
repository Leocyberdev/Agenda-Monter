from flask_mail import Message
from flask import current_app
from src.models.user import User
import logging

def send_email(subject, recipients, body, html_body=None):
    """
    Envia e-mail usando Flask-Mail

    Args:
        subject (str): Assunto do e-mail
        recipients (list): Lista de destinatários
        body (str): Corpo do e-mail em texto
        html_body (str, optional): Corpo do e-mail em HTML

    Returns:
        bool: True se enviado com sucesso, False caso contrário
    """
    try:
        from src.main import mail

        msg = Message(
            subject=subject,
            recipients=recipients,
            body=body,
            html=html_body
        )

        mail.send(msg)
        logging.info(f"E-mail enviado com sucesso para {len(recipients)} destinatário(s)")
        return True

    except Exception as e:
        logging.error(f"Erro ao enviar e-mail: {str(e)}")
        return False

def send_meeting_notification(meeting, action='created', custom_message=None, recipients=None):
    """
    Envia notificação de reunião para os participantes

    Args:
        meeting: Objeto Meeting
        action (str): Tipo de ação ('created', 'updated', 'cancelled')
        custom_message (str, optional): Mensagem personalizada
        recipients (list, optional): Lista de e-mails dos destinatários

    Returns:
        bool: True se enviado com sucesso, False caso contrário
    """
    try:
        if recipients is None or not recipients:
            logging.warning("Nenhum destinatário fornecido para notificação")
            return False

        # Garantir que start_datetime seja timezone-aware para formatação
        from src.utils.timezone_utils import ensure_timezone_aware
        start_dt = ensure_timezone_aware(meeting.start_datetime)
        end_dt = ensure_timezone_aware(meeting.end_datetime)

        if action == 'created':
            subject = f'Nova Reunião Agendada: {meeting.title}'
            body = custom_message or f"""
Uma nova reunião foi agendada:

Título: {meeting.title}
Data: {start_dt.strftime('%d/%m/%Y')}
Horário: {start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}
Local: {meeting.room.name}
Organizador: {meeting.creator.username}

{f'Descrição: {meeting.description}' if meeting.description else ''}

Sistema de Reuniões - Monter Elétrica
            """.strip()
        elif action == 'updated':
            subject = f'Reunião Atualizada: {meeting.title}'
            body = custom_message or f"""
A reunião foi atualizada:

Título: {meeting.title}
Data: {start_dt.strftime('%d/%m/%Y')}
Horário: {start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}
Local: {meeting.room.name}
Organizador: {meeting.creator.username}

{f'Descrição: {meeting.description}' if meeting.description else ''}

Sistema de Reuniões - Monter Elétrica
            """.strip()
        elif action == 'cancelled':
            subject = f'Reunião Cancelada: {meeting.title}'
            body = custom_message or f"""
A reunião foi cancelada:

Título: {meeting.title}
Data: {start_dt.strftime('%d/%m/%Y')}
Horário: {start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}
Local: {meeting.room.name}
Organizador: {meeting.creator.username}

Sistema de Reuniões - Monter Elétrica
            """.strip()
        else:
            subject = f'Notificação de Reunião: {meeting.title}'
            body = custom_message or f"Atualização sobre a reunião: {meeting.title}"

        return send_email(subject, recipients, body)

    except Exception as e:
        logging.error(f"Erro ao enviar notificação de reunião: {str(e)}")
        return False


from flask import url_for

def send_password_reset_email(user, token):
    reset_url = url_for("auth.reset_password", token=token, _external=True)
    subject = "Redefinição de Senha - Sistema de Reuniões"
    body = f"""
Olá {user.username},

Para redefinir sua senha, visite o seguinte link:
{reset_url}

Se você não solicitou uma redefinição de senha, por favor, ignore este e-mail.

Sistema de Reuniões - Monter Elétrica
    """.strip()
    send_email(subject, [user.email], body)


