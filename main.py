"""Executa o algoritmo genético pela linha de comando.

Exemplo: python main.py --semente 42 --selecao torneio --crossover ox
"""
import argparse
from datetime import datetime

from ag.algoritmo import Config, executar
from ag.dados import carregar
from ag.saida import salvar, tabela_texto


def main():
    cfg = Config()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--populacao", type=int, default=cfg.tamanho_populacao)
    ap.add_argument("--min-geracoes", type=int, default=cfg.min_geracoes)
    ap.add_argument("--max-geracoes", type=int, default=cfg.max_geracoes)
    ap.add_argument("--paciencia", type=int, default=cfg.paciencia)
    ap.add_argument("--selecao", choices=["torneio", "roleta"], default=cfg.selecao)
    ap.add_argument("--crossover", choices=["ox", "pbx", "periodo"], default=cfg.crossover)
    ap.add_argument("--taxa-crossover", type=float, default=cfg.taxa_crossover)
    ap.add_argument("--taxa-mutacao", type=float, default=cfg.taxa_mutacao)
    ap.add_argument("--taxa-mutacao-dirigida", type=float, default=cfg.taxa_mutacao_dirigida)
    ap.add_argument("--elitismo", type=int, default=cfg.elitismo)
    ap.add_argument("--semente", type=int)
    ap.add_argument("--saida", default=f"resultados/{datetime.now():%Y%m%d-%H%M%S}")
    args = ap.parse_args()

    cfg = Config(tamanho_populacao=args.populacao, min_geracoes=args.min_geracoes,
                 max_geracoes=args.max_geracoes, paciencia=args.paciencia, selecao=args.selecao,
                 crossover=args.crossover, taxa_crossover=args.taxa_crossover,
                 taxa_mutacao=args.taxa_mutacao, taxa_mutacao_dirigida=args.taxa_mutacao_dirigida,
                 elitismo=args.elitismo, semente=args.semente)
    prob = carregar()

    def progresso(g):
        if g.numero % 100 == 0:
            print(f"geração {g.numero:5}  melhor {g.melhor:8.0f}  média {g.media:9.1f}  "
                  f"conflitos {g.conflitos_melhor}  diversidade {g.diversidade:.0%}")

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
    salvar(r, prob, args.saida)
    print(f"Resultados salvos em {args.saida}/")


if __name__ == "__main__":
    main()
