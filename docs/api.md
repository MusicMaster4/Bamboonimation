# API e linha de comando

As assinaturas abaixo descrevem a API do projeto. Use `python -m bamboonimation COMANDO --help` para confirmar as opções da instalação em uso.

## Scene e ordem de desenho

```python
from bamboonimation import Scene

scene = Scene(width=1280, height=720, duration=12,
              background="#f2e4cb", seed=1,
              painter=None, post_painter=None)
```

`width` e `height` são dimensões lógicas positivas, `duration` está em segundos e `seed` controla variações dos helpers que usam aleatoriedade. `background=None` mantém o fundo transparente quando o formato de saída suporta alpha.

A ordem de composição é: fundo, nodes na ordem de `scene.add`, `painter(canvas,t)` com câmera e `post_painter(canvas,t)` sem câmera. O último callback é útil para papel, vinheta ou desenho fixo em tela. `scene.find(name)` procura um objeto nomeado. `scene.audio` aceita os clipes de áudio descritos adiante. `scene.metadata` fica disponível para dados de autoria.

A função de desenho deve ser determinística para um dado `t`. O motor não impõe um assunto nem um banco obrigatório de personagens: desenhe livremente, carregue assets autorizados ou combine ambos.

## Canvas

| Método | Convenção |
| --- | --- |
| `path(data, fill=None, stroke='#302d3c', width=3, rough=None)` | String SVG path ou `skia.Path`; curvas e formas livres |
| `ellipse(x,y,rx,ry,fill=None,stroke=None,width=3)` | Centro e raios |
| `rect(x,y,w,h,fill=None,stroke=None,width=3,radius=0)` | Canto superior esquerdo, dimensões e raio opcional |
| `line(points,stroke='#302d3c',width=3)` | Polilinha de pares `(x,y)` |
| `polygon(points,fill=None,stroke=None,width=3)` | Contorno fechado |
| `text(text,x,y,size=24,fill='#302d3c',font=None)` | `y` é a linha de base; família de fonte do sistema |
| `text_width(text,size=24,font=None)` | Largura estimada pelo Skia |
| `image(path,x,y,w=None,h=None,opacity=1)` | Imagem raster ou SVG; proporção preservada se só uma dimensão for dada |
| `gradient_rect(x,y,w,h,colors,start=None,end=None,positions=None)` | Gradiente linear; padrão vertical |
| `shadow(x,y,rx,ry,opacity=.14,fill='#302d3c')` | Sombra elíptica simples |
| `paper(amount=.12,seed=None,size=256)` | Granulação repetível; aplique após o desenho |

Use cores hexadecimais `#RGB`, `#RGBA`, `#RRGGBB` ou `#RRGGBBAA`, tuplas de canais inteiros RGB/RGBA ou cores Skia. Use `None` para omitir preenchimento ou contorno. Coordenadas crescem para a direita e para baixo; rotações são dadas em graus no sentido horário.

```python
with c.transform(x=300, y=280, rotation=-8, sx=1.1, sy=.9):
    c.path("M -50 25 Q -80 -80 0 -95 Q 80 -80 50 25 Z",
           fill="#e6a777", stroke="#403944", width=3)
```

`transform` restaura o estado gráfico ao sair, inclusive em exceções. `save`, `restore`, `translate`, `rotate` e `scale(x,y=None)` também estão disponíveis. `clip(path)` e `opacity(value)` são context managers:

```python
with c.clip("M 0 0 H 180 V 160 H 0 Z"):
    with c.opacity(.5):
        c.ellipse(90, 80, 110, 70, fill="#a6b9b2")
```

`c.roughness = .45` altera o contorno, mantendo o preenchimento. `c.boil_fps = 12` modifica a variação em exposições discretas de 12 Hz. Use valores pequenos; excesso de variação parece tremor. `saved()`, `transform()` e `clip()` isolam o estado gráfico e restauram `roughness` e `boil_fps` ao sair. Os métodos manuais `save/restore` salvam apenas o estado Skia; ajuste o estilo explicitamente ao usá-los.

`c.stroke_scale` é um número positivo e finito que multiplica largura de contorno e amplitude de irregularidade nos métodos do wrapper. Em um insert, use explicitamente `c.stroke_scale = 1 / zoom` para compensar aproximadamente o aumento do traço em tela. O preenchimento não muda; imagens raster/SVG e operações diretas em `c.raw` mantêm seus próprios estilos. `saved()`, `transform()` e `clip()` restauram esse fator ao sair.

