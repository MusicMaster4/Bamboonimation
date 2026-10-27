# Contribuindo com o Bamboonimation

Contribuições úteis tornam a autoria mais simples, o movimento mais expressivo ou a renderização mais previsível. Leia [README](README.md), [arquitetura](docs/architecture.md), [termos de contribuição](CONTRIBUTOR_AGREEMENT.md) e [código de conduta](CODE_OF_CONDUCT.md).

## Ambiente de desenvolvimento

```powershell
git clone https://github.com/MusicMaster4/Bamboonimation.git
cd Bamboonimation
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
```

Em Linux/macOS use `python3 -m venv .venv` e `.venv/bin/python`. Não é necessário ativar o ambiente. No Ubuntu/Debian, instale também `libegl1` conforme as [instruções de instalação](README.md#linux-e-macos); o wheel do Skia precisa dessa biblioteca mesmo para renderizar em CPU.

## Fluxo

1. Abra uma issue para mudanças extensas de API, licença ou formato de cena.
2. Crie um branch focado e preserve as alterações de outros colaboradores.
3. Mantenha o resultado de um frame determinado apenas por cena, tempo e seed. Evite estado acumulado por frame, aleatoriedade global e dependências de resolução na atuação.
4. Corrija ou acrescente testes quando o comportamento exigir. Para mudanças visuais, gere um frame anterior/posterior e um trecho curto em mais de uma resolução.
5. Atualize os exemplos e a documentação pública junto com a API.
6. Rode os testes e construa a distribuição: `python -m pytest` e `python -m build`.
7. Revise o diff, licenças de assets e possíveis dados privados. Assine a origem com `git commit -s` e envie um pull request.

## O que descrever no pull request

Explique o problema e o comportamento resultante. Informe comandos de verificação, ambiente, impacto visual e custo de renderização quando relevantes. Inclua capturas ou vídeos pequenos de cenas originais; não publique frames copiados da referência.

## Convenções

- Python 3.11 ou superior, anotações de tipos nas APIs públicas e mensagens de erro acionáveis.
- Sem chamadas de rede, telemetria ou modelos externos na importação ou renderização de cenas.
- Valide parâmetros antes de criar arquivos de saída. Não sobrescreva trabalho do usuário sem uma opção explícita.
- Prefira dependências pequenas e mantidas. Justifique novas dependências.
- Não adicione benchmarks universais: informe cena, resolução, FPS, duração, hardware, configuração e método.
- Não altere a licença de arquivos existentes nem remova avisos de terceiros.

## Ajuda e problemas

Use as [issues](https://github.com/MusicMaster4/Bamboonimation/issues) para bugs e propostas. Para problemas de segurança, siga [SECURITY.md](SECURITY.md).
