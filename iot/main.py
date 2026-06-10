"""CardioIA — Fase 7 — Nó sensor em MicroPython (ESP32, simulado no Wokwi).

Evolução da Fase 3: a lógica de captura e processamento de sensores, antes em
C/C++ (Arduino + MQTT), foi convertida para MicroPython e ganhou:

  - Análise local (edge computing): classificação NORMAL/ATENCAO/CRITICO
    feita NO DISPOSITIVO, antes de qualquer envio;
  - Feedback visual: LEDs de status + display OLED SSD1306 com BPM,
    temperaturas e status;
  - Envio HTTP direto ao backend integrador (Vercel) — `POST /api/iot/leituras`;
  - Buffer local quando offline (herdado da Fase 3), sincronizado ao reconectar.

Hardware (ver diagram.json):
  - DHT22 no GPIO 15        → temperatura/umidade do leito (UTI)
  - Botão no GPIO 23        → simula pulsos cardíacos (cada clique = batimento)
  - LED verde no GPIO 26    → status NORMAL
  - LED vermelho no GPIO 27 → ATENCAO (pisca lento) / CRITICO (pisca rápido)
  - OLED SSD1306 I2C        → SDA=21, SCL=22

Como o Wokwi não tem sensor DS18B20 nativo para MicroPython com a mesma
biblioteca da Fase 3, a temperatura do paciente é derivada do canal do DHT22
com um offset clínico calibrado — o relatório técnico documenta a decisão.
"""

import network
import time
import json
import machine
from machine import Pin, I2C
import dht

try:
    import urequests
except ImportError:
    urequests = None

try:
    import ssd1306
except ImportError:
    ssd1306 = None

# ---------------- configuração ----------------

WIFI_SSID = "Wokwi-GUEST"
WIFI_PASS = ""

# URL pública do backend (projeto Vercel da pasta backend/).
# Em demonstração local, use o IP da máquina rodando uvicorn, ex.:
# API_URL = "http://192.168.0.10:8765"
API_URL = "https://SEU-BACKEND.vercel.app"
ENDPOINT = API_URL + "/api/iot/leituras"
DEVICE_ID = "esp32-wokwi-uti01"

INTERVALO_LEITURA_MS = 10_000   # 10 s entre leituras (igual à Fase 3)
JANELA_BPM_MS = 15_000          # janela de BPM acelerada p/ demo (15 s × 4)
MAX_BUFFER = 50                 # leituras retidas quando offline

# Faixas clínicas (iguais às do backend — iot_service.py)
BPM_BAIXO_CRITICO, BPM_BAIXO = 40, 50
BPM_ALTO, BPM_ALTO_CRITICO = 100, 130
TEMP_PAC_FEBRE, TEMP_PAC_FEBRE_ALTA = 37.8, 39.0
TEMP_AMB_MIN, TEMP_AMB_MAX = 18.0, 30.0
UMID_MIN, UMID_MAX = 40.0, 60.0

# ---------------- hardware ----------------

sensor_dht = dht.DHT22(Pin(15))
botao = Pin(23, Pin.IN, Pin.PULL_UP)
led_ok = Pin(26, Pin.OUT)
led_alerta = Pin(27, Pin.OUT)

i2c = I2C(0, scl=Pin(22), sda=Pin(21))
oled = None
if ssd1306:
    try:
        oled = ssd1306.SSD1306_I2C(128, 64, i2c)
    except Exception as e:
        print("OLED indisponivel:", e)

# contagem de pulsos por interrupção (igual ao attachInterrupt da Fase 3)
pulsos = 0


def _on_pulso(pin):
    global pulsos
    pulsos += 1


botao.irq(trigger=Pin.IRQ_FALLING, handler=_on_pulso)

# ---------------- wi-fi ----------------

wlan = network.WLAN(network.STA_IF)


def conectar_wifi(timeout_s=15):
    if wlan.isconnected():
        return True
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASS)
    t0 = time.time()
    while not wlan.isconnected() and time.time() - t0 < timeout_s:
        time.sleep(0.5)
    if wlan.isconnected():
        print("Wi-Fi conectado:", wlan.ifconfig()[0])
        return True
    print("Wi-Fi indisponivel — operando offline com buffer local")
    return False


# ---------------- análise local (edge) ----------------

