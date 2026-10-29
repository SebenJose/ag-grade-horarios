# Dados do problema (oferta 2026/2)

| Arquivo | Conteúdo | Fonte |
|---|---|---|
| `disciplinas.json` | 23 disciplinas obrigatórias do 1º ao 4º período: código, professores, aulas semanais (teóricas + práticas) e pré-requisitos (por código) | Grade e Corpo Docente + Planos de Ensino + PPC 2023 |
| `professores.json` | docentes que dão essas disciplinas em 2026/2 e as disciplinas de cada um | Grade e Corpo Docente |
| `pre_requisitos.json` | pré-requisitos por código de disciplina | PPC 2023 (transcrito; muda só se o PPC mudar) |
| `horarios.json` | 5 dias × 12 aulas (M1–M6, T1–T6), turno integral | PPC (turno integral) + padrão UTFPR de aulas de 50 min |
| `raw/grade_corpo_docente_2026-2.html` | página salva manualmente | sistema acadêmico |

## Como atualizar

1. Abrir a página Grade e Corpo Docente, resolver o hCaptcha, clicar em Procurar e salvar com Ctrl+S em `raw/`:
   https://sistemas2.utfpr.edu.br/dpls/sistema/acad00/mpGradeCorpoDocPortal.inicio?campus=sh&curso=002
2. `python scraper/extrair_grade_docente.py dados/raw/<arquivo>.html dados/pre_requisitos.json dados`
   (busca as aulas semanais nos Planos de Ensino, que são públicos)

PPC: https://www.utfpr.edu.br/cursos/coordenacoes/graduacao/santa-helena/sh-ciencia-da-computacao/documentos/documentos-do-curso/ppc-2023.pdf
