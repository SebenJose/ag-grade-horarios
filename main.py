"""Executa o algoritmo genético pela linha de comando.

Exemplo: python main.py --semente 2 --selecao torneio --crossover ox
         python main.py --semente 1 --execucoes 8   # 8 sementes em paralelo, salva a melhor
"""
import argparse
from dataclasses import replace
from datetime import datetime

from ag.algoritmo import Config, executar
from ag.dados import carregar
from ag.paralelo import executar_varias
from ag.saida import salvar, tabela_texto


def main():
    cfg = Config()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    # dest = nome do campo em Config, para montar a configuração direto dos argumentos
    ap.add_argument("--populacao", dest="tamanho_populacao", type=int, default=cfg.tamanho_populacao)
    ap.add_argument("--min-geracoes", dest="min_geracoes", type=int, default=cfg.min_geracoes)
    ap.add_argument("--max-geracoes", dest="max_geracoes", type=int, default=cfg.max_geracoes)
    ap.add_argument("--paciencia", type=int, default=cfg.paciencia)
    ap.add_argument("--selecao", choices=["torneio", "roleta"], default=cfg.selecao)
    ap.add_argument("--crossover", choices=["ox", "pbx", "periodo"], default=cfg.crossover)
    ap.add_argument("--taxa-crossover", dest="taxa_crossover", type=float, default=cfg.taxa_crossover)
    ap.add_argument("--taxa-mutacao", dest="taxa_mutacao", type=float, default=cfg.taxa_mutacao)
    ap.add_argument("--taxa-mutacao-dirigida", dest="taxa_mutacao_dirigida", type=float,
                    default=cfg.taxa_mutacao_dirigida)
    ap.add_argument("--elitismo", type=int, default=cfg.elitismo)
    ap.add_argument("--semente", type=int)
    ap.add_argument("--execucoes", type=int, default=1,
                    help="execuções independentes em paralelo (sementes consecutivas); salva a melhor")
    ap.add_argument("--saida", default=f"resultados/{datetime.now():%Y%m%d-%H%M%S}")
    args = vars(ap.parse_args())
    execucoes, saida = args.pop("execucoes"), args.pop("saida")
    cfg = Config(**args)
    prob = carregar()

    def progresso(g):
        if g.numero % 100 == 0:
            print(f"geração {g.numero:5}  melhor {g.melhor:8.0f}  média {g.media:9.1f}  "
                  f"conflitos {g.conflitos_melhor}  diversidade {g.diversidade:.0%}")

    if execucoes > 1:
        sementes = [None if cfg.semente is None else cfg.semente + i for i in range(execucoes)]

        def concluida(k, n, res):
            print(f"{k}/{n}  semente {res.config.semente}  penalidade {res.avaliacao.penalidade:.0f}  "
                  f"conflitos {res.avaliacao.conflitos}  {res.geracoes} gerações")

        todos = executar_varias(prob, [replace(cfg, semente=s) for s in sementes], ao_concluir=concluida)
        r = min(todos, key=lambda x: x.avaliacao.penalidade)
        print(f"Melhor execução: semente {r.config.semente}")
    else:
        r = executar(prob, cfg, progresso)

    print()
    for p in prob.periodos:
        print(tabela_texto(r.melhor, prob, p), end="\n\n")
    a = r.avaliacao
    print(f"Parada: {r.motivo_parada} após {r.geracoes} gerações ({r.segundos:.1f}s)")
    print(f"Choques de professor: {a.conflitos_professor} | choques de pré-requisito: {a.conflitos_pre_requisito}")
    print(f"Aulas isoladas: {a.aulas_isoladas} | além da dupla: {a.alem_da_dupla} | "
          f"excesso diário: {a.excesso_diario} | janelas: {a.janelas}")
    print(f"Penalidade: {a.penalidade:.0f} | fitness: {a.fitness:.6f}")
    salvar(r, prob, saida)
    print(f"Resultados salvos em {saida}/")


if __name__ == "__main__":
    main()
