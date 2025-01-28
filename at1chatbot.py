import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
import re
from collections import deque
import random

class PrioridadeTicket(Enum):
    BAIXA = 1
    MEDIA = 2
    ALTA = 3
    CRITICA = 4

    @classmethod
    def from_keywords(cls, texto: str) -> 'PrioridadeTicket':
        keywords = {
            'crítico': cls.CRITICA,
            'urgente': cls.CRITICA,
            'emergência': cls.CRITICA,
            'alto': cls.ALTA,
            'importante': cls.ALTA,
            'médio': cls.MEDIA,
            'normal': cls.MEDIA,
            'baixo': cls.BAIXA,
            'rotina': cls.BAIXA
        }
        for keyword, priority in keywords.items():
            if keyword in texto.lower():
                return priority
        return cls.BAIXA

class StatusTicket(Enum):
    ABERTO = 'aberto'
    DESIGNADO = 'designado'
    EM_ANDAMENTO = 'em_andamento'
    PAUSADO = 'pausado'
    AGUARDANDO_CLIENTE = 'aguardando_cliente'
    RESOLVIDO = 'resolvido'
    FECHADO = 'fechado'

@dataclass
class Mensagem:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    remetente_id: str
    remetente_nome: str
    conteudo: str
    timestamp: datetime = field(default_factory=datetime.now)
    is_sistema: bool = False

@dataclass
class Agente:
    id: str
    nome: str
    email: str
    carga_trabalho: int = 0
    especializacoes: Set[str] = field(default_factory=set)
    disponivel: bool = True
    ultimo_login: datetime = field(default_factory=datetime.now)
    tickets_resolvidos: int = 0
    tempo_medio_resolucao: timedelta = field(default_factory=lambda: timedelta())

    def adicionar_especializacao(self, especializacao: str):
        self.especializacoes.add(especializacao.lower())

@dataclass
class Cliente:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nome: str
    email: str
    tickets_abertos: List[str] = field(default_factory=list)
    historico_interacoes: List[str] = field(default_factory=list)

@dataclass
class Ticket:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    titulo: str
    descricao: str
    prioridade: PrioridadeTicket = PrioridadeTicket.BAIXA
    status: StatusTicket = StatusTicket.ABERTO
    cliente: Cliente
    criado_em: datetime = field(default_factory=datetime.now)
    agente_designado: Optional[Agente] = None
    ultima_atualizacao: datetime = field(default_factory=datetime.now)
    mensagens: List[Mensagem] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    tempo_primeira_resposta: Optional[timedelta] = None
    tempo_resolucao: Optional[timedelta] = None
    satisfacao_cliente: Optional[int] = None

    def adicionar_mensagem(self, mensagem: Mensagem):
        self.mensagens.append(mensagem)
        self.ultima_atualizacao = datetime.now()

class AutoRespostaManager:
    def __init__(self):
        self.respostas_padrao = {
            'saudacao': [
                "Olá! Como posso ajudar você hoje?",
                "Bem-vindo ao nosso suporte! Em que posso auxiliar?",
                "Oi! Estou aqui para ajudar. Qual é a sua dúvida?"
            ],
            'despedida': [
                "Obrigado por entrar em contato! Tenha um ótimo dia!",
                "Foi um prazer ajudar! Até mais!",
                "Se precisar de mais alguma coisa, estamos à disposição!"
            ],
            'aguarde': [
                "Por favor, aguarde um momento enquanto processo sua solicitação.",
                "Estou analisando sua questão, só um instante.",
                "Aguarde um momento, já estou verificando isso para você."
            ]
        }

    def get_resposta(self, tipo: str) -> str:
        return random.choice(self.respostas_padrao.get(tipo, ["Desculpe, não entendi."]))

class AnalisadorMensagens:
    def __init__(self):
        self.palavras_chave = {
            'problema': set(['erro', 'bug', 'falha', 'problema', 'não funciona']),
            'urgencia': set(['urgente', 'crítico', 'emergência', 'imediato']),
            'ajuda': set(['ajuda', 'suporte', 'auxílio', 'como'])
        }

    def classificar_mensagem(self, texto: str) -> Dict[str, bool]:
        texto_lower = texto.lower()
        return {
            categoria: any(palavra in texto_lower for palavra in palavras)
            for categoria, palavras in self.palavras_chave.items()
        }

    def extrair_prioridade(self, texto: str) -> PrioridadeTicket:
        return PrioridadeTicket.from_keywords(texto)

