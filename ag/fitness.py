"""Função de avaliação (fitness) de um indivíduo.

Indivíduo: lista com um cromossomo por período. Cada cromossomo tem `n_slots` genes
(um por horário da semana) cujo valor é o índice da disciplina ou VAZIO.
Como cada horário de um período guarda um único gene, choques dentro do mesmo
período são impossíveis por construção.
"""
from collections import Counter
from dataclasses import dataclass

VAZIO = -1


@dataclass
class Pesos:
    professor: float = 1000   # restrição obrigatória
    pre_requisito: float = 1000  # restrição obrigatória
    aula_isolada: float = 10  # aula sem outra da mesma disciplina colada no turno
    excesso_diario: float = 20  # aulas da disciplina no dia acima do limite
    janela: float = 5  # horário vago entre aulas de um mesmo turno


@dataclass
class Avaliacao:
    conflitos_professor: int
    conflitos_pre_requisito: int
    aulas_isoladas: int
    excesso_diario: int
    janelas: int
    penalidade: float

    @property
    def conflitos(self):
        return self.conflitos_professor + self.conflitos_pre_requisito

    @property
    def fitness(self):
        # Sempre positivo e maior para melhores soluções (necessário para a roleta)
        return 1 / (1 + self.penalidade)


def _disciplinas_no_slot(ind, slot):
    return [crom[slot] for crom in ind if crom[slot] != VAZIO]


def _conflitos_no_slot(presentes, prob):
    """Retorna (choques de professor, choques de pré-requisito) num horário."""
    profs = Counter(p for d in presentes for p in prob.professores_por_disciplina[d])
    professor = sum(n - 1 for n in profs.values() if n > 1)
    pre = sum(
        (min(a, b), max(a, b)) in prob.pares_pre_requisito
        for i, a in enumerate(presentes) for b in presentes[i + 1:]
    )
    return professor, pre


def avaliar(ind, prob, pesos):
    professor = pre = 0
    for slot in range(prob.n_slots):
        presentes = _disciplinas_no_slot(ind, slot)
        if len(presentes) > 1:
            p, r = _conflitos_no_slot(presentes, prob)
            professor += p
            pre += r

    isoladas = excesso = janelas = 0
    for crom in ind:
        por_dia = Counter()
        for bloco in prob.blocos_turno:
            genes = [crom[s] for s in bloco]
            ocupados = [i for i, g in enumerate(genes) if g != VAZIO]
            if not ocupados:
                continue
            janelas += sum(genes[i] == VAZIO for i in range(ocupados[0], ocupados[-1]))
            for i in ocupados:
                g = genes[i]
                por_dia[(prob.dia_do_slot(bloco[0]), g)] += 1
                vizinhos = genes[i - 1] if i > 0 else None, genes[i + 1] if i + 1 < len(genes) else None
                isoladas += g not in vizinhos
        excesso += sum(max(0, n - prob.limite_diario[d]) for (_, d), n in por_dia.items())

    penalidade = (pesos.professor * professor + pesos.pre_requisito * pre + pesos.aula_isolada * isoladas
                  + pesos.excesso_diario * excesso + pesos.janela * janelas)
    return Avaliacao(professor, pre, isoladas, excesso, janelas, penalidade)


def penalidade_minima(prob, pesos):
    """Menor penalidade possível (ótimo conhecido), usada como critério de parada.

    Choques e janelas podem chegar a zero, mas uma disciplina com uma única aula,
    ou com número ímpar de aulas e limite diário de 2, sempre deixa uma aula isolada.
    """
    isoladas = sum(d.aulas_semanais == 1 or (lim == 2 and d.aulas_semanais % 2 == 1)
                   for d, lim in zip(prob.disciplinas, prob.limite_diario))
    return pesos.aula_isolada * isoladas


def genes_em_conflito(ind, prob):
    """Posições (período, horário) envolvidas em choques obrigatórios; usadas na mutação dirigida."""
    posicoes = []
    for slot in range(prob.n_slots):
        presentes = _disciplinas_no_slot(ind, slot)
        if len(presentes) > 1 and any(_conflitos_no_slot(presentes, prob)):
            posicoes += [(p, slot) for p, crom in enumerate(ind) if crom[slot] != VAZIO]
    return posicoes