A textura de `paper` pode acrescentar cobertura alpha em regiões vazias. Para um sprite com exterior transparente, use `clip` na silhueta antes de aplicá-la.

`c.raw` expõe o `skia.Canvas` para operações avançadas. `c.time`, `c.seed`, `c.width` e `c.height` descrevem o frame e o espaço lógico.

## Direção de arte compartilhada

`ArtStyle` reúne paleta nomeada, irregularidade de linha, papel e seed. Os presets `PAPER`, `NIGHT` e `CEL` são escolhas opcionais para qualquer assunto. A paleta é imutável; `derive` cria outra direção e mescla as cores informadas.

```python
from bamboonimation import Scene, PAPER

style = PAPER.derive(palette={"warm": "#b66e70"}, roughness=.25)


def paint(c, t):
    with style.apply(c, zoom=1, boil_fps=0):
        c.path("M520 450 Q470 240 640 220 Q800 250 760 450 Z",
               fill=style["warm"], stroke=style["ink"], width=3)


scene = Scene(background=style["paper"], painter=paint,
              post_painter=lambda c, t: style.finish(c))
```

`style.apply(c,zoom=1,boil_fps=0)` isola/restaura as configurações do Canvas, inclusive em exceções, e usa `stroke_scale=1/zoom`. Passe o zoom real ao compensar um insert; isso mantém aproximadamente o peso do contorno, sem mudar a geometria preenchida. `style.finish(c)` aplica papel e deve ficar depois do desenho, normalmente em `post_painter` para uma textura fixa em tela. A paleta não recolore assets ou formas automaticamente: use explicitamente `style["ink"]`, `style["warm"]` e as demais cores nos seus desenhos.
## Objetos e hierarquias

Objetos compartilham `x`, `y`, `rotation`, `sx`, `sy`, `opacity`, `pivot=(0,0)`, `visible`, `name` e `painter`. Filhos herdam a transformação e opacidade do pai.

```python
from bamboonimation import Scene, Group, Path, Ellipse

head = Group(
    Ellipse(70, 85, fill="#e8b58c", stroke="#403944", width=3),
    Ellipse(7, 11, fill="#403944", x=-23, y=-10),
    Ellipse(7, 11, fill="#403944", x=23, y=-10),
    Path("M -20 28 Q 0 43 20 28", stroke="#403944", width=3),
    x=640, y=340, name="head",
)
head.at(0, rotation=0).at(2, rotation=-12).at(3, rotation=8)
head.animate("x", 760, start=4, duration=1.2, ease="smooth")
scene = Scene(duration=12).add(head)
```

| Tipo | Assinatura específica |
| --- | --- |
| `Group(*children, **node_args)` | Grupo livre; `add`, `remove`, `find` |
| `Path(data,fill=None,stroke='#302d3c',width=3,**node_args)` | Path SVG |
| `Ellipse(rx=20,ry=None,fill=...,stroke=None,width=3,**node_args)` | Desenho centrado na origem local |
| `Rect(width=100,height=100,fill=...,stroke=None,stroke_width=3,radius=0,**node_args)` | Retângulo a partir da origem local; note `stroke_width` |
| `Text(text,size=24,fill=...,font=None,**node_args)` | Texto com baseline na origem |
| `Image(source,width=None,height=None,**node_args)` | Asset raster/SVG |
| `Sprite(frames,fps=12,start=0,hold=False,width=None,height=None,**node_args)` | Desenhos substitutos; arquivos ou callbacks `(canvas,t)` |
| `Layer(*children,depth=1,**node_args)` | Grupo de primeiro nível com parallax |

Um node só pode ter um pai. Remova-o do pai anterior antes de reparentar. Ciclos são rejeitados. A ordem dos filhos é a ordem visual; objetos posteriores cobrem os anteriores. `node.world_point(point=(0,0),time=0)` e `node.local_point(point,time=0)` convertem pontos incluindo ancestrais, sem aplicar a câmera.

### Keyframes