class SistemaSuporte:
    def __init__(self):
        self.agentes: Dict[str, Agente] = {}
        self.tickets: Dict[str, Ticket] = {}
        self.clientes: Dict[str, Cliente] = {}
        self.auto_resposta = AutoRespostaManager()
        self.analisador = AnalisadorMensagens()
        self.historico_global: deque = deque(maxlen=1000)
        self.sla_configs = {
            PrioridadeTicket.CRITICA: timedelta(hours=1),
            PrioridadeTicket.ALTA: timedelta(hours=4),
            PrioridadeTicket.MEDIA: timedelta(hours=12),
            PrioridadeTicket.BAIXA: timedelta(hours=24)
        }

    def adicionar_agente(self, agente: Agente):
        self.agentes[agente.id] = agente

    def registrar_cliente(self, nome: str, email: str) -> Cliente:
        cliente = Cliente(nome=nome, email=email)
        self.clientes[cliente.id] = cliente
        return cliente

    def criar_ticket(self, cliente: Cliente, titulo: str, descricao: str) -> Ticket:
        prioridade = self.analisador.extrair_prioridade(descricao)
        ticket = Ticket(
            titulo=titulo,
            descricao=descricao,
            prioridade=prioridade,
            cliente=cliente
        )
        
        # Adicionar mensagem inicial
        mensagem_sistema = Mensagem(
            remetente_id='sistema',
            remetente_nome='Sistema',
            conteudo=f"Ticket criado com prioridade {prioridade.name}",
            is_sistema=True
        )
        ticket.adicionar_mensagem(mensagem_sistema)
        
        self.tickets[ticket.id] = ticket
        cliente.tickets_abertos.append(ticket.id)
        
        # Tentar designar automaticamente
        self.designar_ticket(ticket)
        return ticket

    def designar_ticket(self, ticket: Ticket) -> Optional[Agente]:
        agentes_disponiveis = [
            agente for agente in self.agentes.values()
            if agente.disponivel and agente.carga_trabalho < 5
        ]

        if not agentes_disponiveis:
            return None

        # Priorizar agentes com especialização adequada
        agentes_especializados = [
            agente for agente in agentes_disponiveis
            if ticket.prioridade.name.lower() in agente.especializacoes
        ]

        # Considerar carga de trabalho e experiência
        def pontuacao_agente(agente):
            pontos = 100 - (agente.carga_trabalho * 20)
            if agente in agentes_especializados:
                pontos += 50
            pontos += agente.tickets_resolvidos // 10
            return pontos

        agente_selecionado = max(agentes_disponiveis, key=pontuacao_agente)
        
        ticket.agente_designado = agente_selecionado
        ticket.status = StatusTicket.DESIGNADO
        agente_selecionado.carga_trabalho += 1
        
        # Registrar primeira resposta
        if not ticket.tempo_primeira_resposta:
            ticket.tempo_primeira_resposta = datetime.now() - ticket.criado_em
        
        mensagem = Mensagem(
            remetente_id='sistema',
            remetente_nome='Sistema',
            conteudo=f"Ticket designado para {agente_selecionado.nome}",
            is_sistema=True
        )
        ticket.adicionar_mensagem(mensagem)
        
        return agente_selecionado

    def processar_mensagem(self, ticket_id: str, remetente_id: str, conteudo: str) -> List[str]:
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            return ["Ticket não encontrado."]

        # Identificar remetente
        if remetente_id == ticket.cliente.id:
            remetente_nome = ticket.cliente.nome
        elif remetente_id == ticket.agente_designado.id if ticket.agente_designado else None:
            remetente_nome = ticket.agente_designado.nome
        else:
            return ["Remetente não autorizado."]

        # Criar e adicionar mensagem
        mensagem = Mensagem(
            remetente_id=remetente_id,
            remetente_nome=remetente_nome,
            conteudo=conteudo
        )
        ticket.adicionar_mensagem(mensagem)
        self.historico_global.append(mensagem)

        # Análise automática da mensagem
        classificacao = self.analisador.classificar_mensagem(conteudo)
        respostas = []

        # Gerar respostas automáticas baseadas na classificação
        if classificacao.get('problema', False):
            respostas.append(self.auto_resposta.get_resposta('problema'))
        if classificacao.get('urgencia', False):
            nova_prioridade = self.analisador.extrair_prioridade(conteudo)
            if nova_prioridade != ticket.prioridade:
                ticket.prioridade = nova_prioridade
                respostas.append(f"Prioridade do ticket atualizada para {nova_prioridade.name}")

        # Verificar SLA
        tempo_decorrido = datetime.now() - ticket.ultima_atualizacao
        if tempo_decorrido > self.sla_configs[ticket.prioridade]:
            respostas.append("⚠️ Atenção: Este ticket está próximo de ultrapassar o SLA!")

        return respostas

    def atualizar_status_ticket(self, ticket_id: str, novo_status: StatusTicket, comentario: str = None):
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            return False

        ticket.status = novo_status
        if comentario:
            mensagem = Mensagem(
                remetente_id='sistema',
                remetente_nome='Sistema',
                conteudo=f"Status atualizado para {novo_status.value}: {comentario}",
                is_sistema=True
            )
            ticket.adicionar_mensagem(mensagem)

        if novo_status == StatusTicket.RESOLVIDO:
            if ticket.agente_designado:
                agente = ticket.agente_designado
                agente.carga_trabalho -= 1
                agente.tickets_resolvidos += 1
                ticket.tempo_resolucao = datetime.now() - ticket.criado_em
                
                # Atualizar tempo médio de resolução do agente
                if agente.tickets_resolvidos == 1:
                    agente.tempo_medio_resolucao = ticket.tempo_resolucao
                else:
                    total = agente.tempo_medio_resolucao * (agente.tickets_resolvidos - 1)
                    agente.tempo_medio_resolucao = (total + ticket.tempo_resolucao) / agente.tickets_resolvidos

        return True

    def avaliar_satisfacao(self, ticket_id: str, nota: int, comentario: str = None):
        if not (1 <= nota <= 5):
            return False
        
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            return False

        ticket.satisfacao_cliente = nota
        if comentario:
            mensagem = Mensagem(
                remetente_id='sistema',
                remetente_nome='Sistema',
                conteudo=f"Avaliação do cliente: {nota}/5 - {comentario}",
                is_sistema=True
            )
            ticket.adicionar_mensagem(mensagem)
        return True

    def gerar_relatorio_desempenho(self) -> Dict:
        total_tickets = len(self.tickets)
        tickets_resolvidos = len([t for t in self.tickets.values() if t.status == StatusTicket.RESOLVIDO])
        tempo_medio_resolucao = timedelta()
        satisfacao_media = 0
        total_avaliacoes = 0

        for ticket in self.tickets.values():
            if ticket.tempo_resolucao:
                tempo_medio_resolucao += ticket.tempo_resolucao
            if ticket.satisfacao_cliente:
                satisfacao_media += ticket.satisfacao_cliente
                total_avaliacoes += 1

        if tickets_resolvidos:
            tempo_medio_resolucao /= tickets_resolvidos
        if total_avaliacoes:
            satisfacao_media /= total_avaliacoes

        return {
            'total_tickets': total_tickets,
            'tickets_resolvidos': tickets_resolvidos,
            'taxa_resolucao': (tickets_resolvidos / total_tickets * 100) if total_tickets else 0,
            'tempo_medio_resolucao': tempo_medio_resolucao,
            'satisfacao_media': satisfacao_media,
            'agentes_mais_produtivos': sorted(
                self.agentes.values(),
                key=lambda a: a.tickets_resolvidos,
                reverse=True
            )[:3]
        }

def main():
    # Exemplo de uso do sistema
    sistema = SistemaSuporte()
    
    # Criar agentes com especializações
    agente1 = Agente('1', 'João', 'joao@exemplo.com')
    agente1.adicionar_especializacao('alta')
    agente1.adicionar_
