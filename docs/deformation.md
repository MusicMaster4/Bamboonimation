# Deformação vetorial com uma fonte estável

`warp_path`, `LatticeWarp` e `WarpCanvas` permitem remodelar desenhos arbitrários: cabeça, cabelo, roupa, criaturas, plantas, máquinas flexíveis ou qualquer outro contorno vetorial. O artista define os deslocamentos. O framework mantém a fonte intacta para que cada frame possa ser calculado pelo tempo absoluto.

Essas ferramentas complementam `Path.morph` e as trocas de desenho. Uma malha de deslocamentos ajuda a curvar ou esticar uma forma que conserva sua estrutura. Uma mão aberta virar um punho, uma boca revelar dentes ou um braço passar de trás para frente do corpo normalmente exige desenhos alternativos e decisões explícitas de sobreposição.

## API

```python
from bamboonimation.deformation import warp_path, LatticeWarp, WarpCanvas

# mapper recebe dois números e devolve uma posição (x, y).
nova_forma = warp_path(svg_data_ou_skia_path, mapper)

warp = LatticeWarp(
    bounds=(left, top, right, bottom),  # LTRB; não é x, y, largura, altura
    offsets=[
        [(dx00, dy00), (dx01, dy01)],  # linha de cima: esquerda → direita
        [(dx10, dy10), (dx11, dy11)],  # linha de baixo
    ],
    clamp=True,
    strength=1.0,
)

ponto = warp.map(x, y)
ponto = warp.map((x, y))
ponto = warp(x, y)
outro_warp = warp.with_strength(0.5)
```

`warp_path` devolve um novo `skia.Path`, aceito diretamente por `Canvas.path`. A fonte pode ser uma string de comandos SVG ou um `skia.Path`. O mapper deve ter assinatura `mapper(x, y) -> (x, y)` e devolver coordenadas finitas. Ele deve ser determinístico para que buscas fora de ordem produzam o mesmo desenho.

A malha precisa ter pelo menos duas linhas e duas colunas, com a mesma quantidade de colunas em todas as linhas. Cada célula contém um par de **deslocamentos**, e não a posição final de um ponto de controle. `bounds` também aceita `skia.Rect`. Os limites precisam ter largura e altura positivas e finitas. Os dados recebidos são copiados para tuplas imutáveis, portanto alterar depois a lista usada para criar a malha não altera o warp.

`strength=0` é identidade; `1` aplica os deslocamentos completos. Valores negativos e maiores que um são permitidos para antecipação e overshoot. `with_strength` cria outro objeto e preserva o anterior. Não há simulação acumulada nem dependência do fps de saída.

Com `clamp=True`, pontos fora dos limites recebem o deslocamento da borda mais próxima. A posição original do ponto continua fora: a opção **não recorta a geometria**. Com `clamp=False`, o deslocamento é extrapolado a partir da célula da borda. Use essa opção deliberadamente, pois pontos distantes podem receber deslocamentos grandes.

## Exemplo completo: forma flexível, detalhe e contato

Salve o exemplo a seguir como `flexivel.py`. Ele produz uma cena de 12 segundos sem baixar imagens, usar um personagem pronto ou chamar um modelo de IA.

