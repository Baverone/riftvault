"""Passwords que NUNCA SE LEEM (2026-09-30).

André, 2026-09-30: *"em vez de discord, nao era melhor a pessoa criar uma conta
com usuario e password e ficar guardado em base de dados?? / o esqueci-me da
password fica manual, eu acedo o ficheiro e digo A pessoa a password dela /
isto e uma coisa caseira, para usar entre amigos, entao nao ha problema"*.

A primeira metade fez-se: entra-se com **utilizador e password**, guardada na
base. A segunda metade **não**, e ele aceitou a contraproposta — *"pode ficar a
tua sugestao de nova password, e melhor"*:

    ELE NUNCA LÊ A PASSWORD DE NINGUÉM. Quem se esquece não recebe a que tinha
    — recebe uma NOVA, temporária, que é obrigado a trocar ao entrar.

A RAZÃO, e é a única que interessa: **as pessoas reutilizam passwords.** A que
o amigo escolher é provavelmente a do email dele. Guardá-la em claro num PC
de casa, ao lado de um repositório público que é empurrado de 30 em 30
minutos, transforma «alguém leu o meu ficheiro» em «alguém entrou no email de
três amigos meus». O estrago não seria sobre cartas. E o fluxo dele fica
IGUAL — continua a ser ele a resolver, na consola, sem emails nem sistemas:
o que muda é que em vez de LER dá uma nova.

Por isso o que vai para a base é o resultado de uma função que não se inverte.
Ver `docs/contas-e-autenticacao.md`, secção 1.

---------------------------------------------------------------------------
O KDF: `hashlib.scrypt`, n=2**16, r=8, p=1
---------------------------------------------------------------------------
**Está na biblioteca padrão** (`hashlib.scrypt`, via OpenSSL), por isso não há
dependência nova para instalar, para actualizar, nem para explicar ao André
quando um dia reinstalar o Python. O argon2 seria a escolha de manual, mas
obrigava a um `pip install argon2-cffi` numa máquina onde a única coisa que
tem de correr sozinha é uma tarefa agendada — e a diferença prática entre
scrypt bem parametrizado e argon2id, aqui, é nenhuma.

**MEDIDO NA MÁQUINA DELE a 2026-09-30** (Python 3.14, média de 3 corridas):

    n=2**14  r=8  p=1   16,8 MB    32 ms
    n=2**15  r=8  p=1   33,6 MB    64 ms
    n=2**16  r=8  p=1   67,1 MB   130 ms   <-- o escolhido
    n=2**17  r=8  p=1  134,2 MB   262 ms

Escolheu-se o de **130 ms**: é imperceptível para quem entra (uma vez por
mês), e é o custo que um atacante paga por CADA tentativa se um dia levar o
`auth.db`. Com os 67 MB de memória por tentativa, atacar isto com uma GPU
deixa de ser interessante — é exactamente para isso que o scrypt existe.
Não se foi aos 262 ms porque o servidor é o PC dele a fazer outras coisas, e
porque com o travão de tentativas (ver `travao`) a diferença entre 130 e 260
ms não muda nada do lado de fora.

**ARMADILHA MEDIDA: o `maxmem` tem de ir explícito.** O `hashlib.scrypt` passa
`maxmem=0` ao OpenSSL, que significa «o limite por omissão», **32 MB** — e
n=2**16 precisa de 67. Sem o argumento, isto rebentava com um
`MemoryError`/`ValueError` na primeira password. Passa-se o dobro do
necessário, com folga.

O HASH GUARDADO DIZ COMO FOI FEITO
    scrypt$65536$8$1$<sal em base64>$<hash em base64>

    Auto-descritivo de propósito: o dia em que estes parâmetros ficarem
    baratos, sobe-se o `N` e **as passwords antigas continuam a entrar** — cada
    uma verifica-se com os parâmetros dela. E quem entrar com uma cifrada à
    antiga é recifrado nesse momento (`precisa_recifrar`), sem ter de saber de
    nada. Guardar só o hash e presumir os parâmetros do módulo era prender-se
    a eles para sempre.

O SAL é de 16 bytes e é POR PESSOA (`secrets.token_bytes`): duas pessoas com a
mesma password têm hashes diferentes, e uma tabela pré-calculada não serve
para nada.

---------------------------------------------------------------------------
A PASSWORD TEMPORÁRIA: quatro palavras e dois dígitos
---------------------------------------------------------------------------
    varanda-tigre-bolo-chave-47

Gerada aqui, nunca escolhida por ele — *"Password temporaria gerada por ti,
forte, facil de ditar pelo WhatsApp"*. Quatro palavras de uma lista de **256**
(8 bits cada) e dois dígitos: **38,6 bits**, ou seja 4×10^11 combinações.

O que isso vale, com números: online, com o travão de tentativas, é
inalcançável (são milhões de anos). Offline, se alguém levar o `auth.db`, são
**~1 600 anos** de um núcleo a 130 ms por tentativa. E mesmo isso é folga a
mais do que o necessário, porque a temporária **tem de ser trocada na primeira
entrada** — o tempo de vida dela é o tempo que o amigo leva a abrir o
WhatsApp.

As palavras são todas em ASCII, 3 a 6 letras, **sem acentos e sem cedilha**:
ditar «varanda» não tem nada para explicar, e escrever também não. Os hífens
entre elas dizem onde uma acaba e a outra começa, que é o que se perde quando
se lê um bloco de letras ao telefone.

---------------------------------------------------------------------------
AS REGRAS DA PASSWORD NOVA (a que a pessoa escolhe)
---------------------------------------------------------------------------
**Comprimento decente e mais nada.** Dez caracteres, e recusam-se as óbvias —
o nome dela, o nome do site, as da lista dos mais usados, e as que são um
caractere repetido.

Não há exigência de maiúscula, dígito e símbolo, e é uma decisão: essa regra
produz `Password1!` e um post-it no monitor. Dez caracteres de qualquer coisa
que a pessoa se lembre valem mais do que oito com teatro de complexidade.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import unicodedata

# --------------------------------------------------------------------------
# O KDF
# --------------------------------------------------------------------------

ALGORITMO = "scrypt"

#: Os parâmetros de hoje. Medidos na máquina dele — ver o topo do ficheiro.
N = 2 ** 16
R = 8
P = 1
DKLEN = 32
SAL_BYTES = 16

#: O `hashlib.scrypt` passa `maxmem=0` ao OpenSSL, que são **32 MB** — e o
#: n=2**16 precisa de 67. Sem isto rebentava na primeira password.
def _maxmem(n: int, r: int, p: int) -> int:
    return 128 * n * r * max(1, p) * 2 + (1 << 20)


class SenhaFraca(ValueError):
    """A password escolhida não passa as regras. A mensagem é para se mostrar."""


class HashInvalido(ValueError):
    """O que está na base não é um hash desta aplicação."""


def cifrar(senha: str, *, sal: bytes | None = None,
           n: int = N, r: int = R, p: int = P) -> str:
    """A password -> a linha que vai para a base. **Não se inverte.**

    O que sai leva os parâmetros lá dentro, para uma password cifrada hoje
    continuar a entrar quando eles subirem.
    """
    if not isinstance(senha, str) or not senha:
        raise SenhaFraca("falta escrever a password.")
    sal = sal if sal is not None else secrets.token_bytes(SAL_BYTES)
    bruto = hashlib.scrypt(senha.encode("utf-8"), salt=sal, n=n, r=r, p=p,
                           dklen=DKLEN, maxmem=_maxmem(n, r, p))
    return "$".join([ALGORITMO, str(n), str(r), str(p),
                     base64.b64encode(sal).decode("ascii"),
                     base64.b64encode(bruto).decode("ascii")])


def _partir(guardado: str) -> tuple[int, int, int, bytes, bytes]:
    partes = str(guardado or "").split("$")
    if len(partes) != 6 or partes[0] != ALGORITMO:
        raise HashInvalido(
            f"isto não é um hash do riftvault (esperava «{ALGORITMO}$n$r$p$"
            f"sal$hash»).")
    try:
        n, r, p = int(partes[1]), int(partes[2]), int(partes[3])
        sal = base64.b64decode(partes[4], validate=True)
        bruto = base64.b64decode(partes[5], validate=True)
    except (ValueError, TypeError) as e:
        raise HashInvalido(f"hash estragado: {e}") from e
    return n, r, p, sal, bruto


def confere(guardado: str, senha: str) -> bool:
    """Esta password dá aquele hash?

    Compara em TEMPO CONSTANTE (`hmac.compare_digest`): um `==` em bytes sai
    mais na primeira diferença, e isso mede-se de fora.

    Usa os parâmetros do PRÓPRIO hash e não os do módulo — é o que deixa subir
    o custo sem trancar ninguém de fora.
    """
    try:
        n, r, p, sal, bruto = _partir(guardado)
    except HashInvalido:
        return False
    if not isinstance(senha, str) or not senha:
        return False
    try:
        tentativa = hashlib.scrypt(senha.encode("utf-8"), salt=sal, n=n, r=r,
                                   p=p, dklen=len(bruto) or DKLEN,
                                   maxmem=_maxmem(n, r, p))
    except (ValueError, MemoryError):
        # Parâmetros que esta máquina não aguenta: recusa-se, não se finge que
        # está certo.
        return False
    return hmac.compare_digest(tentativa, bruto)


def precisa_recifrar(guardado: str) -> bool:
    """Foi cifrada com parâmetros mais baratos do que os de hoje?

    Chamado depois de uma entrada BEM SUCEDIDA (é a única altura em que a
    password existe em claro): recifra-se ali e a pessoa não sabe de nada.
    """
    try:
        n, r, p, _sal, _h = _partir(guardado)
    except HashInvalido:
        return True
    return (n, r, p) < (N, R, P)


# --------------------------------------------------------------------------
# A PASSWORD TEMPORÁRIA
# --------------------------------------------------------------------------

#: 256 palavras — 8 bits exactos cada uma. Todas em ASCII (sem acentos nem
#: cedilha), 3 a 6 letras, para não haver nada a explicar ao ditá-las nem a
#: escrevê-las. A lista é fixa de propósito: gerá-la de um dicionário do
#: sistema dava passwords diferentes em máquinas diferentes.
PALAVRAS = (
    "abelha agulha aldeia alho alma aluno amiga amora anel anjo arame areia "
    "arroz arte atum aula aveia azul bacia bairro bala balde banco banda "
    "barba barco barro batata beijo bicho bico bife bigode boca bola bolo "
    "bolso bomba bota bravo breve brinco bruxa bule burro cabra cacau cadeia "
    "caixa cama camelo campo canal caneta canto capa cara carne carro "
    "carta casa casaco casca cebola cego cela cesto chapa chave "
    "cheiro chuva cidade cinco cinza circo claro cobra coco colar colher "
    "comida conta copo corda coroa corpo corte coruja costa couve cova cravo "
    "cruz cubo culpa curso curva custo dado dama data dedo dente desejo dever "
    "dica dieta disco dobra doce dono dose duna duro eixo elenco elmo "
    "equipa erva escada escola escova esfera espada etapa euro exame faca "
    "fada faixa falta fama farol fase fava febre fecho feira ferro festa "
    "fibra ficha figo fila filho filme fita flor fogo folha fome fonte forma "
    "forno forte fosso foto fralda frango frase freio fresco fruta fumo funil "
    "furo gado gaiola gaita galo ganso garfo garra gato gaveta gelo gema "
    "genro gesto globo gola golfe gordo gorro gosto gota grama grande "
    "graxa greve grelha grito grupo gruta guarda guerra guia hino hora "
    "horta hotel humor ideia igreja ilha imagem isca janela jantar "
    "jardim jarra jato joelho jogada jogo joia jornal jovem juba judo juiz "
    "julho junho junta justo lado lago lama lanche largo larva "
    "lava legume leite lenda lenha leque letra liga lima limpo lindo linha "
    "lista litro livro lixo lobo local logo loja lona longe louco luta luva"
).split()

#: Quantos dígitos vão no fim. Dois, e não mais: o que dá força são as
#: palavras (8 bits cada); os dígitos são para o caso — improvável — de duas
#: gerações darem as mesmas quatro palavras.
DIGITOS = 2
QUANTAS = 4


def _bits() -> float:
    import math
    return QUANTAS * math.log2(len(PALAVRAS)) + DIGITOS * math.log2(10)


#: A força da temporária, em bits. Calculada e não escrita à mão: mudar a
#: lista ou o número de palavras muda este número sozinho.
BITS = _bits()


def temporaria() -> str:
    """Uma password nova, forte e fácil de ditar. **Nunca se guarda em claro.**"""
    palavras = [secrets.choice(PALAVRAS) for _ in range(QUANTAS)]
    numero = "".join(secrets.choice("0123456789") for _ in range(DIGITOS))
    return "-".join(palavras) + "-" + numero


# --------------------------------------------------------------------------
# AS REGRAS DA PASSWORD NOVA
# --------------------------------------------------------------------------

#: Dez. Ver o topo do ficheiro para o porquê de não haver regra de complexidade.
MINIMO = 10
MAXIMO = 256   # não é política: é para o scrypt não receber um megabyte

#: As óbvias. Lista curta de propósito — uma lista de dez mil palavras dá a
#: ilusão de rigor e não muda nada: quem escolhe `123456789012` é apanhado
#: pelas regras de forma, não por estar numa lista.
OBVIAS = frozenset({
    "password", "passwords", "palavrapasse", "palavradepasse", "senha",
    "senha123", "123456", "1234567", "12345678", "123456789", "1234567890",
    "12345678910", "0123456789", "987654321", "qwerty", "qwertyuiop",
    "asdfghjkl", "abcdefghij", "abc123456", "iloveyou", "admin", "administrador",
    "utilizador", "riftvault", "riftbound", "baverone", "cardmarket",
    "cardtrader", "colecao", "coleccao", "leblanc", "letmein", "welcome",
    "changeme", "trocaesta", "mudaresta", "asenhadela", "asenhadele",
})


def _sem_acentos(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


def _nu(s: str) -> str:
    """A forma para comparar com as óbvias: sem acentos, sem separadores."""
    return re.sub(r"[^a-z0-9]+", "", _sem_acentos(str(s or "")).lower())


def validar(nova: str, *, slug: str = "", nome: str = "") -> str:
    """As regras, ou `SenhaFraca` com a razão escrita em português.

    Devolve a password tal e qual — **não a normaliza**. Cortar espaços ou
    mudar maiúsculas aqui era mudar em silêncio a password que a pessoa acabou
    de escolher, e depois ela não entrava com o que escreveu.
    """
    s = str(nova or "")
    if not s:
        raise SenhaFraca("falta escrever a password nova.")
    if len(s) < MINIMO:
        raise SenhaFraca(
            f"a password tem de ter pelo menos {MINIMO} caracteres "
            f"(escreveste {len(s)}). Não precisa de maiúsculas nem de "
            f"símbolos — uma frase curta serve: «o meu gato dorme muito».")
    if len(s) > MAXIMO:
        raise SenhaFraca(f"a password não pode passar dos {MAXIMO} caracteres.")
    if s.strip() != s:
        # Um espaço no início ou no fim perde-se ao copiar e colar, e depois
        # ela não entra e não sabe porquê.
        raise SenhaFraca(
            "a password não pode começar nem acabar com um espaço — perde-se "
            "ao copiar e colar.")
    if len(set(s)) < 4:
        raise SenhaFraca(
            "a password é o mesmo caractere quase todo — escreve outra coisa.")

    limpa = _nu(s)
    # Compara-se também SEM os dígitos do fim: `password12345` é a forma mais
    # comum de fugir a uma lista de obviedades, e continua a ser `password`.
    if limpa in OBVIAS or re.sub(r"\d+$", "", limpa) in OBVIAS:
        raise SenhaFraca(
            "essa é uma das passwords mais usadas do mundo — escolhe outra "
            "(pôr números no fim não muda nada).")
    for proibido, o_que in ((slug, "o teu nome de utilizador"),
                            (nome, "o teu nome")):
        alvo = _nu(proibido)
        if alvo and len(alvo) >= 3 and alvo in limpa:
            raise SenhaFraca(
                f"a password não pode conter {o_que} («{proibido}») — é o "
                f"primeiro palpite de quem a tentar adivinhar.")
    if re.fullmatch(r"(?:0123456789|1234567890|9876543210)+", limpa or "x"):
        raise SenhaFraca("essa é uma sequência de números — escolhe outra.")
    return s


# --------------------------------------------------------------------------
# Higiene
# --------------------------------------------------------------------------


def esconder(senha: str) -> str:
    """Como uma password se escreve num registo, num log ou num erro.

    Existe para não haver desculpa: quem tiver de mencionar uma password numa
    mensagem chama isto. Nunca devolve um pedaço dela — nem o primeiro
    caractere, nem o comprimento exacto, que já é uma pista.
    """
    return "(password escondida)" if senha else "(vazio)"


assert len(PALAVRAS) == 256, f"a lista tem de ter 256 palavras, tem {len(PALAVRAS)}"
assert len(set(PALAVRAS)) == 256, "há palavras repetidas na lista"
