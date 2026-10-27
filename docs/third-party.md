# Dependências, assets e referência

O código original do projeto está sob [PolyForm Noncommercial 1.0.0](../LICENSE). As dependências continuam sujeitas às suas próprias licenças; a licença do Bamboonimation não as substitui.

| Componente | Função | Licença / origem |
| --- | --- | --- |
| skia-python | Rasterização vetorial CPU e texto | BSD-3-Clause; [projeto](https://github.com/kyamagu/skia-python) |
| Skia | Motor gráfico usado pelo binding | BSD-3-Clause; [licenças e terceiros](https://skia.org/docs/user/license/) |
| NumPy | Arrays e cálculos | BSD-3-Clause; [licença](https://numpy.org/doc/stable/license.html) |
| imageio-ffmpeg | Localização/distribuição de executável FFmpeg | BSD-2-Clause para o wrapper; [projeto](https://github.com/imageio/imageio-ffmpeg) |
| FFmpeg | Codificação de áudio/vídeo | LGPL/GPL conforme o build e codecs; [informações legais](https://ffmpeg.org/legal.html) |
| pytest, build | Desenvolvimento e testes | MIT; [pytest](https://github.com/pytest-dev/pytest), [build](https://github.com/pypa/build) |
| psutil | Medição opcional de recursos | BSD-3-Clause; [projeto](https://github.com/giampaolo/psutil) |

Verifique as versões efetivamente instaladas e seus avisos antes de redistribuir uma distribuição binária ou empacotar FFmpeg. Um executável com `libx264`, por exemplo, pode trazer obrigações GPL; não presuma que todo build do FFmpeg tem os mesmos termos. O repositório não substitui nem relicencia essas dependências.

## Fontes

Texto usa as fontes disponíveis no sistema quando uma família é solicitada. Para renders consistentes entre máquinas, instale e utilize uma fonte licenciada explicitamente para seu projeto. Uma fonte existir no seu computador não concede o direito de distribuí-la.

## Referência de direção artística

[CEREAL! — Animated Student Film](https://www.youtube.com/watch?v=nCKwUB8EVbc), de XrayAlphaCharlie, foi indicado como referência visual. O estudo considera contornos irregulares, cores suaves, profundidade do cenário e atuação por poses. O curta, seus personagens, frames, logotipos e áudio não estão incluídos no projeto. Os exemplos devem usar desenhos e histórias originais.

O framework é uma ferramenta de autoria: ele não gera, transfere ou licencia automaticamente o estilo ou a propriedade intelectual de terceiros.
