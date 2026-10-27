# Validação: evidência, correções e medições

Esta revisão fecha os defeitos de anatomia e contato descritos abaixo nos arquivos identificados por SHA-256. A aprovação visual ampla das versões anteriores foi **retirada** após o feedback do usuário. Testes, hashes e decodificação verificam comportamento e integridade; não substituem a avaliação dos desenhos, da atuação ou da continuidade.

## Correções após o feedback visual

Os defeitos estavam nos modelos desenhados e na encenação fornecida aos exemplos. O renderer desenhava essa geometria; trocar o formato de exportação não corrigiria uma sobrancelha extra, um nariz contraditório ou uma pega mal construída. As correções também produziram controles reutilizáveis de cabeça, mão e oclusão na biblioteca, documentados em [personagens e contatos](cartoon.md).

| Defeito observado | Correção no artefato revisto | Verificação concreta |
| --- | --- | --- |
| Menino com nariz externo e traço interno em direções conflitantes; troca brusca de cabeça | Um modelo contínuo de frente a perfil, com um único nariz e oclusão conjunta de olho/sobrancelha distante | Atlas de orientações/expressões e 251 detalhes nativos de rosto; a cabeça manteve esse modelo no chá final |
| Raposa de perfil com duas sobrancelhas e um olho; branco de olho sob a pálpebra fechada | Olho e sobrancelha seguem a mesma visibilidade; sono substitui o olho aberto; focinho e nariz acompanham a virada | Atlas de cabeça/poses, filme completo em sequência e 204 detalhes nativos consecutivos dos frames 156–359 |
| Pega pela parede da xícara com a alça do lado oposto; mão que voltava à alça após soltar | Alça voltada ao personagem, punho/palma/dedos conectados e a mesma mão personalizada durante abertura, retirada e repouso | 317 detalhes nativos de mão/contato; comparação contínua de 196–197 e sequência até o fim |
| Mão livre de Cookie confundida com uma orelha; raiz de manga sobre o peito | Mão separada da silhueta da cabeça, braço ligado ao ombro e contornos de manga adequados ao gesto | Revisão do filme final pelo autor e detalhes exportados de captura e ombro |
| Oferta do biscoito na altura do olho do coelho; ponta indevida de manga na preparação | Oferta dirigida ao focinho inferior e raiz da manga registrada no casaco | Comparação nativa dos frames 223–224 e revisão de todos os 81 frames 216–296 da versão final |

O primeiro candidato corrigido de chá ainda tinha um salto de mão no frame 197 e foi reprovado. Uma revisão de Cookie chegou a interpretar incorretamente a ponta de manga da versão V3 como uma emenda aceitável; essa conclusão foi retirada após comparação nativa. **Cookie V3 não é a entrega**: a correção está no arquivo final identificado abaixo. Esses achados mostram por que ver todos os frames, por si só, não torna um parecer visual infalível.

## Cobertura da revisão visual

A revisão dos exemplos distingue trabalho do autor, checagem por outro agente da equipe e reprodução pelo agente principal. Nenhum desses papéis equivale a certificação humana ou avaliação profissional externa.

| Artefato final | Cobertura da revisão visual desta correção | Alcance da conclusão |
| --- | --- | --- |
| Chá | Filme decodificado por inteiro; 317 crops nativos de mão nos frames 0–71 e 115–359, sem reescala. Os 43 frames 72–114 são uma reação sem a mão humana e foram conferidos separadamente. A revisão de cabeça conservada do candidato anterior cobriu 251 crops nativos nos intervalos 0–41, 115–167 e 204–359, além dos atlas de orientação/oclusão | Nariz, visibilidade olho/sobrancelha, pega, soltura, retirada e repouso revistos. Nenhum novo defeito material dessas classes foi encontrado nessa cobertura |
| Cookie | Autor examinou os 360 frames finais em folhas consecutivas, os 81 frames nativos 216–296 e 13 frames exportados selecionados. Outro agente decodificou o filme final e examinou todos os 81 crops nativos 216–296, comparando V3/V4 em 223–224 | A ponta de manga foi corrigida; oferta, retirada e ligação ombro/punho permanecem coerentes no intervalo examinado. A checagem independente desse intervalo não é apresentada como nova revisão nativa de todo o filme |
| Paper Moon | Autor examinou os 360 frames em sequência e detalhes de poses/virada. Outro agente examinou 204 crops nativos consecutivos 156–359, incluindo virada, sono e despertar | Sobrancelha extra e branco residual corrigidos, sem nova falha material de nariz/focinho/olhos/orelhas/pescoço nesses detalhes |
| Três universos | Arquivo conserva os mesmos bytes da versão anteriormente revisada em 360 frames, com detalhes selecionados | A identidade de bytes preserva aquela revisão; não é apresentada como nova avaliação artística nesta rodada |

