# Qualquer universo em 2D

O motor não impõe tema, personagem, cenário nem estética. `Scene` aceita qualquer função `painter(canvas, tempo)`: ela pode desenhar um organismo microscópico, um mapa, um robô, uma conversa, uma cidade, fantasia ou arte abstrata. As primitivas e as hierarquias também aceitam desenhos próprios, arquivos SVG, imagens raster e sequências de desenhos. Os personagens dos exemplos são material de partida opcional.

A liberdade temática não substitui desenho e direção. Para um resultado complexo, o agente ainda precisa representar as formas, definir a encenação e revisar as poses. O framework executa essas decisões com tempo determinístico e saída em resolução e FPS escolhidos.

## Uma amostra com três universos

```powershell
bamboonimation render examples/versatility.py -o renders/versatility.mp4 --width 1280 --height 720 --fps 24
```

A animação de exemplo tem 15 segundos: um ecossistema de águas-vivas, uma nave atravessando um planeta com anéis e um jardim de tinta com pássaro e uma flor que nasce. Todo o desenho é vetorial e original, definido no código. Não há imagens baixadas, chave de API nem geração paga.

O exemplo usa `Storyboard` para costurar três cenas independentes. A duração final é a soma das durações menos as sobreposições: `4.4 + 4.4 + 7.0 - 0.4 - 0.4 = 15` segundos.

## Sequenciar cenas

```python
from bamboonimation import Scene
from bamboonimation.storyboard import Storyboard

filme = Storyboard(width=1280, height=720)
filme.add(Scene(duration=4, painter=desenhar_mar))
filme.add(Scene(duration=4, painter=desenhar_espaco),
          transition="dissolve", overlap=0.4)
filme.add(Scene(duration=4, painter=desenhar_jardim),
          transition="iris", overlap=0.4)
scene = filme
```

`desenhar_mar`, `desenhar_espaco` e `desenhar_jardim` são funções próprias com assinatura `(canvas, t)`. Cada cena recebe tempo local: o começo dela é `t=0`, mesmo quando ocorre no meio do filme. O storyboard encaixa cada cena no viewport preservando a proporção, centraliza o resultado e recorta o desenho aos limites dela. Cenas com outra proporção recebem barras na cor `Storyboard(background="#000000")`; use `background=None` para barras transparentes. As barras também fazem parte das transições, evitando que uma cena anterior apareça nelas depois de um corte.

As transições disponíveis são `cut` (corte, sem sobreposição), `dissolve` (fusão), `wipe` (revelação da esquerda para a direita) e `iris` (círculo que se abre pelo centro). As três últimas exigem `overlap > 0`. Uma transição não pode cobrir a cena inteira nem se sobrepor a outra transição. Os clips de áudio de cada cena recebem o deslocamento temporal correspondente; em uma fusão, o áudio se sobrepõe sem aplicar um fade de volume automático.

## Caminhos com velocidade uniforme

```python
from bamboonimation.procedural import PathMotion

trajeto = PathMotion([(0, 300), (220, -20), (520, 600), (900, 200)])
x, y, angulo = trajeto.sample(t / 5)
with canvas.transform(x, y, rotation=angulo):
    desenhar_nave(canvas)
```

Um segmento cúbico usa quatro pontos. Para acrescentar outro segmento, acrescente três pontos: o primeiro ponto é compartilhado. A velocidade usa uma tabela aproximada de comprimento de arco, em vez de avançar o parâmetro Bézier linearmente. Aumente `samples_per_segment` quando uma curva muito pequena ou muito fechada exigir mais precisão. O progresso é limitado ao intervalo `[0, 1]`.

## Molas e movimento secundário

```python
from bamboonimation.procedural import spring, overlap

escala = spring(t - 2, frequency=2, damping=0.55)
orelha = overlap(t, start=2, amplitude=12, frequency=3, decay=5)
```

`spring` resolve uma mola amortecida analiticamente, sem integrar quadro a quadro. `frequency` está em Hz, `damping` é a razão de amortecimento, e `velocity` é a velocidade inicial em unidades por segundo. Valores de `damping` menores que 1 oscilam, 1 é o amortecimento crítico e maiores que 1 produzem uma acomodação sem oscilação. `initial` e `target` definem os valores inicial e final. Antes do começo, o valor permanece em `initial`.

`overlap` retorna uma oscilação que se acomoda após um impulso, útil para cabelos, antenas, tecidos, orelhas e objetos flexíveis. Todos esses movimentos funcionam ao buscar um tempo fora de ordem.

