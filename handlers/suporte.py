import logging
import smtplib
from email.message import EmailMessage
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, MessageHandler, filters, CallbackQueryHandler
from config import get_admin_telegram_id, get_support_email_credentials  # adicione no seu config.py

logger = logging.getLogger(__name__)

# Informações do projeto
CRIADOR = "Everton Camargo"
EMAIL_SUPORTE = "everttoncamargo@gmail.com"
VERSAO_BOT = "v0.02"

async def iniciar_suporte(update: Update, context: CallbackContext):
    """Exibe opções de suporte"""
    try:
        if update.callback_query:
            await update.callback_query.answer()
            message = update.callback_query.message
        else:
            message = update.message

        await message.reply_text(
            "🛠️ Como posso ajudar?\nEscolha uma opção abaixo:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🆘 Ajuda", callback_data="suporte_ajuda")],
                [InlineKeyboardButton("ℹ️ Sobre", callback_data="suporte_sobre")],
                [InlineKeyboardButton("🏠 Menu Principal", callback_data="menu_principal")]
            ])
        )
    except Exception as e:
        logger.error(f"Erro ao exibir opções de suporte: {str(e)}")

async def suporte_ajuda(update: Update, context: CallbackContext):
    """Inicia processo de ajuda"""
    await update.callback_query.answer()
    context.user_data['aguardando_ajuda'] = True
    await update.callback_query.message.reply_text(
        "✉️ Por favor, digite sua dúvida ou comentário.\n"
        "Você pode cancelar com /cancelar",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_suporte")]
        ])
    )

async def processar_ajuda(update: Update, context: CallbackContext):
    """Processa a dúvida e envia por Telegram e e-mail"""
    if not context.user_data.get('aguardando_ajuda'):
        return

    try:
        user = update.message.from_user
        mensagem = update.message.text
        admin_id = int(get_admin_telegram_id())
        remetente = f"{user.full_name} (@{user.username or 'sem_username'})"
        user_id = user.id

        # Envia para admin via Telegram
        await context.bot.send_message(
            chat_id=admin_id,
            text=(
                f"📩 NOVO PEDIDO DE AJUDA\n"
                f"👤 {remetente}\n"
                f"🆔 ID: {user_id}\n\n"
                f"💬 {mensagem}"
            )
        )

        # Envia por e-mail
        enviar_email_suporte(remetente, user_id, mensagem)

        await update.message.reply_text(
            "✅ Sua mensagem foi enviada!\nNossa equipe responderá em breve.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Menu Principal", callback_data="menu_principal")]
            ])
        )
        context.user_data.pop('aguardando_ajuda', None)

    except Exception as e:
        logger.error(f"Erro ao processar ajuda: {str(e)}")
        await update.message.reply_text("⚠️ Erro ao enviar sua mensagem.")

def enviar_email_suporte(remetente: str, user_id: int, mensagem: str):
    """Envia a dúvida por e-mail"""
    try:
        email_user, email_pass = get_support_email_credentials()

        msg = EmailMessage()
        msg["Subject"] = "📩 Nova mensagem de suporte (Bot Telegram)"
        msg["From"] = email_user
        msg["To"] = EMAIL_SUPORTE
        msg.set_content(
            f"Remetente: {remetente}\n"
            f"ID do usuário: {user_id}\n\n"
            f"Mensagem:\n{mensagem}"
        )

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(email_user, email_pass)
            smtp.send_message(msg)

    except Exception as e:
        logger.error(f"Erro ao enviar e-mail de suporte: {str(e)}")

async def suporte_sobre(update: Update, context: CallbackContext):
    """Mostra informações sobre o projeto"""
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        f"ℹ️ *Sobre o Projeto*\n\n"
        f"*Criador:* {CRIADOR}\n"
        f"*E-mail:* {EMAIL_SUPORTE}\n"
        f"*Versão do Bot:* {VERSAO_BOT}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Menu Principal", callback_data="menu_principal")]
        ])
    )

async def cancelar_suporte(update: Update, context: CallbackContext):
    """Cancela o envio de ajuda"""
    context.user_data.pop('aguardando_ajuda', None)
    await update.callback_query.answer()
    await update.callback_query.message.edit_text(
        "❌ Solicitação de ajuda cancelada.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Menu Principal", callback_data="menu_principal")]
        ])
    )

def get_suporte_handlers():
    """Registra os handlers no main.py"""
    return [
        CallbackQueryHandler(iniciar_suporte, pattern="^iniciar_suporte$"),
        CallbackQueryHandler(suporte_ajuda, pattern="^suporte_ajuda$"),
        CallbackQueryHandler(suporte_sobre, pattern="^suporte_sobre$"),
        CallbackQueryHandler(cancelar_suporte, pattern="^cancelar_suporte$"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, processar_ajuda),
    ]