`node.at(time, **props)` armazena valores absolutos. `node.animate(prop,to,start=0,duration=1,ease='smooth')` cria uma interpolação a partir do valor existente no começo. `node.value(prop,t)` consulta o resultado sem modificar a cena nem atribuir o valor amostrado ao atributo original.
Os canais de desenho e transformação são amostrados no tempo, incluindo `pivot` (par de números finitos), `Text.font`, `Layer.depth` e `Sprite.width`, `height`, `fps`, `start` e `hold`. `hold` é booleano/discreto. Atributos estruturais não são canais: `name`, `parent`, `children`, `tracks`, `painter`, `Sprite.frames`, `Bone.length` e `Rig.bones`/`poses` são rejeitados por `at`/`channel`. Um atributo público personalizado pode ter um canal, mas um painter personalizado precisa ler `node.value("atributo", t)` explicitamente; a criação de keys não modifica sua leitura direta por `node.atributo`.

```python
from bamboonimation import Track

lift = Track(0).add(0, 0).add(1, -35, "out").add(1.3, 0, "bounce")
y_at_half_second = lift(.5)
```

A interpolação de um intervalo usa o easing do keyframe de destino. Um primeiro keyframe depois de zero interpola a partir do valor padrão em zero. Valores posteriores ao último keyframe mantém seu valor final. Outro keyframe no mesmo tempo substitui o anterior.

Easings: `linear`, `smooth`, `smoother`, `in`, `out`, `back`, `elastic`, `bounce`, `hold` e `step`. Também é possível fornecer uma função. Números, tuplas e cores hexadecimais podem ser interpolados. Strings arbitrárias são mantidas até o destino. Use `hold`/`step` para substituições de desenho.

### Morphing

```python
from bamboonimation import Path

mouth = Path("M -20 0 Q 0 10 20 0", stroke="#403944")
mouth.morph("M -20 0 Q 0 35 20 0", start=2, duration=.25)
```

Os paths precisam dos mesmos comandos, ordem e quantidade de coordenadas; flags de arcos também devem coincidir. Morphing não resolve correspondência entre desenhos arbitrários. Para topologias diferentes, use desenhos substitutos em `Sprite`.

### Desenhos substitutos

```python
from bamboonimation import Sprite

def relaxed(c, t):
    c.path("M -25 0 Q 0 10 25 0", stroke="#403944")

def surprised(c, t):
    c.ellipse(0, 7, 12, 18, fill="#403944")

mouth = Sprite([relaxed, surprised], fps=12, hold=True, x=640, y=350)
mouth.at(0, frame=0)
mouth.channel("frame").add(2.5, 1, "hold").add(3.2, 0, "hold")
```

Sem índice explícito, `Sprite` escolhe `floor((t - sprite.value("start", t)) * sprite.value("fps", t))`, limitado a um índice não negativo. A taxa é amostrada naquele instante; animar `fps` não integra velocidade acumulada. Para uma agenda exata de desenhos, use keys explícitos de `frame` ou [ExposureSheet e DrawingBank](acting.md). `hold=False` repete a sequência; `hold=True` mantém o desenho final. O callback ainda recebe o tempo absoluto da cena. Isso permite animação desenhada quadro a quadro sem limitar a entrega ao FPS dos desenhos. Keys de `frame` são discretos.

## Câmera e profundidade

`scene.camera` começa no centro lógico. Propriedades animáveis: `x`, `y`, `zoom` e `rotation`. Zoom deve ser positivo.

```python
from bamboonimation import Scene, Layer, Rect

scene = Scene(duration=12)
scene.add(Layer(Rect(1280, 720, fill="#d9d5b2"), depth=.2))
scene.add(Layer(Rect(300, 160, fill="#be9375", x=450, y=460), depth=1))
scene.camera.animate("x", 700, start=2, duration=3)
scene.camera.animate("zoom", 1.1, start=2, duration=3)
```

`depth=0` fixa uma camada na tela; `depth=1` acompanha a câmera normalmente. Valores intermediários reduzem sua resposta. A profundidade é interpretada nas `Layer` adicionadas diretamente à cena; grupos aninhados continuam sujeitos à transformação da camada superior. O `painter` recebe a câmera com profundidade 1, enquanto `post_painter` fica fixo em tela.

## Rigs, poses e IK

Um rig é uma hierarquia de ossos 2D. Cada osso aponta ao longo do eixo local +x; o desenho anexado define sua aparência.