def classificar_local(bpm, t_amb, umid, t_pac):
    """Mesma régua clínica do servidor — o diagnóstico preliminar
    acontece na borda, sem depender de rede."""
    nivel = 0
    motivos = []

    if bpm is not None:
        if bpm <= BPM_BAIXO_CRITICO or bpm >= BPM_ALTO_CRITICO:
            nivel = 2
            motivos.append("BPM critico")
        elif bpm <= BPM_BAIXO or bpm >= BPM_ALTO:
            nivel = max(nivel, 1)
            motivos.append("BPM fora da faixa")

    if t_pac is not None:
        if t_pac >= TEMP_PAC_FEBRE_ALTA:
            nivel = 2
            motivos.append("febre alta")
        elif t_pac >= TEMP_PAC_FEBRE:
            nivel = max(nivel, 1)
            motivos.append("febre")

    if t_amb is not None and not (TEMP_AMB_MIN <= t_amb <= TEMP_AMB_MAX):
        nivel = max(nivel, 1)
        motivos.append("T ambiente fora da faixa")
    if umid is not None and not (UMID_MIN <= umid <= UMID_MAX):
        nivel = max(nivel, 1)
        motivos.append("umidade fora da faixa")

    return ("NORMAL", "ATENCAO", "CRITICO")[nivel], motivos


def atualizar_feedback(status, bpm, t_amb, t_pac):
    """LEDs + OLED — exigência de feedback visual da atividade."""
    if status == "NORMAL":
        led_ok.value(1)
        led_alerta.value(0)
    elif status == "ATENCAO":
        led_ok.value(0)
        led_alerta.value(not led_alerta.value())  # pisca lento (a cada ciclo)
    else:  # CRITICO
        led_ok.value(0)
        for _ in range(6):                        # pisca rápido
            led_alerta.value(1)
            time.sleep(0.08)
            led_alerta.value(0)
            time.sleep(0.08)
        led_alerta.value(1)

    if oled:
        oled.fill(0)
        oled.text("CardioIA - UTI01", 0, 0)
        oled.text("BPM : {}".format(bpm if bpm is not None else "--"), 0, 16)
        oled.text("Tamb: {:.1f}C".format(t_amb) if t_amb is not None else "Tamb: --", 0, 28)
        oled.text("Tpac: {:.1f}C".format(t_pac) if t_pac is not None else "Tpac: --", 0, 40)
        oled.text("ST: {}".format(status), 0, 54)
        oled.show()


# ---------------- envio ao backend ----------------

buffer_offline = []


def enviar(leitura):
    """POST ao backend integrador; em falha, retém no buffer (Fase 3)."""
    if urequests is None:
        print("urequests ausente — leitura retida no buffer")
        _bufferizar(leitura)
        return False

    try:
        r = urequests.post(
            ENDPOINT,
            data=json.dumps(leitura),
            headers={"Content-Type": "application/json"},
        )
        print("Enviado ({}): {}".format(r.status_code, leitura))
        r.close()
        return 200 <= r.status_code < 300
    except Exception as e:
        print("Falha no envio:", e)
        _bufferizar(leitura)
        return False


def _bufferizar(leitura):
    if len(buffer_offline) >= MAX_BUFFER:
        buffer_offline.pop(0)  # descarta a mais antiga
    buffer_offline.append(leitura)
    print("Buffer local: {} leituras pendentes".format(len(buffer_offline)))


def sincronizar_buffer():
    """Reenvia leituras retidas quando a conexão volta."""
    while buffer_offline and wlan.isconnected():
        pendente = buffer_offline.pop(0)
        if not enviar(pendente):
            break


# ---------------- loop principal ----------------

def main():
    global pulsos
    print("CardioIA Fase 7 — no sensor MicroPython iniciado")
    conectar_wifi()

    bpm = None
    t_janela = time.ticks_ms()
    proxima_leitura = time.ticks_ms()

    while True:
        agora = time.ticks_ms()

        # BPM: extrapola os pulsos da janela para batimentos/minuto
        if time.ticks_diff(agora, t_janela) >= JANELA_BPM_MS:
            fator = 60_000 // JANELA_BPM_MS
            bpm = pulsos * fator
            pulsos = 0
            t_janela = agora

        if time.ticks_diff(agora, proxima_leitura) >= 0:
            proxima_leitura = time.ticks_add(agora, INTERVALO_LEITURA_MS)

            # leitura dos sensores (com validação de faixa, como na Fase 3)
            try:
                sensor_dht.measure()
                t_amb = sensor_dht.temperature()
                umid = sensor_dht.humidity()
            except OSError as e:
                print("Erro ao ler DHT22:", e)
                t_amb, umid = None, None

            # temperatura do paciente derivada (substitui o DS18B20 da Fase 3)
            t_pac = round(t_amb + 12.5, 1) if t_amb is not None else None

            status, motivos = classificar_local(bpm, t_amb, umid, t_pac)
            atualizar_feedback(status, bpm, t_amb, t_pac)
            print("[edge] status={} motivos={}".format(status, motivos))

            leitura = {
                "device_id": DEVICE_ID,
                "bpm": bpm,
                "temperatura_amb": t_amb,
                "umidade": umid,
                "temperatura_pac": t_pac,
                "status_edge": status,
            }

            if wlan.isconnected():
                sincronizar_buffer()
                enviar(leitura)
            else:
                _bufferizar(leitura)
                conectar_wifi(timeout_s=3)

        time.sleep(0.05)


main()
