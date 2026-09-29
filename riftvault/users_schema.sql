-- QUEM SÃO OS UTILIZADORES (2026-09-29): *"Amigos meus querem usar o site para
-- organizar a coleccao deles"*. Ver `riftvault/utilizador.py` e
-- `docs/multi-utilizador.md`.
--
-- ESTE FICHEIRO É APLICADO EM DOIS SÍTIOS, e a diferença entre eles é toda a
-- questão da privacidade:
--
--   `data/users/registo.db`   O REGISTO DO SERVIÇO: uma linha por utilizador.
--                             Está no `.gitignore`, e TEM de estar.
--   cada `vault.db`           A linha do DONO daquele ficheiro, e só essa. É
--                             para o ficheiro se explicar a quem o abrir ou o
--                             restaurar de um backup — não é o registo.
--
-- PORQUE É QUE O REGISTO NÃO VIVE NO `vault.db` DO ANDRÉ. Porque esse ficheiro
-- está commitado num repositório PÚBLICO e é empurrado de 30 em 30 minutos pela
-- tarefa `riftvault-publicar`. Com o registo lá dentro, registar um amigo
-- publicava-lhe o NOME e o SLUG no GitHub, para sempre e com histórico — e um
-- amigo que escolha manter a coleção privada ficava à mesma com a existência
-- publicada. É a mesma armadilha que fez a coleção de cada um ir para um
-- ficheiro próprio; o registo não podia ficar do lado público.
--
-- Uma definição só, em vez de uma cópia em cada base: duas escritas da mesma
-- tabela divergem, e esta é a tabela que decide de quem são os dados.
CREATE TABLE IF NOT EXISTS users (
    user_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    nome       TEXT NOT NULL,
    -- O subdomínio (`<slug>.rift.baverone.com`) E o nome da pasta em
    -- `data/users/`. Validado em `utilizador.validar_slug`: minúsculas,
    -- dígitos e hífen — o que um DNS e um nome de pasta aceitam os dois, e o
    -- que impede um slug de fugir da pasta.
    slug       TEXT NOT NULL UNIQUE,
    criado_em  TEXT NOT NULL,
    -- O QUE O PÚBLICO VÊ (2026-09-29): `nada` | `sem-valores` | `tudo`. Ver
    -- `riftvault/privacidade.py`.
    --
    -- A OMISSÃO É `nada`, A MAIS FECHADA, e é decisão: publicar a coleção de
    -- outra pessoa tem de ser um acto ESCOLHIDO e não uma coisa que se herda
    -- de um valor por omissão. Uma página pública indexa-se e fica em cache em
    -- sítios que não controlamos — na prática não se despublica. O André fica
    -- em `tudo`, que é o que ele já escolheu e tem hoje.
    --
    -- Quem MANDA é a cópia do REGISTO; a que viaja dentro de cada `vault.db` é
    -- descritiva (`db._carimbar_dono`), para o ficheiro se explicar a quem o
    -- restaura.
    publico    TEXT NOT NULL DEFAULT 'nada'
               CHECK (publico IN ('nada', 'sem-valores', 'tudo')),
    -- ONDE A IDENTIDADE VAI ENCAIXAR — e continua VAZIO de propósito. Esta
    -- corrida é a fundação do modelo de dados, não a autenticação.
    --
    -- NÃO SE ESCREVE AQUI UM IDENTIFICADOR DE PESSOA, nem opaco: esta tabela
    -- viaja em `SELECT *` por todo o lado, e a linha do André viaja para um
    -- repositório público dentro do `vault.db` dele. As credenciais e o mapa
    -- identidade→utilizador vivem numa base à parte, fora do Git.
    auth_ref   TEXT
);
