# Missionfy v2.0 - Redesign + Novas Funcionalidades

## Resumo

Redesign visual completo do Missionfy com foco em clareza, praticidade e senso de evolucao pessoal. Inclui 7 novas funcionalidades e reestruturacao do layout.

## 1. Paleta Visual (Refinado)

Evolucao da identidade atual: fundo escuro quente, verde suave, mais respiro.

| Elemento | Valor |
|---|---|
| Fundo principal | `#12121a` |
| Fundo cards | `#1c1c2e` |
| Hover | `#252538` |
| Input | `#16162a` |
| Borda | `#2e2e42` |
| Texto principal | `#f0f0f5` |
| Texto secundario | `#c8c8d8` |
| Dimmed | `#6b6b80` |
| Accent verde | `#34d399` |
| Accent secundario | `#38bdf8` |
| Amarelo | `#fbbf24` |
| Vermelho | `#f87171` |

- Cards com cantos arredondados (8px)
- Bordas sutis (1px, opacidade reduzida)
- Padding 16px nos cards
- Mais espaco entre elementos

## 2. Popup da Bandeja (Redesign)

Popup funcional com 3 areas, permitindo que 80% do uso aconteca sem abrir o painel.

### Topo - Resumo Inteligente
- Frase de contexto dinamica:
  - "Faltam R$82 pra meta de hoje"
  - "Voce esta 3 dias adiantado"
  - "Meta do dia batida! Parabens"
- Barra de progresso da meta principal
- Streak atual com icone de fogo

### Meio - Registro Rapido
- Campo de valor direto no popup (digita e aperta Enter)
- Selector receita/despesa ao lado do campo
- Abaixo: ate 4 botoes de atalhos recorrentes
- Atalhos baseados nos registros mais frequentes + fixados pelo usuario

### Rodape
- "Abrir Painel" e "Sair"

## 3. Dashboard (Redesign)

Tela unica com scroll vertical, sem abas. Hierarquia de cima pra baixo, do mais imediato ao mais distante.

### 3.1 Seu Dia (topo)
- Numero grande: "R$82 pra meta de hoje"
- Barra de progresso do dia, grossa e colorida
- Botao grande "Registrar" logo abaixo

### 3.2 Sua Semana
- 7 quadradinhos (seg a dom), coloridos conforme bateu a meta ou nao
- Streak em destaque ao lado

### 3.3 Sua Jornada
- Grafico simples de curva, evolucao semana a semana (ultimas 8 semanas)
- Marcos conquistados com icones grandes na linha do tempo
- Historico de reflexoes semanais (como se sentiu em cada semana)

### 3.4 Suas Metas
- Cards grandes, um por meta
- Barra visual clara com valor atual / valor total

### 3.5 Rodape Fixo (sempre visivel)
- 3 botoes: "Registrar", "Importar CSV", "Config"
- Icones + texto

## 4. Importacao de CSV

### Bancos suportados
- Picpay
- Banco do Brasil
- Nubank
- Bradesco

### Fluxo em 3 passos

**Passo 1 - Escolher banco**
- 4 botoes grandes com nome do banco
- Botao "Outro" pra futuro

**Passo 2 - Selecionar arquivo**
- Botao grande "Escolher arquivo CSV"
- Preview das primeiras 5 linhas
- Resumo: "23 entradas encontradas - 15 receitas, 8 despesas"

**Passo 3 - Revisar categorias**
- Lista com cada entrada: data, descricao, valor, categoria sugerida
- Clica na categoria pra trocar (dropdown)
- Cada correcao alimenta o aprendizado
- Regra salva no JSON: ex. "Mercado Livre" = "Venda"
- Botao "Confirmar tudo" no rodape

### Categorizacao automatica com aprendizado
- Começa com regras basicas por palavras-chave
- Cada correcao manual do usuario cria/atualiza uma regra
- Regras salvas no JSON de dados
- Proxima importacao usa regras aprendidas

## 5. Notificacao de Reflexao Semanal

### Mecanica
- Todo domingo as 20h
- Notificacao nativa do Windows (toast) com som
- Titulo: "Missionfy - Reflexao da Semana"
- Texto: "Como foi sua semana? Clique pra avaliar"

### Dialog ao clicar
- Resumo automatico: "Voce registrou R$1.200 esta semana, bateu a meta 5 de 7 dias"
- 3 botoes grandes: "Otima", "Boa", "Podia ser melhor"
- Campo opcional de uma linha: "Uma palavra sobre a semana"

### Historico
- Reflexoes salvas e exibidas na secao "Sua Jornada" do dashboard
- Linha do tempo com semanas + sentimento de cada uma

### Implementacao
- Usar `win10toast` ou `plyer` para toast nativo do Windows com som

## 6. Marcos Pessoais (Milestones)

### Marcos de valor
- Primeiro R$100
- Primeiro R$500
- Primeiro R$1.000
- Primeiro R$5.000
- Primeiro R$10.000

### Marcos de consistencia
- Primeira semana completa (7 dias seguidos)
- Primeiro mes acima da meta
- 3 meses seguidos acima da meta

### Marcos de habito
- 7 dias usando o app
- 30 dias usando o app
- 100 registros no total

### Comportamento
- Ao desbloquear: notificacao nativa do Windows com som celebrando
- No dashboard: marcos aparecem como pontos na linha do tempo em "Sua Jornada"
- Marcos nao conquistados aparecem em cinza com opacidade baixa

## 7. Atalhos Recorrentes

### Logica automatica
- Analisa ultimos 30 registros
- Identifica os 3-4 mais frequentes (mesma descricao + valor)
- Aparecem como botoes rapidos no popup da bandeja

### Personalizacao
- Secao "Atalhos rapidos" no Config
- Usuario pode fixar atalhos manualmente (nome + valor + categoria)
- Fixados tem prioridade sobre automaticos
- Maximo 4 atalhos no popup

## Dependencias Novas

- `win10toast` ou `plyer` - notificacoes nativas do Windows com som
- Nenhuma outra dependencia nova necessaria

## Compatibilidade

- Manter suporte a PyInstaller para gerar .exe
- Manter funcionamento como app portatil (sem instalacao)
- Dados salvos no mesmo `money_mission_data.json`
- Novos campos adicionados com `setdefault` para compatibilidade com dados existentes
