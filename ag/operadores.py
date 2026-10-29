"""Operadores genéticos: inicialização, seleção, crossover e mutação."""
from collections import Counter

from .fitness import VAZIO, genes_em_conflito


# ---------------------------------------------------------------- inicialização

def individuo_aleatorio(prob, rng):
    ind = []
    for p in prob.periodos:
        aulas = prob.aulas_por_periodo[p]
        crom = aulas + [VAZIO] * (prob.n_slots - len(aulas))
        rng.shuffle(crom)
        ind.append(crom)
    return ind


# ---------------------------------------------------------------- seleção

def selecao_torneio(populacao, avaliacoes, n, rng, tamanho=3):
    escolhidos = []
    for _ in range(n):
        competidores = rng.sample(range(len(populacao)), tamanho)
        vencedor = min(competidores, key=lambda i: avaliacoes[i].penalidade)
        escolhidos.append(populacao[vencedor])
    return escolhidos


def selecao_roleta(populacao, avaliacoes, n, rng):
    # Probabilidade proporcional ao fitness: p_i = f_i / soma(f)
    acumulado, total = [], 0.0
    for a in avaliacoes:
        total += a.fitness
        acumulado.append(total)
    escolhidos = []
    for _ in range(n):
        r = rng.uniform(0, total)
        i = next(i for i, v in enumerate(acumulado) if v >= r)
        escolhidos.append(populacao[i])
    return escolhidos


# ---------------------------------------------------------------- crossover
# Aplicados a cada período separadamente. Os cromossomos são permutações de um
# multiconjunto (aulas + vazios), então os filhos precisam conter exatamente os
# mesmos genes dos pais: OX e PBX preservam isso, como no Caixeiro Viajante.

def _completar(filho, doador, posicoes_livres):
    """Preenche as posições livres com os genes que faltam, na ordem em que aparecem no doador."""
    faltam = Counter(doador)
    faltam.subtract(g for g in filho if g is not None)
    resto = []
    for g in doador:
        if faltam[g] > 0:
            resto.append(g)
            faltam[g] -= 1
    for pos, g in zip(posicoes_livres, resto):
        filho[pos] = g
    return filho


def crossover_ox(a, b, rng):
    """Crossover baseado em ordem: mantém um trecho de `a` e o resto na ordem de `b`."""
    n = len(a)
    i, j = sorted(rng.sample(range(n + 1), 2))
    filho = [None] * n
    filho[i:j] = a[i:j]
    livres = list(range(j, n)) + list(range(i))
    return _completar(filho, b[j:] + b[:j], livres)


def crossover_pbx(a, b, rng):
    """Crossover baseado em posição: mantém posições sorteadas de `a` e o resto na ordem de `b`."""
    filho = [g if rng.random() < 0.5 else None for g in a]
    livres = [i for i, g in enumerate(filho) if g is None]
    return _completar(filho, b, livres)


def crossover_periodo(a, b, rng):
    """Crossover uniforme em nível de período: cada período vem inteiro de um dos pais."""
    return list(a) if rng.random() < 0.5 else list(b)


CROSSOVERS = {"ox": crossover_ox, "pbx": crossover_pbx, "periodo": crossover_periodo}


def cruzar(pai1, pai2, rng, tipo="ox"):
    op = CROSSOVERS[tipo]
    filho1 = [op(a, b, rng) for a, b in zip(pai1, pai2)]
    filho2 = [op(b, a, rng) for a, b in zip(pai1, pai2)]
    return filho1, filho2


# ---------------------------------------------------------------- mutação

def mutacao_troca(ind, rng, taxa):
    """Para cada gene, com probabilidade `taxa`, troca-o com outra posição do mesmo período."""
    for crom in ind:
        n = len(crom)
        for i in range(n):
            if rng.random() < taxa:
                j = rng.randrange(n)
                crom[i], crom[j] = crom[j], crom[i]


def mutacao_dirigida(ind, prob, rng):
    """Move uma aula envolvida em choque obrigatório para outro horário do seu período."""
    conflitos = genes_em_conflito(ind, prob)
    if conflitos:
        p, i = rng.choice(conflitos)
        j = rng.randrange(prob.n_slots)
        ind[p][i], ind[p][j] = ind[p][j], ind[p][i]