```python
from bamboonimation import Rig, Path, Scene

arm = Rig(x=500, y=300)
upper = arm.bone("upper", length=90, rotation=20)
lower = arm.bone("lower", length=75, parent="upper", rotation=35)
upper.attach(Path("M 0 -12 L 90 -9 L 90 9 L 0 12 Z", fill="#dfac87"))
lower.attach(Path("M 0 -9 L 75 -7 L 75 7 L 0 9 Z", fill="#dfac87"))
arm.define_pose("rest", {"upper": 20, "lower": 35})
arm.define_pose("wave", {"upper": -55, "lower": -60})
arm.set_pose("rest", time=0).to_pose("wave", start=2, duration=.5)
scene = Scene(duration=12).add(arm)
```

`bone(name,length,parent=None,x=None,y=0,rotation=0)` devolve um `Bone`. Um filho sem `x` começa na ponta do pai. `bone.attach(node,at_tip=True)` coloca o desenho na ponta.

`rig.ik("upper","lower",target=(120,-20),time=4,bend=1)` cria keys para uma cadeia de dois ossos. O alvo está no espaço local do **pai do osso superior**, e não necessariamente nas coordenadas da cena. `bend=-1` escolhe o outro lado do cotovelo. Alvos fora do alcance são limitados; IK não alonga o desenho. A cadeia deve ligar diretamente os ossos, com o inferior começando na ponta do superior. Os valores **amostrados no tempo da solução** dos ossos da cadeia precisam de `sx=sy=1` e `pivot=(0,0)`; aplique escala ao Rig que os contém. A conversão de pontos e `Bone.tip(time)` também consideram o pivô amostrado.

`solve_two_bone(length1,length2,target,origin=(0,0),bend=1)` retorna ângulos superior e inferior relativo. `blend_poses(a,b,amount)` combina poses, usando o menor arco para rotações.

Rigs facilitam reutilização, mas cortes visíveis em articulações continuam exigindo desenho, sobreposição ou poses substitutas. O motor não infere uma anatomia nem deforma uma imagem automaticamente.

### Helpers de atuação

- `blink(t,at,duration=.15)`: fechamento da pálpebra entre 0 e 1.
- `spring(t,start=0,frequency=3,damping=5)`: resposta analítica de acomodação, sem simulação acumulada.
- `walk_cycle(t,period=.8,stride=30)`: dicionário com valores de pernas, braços e corpo; adapte os canais ao seu desenho.
- `follow_path(points,t,start=0,duration=1,ease='smooth')`: ponto em uma Bézier cúbica com quatro pontos de controle.
- `cycle`, `pingpong`, `mix`, `stagger`: composição de tempos e valores; veja as assinaturas no módulo `animation`.

## áudio e bocas

```python
from bamboonimation.audio import AudioClip

scene.audio.append(AudioClip("assets/voice.wav", start=2, volume=.8, offset=.1))
```

`start` posiciona o clipe na cena, `offset` pula o começo do arquivo e `volume` ajusta o nível. FFmpeg mistura os clipes e respeita o intervalo de vídeo exportado. A sincronização visual precisa usar a mesma origem temporal.

```python
from bamboonimation import LipSync, MouthCue

lip = LipSync([MouthCue(.2, .5, "A"), MouthCue(.5, .8, "B")], rest="X")
shape = lip(.6)  # "B"
```

`LipSync.from_rhubarb("assets/voice.json")` lê `mouthCues` com `start`, `end` e `value` do formato Rhubarb. O projeto não executa nem instala Rhubarb automaticamente. Os intervalos são `[start,end)` e não podem se sobrepor. O artista precisa fornecer o desenho de cada boca.

`Envelope.from_wav(path).at(t)`, no módulo `audio`, mede intensidade RMS para WAV compatível. Intensidade não identifica fonemas. `viseme(t, [(0,"rest"),(.1,"open")])` seleciona cues manuais; não é reconhecimento de fala nem geração automática de lip sync.

## Renderização Python

```python
from bamboonimation.render import render, save_frame

save_frame(scene, "renders/pose.png", t=2, width=640, height=360)
report = render(scene, "renders/film.mp4", width=1280, height=720,
                fps=24, threads=2, overwrite=False)
print(report.to_dict())
```

