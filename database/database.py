"""
Módulo: database.py

Este módulo gerencia o banco de dados do projeto Tom, utilizando SQLAlchemy para definir
as tabelas e suas relações. Ele armazena informações sobre usuários, exercícios e suas respostas.

Funcionamento:
- Define as tabelas `Usuario`, `Exercicio` e `RespostaExercicio`.
- Estabelece relacionamentos entre usuários e exercícios.
- Cria as tabelas no banco de dados SQLite (`tom_bot.db`).
- Configura uma sessão para interações com o banco de dados.

Tabelas:
1. `usuarios`: Armazena informações dos usuários, como ID do Telegram, nível e progresso.
2. `exercicios`: Contém os exercícios com seus temas, dificuldades e respostas corretas.
3. `respostas_exercicios`: Relaciona usuários aos exercícios e registra acertos ou erros.

"""

from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# Definição da base para os modelos ORM
Base = declarative_base()

# Criação do banco de dados SQLite
engine = create_engine("sqlite:///tom_bot.db")

# Definição das tabelas
class Usuario(Base):
    """
    Representa um usuário do sistema.
    
    Atributos:
    - id: Identificador único do usuário.
    - telegram_id: ID do usuário no Telegram.
    - nome: Nome do usuário.
    - nivel: Nível atual do usuário.
    - progresso_teste: Progresso no teste de nivelamento.
    - acertos_teste: Número de acertos no teste.
    - teste_concluido: Indica se o teste foi concluído.
    - nivel_dificuldade: Nível de dificuldade atribuído ao usuário.
    - acertos_consecutivos: Contagem de acertos consecutivos.
    - exercicios: Relacionamento com respostas de exercícios.
    """
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    nome = Column(String, nullable=False)
    nivel = Column(String)
    progresso_teste = Column(Integer, default=0)
    acertos_teste = Column(Integer, default=0)
    teste_concluido = Column(Boolean, default=False)
    nivel_dificuldade = Column(Integer, default=1)
    acertos_consecutivos = Column(Integer, default=0)
    exercicios = relationship("RespostaExercicio", back_populates="usuario")

class Exercicio(Base):
    """
    Representa um exercício matemático.
    
    Atributos:
    - id: Identificador único do exercício.
    - tema: Tema do exercício.
    - habilidade_bncc: Habilidade relacionada na BNCC.
    - dificuldade: Nível de dificuldade do exercício.
    - enunciado: Enunciado da questão.
    - resposta_correta: Resposta correta do exercício.
    """
    __tablename__ = "exercicios"
    id = Column(Integer, primary_key=True)
    tema = Column(String)
    habilidade_bncc = Column(String)
    dificuldade = Column(Integer)
    enunciado = Column(String)
    resposta_correta = Column(String)

class RespostaExercicio(Base):
    """
    Armazena as respostas dos usuários aos exercícios.
    
    Atributos:
    - id: Identificador único da resposta.
    - usuario_id: ID do usuário que respondeu.
    - exercicio_id: ID do exercício respondido.
    - acerto: Indica se a resposta foi correta.
    - data: Data e hora da resposta.
    - usuario: Relacionamento com a tabela `Usuario`.
    - exercicio: Relacionamento com a tabela `Exercicio`.
    """
    __tablename__ = "respostas_exercicios"
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'))
    exercicio_id = Column(Integer, ForeignKey('exercicios.id'))
    acerto = Column(Boolean)
    data = Column(DateTime, default=datetime.now)
    usuario = relationship("Usuario", back_populates="exercicios")
    exercicio = relationship("Exercicio")

# Criação das tabelas no banco de dados
Base.metadata.create_all(engine)

# Configuração da sessão para interação com o banco de dados
SessionLocal = sessionmaker(bind=engine)
Session = sessionmaker(bind=engine)  # Mantido para compatibilidade

# Define os elementos disponíveis para importação ao utilizar `from database import *`
__all__ = ['Session', 'Usuario', 'Exercicio', 'RespostaExercicio', 'Base']