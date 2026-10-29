import random
import unittest
from collections import Counter

from ag.algoritmo import Config, executar
from ag.dados import carregar
from ag.fitness import VAZIO, Pesos, avaliar
from ag.paralelo import executar_varias
from ag.operadores import CROSSOVERS, cruzar, individuo_aleatorio, mutacao_dirigida, mutacao_troca

PROB = carregar()


def mesmo_conteudo(ind):
    return all(Counter(crom) == Counter(PROB.aulas_por_periodo[p] + [VAZIO] * (PROB.n_slots - len(PROB.aulas_por_periodo[p])))
               for p, crom in zip(PROB.periodos, ind))


def vazio():
    return [[VAZIO] * PROB.n_slots for _ in PROB.periodos]


def indice(codigo):
    return next(i for i, d in enumerate(PROB.disciplinas) if d.codigo == codigo)


class TestOperadores(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(1)

    def test_individuo_aleatorio_tem_todas_as_aulas(self):
        self.assertTrue(mesmo_conteudo(individuo_aleatorio(PROB, self.rng)))

    def test_crossovers_preservam_as_aulas(self):
        for tipo in CROSSOVERS:
            for _ in range(50):
                a, b = individuo_aleatorio(PROB, self.rng), individuo_aleatorio(PROB, self.rng)
                for filho in cruzar(a, b, self.rng, tipo):
                    self.assertTrue(mesmo_conteudo(filho), tipo)

    def test_mutacoes_preservam_as_aulas(self):
        ind = individuo_aleatorio(PROB, self.rng)
        for _ in range(100):
            mutacao_troca(ind, self.rng, 0.05)
            mutacao_dirigida(ind, PROB, self.rng)
        self.assertTrue(mesmo_conteudo(ind))


class TestFitness(unittest.TestCase):
    def test_choque_de_professor(self):
        ind = vazio()
        # Agnaldo dá Projeto Integrador I (3º) e Redes (4º)
        ind[2][0], ind[3][0] = indice("CC3PI1"), indice("CC4RC")
        self.assertEqual(avaliar(ind, PROB, Pesos()).conflitos_professor, 1)

    def test_choque_de_pre_requisito(self):
        ind = vazio()
        ind[0][0], ind[1][0] = indice("CC1AED1"), indice("CC2AED2")
        a = avaliar(ind, PROB, Pesos())
        self.assertEqual((a.conflitos_pre_requisito, a.conflitos_professor), (1, 0))

    def test_aula_isolada_e_janela(self):
        ind = vazio()
        d = indice("MA1LM")
        ind[0][0], ind[0][2], ind[0][3] = d, d, d  # M1, (M2 vago), M3, M4
        a = avaliar(ind, PROB, Pesos())
        self.assertEqual((a.aulas_isoladas, a.janelas), (1, 1))

    def test_bloco_alem_da_dupla(self):
        ind = vazio()
        d = indice("CC3PI1")
        ind[2][:4] = [d] * 4  # M1-M4 seguidas: duas aulas além da dupla
        ind[2][6:8] = [d] * 2  # T1-T2: dupla, sem penalidade
        a = avaliar(ind, PROB, Pesos())
        self.assertEqual((a.alem_da_dupla, a.aulas_isoladas), (2, 0))


class TestAlgoritmo(unittest.TestCase):
    def test_respeita_minimo_de_geracoes(self):
        cfg = Config(tamanho_populacao=10, min_geracoes=20, max_geracoes=20, semente=3)
        r = executar(PROB, cfg)
        self.assertEqual(r.geracoes, 20)
        self.assertEqual(len(r.historico), 21)
        self.assertTrue(mesmo_conteudo(r.melhor))

    def test_paralelo_igual_ao_sequencial(self):
        cfgs = [Config(tamanho_populacao=10, min_geracoes=15, max_geracoes=15, semente=s) for s in (1, 2, 3)]
        paralelo = executar_varias(PROB, cfgs, processos=2)
        for cfg, r in zip(cfgs, paralelo):
            self.assertEqual(r.melhor, executar(PROB, cfg).melhor)


if __name__ == "__main__":
    unittest.main()
