# Segurança

Cenas são programas Python completos. Abrir um arquivo no preview ou renderizá-lo executa seu código com as permissões da sua conta. O Bamboonimation não é uma sandbox.

## Uso seguro

- Revise scripts de terceiros e suas dependências antes de executar.
- Use um ambiente virtual. Para conteúdo não confiável, use isolamento do sistema operacional e limites de recursos adequados.
- O preview deve permanecer em localhost. Não o exponha à internet ou a uma rede compartilhada.
- Não coloque chaves de API, tokens, e-mails privados, caminhos pessoais ou documentos confidenciais nos exemplos, relatórios ou commits.
- FFmpeg e bibliotecas de imagem processam arquivos externos: mantenha as dependências atualizadas e use fontes de assets confiáveis.
- O motor não precisa de conta, chave de API, serviços pagos ou telemetria para renderizar. A instalação inicial pode baixar pacotes e o executável FFmpeg fornecido por dependências.

## Reportar uma vulnerabilidade

Se o repositório oferecer o botão **Security → Report a vulnerability**, use esse canal privado. Caso esteja indisponível, peça um canal privado ao mantenedor sem publicar detalhes de exploração ou dados sensíveis em uma issue pública.

Inclua versão, sistema operacional, passos mínimos, impacto esperado e uma reprodução sem dados reais. Não acesse ou altere arquivos de terceiros para demonstrar uma falha. Correções de segurança serão priorizadas conforme impacto e capacidade dos mantenedores; não há SLA de suporte.
