"""Interface web do algoritmo genético.

Uso: streamlit run app.py
"""
import json
import os
from dataclasses import asdict, replace
from html import escape

import altair as alt
import pandas as pd
import streamlit as st

from ag.algoritmo import Config, executar
from ag.dados import PASTA_DADOS, carregar
from ag.fitness import VAZIO, Pesos, genes_em_conflito, penalidade_minima
from ag.paralelo import executar_varias

st.set_page_config(page_title="AG · Grade de horários", layout="wide")

# Paleta da UTFPR (o tema da página está em .streamlit/config.toml)
PRETO, AMARELO_ESCURO, CINZA = "#000000", "#E6B800", "#A6A6A6"
# Tons alternados de amarelo e cinza para distinguir as disciplinas de um mesmo período
TONS = ["#FFCC00", "#BFBFBF", "#FFE680", "#E3E3E3", "#FFF2B3", "#9E9E9E", "#FFD940"]

st.markdown("""
<style>
.grade {border-collapse: collapse; width: 100%; table-layout: fixed; font-size: .82rem}
.grade th, .grade td {border: 1px solid rgba(128,128,128,.25); padding: 4px 6px; text-align: center}
.grade td.hora {width: 78px; text-align: left; opacity: .75; white-space: nowrap}
.grade td.aula {color: #000; line-height: 1.15}
.grade td.aula small {display: block; opacity: .75; font-size: .7rem; overflow: hidden;
                      text-overflow: ellipsis; white-space: nowrap}
.grade td.choque {background: #000 !important; color: #FFCC00}
.grade tr.turno td {padding: 0; height: 6px; border: none}
h1 {border-left: 8px solid #FFCC00; padding-left: .6rem !important}
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primary"] p {color: #000 !important}
[role="tab"][aria-selected="true"], [role="tab"][aria-selected="true"] * {color: #000 !important; font-weight: 600}
[data-testid="stElementToolbar"] {display: none}
</style>
""", unsafe_allow_html=True)

prob = st.cache_resource(carregar)()
COR = {i: TONS[[x.codigo for x in prob.disciplinas if x.periodo == d.periodo].index(d.codigo) % len(TONS)]
       for i, d in enumerate(prob.disciplinas)}


def grade_html(celula):
    """Tabela da semana (M1..T6 × dias). `celula(slot)` devolve None ou (html, índice da disciplina, choque)."""
    por_dia = len(prob.aulas_dia)
    h = ['<table class="grade"><tr><th></th>' + "".join(f"<th>{d}</th>" for d in prob.dias) + "</tr>"]
    for a, aula in enumerate(prob.aulas_dia):
        if a and aula["codigo"][0] != prob.aulas_dia[a - 1]["codigo"][0]:
            h.append(f'<tr class="turno"><td colspan="{len(prob.dias) + 1}"></td></tr>')
        h.append(f'<tr><td class="hora">{aula["codigo"]} · {aula["inicio"]}</td>')
        for dia in range(len(prob.dias)):
            c = celula(dia * por_dia + a)
            if c is None:
                h.append("<td></td>")
            else:
                conteudo, g, choque = c
                h.append(f'<td class="aula{" choque" if choque else ""}" style="background:{COR[g]}">{conteudo}</td>')
        h.append("</tr>")
    return "".join(h) + "</table>"


def grade_periodo(ind, p_idx, choques):
    def celula(slot):
        g = ind[p_idx][slot]
        if g == VAZIO:
            return None
        d = prob.disciplinas[g]
        profs = ", ".join(f"{x.split()[0]} {x.split()[-1]}" for x in d.professores)
        return f"<b>{d.codigo}</b><small>{escape(profs)}</small>", g, (p_idx, slot) in choques
    return grade_html(celula)


def grade_professor(ind, prof):
    p = prob.professores.index(prof)

    def celula(slot):
        presentes = [c[slot] for c in ind if c[slot] != VAZIO and p in prob.professores_por_disciplina[c[slot]]]
        if presentes:
            return "<br>".join(f"<b>{prob.disciplinas[g].codigo}</b>" for g in presentes), presentes[0], len(presentes) > 1
    return grade_html(celula)


