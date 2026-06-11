# -*- coding: utf-8 -*-
"""Gera docs/relatorio-tecnico.pdf (<= 5 paginas) com diagrama de arquitetura
desenhado nativamente em reportlab. Uso: python docs/build_pdf.py"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).resolve().parent / "relatorio-tecnico.pdf"

AZUL = colors.HexColor("#1d3461")
VERMELHO = colors.HexColor("#e63956")
CINZA = colors.HexColor("#5b6b8c")
FUNDO = colors.HexColor("#eef2fa")

styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1x", parent=styles["Heading1"], fontSize=15, textColor=AZUL, spaceAfter=4)
H2 = ParagraphStyle("H2x", parent=styles["Heading2"], fontSize=11.5, textColor=AZUL,
                    spaceBefore=8, spaceAfter=3)
BODY = ParagraphStyle("BODYx", parent=styles["BodyText"], fontSize=9.2, leading=12.4,
                      alignment=4, spaceAfter=4)
SUB = ParagraphStyle("SUBx", parent=BODY, textColor=CINZA, alignment=TA_CENTER, fontSize=9)
CELL = ParagraphStyle("CELLx", parent=BODY, fontSize=8.2, leading=10.5, spaceAfter=0)


class Diagrama(Flowable):
    """Diagrama de arquitetura final desenhado em vetores."""

    def __init__(self, largura=170 * mm, altura=92 * mm):
        super().__init__()
        self.width = largura
        self.height = altura

    def _caixa(self, c, x, y, w, h, titulo, linhas, cor=AZUL, fundo=FUNDO):
        c.setStrokeColor(cor)
        c.setLineWidth(1.2)
        c.setFillColor(fundo)
        c.roundRect(x, y, w, h, 3 * mm, stroke=1, fill=1)
        c.setFillColor(cor)
        c.setFont("Helvetica-Bold", 8.3)
        c.drawCentredString(x + w / 2, y + h - 5 * mm, titulo)
        c.setFont("Helvetica", 7.2)
        c.setFillColor(colors.HexColor("#26324d"))
        ty = y + h - 9.5 * mm
        for ln in linhas:
            c.drawCentredString(x + w / 2, ty, ln)
            ty -= 3.6 * mm

    def _seta(self, c, x1, y1, x2, y2, rotulo="", cor=VERMELHO):
        c.setStrokeColor(cor)
        c.setLineWidth(1.3)
        c.line(x1, y1, x2, y2)
        # ponta
        import math
        ang = math.atan2(y2 - y1, x2 - x1)
        L = 2.6 * mm
        c.setFillColor(cor)
        c.line(x2, y2, x2 - L * math.cos(ang - 0.45), y2 - L * math.sin(ang - 0.45))
        c.line(x2, y2, x2 - L * math.cos(ang + 0.45), y2 - L * math.sin(ang + 0.45))
        if rotulo:
            c.setFont("Helvetica-Oblique", 6.6)
            c.setFillColor(cor)
            c.drawCentredString((x1 + x2) / 2, (y1 + y2) / 2 + 1.6 * mm, rotulo)

    def draw(self):
        c = self.canv
        W, H = self.width, self.height

        # faixas de contexto
        c.setFont("Helvetica-Bold", 7.5)
        c.setFillColor(CINZA)
        c.drawCentredString(W * 0.135, H - 4 * mm, "EDGE — Wokwi (ESP32)")
        c.drawCentredString(W * 0.50, H - 4 * mm, "NUVEM — Vercel")
        c.drawCentredString(W * 0.865, H - 4 * mm, "USUÁRIOS")

        c.setStrokeColor(colors.HexColor("#c9d4ea"))
        c.setLineWidth(0.6)
        c.setDash(2, 2)
        c.line(W * 0.27, 0, W * 0.27, H - 7 * mm)
        c.line(W * 0.73, 0, W * 0.73, H - 7 * mm)
        c.setDash()

        # caixas
        self._caixa(c, W * 0.01, H * 0.42, W * 0.245, H * 0.46,
                    "Sensor MicroPython",
                    ["DHT22 (temp/umid)", "Botão -> BPM (IRQ)",
                     "Análise local (edge):", "NORMAL/ATENÇÃO/CRÍTICO",
                     "LED verde/vermelho", "OLED SSD1306",
                     "Buffer offline (50)"])

        self._caixa(c, W * 0.30, H * 0.46, W * 0.40, H * 0.42,
                    "Backend integrador — FastAPI (Serverless Function)",
                    ["/api/iot/leituras   /api/predicoes", "/api/triagem-nlp   /api/chat",
                     "/api/pacientes   /api/protocolos",
                     "Motores de IA embarcados:",
                     "RF 300 árvores (JSON, Python puro) - F6",
                     "Multiagente c/ handoffs e trace - F6",
                     "Ontologia + TF-IDF/LogReg - F2",
                     "NLU de intents (ex-Watson) - F5"])

        self._caixa(c, W * 0.345, H * 0.06, W * 0.31, H * 0.26,
                    "Persistência",
                    ["Postgres Neon (Marketplace)", "ou SQLite /tmp + seed",
                     "pacientes · predições ·", "leituras IoT · chat"],
                    cor=CINZA)

        self._caixa(c, W * 0.755, H * 0.60, W * 0.235, H * 0.28,
                    "Web SPA — React+Vite",
                    ["login · dashboard · IoT", "predição c/ trace · chat",
                     "CI/CD por push (Vercel)"], cor=VERMELHO,
                    fundo=colors.HexColor("#fdeef1"))

        self._caixa(c, W * 0.755, H * 0.18, W * 0.235, H * 0.28,
                    "Mobile — Expo (.apk)",
                    ["EAS Build perfil preview", "login · dados cardíacos",
                     "assistente virtual"], cor=VERMELHO,
                    fundo=colors.HexColor("#fdeef1"))

        # setas
        self._seta(c, W * 0.255, H * 0.65, W * 0.30, H * 0.65, "HTTPS POST")
        self._seta(c, W * 0.50, H * 0.46, W * 0.50, H * 0.32, "SQL", cor=CINZA)
        self._seta(c, W * 0.70, H * 0.70, W * 0.755, H * 0.74, "REST")
        self._seta(c, W * 0.70, H * 0.55, W * 0.755, H * 0.32, "REST")

        # legenda do fluxo
        c.setFont("Helvetica-Bold", 7.8)
        c.setFillColor(AZUL)
        c.drawCentredString(W / 2, 1.5 * mm,
                            "Fluxo: Sensor -> MicroPython -> Backend Python -> APIs de IA -> UI (Web/Mobile)")


def p(texto):
    return Paragraph(texto, BODY)


def tabela(dados, larguras):
    t = Table([[Paragraph(f"<b>{c}</b>", CELL) for c in dados[0]]] +
              [[Paragraph(c, CELL) for c in row] for row in dados[1:]],
              colWidths=larguras)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, FUNDO]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d4ea")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    return t


# corrige tabela de cabeçalho: estilo branco
HEADCELL = ParagraphStyle("HEADCELL", parent=CELL, textColor=colors.white)


def tabela2(dados, larguras):
    t = Table([[Paragraph(f"<b>{c}</b>", HEADCELL) for c in dados[0]]] +
              [[Paragraph(c, CELL) for c in row] for row in dados[1:]],
              colWidths=larguras)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, FUNDO]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d4ea")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    return t


def main():
    doc = SimpleDocTemplate(
        str(OUT), pagesize=A4,
        topMargin=14 * mm, bottomMargin=14 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
        title="Relatório Técnico — CardioIA Fase 7",
        author="Grupo CardioIA (FIAP)",
    )

    story = []
    story.append(Paragraph("Relatório Técnico — CardioIA Fase 7:<br/>Coração Sob Controle", H1))
    story.append(Paragraph(
        "Curso de Inteligência Artificial — FIAP · Fase 7 · Junho/2026<br/>"
        "Grupo: Tiago Martins da Silva (RM560639) · Mauricio Cortes Moreira (RM559923) · "
        "Lucas Costa dos Santos Castro (RM559625)", SUB))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("1. Visão geral", H2))
    story.append(p(
        "A Fase 7 consolida a CardioIA como <b>Plataforma de Inteligência Cardíaca Total</b>: "
        "os módulos construídos nas fases 1–6 (coleta de dados, diagnóstico NLP, monitoramento "
        "IoT, visão computacional, chatbot e sistema preditivo multiagente) foram unificados em "
        "um único produto digital com deploy profissional e CI/CD. Um <b>sensor ESP32 rodando "
        "MicroPython</b> (simulado no Wokwi) captura sinais do paciente, faz <b>análise local "
        "(edge)</b> e envia as leituras a um <b>backend integrador em Python</b>, que aciona os "
        "<b>motores de IA</b> e entrega recomendações clínicas em tempo quase-real às interfaces "
        "<b>Web (React+Vite na Vercel)</b> e <b>Mobile (APK via Expo EAS Build)</b>."))

    story.append(Paragraph("2. Diagrama de arquitetura final", H2))
    story.append(Diagrama())
    story.append(Spacer(1, 2 * mm))

    story.append(Paragraph("3. Decisões de arquitetura", H2))
    story.append(p(
        "<b>3.1 Deploy 100% Vercel.</b> A atividade permitia combinar provedores; o grupo optou "
        "por concentrar web e backend na Vercel, com um único repositório GitHub e CI/CD "
        "automático nos dois projetos a cada push. O backend FastAPI roda como <b>Serverless "
        "Function Python</b> (<i>backend/api/index.py</i> + rewrite no <i>vercel.json</i>). Três "
        "adaptações tornaram isso viável:"))
    story.append(p(
        "<b>(1) Inferência de ML em Python puro.</b> Empacotar scikit-learn+scipy+numpy "
        "(&gt;150 MB) numa serverless function é inviável. A Random Forest da Fase 6 (300 "
        "árvores) foi <b>exportada para JSON</b> (<i>ml/export_model.py</i>) e o serviço de ML "
        "caminha as árvores manualmente, reproduzindo <i>predict_proba</i> com <b>paridade "
        "verificada (delta &lt; 1e-9)</b>. O classificador textual da Fase 2 (TF-IDF + Regressão "
        "Logística, 90% de acurácia em holdout) foi exportado da mesma forma (vocabulário, IDF e "
        "coeficientes). A function final tem poucos MB e cold start baixo. "
        "<b>(2) Persistência adaptável.</b> Serverless tem filesystem efêmero: a camada de dados "
        "usa <b>Postgres gerenciado</b> (Vercel Marketplace/Neon) quando <i>POSTGRES_URL</i> "
        "existe; sem ele, SQLite em <i>/tmp</i> com seed idempotente a cada cold start mantém a "
        "demonstração operacional. <b>(3) Estado do chat em banco.</b> As sessões do chatbot são "
        "persistidas em tabela própria (não em memória), pois requisições podem atender em "
        "instâncias diferentes."))
    story.append(p(
        "<b>3.2 Conversão IoT para MicroPython (Fase 3 → 7).</b> O firmware C/C++ da Fase 3 "
        "(Arduino: DHT22 + DS18B20 + botão, MQTT/HiveMQ) foi reescrito em MicroPython "
        "(<i>iot/main.py</i>), mantendo a essência — leitura a cada 10 s, validação de faixas de "
        "UTI e buffer local offline com sincronização — e evoluindo em três pontos: "
        "<b>(a)</b> classificação clínica na borda (NORMAL/ATENÇÃO/CRÍTICO) antes de qualquer "
        "envio; <b>(b)</b> feedback visual — LEDs com padrões de pisca por severidade e OLED "
        "SSD1306 com BPM, temperaturas e status; <b>(c)</b> envio HTTP direto ao backend "
        "(<i>urequests.post</i>), eliminando o broker MQTT: o fluxo exigido fica mais curto e "
        "auditável. O DS18B20 foi substituído por temperatura derivada do DHT22 (+12,5 °C) por "
        "ausência de driver MicroPython nativo no Wokwi — mover o slider do DHT22 simula febre."))

    story.append(Paragraph("3.3 Unificação dos motores de IA", H2))
    story.append(tabela2(
        [["Motor", "Fase", "Implementação na Fase 7"],
         ["Modelo preditivo (Random Forest, AUC 0,815)", "6",
          "Exportado p/ JSON + inferência pura; fallback heurístico calibrado"],
         ["Sistema multiagente (Orquestrador → Analista de Risco → Especialista em "
          "Protocolos; tools, handoffs, trace auditável)", "6",
          "Preservado; acionado por predição manual, chat e automaticamente por leitura IoT crítica"],
         ["Triagem NLP (ontologia 22 regras + risco textual)", "2",
          "nlp_service.py + endpoint /api/triagem-nlp e tela própria na web"],
         ["Chatbot (intents Watson: emergência, exames, pressão, sintomas)", "5",
          "NLU local por palavras-chave — sem credenciais IBM; respostas dos dialog nodes "
          "preservadas; handoff para coleta guiada + pipeline multiagente"]],
        [62 * mm, 10 * mm, 98 * mm]))
    story.append(Spacer(1, 2 * mm))
    story.append(p(
        "A integração mais relevante: uma <b>leitura IoT classificada como CRÍTICA pelo servidor "
        "dispara automaticamente o pipeline multiagente</b>, registrando predição e recomendação "
        "clínica que aparecem no dashboard — sensor e IA fechados em ciclo."))

    story.append(Paragraph("4. Experiência do usuário", H2))
    story.append(p(
        "<b>Web (médico):</b> login, dashboard com indicadores de risco e fluxo do sensor em "
        "tempo quase-real (polling 4–5 s), predição com trace completo dos agentes, triagem NLP, "
        "protocolos, métricas do modelo e chat. Hierarquia visual de risco por badges coloridos "
        "(BAIXO/MODERADO/ALTO/CRÍTICO + nível de atenção). <b>Mobile (paciente):</b> login, "
        "dashboard de dados cardíacos e assistente conversacional — APK gerado pelo perfil "
        "<i>preview</i> do EAS (<i>buildType: apk</i>), pacote <i>br.com.fiap.cardioia</i>."))

    story.append(Paragraph("5. Qualidade e reprodutibilidade", H2))
    story.append(p(
        "<b>7 smoke tests</b> (pytest) cobrem health, CRUD, predição multiagente, triagem NLP, "
        "fluxo IoT (incluindo o disparo automático da IA) e os fluxos do chat (intents da Fase 5 "
        "+ triagem completa fim-a-fim). Base sintética e modelo determinísticos (seed 42); "
        "exportação com verificação automática de paridade. Repositório privado no GitHub "
        "compartilhado com o tutor; commits organizados por etapa; CI/CD ativo na Vercel."))

    story.append(Paragraph("6. Limitações e próximos passos", H2))
    story.append(p(
        "A autenticação é simplificada (MVP) e a base do modelo é sintética; a análise de imagens "
        "da Fase 4 está descrita como extensão natural (endpoint dedicado de visão computacional). "
        "Próximos passos: IdP real, dados clínicos anonimizados e predição assíncrona em escala. "
        "<b>Aviso:</b> sistema educacional — não substitui avaliação médica. Emergências: 192 (SAMU)."))

    doc.build(story)
    print(f"[ok] PDF gerado: {OUT}")


if __name__ == "__main__":
    main()
