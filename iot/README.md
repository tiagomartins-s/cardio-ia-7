# IoT — Nó sensor em MicroPython (ESP32 / Wokwi)

Conversão da lógica de sensores da **Fase 3** (C/C++ Arduino + MQTT) para
**MicroPython**, com análise local (edge), feedback visual (LEDs + OLED) e
envio HTTP direto ao backend integrador na Vercel.

## Arquivos

| Arquivo | Função |
|---|---|
| `main.py` | Script MicroPython: leitura DHT22, BPM por botão (IRQ), classificação local, LEDs/OLED, POST HTTP com buffer offline |
| `diagram.json` | Circuito Wokwi: ESP32 + DHT22 + botão + 2 LEDs + OLED SSD1306 |
| `ssd1306.py` | Driver do display (micropython-lib, MIT) — adicionar como arquivo extra no Wokwi |

## Como criar o projeto no Wokwi (≈ 3 minutos)

1. Acesse <https://wokwi.com> (logado) → **New Project** → **MicroPython on ESP32**.
2. Substitua o conteúdo de `main.py` pelo `main.py` desta pasta.
3. Abra a aba `diagram.json` do projeto e substitua pelo `diagram.json` desta pasta.
4. Clique no **＋** ao lado das abas → **New file** → nomeie `ssd1306.py` → cole o conteúdo do `ssd1306.py` desta pasta.
5. Em `main.py`, ajuste a constante `API_URL` para a URL pública do backend
   (ex.: `https://cardio-ia-7-backend.vercel.app`).
6. ▶ **Play** para simular. Clique no botão vermelho repetidamente para gerar
   batimentos; altere a temperatura clicando no DHT22.
7. **Save** e use **Share** para obter o link público (vai no README raiz e no relatório).

## O que observar na simulação

- **OLED**: BPM, temperatura ambiente, temperatura do paciente e status.
- **LED verde** aceso = NORMAL; **LED vermelho** piscando lento = ATENÇÃO,
  piscando rápido/fixo = CRÍTICO.
- **Serial monitor**: logs `[edge] status=...`, envios HTTP e buffer offline.
- **Plataforma web** (aba *Monitor IoT*): cada leitura aparece em até 4 s;
  leituras críticas disparam automaticamente o pipeline multiagente.

## Decisões técnicas

- **HTTP em vez de MQTT**: o fluxo exigido na Fase 7 (Sensor → MicroPython →
  Backend → IA → UI) fica mais direto com `urequests.post()` no endpoint
  `/api/iot/leituras`, sem broker intermediário. O backend já reavalia cada
  leitura e decide quando acionar a IA. (Na Fase 3 o MQTT atendia o requisito
  de dashboard Node-RED; aqui a UI é a própria plataforma.)
- **BPM por botão**: cada clique = 1 batimento, em janela de 15 s extrapolada
  para bpm (15 s × 4) — acelera a demonstração sem mudar a matemática.
- **Temperatura do paciente derivada do DHT22** (+12,5 °C de offset): substitui
  o DS18B20 da Fase 3, que não tem driver MicroPython nativo no firmware do
  Wokwi. Mexer no slider de temperatura do DHT22 simula febre.
- **Buffer offline**: leituras são retidas (máx. 50) quando o Wi-Fi cai e
  reenviadas na reconexão — comportamento herdado da Fase 3.