DISCIPLINAS = pd.DataFrame([{"período": d.periodo, "código": d.codigo, "disciplina": d.nome,
                             "professores": ", ".join(d.professores), "aulas": d.aulas_semanais,
                             "pré-requisitos": ", ".join(d.pre_requisitos)} for d in prob.disciplinas])


def grafico_evolucao(historico):
    df = pd.DataFrame([asdict(g) for g in historico]).rename(columns={"melhor": "Melhor", "media": "Média", "pior": "Pior"})
    return alt.Chart(df).transform_fold(["Melhor", "Média", "Pior"], ["serie", "penalidade"]).mark_line().encode(
        x=alt.X("numero:Q", title="Geração"),
        y=alt.Y("penalidade:Q", title="Penalidade (escala log)", scale=alt.Scale(type="log")),
        color=alt.Color("serie:N", title=None, scale=alt.Scale(domain=["Melhor", "Média", "Pior"],
                                                                range=[PRETO, AMARELO_ESCURO, CINZA])),
    ).properties(height=320)


def resumo_execucao(r):
    return {"semente": r.config.semente or "aleatória", "penalidade": r.avaliacao.penalidade,
            "conflitos": r.avaliacao.conflitos, "gerações": r.geracoes, "segundos": round(r.segundos, 1),
            "parada": r.motivo_parada}


# ---------------------------------------------------------------- parâmetros
p0, w0 = Config(), Pesos()
with st.sidebar:
    st.header("Parâmetros")
    selecao = st.radio("Seleção", ["torneio", "roleta"], horizontal=True)
    crossover = st.selectbox("Crossover", ["ox", "pbx", "periodo"],
                             format_func={"ox": "OX (baseado em ordem)", "pbx": "PBX (baseado em posição)",
                                          "periodo": "Período inteiro"}.get)
    populacao = st.slider("Tamanho da população", 20, 400, p0.tamanho_populacao, 10)
    semente = st.number_input("Semente (0 = aleatória)", 0, 10**9, 2)
    execucoes = st.number_input("Execuções em paralelo", 1, os.cpu_count() or 1, 1,
                                help="Roda várias sementes ao mesmo tempo, uma por núcleo do processador, "
                                     "e mostra a melhor. Com 1, acompanha a evolução ao vivo.")

    with st.expander("Avançado"):
        c1, c2 = st.columns(2)
        min_ger = c1.number_input("Mín. gerações", 1, 10000, p0.min_geracoes, 50)
        max_ger = c2.number_input("Máx. gerações", 1, 20000, p0.max_geracoes, 100)
        if min_ger < 500:
            st.caption("O trabalho exige pelo menos 500 gerações.")
        if max_ger < min_ger:
            st.caption(f"O máximo será igual ao mínimo ({min_ger}).")
        paciencia = st.number_input("Paciência (gerações sem melhoria)", 1, 5000, p0.paciencia, 50)
        torneio = st.slider("Tamanho do torneio", 2, 10, p0.tamanho_torneio, disabled=selecao != "torneio")
        tx_cross = st.slider("Taxa de crossover", 0.0, 1.0, p0.taxa_crossover, 0.05)
        tx_mut = st.slider("Taxa de mutação (por gene)", 0.0, 0.05, p0.taxa_mutacao, 0.001, format="%.3f")
        tx_dir = st.slider("Taxa de mutação dirigida (por indivíduo)", 0.0, 1.0, p0.taxa_mutacao_dirigida, 0.05)
        elitismo = st.slider("Elitismo", 0, 20, p0.elitismo)
        duplicados = st.checkbox("Rejeitar filhos duplicados", p0.evitar_duplicados)
        st.markdown("**Pesos da penalidade**")
        pesos = Pesos(
            professor=st.number_input("Choque de professor", 1, 100000, int(w0.professor), 100),
            pre_requisito=st.number_input("Choque de pré-requisito", 1, 100000, int(w0.pre_requisito), 100),
            aula_isolada=st.number_input("Aula isolada", 0, 1000, int(w0.aula_isolada)),
            alem_da_dupla=st.number_input("Aula além da dupla", 0, 1000, int(w0.alem_da_dupla)),
            excesso_diario=st.number_input("Excesso diário", 0, 1000, int(w0.excesso_diario)),
            janela=st.number_input("Janela", 0, 1000, int(w0.janela)),
        )