## Partículas sem simulação acumulativa

```python
from bamboonimation.procedural import ParticleSystem

poeira = ParticleSystem(
    seed=42, rate=12, origin=(640, 720), spread=(500, 20),
    velocity=((-8, 8), (-90, -30)), acceleration=(0, -4),
    lifetime=(2, 4), size=(1, 3), colors=("#ecd8b7", "#c7cbb0"),
)

def desenhar(canvas, t):
    poeira.draw(canvas, t)
```

`velocity` contém os intervalos de velocidade X e Y. `spread` é a metade da extensão do emissor em cada eixo; `lifetime` e `size` são intervalos mínimo/máximo. `start` e `end` delimitam a emissão; partículas vivas continuam depois de `end`. `fade=True` suaviza entrada e saída. `max_particles` rejeita configurações que excedem a população máxima estimada, evitando uma emissão acidentalmente enorme.

Para estrelas, fumaça estilizada, folhas ou criaturas, passe um desenho próprio:

```python
def folha(canvas, p):
    with canvas.transform(p.x, p.y, rotation=p.rotation, sx=p.size):
        canvas.path("M0 0 Q-2 -4 0 -6 Q2 -3 0 0Z", fill=p.color,
                    stroke=None)

poeira.draw(canvas, t, painter=folha)
```

`sample(t)` retorna tuplas de `Particle` imutáveis com `index`, `x`, `y`, `age`, `life`, `size`, `rotation`, `opacity` e `color`. O mesmo índice e seed sempre têm as mesmas condições iniciais. Desenhar `t=5`, depois `t=1`, depois `t=5` produz o mesmo estado em ambas as amostras de 5 segundos. A escolha do FPS altera a frequência de amostragem, não a trajetória.

## Para agentes: escolha a representação certa

- Formas arbitrárias: `Canvas.path` com curvas SVG ou `skia.Path` próprio.
- Desenhos importados: `Canvas.image` e nós `Image`/`Sprite`.
- Personagens articulados: grupos hierárquicos, bones, poses e IK.
- Mudanças de silhueta: desenhos substitutos em `Sprite` ou morph com topologia compatível.
- Efeitos ambientais: `ParticleSystem` com desenho personalizado.
- Trajetórias curvas: `PathMotion` e canais temporais.
- Atuação flexível: molas e `overlap`, respeitando as poses principais.
- Sequências longas: cenas curtas em `Storyboard`; cada plano tem tempo e seed próprios.

Renderize quadros de poses importantes e também pequenos vídeos de revisão. Um quadro bonito sozinho não comprova boa animação: verifique continuidade, timing, contato dos pés/mãos, legibilidade e transições.

## Camadas estáticas rápidas

Gradientes, texturas de papel e cenários detalhados podem ser mais caros que a movimentação dos personagens. Use um cache explícito quando um desenho não depender do tempo:

```python
from bamboonimation.procedural import StaticLayer

fundo = StaticLayer(desenhar_cenario, width=1280, height=720, seed=1)

def pintar(canvas, t):
    fundo(canvas)
    desenhar_personagem(canvas, t)
```

O cache usa a escala efetiva do dispositivo e arredonda a densidade de pixels **para cima** em degraus de 0,25. Assim, resoluções maiores ou um zoom da câmera geram uma nova imagem com detalhe suficiente; translação e rotação não obrigam redesenhar o cenário. `max_cache_bytes` limita os pixels retidos por camada (64 MiB por padrão). Imagens maiores continuam funcionando, mas não são retidas. `layer.cache_info` expõe entradas, bytes, acertos e reconstruções; `layer.clear_cache()` invalida o conteúdo quando o desenho estático mudar. O orçamento é por camada: some as camadas ao estimar RAM.

Para papel sobre a composição inteira, use uma camada transparente com ruído:
```python
def textura(c):
    c.paper(0.12, seed=7)

papel = StaticLayer(textura)
```

A textura é calculada uma vez por faixa de resolução. `Canvas.paper` usa preto com transparência para produzir o escurecimento do papel sem uma operação de multiplicação cara. Sua composição ainda tem custo por pixel em cada quadro. Para o modo mais rápido, incorpore o papel ao desenho do fundo em vez de aplicá-lo por cima de toda a cena. `StaticLayer` aceita transformações afins; uma transformação de perspectiva projetiva precisa de outra estratégia. Para partículas com arte personalizada, `draw(..., painter=...)` aplica transparência por uma camada intermediária; em populações grandes, aplicar a opacidade diretamente às cores do desenho evita esse custo.
