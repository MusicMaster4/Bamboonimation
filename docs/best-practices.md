# Boas práticas de autoria e renderização

## Comece pela história e pela silhueta

Defina uma ação que possa ser lida sem áudio. Separe-a em preparação, antecipação, ação, reação e resolução. Um curta de 12 segundos pode conter poucos gestos bem escolhidos. Movimento constante costuma reduzir o contraste entre os momentos importantes.

Desenhe as poses principais antes dos intermediários. Reduza o frame ou olhe só a silhueta: mãos, braços e objetos devem continuar distinguíveis. Direcione olhos, cabeça e peito para tornar a intenção legível. Evite tangências involuntárias entre contornos.

## Defina um sistema visual

Escolha uma paleta curta com cor de contorno, luz, sombra e dois ou três acentos. Um fundo mais discreto ajuda o personagem a destacar-se. Use linhas de perspectiva e sobreposição para dar profundidade mesmo sem mover a câmera.

Mantenha espessuras consistentes em unidades lógicas. Variação de contorno pode sugerir lápis, mas não compensa desenhos sem estrutura. Aplique papel uma vez ao final com intensidade pequena; o efeito deve continuar discreto em movimento.

Arte original é independente do tema. Um rig humano, um inseto, uma máquina ou um objeto abstrato usam os mesmos transforms e canais. Não adapte todo assunto à aparência dos personagens dos exemplos.

## Faça atuação, depois interpolação

Uma mão pode preparar um movimento devagar, acelerar e parar rapidamente no contato. Interpolar tudo com o mesmo easing tende a parecer flutuação. Reserve pausas de leitura e crie antecipação proporcional à força da ação.

Use squash/stretch com propósito: preserve o volume aparente e mantenha pés e mãos nos contatos. Uma cabeça oval escalada sem revisão pode alterar olhos e boca de forma indesejada. Use desenhos substitutos quando uma nova perspectiva precisar de anatomia diferente.

Piscar deve acompanhar o ritmo da atuação, sem esconder o olhar no momento decisivo. Respiração, cabelo e roupa podem reagir com atraso; mantenha a amplitude pequena para que não disputem atenção com a ação principal.

## Contatos e rigs

Confira um frame antes, no instante e um frame depois de pegar um objeto. O objeto deve acompanhar a mão no intervalo apropriado. Evite deslizamento de pés ou dedos no plano de apoio.

No `Actor` opcional, use [BodyPose](cartoon.md#bodypose-peso-apoio-e-contato) para contrapor peito e pelve sem mover os apoios autorados dos pés. Compartilhe o mesmo `body` e a mesma colocação entre desenho e helpers de mão; `pose_for_hand` resolve a posição da palma, enquanto dedos, oclusão e anatomia continuam sendo decisões de desenho. Para outros sujeitos, use poses e anchors próprios.

Marque pivôs locais antes de animar. Ossos apontam em +x; a malha/desenho deve estar orientada de acordo. Em IK, confira o espaço de coordenadas do alvo e o lado escolhido para o cotovelo. Alvos inalcançáveis são limitados; isso não torna qualquer pose convincente.

Dobre detalhes que revelam cortes sob mangas, cabelo e outras peças de sobreposição. Quando o contorno precisar mudar muito, substitua o desenho ou use morphing compatível.

## Animação desenhada em código

Use funções de desenho pequenas: cabeça, mão, roupa, objeto e cenário. Dê nomes às cores, medidas e marcos temporais. Um agente consegue editar `hand_reach` ou `cup_contact_time` com mais segurança do que dezenas de números sem nome.

Guarde curvas vetoriais e assets recorrentes fora do trabalho por frame. Imagens devem usar caminhos relativos ao arquivo de cena, com `Path(__file__).parent`. Importe somente assets que você possa distribuir e usar.

Calcule poses com tempo absoluto. Para variação estável, use seed explícita. Se uma cena exigir simulação física, calcule e salve previamente os estados ou use uma solução analítica em vez de simular de novo a partir do frame consultado.

## Câmera e enquadramento

Movimento de câmera precisa de motivação: mostrar uma reação, revelar algo ou acompanhar uma ação. Um zoom sutil não substitui uma pose fraca. Confira bordas, membros cortados e espaço para o olhar durante todo o movimento.

Crie a composição lógica na proporção desejada. Exportar 16:9 em 9:16 com barras preserva a imagem, mas não cria um enquadramento vertical pensado. Faça uma variante de cena quando a leitura exigir.

## Trabalhe por níveis de revisão

1. **Poses:** frames em baixa resolução nos tempos principais.
2. **Movimento:** rascunho 640 × 360, FPS adequado para avaliar ritmo.
3. **Acabamento:** render de um trecho difícil com a resolução final.
4. **Entrega:** vídeo completo com formato, taxa e áudio conferidos.

Veja o filme em velocidade normal. Um contact sheet ajuda a detectar poses ruins, mas não prova ritmo, continuidade, sincronização ou ausência de tremor. Ouça também a transição e o fim do áudio.

## Mantenha o custo previsível

Quantidade de pixels e frequência de amostragem são fatores grandes. 3840 × 2160 contém quatro vezes os pixels de 1920 × 1080. A 60 fps são 2,5 vezes os frames de 24 fps. A combinação pode gerar aproximadamente dez vezes o trabalho de pixels, antes de considerar o codec e os efeitos.

Evite superfícies desnecessárias, muitos layers de opacidade e blur pesado. Não leia arquivos, gere ruído grande ou faça chamadas de rede dentro do callback. Faça rascunhos antes de aumentar supersampling. Use a quantidade de threads necessária ao seu fluxo e deixe espaço para o restante do computador.

Não salve todos os frames em memória. Uma sequência PNG facilita retomada e composição externa, mas consome disco. Um vídeo codificado em fluxo costuma ser mais compacto. Confira o espaço disponível antes de um trabalho longo.

## Entregas reproduzíveis

Registre commit da cena, versões de Python/dependências, seed, resolução, FPS exato, intervalo e opções de encoder. Use as mesmas fontes e assets. Guarde o relatório e uma imagem de referência do seu próprio render.

Para benchmark, informe a cena e a máquina, não apenas “FPS de render”. Separe throughput de entrega em tempo real, velocidade de amostragem e custo de codificação. Meça o processo completo se for afirmar uso de RAM incluindo FFmpeg. Resultados locais não garantem a mesma performance em hardware diferente.

## Revisão pública

Antes de compartilhar, confira licença de código e assets, remova dados privados e mantenha os avisos necessários. Não use uma obra de referência como se o projeto concedesse direitos sobre ela. A licença do software é não comercial; consulte [LICENSE](../LICENSE).