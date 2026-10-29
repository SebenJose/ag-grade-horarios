"""Execuções independentes do AG em paralelo, uma por núcleo do processador.

Cada execução é exatamente `algoritmo.executar`; processos (e não threads) contornam o GIL do Python.
"""
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor, as_completed

from .algoritmo import executar


def executar_varias(prob, cfgs, processos=None, ao_concluir=None):
    """Executa cada configuração em um processo e devolve os resultados na ordem de `cfgs`.

    `ao_concluir(concluidas, total, resultado)` permite acompanhar o progresso.
    """
    resultados = [None] * len(cfgs)
    # "spawn" funciona igual no Linux e no Windows e é seguro dentro do servidor do Streamlit
    with ProcessPoolExecutor(min(processos or os.cpu_count() or 1, len(cfgs)),
                             multiprocessing.get_context("spawn")) as pool:
        futuros = {pool.submit(executar, prob, cfg): i for i, cfg in enumerate(cfgs)}
        for k, futuro in enumerate(as_completed(futuros), 1):
            resultados[futuros[futuro]] = futuro.result()
            if ao_concluir:
                ao_concluir(k, len(cfgs), resultados[futuros[futuro]])
    return resultados
