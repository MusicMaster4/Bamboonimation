# Personagens e cenários opcionais

`bamboonimation.cartoon` fornece desenhos originais prontos para experimentar atuação: a personagem Mira, o coelho Pip, uma sala ilustrada e pequenos objetos. Tudo usa a API pública de desenho e pode servir de estudo. O motor funciona igualmente com seu próprio elenco ou qualquer outro assunto 2D.

## Actor

```python
from bamboonimation.cartoon import Actor

actor = Actor(shirt="#cc7053", hair="#35495b", skin="#eeb28f")

# Dentro de painter(canvas,t):
actor.draw(c, x=560, y=670, t=t, scale=1.2,
           pose="think", expression="curious", look=(3, -2))
```

`x,y` posicionam o apoio dos pés. `scale` muda o tamanho; `facing=-1` espelha horizontalmente. `squash` altera a proporção corporal: mantenha-o próximo de 1 para não deformar a atuação. `walk` é uma fase em radianos, não uma velocidade; por exemplo, `walk=t*6` anima um ciclo. A cena decide o deslocamento de caminhada.

`look=(dx,dy)` desloca as pupilas, com limites para preservar o desenho. O piscar padrão é calculado a partir de `t`; `blink=True` ou `False` permite controlar o fechamento. Expressões frontais disponíveis: `content`, `curious`, `surprise`, `delighted`, `worried`, `sleepy` e `shout`. `shout` remodela a mandíbula com `LatticeWarp` e usa uma boca própria; `worried` inclui assimetria de pálpebra/sobrancelha. Nem todo nome produz uma mudança distinta em toda a anatomia. `blink` fecha os dois olhos juntos; não é um controle independente de cada olho.

Poses prontas: `idle`, `offer`, `surprise`, `think`, `celebrate` e `sneak`. Os nomes de expressão e de pose são canais distintos.
`view=0.0` a `view=1.0` controla uma virada contínua de frente para perfil; `"front"`, `"three_quarter"` e `"profile"` são atalhos para 0, 0,55 e 1. O modelo usa um único nariz registrado e move crânio, orelha, franja, olhos e boca de forma coordenada. O olho e a sobrancelha distantes seguem a mesma oclusão, e os detalhes são limitados pelo contorno do rosto. `FacePose` funciona durante toda a virada. Por exemplo, `view=smooth(1, 1.8, t)` faz a cabeça virar em 0,8 s. `facing=-1` espelha o resultado. Coordene também olhar, tronco e ombros para dar intenção à virada; não troque vistas instantaneamente por conveniência. Subclasses que implementam os métodos `head`, `profile` ou `three_quarter` continuam responsáveis por desenhar seus próprios intermediários.

Para trocar o design, crie sua função de desenho ou uma subclasse com outra implementação de `head`/`draw`. As cores do construtor oferecem uma variação rápida do desenho existente; para um novo personagem, revise também mãos, proporções e detalhes de roupa. `Actor` não transforma uma imagem arbitrária em um personagem articulado.

## Pose e transição

```python
from bamboonimation.cartoon import Actor, Pose, POSES, blend_pose, smooth

actor = Actor()
custom = Pose(left=(-80, -180), right=(110, -210),
              tilt=-8, lean=5, crouch=4)


def draw_actor(c, t):
    amount = smooth(2, 2.6, t)
    pose = blend_pose(POSES["idle"], custom, amount)
    actor.draw(c, 560, 670, t, pose=pose, expression="delighted")
```

`left` e `right` são alvos locais das mãos, medidos a partir da origem do personagem nos pés. `tilt` é a rotação da cabeça em graus. `lean` desloca/inclina o corpo; `crouch` acrescenta deslocamento vertical ao tronco. Eles são controles artísticos simples, não um simulador de anatomia.

`smooth(a,b,t)` devolve uma rampa 0→1 com extremos mantidos. `blend_pose(a,b,amount)` mistura os campos de duas poses, limitando `amount` ao intervalo 0–1. O desenho fica fácil de consultar em qualquer tempo: não é preciso reproduzir frames anteriores.

## BodyPose: peso, apoio e contato

`BodyPose` acrescenta articulação autorada de peito, pelve, cabeça, joelhos e pés ao `Actor` opcional. Os presets de `BODY_POSES` são `neutral`, `reach`, `brace`, `airborne` e `catch`; passe o nome ou um objeto em `body=`. `body=None`, o padrão, conserva o modelo anterior. `body="neutral"` já ativa o novo desenho corporal, em posição neutra; não é uma promessa de pixels iguais ao modelo anterior.

