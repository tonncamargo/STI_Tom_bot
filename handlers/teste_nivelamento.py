import logging
from typing import Tuple, Dict, List
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
import openai
from datetime import datetime, timedelta
from database.database import Session, Usuario, TesteRealizado, QuestaoTeste
from config import get_openai_key
import random
from threading import Lock

logger = logging.getLogger(__name__)
db_lock = Lock()

CATEGORIAS = [
    ("1️⃣ Operações com Números Naturais/Inteiros", "operacoes_inteiros"),
    ("2️⃣ Frações/Porcentagem", "fracoes_porcentagem"),
    ("3️⃣ Regra de Três e Proporção", "regra_tres"),
    ("4️⃣ Equações/Inequações 1º/2º Grau", "equacoes"),
    ("5️⃣ Geometria Plana/Espacial", "geometria"),
    ("6️⃣ Expressões Algébricas e Fatoração", "expressoes_algebricas")
]

TEMPO_POR_QUESTAO = 30  # segundos

class EstadoTeste:
    __slots__ = ['categoria_atual', 'questoes', 'respostas_corretas', 
                'respostas_usuario', 'tempo_inicio', 'indice_questao_atual']
    
    def __init__(self):
        self.categoria_atual = None
        self.questoes = []
        self.respostas_corretas = []
        self.respostas_usuario = []
        self.tempo_inicio = None
        self.indice_questao_atual = 0

def gerar_questao(categoria: str) -> Tuple[str, str, List[str]]:
    try:
        prompt = f"""
        Crie uma questão objetiva sobre {categoria} para ensino médio com:
        - 4 alternativas (A-D)
        - Apenas UMA correta
        - Dificuldade média
        Formato SEM MARKDOWN:
        ENUNCIADO
        A) Alternativa A
        B) Alternativa B
        C) Alternativa C
        D) Alternativa D
        RESPOSTA: [A-D]
        """
        
        resposta = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
            timeout=15
        )
        
        conteudo = resposta['choices'][0]['message']['content'].strip()
        partes = conteudo.split("\n")
        
        # Verificação robusta do formato da resposta
        if len(partes) < 6:
            raise ValueError("Formato de resposta inválido do OpenAI - menos de 6 linhas")
            
        enunciado = "\n".join(partes[:-5])
        alternativas = partes[-5:-1]
        resposta_correta = partes[-1].split(":")[-1].strip()[0].upper()
        
        if resposta_correta not in ['A', 'B', 'C', 'D']:
            raise ValueError(f"Resposta inválida: {resposta_correta}")
            
        # Verifica se as alternativas começam com A), B), C), D)
        for i, alt in enumerate(alternativas):
            if not alt.startswith(f"{chr(65+i)})"):
                raise ValueError(f"Alternativa {i+1} não começa com {chr(65+i)})")
                
        return enunciado, resposta_correta, alternativas
        
    except Exception as e:
        logger.error(f"Erro ao gerar questão: {str(e)}")
        # Questão fallback padrão
        return (
            "Qual é o resultado de 2 + 2?",
            "B",
            ["A) 3", "B) 4", "C) 5", "D) 6"]
        )

