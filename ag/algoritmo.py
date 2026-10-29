"""Laço principal do algoritmo genético."""
import random
import time
from collections import Counter
from dataclasses import dataclass, field

from .fitness import Pesos, avaliar, penalidade_minima
from .operadores import (cruzar, individuo_aleatorio, mutacao_dirigida, mutacao_troca,
                         selecao_roleta, selecao_torneio)


@dataclass
class Config:
    tamanho_populacao: int = 100
    min_geracoes: int = 500      # exigência do trabalho
    max_geracoes: int = 3000
    paciencia: int = 300         # gerações sem melhoria para parar (após o mínimo)
    selecao: str = "torneio"     # "torneio" ou "roleta"
    tamanho_torneio: int = 3
    crossover: str = "ox"        # "ox", "pbx" ou "periodo"
    taxa_crossover: float = 0.8
    taxa_mutacao: float = 0.003  # por gene (~0,7 troca por indivíduo)
    taxa_mutacao_dirigida: float = 0.3  # por indivíduo
    elitismo: int = 2
    evitar_duplicados: bool = True
    top_solucoes: int = 5
    semente: int | None = None
    pesos: Pesos = field(default_factory=Pesos)


@dataclass
class Geracao:
    numero: int
    melhor: float
    media: float
    pior: float
    conflitos_melhor: int
    diversidade: float  # fração média de genes diferentes do gene mais comum (consenso) em cada posição


@dataclass
class Resultado:
    melhor: list
    avaliacao: object
    top: list            # [(avaliacao, individuo)] melhores soluções distintas já vistas
    historico: list
    geracoes: int
    motivo_parada: str
    segundos: float
    config: Config


def _chave(ind):
    return tuple(g for crom in ind for g in crom)


def _copia(ind):
    return [list(crom) for crom in ind]


def _diversidade(populacao):
    """0 quando todos os indivíduos são iguais; cresce à medida que diferem do consenso."""
    genes = [_chave(ind) for ind in populacao]
    n = len(genes)
    return sum(1 - Counter(pos).most_common(1)[0][1] / n for pos in zip(*genes)) / len(genes[0])


def executar(prob, cfg=Config(), ao_fim_geracao=None):
    """Executa o AG. `ao_fim_geracao(Geracao)` permite acompanhar o progresso (interface web)."""
    rng = random.Random(cfg.semente)
    inicio = time.perf_counter()

    populacao = [individuo_aleatorio(prob, rng) for _ in range(cfg.tamanho_populacao)]
    avaliacoes = [avaliar(ind, prob, cfg.pesos) for ind in populacao]
    historico, top = [], {}
    otimo = penalidade_minima(prob, cfg.pesos)
    melhor_penalidade, sem_melhoria = float("inf"), 0
    geracao, motivo = 0, ""

    while True:
        # Registro da geração atual e das melhores soluções
        ordem = sorted(range(len(populacao)), key=lambda i: avaliacoes[i].penalidade)
        for i in ordem[:cfg.top_solucoes]:
            top.setdefault(_chave(populacao[i]), (avaliacoes[i], _copia(populacao[i])))
        top = dict(sorted(top.items(), key=lambda kv: kv[1][0].penalidade)[:cfg.top_solucoes])

        penalidades = [a.penalidade for a in avaliacoes]
        estado = Geracao(geracao, penalidades[ordem[0]], sum(penalidades) / len(penalidades),
                         penalidades[ordem[-1]], avaliacoes[ordem[0]].conflitos, _diversidade(populacao))
        historico.append(estado)
        if ao_fim_geracao:
            ao_fim_geracao(estado)

        if estado.melhor < melhor_penalidade:
            melhor_penalidade, sem_melhoria = estado.melhor, 0
        else:
            sem_melhoria += 1

        # Critérios de parada
        if geracao >= cfg.max_geracoes:
            motivo = "número máximo de gerações"
        elif geracao >= cfg.min_geracoes and melhor_penalidade <= otimo:
            motivo = f"ótimo conhecido alcançado (penalidade mínima {otimo:.0f})"
        elif geracao >= cfg.min_geracoes and sem_melhoria >= cfg.paciencia:
            motivo = f"convergência ({cfg.paciencia} gerações sem melhoria)"
        if motivo:
            break

        # Nova geração: elitismo + filhos de pais selecionados
        nova = [_copia(populacao[i]) for i in ordem[:cfg.elitismo]]
        vistos = {_chave(i) for i in nova}
        n_filhos = cfg.tamanho_populacao - len(nova)
        if cfg.selecao == "roleta":
            pais = selecao_roleta(populacao, avaliacoes, n_filhos + 1, rng)
        else:
            pais = selecao_torneio(populacao, avaliacoes, n_filhos + 1, rng, cfg.tamanho_torneio)

        for k in range(0, len(pais) - 1, 2):
            if rng.random() < cfg.taxa_crossover:
                filhos = cruzar(pais[k], pais[k + 1], rng, cfg.crossover)
            else:
                filhos = _copia(pais[k]), _copia(pais[k + 1])
            for filho in filhos:
                for _ in range(5):  # evita inserir filhos repetidos (convergência prematura)
                    mutacao_troca(filho, rng, cfg.taxa_mutacao)
                    if rng.random() < cfg.taxa_mutacao_dirigida:
                        mutacao_dirigida(filho, prob, rng)
                    if not cfg.evitar_duplicados or _chave(filho) not in vistos:
                        break
                vistos.add(_chave(filho))
                nova.append(filho)
        populacao = nova[:cfg.tamanho_populacao]
        avaliacoes = [avaliar(ind, prob, cfg.pesos) for ind in populacao]
        geracao += 1

    melhor_aval, melhor = next(iter(top.values()))
    return Resultado(melhor, melhor_aval, list(top.values()), historico, geracao, motivo,
                     time.perf_counter() - inicio, cfg)