`frame(scene,t,width=None,height=None,supersample=1)` devolve uma `skia.Image`. Com `supersample=N`, cada pixel final é a média exata dos N × N subpixels. `save_frame` escreve PNG. `render` devolve `RenderReport`; por padrão também produz um relatório de renderização. Não interprete throughput de uma cena como garantia de desempenho para todas as outras.

Parâmetros de `render`: `width`, `height`, `fps`, `start=0`, `end=None`, `supersample=1`, `overwrite=False`, `transparent=False`, `threads=2`, `preset='fast'`, `crf=18`, `format=None`, `report=True`, `progress=None`, `workers=1`.

`workers=N` renderiza frames em N processos e os entrega ao encoder na ordem; o resultado é idêntico ao render serial, porque cada frame depende apenas de `t`. Cada processo reconstrói a cena: cenas obtidas com `load_scene()` são recarregadas do arquivo; as demais precisam ser serializáveis com `pickle` (painters definidos no nível do módulo, não lambdas). Num script com `render(..., workers=N)`, proteja a chamada com `if __name__ == "__main__":`. Cada worker ocupa sua própria memória de raster.

```python
from bamboonimation.render import contact_sheet, frame_times

# Todos os frames exportados a 24 fps entre 4,6 s e 6,3 s, em uma única imagem.
contact_sheet(scene, "renders/salto.png", frame_times(4.6, 6.3, 24), cell_width=240)
```

`contact_sheet(scene, output, times, cell_width=320, columns=None, fps=24, supersample=1, overwrite=False, workers=1, labels=True)` grava uma grade PNG com tempo e número de frame (`round(t * fps)`) sob cada célula. `frame_times(start, end, fps)` devolve exatamente os tempos que `render` amostra.

## CLI

```text
bamboonimation render SCENE -o OUTPUT [opções]
bamboonimation frame SCENE -o OUTPUT --time SEGUNDOS [opções]
bamboonimation sheet SCENE -o SHEET.png [--count N | --every-frame] [opções]
bamboonimation benchmark SCENE -o OUTPUT [opções de render]
bamboonimation preview SCENE [opções]
bamboonimation init DIRECTORY
bamboonimation doctor [--json]
```

`python -m bamboonimation` usa a mesma CLI. Um arquivo de cena fornece `scene` ou `make_scene()`. Caminhos relativos usados dentro da sua cena devem ser resolvidos em relação ao arquivo, por exemplo com `Path(__file__).parent / "assets" / "prop.png"`.

| Opção de render | Finalidade |
| --- | --- |
| `--width N --height N` | Resolução em pixels; escala uniforme com barras quando necessário |
| `--fps 24` ou `--fps 24000/1001` | Taxa positiva inteira, decimal ou racional |
| `--start SEC --end SEC` | Intervalo absoluto dentro da cena |
| `--supersample N` | Render maior antes de reduzir; aumenta custo de memória/pixels |
| `--workers auto` | Processos que renderizam frames em paralelo; `auto` usa até 8 núcleos e mantém clipes curtos em série |
| `--threads 2` | Limite de threads solicitado ao encoder |
| `--crf 18 --preset fast` | Controle de qualidade/velocidade para codecs que usam esses parâmetros |
| `--format mp4/webm/mov/png` | Formato explícito; extensão costuma bastar para vídeo |
| `--transparent` | Preserva alpha em formatos compatíveis; não use com MP4 |
| `--overwrite` | Permite substituir um arquivo existente após render bem-sucedido |

### Formatos

| Saída | Codec / comportamento | Alpha |
| --- | --- | --- |
| `.mp4` | H.264, dimensões pares | Não |
| `.webm` | VP9, dimensões pares | Com `--transparent`; compatibilidade de playback varia |
| `.mov` | ProRes 4444 | Com `--transparent` |
| `--format png -o DIRETORIO` | Sequência de frames PNG | Com `--transparent` e fundo transparente |
| Comando `frame -o FRAME.png` | Imagem PNG isolada | Preserva fundo transparente |

PNG sequence exige um diretório novo e não o substitui mesmo com `--overwrite`. Vídeos e frames recusam arquivos existentes por padrão. O vídeo é escrito temporariamente e só ocupa o destino final após sucesso; uma falha não deve destruir o vídeo anterior.