```python
import skia
from bamboonimation import Scene, Track
from bamboonimation.deformation import LatticeWarp, warp_path

# Contorno e detalhe sempre permanecem na posição original.
SHELL = "M0 0 L0 -180 C80 -220 160 -220 240 -180 L240 0 Z"
SEAM = "M20 -10 L20 -174 C85 -201 155 -201 220 -174 L220 -10"
CONTACT = (240, -180)  # um endpoint do contorno, não um ponto estimado por frame

lattice = LatticeWarp(
    (0, -220, 240, 0),
    [
        [(-15, -20), (0, -40), (30, -10)],
        [(-8, 0), (18, -12), (16, 5)],
        [(0, 0), (0, 0), (0, 0)],  # base fixada
    ],
)
amount = (
    Track(0).add(0, 0).add(2, .7).add(3, -.2)
    .add(4, 0).add(6, 1).add(7.5, 0).add(12, 0)
)


def paint(c, t):
    deformation = lattice.with_strength(amount(t))
    with c.transform(470, 500):
        c.path(warp_path(SHELL, deformation), "#cf8c6e", "#34303e", 3)
        c.path(warp_path(SEAM, deformation), None, "#f8dcb1", 2)
        # O contato usa o mesmo mapper que o endpoint desenhado.
        x, y = deformation.map(CONTACT)
        c.ellipse(x, y, 9, 9, "#726e9d", "#34303e", 2)


scene = Scene(1280, 720, 12, background="#ede0c5", painter=paint)
```

Renderize com:

```sh
python -m bamboonimation render flexivel.py -o renders/flexivel.mp4
```

O contorno, a costura e a posição de contato derivam do mesmo estado. A base permanece fixa porque seus deslocamentos são zero. O marcador é um objeto rígido que acompanha o endpoint; para deformar também sua silhueta, crie sua forma como `skia.Path` e aplique `warp_path` nela.

## Deformar um desenho inteiro com transformações internas

`WarpCanvas(canvas, mapper)` é um `Canvas` que aplica o mesmo mapper a todos os caminhos desenhados por ele. Isso inclui `path`, `ellipse`, `rect`, `line`, `polygon` e o caminho usado por `clip`. Um desenho procedural existente pode manter seus grupos locais para cabeça, olhos, mãos e roupa.

Crie o wrapper **dentro da transformação que posiciona o personagem**. Esse espaço do pai fica registrado na construção. Novas transformações internas são convertidas para esse espaço antes da deformação:

```python
from bamboonimation.deformation import LatticeWarp, WarpCanvas


def draw_figure(c):
    c.rect(-35, -110, 70, 110, "#cd8a61", "#34303e", 2, radius=9)
    with c.transform(0, -145):
        c.ellipse(0, 0, 34, 39, "#efc09b", "#34303e", 2)
        with c.transform(12, -6):
            c.ellipse(0, 0, 5, 8, "#34303e")
    with c.transform(35, -90):
        c.line([(0, 0), (22, 12), (32, -4)], "#34303e", 9)


def paint(c, t):
    warp = LatticeWarp(
        (-70, -190, 100, 0),
        [
            [(35, -10), (60, -15)],
            [(10, 0), (24, -5)],
            [(0, 0), (0, 0)],
        ],
        strength=1.0 if 1.0 <= t < 1.1 else 0.0,
    )
    with c.transform(500, 550):
        deformed = WarpCanvas(c, warp)
        draw_figure(deformed)
```

O olho passa por duas transformações locais, mas recebe a deformação da mesma região da malha que a cabeça. Não desenhe uma segunda figura normal por baixo do wrapper quando a intenção for substituir a silhueta por um smear: desenhe uma única versão deformada nesse frame. A autoria da pose, dos deslocamentos e da exposição continua com o artista.

Em termos de coordenadas, `B` é a matriz do pai capturada na construção e `M` é a matriz atual do Skia. Para cada ponto local, o wrapper calcula `P = inverse(B) * M`, deforma `P(ponto)` e converte o resultado de volta com `inverse(P)`. O Skia desenha o caminho sob a transformação atual. Isso mantém o desenho e seus detalhes no mesmo espaço, mesmo com translações, rotações e escalas internas. Um anchor expresso no espaço capturado pode usar `warp(anchor)` para acompanhar um endpoint correspondente.

O wrapper compartilha `raw` e copia largura, altura, tempo e seed na construção. `roughness`, `boil_fps` e `stroke_scale` começam com os mesmos valores, mas alterações posteriores de estilo no wrapper não alteram o `Canvas` original. Como a superfície e a pilha de transformações são compartilhadas, use `with deformed.transform(...)` ou `with deformed.saved()` para isolar transformações. Crie um wrapper por amostra de tempo a partir da fonte estável; ele não integra estados anteriores.

