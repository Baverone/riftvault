# Relatório do dia — 2026-10-02

Escrito no fim de uma sessão em que o André esteve fora várias horas e pediu:
*"que acabes o que tens para fazer / depois de terminado faças um checkup geral
a tudo, e encontres Bugs e/ou melhorias e/ou correções e faças o que tiver que
ser feito / no final fazes um relatório do estado de tudo"*.

---

## 1. O estado, agora

| | |
|---|---|
| `main` | igual ao `origin/main`, árvore limpa |
| suite | **81 ficheiros · 2 646 testes · 0 a falhar**, 81 verdes à primeira, zero colisões |
| portão | VERDE, impressão digital dos dois lados da corrida a bater |
| site | `rift.baverone.com` no ar, raiz com `noindex` |
| coleções | André 1 057 impressões · Gonçalves 761 · Miguel 6 · Rafael 4 (privado) |
| 8770 | de pé, Google e Discord prontos |
| commits hoje | 85, em 9 merges |

As quatro coleções foram medidas por `sha256` antes e depois de **cada** merge do
dia. Nenhuma mudou por causa de código — só por ele e pelos amigos a meterem
cartas. O Gonçalves entrou o dia com 436 impressões e acabou com 761.

---

## 2. O que entrou hoje, e o que estava mal

### Funcionalidades que ele pediu

**Colar uma decklist em texto** (secção Decks, no editar, cada um na sua conta).
Lê o mesmo formato dos ficheiros `.txt` pelo MESMO código — não há segundo
leitor. Mostra o que vai gravar antes de gravar, conta as linhas que o catálogo
não conhece, e só grava com confirmação.

**Ler uma decklist de uma IMAGEM.** 31 de 31 cartas da página que ele mandou,
zero dúvidas, **sem OCR nenhum**: não há nenhum instalado na máquina, mas havia
Pillow, numpy e as 1 180 artes em cache — por isso casa-se cada recorte com a
ARTE do catálogo, o que identifica a *impressão* e não só a carta. Três coisas
que só a medição revelou: os battlefields vêm deitados na página; duas
impressões podem ter a mesma arte com molduras diferentes; e os crachás de
quantidade confundiam 3 com 8 nove vezes em 31, o que se resolveu a contar os
buracos do glifo.

**Três caixas novas nas Faltas** — Overnumbered (51 em falta, 6 660,55 €),
Alt Art (160, 1 014,90 €) e Vendetta inteira (58, 2 069,42 €), todas com preço,
total e lista para o Cardmarket. Cada uma diz a linha mais cara no cabeçalho,
porque sem isso os 6 660 € não se leem: 2 100 são UMA carta (o Baron Nashor
`UNL-238`, que ele disse a 05/09 que nunca compraria — 31% da caixa).

**Os `+`/`−` saíram da página do deck.** O `app.js` desenha-os em nove sítios e
só dois eram do deck; saíram esses e mais nada.

**As runas Alt Art contam-se POR EDIÇÃO.** Somavam as cinco edições num número
só e repetiam-no em todas: na página do OGN a Calm Rune dizia 21, e 12 dessas
eram do SFD; na do UNL dizia os mesmos 21 sem ele lá ter uma única runa.

### Correcções de segurança e de verdade

**A raiz publicada deixou de se indexar.** Nomeia o Miguel e o Gonçalves com o
valor das coleções; as páginas de cada um já tinham `noindex`, a raiz não. O
`robots.txt` que devia travar isso estava em `u/<slug>/`, um sítio que nenhum
motor de busca lê — ficou, mas o comentário que dizia que «os dois juntos fecham
as duas portas» foi corrigido: só uma fechava.

**O payload deixou de se contradizer.** Com a porta aberta e o mesmo pedido
anónimo, o `conta.json` dizia `editavel: false` e oito payloads diziam
`editable: true`. O `app.js` corrigia-o do lado do cliente. Ao torná-lo honesto
descobriu-se que o campo tinha de se partir em dois: o `app.js` usava-o também
para decidir se pedia o `conta.json`, e a versão honesta **escondia a caixa de
Entrar**.

**O rasto e os backups de cada um caem na pasta dele.** Três logs e dois
caminhos de backup escreviam sempre na pasta do dono, sem coluna que dissesse de
quem era a linha. Não era fuga pública (está tudo no `.gitignore`, verificado),
mas a promessa que o código faz — «se uma cópia aparecer num deck sem linha
aqui, é bug» — deixava de se poder verificar com quatro pessoas a escrever no
mesmo ficheiro.

**O `conta.apagar()` deixava o hash da password atrás.**

**A checklist deixou de mentir.** O `riftvault multi --verificar` dizia `[TEU]`
— «falta fazer» — à conta na Cloudflare e aos nameservers + túnel, que estão
feitos há semanas. Mandar alguém repetir um passo *com risco* que já fez é um
defeito, não um enfeite: o próprio aviso dizia «o rift.baverone.com não pode
cair». Agora MEDE: pergunta ao endereço público e lê os sinais que a própria app
escreve. Sem rede responde «NÃO SEI», nunca «falta».

