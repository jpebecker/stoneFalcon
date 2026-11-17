"""F9.1 (v6): captura as telas do protótipo seguindo o roteiro do LEIA-ME (depois de "Reiniciar a demo").

Na v6 as telas mostram as fotos das personas e as abas novas: Roteiros e Perguntas da Ferramenta (só da Helena) e Plugins.

Pré-requisito: o app rodando em http://localhost:8765 (iniciar.bat). Modo simulado: sem chave nem internet.
Uso:  .venv/Scripts/python.exe capturar_telas.py
Saída: entregaveis/telas/*.png (1600×900). No fim, reinicia a demo de novo para deixar o app limpo.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE = os.environ.get("STONEFALCON_URL", "http://localhost:8765").rstrip("/")   # outro endereço: STONEFALCON_URL=...
API = BASE + "/api/v1"
PASTA = Path(__file__).resolve().parents[1] / "telas"
PASTA.mkdir(exist_ok=True)


def api(metodo, caminho, quem, corpo=None):
    r = requests.request(metodo, API + caminho, headers={"X-Usuario": quem}, json=corpo, timeout=60)
    r.raise_for_status()
    return r.json()


def agente(nome_parcial: str) -> str:
    for a in api("GET", "/agentes", "helena"):
        if nome_parcial.lower() in a["nome"].lower():
            return a["id"]
    raise LookupError(nome_parcial)


op = webdriver.ChromeOptions()
op.add_argument("--headless=new")
op.add_argument("--window-size=1600,900")
op.add_argument("--force-device-scale-factor=1.5")
op.add_argument("--hide-scrollbars")
nav = webdriver.Chrome(options=op)
espera = WebDriverWait(nav, 20)


def entrar(quem: str):
    nav.get(BASE + "/")
    nav.execute_script("localStorage.setItem('stonefalcon.perfil', arguments[0]);", quem)


def abrir(caminho: str, quem: str, aguardar_texto: str | None = None, pausa=1.5):
    entrar(quem)
    nav.get(BASE + caminho)
    if aguardar_texto:
        espera.until(EC.presence_of_element_located((By.XPATH, "//*[contains(normalize-space(.), %r)]" % aguardar_texto)))
    time.sleep(pausa)


def foto(nome: str):
    nav.save_screenshot(str(PASTA / (nome + ".png")))
    print("ok", nome)


def clicar_texto(texto: str, tag="*"):
    el = espera.until(EC.element_to_be_clickable((By.XPATH, "//%s[contains(normalize-space(.), %r)]" % (tag, texto))))
    nav.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    el.click()


try:
    api("POST", "/demo/reiniciar", "helena")

    # 1. Estúdio: exemplo -> montar -> canvas
    abrir("/estudio", "marina", "Montar meu agente")
    clicar_texto("troca de maquininha", "button")
    time.sleep(0.5)
    clicar_texto("Montar meu agente", "button")
    espera.until(EC.presence_of_element_located((By.XPATH, "//*[contains(., 'Testar no sandbox') or contains(., 'Publicar')]")))
    time.sleep(2.5)
    foto("01-estudio-canvas")

    # 2. Agente com ação sensível (Rafael, L1003): para pedindo confirmação
    tri = agente("chargeback")
    exe = api("POST", "/agentes/%s/executar" % tri, "rafael", {"entrada": {"lojista_id": "L1003"}})
    abrir("/execucoes/%s" % exe["id"], "rafael", "Confirmar", pausa=2)
    foto("02-execucao-acao-sensivel")
    nav.execute_script("window.scrollTo(0, 0)")

    # 3. Saúde e alerta: Lucas derruba o cadastro; Marina executa; a execução escala e o alerta chega
    api("POST", "/ferramentas/consultar_lojista/falha", "lucas", {"falha": "fora_do_ar"})
    duv = agente("dúvidas")
    for _ in range(3):
        api("POST", "/agentes/%s/executar" % duv, "marina", {"entrada": {"lojista_id": "L1001", "pergunta": "Quando cai meu repasse?"}})
    abrir("/saude", "marina", "Saúde", pausa=2.5)
    foto("03-saude-alerta")
    abrir("/alertas", "marina", "lerta", pausa=2)
    foto("04-alertas")
    api("POST", "/ferramentas/consultar_lojista/falha", "lucas", {"falha": None})

    # 4. Governança: auditoria com cadeia íntegra
    abrir("/auditoria", "lucas", "íntegra", pausa=2)
    foto("05-auditoria")

    # 5. Gestão: painel executivo (5 critérios), finanças e calculadora
    abrir("/painel", "helena", "ROI", pausa=3)
    foto("06-painel-executivo")
    abrir("/financas", "helena", "roteador", pausa=3)
    foto("07-financas")
    abrir("/financas/calculadora", "helena", "Payback", pausa=3)
    foto("08-calculadora")
    abrir("/ferramentas", "lucas", "Reter repasses", pausa=2)
    foto("09-catalogo")

    # 6. v6: acesso por perfil e marketplace de plugins
    abrir("/roteiros", "helena", "Roteiros guiados", pausa=2)
    foto("10-roteiros-helena")
    abrir("/perguntas", "helena", "Perguntas da Ferramenta", pausa=2)
    foto("11-perguntas-da-ferramenta")
    abrir("/plugins", "marina", "Plugins", pausa=2)
    foto("12-plugins-vitrine")
    # Thiago integra o Slack, cria o agente da troca de maquininha (que avisa o canal) e o usa: a página do Slack mostra a mensagem
    api("POST", "/roteiros/thiago/reiniciar", "thiago")
    api("POST", "/plugins/slack/integrar", "thiago")
    descricao = ("Quando o lojista pede troca de maquininha eu confiro o cadastro, a regra de troca e o estoque do modelo ao mesmo tempo, "
                 "abro o chamado na logística, aviso o lojista e aviso o canal da logística no Slack. Levo uns 12 minutos.")
    bp = api("POST", "/estudio/sugerir", "thiago", {"descricao": descricao})["blueprint"]
    ag = api("POST", "/agentes", "thiago", {"blueprint": bp, "nota": "captura"})["id"]
    api("POST", "/agentes/%s/publicar" % ag, "thiago")
    api("POST", "/agentes/%s/executar" % ag, "thiago", {"entrada": {"lojista_id": "L1003", "modelo": "Maquininha Smart",
                                                                   "relato": "A tela ficou preta e a maquininha não liga mais."}})
    abrir("/plugins/slack", "thiago", "Visão consolidada", pausa=3)
    foto("13-plugin-slack-consolidado")
finally:
    nav.quit()
    try:
        api("POST", "/demo/reiniciar", "helena")
    except Exception as e:   # noqa: BLE001
        print("aviso: não reiniciou a demo:", e)
