
from datetime import datetime, timezone
import pytz

# Timezone padrão do Brasil usando pytz
BRAZIL_TZ = pytz.timezone("America/Sao_Paulo")

def get_brazil_now():
    """Retorna o datetime atual no timezone do Brasil"""
    return datetime.now(BRAZIL_TZ)

def get_utc_now():
    """Retorna o datetime atual em UTC"""
    return datetime.now(timezone.utc)

def to_brazil_timezone(dt):
    """Converte um datetime para o timezone do Brasil"""
    if dt is None:
        return None
    
    if dt.tzinfo is None:
        # Se é naive, assume que está em UTC e converte para Brasil
        dt = pytz.utc.localize(dt)
    
    # Converte para o timezone do Brasil
    return dt.astimezone(BRAZIL_TZ)

def to_utc(dt):
    """Converte um datetime para UTC"""
    if dt is None:
        return None
    
    if dt.tzinfo is None:
        # Se é naive, assume que está no timezone do Brasil
        dt = BRAZIL_TZ.localize(dt)
    
    return dt.astimezone(timezone.utc)

def make_timezone_aware(dt, tz=None):
    """Torna um datetime naive em timezone-aware"""
    if dt is None:
        return None
    
    if tz is None:
        tz = BRAZIL_TZ
    
    if dt.tzinfo is None:
        return tz.localize(dt)
    
    return dt

def is_in_past(dt, reference_tz=None):
    """Verifica se um datetime está no passado considerando o timezone"""
    if dt is None:
        return False
    
    if reference_tz is None:
        reference_tz = BRAZIL_TZ
    
    # Garante que ambos os datetimes estão no mesmo timezone
    dt_aware = make_timezone_aware(dt, reference_tz)
    now_aware = datetime.now(reference_tz)
    
    return dt_aware < now_aware

def format_datetime_for_input(dt):
    """Formata datetime para input datetime-local HTML"""
    if dt is None:
        return ""
    
    # Converte para timezone do Brasil se necessário
    dt_brazil = to_brazil_timezone(dt)
    
    # Formato esperado pelo input datetime-local: YYYY-MM-DDTHH:MM
    return dt_brazil.strftime("%Y-%m-%dT%H:%M")

def ensure_timezone_aware(dt, tz=None):
    """Garante que um datetime seja timezone-aware, especialmente para dados do banco"""
    if dt is None:
        return None
    
    if tz is None:
        tz = BRAZIL_TZ
    
    if dt.tzinfo is None:
        # Se é naive (comum em dados do banco), assume timezone do Brasil
        return tz.localize(dt)
    
    return dt

def parse_datetime_from_input(dt_str):
    """Converte string do input datetime-local para datetime timezone-aware"""
    if not dt_str:
        return None
    
    try:
        # Parse da string no formato YYYY-MM-DDTHH:MM
        dt_naive = datetime.fromisoformat(dt_str)
        # Assume que está no timezone do Brasil
        return BRAZIL_TZ.localize(dt_naive)
    except ValueError:
        return None

def format_datetime_display(dt):
    """Formata datetime para exibição nas páginas (sempre em horário de São Paulo)"""
    if dt is None:
        return ""
    
    # Converte para timezone do Brasil
    dt_brazil = to_brazil_timezone(dt)
    
    # Retorna formatado para exibição
    return dt_brazil.strftime("%d/%m/%Y às %H:%M")
