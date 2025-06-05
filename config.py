"""
Módulo: config.py

Este módulo armazena as configurações essenciais do projeto, incluindo:
- Chaves de API para a OpenAI e Telegram.
- Configuração de logs para depuração e suporte.

Recomendações de Segurança:
- **NÃO ARMAZENAR CHAVES DIRETAMENTE NO CÓDIGO!**
- Utilize variáveis de ambiente ou métodos seguros para gerenciamento de credenciais.

"""
import os
import logging
from logging.handlers import RotatingFileHandler

# Recupera as chaves da API de variáveis de ambiente
OPENAI_KEY = os.getenv("OPENAI_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "SEU_TOKEN_AQUI")
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID", "SEU_ID_AQUI")

# Funções para obter as chaves

def get_openai_key():
    """Retorna a chave da API da OpenAI."""
    return OPENAI_KEY

def get_telegram_token():
    """Retorna o token do bot do Telegram."""
    return TELEGRAM_TOKEN

def get_admin_telegram_id():
    """Retorna o ID do administrador no Telegram."""
    return ADMIN_TELEGRAM_ID

# Configurações de Log
LOG_FILE = "logs/bot.log"
SUPPORT_LOG_FILE = "logs/suporte.log"
LOG_LEVEL = "INFO"

def configure_logging():
    """
    Configura o sistema de logs para registrar atividades do bot.
    - Usa arquivos rotativos para limitar o tamanho do log.
    - Registra eventos em um arquivo principal e em um específico para suporte.
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    os.makedirs("logs", exist_ok=True)  # <- Adicione esta linha

    logging.basicConfig(
        level=LOG_LEVEL,
        format=log_format,
        handlers=[
            RotatingFileHandler(LOG_FILE, maxBytes=1e6, backupCount=3),
            logging.StreamHandler()
        ]
    )
    
    # Logger específico para suporte
    support_logger = logging.getLogger("SUPPORT_LOGGER")
    support_logger.setLevel(LOG_LEVEL)
    handler = RotatingFileHandler(SUPPORT_LOG_FILE, maxBytes=1e6, backupCount=3)
    handler.setFormatter(logging.Formatter(log_format))
    support_logger.addHandler(handler)
    support_logger.propagate = False

def get_support_email_credentials():
    return ("everttoncamargo@gmail.com", "ndks qpyq tgyr nbud")  # Use App Password
