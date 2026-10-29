"""Leitura dos dados do problema (pasta `dados/`) e pré-cálculos usados pelo AG."""
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

PASTA_DADOS = Path(__file__).resolve().parent.parent / "dados"


@dataclass(frozen=True)
class Disciplina:
    codigo: str
    nome: str
    periodo: int
    professores: tuple
    aulas_semanais: int
    pre_requisitos: tuple


@dataclass
class Problema:
    disciplinas: list
    dias: list
    aulas_dia: list  # [{"codigo": "M1", "inicio": "07:30"}, ...]
    periodos: list = field(init=False)
    n_slots: int = field(init=False)
    aulas_por_periodo: dict = field(init=False)
    professores_por_disciplina: list = field(init=False)
    pares_pre_requisito: set = field(init=False)
    limite_diario: list = field(init=False)
    blocos_turno: list = field(init=False)

    def __post_init__(self):
        indice = {d.codigo: i for i, d in enumerate(self.disciplinas)}
        self.periodos = sorted({d.periodo for d in self.disciplinas})
        self.n_slots = len(self.dias) * len(self.aulas_dia)

        # Multiconjunto de genes de cada período: uma entrada por aula (índice da disciplina)
        self.aulas_por_periodo = {
            p: [i for i, d in enumerate(self.disciplinas) if d.periodo == p for _ in range(d.aulas_semanais)]
            for p in self.periodos
        }
        for p, aulas in self.aulas_por_periodo.items():
            if len(aulas) > self.n_slots:
                raise ValueError(f"{p}º período tem {len(aulas)} aulas para {self.n_slots} horários")

        nomes = sorted({p for d in self.disciplinas for p in d.professores})
        self.professores = nomes
        self.professores_por_disciplina = [tuple(nomes.index(p) for p in d.professores) for d in self.disciplinas]

        # Pares (disciplina, pré-requisito) que não podem dividir horário
        self.pares_pre_requisito = {
            (min(i, indice[c]), max(i, indice[c]))
            for i, d in enumerate(self.disciplinas) for c in d.pre_requisitos if c in indice
        }

        # Máximo de aulas de uma disciplina no mesmo dia antes de penalizar
        self.limite_diario = [max(2, math.ceil(d.aulas_semanais / 3)) for d in self.disciplinas]

        # Horários consecutivos de cada turno de cada dia (M1..M6 e T1..T6)
        por_dia = len(self.aulas_dia)
        turnos = {}
        for a, aula in enumerate(self.aulas_dia):
            turnos.setdefault(aula["codigo"][0], []).append(a)
        self.blocos_turno = [[dia * por_dia + a for a in aulas] for dia in range(len(self.dias))
                             for aulas in turnos.values()]

    def dia_do_slot(self, slot):
        return slot // len(self.aulas_dia)


def carregar(pasta=PASTA_DADOS):
    pasta = Path(pasta)
    brutos = json.load(open(pasta / "disciplinas.json", encoding="utf-8"))["disciplinas"]
    horarios = json.load(open(pasta / "horarios.json", encoding="utf-8"))
    disciplinas = [
        Disciplina(d["codigo"], d["nome"], d["periodo"], tuple(d["professores"]),
                   d["aulas_semanais"], tuple(d["pre_requisitos"]))
        for d in brutos
    ]
    return Problema(disciplinas, horarios["dias"], horarios["aulas"])
