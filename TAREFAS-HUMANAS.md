# ✅ TAREFAS HUMANAS — o que falta para fechar a entrega

> O agente de IA já fez: todo o código (backend, web, mobile, IoT), 7 testes
> passando, **deploy da web e do backend na Vercel (já no ar!)**, relatório
> técnico em PDF, roteiro do vídeo e commits organizados.
>
> **Já funcionando agora:**
> - 🌐 Web: <https://cardio-ia-7-web.vercel.app>
> - ⚙️ API: <https://cardio-ia-7-backend.vercel.app/api/health>
>
> Abaixo, **em ordem**, o que só você pode fazer (estimativa total: ~1h30 + vídeo).

---

## 1. GitHub — repositório privado + compartilhar com o tutor (~10 min)

O repositório git local já está pronto (commits por etapa) em `C:\fiap\fase-7\cardio-ia-7`.

```powershell
cd C:\fiap\fase-7\cardio-ia-7
gh auth login                       # autenticar no GitHub (browser)
gh repo create cardio-ia-7 --private --source . --push
```

Sem o `gh`: crie o repo privado em <https://github.com/new> e depois:

```powershell
git remote add origin https://github.com/SEU-USUARIO/cardio-ia-7.git
git push -u origin main
```

- [ ] Compartilhar com o tutor: repo → **Settings → Collaborators → Add people** (usuário do tutor).

## 2. Vercel — ligar o CI/CD ao GitHub (~5 min)

Os dois projetos já existem e estão no ar (deploy feito via CLI). Falta conectá-los
ao repo para que **cada push dispare deploy automático** (requisito da atividade):

```powershell
cd C:\fiap\fase-7\cardio-ia-7\backend
npx vercel git connect

cd C:\fiap\fase-7\cardio-ia-7\web
npx vercel git connect
```

(Alternativa pelo dashboard: projeto → Settings → Git → Connect Git Repository,
definindo Root Directory `backend/` e `web/` respectivamente.)

- [ ] **Opcional (recomendado):** persistência durável — no dashboard do projeto
  `cardio-ia-7-backend` → aba **Storage** → **Create Database → Neon (Postgres)**.
  A env `POSTGRES_URL` é injetada sozinha; o backend detecta e passa a usar o
  Postgres (sem isso, usa SQLite efêmero em /tmp — funciona para a demo, mas
  os dados somem a cada cold start).

## 3. Expo / EAS — gerar o APK (~20 min, build na nuvem)

```powershell
cd C:\fiap\fase-7\cardio-ia-7\mobile
npx eas-cli login                                   # conta Expo (criar em expo.dev se não tiver)
npx eas-cli init                                    # vincula o projeto (preenche extra.eas.projectId)
npx eas-cli build -p android --profile preview      # gera o .apk na nuvem
```

- [ ] Ao terminar, copiar o **link do build** (aparece no terminal e em
  <https://expo.dev> → projeto → Builds) e colar no README (tabela de URLs).
- [ ] Baixar o `.apk` no celular Android (ou via QR Code do dashboard), instalar
  (permitir "fontes desconhecidas") e **validar: login → dashboard com dados
  cardíacos → chat**.
- [ ] Commitar o `app.json` atualizado pelo `eas init`:
  `git add mobile/app.json; git commit -m "EAS project id"; git push`

## 4. Wokwi — simulação pública em MicroPython (~10 min)

Siga [iot/README.md](iot/README.md):

1. <https://wokwi.com> → **New Project → MicroPython on ESP32**.
2. Colar `iot/main.py` em `main.py` (a URL da API já está correta).
3. Substituir o `diagram.json` pelo de `iot/diagram.json`.
4. Criar arquivo `ssd1306.py` e colar o conteúdo de `iot/ssd1306.py`.
5. ▶ Play → clicar o botão (batimentos), mexer na temperatura do DHT22.
6. **Validar o fim-a-fim:** abrir <https://cardio-ia-7-web.vercel.app> → aba
   *Monitor IoT* → as leituras do Wokwi devem aparecer em ~4 s (leitura crítica
   gera predição automática da IA).
7. **Save** → **Share** → copiar o **link público** e colar no README.

## 5. Prints comprobatórios (~10 min)

Salvar em `docs/prints/` e referenciar no README (seção "Prints do deploy"):

- [ ] Dashboard da Vercel mostrando os 2 deploys **Ready** (web e backend)
- [ ] Página de build do EAS com status **finished** (e QR Code)
- [ ] App instalado rodando no celular (foto/screenshot)
- [ ] Simulação Wokwi rodando (OLED + serial monitor)
- [ ] `git add docs/prints; git commit -m "prints do deploy"; git push`

## 6. Vídeo demonstrativo ≤ 5 min (~30 min com preparação)

- [ ] Gravar seguindo o roteiro pronto: [docs/script-video.md](docs/script-video.md)
  (cena a cena, com falas sugeridas e tempos).
- [ ] Subir (YouTube não listado / Drive) e colar o link no README.

## 7. Finalização do README (~5 min)

- [ ] Preencher **nomes dos integrantes** ao lado dos RMs (e RMs que faltam).
- [ ] Conferir a tabela de URLs: Web ✅ · API ✅ · APK (passo 3) · Wokwi (passo 4) · Vídeo (passo 6).
- [ ] `git add README.md; git commit -m "URLs e integrantes"; git push`
  (o push já redeploya tudo automaticamente se o passo 2 foi feito).

## 8. Entrega final

- [ ] Gerar/entregar o PDF do relatório: já pronto em `docs/relatorio-tecnico.pdf`
  (se alterar o markdown, regerar com `.venv\Scripts\python.exe docs\build_pdf.py`).
- [ ] Submeter na plataforma da FIAP: link do repositório privado + relatório PDF.

---

### Se algo falhar

| Sintoma | Causa provável | Correção |
|---|---|---|
| Web não mostra dados | backend dormiu (cold start) e SQLite /tmp zerou | recarregar a página; ou adicionar Postgres (passo 2) |
| Wokwi não envia leituras | `API_URL` errada no main.py | conferir a constante no topo do arquivo |
| `eas build` pede projectId | `eas init` não rodou | rodar `npx eas-cli init` antes do build |
| 401 ao abrir URL com hash (ex.: `...-ir68j8pnq-...vercel.app`) | é a URL interna do deploy | usar as URLs públicas: `cardio-ia-7-web.vercel.app` / `cardio-ia-7-backend.vercel.app` |
