# Pomodoro Timer - Design Spec

## Resumo

Timer Pomodoro integrado ao popup da bandeja do Missionfy. Simples, pratico, sem gamificacao.

## Localizacao

No popup da bandeja, entre o resumo inteligente e o registro rapido.

## Visual

- Timer grande mostrando "25:00" centralizado
- Indicador da fase: "Foco" em ACCENT (verde) ou "Pausa" em YELLOW
- Botao "Iniciar" (vira "Pausar" quando rodando, "Continuar" quando pausado)
- Botao "Pular" ao lado pra avancar pra proxima fase
- Contador: "Pomodoro 3/4" (reseta ao fechar o app)

## Comportamento

- Ao terminar foco: popup abre automaticamente mostrando "Pausa! 5min", inicia pausa
- Ao terminar pausa: popup abre mostrando "Foco!", inicia proximo ciclo
- Pausar congela o timer, Continuar retoma
- Pular avanca pra proxima fase imediatamente
- Timer roda em background mesmo com popup fechado (thread separada)

## Configuracao

- Tempo de foco: padrao 25 minutos (configuravel no Config)
- Tempo de pausa: padrao 5 minutos (configuravel no Config)
- Novos campos no data JSON via setdefault:
  - `settings.pomodoro_focus`: int (minutos, padrao 25)
  - `settings.pomodoro_break`: int (minutos, padrao 5)

## Dados

- Nao salva historico de pomodoros
- Nao da XP
- Estado do timer vive apenas em memoria (atributos da classe Missionfy)

## Estado em memoria

```python
self._pomo_phase = "idle"  # "idle", "focus", "break"
self._pomo_remaining = 0    # segundos restantes
self._pomo_count = 0        # ciclos completos na sessao
self._pomo_running = False   # True se timer esta contando
```

## Integracao

- Timer roda em thread daemon separada, tick a cada segundo
- Quando fase termina, chama `_show_tray_popup` pra abrir o popup
- Config de tempos acessivel na janela de Config existente