| Campos | Espaço e significado |
| --- | --- |
| `chest`, `pelvis`, `head` | Deslocamentos a partir do modelo em repouso, em unidades locais do ator |
| `chest_angle`, `pelvis_angle`, `head_angle` | Graus; peito gira em torno de `(0,-182)`, pelve em torno de `(0,-104)` e cabeça recebe ajuste próprio no pescoço |
| `left_foot`, `right_foot`, `left_knee`, `right_knee` | Pontos locais absolutos, antes de posição, escala, espelhamento e squash do ator |
| `heel_lift` | Par esquerda/direita para rolar cada sapato sobre a ponta; o apoio local fica em `foot + (22,6)` |
| `elbow_bias` | Par de ajustes esquerda/direita da curva dos cotovelos |
| `planes` | Quatro pesos das soluções de contorno reach/brace/airborne/catch; uso avançado |

`blend_body(a,b,amount)` aceita objetos ou nomes de presets e limita `amount` a 0–1. Interpola pontos, ângulos e pesos dos contornos, sem trocar a geometria abruptamente no meio. `mode` é um rótulo, não um estado que muda sozinho durante a interpolação. Use `dataclasses.replace` para derivar uma pose imutável. Os presets têm apoios diferentes: para manter os pés plantados, fixe os mesmos pontos de pé nas duas poses e controle os calcanhares. Alterar `x`, `y`, `scale`, `facing`, `squash` ou uma transformação externa ainda move esses apoios; o helper não resolve automaticamente contato com o chão.

### Uma mão fixa enquanto o corpo muda

Salve como `body_contact.py`. Este exemplo completo mantém o registro da palma em um alvo enquanto peito e pelve mudam; o pequeno objeto usa o mesmo anchor. Não há assets externos.

```python
from dataclasses import replace
from bamboonimation import Scene
from bamboonimation.cartoon import Actor, Pose, blend_body, smooth

actor = Actor()
TARGET = (735, 450)


def draw(c, t):
    amount = smooth(.4, 1.5, t) * (1 - smooth(2.3, 3.5, t))
    body = replace(blend_body("neutral", "reach", amount),
                   left_foot=(-32, -9), right_foot=(36, -9),
                   heel_lift=(0, 0))
    placement = dict(x=600, y=672, t=t, scale=1.25,
                     walk=0, facing=1, squash=1, body=body)
    pose = actor.pose_for_hand("right", TARGET,
                              pose=Pose(left=(-65, -145)), **placement)
    c.rect(0, 668, 1280, 52, fill="#cbb48e")
    c.shadow(600, 668, 67, 8)
    actor.draw(c, pose=pose, hand_shapes={"right": "open"},
               shadow=False, **placement)
    actor.draw_arm(c, "right", pose=pose, shape="open",
                   occlude_root=True, **placement)
    px, py, _ = actor.hand_anchor("right", pose=pose, **placement)
    c.ellipse(px, py, 9, 9, fill="#738e88", stroke="#493f4a", width=2)


scene = Scene(duration=4, background="#f2e4cb", painter=draw)
```

`pose_for_hand` devolve uma nova `Pose` cuja palma alcança o alvo, incluindo peito, lean, bob, squash, escala e espelhamento. É uma restrição de **posição**: não escolhe orientação dos dedos, grip, alcance anatômico ou oclusão. O exemplo desenha um objeto no registro da palma; para envolvê-lo com dedos, desenhe explicitamente as camadas posterior/objeto/anterior.

Passe o **mesmo `body` e os mesmos parâmetros de colocação** para `pose_for_hand`, `draw`, `hand_anchor` e `draw_arm`. O alvo e o anchor ficam no espaço do pai do ator; excluem câmera e escala da exportação. Para uma rotação externa em torno de `(x,y)`, `pose_for_hand(..., rotation=graus)` inverte essa rotação; desenhe sob a transformação correspondente. `hand_anchor` não inclui essa rotação externa: componha-a ao converter o resultado para o espaço que contém o prop.

`front_hands=("right",)` põe esse braço/mão à frente do corpo; `hand_shapes` aceita `fist`, `open` ou `none` por lado; `none` deixa o desenho da mão a cargo da cena. Se uma mesa ou outro primeiro plano for desenhado depois do ator, use `draw_arm` após esse elemento, com os mesmos `pose`, `body`, `shoulder_turn` e argumentos de colocação, e então desenhe o prop e os dedos anteriores. `draw_arm(..., occlude_root=True)` mantém a raiz da manga atrás do limite do casaco, preservando a mão e o trecho do braço que deve passar sobre o prop. Use essa opção no redesenho de braços sobre mesas/objetos; o padrão `False` permite gestos intencionais à frente do tronco. A mão não é apagada pelo recorte da raiz. `shadow=False` remove apenas a sombra automática do ator, permitindo uma sombra própria fixa no chão durante um salto.