cfg = Config(tamanho_populacao=populacao, min_geracoes=min_ger, max_geracoes=max(max_ger, min_ger),
             paciencia=paciencia, selecao=selecao, tamanho_torneio=torneio, crossover=crossover,
             taxa_crossover=tx_cross, taxa_mutacao=tx_mut, taxa_mutacao_dirigida=tx_dir, elitismo=elitismo,
             evitar_duplicados=duplicados, semente=semente or None, pesos=pesos)

# ---------------------------------------------------------------- página
st.title("Grade de horários com Algoritmo Genético")
st.caption(f"Ciência da Computação · UTFPR Santa Helena · oferta 2026/2 · {len(prob.disciplinas)} disciplinas, "
           f"{len(prob.professores)} professores, {len(prob.pares_pre_requisito)} pares de pré-requisito")

aba_exec, aba_exp, aba_dados = st.tabs(["Execução", "Comparar estratégias", "Dados do problema"])

with aba_exec:
    if st.button("Executar algoritmo genético", type="primary"):
        status = st.status("Executando…", expanded=True)
        st.session_state.execucoes = None
        if execucoes == 1:
            texto, grafico, parcial = status.empty(), status.empty(), []

            def progresso(g):
                parcial.append(g)
                if g.numero % 25 == 0:
                    texto.markdown(f"Geração **{g.numero}** · melhor penalidade **{g.melhor:.0f}** · "
                                   f"conflitos {g.conflitos_melhor} · diversidade {g.diversidade:.0%}")
                    grafico.altair_chart(grafico_evolucao(parcial), width="stretch")

            st.session_state.resultado = executar(prob, cfg, progresso)
        else:
            # Sementes consecutivas a partir da escolhida (ou todas aleatórias com 0)
            barra = status.progress(0.0)
            todos = executar_varias(prob, [replace(cfg, semente=semente + i if semente else None)
                                           for i in range(execucoes)],
                                    ao_concluir=lambda k, n, _: barra.progress(k / n, f"{k} de {n} execuções concluídas"))
            st.session_state.resultado = min(todos, key=lambda r: r.avaliacao.penalidade)
            st.session_state.execucoes = pd.DataFrame([resumo_execucao(r) for r in todos])
        status.update(label="Concluído", state="complete", expanded=False)

    r = st.session_state.get("resultado")
    if r is None:
        st.markdown("Escolha os parâmetros na barra lateral e clique em **Executar**.")
    else:
        a, ind = r.avaliacao, r.melhor
        m = st.columns(4)
        m[0].metric("Choques de professor", a.conflitos_professor)
        m[1].metric("Choques de pré-requisito", a.conflitos_pre_requisito)
        m[2].metric("Penalidade", f"{a.penalidade:.0f}",
                    help=f"Ótimo conhecido: {penalidade_minima(prob, r.config.pesos):.0f}")
        m[3].metric("Gerações", r.geracoes)
        st.caption(f"Aulas isoladas {a.aulas_isoladas} · além da dupla {a.alem_da_dupla} · "
                   f"excesso diário {a.excesso_diario} · janelas {a.janelas} · "
                   f"parada: {r.motivo_parada} ({r.segundos:.1f} s)")
        choques = set(genes_em_conflito(ind, prob))
        if choques:
            st.warning(f"A grade ainda tem {a.conflitos} choque(s) (aulas em preto) e não é válida. "
                       "Aumente as gerações ou a população.")
        if st.session_state.get("execucoes") is not None:
            with st.expander(f"Melhor de {len(st.session_state.execucoes)} execuções em paralelo (semente {r.config.semente or 'aleatória'})"):
                st.dataframe(st.session_state.execucoes, hide_index=True, width="stretch")

        v_periodo, v_prof, v_evol = st.tabs(["Grade por período", "Grade por professor", "Evolução"])
        with v_periodo:
            for p_idx, p in enumerate(prob.periodos):
                st.subheader(f"{p}º período")
                st.markdown(grade_periodo(ind, p_idx, choques), unsafe_allow_html=True)
                with st.expander("Legenda"):
                    st.dataframe(DISCIPLINAS[DISCIPLINAS["período"] == p].drop(columns="período"),
                                 hide_index=True, width="stretch")
        with v_prof:
            prof = st.selectbox("Professor", prob.professores)
            st.markdown(grade_professor(ind, prof), unsafe_allow_html=True)
        with v_evol:
            st.altair_chart(grafico_evolucao(r.historico), width="stretch")
            st.altair_chart(alt.Chart(pd.DataFrame([asdict(g) for g in r.historico])).mark_line(color=PRETO).encode(
                x=alt.X("numero:Q", title="Geração"),
                y=alt.Y("diversidade:Q", title="Diversidade", axis=alt.Axis(format="%"),
                        scale=alt.Scale(domain=[0, 1]))).properties(height=200), width="stretch")
            st.caption("Diversidade: fração média de genes que diferem do gene mais comum da população em cada "
                       "posição. Cai quando a população converge.")

