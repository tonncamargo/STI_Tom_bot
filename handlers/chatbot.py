import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, MessageHandler, filters, CallbackQueryHandler
import openai
from config import get_openai_key
from telegram.helpers import escape_markdown

logger = logging.getLogger(__name__)
openai.api_key = get_openai_key()

class ChatbotState:
    def __init__(self):
        self.active_users = set()

chatbot_state = ChatbotState()

async def toggle_chatbot(update: Update, context: CallbackContext):
    """Ativa/desativa o modo chatbot"""
    user_id = update.effective_user.id
    
    if user_id in chatbot_state.active_users:
        chatbot_state.active_users.remove(user_id)
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            "🔴 Modo Chatbot desativado",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Menu Principal", callback_data="menu_principal")]
            ])
        )
    else:
        chatbot_state.active_users.add(user_id)
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            "💬 Modo Chatbot ativado! Envie suas perguntas matemáticas.\n"
            "Exemplos:\n- Como resolver equações?\n- Explique Pitágoras\n\n"
            "Use /sair para desativar.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔴 Sair do Chatbot", callback_data="sair_chatbot")]
            ])
        )

async def handle_chatbot_message(update: Update, context: CallbackContext):
    """Processa mensagens no modo chatbot"""
    if update.effective_user.id not in chatbot_state.active_users:
        return
        
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "system",
                "content": "Você é um tutor de matemática para ensino fundamental. Seja claro e use exemplos práticos."
            }, {
                "role": "user",
                "content": update.message.text
            }],
            temperature=0.7
        )
        
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔴 Sair do Chatbot", callback_data="sair_chatbot")]
        ])

        conteudo = response.choices[0].message.content
        conteudo_escapado = escape_markdown(conteudo, version=2)
        cabecalho = escape_markdown("🧠 *Resposta:*", version=2)

        await update.message.reply_text(
            f"{cabecalho}\n\n{conteudo_escapado}",
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Erro no chatbot: {str(e)}")
        await update.message.reply_text("⚠️ Ocorreu um erro ao processar sua pergunta.")

async def sair_chatbot(update: Update, context: CallbackContext):
    """Sai do modo chatbot"""
    user_id = update.effective_user.id
    if user_id in chatbot_state.active_users:
        chatbot_state.active_users.remove(user_id)
    
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "🔴 Você saiu do modo chatbot.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Menu Principal", callback_data="menu_principal")]
        ])
    )

def get_chatbot_handlers():
    """Retorna os handlers para registrar no main.py"""
    return [
        CallbackQueryHandler(toggle_chatbot, pattern="^modo_chatbot$"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chatbot_message),
        CallbackQueryHandler(sair_chatbot, pattern="^sair_chatbot$")
    ]