De outro diretório, informe os caminhos absolutos da cena e da saída. Por exemplo, partindo da pasta do projeto em PowerShell:

```powershell
$bodyScene = (Resolve-Path .\body_contact.py).Path
$bodyOutput = Join-Path (Split-Path $bodyScene) 'renders\body_contact.mp4'
Push-Location $env:TEMP
python -m bamboonimation render $bodyScene -o $bodyOutput --width 640 --height 360 --fps 24
Pop-Location
```

O Python usado nesse comando precisa ter o pacote instalado. Reexecutar sobre uma saída existente exige novo nome ou `--overwrite`. Para um sujeito original — criatura, robô, objeto ou outro personagem — desenhe suas próprias poses e anchors com [DrawingBank](acting.md#register-replacement-drawings), [deformação](deformation.md) ou callbacks; `BodyPose` não infere anatomia de um desenho arbitrário e não é uma classe obrigatória do motor.

## Rabbit

```python
from bamboonimation.cartoon import Rabbit

rabbit = Rabbit()


def draw_rabbit(c, t):
    rabbit.draw(c, 850, 650, t, scale=1.3,
                look=(-2, 0), expression="sleepy", squash=1.03)
```

A origem também fica no apoio inferior do desenho. O helper possui `x`, `y`, `t`, `scale`, `expression`, `look` e `squash`. As expressões são `content`, `sleepy`, `inhale`, `sneeze` e `laugh`, com alterações de olhos, boca e sobrancelhas conforme o gesto. Não presuma o mesmo banco de expressões do `Actor`. Para um salto, anime explicitamente `y` e a proporção.

## Cenário, objetos e acabamento

```python
from bamboonimation import Scene
from bamboonimation.cartoon import Actor, Rabbit, room, grain

actor, rabbit = Actor(), Rabbit()


def draw(c, t):
    room(c)
    actor.draw(c, 500, 665, t, pose="offer", expression="content")
    rabbit.draw(c, 850, 655, t, scale=1.4, look=(-2, 0))
    grain(c, amount=.12, seed=1)


scene = Scene(duration=12, painter=draw)
```

`room(c,mood='day')` desenha uma sala original no espaço 1280 × 720. O fundo estático é reutilizado por uma camada cacheada, considerando a escala de saída. Para proporções ou dimensões lógicas diferentes, faça um cenário próprio ou aplique uma transformação planejada; o helper não redesenha automaticamente a composição.

`grain(c,amount=.12,seed=1)` aplica acabamento de papel pela textura de `Canvas.paper`. Use-o depois do desenho. A API `Canvas.paper` oferece o mesmo tipo de acabamento para cenários próprios. Intensidade e seed fixas mantêm a textura estável.

Para criar sua própria camada de papel estática:

```python
from bamboonimation.procedural import StaticLayer

paper = StaticLayer(lambda c: c.paper(amount=.12, seed=1))


def finish(c, t):
    paper(c)  # composição sobre fundo transparente; sem preencher de branco
```

A granulação pode acrescentar alpha também a regiões vazias de uma cena transparente. Para sprites com transparência limpa fora da silhueta, aplique papel dentro de `Canvas.clip` ou prepare o acabamento no próprio desenho.

Outros helpers no mesmo módulo: `cup`, `cup_fingers`, `cookie`, `plant`, `table`, `steam` e `accents`. Consulte as assinaturas no código antes de usar. São elementos opcionais dos curtas, sem limitar cenários ou histórias novos.

## Xícara e contato de dedos

`cup(c,x,y,rotation=0,scale=1)` e `cup_fingers(c,x,y,rotation=0,scale=1)` compartilham a mesma colocação. Desenhe a mão/braço posterior, a xícara e depois os dedos anteriores:

```python
from bamboonimation.cartoon import cup, cup_fingers


def draw_grip(c, t):
    placement = dict(x=707, y=543, rotation=-8, scale=1)
    # O desenho de braço/palma posterior deve chegar a esse mesmo grip.
    cup(c, **placement)
    cup_fingers(c, **placement)
```

Esse grupo desenha contato visível na borda; não encontra automaticamente o punho do personagem. Ao pegar ou soltar, anime aproximação, registro, oclusão e retirada. O pires permanece no apoio durante o movimento da xícara. Para personagens com outro desenho ou cor de pele, forneça seus próprios dedos. Para grips e substituições genéricos, veja [DrawingBank](acting.md#register-replacement-drawings); para mudar formas, veja [deformação](deformation.md).
## Rascunho rápido

O arquivo [quickstart.py](../examples/quickstart.py) combina personagem, olhar, mariposa e acabamento em poucas linhas:

```bash
python -m bamboonimation frame examples/quickstart.py --time 2 -o renders/quickstart-pose.png --width 640 --height 360
python -m bamboonimation render examples/quickstart.py -o renders/quickstart.mp4 --width 640 --height 360 --fps 24
```

Assista à ação antes de aumentar a resolução. Troque um elemento por vez para aprender como os controles alteram a leitura da cena.
## Atuação em três quartos e mãos registradas

`Actor.draw(..., view="three_quarter", face=FacePose(...), shoulder_turn=...)` usa um desenho próprio de cabelo, orelha, nariz, bochecha e planos dos olhos. `FacePose` controla cada pálpebra e sobrancelha, além de bochecha e mandíbula. `shoulder_turn`, entre -1 e 1, muda a silhueta do casaco e a origem dos braços. Assim, olhos, cabeça e ombros podem preparar e concluir o gesto em momentos diferentes. Os controles de `FacePose` acompanham também a virada contínua de frente para perfil, mantendo o mesmo modelo.

Para alinhar uma palma a um objeto, `pose_for_hand` devolve uma nova `Pose`. O alvo usa coordenadas do espaço pai do ator, antes da câmera e da escala de exportação. A função considera lean, crouch, respiração, caminhada, facing e squash; o argumento `rotation` inclui uma rotação externa do Canvas ao redor do ator. Ela resolve posição: orientação do punho, dedos, alcance anatômico e intenção da pose continuam decisões de autoria.

Este exemplo mantém o contato ao variar squash e contragirar os ombros:

```python
import math
from bamboonimation import Scene
from bamboonimation.cartoon import (Actor, FacePose, room, table, cup,
                                    cup_handle_anchor, cup_handle_grip)

actor = Actor()


def paint_contact(c, t):
    room(c)
    squash = 1 + .025 * math.sin(t * 2)
    placement = dict(x=535, y=670, t=t, scale=1.15, squash=squash)
    wrist = cup_handle_anchor(715, 530, handle_side=-1)
    pose = actor.pose_for_hand("right", wrist, pose="offer", **placement)
    turn = -.4 * math.sin(t)
    actor.draw(c, pose=pose, view="three_quarter", shoulder_turn=turn,
               hand_shapes={"right": "none"}, face=FacePose(eye_open=(.65, 1), brow_offset=(2, -2), cheek=3),
               look=(3, 4), **placement)
    table(c)
    # A mesa encobre o corpo, mas o antebraço passa acima dela.
    actor.draw_arm(c, "right", pose=pose, shoulder_turn=turn, shape="none", **placement)
    cup(c, 715, 530, handle_side=-1)
    cup_handle_grip(c, 715, 530, handle_side=-1, skin=actor.skin)


scene = Scene(duration=10, painter=paint_contact)
```

Use os mesmos argumentos de colocação no ator, no solver e em `draw_arm`. O solver não limita alvos distantes ao alcance do braço: reveja a silhueta e mova o corpo quando necessário. Para outros personagens, o grafo fornece `Node.world_point` e `Node.local_point`, e `DrawingBank.anchor` registra pontos em desenhos substitutos; a matemática não depende do modelo Mira.

## Contato com a alça e mãos personalizadas

O exemplo de chá orienta a alça para o personagem: `cup(c, x, y, handle_side=-1)`. `cup_handle_anchor(x, y, rotation, scale, handle_side=-1)` devolve o contato do punho correspondente ao desenho `cup_handle_grip`. Resolva o braço com `pose_for_hand`, desenhe a xícara e então a mão registrada. `closure=0..1` abre/fecha os dedos, e `skin` preserva a cor do personagem. Rotação, escala e lado precisam coincidir entre objeto, anchor e mão.

Use `hand_shapes={"right": "none"}` em `Actor.draw` e `shape="none"` em `draw_arm` para suprimir a mão genérica quando seu desenho de contato já inclui punho, palma e dedos. Isso permite também criar mãos para qualquer outro objeto. Evite sobrepor uma segunda palma ou dedos soltos. Mantenha o mesmo desenho ao retirar a mão: trocar de repente pelo punho genérico pode fazê-la saltar de volta para o objeto. Uma coincidência numérica de anchors não substitui revisar o contorno e a ordem de oclusão em tamanho nativo.
