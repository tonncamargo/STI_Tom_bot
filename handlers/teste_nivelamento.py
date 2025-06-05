import logging
from typing import Tuple
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
import openai
from database.database import Session, Usuario
from config import get_openai_key

logger = logging.getLogger(__name__)

NIVEIS_TESTOES = [
    "operações básicas", 
    "números inteiros", 
    "frações", 
    "porcentagem", 
    "equações"
]

def gerar_questao(nivel: str) -> Tuple[str, str]:
    try:
        prompt = (
            f"Crie uma questão de múltipla escolha sobre {nivel} para ensino fundamental.\n"
            "Formato exigido SEM MARKDOWN:\n"
            "Enunciado da questão\n"
            "A) Alternativa A\n"
            "B) Alternativa B\n"
            "C) Alternativa C\n"
            "D) Alternativa D\n"
            "Resposta correta: [APENAS A LETRA, ex: A]"
        )
        
        resposta = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
            timeout=15
        )
        
        questao_completa = resposta['choices'][0]['message']['content'].strip()
        resposta_correta = questao_completa.split("Resposta correta: ")[-1].strip()[0]
        questao = questao_completa.replace(f"Resposta correta: {resposta_correta}", "")
        
        return questao, resposta_correta.upper()
        
    except Exception as e:
        logger.error(f"Erro ao gerar questão: {str(e)}")
        return "🔴 Erro ao gerar questão. Tente novamente!", "A"

async def iniciar_teste(update: Update, context: CallbackContext) -> None:
    try:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        with Session() as session:
            usuario = session.query(Usuario).filter_by(telegram_id=user_id).first()
            
            if not usuario:
                await query.message.reply_text("🔍 Use /start antes de iniciar o teste.")
                return

            if usuario.teste_concluido:
                await query.message.reply_text("🎓 Você já completou o teste!")
                return

            usuario.progresso_teste = 0
            usuario.acertos_teste = 0
            session.commit()
            await enviar_questao(update, context, usuario)

    except Exception as e:
        logger.error(f"Erro ao iniciar teste: {str(e)}", exc_info=True)
        await update.effective_message.reply_text("⚠️ Falha ao iniciar o teste.")

async def enviar_questao(update: Update, context: CallbackContext, usuario: Usuario) -> None:
    try:
        nivel = NIVEIS_TESTOES[usuario.progresso_teste]
        questao, resposta_correta = gerar_questao(nivel)
        
        context.user_data["resposta_correta"] = resposta_correta
        
        botoes = [[InlineKeyboardButton(opcao, callback_data=opcao) for opcao in ["A", "B", "C", "D"]]]
        
        await update.callback_query.message.reply_text(
            f"📝 Questão {usuario.progresso_teste + 1}/5\n\n{questao}",
            reply_markup=InlineKeyboardMarkup(botoes)
        )

    except Exception as e:
        logger.error(f"Erro ao enviar questão: {str(e)}")
        await update.effective_message.reply_text("⚠️ Erro ao carregar questão.")

async def processar_resposta(update: Update, context: CallbackContext) -> None:
    try:
        query = update.callback_query
        await query.answer()
        resposta_usuario = query.data[0]
        resposta_correta = context.user_data.get("resposta_correta", "A")

        with Session() as session:
            usuario = session.query(Usuario).filter_by(telegram_id=query.from_user.id).first()
            
            if resposta_usuario.upper() == resposta_correta.upper():
                usuario.acertos_teste += 1
                feedback = "✅ *Correto!* Bom trabalho!"
            else:
                feedback = f"❌ *Incorreto.* Resposta correta: `{resposta_correta}`"
            
            await query.message.reply_text(
                feedback,
                parse_mode="MarkdownV2"
            )
            
            usuario.progresso_teste += 1
            
            if usuario.progresso_teste >= 5:
                await finalizar_teste(update, usuario)
            else:
                session.commit()
                await enviar_questao(update, context, usuario)

    except Exception as e:
        logger.error(f"Erro ao processar resposta: {str(e)}")
        await update.effective_message.reply_text("⚠️ Erro no processamento.")

async def finalizar_teste(update: Update, usuario: Usuario) -> None:
    try:
        with Session() as session:
            usuario = session.merge(usuario)
            niveis = ["iniciante", "básico", "intermediário", "avançado"]
            nivel = niveis[min(usuario.acertos_teste, len(niveis) - 1)]
            
            usuario.nivel = nivel
            usuario.teste_concluido = True
            session.commit()

            mensagem = (
                f"🏆 Teste Concluído!\n\n"
                f"✅ Acertos: {usuario.acertos_teste}/5\n"
                f"🎓 Seu nível: {nivel}"
            )
            
            botoes = [[InlineKeyboardButton("🏠 Início", callback_data="menu_principal")]]
            
            await update.callback_query.message.reply_text(
                mensagem,
                reply_markup=InlineKeyboardMarkup(botoes)
            )

    except Exception as e:
        logger.error(f"Erro ao finalizar teste: {str(e)}")
        await update.effective_message.reply_text("⚠️ Erro ao gerar resultados.")