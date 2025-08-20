
import threading
import time
from datetime import datetime
from src.utils.meeting_utils import check_and_move_finished_meetings
from src.utils.timezone_utils import get_brazil_now

class MeetingScheduler:
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start(self):
        """Inicia o scheduler em uma thread separada"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.thread.start()
            print("📅 Scheduler de reuniões iniciado!")
    
    def stop(self):
        """Para o scheduler"""
        self.running = False
        if self.thread:
            self.thread.join()
        print("📅 Scheduler de reuniões parado!")
    
    def _run_scheduler(self):
        """Executa o loop principal do scheduler"""
        while self.running:
            try:
                # Verificar reuniões finalizadas a cada 5 minutos (300 segundos)
                moved_count = check_and_move_finished_meetings()
                if moved_count > 0:
                    now = get_brazil_now()
                    print(f"🔄 [{now.strftime('%d/%m/%Y %H:%M:%S')}] {moved_count} reuniões movidas para finalizadas.")
                
                # Aguardar 5 minutos antes da próxima verificação
                time.sleep(300)
                
            except Exception as e:
                print(f"❌ Erro no scheduler de reuniões: {e}")
                # Aguardar 1 minuto em caso de erro antes de tentar novamente
                time.sleep(60)

# Instância global do scheduler
meeting_scheduler = MeetingScheduler()

def start_meeting_scheduler():
    """Função para iniciar o scheduler"""
    meeting_scheduler.start()

def stop_meeting_scheduler():
    """Função para parar o scheduler"""
    meeting_scheduler.stop()
