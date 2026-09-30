# Prova de ponta a ponta das passwords — 2026-09-30

Gerado por `_revisao/_prova_senhas.py`, **por HTTP de verdade** contra
o `riftvault serve` na base de ENSAIO (porta 8779), com duas contas
criadas pelo comando que ele vai correr (`riftvault conta --criar`).
Não escreve no `data/` real — a coleção do André é lida por uma cópia
tirada com `VACUUM INTO`, e o `sha256` dela no princípio e no fim é a
prova de que não lhe mexeu.

Árvore: `C:\Users\Catarina\Desktop\Riftbound`

```
==========================================================================
PROVA DE PONTA A PONTA — entrar com PASSWORD
árvore: C:\Users\Catarina\Desktop\Riftbound
==========================================================================

0. A COLEÇÃO DO ANDRÉ, ANTES (base real, lida por cópia)
   sha256 1f6c9cae5e6d6145a2b6f9dc9e6371021742b2ac1de69090c4173b655e444e56
   1046 linhas · 2663 normais · 540 foil

1. ENSAIO em C:\Users\Catarina\Desktop\Riftbound\data-ensaio
  [OK  ] o ensaio não é o data/ real — C:\Users\Catarina\Desktop\Riftbound\data-ensaio

2. ELE CRIA AS CONTAS (o comando que vai correr a sério)
  [OK  ] `conta --criar miguel` deu uma temporária de 4 palavras — cabra-campo-lista-larva-89
  [OK  ] e a do joão é outra — lindo-custo-hotel-faixa-84
  [OK  ] a lista diz o estado e NUNCA a password

3. O MIGUEL ENTRA COM A TEMPORÁRIA — E NÃO PODE FAZER NADA
  [OK  ] entrou — {"nome": "miguel", "ok": true, "senha_temporaria": true, "slug": "miguel"}
  [OK  ] o site diz que a password é temporária
  [OK  ] e que NÃO é editável
  [OK  ] escrever com a temporária dá 403 — entraste com a password temporária que o André te deu. Escolhe uma password tua 
  [OK  ] e LER também — a temporária andou pelo WhatsApp

4. A PASSWORD ERRADA NÃO ENTRA, E A MENSAGEM NÃO DENUNCIA NADA
  [OK  ] password errada: 401
  [OK  ] nome que não existe: a MESMA resposta — o nome ou a password não estão certos. Se te esqueceste, pede ao André

5. O MIGUEL ESCOLHE A PASSWORD DELE
  [OK  ] uma password curta é recusada com a razão — a password tem de ter pelo menos 10 caracteres (escreveste 5). Não precisa de ma
  [OK  ] sem a password actual não troca
  [OK  ] com a actual certa, troca — {"csrf":"tC9G_Ocbh4PCtM0woXN8wB3xVaEMt2qdaaPFk4hHZqo","ok":true}

  [OK  ] o site abriu
  [OK  ] a temporária deixou de servir

6. O MIGUEL MARCA CARTAS, E O NÚMERO SOBE
  [OK  ] três `+` deram 3 — qty=3

7. REINICIAR O SERVIDOR — O NÚMERO FICA E A PASSWORD TAMBÉM
  [OK  ] voltou a entrar com a password DELE
  [OK  ] o 3 sobreviveu ao reinício — qty=3

8. O JOÃO ENTRA, E NÃO CHEGA AO MIGUEL
  [OK  ] o João entrou com a temporária dele
  [OK  ] escolheu a dele — {"csrf":"pHzA0UjFv_2b80jMgz7qk6hXhVLRSgbu6r_LoZCHXZE","ok":true}

  [OK  ] o João vê a coleção DELE
  [OK  ] a carta que o Miguel marcou está a ZERO para o João — qty=0
  [OK  ] a password do Miguel não entra na conta do João

9. AS ROTAS DE ESCRITA, UMA POR UMA
  [OK  ] sem entrar: 20/20 recusaram com 401
  [OK  ] com CSRF errado: 20/20 recusaram com 403
  [OK  ] pela porta do outro: 20/20 recusaram

10. O «ESQUECI-ME»: ELE DÁ UMA NOVA, NÃO LÊ A ANTIGA
  [OK  ] o comando correu
  [OK  ] deu outra password, diferente das duas anteriores — casaco-elmo-equipa-cebola-14
  [OK  ] e em lado nenhum aparece a que ele tinha escolhido
  [OK  ] a password DELE não está no auth.db em claro
  [OK  ] as sessões antigas dele foram fechadas

11. APAGAR O MIGUEL NÃO MEXE NO JOÃO
  [OK  ] o João marcou 5 cópias de uma carta dele — {"applied":5,"duplicate":false,"foil":0,"locations":[{"label":"Cole\u00e7\u00e3o","loc":"colecao","qty":5}],"op_id":1,"p
  [OK  ] o `--apagar --sim` correu — sers\miguel
e do auth.db: 1 senhas
a cópia ficou em C:\Users\Catarina\Desktop\Riftbound\data-ensaio\backups\conta-miguel-20260930-101223.zip
  [OK  ] apagou também a password e as sessões dele — ['e do auth.db: 1 senhas']
  [OK  ] a coleção do João está byte a byte igual — 18da537cbcc9dc97… · 1 linhas
  [OK  ] o Miguel já não entra
  [OK  ] o João continua a entrar

12. O TRAVÃO DAS TENTATIVAS
  [OK  ] ao fim de umas tentativas erradas passa a 429 — códigos: [401, 401, 401, 401, 429, 429, 429]
  [OK  ] e trava a password CERTA também (senão não travava nada) — password errada demasiadas vezes (5 vezes nesta conta). Espera 59 segundos e tenta outra v

13. A COLEÇÃO DO ANDRÉ, DEPOIS
   sha256 1f6c9cae5e6d6145a2b6f9dc9e6371021742b2ac1de69090c4173b655e444e56
   1046 linhas · 2663 normais · 540 foil
  [OK  ] o sha256 é o mesmo do princípio

==========================================================================
TUDO VERDE.
==========================================================================
```
