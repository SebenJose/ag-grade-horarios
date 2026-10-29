"""Conversão do melhor indivíduo em grade legível e exportação dos resultados."""
import csv
import json
from dataclasses import asdict
from pathlib import Path

from .fitness import VAZIO


def grade_do_periodo(ind, prob, periodo):
    """Matriz [aula][dia] com o código da disciplina (ou "") em cada horário."""
    crom = ind[prob.periodos.index(periodo)]
    por_dia = len(prob.aulas_dia)
    return [[prob.disciplinas[g].codigo if (g := crom[dia * por_dia + a]) != VAZIO else ""
             for dia in range(len(prob.dias))] for a in range(por_dia)]


def tabela_texto(ind, prob, periodo):
    linhas = [f"{periodo}º período", "      " + "".join(f"{d[:7]:>9}" for d in prob.dias)]
    for aula, cel in zip(prob.aulas_dia, grade_do_periodo(ind, prob, periodo)):
        linhas.append(f"{aula['codigo']} {aula['inicio']}" + "".join(f"{c or '·':>9}" for c in cel))
    return "\n".join(linhas)


def aulas(ind, prob):
    """Lista plana de aulas alocadas (uma linha por aula)."""
    por_dia = len(prob.aulas_dia)
    for p, crom in zip(prob.periodos, ind):
        for slot, g in enumerate(crom):
            if g != VAZIO:
                d = prob.disciplinas[g]
                dia, a = divmod(slot, por_dia)
                yield {"periodo": p, "dia": prob.dias[dia], "aula": prob.aulas_dia[a]["codigo"],
                       "inicio": prob.aulas_dia[a]["inicio"], "codigo": d.codigo, "disciplina": d.nome,
                       "professores": ", ".join(d.professores)}


def salvar(resultado, prob, pasta):
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    with open(pasta / "historico.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(asdict(resultado.historico[0])))
        w.writeheader()
        w.writerows(asdict(g) for g in resultado.historico)
    with open(pasta / "grade.csv", "w", newline="", encoding="utf-8") as f:
        linhas = list(aulas(resultado.melhor, prob))
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)
    resumo = {
        "geracoes": resultado.geracoes,
        "motivo_parada": resultado.motivo_parada,
        "segundos": round(resultado.segundos, 2),
        "config": asdict(resultado.config),
        "melhores": [{**asdict(a), "fitness": a.fitness} for a, _ in resultado.top],
    }
    json.dump(resumo, open(pasta / "resumo.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    (pasta / "grade.txt").write_text("\n\n".join(tabela_texto(resultado.melhor, prob, p) for p in prob.periodos),
                                     encoding="utf-8")
