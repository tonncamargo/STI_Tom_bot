import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
import openai
from database.database import Session, Usuario, Exercicio, RespostaExercicio
from config import get_openai_key

openai.api_key = get_openai_key() 

logger = logging.getLogger(__name__)

def gerar_questao_bncc(codigo_bncc: str, tema: str, emoji: str) -> tuple:
    try:
        prompt = f"""
        Crie uma questão para o ensino fundamental II sobre {tema} que:
        - Seja lúdica e contextualizada (ex: jogos, situações cotidianas)
        - Use emojis relacionados ({emoji})
        - Tenha 4 alternativas claras (A-D)
        - Seguir habilidade BNCC {codigo_bncc}
        - Formato resposta: ||RESPOSTA||[LETRA]
        """
        
        resposta = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7
        )
        
        conteudo = resposta.choices[0].message.content.strip()
        questao, resposta = conteudo.split("||RESPOSTA||")
        return questao.strip(), resposta[0].upper()
        
    except Exception as e:
        logger.error(f"Erro na geração: {str(e)}")
        return "🔴 Erro ao gerar exercício. Tente novamente!", "A"

async def iniciar_exercicios(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        
        categorias = [
            ["1️⃣ Operações com Números Naturais/Inteiros"],
            ["2️⃣ Frações/Porcentagem"],
            ["3️⃣ Regra de Três e Proporção"],
            ["4️⃣ Equações/Inequações 1º/2º Grau"],
            ["5️⃣ Geometria Plana/Espacial"],
            ["6️⃣ Expressões Algébricas e Fatoração"]
        ]
        
        teclado = [
            [InlineKeyboardButton(cat[0], callback_data=f"CATEGORIA_{i+1}")] 
            for i, cat in enumerate(categorias)
        ]
        teclado.append([InlineKeyboardButton("🏠 Menu Principal", callback_data="menu_principal")])
        
        await query.message.reply_text(
            "📚 Escolha uma categoria de exercícios:",
            reply_markup=InlineKeyboardMarkup(teclado)
        )

    except Exception as e:
        logger.error(f"Erro ao mostrar categorias: {str(e)}")

async def selecionar_categoria_exercicio(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        
        categoria_id = int(query.data.split("_")[1])
        
        categorias = {
            1: ("EF06MA03", "Operações com números naturais e inteiros", "🧮"),
            2: ("EF06MA08", "Frações e porcentagem", "🍕"),
            3: ("EF07MA12", "Proporcionalidade e regra de três", "📐"),
            4: ("EF08MA06", "Equações e inequações", "⚖️"),
            5: ("EF06MA16", "Geometria plana e espacial", "🔺"),
            6: ("EF08MA05", "Expressões algébricas", "🔣")
        }
        
        codigo, tema, emoji = categorias.get(categoria_id, ("EF06MA01", "Geral", "📚"))
        questao, resposta = gerar_questao_bncc(codigo, tema, emoji)
        
        if "🔴 Erro" in questao:
            await query.message.reply_text(questao)
            return
        
        with Session() as session:
            usuario = session.query(Usuario).filter_by(telegram_id=query.from_user.id).first()
            
            exercicio = Exercicio(
                tema=tema,
                dificuldade=usuario.nivel_dificuldade,
                enunciado=questao,
                resposta_correta=resposta,
                habilidade_bncc=codigo
            )
            session.add(exercicio)
            session.commit()
            
            teclado = [
                [InlineKeyboardButton(opcao, callback_data=f"EXERC_{opcao}_{exercicio.id}") 
                for opcao in ["A", "B", "C", "D"]],
                [InlineKeyboardButton("🏠 Menu Principal", callback_data="menu_principal")]
            ]
            
            await query.message.reply_text(
                f"{emoji} <b>Exercício de {tema}</b>\n\n{questao}",
                reply_markup=InlineKeyboardMarkup(teclado),
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Erro ao selecionar categoria: {str(e)}", exc_info=True)
        await query.message.reply_text("⚠️ Falha ao carregar exercício. Tente novamente.")

async def processar_exercicio(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        resposta_usuario, exercicio_id = query.data.split("_")[1:]
        
        with Session() as session:
            usuario = session.query(Usuario).filter_by(telegram_id=query.from_user.id).first()
            exercicio = session.query(Exercicio).get(int(exercicio_id))
            
            acerto = (resposta_usuario.upper() == exercicio.resposta_correta.upper())
            resposta_db = RespostaExercicio(
                usuario_id=usuario.id,
                exercicio_id=exercicio.id,
                acerto=acerto
            )
            session.add(resposta_db)
            
            total_tema = session.query(RespostaExercicio)\
                .join(Exercicio)\
                .filter(
                    RespostaExercicio.usuario_id == usuario.id,
                    Exercicio.tema == exercicio.tema
                )\
                .count()
            
            acertos_tema = session.query(RespostaExercicio)\
                .join(Exercicio)\
                .filter(
                    RespostaExercicio.usuario_id == usuario.id,
                    Exercicio.tema == exercicio.tema,
                    RespostaExercicio.acerto == True
                )\
                .count()
            
            mensagem = (
                f"{'✅' if acerto else '❌'} {'Correto!' if acerto else 'Errado!'}\n"
                f"Resposta correta: {exercicio.resposta_correta}\n\n"
                f"📊 Estatísticas em {exercicio.tema.split()[0]}\n"
                f"Acertos: {acertos_tema}/{total_tema}"
            )
            
            await query.message.reply_text(mensagem)
            
            if acerto:
                usuario.acertos_consecutivos += 1
                if usuario.acertos_consecutivos % 3 == 0:
                    usuario.nivel_dificuldade = min(usuario.nivel_dificuldade + 1, 3)
                    await query.message.reply_text("🚀 Nível aumentado!")
            else:
                usuario.acertos_consecutivos = 0
                usuario.nivel_dificuldade = max(usuario.nivel_dificuldade - 1, 1)
                teclado = [[InlineKeyboardButton("📖 Explicação", callback_data=f"EXPLICAR_{exercicio.id}")]]
                await query.message.reply_text(
                    "📉 Dificuldade ajustada. Quer ajuda?",
                    reply_markup=InlineKeyboardMarkup(teclado)
                )

            session.commit()
            await iniciar_exercicios(update, context)

    except Exception as e:
        logger.error(f"Erro ao processar exercício: {str(e)}")
        await query.message.reply_text("⚠️ Erro ao processar resposta.")

async def explicar_exercicio(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        exercicio_id = query.data.split("_")[1]
        
        with Session() as session:
            exercicio = session.query(Exercicio).get(int(exercicio_id))
            
            prompt = f"""
            Explique a solução desta questão para um adolescente:
            {exercicio.enunciado}
            - Use analogias com jogos ou redes sociais
            - Máximo de 3 passos
            - Inclua emojis
            - Seja encorajador
            """
            
            resposta = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "system", "content": prompt}]
            )
            
            explicacao = resposta.choices[0].message.content.strip()
            await query.message.reply_text(
                f"🧠 *Explicação Detalhada:*\n\n{explicacao}",
                parse_mode="MarkdownV2"
            )

    except Exception as e:
        logger.error(f"Erro na explicação: {str(e)}")
        await query.message.reply_text("⚠️ Erro ao gerar explicação.")