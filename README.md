<p align="center">
  <img src="logo.png" alt="Missionfy" width="120">
</p>

<h1 align="center">Missionfy</h1>

<p align="center">
  <strong>Seu app de metas financeiras para Windows</strong><br>
  Acompanhe suas missões financeiras direto da bandeja do sistema.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/plataforma-Windows-blue?style=flat-square" alt="Windows">
  <img src="https://img.shields.io/badge/python-3.12-green?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/licença-MIT-yellow?style=flat-square" alt="MIT">
  <img src="https://img.shields.io/badge/versão-1.0-red?style=flat-square" alt="v1.0">
</p>

---

## O que é?

**Missionfy** é um app desktop para Windows que vive na bandeja do sistema e te ajuda a acompanhar metas financeiras. Registre receitas e despesas, defina missões, acompanhe seu progresso com gráficos e desbloqueie conquistas enquanto faz dinheiro.

## Funcionalidades

| Recurso | Descrição |
|---|---|
| **System Tray** | Ícone na bandeja com popup customizado e duplo clique para abrir painel |
| **Missões** | Crie múltiplas metas financeiras com prazos |
| **Receitas e Despesas** | Registre entradas com categorias personalizáveis |
| **Gamificação** | Sistema de XP, 5 níveis, 10 medalhas e streak diário |
| **Gráficos** | Progresso acumulado e receitas por categoria |
| **Missão Diária** | Meta sugerida por dia com status em tempo real |
| **Notificações** | Lembretes configuráveis (30min a mensal) |
| **Dark Mode** | Tema escuro inspirado no SpendeePlus |
| **Exportar CSV** | Exporte todo o histórico |
| **Backup Automático** | Backup a cada 30 minutos |
| **Atalho Global** | `Ctrl+Shift+M` abre o painel de qualquer lugar |
| **Instalador** | Setup profissional com atalhos no desktop e startup |

## Níveis

| Nível | XP necessário |
|---|---|
| Iniciante | 0 XP |
| Focado | 50 XP |
| Dedicado | 150 XP |
| Imparável | 350 XP |
| Lenda | 700 XP |

## Medalhas

| Medalha | Como desbloquear |
|---|---|
| 💰 Primeira Receita | Registre sua primeira receita |
| 🔥 3 Dias Seguidos | Bata a meta 3 dias seguidos |
| ⭐ Semana Perfeita | Bata a meta 7 dias seguidos |
| 👑 Mês Imparável | Bata a meta 30 dias seguidos |
| 🎯 25% da Missão | Atinja 25% da meta |
| 🚀 Metade do Caminho | Atinja 50% da meta |
| 💎 Quase Lá | Atinja 75% da meta |
| 🏆 Missão Completa! | Atinja 100% da meta |
| 📝 10 Registros | Faça 10 registros |
| 📊 50 Registros | Faça 50 registros |

## Instalação

### Opção 1: Instalador (recomendado)

1. Baixe o `Missionfy_Setup.exe` na aba [Releases](https://github.com/eneascruzmkt-lab/Missionfy/releases)
2. Execute e siga os passos do instalador
3. Pronto! O app abre automaticamente

### Opção 2: Executável portátil

1. Baixe o `Missionfy.exe` na aba [Releases](https://github.com/eneascruzmkt-lab/Missionfy/releases)
2. Coloque numa pasta e dê duplo clique
3. O ícone **$** aparece na bandeja do sistema

### Opção 3: Rodar do código fonte

```bash
# Clone o repositório
git clone https://github.com/eneascruzmkt-lab/Missionfy.git
cd Missionfy

# Instale as dependências
pip install pystray pillow keyboard

# Execute
python money_mission.py
```

## Compilar o .exe

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --name "Missionfy" --icon="money_mission.ico" --add-data "icon.png;." --add-data "money_mission.ico;." --add-data "fonts;fonts" money_mission.py
```

## Gerar o instalador

Requer [Inno Setup](https://jrsoftware.org/isdl.php) instalado:

```bash
iscc installer.iss
```

## Como usar

1. **Clique** no ícone $ na bandeja → menu rápido
2. **Duplo clique** → abre o painel completo
3. **Ctrl+Shift+M** → abre o painel de qualquer lugar

### Abas do painel

- **Início** — Resumo, missão diária, gamificação, gráficos
- **Registrar** — Adicionar receita ou despesa
- **Missões** — Gerenciar metas e categorias
- **Config** — Histórico, notificações

## Tech Stack

- **Python 3.12** — linguagem principal
- **tkinter** — interface gráfica
- **pystray** — ícone na bandeja do sistema
- **Pillow** — manipulação de imagens e ícones
- **Poppins** — fonte do Google Fonts
- **PyInstaller** — compilação para .exe
- **Inno Setup** — geração do instalador

## Design

Tema dark mode inspirado no [SpendeePlus](https://www.behance.net/) com paleta de cores:

- Fundo: `#0a0a0f` (preto espacial)
- Cards: `#161620`
- Accent: `#00d47e` (verde neon)
- Secundário: `#00b8d4` (ciano)

---

<p align="center">
  Desenvolvido por <a href="https://github.com/eneascruzmkt-lab"><strong>Enéas Cruz</strong></a>
</p>

<p align="center">
  <sub>Feito com Python e Claude AI</sub>
</p>
