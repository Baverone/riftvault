"""Passwords que NUNCA SE LEEM — e desde 2026-10-31 vivem no cofre de contas.

Este módulo nasceu aqui a 2026-09-30 (o KDF, a temporária, as regras da
password nova, com as medições e as razões escritas). A 2026-10-31 mudou-se,
tal e qual, para `contas/senha.py` — o pacote `contas`, partilhado com o
mtgvault —, porque dois sites a cifrar a mesma password com dois módulos eram
duas respostas à mesma pergunta, e um dia divergiam.

O QUE FICA AQUI É UM ALIAS: importar `riftvault.senha` dá o PRÓPRIO módulo
`contas.senha` (o mesmo objecto, não uma cópia), por isso o código e os testes
que escrevem `from . import senha` continuam a falar com o mesmo `cifrar`, o
mesmo `confere` e a mesma `SenhaFraca` que o cofre usa. Ler as razões do KDF:
`contas/senha.py`.

Este import é o único que não é preguiçoso, e não precisa de ser: ninguém
importa o `senha` à cabeça de um módulo — o `auth.py`, a CLI e as rotas só o
pedem dentro das funções que tratam passwords, e o `build` nunca lá chega.
"""

import sys

from . import cofre as _cofre

_cofre.no_caminho()

import contas.senha as _contas_senha  # noqa: E402

sys.modules[__name__] = _contas_senha
