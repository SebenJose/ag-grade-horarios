"""Extrai disciplinas e docentes do 1º ao 4º período da página "Grade e Corpo Docente"
do sistema acadêmico da UTFPR (salva manualmente, pois a consulta exige hCaptcha) e
completa cada disciplina com as aulas semanais do Plano de Ensino (página pública).

Os pré-requisitos vêm de `pre_requisitos.json` (transcritos do PPC 2023), pois a
página da grade não os informa.

Uso: python scraper/extrair_grade_docente.py "<grade salva.html>" dados/pre_requisitos.json dados/
"""
import html
import json
import re
import sys
import time
import urllib.request

BASE = "https://sistemas2.utfpr.edu.br/dpls/sistema/acad00/"
PERIODOS = range(1, 5)

RE_LINHA = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
RE_DISCIPLINA = re.compile(
    r"rowspan=\"\d+\">(\d+)</td>"                        # período
    r"<td[^>]*>(.*?)</td>"                                # optativa ([412] quando é)
    r"<td[^>]*><a[^>]*popup\('([^']+)'\)[^>]*>(\w+)</a></td>"  # link do plano + código
    r"<td[^>]*>(.*?)</td>"                                # nome
    r"<td[^>]*>(\d+)</td>",                               # carga horária
    re.S,
)
RE_DOCENTE = re.compile(
    r"&#10004;(?:<a[^>]*>)?([^<]+?)(?:</a>)?\s*<br><span[^>]*><i>([^<]+)<br>", re.S)
RE_CARGA_PLANO = re.compile(r"Total" + r"\s*\|\s*(\d+)" * 8)


def texto(fragmento):
    fragmento = re.sub(r"<(br|/p|/tr|/div)[^>]*>", "\n", fragmento, flags=re.I)
    fragmento = re.sub(r"<t[dh][^>]*>", " | ", fragmento, flags=re.I)
    return html.unescape(re.sub(r"<[^>]+>", "", fragmento))


def ler_grade(caminho):
    pagina = open(caminho, encoding="iso-8859-1").read()
    ano = re.search(r"Ano/Per.odo Atual:\s*(?:<[^>]+>\s*)*([\d/]+)", pagina).group(1)
    disciplinas = []
    for linha in RE_LINHA.findall(pagina):
        m = RE_DISCIPLINA.search(linha)
        if m:
            periodo, optativa, plano, codigo, nome, ch = m.groups()
            disciplinas.append({
                "codigo": codigo,
                "nome": html.unescape(nome).strip(),
                "periodo": int(periodo),
                "optativa": bool(optativa.strip()),
                "ch_total": int(ch),
                "plano_url": BASE + html.unescape(plano),
                "professores": [],
            })
        elif not disciplinas or "desc_" not in linha:
            continue
        # Linhas "desc_" trazem os docentes adicionais da disciplina anterior
        for nome_doc, cargo in RE_DOCENTE.findall(linha):
            disciplinas[-1]["professores"].append({"nome": html.unescape(nome_doc).strip(),
                                                   "cargo": cargo.strip()})
    return ano, disciplinas


def aulas_semanais(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})) as r:
        pagina = r.read().decode("iso-8859-1")
    at, ap = RE_CARGA_PLANO.search(texto(pagina)).groups()[:2]
    return int(at), int(ap)


def main(grade_html, pre_requisitos_json, saida):
    ano, grade = ler_grade(grade_html)
    grade = [d for d in grade if d["periodo"] in PERIODOS and not d["optativa"]]
    pre_requisitos = json.load(open(pre_requisitos_json, encoding="utf-8"))["pre_requisitos"]
    codigos = {d["codigo"] for d in grade}
    faltando = {c for pres in pre_requisitos.values() for c in pres} - codigos
    if faltando:
        sys.exit(f"Pré-requisitos com códigos fora da grade: {faltando}")

    for d in grade:
        d.pop("optativa")
        d["aulas_teoricas"], d["aulas_praticas"] = aulas_semanais(d["plano_url"])
        d["aulas_semanais"] = d["aulas_teoricas"] + d["aulas_praticas"]
        d["pre_requisitos"] = pre_requisitos.get(d["codigo"], [])
        time.sleep(0.5)  # gentileza com o servidor da universidade

    professores = {}
    for d in grade:
        for p in d["professores"]:
            professores.setdefault(p["nome"], {**p, "disciplinas": []})["disciplinas"].append(d["codigo"])
        d["professores"] = [p["nome"] for p in d["professores"]]

    cabecalho = {"fonte": "UTFPR - Grade e Corpo Docente (sistema acadêmico) + Planos de Ensino; pré-requisitos do PPC 2023",
                 "ano_periodo": ano}
    json.dump({**cabecalho, "disciplinas": grade},
              open(f"{saida}/disciplinas.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump({**cabecalho, "professores": sorted(professores.values(), key=lambda p: p["nome"])},
              open(f"{saida}/professores.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("Ano/período:", ano)
    for d in grade:
        print(f'{d["periodo"]} {d["codigo"]:8} {d["aulas_semanais"]:2} aulas  {d["nome"][:42]:42} '
              f'{", ".join(d["professores"])}  <- {d["pre_requisitos"]}')


if __name__ == "__main__":
    main(*sys.argv[1:4])
