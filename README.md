# Grade de horários com Algoritmo Genético

Trabalho de Fundamentos de Sistemas Inteligentes (UTFPR, câmpus Santa Helena): um algoritmo genético
monta a grade semanal do 1º ao 4º período do curso de Ciência da Computação, com os dados reais da
oferta 2026/2, garantindo que:

- um professor não dê duas aulas no mesmo dia e horário;
- uma disciplina não coincida com o horário de seus pré-requisitos (para quem cursa as duas);
- disciplinas do mesmo período não se sobreponham.

Além disso, o AG procura grades mais confortáveis: aulas em duplas (duas seguidas, como no artigo
de Santos e Barbosa indicado nas referências), sem excesso da mesma disciplina no dia e sem janelas
entre aulas.

## Como funciona

| Etapa | Estratégia |
|---|---|
| Cromossomo | um vetor de 60 posições (5 dias × 12 aulas) por período, contendo as aulas e os vazios; choques no mesmo período são impossíveis por construção |
| Fitness | `1 / (1 + penalidade)`: peso 1000 para choques de professor e de pré-requisito, pesos menores para aulas isoladas, blocos com mais de duas aulas seguidas, excesso diário e janelas |
| Seleção | torneio (padrão) ou roleta |
| Crossover | baseado em ordem (OX), baseado em posição (PBX) ou período inteiro de um dos pais |
| Mutação | troca de posições no mesmo período e mutação dirigida, que move aulas em choque |
| Diversidade | elitismo e rejeição de filhos duplicados |
| Parada | mínimo de 500 gerações; depois, ótimo conhecido, convergência ou máximo de gerações |

## Dados

Disciplinas e professores vêm da página "Grade e Corpo Docente" do sistema acadêmico da UTFPR,
aulas semanais dos Planos de Ensino e pré-requisitos do Projeto Pedagógico do Curso (PPC 2023).
Detalhes e como atualizar em [`dados/README.md`](dados/README.md).

## Uso

Python 3.10+, sem dependências externas.

```bash
python main.py --semente 42                 # executa e salva em resultados/<data-hora>/
python main.py --help                       # parâmetros (seleção, crossover, taxas, gerações...)
python -m unittest -v tests.test_ag         # testes
```

## Estrutura

| Pasta/arquivo | Conteúdo |
|---|---|
| `ag/dados.py` | leitura de `dados/` e pré-cálculos |
| `ag/fitness.py` | penalidades e fitness |
| `ag/operadores.py` | inicialização, seleção, crossover e mutação |
| `ag/algoritmo.py` | laço do AG, elitismo e critérios de parada |
| `ag/saida.py` | grade em texto e exportação (CSV/JSON) |
| `main.py` | linha de comando |
| `dados/` | disciplinas, professores, pré-requisitos e horários |
| `scraper/` | extração dos dados do sistema da UTFPR |
| `tests/` | testes dos operadores, do fitness e do laço |