Os exemplos empregam poses autoradas, exposições variadas, mudanças de silhueta, apoio e contato, com desenhos e histórias originais. O fechamento dos defeitos relatados não prova que cada frame seja artisticamente perfeito, nem garante consistência automática em uma nova cena. A autoria ainda precisa construir e revisar seus modelos, contatos e encenação. O [registro visual estruturado](../assets/validation/visual-review.json) liga as conclusões aos hashes da entrega. Relatórios detalhados e folhas de revisão permanecem no diretório local ignorado, fora da distribuição pública.

## Arquivos de entrega e integridade

Todos os quatro MP4s têm **15,000 s, 1280 × 720, 24 fps e 360 frames**, codificados em H.264. Os três curtas narrativos têm AAC mono a 48 kHz; `versatility.mp4` é intencionalmente silencioso. A verificação técnica decodificou **1.440 frames** e conferiu duração, codec e áudio. O [manifesto de mídia](../assets/validation/media.json) registra também hashes dos frames decodificados a 320 × 180; isso é uma checagem de integridade, não uma avaliação estética.

| Arquivo | Bytes | SHA-256 |
| --- | ---: | --- |
| [`tea_for_two.mp4`](../assets/gallery/tea_for_two.mp4) | 4.555.699 | `47dc24a2eff270f3cb42554c6dfdf8dc259f80774956c77b1c6fcd30c1fe570b` |
| [`the_last_cookie.mp4`](../assets/gallery/the_last_cookie.mp4) | 3.962.665 | `a7ab9ab3cd064905adf7b5a0cdbb4340ab0af016df0b36e1993cef5aca4cf7ee` |
| [`versatility.mp4`](../assets/gallery/versatility.mp4) | 3.435.929 | `05f3b0c1eaf61a606a69e51ee9c55a9db80873a0bb43e4996afb13127206ed0a` |
| [`paper_moon.mp4`](../assets/gallery/paper_moon.mp4) | 2.304.220 | `3c9040a528fae08b5145ecca869d3f2e1fc65755e9bd5e40ac6975b95f90a018` |

A [verificação de reprodução](../assets/validation/playback.json) registra início e término a 1× no Chrome, até 15 s, sem erro de mídia. Para os três arquivos alterados, ela foi repetida nesta revisão; Três universos mantém os mesmos bytes do arquivo anteriormente verificado. Esse registro não alega acompanhamento humano contínuo de todos os frames nem audição perceptual. A análise de áudio confirma amostras finitas, nível abaixo do limite de clipping verificado e atividade no encerramento; não certifica qualidade sonora ou sincronismo percebido.

A entrega solicitada é por WaterDrop, usando a API. Links de compartilhamento, comprovantes e caminhos privados não são publicados no Git. O nome, tamanho e SHA-256 do arquivo recebido permitem compará-lo à tabela.

## Testes, documentação e pacote

A suíte local passou com **113 testes em Python 3.12.10** e **113 em Python 3.14.6**, no Windows. Inclui carregamento dos exemplos fora do diretório do projeto, acesso temporal em ordem variável, FPS racional, transparência, preservação de saídas existentes, encerramento de launcher/encoder filho após erro, continuidade da virada de cabeça e oclusão de manga nos dois caminhos de corpo. Os testes de geometria e pixels detectam regressões específicas; não são um classificador de qualidade artística.