```bash
python -m bamboonimation render scene.py -o renders/shot.mp4 --start 2 --end 5 --fps 24
python -m bamboonimation render scene.py -o renders/alpha.mov --transparent
python -m bamboonimation render scene.py -o renders/sequence --format png --transparent
python -m bamboonimation frame scene.py -o renders/contact.png --time 2.4 --width 640 --height 360
```

### Folhas de contato

```bash
# 12 frames distribuídos de 0 s ao fim da cena (padrão)
python -m bamboonimation sheet scene.py -o renders/visao-geral.png
# Todos os frames de uma ação, como serão exportados a 24 fps
python -m bamboonimation sheet scene.py -o renders/acao.png --start 4.6 --end 6.3 --every-frame --fps 24
```

`--count N` distribui N tempos de `--start` a `--end`, inclusive. `--every-frame` usa os mesmos tempos do comando `render` no intervalo `[start, end)`. `--width` define a largura de cada célula (padrão 320), `--columns` fixa a grade e `--workers` funciona como no render. Uma folha aceita até 400 frames.

A quantidade de frames cobre o intervalo com arredondamento para cima. Assim, a duração codificada pode exceder o intervalo solicitado por menos de um frame. Não prometa uma duração exata que não possa ser representada na taxa escolhida.

### Preview e scaffold

```bash
python -m bamboonimation init minha_animacao
python -m bamboonimation preview minha_animacao/scene.py --width 640 --height 360 --port 8765 --no-open --fps 24
```

O preview usa somente `127.0.0.1`. A timeline solicita PNGs por tempo e é silenciosa: não reproduz `scene.audio`. Se a renderização não acompanhar o relógio, instantes intermediários podem ser omitidos. Use scrub para inspeção pontual e o vídeo exportado para avaliar cadência e áudio; o preview não é benchmark de reprodução em tempo real. As setas avançam ou recuam um frame na taxa de `--fps` (Shift+seta: um segundo; Home/End: extremos), e o relógio mostra o número do frame. `--no-open` evita abrir o navegador automaticamente. Encerre com `Ctrl+C`.

Ao salvar qualquer arquivo `.py` da pasta da cena, o preview recarrega a cena (inclusive módulos auxiliares dessa pasta) e redesenha o tempo atual, sem reiniciar. Se o novo código falhar ao carregar, a página mostra o erro e continua exibindo a última versão válida; o traceback completo aparece no terminal. Erros de desenho também mostram tipo e mensagem na página. Use `--no-reload` para desativar a observação de arquivos. O comando `init` cria um ponto de partida; confira os nomes impressos pela CLI antes de editar.

## Sequências, partículas e cache de cenários

[Qualquer universo em 2D](versatility.md) documenta `Storyboard` para cenas com tempo local e transições, `PathMotion` para trajetórias com velocidade aproximada uniforme, `ParticleSystem` para partículas determinísticas e `StaticLayer` para reutilização de desenhos estáticos. São ferramentas genéricas, sem tema obrigatório. Seus módulos são `bamboonimation.storyboard` e `bamboonimation.procedural`.

O módulo `procedural` também possui uma função `spring` com parâmetros próprios. Confira a assinatura: ela difere do helper `spring` exportado originalmente por `rig`. Não troque uma função pela outra só por compartilhar o nome.
## Personagens e cenários opcionais

O módulo `bamboonimation.cartoon` reúne `Actor`, `Rabbit`, `Pose`, `blend_pose`, `room` e `grain`, além de objetos de cena. Eles usam a mesma API pública e facilitam começar com atuação. Veja [personagens e cenários](cartoon.md). Não é necessário herdar dessas classes para desenhar qualquer outro conteúdo 2D.
## Exposição, deformação e efeitos genéricos

- [Atuação e desenhos substitutos](acting.md): `ExposureSheet`, `Exposure`, `DrawingBank`, `smear_path` e `volume_preserving_squash`.
- [Deformação vetorial](deformation.md): `warp_path`, `LatticeWarp` e `WarpCanvas` a partir de paths originais estáveis, incluindo transformações internas de um desenho vetorial.
- [Efeitos](effects.md): `impact_flash`, `hatch`, `speed_lines`, `motion_echo`, `camera_shake` e `FollowThrough`.

Esses nomes também são exportados por `bamboonimation`. As ferramentas operam em desenhos próprios; poses, perspectiva, contatos, silhuetas e ritmo continuam sendo decisões de autoria. A presença da API não comprova a qualidade da animação que a utiliza.