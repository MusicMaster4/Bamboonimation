# Guia para agentes de IA

O objetivo é produzir **código de animação 2D original e verificável**. O Bamboonimation não restringe o assunto: personagens, animais, objetos, máquinas, mundos fantásticos, abstrações e histórias usam a mesma API. Os curtas de exemplo ajudam com organização e acabamento, sem definir um tema obrigatório.

## Antes de editar

Leia `README.md`, `docs/api.md` e um arquivo de exemplo. Confirme a versão e as opções com `python -m bamboonimation --help`. Não invente métodos com base em Manim ou em outra biblioteca. Verifique o código local quando uma assinatura não estiver clara.

Colete estes elementos do briefing, adotando escolhas razoáveis se não forem especificados:

| Elemento | Exemplo |
| --- | --- |
| Ação | Um objeto escapa, o personagem reage e o recupera |
| Duração e entrega | 12 s, 1280 × 720, 24 fps, MP4 |
| Linguagem visual | Papel quente, cores contidas, traço irregular discreto |
| Atuação | Antecipação, ação rápida, pausa para reação |
| Assets | Originais em código ou arquivos locais autorizados |
| Revisão | Poses iniciais, todos os frames de ação, reprodução e render final |

## Plano de autoria

1. Escreva em uma frase o que muda entre o começo e o final.
2. Marque tempos para cinco a sete momentos principais.
3. Defina espaço lógico, paleta e ordem de camadas.
4. Desenhe cenário e poses principais antes de interpolar.
5. Escolha graph/rig para partes reutilizáveis, `DrawingBank`/`Sprite` para desenhos substitutos, `ExposureSheet` para durações autoradas, morph para topologias compatíveis e `LatticeWarp`/callbacks para mudanças de forma.
6. Acrescente contatos, olhares e pausas de leitura.
7. Acrescente movimento secundário em amplitude pequena.
8. Gere frames e assista ao movimento; corrija o que as imagens mostram.

Um exemplo de tabela temporal para 12 segundos:

| Tempo | Estado |
| --- | --- |
| 0–2 s | Situação e intenção legíveis |
| 2–3 s | Antecipação |
| 3–5 s | Ação e contato |
| 5–7 s | Reação |
| 7–10 s | Consequência e movimento secundário |
| 10–12 s | Resolução e pose final |

A tabela é um ponto de partida, não um molde para toda história.

## Regras de implementação

- Exponha `scene` ou `make_scene()` no módulo.
- Use segundos e tempo absoluto; uma consulta fora de ordem deve produzir a mesma pose.
- Não execute renderização no momento de importar o módulo.
- Separe desenho e cálculo de pose em funções pequenas com nomes claros.
- Use constantes para paleta e marcos de tempo.
- Não chame APIs, não baixe assets e não leia arquivos repetidamente por frame.
- Use paths, SVGs, imagens e sprites autorizados; não copie personagens ou frames de terceiros.
- Faça variação aleatória com seed e confira seus limites em valores extremos.
- Resolva assets a partir de `__file__`, não do diretório de onde a CLI foi chamada.
- Não entregue um arquivo de vídeo inexistente ou um link que não foi verificado.

## Recursos de autoria além de um recorte frontal

Leia [atuação e exposições](acting.md), [deformação](deformation.md) e [efeitos](effects.md). Essas ferramentas funcionam com sujeitos originais de qualquer tema.

1. Desenhe intenção, antecipação, extremo, contato e recuperação. Acrescente perfil, costas, escorço e inserts quando o plano exigir; um espelhamento ou zoom não cria uma nova perspectiva.
2. Registre raiz, pé, punho e grip em `DrawingBank`; verifique os anchors nas duas poses de cada troca. Desenhe dedos posteriores, objeto e dedos anteriores na ordem adequada.
3. Use `ExposureSheet` por parte/camada para holds, acentos de um frame e recuperação. `sheet.time(t)` é o começo da exposição, não o tempo atual. Uma saída em FPS menor pode omitir acentos curtos; confira o arquivo final na taxa pedida.
4. Calcule `LatticeWarp` sempre a partir da geometria original. Deforme detalhes da mesma superfície juntos. Para contato exato, prefira um endpoint compartilhado pelo contorno e pelo anchor; um mapper não linear transforma a rede de controle, não toda a curva ponto a ponto.
5. Use efeitos para reforçar causa e consequência: silhueta, nascimento, pico e dissipação. Hachura, impacto gráfico, rastro e tremor não corrigem pose ilegível ou objeto sem contato.
6. Compartilhe uma direção de arte por cena com `ArtStyle` ou um preset `PAPER`/`NIGHT`/`CEL`; derive uma paleta original e use as cores explicitamente nos desenhos. O estilo não recolore assets nem cria iluminação automaticamente. Aplique `style.apply(c, zoom=zoom_real)` ao desenho e `style.finish(c)` no acabamento.
7. Planeje câmera, linha e bordas. Um insert pode pedir `c.stroke_scale = 1 / zoom`; confira também os limites do cenário e a leitura da anatomia no corte.

