import logging
import openai
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackContext,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from database.database import Session, Usuario
from handlers import (
    iniciar_teste, processar_resposta,
    iniciar_exercicios, processar_exercicio, explicar_exercicio,
    toggle_chatbot, sair_chatbot, handle_chatbot_message,
    ver_progresso, selecionar_categoria_exercicio,
    ver_ranking, selecionar_ranking_categoria,
    exibir_ranking_categoria, exibir_ranking_geral,
    iniciar_suporte, suporte_ajuda, suporte_sobre, cancelar_suporte, processar_ajuda
)
from config import get_telegram_token, configure_logging, get_openai_key

openai.api_key = get_openai_key()
configure_logging()
logger = logging.getLogger(__name__)

class FiltroModoChatbot(filters.MessageFilter):
    def filter(self, message):
        context = self.data if hasattr(self, 'data') else None
        if context:
            return context.user_data.get('modo_chatbot', False)
        return False

async def start(update: Update, context: CallbackContext):
    try:
        if update.callback_query:
            await update.callback_query.answer()
            message = update.callback_query.message
            if "chat_history" in context.user_data:
                del context.user_data["chat_history"]
        else:
            message = update.message

        with Session() as session:
            user = update.effective_user
            usuario = session.query(Usuario).filter_by(telegram_id=user.id).first()

            if not usuario:
                usuario = Usuario(
                    telegram_id=user.id,
                    nome=user.first_name,
                    nivel="iniciante"
                )
                session.add(usuario)
                session.commit()
                logger.info(f"Novo usuário registrado: ID {user.id} - {user.first_name}")

            teclado = [
                [InlineKeyboardButton("📝 Teste de Nivelamento", callback_data="iniciar_teste")],
                [InlineKeyboardButton("💬 Modo Chatbot", callback_data="modo_chatbot")],
                [InlineKeyboardButton("📚 Exercícios Dirigidos", callback_data="iniciar_exercicios")],
                [
                    InlineKeyboardButton("📊 Meu Progresso", callback_data="ver_progresso"),
                    InlineKeyboardButton("🏆 Ranking Global", callback_data="ver_ranking")
                ],
                [InlineKeyboardButton("🆘 Suporte", callback_data="iniciar_suporte")]
            ]

            await message.reply_text(
                f"👋 Olá {usuario.nome}! Sou o Tom, seu tutor de matemática. Escolha uma opção:",
                reply_markup=InlineKeyboardMarkup(teclado)
            )

    except Exception as e:
        logger.error(f"Erro no /start: {str(e)}")

def main():
    app = Application.builder().token(get_telegram_token()).build()

    # Crie o filtro e passe o contexto
    filtro_chatbot = FiltroModoChatbot()

    # 1. Handler do chatbot (mensagens no modo Chatbot)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filtro_chatbot,
        handle_chatbot_message
    ))

    # 2. Handler das mensagens de ajuda (quando o usuário escreve após clicar em "🆘 Ajuda")
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        processar_ajuda
    ))

    # 3. Handlers gerais
    app.add_handlers([
        CommandHandler("start", start),
        CallbackQueryHandler(start, pattern="^menu_principal$"),
        CallbackQueryHandler(iniciar_teste, pattern="^iniciar_teste$"),
        CallbackQueryHandler(processar_resposta, pattern="^(A|B|C|D)$"),
        CallbackQueryHandler(toggle_chatbot, pattern="^modo_chatbot$"),
        CallbackQueryHandler(sair_chatbot, pattern="^sair_chatbot$"),
        CallbackQueryHandler(iniciar_exercicios, pattern="^iniciar_exercicios$"),
        CallbackQueryHandler(processar_exercicio, pattern="^EXERC_"),
        CallbackQueryHandler(explicar_exercicio, pattern="^EXPLICAR_"),
        CallbackQueryHandler(ver_progresso, pattern="^ver_progresso$"),
        CallbackQueryHandler(selecionar_categoria_exercicio, pattern="^CATEGORIA_"),
        CallbackQueryHandler(ver_ranking, pattern="^ver_ranking$"),
        CallbackQueryHandler(selecionar_ranking_categoria, pattern="^RANKING_categorias$"),
        CallbackQueryHandler(exibir_ranking_categoria, pattern=r"^RANKING_\d+$"),
        CallbackQueryHandler(exibir_ranking_geral, pattern="^RANKING_geral$"),

        # Suporte
        CallbackQueryHandler(iniciar_suporte, pattern="^iniciar_suporte$"),
        CallbackQueryHandler(suporte_ajuda, pattern="^suporte_ajuda$"),
        CallbackQueryHandler(suporte_sobre, pattern="^suporte_sobre$"),
        CallbackQueryHandler(cancelar_suporte, pattern="^cancelar_suporte$"),
    ])

    logger.info("✅ Bot inicializado com sucesso")
    app.run_polling()

if __name__ == "__main__":
    main()