### Ferramenta

**O portão dos merges tinha um furo que ele próprio não apanhava.** A impressão
digital tirava-se *depois* do ciclo: um ficheiro editado a meio da corrida dava
um placar VERDE a descrever bytes que nunca correram inteiros. Agora tiram-se
duas, uma de cada lado. Encontrado por uma das ordens, a quem aconteceu.

**A suite corre em paralelo.** Os 79 ficheiros dão exactamente o mesmo resultado
em paralelo e em série, teste a teste — não só na soma. O número de
trabalhadores saiu da medição, não do palpite: 1 → 462 s, 2 → 314, 4 → 241,
**6 → 189 s (2,4×)**. Fica nos 6 porque o 8770 e os outros três projectos correm
na mesma máquina.

**Um teste que passava por sorte.** O `test_runas_por_edicao` comparava uma
fotografia que levava um relógio dentro: falhou por **um segundo**. Passava ou
falhava conforme calhasse.

### O ai-pc

**A fuga de processos era real, mas a causa não era a que eu disse.** O runner
matava o `claude.exe`, que é um lançador: o neto — a sessão a sério — sobrevivia
a escrever na árvore. Isso explica as três ordens do dia que «morreram» e
afinal tinham feito o trabalho. Agora morre a árvore toda, folhas primeiro, e a
limpeza é por ascendência registada, nunca por nome.

**O relatório de uma ordem deixou de mentir.** `exit 3221225794` em 4 segundos é
o Windows a não conseguir criar o processo — a ordem nunca correu — e adia-se em
vez de se chamar «failed». Uma sessão ainda viva diz `indeterminado`.

**46 worktrees e 84 ramos mortos apagados, 1,25 GB libertados**, guardando tudo
o que tinha trabalho por gravar.

---

## 3. Erros meus, neste dia

Ponho-os aqui porque um relatório que só conta o que correu bem não serve para
nada.

1. **Disse que havia nove processos `claude` órfãos** a segurar 1,4 GB de uma
   ordem acabada. Eram a **aplicação de secretária do André**. Mandei medir
   antes de matar, e foi isso que impediu que lhe fechasse o Claude a meio do
   trabalho.
2. **A minha guarda do config parou um merge legítimo** depois de ele já estar
   feito, só porque o config tinha mudado — e tinha mudado de propósito. A
   pergunta certa não é «mudou?», é «perdeu alguma coisa, ou fechou a porta?».
3. **A primeira medição do paralelo deu 1,2× e quase me fez descartá-lo.**
   Estava contaminada por duas ordens pesadas a correr ao mesmo tempo.
4. **Escrevi um teste que usava um atributo que a classe não tinha.** O teste
   apanhou-o, que é para isso que serve.
5. **O documento da varredura afirma que a coleção ficou nas mesmas 1 046
   linhas do princípio ao fim** da corrida. É o número da manhã anterior: mediu
   uma cópia velha duas vezes. A coleção estava bem — o que estava mal era a
   prova.

---

## 4. Por fazer, e o que precisa de decisão dele

**Precisa de uma acção dele ou de um momento morto:**

- **O runner ainda corre o código antigo.** A correcção da fuga só pega quando
  for relançado, e relançar mata o que estiver a correr. Tentei durante 35
  minutos e houve sempre uma ordem dele do MTG a correr. É seguro: a tarefa
  `ai-pc-watchdog` relança-o em menos de 5 minutos, sem nada a fazer à mão.
- **O contador de runas por edição.** As 14 que ele contou à mão (Body 3, Calm
  3, Chaos 2, Fury 3, Mind 1, Order 2) **não têm edição gravada**. Reparti-las
  seria inventar. Se quiser um contador por edição, tem de dizer para onde vão.

**Medido e deixado como está, de propósito:**

- **`decks.so_base: true`** contradiz a regra que ele próprio deu a 17/09 e
  repetiu hoje. Virá-lo dá **zero** hoje — as duas cartas que lhe faltam não
  existem em arte nenhuma na mão dele. É uma incoerência, não um defeito, e a
  decisão é dele.
- **`robots.txt` na raiz** — viu as quatro hipóteses e escolheu só o `noindex`.
- **Eficiência:** o site são ~1,67 MB por pessoa e cada publicação reescreve 46
  ficheiros. Mede-se que isto deixa de servir **entre 10 e 15 pessoas**. Com
  quatro não se sente.
- **Seis ramos com commits fora do `main`** e doze worktrees com trabalho por
  gravar — incluindo uma com 21 ficheiros não commitados. Nenhum foi tocado.
- **`test_tarefas` do ai-pc** continua vermelho (gestor-email sem cenário de
  «verde a fingir»), como está documentado desde 30/09.