## Revisão inicial de poses

```bash
python -m bamboonimation doctor
python -m bamboonimation frame examples/tea_for_two.py --time 0 -o renders/review-00.png --width 640 --height 360
python -m bamboonimation frame examples/tea_for_two.py --time 3 -o renders/review-03.png --width 640 --height 360
python -m bamboonimation frame examples/tea_for_two.py --time 6 -o renders/review-06.png --width 640 --height 360
python -m bamboonimation frame examples/tea_for_two.py --time 9 -o renders/review-09.png --width 640 --height 360
python -m bamboonimation frame examples/tea_for_two.py --time 11 -o renders/review-11.png --width 640 --height 360
python -m bamboonimation render examples/tea_for_two.py -o renders/draft.mp4 --width 640 --height 360 --fps 24
```

Use novos nomes ou `--overwrite` quando quiser substituir arquivos já revisados. Os cinco frames acima são uma triagem inicial, insuficiente para aprovar a animação.

No render produzido, examine **todos os frames consecutivos de cada ação**, incluindo aproximação, pega, impacto, soltura, desenho substituto, smear e recuperação, com alguns frames antes/depois. Revise todos os cortes e todas as bordas de enquadramento. Para curtas de 15 segundos a 24 fps, uma revisão sequencial integral cobre 360 frames por arquivo; folhas de contato sem saltos ajudam a assegurar cobertura, mas os detalhes de rosto, dedos, linha e clipping precisam também de inspeção na resolução de entrega.

Depois reproduza o curta completo em velocidade normal para avaliar leitura, intenção, pausas e ritmo. Se o player não reproduziu, registre essa limitação: miniaturas não comprovam playback, áudio ou sincronização. Ao corrigir código, renderize novamente a passagem alterada e confira o artefato final correspondente. Registre índice/tempo, arquivo, defeito e resultado da rechecagem. Não marque uma cena como boa só porque o encoder saiu com código zero.

## Critérios de avaliação

| Critério | Evidência |
| --- | --- |
| Leitura | A ação é compreensível em velocidade normal e sem texto explicativo |
| Atuação | Olhar, cabeça, mãos e corpo expressam a intenção |
| Contatos | Objetos ficam presos às mãos ou apoios nos intervalos corretos |
| Silhueta | Poses principais são distinguíveis em tamanho pequeno |
| Estilo | Paleta, contornos e acabamento permanecem consistentes |
| Continuidade | Não há saltos não planejados, clipping ou desaparecimentos |
| Independência de FPS | O mesmo tempo corresponde à mesma pose |
| Performance | Medição informa cena, dimensões, taxa, duração e ambiente |

Se a direção exigir semelhança com uma referência, compare as características visuais concretas. Declare diferenças relevantes. Um motor funcional não prova equivalência artística a um filme de animação.

## Prompt de continuação

```text
Continue a cena existente sem substituir seu assunto por um prefab.
Preserve API pública e alterações de outras pessoas.
Inspecione os frames renderizados nos tempos críticos antes de escolher mudanças.
Melhore primeiro poses, contatos e enquadramento; depois ajuste textura e efeitos.
Renderize um rascunho curto, verifique ritmo e só então exporte a entrega final.
Informe arquivos gerados, comandos executados e limitações observadas.
```

Para ampliar o framework, siga [CONTRIBUTING.md](../CONTRIBUTING.md). Para executar arquivos de terceiros, leia [SECURITY.md](../SECURITY.md).