`opacity` funciona normalmente; `shadow` usa uma elipse deformada. `gradient_rect` deforma o contorno do retângulo, mas mantém o shader do gradiente nas coordenadas locais: ele não deforma as cores ponto a ponto. A largura dos contornos conserva a política de estilo do `Canvas`; não se estica automaticamente segundo a derivada local da malha. O grão de `paper` permanece como composição de textura sem deformação.

`text` e `image` levantam `NotImplementedError` com orientação para fornecer contornos vetoriais. Isso inclui documentos SVG completos importados por `image`: passe dados de caminhos a `path` para deformá-los. Chamadas diretas a `deformed.raw` são uma saída explícita sem warp. Matrizes do pai ou de transformações internas precisam ser finitas e invertíveis. Uma escala zero levanta `ValueError`; omita o desenho nesse estado ou use uma escala pequena diferente de zero quando fizer sentido artístico.

## O que é preservado

A iteração usa os verbos nativos do Skia. Movimentos, linhas, curvas quadráticas, curvas cúbicas, cônicas racionais e fechamento de contornos são reconstruídos com a mesma estrutura. As cônicas conservam seus pesos, inclusive nas elipses e nos segmentos produzidos por arcos SVG. A regra de preenchimento também é preservada.

Uma função afim — translação, rotação, escala, shear ou sua composição — aplicada aos pontos de controle reproduz exatamente a curva transformada, dentro da precisão de ponto flutuante do Skia. Uma função não linear transforma a **rede de pontos de controle**: ela não representa necessariamente a transformação ponto a ponto de todo o interior de uma curva. Esse é um controle de desenho, não uma promessa de deformação geométrica exata.

Um anchor que coincide com um endpoint desenhado acompanha esse endpoint exatamente quando ambos usam o mesmo mapper. Um anchor arbitrário no interior de uma curva pode precisar ser recalculado a partir da curva deformada: sob uma função não linear, mapear o ponto original da curva não é, em geral, igual a avaliar a curva cujos pontos de controle foram mapeados.

## Boas práticas e limites

- Calcule cada frame a partir do contorno original. Aplicar um warp ao resultado do frame anterior acumula erros e impede busca determinística.
- Inclua os pontos de controle relevantes nos limites da malha; uma alça de Bézier fora da malha recebe o comportamento de borda escolhido.
- Deforme juntos os detalhes que pertencem à mesma superfície: sombra, costura, sobrancelha ou linha interna precisam acompanhar a forma principal.
- Use controles locais para manter mandíbula, ombro, punho e raízes de cabelo coerentes. Uma malha não conhece anatomia nem conserva volume automaticamente.
- Separe mudança de forma, troca de desenho, ordem de camadas e contato. Cada uma resolve uma parte diferente da atuação.
- Use curvas e poses fortes antes de adicionar jitter, textura ou movimento secundário. Esses efeitos não corrigem um gesto sem clareza.
- Textos, imagens raster e documentos SVG completos não são deformados por essa API. Ela opera em dados de caminho ou `skia.Path`; não converte automaticamente layout de texto ou pixels em vetores.
- O estilo de contorno continua sendo responsabilidade do `Canvas`. Para compensar um zoom de câmera, `c.stroke_scale = 1 / zoom` controla explicitamente a largura do traço e a amplitude da irregularidade. Geometria preenchida permanece intacta; desenho direto em `c.raw` e imagens importadas conservam seus próprios estilos.

Os testes verificam transformação afim contra o Skia, identidade de contornos, pesos de cônicas de círculos, interpolação e comportamento externo da malha, coerência de um endpoint com seu anchor, busca em ordem inversa e rejeição de entradas inválidas. Esses testes não comprovam equivalência artística a um filme de referência; essa avaliação depende dos desenhos e de revisão visual sequencial.
