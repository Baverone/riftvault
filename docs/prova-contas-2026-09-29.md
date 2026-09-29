# Prova de ponta a ponta das contas — 2026-09-29

Gerado por `_revisao/_prova_contas.py`, **por HTTP de verdade** contra
o `riftvault serve` na base de ENSAIO (porta 8779), com dois
utilizadores de mentira. Não escreve no `data/` real — a coleção do
André é lida por uma cópia tirada com `VACUUM INTO`, e o `sha256` dela
no princípio e no fim é a prova de que não lhe mexeu.

Árvore: `C:\Users\Catarina\_revisao\scratch-contas`

```
==========================================================================
PROVA DE PONTA A PONTA — contas, isolamento e privacidade
worktree: C:\Users\Catarina\_revisao\scratch-contas
==========================================================================

0. A COLEÇÃO DO ANDRÉ, ANTES (base real, lida por cópia)
   sha256 1f6c9cae5e6d6145a2b6f9dc9e6371021742b2ac1de69090c4173b655e444e56
   1046 linhas · 2663 normais · 540 foil

1. ENSAIO em C:\Users\Catarina\_revisao\scratch-contas\data-ensaio
  [OK  ] o ensaio não é o data/ real — C:\Users\Catarina\_revisao\scratch-contas\data-ensaio

2. O A REGISTA-SE
  [OK  ] entrou mas ainda não tem conta — {"nome": "amigo-a-sub", "provedor": "local", "slug_sugerido": "amigo-a-sub"}
  [OK  ] a conta nasceu — {"csrf": "Ud2w266db793gUD5TGVct6PNuPR79GddobgEOIgDc7M", "nome": "amigo-a-sub", "ok": true, "slug": "miguel"}
  [OK  ] agora está dentro e pode editar — slug=miguel
  [OK  ] a coleção dele nasce PRIVADA — nada

3. O A MARCA CARTAS, E O NÚMERO SOBE
  [OK  ] três `+` deram 3 — qty=3

4. REINICIAR O SERVIDOR — O NÚMERO FICA
  [OK  ] voltou a entrar como o mesmo utilizador
  [OK  ] o 3 sobreviveu ao reinício — qty=3

5. O B REGISTA-SE, E NÃO CHEGA AO A
  [OK  ] a conta do B nasceu
  [OK  ] o B vê a coleção DELE, vazia
  [OK  ] a carta que o A marcou está a ZERO para o B — qty=0

6. AS ROTAS DE ESCRITA, UMA POR UMA
  [OK  ] sem entrar: 20/20 recusaram com 401
  [OK  ] com CSRF errado: 20/20 recusaram com 403
  [OK  ] pela porta do outro: 20/20 recusaram

7. DEPOIS DE O B TENTAR TUDO, O A ESTÁ INTACTO
  [OK  ] cada um tem o SEU ficheiro — vault.db e vault.db em pastas diferentes
  [OK  ] a coleção do A está como ele a deixou — qty=3
   A: ef843da4e4327295… (1 linhas)
   B: e3b0c44298fc1c14… (0 linhas)

8. A PRIVACIDADE DO A, NOS TRÊS VALORES
  [OK  ] «tudo» ficou guardado — {"ok":true,"publico":"tudo"}

  [OK  ] «sem-valores» ficou guardado — {"ok":true,"publico":"sem-valores"}

  [OK  ] «nada» ficou guardado — {"ok":true,"publico":"nada"}

  [OK  ] um valor inventado recusa

9. APAGAR O A NÃO MEXE UMA LINHA DO B
  [OK  ] sem escrever o nome certo, recusa — para apagar, escreve «miguel» no campo de confirmação.
  [OK  ] apagou — {"ficheiros":["vault.db"],"identidades":1,"linhas":{"cardmarket_trend":0,"copies":1,"copy_locations":0,"deck_cards":0,"deck_need_log":0,"decks":0,"foil_ops":0,"location_ops":0,"ops":3,"pending":0,"rune_counter":0,"sale_lines":0,"sale_log":0,"sealed_copies":0,"sealed_price":0,"settings":0},"ok":true,
   linhas: {"cardmarket_trend": 0, "copies": 1, "copy_locations": 0, "deck_cards": 0, "deck_need_log": 0, "decks": 0, "foil_ops": 0, "location_ops": 0, "ops": 3, "pending": 0, "rune_counter": 0, "sale_lines": 0, "sale_log": 0, "sealed_copies": 0, "sealed_price": 0, "settings": 0}
   identidades 1 · sessões 3
  [OK  ] a sessão do A morreu
  [OK  ] o B está BYTE A BYTE igual — e3b0c44298fc1c14…
  [OK  ] o B continua a entrar e a ser ele

10. A COLEÇÃO DO ANDRÉ, DEPOIS
   sha256 1f6c9cae5e6d6145a2b6f9dc9e6371021742b2ac1de69090c4173b655e444e56
  [OK  ] o sha256 da `copies` dele é o MESMO — 1046 linhas · 2663 normais · 540 foil

==========================================================================
PLACAR DA PROVA: tudo verde
==========================================================================
```