with aba_exp:
    st.markdown("Executa cada combinação de seleção e crossover com várias sementes, em paralelo, usando os "
                "demais parâmetros da barra lateral.")
    c1, c2, c3 = st.columns(3)
    sels = c1.multiselect("Seleções", ["torneio", "roleta"], ["torneio", "roleta"])
    cxs = c2.multiselect("Crossovers", ["ox", "pbx", "periodo"], ["ox", "pbx", "periodo"])
    n_sementes = c3.number_input("Sementes por combinação", 1, 10, 3)
    combos = [(s, c, sem) for s in sels for c in cxs for sem in range(1, n_sementes + 1)]
    if st.button(f"Executar {len(combos)} rodadas", disabled=not combos):
        barra = st.progress(0.0, "Iniciando processos…")
        resultados = executar_varias(prob, [replace(cfg, selecao=s, crossover=c, semente=sem) for s, c, sem in combos],
                                     ao_concluir=lambda k, n, _: barra.progress(k / n, f"{k} de {n} rodadas concluídas"))
        barra.empty()
        st.session_state.experimento = (
            pd.DataFrame([{"estratégia": f"{s} + {c}", **resumo_execucao(res)}
                          for (s, c, _), res in zip(combos, resultados)]),
            pd.DataFrame([{"seleção": s, "crossover": c, "numero": g.numero, "melhor": g.melhor}
                          for (s, c, _), res in zip(combos, resultados) for g in res.historico]))

    if "experimento" in st.session_state:
        tab, curvas = st.session_state.experimento
        st.dataframe(tab.groupby("estratégia").agg(
            penalidade_media=("penalidade", "mean"), melhor=("penalidade", "min"), pior=("penalidade", "max"),
            sem_conflitos=("conflitos", lambda c: f"{(c == 0).sum()}/{len(c)}"),
            geracoes_media=("gerações", "mean"), segundos_medio=("segundos", "mean"),
        ).sort_values("penalidade_media").round(1), width="stretch")
        media = curvas.groupby(["seleção", "crossover", "numero"], as_index=False)["melhor"].mean()
        st.altair_chart(alt.Chart(media).mark_line().encode(
            x=alt.X("numero:Q", title="Geração"),
            y=alt.Y("melhor:Q", title="Melhor penalidade média (log)", scale=alt.Scale(type="log")),
            color=alt.Color("crossover:N", scale=alt.Scale(domain=["ox", "pbx", "periodo"],
                                                           range=[PRETO, AMARELO_ESCURO, CINZA])),
            strokeDash=alt.StrokeDash("seleção:N", scale=alt.Scale(domain=["torneio", "roleta"],
                                                                   range=[[1, 0], [6, 3]])),
        ).properties(height=340), width="stretch")

with aba_dados:
    st.dataframe(DISCIPLINAS, width="stretch", hide_index=True)
    st.caption(" · ".join(f"{p}º período: {len(v)} aulas em {prob.n_slots} horários"
                          for p, v in prob.aulas_por_periodo.items()))
    st.caption("Fonte: " + json.load(open(PASTA_DADOS / "disciplinas.json", encoding="utf-8"))["fonte"])
