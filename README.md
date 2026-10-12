# ASCII-Vibes-Visualizer

Visualizador musical retro-futurista para **Windows 10/11**. Todo lo que ves está hecho con
caracteres ASCII generados por código (nada de vídeos ni imágenes convertidas) y reacciona en
tiempo real al audio de tu PC.

## Instalador de Windows

El proyecto incluye `build_installer.bat` y `installer\ASCII-Vibes-Visualizer.iss` para crear un
instalador con **Inno Setup 6**. El asistente permite seleccionar español o inglés, muestra el logo
del proyecto y crea accesos directos con su icono.

1. Instala Inno Setup 6 desde [jrsoftware.org/isinfo.php](https://jrsoftware.org/isinfo.php).
2. Ejecuta `setup.bat` para preparar el entorno Python.
3. Ejecuta `build_installer.bat`.
4. El instalador aparece en `dist\installer\ASCII-Vibes-Visualizer-Setup.exe`.

El proceso genera primero una aplicación portable con PyInstaller y luego la empaqueta. Para crear
solo la versión portable, ejecuta `build_exe.bat`; el resultado queda en
`dist\ASCII-Vibes-Visualizer\`.

## Instalación (VS Code)

1. Necesitas Python 3.10 o superior (también funciona con 3.14) desde python.org, con *Add python.exe to PATH*.
2. Abre esta carpeta en VS Code (`Archivo > Abrir carpeta`).
3. En la terminal de VS Code:
   ```bat
   setup.bat
   ```
   (crea `.venv` e instala `pygame-ce`, `numpy` y la librería de captura: `PyAudioWPatch`, o `soundcard` en Python 3.14).
4. Ejecuta con `run.bat`, o con **F5** en VS Code (elige el intérprete `.venv` si te lo pide).

Para probar sin captura real: `run.bat --demo` (música sintética). Para arrancar a pantalla
completa: `run.bat --fullscreen`.

## Audio

* **Salida predeterminada de Windows (loopback)**: captura todo lo que suena en el PC, sin
  instalar nada (usa WASAPI loopback vía PyAudioWPatch). Es la opción que se elige por defecto.
* Cualquier otra salida (loopback), micrófonos y entradas físicas, y dispositivos virtuales ya
  instalados (VB-CABLE, VoiceMeeter…, marcados como `VIRTUAL`). Se muestran con su nombre real.
* «ACTUALIZAR DISPOSITIVOS» vuelve a listar y reabre la fuente actual; se puede cambiar de
  dispositivo en caliente. Si un dispositivo se desconecta, la app muestra el motivo y reintenta
  cada pocos segundos; un fallo de audio nunca cierra el programa.
* Si Windows bloquea el micrófono: *Configuración > Privacidad y seguridad > Micrófono* y permite
  las aplicaciones de escritorio.
* Silencio: con loopback, Windows no entrega muestras cuando no suena nada; las visuales siguen
  animándose por sí solas.

Análisis (hilo separado del render): RMS, graves (30–220 Hz), medios (220–2200 Hz), agudos
(2.2–14 kHz) por FFT de 2048 puntos con ventana de Hann, normalización adaptativa (AGC),
suavizado ataque/liberación y detección de transitorios por flujo espectral.

## Controles

| Tecla | Acción |
|---|---|
| `F11` | Pantalla completa real (sin bordes ni controles) |
| `Esc` | Salir de pantalla completa / volver a la interfaz |
| `Espacio` | Pausar / reanudar |
| `Tab` | Mostrar u ocultar el panel |
| `←` `→` | Efecto anterior / siguiente |
| `A` | Modo AUTO |
| `M` | Medidores en pantalla (modo inmersivo) |
| `W` | Cubo/tetraedro: alambre o sombreado |
| `C` | Monocromo |
| `P` | Siguiente paleta |

Panel: efecto (o **AUTO**), duración de escena, cambio de efecto aleatorio (intervalos aleatorios
entre 20 y 100 s), paleta, cambio automático de colores (cada 8 s), monocromo, dispositivo,
intensidad de reacción, sensibilidad, velocidad, brillo, densidad de caracteres (tamaño de celda),
medidores y botones de audio/pausa. Cada uno de los cinco controles numéricos tiene un botón
**AZAR** que cambia su valor aleatoriamente cada 1–2.5 s mientras está activo y restaura el valor
previo al desactivarlo. También se puede alternar aleatoriamente entre alambre y sombreado cada
1–2.5 s; al desactivarlo se restaura el estilo anterior. La aleatorización se pausa al pausar la
animación. El panel permite cambiar el idioma (español o inglés), elegir entre once temas de
interfaz y trece paletas de color, y escribir un nombre de DJ para mostrarlo como arte ASCII
animado con lluvia de caracteres Matrix en el efecto **Visual DJ ASCII**. Los ajustes se guardan en
`%APPDATA%\ASCII-Vibes-Visualizer\settings.json`; la configuración existente se migra al iniciar.

## Qué controla cada banda

* **Graves**: pulsos, expansión, deformación grande, amplitud de las ondas, velocidad del túnel.
* **Medios**: giro, ondulaciones, remolinos, estructura del flujo.
* **Agudos**: destellos, chispas, detalle fino, estelas.
* **Volumen**: brillo y energía global.
* **Picos**: explosiones de partículas, anillos en las ondas, onda expansiva en humo/vórtice,
  «golpe» elástico en las figuras 3D y cambios de escena en AUTO (con transición de disolución).

## Efectos

Ondas líquidas · Humo y plasma · Cráneo 3D · Cerebro 3D · Rostro 3D · Cubo 3D ·
Tetraedro/estrella tetraédrica · Partículas y explosiones · Túnel · Vórtice · Visual DJ ASCII ·
Osciloscopio · Ecualizador circular · Lluvia de meteoros · Portal de ondas · Glitch digital · AUTO.

## Arquitectura

```
run.py                 punto de entrada
asciiviz/
  audio.py             captura WASAPI/loopback, FFT, bandas, picos (hilos propios)
  canvas.py            Canvas (z-buffer, luminancia/tono) + renderizador de glifos pygame
  palettes.py          paletas
  geometry.py          SDF -> nube de puntos con normales (cráneo, cerebro, rostro)
  effects/             un módulo por familia de efectos
  scenes.py            contexto, gestor de escenas, transiciones y modo AUTO
  ui.py                widgets (modo inmediato)
  app.py               ventana, eventos, panel, ajustes
```

Canalización 3D: geometría (vértices + normales) → rotaciones → proyección en perspectiva →
profundidad (z-buffer) e iluminación (difusa, especular, borde, oclusión ambiental) → carácter
según luminancia (` .,-~:;=!*#$@`) → color por paleta → blit de glifos en caché.

## Cráneo, cerebro y rostro

* **Cráneo** (sin mandíbula) y **cerebro** (un solo óvalo con pliegues, cerebelo y tronco) giran
  360° de forma continua.
* **Rostro**: máscara angular «low-poly» de facetas planas, ojos resaltados que parpadean y boca que
  abre y cierra al ritmo de la animación y responde también a los medios. Mira de lado a lado sin girar 360°.
* Alrededor de las tres figuras hay un **HUD ASCII**: hélices de ADN, anillos orbitales, nodos
  flotantes, marco, escalera de datos, barras reactivas y onda de volumen.
* Sombreado «retrato ASCII» con grano tipo halftone y oclusión en huecos.
* Sube «Densidad de caracteres» en el panel para más detalle fino (por defecto 1.35).

## Limitaciones honestas

* Cráneo, cerebro y rostro son **procedurales y estilizados** (campos de distancia con
  primitivas); son reconocibles pero no anatómicamente exactos. El rostro es una cabeza calva
  estilizada. Se generan en segundo plano al arrancar (≈2–3 s; mientras tanto se ve una esfera).
* Probado el motor visual y el análisis de audio en entorno simulado; la captura WASAPI real
  depende de PyAudioWPatch en tu Windows. Si algo falla, el panel muestra el mensaje exacto.
* Con ventanas 4K y densidad alta, sube la «densidad» con cuidado: más celdas = más CPU.

## Crear el ejecutable portable

Con el entorno ya creado (`setup.bat`), ejecuta `build_exe.bat`. El resultado queda en
`dist\ASCII-Vibes-Visualizer\ASCII-Vibes-Visualizer.exe`; copia la carpeta completa. Se puede usar
en otros PCs sin instalar Python. Si no abre, genera la versión con consola:
`build_exe.bat console`.