async def iniciar_selecao_categoria(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton(nome, callback_data=tag)]
        for nome, tag in CATEGORIAS
    ]
    
    await update.message.reply_text(
        "📚 Selecione uma categoria de teste:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    # Verifica testes já realizados
    with Session() as session:
        usuario = session.query(Usuario).filter_by(
            telegram_id=update.effective_user.id).first()
            
        if usuario:
            testes_feitos = {t.categoria for t in usuario.testes_realizados}
            for btn in keyboard:
                if btn[0].callback_data in testes_feitos:
                    btn[0].text += " ✅"

async def iniciar_teste_categoria(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    categoria_tag = query.data
    categoria_nome = next(n for n, t in CATEGORIAS if t == categoria_tag)
    
    estado = EstadoTeste()
    estado.categoria_atual = categoria_tag
    estado.tempo_inicio = datetime.now()
    
    # Gerar 5 questões
    for _ in range(5):
        questao, resposta, alternativas = gerar_questao(categoria_nome)
        estado.questoes.append((questao, alternativas))
        estado.respostas_corretas.append(resposta)
    
    context.user_data['estado_teste'] = estado
    await enviar_questao_atual(query, context)

async def enviar_questao_atual(query, context: CallbackContext) -> None:
    estado = context.user_data['estado_teste']
    indice = estado.indice_questao_atual
    questao, alternativas = estado.questoes[indice]
    
    # Criar botões com timer
    botoes = [InlineKeyboardButton(
        alt.split(")")[0],
        callback_data=f"resp_{indice}_{alt[0]}") 
        for alt in alternativas]
    
    tempo_restante = TEMPO_POR_QUESTAO - (datetime.now() - estado.tempo_inicio).seconds
    mensagem = (
        f"⏳ Tempo restante: {max(0, tempo_restante)}s\n"
        f"📝 Questão {indice+1}/5 - {next(n for n, t in CATEGORIAS if t == estado.categoria_atual)}\n\n"
        f"{questao}\n\n" +
        "\n".join(alternativas)
    )
    
    await query.message.reply_text(
        mensagem,
        reply_markup=InlineKeyboardMarkup([botoes[i:i+2] for i in range(0, 4, 2)]))
    
    # Agendar verificação de timeout
    context.job_queue.run_once(
        verificar_timeout,
        TEMPO_POR_QUESTAO,
        user_id=query.from_user.id,
        data=indice,
        name=f"timeout_{query.from_user.id}_{indice}"
    )

async def processar_resposta(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    _, indice, resposta = query.data.split("_")
    indice = int(indice)
    estado = context.user_data['estado_teste']
    
    # Validar resposta
    if estado.indice_questao_atual != indice:
        await query.message.reply_text("⌛ Essa questão já foi respondida!")
        return
    
    estado.respostas_usuario.append(resposta)
    estado.indice_questao_atual += 1
    
    # Feedback imediato
    correto = resposta == estado.respostas_corretas[indice]
    await query.message.reply_text(
        "✅ Correto!" if correto else 
        f"❌ Errado! Resposta correta: {estado.respostas_corretas[indice]}")
    
    if estado.indice_questao_atual < 5:
        await enviar_questao_atual(query, context)
    else:
        await finalizar_teste(query, context)

async def verificar_timeout(context: CallbackContext) -> None:
    job = context.job
    estado = context.user_data.get('estado_teste')
    
    if not estado or estado.indice_questao_atual != job.data:
        return
    
    estado.respostas_usuario.append("")  # Resposta vazia = timeout
    estado.indice_questao_atual += 1
    
    if estado.indice_questao_atual < 5:
        await context.bot.send_message(
            job.user_id,
            "⏰ Tempo esgotado! Próxima questão...")
        
        # Recuperamos a mensagem original para continuar o fluxo
        chat = await context.bot.get_chat(job.user_id)
        message = await chat.send_message("Carregando próxima questão...")
        fake_query = type('', (), {'message': message, 'from_user': type('', (), {'id': job.user_id})})()
        await enviar_questao_atual(fake_query, context)
    else:
        await context.bot.send_message(
            job.user_id,
            "⏰ Tempo esgotado! Finalizando teste...")
        fake_query = type('', (), {'message': type('', (), {'chat': chat}), 'from_user': type('', (), {'id': job.user_id})})()
        await finalizar_teste(fake_query, context)

async def finalizar_teste(query, context: CallbackContext) -> None:
    estado = context.user_data['estado_teste']
    tempo_total = datetime.now() - estado.tempo_inicio
    
    # Salvar no banco de dados
    with db_lock, Session() as session:
        usuario = session.query(Usuario).filter_by(
            telegram_id=query.from_user.id).first()
            
        if not usuario:
            await query.message.reply_text("❌ Erro: Usuário não encontrado!")
            return
            
        teste = TesteRealizado(
            usuario_id=usuario.id,
            categoria=estado.categoria_atual,
            tempo_segundos=tempo_total.seconds,
            data_realizacao=datetime.now()
        )
        
        session.add(teste)
        session.flush()
        
        acertos = 0
        for i in range(min(5, len(estado.respostas_usuario))):  # Garante que não ultrapasse o limite
            correto = i < len(estado.respostas_corretas) and estado.respostas_usuario[i] == estado.respostas_corretas[i]
            if correto:
                acertos += 1
                
            session.add(QuestaoTeste(
                teste_id=teste.id,
                numero_questao=i+1,
                resposta_usuario=estado.respostas_usuario[i] if i < len(estado.respostas_usuario) else "",
                resposta_correta=estado.respostas_corretas[i] if i < len(estado.respostas_corretas) else "",
                acertou=correto
            ))
        
        session.commit()
    
    # Feedback detalhado
    relatorio = []
    for i in range(5):
        if i >= len(estado.respostas_usuario) or i >= len(estado.respostas_corretas):
            status = "⏰"
            resposta_user = "N/A"
            resposta_correta = estado.respostas_corretas[i] if i < len(estado.respostas_corretas) else "N/A"
        else:
            status = "✅" if estado.respostas_usuario[i] == estado.respostas_corretas[i] else "❌"
            resposta_user = estado.respostas_usuario[i] or 'N/A'
            resposta_correta = estado.respostas_corretas[i]
            
        relatorio.append(
            f"{status} Questão {i+1}: Sua resposta: {resposta_user} | "
            f"Correta: {resposta_correta}")

    mensagem = (
        f"🏁 Teste Finalizado!\n\n"
        f"📊 Acertos: {acertos}/5\n"
        f"⏱ Tempo: {tempo_total.seconds} segundos\n\n"
        "📝 Detalhes:\n" + "\n".join(relatorio)
    )
    
    await query.message.reply_text(mensagem)
    del context.user_data['estado_teste']