O [workflow](../.github/workflows/ci.yml) configura Ubuntu e Windows em Python 3.11, 3.12 e 3.13, com testes, `doctor` e build. No Ubuntu instala `libegl1`, exigida pelo wheel do Skia mesmo na renderização em CPU; instala também `ffprobe` nas duas plataformas para executar as verificações de metadados. O resultado de uma execução deve ser conferido em [Actions](https://github.com/MusicMaster4/Bamboonimation/actions), no commit correspondente. A configuração da matriz não é apresentada como aprovação antecipada do próximo CI.

A auditoria atual dos guias examinou **19 arquivos de README, documentação e apoio**: **93 links relativos/âncoras** resolveram e **51 blocos Python** compilaram. Uma auditoria anterior havia executado 28 blocos selecionados e 120 chamadas de desenho/amostragem; esses números descrevem aquela auditoria, não execução integral de todos os blocos após cada alteração. Receitas que dependem de assets/callbacks do usuário exigem seu próprio contexto.

O [registro do pacote](../assets/validation/package.json) identifica o build e suas verificações. O wheel instalado isoladamente em Python 3.12.10 foi importado do ambiente instalado, com os 17 módulos do motor conferidos contra as fontes. Os smokes incluem virada numérica/`FacePose`, `BodyPose`, supressão da mão genérica/pega na alça, encoders, PNG vertical de 1080 × 1920, taxa racional de 30000/1001 fps e `WarpCanvas`. O sdist final teve 78 arquivos públicos comparados byte a byte com o projeto, incluindo exemplos, assets e guias. A inspeção confirmou a ausência do estudo local, da mídia privada e dos comprovantes de entrega. Alterações posteriores precisam de nova verificação.

## Medições finais de CPU, memória e tempo

As cinco medições foram realizadas sequencialmente, em processos Python/FFmpeg, com o mesmo snapshot do motor. O arquivo de cena, o motor e o inventário de áudio ficaram estáveis do início ao fim de cada render. Nos quatro curtas, os MP4s medidos coincidem byte a byte com os arquivos revisados da tabela. O snapshot de áudio inventaria os WAV do repositório; não afirma que toda cena usa todos eles.

Ambiente: Windows, Python 3.14.6, Skia 144.0.post2, NumPy 2.5.3, imageio-ffmpeg 0.6.0, 24 CPUs lógicas e 63,91 GiB de RAM física. H.264, preset `fast`, CRF 18, duas threads do encoder e supersampling 1. Os relatórios contêm os hashes de entrada e o método completo.

| Cena / saída | Duração / frames | Tempo do processo | Throughput do render | Pico RSS somado | CPU amostrada / núcleos médios | Relatório |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `tea_for_two.py` · 1280 × 720 / 24 fps | 15 s / 360 | 32,411 s | 11,27 fps | 335,53 MiB | 39,188 s / 1,21 | [JSON](../assets/validation/tea_for_two-1280x720-24.json) |
| `the_last_cookie.py` · 1280 × 720 / 24 fps | 15 s / 360 | 20,552 s | 17,92 fps | 272,77 MiB | 28,609 s / 1,39 | [JSON](../assets/validation/the_last_cookie-1280x720-24.json) |
| `versatility.py` · 1280 × 720 / 24 fps | 15 s / 360 | 19,932 s | 18,43 fps | 256,57 MiB | 27,625 s / 1,39 | [JSON](../assets/validation/versatility-1280x720-24.json) |
| `paper_moon.py` · 1280 × 720 / 24 fps | 15 s / 360 | 27,554 s | 13,27 fps | 280,04 MiB | 32,719 s / 1,19 | [JSON](../assets/validation/paper_moon-1280x720-24.json) |
| `quickstart.py` · 1920 × 1080 / 60 fps | 10 s / 600 | 46,448 s | 13,04 fps | 424,64 MiB | 63,172 s / 1,36 | [JSON](../assets/validation/quickstart-1920x1080-60.json) |

Os quatro curtas de 15 s levaram de **19,9 a 32,4 s** neste computador, com picos RSS somados amostrados entre **256,57 e 335,53 MiB**. O quickstart de 10 s em 1080p/60 fps levou 46,4 s. São resultados destas cenas e deste ambiente; não são garantia de tempo real ou de custo constante em outra máquina, resolução ou composição.

O script [measure_render.py](../tools/measure_render.py) amostra a família Python/FFmpeg a cada 50 ms e exclui seu próprio processo observador. RSS somado pode contar páginas compartilhadas duas vezes e perder picos entre amostras. CPU é a soma dos últimos tempos user+system observados por identidade de processo; processos breves e trabalho após a última observação podem escapar. “Núcleos médios” divide essa CPU amostrada pelo tempo total do processo e não representa uso percentual global da máquina nem energia. O tempo do processo inclui inicialização/importação; throughput usa o intervalo de render/exportação do `RenderReport`.

Para repetir uma medição:

```bash
python tools/measure_render.py examples/tea_for_two.py --width 1280 --height 720 --fps 24
```

Instale as dependências de desenvolvimento e registre sistema, versões, resolução, duração, FPS, supersampling, codec/preset, threads e hashes. Relatórios públicos devem usar nomes relativos e dados de ambiente sanitizados.

## Preview, som e limites práticos

O preview de navegador é uma timeline **silenciosa de PNGs** e não reproduz `scene.audio`. Seu relógio pode avançar enquanto uma imagem está sendo calculada, omitindo solicitações intermediárias. Scrub inspeciona um tempo isolado; o MP4 exportado é o artefato para revisar reprodução e áudio.

O renderer usa Skia em CPU e transmite os frames ao FFmpeg sem guardar o filme inteiro em RAM. Memória e tempo ainda dependem de resolução, supersampling, geometria, assets, caches, composição e codec. Os limites de endereçamento/Skia e uma estimativa de buffers são verificados; não há suporte a dimensões infinitas ou custo zero. A exportação admite taxas positivas, inclusive racionais, mas aumentar FPS não cria desenhos novos e uma amostragem mais baixa pode omitir exposições artísticas curtas.

Renderizar as cenas locais não exige inferência de IA ou serviço pago por frame. CPU, RAM, disco, autoria e ferramentas opcionais continuam tendo custos. Um vídeo tecnicamente válido ainda pode exigir mais desenho e direção para atingir o resultado artístico pretendido.
