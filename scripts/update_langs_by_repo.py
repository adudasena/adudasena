import os
import sys
import json
import urllib.parse
import requests
from collections import Counter
from pathlib import Path

USERNAME = "adudasena"  # seu usuário do GitHub
README_PATH = Path("README.md")
START_TAG = "<!-- LANGS-BY-REPO:START -->"
END_TAG   = "<!-- LANGS-BY-REPO:END -->"

# Se tiver token (opcional), a API fica com mais limite de requisição
GH_TOKEN = os.getenv("GH_TOKEN")

def gh_get(url, params=None):
    headers = {"Accept": "application/vnd.github+json"}
    if GH_TOKEN:
        headers["Authorization"] = f"Bearer {GH_TOKEN}"
    r = requests.get(url, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def list_repos(username):
    # type=owner pega só o que é seu; fork=false filtramos depois
    repos = []
    page = 1
    while True:
        data = gh_get(
            f"https://api.github.com/users/{username}/repos",
            params={"per_page": 100, "page": page, "type": "owner", "sort": "pushed"}
        )
        if not data:
            break
        repos.extend(data)
        page += 1
    # filtra forks e arquivados
    repos = [r for r in repos if not r.get("fork") and not r.get("archived")]
    return repos

def count_by_language(repos):
    # conta 1 repo = 1 ponto pela linguagem principal
    langs = []
    for r in repos:
        lang = r.get("language")
        if not lang or str(lang).strip() == "":
            lang = "Outros"
        langs.append(lang)
    return Counter(langs)

def make_quickchart_url(counter):
    # ordena por contagem desc
    items = sorted(counter.items(), key=lambda kv: kv[1], reverse=True)
    labels = [k for k, _ in items]
    data = [v for _, v in items]

    chart_cfg = {
        "type": "pie",
        "data": {
            "labels": labels,
            "datasets": [{"data": data}]
        },
        # fundo transparente pra combinar com temas escuros
        "options": {"plugins": {"legend": {"position": "right"}}},
    }

    cfg_str = json.dumps(chart_cfg, ensure_ascii=False)
    encoded = urllib.parse.quote(cfg_str, safe="")
    # backgroundColor=transparent deixa sem fundo
    return f"https://quickchart.io/chart?c={encoded}&backgroundColor=transparent"

def build_markdown(counter, chart_url, total_repos):
    # Tabela + gráfico
    lines = []
    lines.append(f"**Linguagens por repositório (total: {total_repos})**")
    lines.append("")
    lines.append(f"![Linguagens por repositório]({chart_url})")
    lines.append("")
    lines.append("| Linguagem | Repositórios |")
    lines.append("|---|---:|")
    for lang, count in sorted(counter.items(), key=lambda kv: kv[1], reverse=True):
        lines.append(f"| {lang} | {count} |")
    lines.append("")
    return "\n".join(lines)

def replace_between_tags(text, start_tag, end_tag, new_content):
    if start_tag not in text or end_tag not in text:
        raise RuntimeError("Marcadores não encontrados no README. Crie <!-- LANGS-BY-REPO:START --> e <!-- LANGS-BY-REPO:END -->")
    before = text.split(start_tag)[0]
    after = text.split(end_tag)[1]
    return f"{before}{start_tag}\n{new_content}\n{end_tag}{after}"

def main():
    repos = list_repos(USERNAME)
    counter = count_by_language(repos)
    total = sum(counter.values())
    chart_url = make_quickchart_url(counter)
    new_block = build_markdown(counter, chart_url, total)

    readme = README_PATH.read_text(encoding="utf-8")
    updated = replace_between_tags(readme, START_TAG, END_TAG, new_block)

    if updated != readme:
        README_PATH.write_text(updated, encoding="utf-8")
        print("README atualizado.")
    else:
        print("Sem mudanças.")

if __name__ == "__main__":
    main()
