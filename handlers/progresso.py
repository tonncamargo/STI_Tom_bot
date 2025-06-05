import logging
import os
import matplotlib.pyplot as plt
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
from database.database import Session, Usuario, Exercicio, RespostaExercicio
from sqlalchemy import func, cast, Integer

logger = logging.getLogger(__name__)

async def ver_progresso(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        
        with Session() as session:
            user = query.from_user
            usuario = session.query(Usuario).filter_by(telegram_id=user.id).first()
            
            mensagem = (
                f"🎓 *Nível Atual:* {usuario.nivel}\n"
                f"✅ *Acertos Totais:* {usuario.acertos_teste}\n"
                f"📈 *Nível de Dificuldade:* {usuario.nivel_dificuldade}/3\n"
            )
            
            resultados = session.query(
                Exercicio.tema,
                func.count(RespostaExercicio.id).label('total'),
                func.sum(cast(RespostaExercicio.acerto, Integer)).label('acertos')
            ).join(Exercicio)\
             .filter(RespostaExercicio.usuario_id == usuario.id)\
             .group_by(Exercicio.tema).all()
            
            temas = []
            acertos = []
            erros = []
            
            for tema, total, acerto in resultados:
                temas.append(tema)
                acertos.append(acerto)
                erros.append(total - acerto)
            
            if temas:
                plt.figure(figsize=(8, 6))
                sizes = [sum(acertos), sum(erros)]
                labels = ['Acertos', 'Erros']
                cores = ['#4CAF50', '#F44336']
                plt.pie(sizes, labels=labels, colors=cores, autopct='%1.1f%%', startangle=90)
                plt.axis('equal')
                plt.title('Desempenho Geral')

                folder_path = 'progressos'
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)

                chart_path = os.path.join(folder_path, f"progresso_{user.id}.png")
                plt.savefig(chart_path)
                plt.close()
                
                with open(chart_path, 'rb') as chart:
                    await query.message.reply_photo(
                        photo=chart,
                        caption=f"{mensagem}\n📋 *Conteúdos com mais acertos:* {max(temas, key=lambda x: acertos[temas.index(x)])}\n❌ *Conteúdos com mais erros:* {max(temas, key=lambda x: erros[temas.index(x)])}",
                        parse_mode="Markdown"
                    )
            else:
                await query.message.reply_text("📭 Você ainda não completou exercícios suficientes para gerar estatísticas.")

    except Exception as e:
        logger.error(f"Erro no progresso: {str(e)}")
        await query.message.reply_text("⚠️ Falha ao gerar relatório.")