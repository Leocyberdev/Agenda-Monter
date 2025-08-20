from datetime import datetime
from src.models.meeting import Meeting
from src.models.finished_meeting import FinishedMeeting
from src.models.user import db
from src.utils.timezone_utils import get_brazil_now

def move_meeting_to_finished(meeting):
    """
    Move uma reunião específica para a tabela de reuniões finalizadas
    Se for reunião mãe recorrente, promove a próxima filha como nova mãe
    """
    try:
        # Criar registro na tabela de reuniões finalizadas
        print(f"DEBUG: Movendo reunião {meeting.id} - {meeting.title} para finalizadas.")
        finished_meeting = FinishedMeeting(
            original_meeting_id=meeting.id,
            title=meeting.title,
            description=meeting.description,
            start_datetime=meeting.start_datetime,
            end_datetime=meeting.end_datetime,
            created_by=meeting.created_by,
            room_id=meeting.room_id,
            participants=meeting.participants,
            was_recurring=meeting.is_recurring,
            recurrence_type=meeting.recurrence_type,
            created_at=meeting.created_at,
            finished_at=get_brazil_now()
        )
        
        db.session.add(finished_meeting)
        
        # Se for uma reunião mãe recorrente, promover a próxima filha como nova mãe
        if meeting.is_recurring and not meeting.parent_meeting_id:
            print(f"DEBUG: Reunião mãe recorrente sendo removida. Buscando próxima reunião filha...")
            
            # Buscar a próxima reunião filha (a mais próxima no tempo)
            next_child = Meeting.query.filter(
                Meeting.parent_meeting_id == meeting.id
            ).order_by(Meeting.start_datetime.asc()).first()
            
            if next_child:
                print(f"DEBUG: Promovendo reunião filha {next_child.id} como nova mãe da série")
                
                # Buscar todas as outras filhas que vão passar a ser filhas da nova mãe
                other_children = Meeting.query.filter(
                    Meeting.parent_meeting_id == meeting.id,
                    Meeting.id != next_child.id
                ).all()
                
                # Transformar a próxima filha em reunião mãe
                next_child.is_recurring = True
                next_child.recurrence_type = meeting.recurrence_type
                next_child.recurrence_end = meeting.recurrence_end
                next_child.parent_meeting_id = None  # Remove o parent para se tornar mãe
                
                # Atualizar todas as outras filhas para apontarem para a nova mãe
                for child in other_children:
                    child.parent_meeting_id = next_child.id
                
                print(f"DEBUG: Nova reunião mãe: {next_child.id} - {next_child.title}")
                print(f"DEBUG: {len(other_children)} reuniões filhas agora apontam para a nova mãe")
            else:
                print(f"DEBUG: Não há reuniões filhas. Série recorrente será finalizada.")
        
        # Remover apenas a reunião específica
        db.session.delete(meeting)
        
        db.session.commit()
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao mover reunião para finalizadas: {e}")
        return False

def move_expired_meetings_to_finished():
    """
    Move apenas reuniões individuais expiradas para a tabela de reuniões finalizadas
    Não move reuniões filhas quando a mãe termina
    """
    now = get_brazil_now()
    
    # Buscar apenas reuniões que já terminaram individualmente
    expired_meetings = Meeting.query.filter(
        Meeting.end_datetime < now
    ).all()
    
    moved_count = 0
    for meeting in expired_meetings:
        # Verificar se é uma reunião mãe recorrente
        if meeting.is_recurring and not meeting.parent_meeting_id:
            # Se for reunião mãe recorrente, mover apenas ela, não as filhas
            print(f"DEBUG: Movendo apenas reunião mãe recorrente: {meeting.id} - {meeting.title}")
            if move_meeting_to_finished(meeting):
                moved_count += 1
        elif meeting.parent_meeting_id:
            # Se for reunião filha, mover normalmente
            print(f"DEBUG: Movendo reunião filha: {meeting.id} - {meeting.title}")
            if move_meeting_to_finished(meeting):
                moved_count += 1
        else:
            # Se for reunião normal (não recorrente), mover normalmente
            print(f"DEBUG: Movendo reunião normal: {meeting.id} - {meeting.title}")
            if move_meeting_to_finished(meeting):
                moved_count += 1
    
    return moved_count

def check_and_move_finished_meetings():
    """
    Verifica e move reuniões que acabaram de terminar
    Esta função pode ser chamada periodicamente
    """
    return move_expired_meetings_to_finished()

