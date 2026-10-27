# Validação: evidência, revisões e medições

O Bamboonimation está pronto para autoria de cartoon 2D por código. A rodada final de chá atende aos critérios visuais definidos de dinâmica, contato, apoio, variação de desenho e acabamento da direção estudada em CEREAL!. Essa conclusão vem dos renders e da revisão sequencial descritos abaixo. Os testes comprovam o comportamento do motor; a avaliação artística está vinculada aos exemplos efetivamente examinados. A qualidade de novas cenas depende de sua autoria.

## Referência analisada

A referência indicada é [CEREAL! — Animated Student Film](https://www.youtube.com/watch?v=nCKwUB8EVbc), de XrayAlphaCharlie, com crédito de filme para Xierra Cansino. O [estudo integral](reference-study.md) registra mecanismos e exemplos por índice de frame, sem redistribuir imagens, áudio ou personagens da obra.

- Arquivo de estudo: 1280 × 720, 24 fps, **2.035 frames decodificados**, índices 0–2.034; duração correspondente de aproximadamente 84,792 s.
- Cobertura: **85 folhas consecutivas**, 24 frames por folha (a última contém 19), em miniaturas de 320 × 180, sem saltos temporais.
- Revisão: **cinco agentes de IA — principal e quatro subagentes**, com intervalos contíguos. Não é certificação humana nem revisão profissional independente.
- Todos os frames foram cobertos visualmente nas miniaturas. Detalhes selecionados também foram ampliados a 720p. Não se afirma que cada frame foi examinado individualmente em resolução original.
- Grades de miniaturas podem ocultar alterações muito pequenas, fases curtas de gesto, detalhe de linha e compressão. Diferenças de pixels não contam exatamente desenhos novos. Folhas de contato também não comprovam reprodução, áudio ou sincronização.

## Histórico de revisão dos exemplos

As três primeiras rodadas abaixo são registros históricos de versões já substituídas. Seus defeitos e reprovações descrevem aqueles arquivos; as correções e o veredicto da entrega estão nas seções das rodadas posteriores.

| Rodada / artefato | Cobertura documentada | Resultado |
| --- | --- | --- |
| Primeira rodada | Frames e código dos exemplos iniciais; não houve alegação de revisão integral de todos os vídeos | Funcionalidade e liberdade de assunto demonstradas. Predomínio frontal, ritmo uniforme, contatos e encenação insuficientes; não aprovada como prova de equivalência. |
| Segunda rodada, chá de 12 s | Todos os 288 frames em miniaturas sequenciais; três agentes de IA, intervalos 0–95, 96–191 e 192–287; detalhes selecionados | Perfil, planos, grip e exposições melhoraram. Ainda havia smear fragmentado, contato de captura fraco, xícara sem apoiar, sorriso longo e limite do cenário exposto no plano final. |
| Terceira rodada, chá de 15 s | Todos os 360 frames em 15 folhas sequenciais; dois agentes de IA, intervalos 0–167 e 168–359; 25 detalhes selecionados a 720p | Arco da xícara, espirro, apoio no pires e enquadramento final melhoraram. Permanecem problemas de smear, mão receptora, corte que esconde contato, mecânica corporal, soltura e gesto final oculto. |
| Paper Moon, render refinado de 15 s | Relatório do agente autor registra todos os 360 frames em 15 folhas, após corrigir e renderizar novamente | Troca de criatura, impacto, salto, captura, plantio e resolução foram revisados. Isso demonstra mecanismos adicionais, sem uma aprovação de equivalência ou uma revisão independente da autoria. |

Os relatórios detalhados e derivados de análise ficam no diretório local ignorado `renders/`. Eles não acompanham o pacote público. Os achados relevantes e seus limites estão resumidos aqui e no estudo da referência.

### Terceira rodada de chá: registro histórico

A revisão corresponde ao MP4 de 4.256.483 bytes com SHA-256 `01dd3e9f9c8044d99cb8e92eaa32b1c8cbe8dcb8c14e8dea6dd1e0bc55d7eb16`. Essa identificação é histórica; não identifica automaticamente o arquivo final da galeria.

Melhorias verificadas nesse render:

- O insert da pega deixa a mão/xícara mais legíveis; os dedos acompanham o objeto e o pires permanece na mesa.
- Inalação e espirro do coelho têm bocas distintas, com progressão de compressão e extensão.
- A xícara apresenta deslocamento e rotação contínuos no trecho visível; o perfil permanece consistente durante o plano da trajetória.
- A xícara chega ao pires por volta do frame 192 / 8 s e fica apoiada até o fim. Não há um segundo pires voando.
- O plano geral de 9–15 s preenche o quadro; o antigo corte em 10,5 s e suas faixas expostas nas bordas foram removidos.
- O sorriso final passa a uma boca menor, com piscadas e estados de repouso do elenco.

Pendências que foram observadas naquele artefato e motivaram as rodadas seguintes:

| Momento | Problema visível | O que uma correção precisa comprovar |
| --- | --- | --- |
| Frame 116 / 4,833 s | Cunhas de cor passam sobre o rosto, mantendo a cabeça neutra por baixo | Deformação/substituição da silhueta e de seus detalhes, com identidade conectada, ou remoção do acento |
| 125–147 / 5,208–6,125 s | Inclinação corporal pouco articulada; mãos fechadas e aproximação do prop deixam a intenção da tentativa de captura incerta | Apoio de pés/joelhos/pelve e palma receptora antes do contato, com miss/rebote ou amortecimento explícito |
| Corte em 148 e frames 148–167 | Xícara/mão ficam cortadas à direita durante uma fase importante | Reenquadrar a ação ou separar claramente reação e contato em planos legíveis |
| Frame 196 / 8,167 s | Dedos anteriores desaparecem juntos depois de apoiar a xícara | Desenhos registrados de abertura, separação e retirada da mão |
| 302–318 / cerca de 12,6–13,25 s | Mão do gesto de pensar fica escondida pelo tronco/cabeça | Ordem de camadas e silhueta que tornem o gesto visível |
| Resolução em plano geral | Alterações faciais existem, mas a direção de atenção entre xícara e companheiro é pouco explícita | Escolha clara de intenção e pausa, avaliada também em velocidade normal |

O desenho original pode ser diferente da referência. O critério é a clareza da atuação, contato, peso, mudança de forma e montagem. Os problemas registrados acima motivaram correções de autoria; não representam uma exigência de copiar personagens ou acontecimentos do filme. A revisão daquela rodada não incluiu aprovação de reprodução em velocidade normal ou de áudio. A verificação da entrega aparece adiante.

## Entrega final: quatro arquivos de 15 segundos

A especificação é **1280 × 720, 24 fps, 360 frames e 15 segundos por vídeo**, em MP4. Os nomes são `tea_for_two.mp4`, `the_last_cookie.mp4`, `versatility.mp4` e `paper_moon.mp4`, na [galeria](../assets/gallery/). A entrega solicitada é por WaterDrop. Links de compartilhamento, tokens e caminhos privados não são publicados neste documento. Os quatro arquivos foram enviados pela API local do WaterDrop; tamanho e SHA-256 foram conferidos localmente, pela URL preferencial e pelo conteúdo efetivamente baixado. Os comprovantes de entrega ficam apenas em `renders/delivery/`, ignorado pelo Git.

Os quatro arquivos identificados na tabela foram decodificados integralmente: **1.440 frames**, sem erros de decoder. Cada arquivo tem H.264, 1280 × 720, 24 fps e 15,000 segundos. Os três curtas narrativos incluem AAC mono 48 kHz; `versatility` é intencionalmente silencioso. [Manifesto completo com hashes de cada frame](../assets/validation/media.json).

| Arquivo | Bytes | SHA-256 | Revisão |
| --- | ---: | --- | --- |
| `tea_for_two.mp4` | 4,539,650 | `66e8791de566da2489e57127f47f819af39cc62172a01291964deec63d817078` | 360/360 frames consecutivos; detalhes selecionados a 720p |
| `the_last_cookie.mp4` | 3,943,401 | `b6247e8af67d39c872c7f41dd6fdead7bc3eac302c222e3bb32f92895637203a` | 360/360 frames consecutivos; detalhes selecionados a 720p |
| `versatility.mp4` | 3,435,929 | `05f3b0c1eaf61a606a69e51ee9c55a9db80873a0bb43e4996afb13127206ed0a` | 360/360 frames consecutivos; detalhes selecionados a 720p |
| `paper_moon.mp4` | 2,274,054 | `2ee6c81539e1841d39d16afe23392a153a5f75d81491155c06d1786f0f34cc64` | 360/360 frames consecutivos; detalhes selecionados a 720p |

### Rodadas 4 a 7 e revisão dos arquivos de entrega

Nas rodadas 4 a 6, o chá passou por três novas exportações e revisões. A quarta trocou as faixas sobre o rosto por deformação conectada com `WarpCanvas`, articulou os joelhos e isolou o insert de reação. A revisão encontrou que esse insert escondia a captura. A quinta mostrou a palma aberta aproximando-se do objeto e o fechamento no mesmo enquadramento. A sexta manteve o perfil durante o contato e redesenhou o antebraço sobre a mesa, corrigindo o pulso atravessado pela borda. Na soltura, a mão aberta vem do braço registrado, sem uma palma isolada sobreposta.

A revisão cumulativa cobriu todos os 360 frames: um segundo agente examinou 0-191 na rodada 4 e o principal examinou 192-359; os intervalos alterados nas rodadas seguintes foram rechecados em sequência. Detalhes selecionados incluem os frames 44, 70, 116, 132, 148, 156-168, 192-205 e 310. O render da sexta rodada foi a base para o novo trecho de atuação da sétima. O intervalo alterado recebeu revisão adicional, descrita abaixo.

A sétima rodada acrescentou uma cabeça de três quartos desenhada separadamente, com planos próximo/distante dos olhos, bochecha e mandíbula variáveis. Um plano médio de 9-11,5 s mostra o olhar descer à xícara e depois seguir para o coelho antes da mudança maior de cabeça e ombros. Pálpebras e sobrancelhas assimétricas usam exposição independente do corpo. O retorno ao plano geral ocorre num corte explícito em 11,5 s. Outro agente examinou todos os 360 frames dessa rodada e dez detalhes a 720p, confirmando contato, oclusão, leitura do olhar e junções. Uma última correção suavizou a recuperação do braço esquerdo em 168-174; após novo render, o principal rechecou a sequência e o limite 167/168. A autoria de seus controles pelo mesmo agente está registrada; não é certificação humana independente.

`Actor.pose_for_hand` também substitui a inversão manual de matrizes do exemplo: o autor especifica a posição desejada da palma, com os mesmos argumentos de colocação usados no ator. Um teste cobre 80 alvos com rotação, squash, espelhamento, caminhada e inclinação. O [exemplo de contato documentado](cartoon.md#atuação-em-três-quartos-e-mãos-registradas) foi executado e renderizado fora do curta.

Cookie e Worlds tiveram todos os 360 frames das versões identificadas na tabela revisados pelo agente autor, com auditoria adicional do principal em contatos, cortes e transições. Cookie corrige a pega pela pata, a trajetória até a mão, o uso de squash nos pontos de contato e a partilha por duas metades do mesmo desenho. O corpo avança para oferecer o pedaço sem esticar excessivamente o braço. Worlds conserva os pés do pássaro no solo durante a respiração. Os arquivos da galeria identificados na tabela são idênticos aos arquivos revisados.

Paper Moon teve todos os 360 frames examinados pelo autor, por outro agente e pelo principal, em miniaturas consecutivas. Captura e plantio receberam inspeção de detalhes a 720p. O render de Paper Moon identificado na tabela usa a trilha original retimada; os hashes de todos os 360 frames visuais coincidem com o vídeo revisto antes da troca da trilha.

### Rodada 8: corpo, apoio e peso

Os planos de alcance e captura foram refeitos com `BodyPose`: quadril e tórax se movem em sentidos opostos, a cabeça responde separadamente, e casaco, babador, mangas e calças mudam seus contornos e planos. Os pés permanecem em pontos de apoio durante o alcance. A sombra permanece no chão durante o salto. A xícara voa de 115 a 149; o ator salta de 121 a 139 e aterrissa antes da captura, que comprime o corpo até 154 e assenta até 160. A mão secundária recupera depois da pega. O apoio da xícara ocorre no frame 180 e a abertura da mão no frame 184. O áudio original foi retimado para esses eventos.

Uma revisão encontrou a raiz da manga sobreposta ao casaco ao redesenhar o braço em primeiro plano. `occlude_root=True` conserva a raiz da manga sob o contorno exato do casaco e mantém punho/palma visíveis. A exportação final foi novamente decodificada: o agente do motor revisou 0-191 em sequência e ampliou 44/180; outro agente cobriu o filme inteiro e seus detalhes, além da inspeção do principal. A emenda foi resolvida, sem regressão observada de contato ou silhueta. Os três outros MP4s conservam os mesmos bytes dos arquivos revistos anteriormente.

| Critério declarado antes da revisão | Evidência no render final | Resultado |
| --- | --- | --- |
| Preparação e contramovimento | Olhos antecipam alcance; quadril/tórax/cabeça mudam em 18-40 | Aprovado |
| Apoio e peso | Pés fixos no alcance; compressão 118-121; salto de 18 frames e aterrissagem 139 | Aprovado |
| Desenho e volume | Babador curvo, planos de casaco/manga e joelhos dobrados mudam dentro do gesto | Aprovado |
| Identidade e conexão | Frente, três quartos e perfil mantêm cabelo/orelha/pescoço conectados | Aprovado |
| Contato e oclusão | Palma aberta 144-148, fechamento 149, apoio 180 e soltura 184; raiz de manga preservada | Aprovado |
| Recuperação e sobreposição | Compressão da captura 149-154, assentar 154-160, braço secundário em atraso | Aprovado |
| Encenação e estilo | Planos motivados, contorno compensado nos closes, paleta/textura coerentes e quadro preenchido | Aprovado |
| Integridade e reprodução | 360 frames decodificados; MP4 a 1× no Chrome chega a 15 s sem erro de mídia | Aprovado |

**Resultado visual:** a amostra final demonstra linguagem de cartoon comparável à referência nos mecanismos observados: antecipação, mudanças de silhueta/volume, atuação assimétrica, ritmo variado, contato, peso e resolução. A avaliação considera personagens e encenação originais. Há espaço para refinamentos de virada de cabeça e detalhes de cabelo/tecido; eles não impedem a leitura nem a consistência dos gestos revisados. Paper Moon acrescenta desenhos substitutos e transformação de criatura; Worlds demonstra universos diferentes. Os pareceres são de agentes de IA e registram seus limites, sem certificação humana ou porcentagem arbitrária de semelhança.

A reprodução dos quatro MP4s no Chrome foi verificada separadamente ([registro](../assets/validation/playback.json)), a 1×, até o término dos quatro vídeos em 15 s. A verificação de áudio confirma decoder, duração, amostras finitas e ausência de clipping nos arquivos, sem alegar uma avaliação auditiva humana ou perceptual.

## Testes e exemplos de documentação

Na auditoria de documentação desta etapa, **51 blocos Python foram compilados em 23 arquivos de documentação/apoio**; 28 blocos selecionados foram executados, com 120 chamadas de desenho/amostragem. A seleção inclui os exemplos de README/API/cartoon, quickstart em inglês, duas cenas de deformação (incluindo `WarpCanvas`) e as folhas de exposição. Canvas, tempo, cena e imports mostrados em trechos anteriores foram fornecidos quando o bloco dependia desse contexto. Trechos ilustrativos com callbacks/arquivos do usuário e os exemplos de áudio externo/exportação foram apenas compilados. Isso verifica correspondência com a API naquele estado do código, sem provar a qualidade visual de cada curta.

A suíte verificada nesta etapa passou com **106 testes em Python 3.14.6** e **106 em Python 3.12.10**, no Windows. Inclui exemplos carregados fora do diretório do projeto, duração de 15 s, assets de áudio resolvidos, amostragem de desenhos/impactos e retorno a tempos anteriores com pixels idênticos. Os avisos restantes são depreciações de APIs das dependências. O [registro de verificação do pacote](../assets/validation/package.json) confirma build de wheel/sdist e instalação isolada do wheel em Python 3.12.10. Os módulos do motor no wheel e no sdist coincidem, byte a byte, com as fontes verificadas; o sdist inclui exemplos e assets e contém apenas conteúdo público. O teste da instalação confirmou os encoders, um PNG vertical de 1080 × 1920, exportação com taxa racional de 30000/1001 fps e desenho com `WarpCanvas`. Essas verificações se aplicam ao build registrado; alterações posteriores precisam de nova validação.

## Medições finais de CPU, memória e tempo

Renderização medida sequencialmente em processos isolados de Python/FFmpeg; os números abaixo correspondem às versões medidas das fontes e aos MP4s identificados na tabela. Alterações posteriores exigem nova medição; os resultados não representam uma declaração de congelamento das fontes. Windows, Python 3.14.6, Skia 144.0.post2, NumPy 2.5.3, imageio-ffmpeg 0.6.0, 24 CPUs lógicas, 63,91 GiB de RAM física. H.264, preset fast/CRF 18, duas threads do encoder, supersampling 1.

| Cena / saída | Duração / frames | Processo | Throughput | Pico RSS somado | CPU amostrada | Relatório |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| tea_for_two, 1280 x 720 / 24 fps | 15 s / 360 | 26.741 s | 13.71 fps | 335.64 MiB | 32.578 s (1.22 núcleos médios) | [JSON](../assets/validation/tea_for_two-1280x720-24.json) |
| the_last_cookie, 1280 x 720 / 24 fps | 15 s / 360 | 16.836 s | 21.91 fps | 272.67 MiB | 23.328 s (1.39 núcleos médios) | [JSON](../assets/validation/the_last_cookie-1280x720-24.json) |
| versatility, 1280 x 720 / 24 fps | 15 s / 360 | 16.848 s | 21.88 fps | 254.50 MiB | 22.781 s (1.35 núcleos médios) | [JSON](../assets/validation/versatility-1280x720-24.json) |
| paper_moon, 1280 x 720 / 24 fps | 15 s / 360 | 22.310 s | 16.43 fps | 282.02 MiB | 28.469 s (1.28 núcleos médios) | [JSON](../assets/validation/paper_moon-1280x720-24.json) |
| quickstart, 1920 x 1080 / 60 fps | 10 s / 600 | 38.553 s | 15.75 fps | 425.01 MiB | 52.547 s (1.36 núcleos médios) | [JSON](../assets/validation/quickstart-1920x1080-60.json) |

Os quatro curtas de 15 s levam 16,8-26,7 s neste computador: aproximadamente 1,1-1,8 vezes a duração do vídeo. O quickstart de 10 s em 1080p/60 fps levou 38,6 s. O processo não faz inferência de IA nem chama serviços de geração por frame. O snapshot de fonte/motor/áudio ficou estável do início ao fim de cada medição.

Informe sistema operacional, versão de Python, dependências, CPUs lógicas, RAM física, resolução, duração, fps, supersampling, codec/preset e threads do encoder. Uma amostra de um computador não é garantia para outra máquina, cena ou versão.

O script [measure_render.py](../tools/measure_render.py) mede um processo Python filho e seus descendentes FFmpeg, consultando-os a cada 50 ms. Soma RSS da família e CPU user+system amostrada; páginas compartilhadas podem ser contadas mais de uma vez, picos entre consultas podem ser perdidos e processos muito breves podem não ser capturados integralmente. Tempo do processo inclui importação/inicialização; `RenderReport.elapsed_seconds` mede a etapa de render/exportação. Nenhum desses números mede sozinho uso global do computador ou energia.

```bash
python tools/measure_render.py examples/tea_for_two.py --width 1280 --height 720 --fps 24
python tools/measure_render.py examples/the_last_cookie.py --width 1280 --height 720 --fps 24
python tools/measure_render.py examples/versatility.py --width 1280 --height 720 --fps 24
python tools/measure_render.py examples/paper_moon.py --width 1280 --height 720 --fps 24
python tools/measure_render.py examples/quickstart.py --width 1920 --height 1080 --fps 60
```

O script requer as dependências de desenvolvimento. Os relatórios de medição devem conter SHA-256 do arquivo de cena e do conjunto de módulos do motor; registre também o hash dos assets relevantes quando mudarem. Eles devem usar nomes relativos e dados de ambiente sanitizados, sem nome da máquina, usuário, caminhos absolutos ou credenciais. A configuração de threads é do encoder; não representa automaticamente paralelismo de desenho Python.

## Preview, som e limites práticos

O preview de navegador é uma timeline **silenciosa de PNGs**; não reproduz `scene.audio`. O relógio pode avançar enquanto uma imagem está sendo calculada, omitindo solicitações intermediárias. Scrub ajuda a inspecionar um tempo isolado. Esse preview não prova reprodução de todos os frames em tempo real nem sincronização de áudio. Revise o MP4 exportado para esses critérios.

O renderer usa Skia em CPU e transmite frames ao FFmpeg sem guardar o filme inteiro em RAM. A memória ainda depende de resolução, supersampling, assets, caches, composição e encoder. Os limites de endereçamento/Skia e uma estimativa de buffers são verificados, mas não há suporte a dimensões infinitas nem custo zero. FPS de entrega é uma decisão de exportação; não cria desenhos novos e pode omitir uma exposição artística mais curta que seu intervalo de amostragem.

Renderizar as cenas em código não exige serviço pago de IA ou inferência por frame. CPU, RAM, disco, autoria e ferramentas externas opcionais têm custos. Vídeo sem falhas técnicas também pode precisar de mais desenho e direção para atingir o resultado artístico pretendido.