import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
from database.database import Session, Usuario, RespostaExercicio, Exercicio
from sqlalchemy import func, cast, Integer

logger = logging.getLogger(__name__)

async def ver_ranking(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        
        teclado = [
            [InlineKeyboardButton("🏆 Ranking Geral", callback_data="RANKING_geral")],
            [InlineKeyboardButton("📚 Ranking por Categoria", callback_data="RANKING_categorias")],
            [InlineKeyboardButton("🏠 Menu Principal", callback_data="menu_principal")]
        ]
        
        await query.message.reply_text(
            "📊 Escolha o tipo de ranking:",
            reply_markup=InlineKeyboardMarkup(teclado)
        )

    except Exception as e:
        logger.error(f"Erro ao mostrar opções de ranking: {str(e)}")

async def selecionar_ranking_categoria(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        
        categorias = [
            ["🧮 Operações Numéricas", "RANKING_1"],
            ["🍕 Frações/Porcentagem", "RANKING_2"],
            ["📐 Proporção/Regra Três", "RANKING_3"],
            ["⚖️ Equações/Inequações", "RANKING_4"],
            ["🔺 Geometria", "RANKING_5"],
            ["🔣 Expressões Algébricas", "RANKING_6"]
        ]
        
        teclado = [
            [InlineKeyboardButton(nome, callback_data=callback)] 
            for nome, callback in categorias
        ]
        teclado.append([InlineKeyboardButton("🔙 Voltar", callback_data="ver_ranking")])
        
        await query.message.reply_text(
            "📚 Selecione uma categoria para ver o ranking:",
            reply_markup=InlineKeyboardMarkup(teclado)
        )

    except Exception as e:
        logger.error(f"Erro ao selecionar categoria ranking: {str(e)}")

async def exibir_ranking_categoria(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        
        categoria_id = int(query.data.split("_")[1])
        categorias = {
            1: "Operações com números naturais e inteiros",
            2: "Frações e porcentagem", 
            3: "Proporcionalidade e regra de três",
            4: "Equações e inequações",
            5: "Geometria plana e espacial",
            6: "Expressões algébricas"
        }
        categoria_nome = categorias.get(categoria_id, "Geral")
        
        with Session() as session:
            ranking = session.query(
                Usuario.nome,
                (func.sum(cast(RespostaExercicio.acerto, Integer))).label('pontos')
            ).join(RespostaExercicio
            ).join(Exercicio
            ).filter(
                Exercicio.tema == categoria_nome,
                RespostaExercicio.acerto == True
            ).group_by(Usuario.nome
            ).order_by(func.count(RespostaExercicio.id).desc()
            ).limit(10).all()

            emojis = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
            mensagem = f"🏆 <b>Ranking de {categoria_nome}</b>\n\n"
            
            for posicao, (nome, pontos) in enumerate(ranking, 1):
                emoji = emojis[posicao-1] if posicao <= 3 else f"{posicao}º"
                mensagem += f"{emoji} {nome} - {pontos if pontos else 0} acertos\n"
            
            mensagem += f"\n🔍 Baseado nos exercícios corretos de {categoria_nome.lower()}"
            
            teclado = [[InlineKeyboardButton("🔙 Voltar", callback_data="RANKING_categorias")]]
            
            await query.message.reply_text(
                mensagem,
                reply_markup=InlineKeyboardMarkup(teclado),
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Erro ranking categoria: {str(e)}")
        await query.message.reply_text("⚠️ Ranking indisponível para esta categoria")

async def exibir_ranking_geral(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        
        with Session() as session:
            ranking = session.query(
                Usuario.nome,
                func.sum(cast(RespostaExercicio.acerto, Integer)).label('pontos')
            ).join(RespostaExercicio
            ).group_by(Usuario.nome
            ).order_by(func.sum(cast(RespostaExercicio.acerto, Integer)).desc()
            ).limit(10).all()

            emojis = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
            mensagem = "🏆 <b>Ranking Geral</b>\n\n"
            
            for posicao, (nome, pontos) in enumerate(ranking, 1):
                emoji = emojis[posicao-1] if posicao <= 3 else f"{posicao}º"
                mensagem += f"{emoji} {nome} - {pontos if pontos else 0} acertos\n"
            
            mensagem += "\n🔍 Baseado em todos os exercícios respondidos"
            
            teclado = [[InlineKeyboardButton("🔙 Voltar", callback_data="ver_ranking")]]
            
            await query.message.reply_text(
                mensagem,
                reply_markup=InlineKeyboardMarkup(teclado),
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Erro no ranking geral: {str(e)}")
        await query.message.reply_text("⚠️ Falha ao gerar ranking geral.")