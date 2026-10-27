# Estudo integral da referência e critérios de qualidade

A referência é **[CEREAL! — Animated Student Film](https://www.youtube.com/watch?v=nCKwUB8EVbc)**, do canal **XrayAlphaCharlie**, com crédito de filme para **Xierra Cansino**. O estudo procura entender desenho, atuação, montagem e exposição para orientar animações originais. Não distribui o filme, seus frames, personagens, áudio ou identidade gráfica.

**Resultado das duas primeiras rodadas:** os exemplos demonstram cartoon programável, personagens originais e renderização local. A segunda rodada melhorou planos, contato e seleção de desenhos, mas a revisão sequencial ainda encontrou defeitos de atuação, continuidade e enquadramento. **Essas duas rodadas não receberam aprovação de qualidade dinâmica ou artística.** As rodadas seguintes produziram novos renders e rechecagens; o estado atual está em [Validação](validation.md). Acrescentar funções ou alterar o código não é, sozinho, uma aprovação de qualidade.

## Método e limites da evidência

O arquivo analisado tem **1280 × 720**, **24 fps** e **2.035 frames decodificados**. O primeiro índice é 0 e o último é 2.034; os timestamps são `índice / 24`. O último frame começa em 84,750 s e seu intervalo de exibição termina em aproximadamente **84,792 s**.

A revisão foi dividida entre **cinco agentes de IA (agente principal e quatro subagentes)** em intervalos contíguos. Trata-se de análise assistida por IA, sem certificação humana ou revisão profissional independente. Foram geradas **85 folhas de contato**, com 24 frames consecutivos por folha, em miniaturas de 320 × 180. Não houve descarte temporal: as folhas contêm todos os frames decodificados, em ordem. A última possui 19 frames reais; os cinco espaços vazios restantes não pertencem ao vídeo. Os derivados e relatórios locais de revisão ficam fora do versionamento público.

| Intervalo atribuído | Frames inclusivos | Folhas | Quantidade |
| --- | --- | --- | ---: |
| Início / apresentação | 0–407 | 000–016 | 408 |
| Desenvolvimento | 408–815 | 017–033 | 408 |
| Cozinha / transformação | 816–1.223 | 034–050 | 408 |
| Clímax / retorno | 1.224–1.631 | 051–067 | 408 |
| Créditos / gag final / encerramento | 1.632–2.034 | 068–084 | 403 |

A cobertura exaustiva é de **miniaturas**, com inspeções adicionais de frames selecionados na resolução original para confirmar olhos, dedos, materiais, luz e contorno. Isso é mais amplo que selecionar apenas algumas poses bonitas, mas não significa que cada um dos 2.035 frames tenha sido ampliado individualmente a 720p. Miniaturas em uma grade de 4 × 6 podem esconder fases muito pequenas, detalhe de contorno e artefatos de compressão; as ampliações selecionadas reduzem esse limite, sem eliminá-lo. A análise temporal também precisa de reprodução em velocidade normal: folhas de contato não provam, sozinhas, cadência percebida, áudio ou sincronização.

Hashes, diferenças de pixels e proporções de pixels alterados são sensíveis à compressão, granulação e mudanças em efeitos. Eles ajudam a localizar mudanças, mas **não medem a quantidade exata de desenhos novos**. Um corpo pode estar em hold enquanto câmera, fumaça, fogo ou outro plano mudam. As observações sobre desenhos em pares são visuais e locais, não uma regra inferida para todo o filme.

## O que a referência faz

### Desenha a atuação, não apenas a posição

O personagem conserva identidade por cabelo, roupa, olhos, proporções e objetos reconhecíveis, enquanto a silhueta muda muito. Perfil, costas, três quartos, rosto comprimido, mão em escorço e corpo alongado usam soluções de desenho diferentes. A continuidade não depende de repetir o mesmo contorno frontal.

No começo, a caminhada e o uso do telefone coexistem com deslocamento de cenário e atraso do cabelo. Mais tarde, o corpo atravessa uma passagem escura por um desenho de silhueta grande e irregular, a mandíbula abre para bocejar e braços/pernas se reorganizam ao perder o equilíbrio. Esses gestos não podem ser descritos apenas por translação, rotação e escala de um recorte fixo.

### Usa tempos diferentes para cada parte

Há desenhos frequentemente expostos em pares, mas também pausas longas, piscadas curtas, acentos de um frame e câmera movendo sobre poses mantidas. Olhos podem indicar uma intenção antes de cabeça, ombros e mãos. Cabelo, tecido e objetos seguem com atraso.

Uma quantização global como `floor(t * 12) / 12` é uma ferramenta de exposição limitada, não a descrição completa desse ritmo. A atuação precisa de seleção de desenho e exposição por camada ou por parte, preservando holds genuínos onde a história pede.

### Alterna planos com propósito

O filme passa por acompanhamento lateral, corredor longo, ângulo inclinado, detalhe de produto, close de rosto, cozinha, ponto de vista de dentro da geladeira, mão em primeiro plano, ângulo de chão, exterior e planos de queda com perspectiva oposta. A geometria é desenhada para cada ponto de vista.

O close não é apenas uma aproximação decorativa: ele torna legível uma decisão dos olhos, um contato de dedos ou a mudança de forma de um objeto. O plano geral seguinte devolve contexto à consequência. Um zoom suave e contínuo sobre um único cenário frontal não demonstra esse repertório.

### Mantém contatos durante mudanças grandes

A mão envolve uma embalagem com dedos em camadas diferentes, o punho continua ligado ao objeto durante o corte, os pés têm relação com o chão e uma garra permanece apoiada no telhado enquanto o pescoço se alonga. Ancoragem e ordem de oclusão precisam continuar corretas mesmo quando o desenho é substituído.

### Faz efeitos com forma e consequência

Fogo, fumaça, estilhaços e movimentos rápidos têm famílias de silhuetas, sobreposições e evolução. Uma nuvem pode encobrir uma transformação e revelar outro enquadramento. Uma fumaça pode nascer de uma borda que queima; uma fagulha se separa e continua seu percurso. Não são apenas círculos independentes deslocados pelo quadro.

Em momentos de impacto, a direção de arte muda por poucos frames: desenho branco sobre preto, massa branca rachada ou personagem preto hachurado diante de luz amarela. Esses quadros têm desenho específico, em vez de serem somente uma tremida de câmera ou uma tela branca sobreposta.

### Organiza luz, materiais e atenção

Contornos principais são mais legíveis; cenários distantes ficam suaves. Há hachuras, desgaste, dobras e marcas locais de material. A granulação permanece discreta e não substitui desenho. O roteiro de cores muda entre ambientes e ações: uma cozinha fria pode receber luz quente localizada, enquanto um close usa madeira escura para sustentar o rosto.

## Registro de momentos verificáveis

Os índices abaixo são do arquivo de referência a 24 fps. Eles permitem localizar exemplos concretos, sem publicar imagens da obra.

| Frames / tempo aproximado | Evidência observada | Consequência para autoria |
| --- | --- | --- |
| 0–129 / 0–5,38 s | Acompanhamento lateral, caminhada/telefone e cabelo com atraso; cenário pode mudar enquanto o desenho corporal se mantém por pares | Separar exposição do ator, movimento do fundo e follow-through |
| 130–241 / 5,42–10,04 s | Corredor, aproximação, ângulo inclinado, produto e detalhe; close de rosto em 241 | Criar planos diferentes, com hierarquia de atenção |
| 250–285 / 10,42–11,88 s | Piscada em 250–253, pupila em espiral em 254–257 e expansão atrasada do cabelo com boca assimétrica | Desenhar expressões e ritmos específicos de cada parte |
| 286–407 / 11,92–16,96 s | Corte à cozinha, hold, silhueta de passagem em 307–308, entrada em profundidade, bocejo, perda de equilíbrio, queda fora do quadro e reação secundária da tigela | Usar antecipação, extremo direcional, sobreposição e consequência do prop |
| 408–470 / 17–19,58 s | Caixa gira, braços erguem, tronco estica e coluna de cereal cresce; corte em 470 para o detalhe da abertura | Mudar desenho, oclusão e enquadramento junto com a ação |
| 521–532 / 21,71–22,17 s | Dedos dobrados em 521–522, mão aberta em 523–524, palma espalmada em 525–526, depois hold | Substituir silhuetas de mão, em vez de girar uma única luva |
| 533–599 / 22,21–24,96 s | Plano angulado, gesto atravessa o rosto e apresentação ampla; corte em 590 para colocar o anel no dedo em 596–597 e soltar em 598–599 | Planejar trajetória corporal, camadas e abordagem/contato/liberação |
| 604–674 / 25,17–28,08 s | Hold prolongado da palma; corte em 633 para pose confiante sustentada, com pequena mudança de olhos | Preservar pausas de leitura sem bob corporal automático |
| 693–724 / 28,88–30,17 s | Um olho grande e outro comprimido, mão no queixo, depois palma quase de perfil em 723–724 | Articular assimetria facial e perspectiva dos dedos |
| 772–815 / 32,17–33,96 s | Plano geral com personagem quase mantido e pequenas mudanças independentes na torre de cereal | Separar relógios de ator, objeto e efeito |
| 840–887 / 35–36,96 s | Corpo quase mantido antes do lançamento da colher; virada por perfil/costas e captura | Contrastar hold e ação, com desenhos de virada |
| 897–926 / 37,38–38,58 s | Geladeira vista por dentro, luz acende, mão aumenta em primeiro plano, dedos fecham e retiram embalagem | Desenhar escorço e contatos em camadas |
| 974–1.014 / 40,58–42,25 s | Pausa de inspeção, antecipação e agitação angular da embalagem; cabelo reage com atraso | Evitar o mesmo easing em todos os canais |
| 1.083–1.103 / 45,13–45,96 s | Close de mão e objeto; dedos/garra e embalagem mudam de topologia mantendo a relação de grip | Substituir desenhos com registro de contato |
| 1.136–1.175 / 47,33–48,96 s | Corpo comprime/alonga; corte a exterior quieto, depois explosão de fumaça e detritos | Fazer desenho extremo e transição causal |
| 1.250–1.271 / 52,08–52,96 s | Jato cresce; em 1.260 personagem vira solução hachurada preta contra clarão amarelo | Desenhar valores e luz por exposição |
| 1.359–1.392 / 56,63–58 s | Close de mão sustentado por cerca de 34 frames, com mudança pequena nas rachaduras/luz | Permitir holds dramáticos com microação localizada |
| 1.393–1.404 / 58,04–58,50 s | Branco sobre preto, massa rachada e letras de impacto em substituições rápidas | Reservar desenho especial para o impacto |
| 1.423–1.426 / 59,29–59,42 s | Aproximação de câmera muito rápida atravessa elementos e revela o rosto | Usar montagem e câmera em função do evento |
| 1.487–1.554 / 61,96–64,75 s | Fumaça mascara transformação, queda em escorço e corte em 1.543 para perspectiva inversa | Planejar continuidade entre desenhos e pontos de vista |
| 1.632–1.799 / 68–74,96 s | Créditos sobre cozinha danificada, corpo quase parado e fogo/fumaça/pequeno papel em movimento | Não confundir hold corporal com ausência de atividade da composição |
| 1.800–1.877 / 75–78,21 s | Close pós-créditos com reação cansada, piscada assimétrica, papel inicialmente grande/desfocado e depois legível, fumaça e brasa | Fazer detalhe facial e profundidade com foco; secundária pode carregar a piada |
| 1.878–2.034 / 78,25–84,75 s | Pausa preta; linha do logo começa em 1.916 e marca institucional permanece até o final | Separar encerramento gráfico da avaliação de animação de personagem |

Os créditos e o encerramento não devem inflar conclusões sobre dinâmica corporal. No trecho final revisado, há 168 frames de créditos sobre uma composição animada mantida, 78 frames da gag pós-créditos, 38 frames de pausa preta e 119 frames de construção/hold do logo institucional.

## Diagnóstico da primeira rodada do Bamboonimation

As cenas iniciais possuem uma paleta coerente, desenhos originais, contorno irregular, textura, cenário, expressões, movimento de mãos, squash e objetos. A cena de versatilidade demonstra assuntos diferentes com o mesmo motor. Isso comprova liberdade de autoria e funcionamento do renderer.

As comparações visuais e de código mostram diferenças materiais em relação à referência:

- Ator predominantemente frontal, com cabeça/corpo reutilizados, em vez de um banco amplo de viradas e extremos.
- Cenas concentradas em um plano geral de sala/mesa, com zoom suave, sem variedade equivalente de inserts, perspectiva e contraplano.
- Mistura de poses e exposição global em 12 Hz que deixam o ritmo mais uniforme do que a referência.
- Mãos compactas e contatos que precisam de dedos posteriores, objeto e dedos anteriores em camadas registradas.
- Reações faciais pequenas em relação às mudanças de mandíbula, bochecha, pescoço, ombro e assimetria dos olhos da referência.
- Efeitos simples que não demonstram a mesma evolução de silhueta, profundidade e influência na luz.
- Acabamento mais geométrico e contorno mais uniforme, com menos hierarquia de material, foco e iluminação local.

Na primeira rodada, a inspeção de frames de chá também encontrou um pires acompanhando a xícara no ar enquanto outro permanecia sobre a mesa. Esse tipo de duplicação sem causa é uma falha de continuidade de prop, e precisa ser corrigido e rechecado antes de aprovar a cena. As mãos junto ao biscoito também precisam mostrar contato visível, em vez de mera proximidade.

Acrescentar papel ou elevar resolução não fecha essas diferenças. A próxima rodada precisa mudar a autoria da atuação e dos planos, além de ampliar os recursos que tornam essa autoria prática.

## Segunda rodada: revisão sequencial do curta de chá

O arquivo local revisado foi a versão de **12 segundos** de `tea_for_two.mp4`, com **288 frames a 24 fps**. Esse registro é histórico: não corresponde automaticamente aos quatro renders finais de 15 segundos. Três agentes de IA cobriram intervalos contíguos, sem saltos temporais:

| Frames inclusivos | Quantidade | Relatório local |
| --- | ---: | --- |
| 0–95 | 96 | `renders/round2/review-core.md` |
| 96–191 | 96 | `renders/round2/review-versatility.md` |
| 192–287 | 96 | `renders/round2/review-docs.md` |

A revisão cobriu todos os 288 frames em folhas sequenciais e ampliou detalhes selecionados. Não significa que cada frame tenha sido ampliado individualmente a 720p, nem comprova reprodução do vídeo em velocidade normal.

Melhorias observadas: cortes com intenção, cabeça de perfil desenhada separadamente, exposições variáveis, arco de movimento da xícara, dedos anteriores registrados, um único pires no apoio e linha mais estável nos inserts. A xícara e os dedos permanecem coerentes no trecho final revisado.

| Intervalo / detalhe | Defeito observado | Rechecagem necessária |
| --- | --- | --- |
| 0–95; insert 42–71 | Corpo frontal com alcance de cabeça/braços pouco apoiado pelo tronco; insert corta o rosto pelos olhos; antecipação do coelho simples; emendas internas nos braços | Peso, deslocamento corporal, enquadramento e contorno contínuo |
| 104 e 116–117 | Sombra oval parece flutuar; smear separa cabelo/roupa/pele e elimina corpo/pernas | Apoio e desenho direcional conectado, com identidade preservada |
| 118–121 e cortes 122/164 | Grito parece riso; troca direta entre perfil e frente produz salto | Mandíbula/expressão próprias e transição de vista coerente |
| 158–167 | Punho fechado e borda da xícara se sobrepõem antes de um grip legível; contato só fica resolvido depois do corte em 168 | Aproximação, contato e fechamento visíveis antes do corte |
| 192–287 | Xícara continua acima/à direita do pires; sorriso aberto mantido em 210–287 (78 frames, 3,25 s), sem troca de olhar/piscar | Apoiar e soltar de fato; atuação de resolução com intenção e pausa deliberada |
| Corte em 252 / 10,5 s | Plano final revela limite do cenário à direita (x 1228–1279) e embaixo (y 707–719) | Remover/recompor o corte e inspecionar todas as bordas |

**Veredicto histórico da segunda rodada:** houve progresso, mas os defeitos impediram a aprovação de qualidade ou equivalência com a referência naquela versão. Um grip correto em parte do vídeo não elimina problemas no momento da pega, e um novo perfil não prova continuidade na virada.

## Terceira rodada: registro histórico e correções identificadas

O render de chá de 15 segundos foi revisado integralmente: dois agentes de IA cobriram os 360 frames em 15 folhas consecutivas e ampliaram 25 detalhes a 720p. O arco da xícara, a inalação/espirro, o apoio no pires e o enquadramento final melhoraram. O smear sobreposto ao rosto, a palma receptora, o corte que esconde parte do contato, a mecânica corporal, a soltura por desaparecimento dos dedos e a mão final oculta ainda exigiam correções naquele render. O [registro de validação](validation.md) identifica esse arquivo por hash e detalha os achados. Esses achados motivaram novos renders e rechecagens; **a terceira rodada não recebeu aprovação visual final**. O resultado das rodadas posteriores aparece no estado atual deste estudo e no registro de validação.

Os recursos genéricos estão documentados em [exposições e desenhos substitutos](acting.md), [deformação vetorial](deformation.md) e [efeitos](effects.md). A exigência de autoria continua ampla: pessoas, animais, criaturas, máquinas, cenários e abstrações, com desenhos originais para a ação e perspectiva necessárias. Os helpers de chá não definem o limite de qualidade ou de assunto do framework.

A entrega especificada passa a ser **quatro vídeos de exatamente 15 segundos**, 1280 × 720 a 24 fps: `tea_for_two`, `the_last_cookie`, `versatility` e `paper_moon`, enviados por WaterDrop. Cada render precisa de probe de duração/taxa/resolução, identificação por tamanho e SHA-256 e revisão visual do próprio arquivo. O estado da entrega e o veredicto da terceira rodada pertencem a [Validação](validation.md); os quatro arquivos de entrega foram revisados e verificados nas rodadas posteriores, conforme a validação. A revisão final aprovou os mecanismos de atuação e consistência nos gestos observados, conforme o escopo registrado na validação.

## Trabalho motivado pelo estudo

O estudo mudou a prioridade: aperfeiçoar apenas o boneco frontal existente seria insuficiente. Naquela etapa, o trabalho passou a combinar recursos genéricos de autoria e uma demonstração original com encenação mais exigente.

| Frente | Alteração necessária | Como comprovar |
| --- | --- | --- |
| Exposição e atuação | Seleção explícita de desenhos e durações por parte, com holds e acentos independentes dos canais suaves | Cena usa essa seleção em um gesto legível; revisão confirma os limites |
| Banco de desenhos | Viradas, mãos, rostos e extremos com pontos de registro consistentes | Identidade, oclusão e contatos sobrevivem à troca de desenho |
| Deformação e ancoragem | Alterar formas e seus pontos de contato de maneira determinística | Prop acompanha a forma autorada sem deriva ou duplicação |
| Efeitos | Silhuetas com nascimento, pico, sobreposição e dissipação; impacto com desenho e valores específicos | Efeito reforça a ação e continua coerente em frames consecutivos |
| Direção do curta | Planos diferentes, insert/close motivado, retorno ao contexto e pausas de leitura | Reprodução do curta e inspeção dos cortes, não só screenshot final |
| Revisão | Nova rodada sobre o vídeo produzido depois das mudanças | Relatório com falhas restantes e veredicto sem antecipação |

Esta tabela descreve a direção do trabalho. A implementação e sua qualidade só devem ser consideradas verificadas quando houver código, render e análise correspondentes em [Validação](validation.md). Um extremo angular ou alongado não deve ser automaticamente chamado de smear: em vários intervalos a evidência é de desenho substituto e escorço, enquanto a passagem de silhueta em 307–308 mostra um caso próprio de transição direcional.

## Rubrica acionável para a próxima rodada

Esta rubrica avalia comportamento observado, sem uma porcentagem arbitrária de “semelhança”. O assunto e os personagens continuam originais. O alvo é uma linguagem de animação comparável, não copiar os acontecimentos do filme.

| Dimensão | O que a demonstração precisa mostrar | Evidência necessária |
| --- | --- | --- |
| Encenação | Ação compreensível, antecipação, consequência e resolução; close/insert motivado e contexto preservado | Reprodução completa e contato entre planos nos frames dos cortes |
| Desenho e identidade | Substituições que alterem perspectiva ou silhueta; pelo menos um extremo expressivo que não seja apenas escala do desenho neutro | Comparação de poses lado a lado e frames consecutivos da transição |
| Exposição | Holds deliberados, ação curta e recuperação; seleção de desenhos/camadas com tempos próprios | Registro de exposição e revisão quadro a quadro dos limites |
| Atuação facial | Olhar conduz intenção; olhos/boca/cabeça conseguem agir em tempos distintos, com assimetria quando o gesto pede | Close em tamanho de entrega e reprodução em velocidade normal |
| Contato e oclusão | Mão/objeto e apoios ficam registrados durante a ação e o corte; camadas explicam o grip | Frames antes, durante e depois de pegar, impactar ou soltar |
| Overlap | Cabelo, roupa, membro ou objeto secundário reage depois da ação principal e assenta | Sequência consecutiva mostrando atraso e redução da amplitude |
| Efeitos | Forma evolui com o evento; nascimento, pico e dissipação legíveis; não cobre erros de contato | Frames consecutivos do efeito e reprodução com a ação completa |
| Câmera e profundidade | Ponto de vista e escala reforçam a história; composição mantém leitura e proporções | Revisão dos planos completos, incluindo bordas e mudanças de foco quando usadas |
| Estilo visual | Paleta, espessura/hierarquia de linha, materiais e luz são consistentes e próximos da direção estudada | Frames reais na resolução de entrega, além de miniaturas |
| Autoria prática | Uma cena nova pode ser criada pelas APIs documentadas, sem editar o renderer ou pagar geração por frame | Código da cena, comandos reproduzíveis e arquivos resultantes |
| Renderização | Resolução, taxa, duração e formato corretos; custo registrado para aquela cena e máquina | Probe do arquivo, relatório e método em [Validação](validation.md) |

### Critério de aceitação

A entrega atual requer quatro curtas originais de exatamente 15 segundos. A rodada só pode ser aprovada depois de os renders correspondentes serem revisados em velocidade normal e em todos os frames consecutivos das ações, trocas de desenho, contatos, efeitos e cortes, com verificação de rosto, mãos, linha e bordas em tamanho de entrega. Os curtas precisam mostrar os mecanismos de atuação, desenho substituto, contato e encenação acima de forma convincente, sem defeitos pendentes que prejudiquem a leitura.

O relatório da rodada deve registrar o que foi melhorado, os comandos/artefatos verificados e as diferenças que ainda existem em relação à referência. Testes automáticos aprovados são evidência de comportamento do motor; não substituem a avaliação do filme. Da mesma forma, a existência de APIs de exposição, desenhos e efeitos não prova que a demonstração as usa bem.

**Estado deste estudo:** oito rodadas renderizadas, correções rechecadas e quatro vídeos de demonstração de 15 segundos. A rodada final de chá atende aos critérios declarados de apoio, contramovimento, volume, captura, oclusão, identidade e ritmo. O veredicto e as evidências estão em [Validação](validation.md). A comparação considera a linguagem de cartoon e os gestos observados; as cenas usam desenhos originais. Novas cenas e refinamentos adicionais continuam dependendo das decisões de desenho, tempo e encenação de seus autores.
