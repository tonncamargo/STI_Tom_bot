from .teste_nivelamento import (
    gerar_questao,
    iniciar_teste,
    enviar_questao,
    processar_resposta,
    finalizar_teste
)

from .exercicios import (
    gerar_questao_bncc,
    iniciar_exercicios,
    selecionar_categoria_exercicio,
    processar_exercicio,
    explicar_exercicio
)

from .chatbot import (
    toggle_chatbot,  # Use o nome real da função
    handle_chatbot_message,
    sair_chatbot
)

from .progresso import (
    ver_progresso
)

from .ranking import (
    ver_ranking,
    selecionar_ranking_categoria,
    exibir_ranking_categoria,
    exibir_ranking_geral
)

from .suporte import (
    iniciar_suporte, suporte_ajuda, suporte_sobre, cancelar_suporte, processar_ajuda
)

__all__ = [
    # Teste nivelamento
    'gerar_questao', 'iniciar_teste', 'enviar_questao', 'processar_resposta', 'finalizar_teste',
    
    # Exercícios
    'gerar_questao_bncc', 'iniciar_exercicios', 'selecionar_categoria_exercicio', 
    'processar_exercicio', 'explicar_exercicio',
    
    # Chatbot
    'toggle_chatbot', 'handle_chatbot_message', 'sair_chatbot',
    
    # Progresso e ranking
    'ver_progresso', 'ver_ranking', 'selecionar_ranking_categoria',
    'exibir_ranking_categoria', 'exibir_ranking_geral',
    
    # Suporte
    'iniciar_suporte', 'suporte_ajuda', 'suporte_sobre', 'cancelar_suporte', 'processar_ajuda'
]