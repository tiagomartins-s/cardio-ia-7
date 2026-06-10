# Roteiro do vídeo demonstrativo (≤ 5 minutos)

> Demonstração fim-a-fim: hardware (Wokwi) → backend (Vercel) → web/APK.
> Grave a tela (OBS/Loom) com narração. Tempos sugeridos abaixo somam ~4m30s.

## Preparação (antes de gravar)

- [ ] Abrir 4 janelas: Wokwi (projeto salvo), URL pública da web (Vercel), celular com APK instalado (ou espelhado via scrcpy), e `/api/health` do backend no navegador.
- [ ] Fazer login na web antes (depois deslogar — o login será mostrado no vídeo).
- [ ] Deixar a simulação Wokwi parada, pronta para o Play.

## Cena 1 — Abertura (0:00–0:30)

**Mostrar:** README do repositório (diagrama mermaid).
**Falar:** "Esta é a CardioIA Fase 7 — a integração de todas as fases anteriores
em uma única plataforma: o sensor em MicroPython no Wokwi, o backend Python na
Vercel com os motores de IA das fases 2, 5 e 6, e as interfaces web e mobile."

## Cena 2 — Backend no ar (0:30–1:00)

**Mostrar:** `https://...backend.vercel.app/api/health` no navegador.
**Falar:** "O backend FastAPI roda como serverless function na Vercel. O health
mostra a Random Forest da Fase 6 carregada — 300 árvores exportadas para JSON
com inferência em Python puro — e o motor NLP da Fase 2 com a ontologia médica."

## Cena 3 — Hardware no Wokwi (1:00–2:00)

**Mostrar:** simulação rodando; clicar o botão várias vezes (batimentos);
aumentar a temperatura do DHT22; apontar o OLED e os LEDs; abrir o serial monitor.
**Falar:** "O firmware da Fase 3 foi convertido de C++ para MicroPython. O
dispositivo classifica os sinais localmente — vejam o OLED e o LED mudando para
ATENÇÃO/CRÍTICO — e envia cada leitura por HTTPS para o backend. Sem Wi-Fi, as
leituras ficam num buffer local e sincronizam depois."

## Cena 4 — Web: login e dado chegando (2:00–3:15)

**Mostrar:** URL pública da Vercel → tela de login → entrar → Dashboard com BPM
atualizando → aba Monitor IoT com a leitura crítica e a predição automática →
aba Predição IA executando o pipeline com trace dos agentes.
**Falar:** "Na URL pública da Vercel, após o login, o dashboard mostra as
leituras do sensor em tempo quase-real. A leitura crítica disparou
automaticamente o pipeline multiagente — Orquestrador, Analista de Risco e
Especialista em Protocolos — e a recomendação clínica já aparece aqui, com o
trace completo das mensagens entre os agentes."

## Cena 5 — Chat e NLP (3:15–4:00)

**Mostrar:** aba Chat — enviar "Estou com muita dor no peito", responder a
coleta guiada, mostrar o resultado da triagem; aba Triagem NLP com um exemplo.
**Falar:** "O chatbot da Fase 5 foi reimplementado sem dependência do Watson —
as mesmas intents, agora com handoff para a triagem por IA. E a triagem por
texto livre usa a ontologia e o classificador da Fase 2."

## Cena 6 — Mobile/APK (4:00–4:30)

**Mostrar:** celular com o APK instalado: login, dashboard com os mesmos dados
do sensor, chat.
**Falar:** "O mesmo backend serve o app Android, gerado pelo EAS Build com o
perfil preview. Login, dados cardíacos em tempo real e o assistente, na palma
da mão."

## Encerramento (4:30–4:45)

**Mostrar:** diagrama de arquitetura.
**Falar:** "Sensor, MicroPython, backend Python, IA e interfaces — o ciclo
completo da CardioIA, com deploy contínuo a cada push. Obrigado!"
