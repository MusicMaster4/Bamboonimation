# Efeitos de desenho e atuação

`bamboonimation.effects` oferece recursos para executar decisões de direção: rastros de poses, marcas de velocidade, impactos gráficos, hachura, tremor de câmera e movimento secundário. Eles funcionam com desenhos próprios e qualquer tema. Não substituem o desenho das poses nem tornam uma cena automaticamente equivalente a um filme de referência.

## Impactos com exposição explícita

```python
from bamboonimation.effects import impact_flash


def desenho_de_impacto(c, t):
    # Um desenho substituto original, com a silhueta apropriada ao gesto.
    c.path("M380 500 Q430 300 590 350 L670 510Z",
           fill="#ffffff", stroke=None)


def pintar(c, t):
    if impact_flash(c, t, at=2.0, frames=2, fps=24,
                    background="#000000", ink="#ffffff",
                    painter=desenho_de_impacto):
        return
    desenhar_cena_normal(c, t)
```

`impact_flash` retorna `True` apenas no intervalo `[at, at + frames / fps)`. Chame a função antes da cena normal e encerre o desenho quando ela estiver ativa. `frames` precisa ser um inteiro positivo; `fps` define a duração artística da exposição. Por exemplo, dois quadros a 24 fps duram 1/12 s; uma exportação a 60 fps amostra esse mesmo intervalo com mais quadros. Para dois quadros exatamente na taxa de exportação, passe essa taxa também em `fps`.

`background=None` mantém o fundo transparente. `ink` recolore todos os pixels não transparentes do desenho para uma cor, preservando sua cobertura. `ink=None` mantém as cores desenhadas pela função; use essa opção para uma exposição com contorno branco, massa preta, riscos e outros detalhes específicos. Um simples filtro de silhueta não produz esse desenho automaticamente.

Você pode combinar exposições adjacentes: primeiro contorno branco sobre preto, depois uma forma branca rachada, depois o desenho normal com follow-through. O desenho e o timing de cada exposição devem ser dirigidos conforme a cena.

## Hachura dentro de formas arbitrárias

```python
from bamboonimation.effects import hatch

sombra = "M380 500 Q430 300 590 350 L670 510Z"
c.path(sombra, fill="#2f2225", stroke=None)
hatch(c, sombra, spacing=5, angle=-35, color="#dbad78",
      width=0.8, seed=7, jitter=1.2)
```

O recorte aceita SVG path data ou `skia.Path`. As linhas têm espaçamento e peso variados com seed estável. A hachura respeita o contorno, inclusive curvas e furos do caminho. Ela não infere iluminação: o agente fornece a forma que representa a sombra ou a região iluminada. Para uma luz dramática, desenhe massas e hachuras próprias para essa exposição, além de mudar as cores do ambiente.

`spacing` e `width` precisam ser positivos; `jitter` é a variação em unidades lógicas. A densidade é limitada a 100.000 traços por chamada para impedir uma configuração acidentalmente enorme. Em uma cena estática, cache a hachura em `StaticLayer`.

## Marcas de velocidade orgânicas

```python
from bamboonimation.effects import speed_lines

speed_lines(c, t, center=(640, 360), count=26,
            radius=(170, 760), length=(30, 160), width=(0.8, 2.2),
            color="#e7d7b4", seed=19, speed=200,
            exposure=12, curve=0.12, opacity=0.4)
```

As marcas saem radialmente do centro, com comprimentos e pesos variados e curvatura discreta. `radius`, `length` e `width` são intervalos mínimo/máximo. `angles=(0,360)` usa a volta inteira; um intervalo menor restringe a área. `speed` negativo inverte a viagem radial.

`exposure=12` mantém apenas os desenhos desse efeito a 12 Hz. Isso permite câmera contínua, personagem com uma exposição e marcas com outra. `exposure=0` mantém movimento contínuo. Desenhe as marcas antes do sujeito ou use `Canvas.clip` para preservar uma área de leitura.

A cor aplica opacidade diretamente aos traços, evitando uma camada intermediária por marca. O limite de contagem é 10.000 por chamada. Marcas de velocidade são uma convenção gráfica; alongar/redesenhar a silhueta do sujeito em um smear continua sendo trabalho de desenho.

## Rastros de poses sem estado acumulativo

```python
from bamboonimation.effects import motion_echo


def sujeito(c, t):
    desenhar_personagem(c, t)


def pintar(c, t):
    desenhar_fundo(c)
    motion_echo(c, sujeito, t, samples=2, spacing=1/48,
                opacity=0.14, ink="#494654")
    sujeito(c, t)
```

A função amostra poses anteriores em ordem da mais antiga para a mais recente. Não guarda imagens dos quadros anteriores; buscar fora de ordem mantém o resultado. A função `sujeito` deve desenhar apenas o personagem/objeto, não a composição inteira. Não são amostrados tempos negativos.

`offset=(dx,dy)` acrescenta deslocamento por amostra. `ink=None` mantém as cores originais; uma cor produz ecos de silhueta. Cada eco exige uma camada intermediária de composição, portanto use poucas amostras e restrinja o efeito a uma passagem breve. O limite de 64 amostras evita crescimento de trabalho sem controle. Um rastro não substitui desenhos de passagem que mudam a anatomia.

## Tremor de câmera determinístico

```python
from bamboonimation.effects import camera_shake

dx, dy, rot = camera_shake(t, at=2.0, duration=0.28,
                          amplitude=6, rotation=0.3,
                          frequency=22, seed=3)
with c.transform(x=dx, y=dy, rotation=rot):
    desenhar_mundo(c, t)
```

O retorno é `(deslocamento_x, deslocamento_y, graus)`. A amplitude limita cada eixo de translação, e `rotation` limita o ângulo. O efeito vale exatamente zero antes do gatilho e depois da duração. Sua envoltória decai para zero; a entrada pode começar com um solavanco, como em um impacto. `frequency` está em Hz. Some o deslocamento à câmera dirigida; não use tremor contínuo para encobrir uma atuação fraca.

## Canal de follow-through

```python
from bamboonimation import Track
from bamboonimation.effects import FollowThrough

angulo = Track(0).add(1, 0).add(1.2, 25).add(1.5, 0)
antecipacao_da_orelha = FollowThrough(angulo, delay=0.08, overlap=0.2)
rotacao_orelha = antecipacao_da_orelha(t)
```

`FollowThrough(source, delay, overlap)` amostra a função ou Track nos tempos `t-delay` e `t-2*delay`. O resultado acompanha o canal com atraso e um pequeno prolongamento da variação. Aceita números e tuplas numéricas de estrutura compatível. É um filtro estilizado e determinístico, não uma simulação física; para uma mola analítica, use `bamboonimation.procedural.spring`.

## Uma revisão útil de animação

Ao revisar uma passagem rápida, confira todos os quadros consecutivos da ação. Preserve a identidade e os pontos de contato, mas permita que as formas mudem conforme gesto, perspectiva e velocidade. Diferencie poses mantidas, detalhes que continuam se movendo, transições de luz e efeitos em outras exposições. Depois assista à passagem na velocidade normal: o desenho precisa funcionar no tempo, além de funcionar parado.
