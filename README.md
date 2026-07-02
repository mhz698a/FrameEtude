# 🎬 FrameEtude

Una aplicación de escritorio moderna para **navegar, inspeccionar y recortar video** con capacidades avanzadas de OCR, gestión de metadata y análisis de fotogramas.

## ☀️ Características Principales

- **Navegador de fotogramas**: Visualiza y navega por los fotogramas de tus videos de forma fluida
- **Recortador de video**: Extrae segmentos específicos de tus videos con precisión
- **OCR integrado**: Extrae texto de fotogramas usando Tesseract con preprocesamiento adaptativo
- **Gestor de metadatos**: Edita y organiza información de episodios y temporadas
- **Caché de miniaturas**: Sistema optimizado de almacenamiento en caché para rendimiento
- **Visión de letras**: Panel especializado para visualización de subtítulos y letras
- **Soporte SMB**: Acceso a comparticiones de red Windows
- **Gestor de letras**: Aplicación complementaria para gestión de letras de canciones

## ✅ Requisitos

- **Python 3.12 o superior**
- Windows (compatible con Windows Share Manager)
- Librerías Python (ver `requirements.txt`)

### Dependencias Principales

- PyQt6 - Interfaz gráfica moderna
- OpenCV (cv2) - Procesamiento de imágenes y video
- Tesseract OCR - Reconocimiento óptico de caracteres
- Pillow - Manipulación de imágenes
- PyFFmpeg - Procesamiento de video

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/mhz698a/FrameEtude.git
cd FrameEtude
```

### 2. Crear entorno virtual

```bash
python3.12 -m venv venv
venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Instalar Tesseract (opcional, para OCR)

Descarga el instalador desde [GitHub - UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki) e instálalo en tu sistema.

## 📖 Uso

### Ejecutar la aplicación principal

```bash
python frame_etude.pyw
```

### Ejecutar el gestor de letras

```bash
python lirycs_mgr.pyw
```

### Ejecutar herramientas auxiliares

```bash
# Obtener lista de episodios
python temp_eps_list_get.pyw

# Sobreescribir rango de fechas
python temp_ov_dtrng.pyw
```

## ⚙️ Configuración

La aplicación utiliza archivos de configuración TOML ubicados en:
- **Windows**: `%APPDATA%\FrameEtude\settings.toml`

### Parámetros de OCR disponibles

```toml
[ocr]
OCR_SCALE = 2              # Escalado de imagen (factor de aumento)
OCR_USE_CLAHE = true       # Aplicar contraste adaptativo
OCR_CLAHE_CLIP = 2.0       # Factor de clipping CLAHE
OCR_DENOISE_KSIZE = 3      # Tamaño kernel para denoising (impar)
OCR_DILATE_ITER = 1        # Iteraciones de dilatación
OCR_INVERT = true          # Invertir colores de imagen
OCR_BINARIZE = true        # Aplicar umbralización OTSU
OCR_PSM = 6                # Tesseract Page Segmentation Mode
OCR_LANG = 'spa'           # Idioma (esp, eng, etc.)
```

### Parámetros generales disponibles

```toml
[general]
BASE_INTERNAL_ROOT = "E:\_Internal"
DEFAULT_THUMB_WIDTH = 700
NUM_THUMBS = 5
CACHE_SIZE = 15
```

## 📁 Estructura del Proyecto

```
FrameEtude/
├── frame_etude.pyw               # Punto de entrada principal
├── lirycs_mgr.pyw                # Gestor de letras de canciones
├── video_main.py                 # Lógica principal de video
├── file_table_widget.py           # Widget tabla de archivos
├── config.py                      # Gestión de configuración
├── ocr_lib.py                     # Funciones OCR
├── cut_lib.py                     # Biblioteca de recorte de video
├── cut_dialog_ex.py              # Diálogo extendido de recorte
├── smb_dialog.py                 # Diálogo de acceso SMB
├── windows_share_manager.py      # Gestor de comparticiones Windows
├── metadata_edit_lib.py           # Edición de metadatos
├── lyric_vision_panel.py          # Panel de visualización de letras
├── settings_dialog.py             # Diálogo de configuración
├── vidwk_lib.py                   # Utilidades de trabajo con video
├── duration_async_lib.py          # Cálculo asincrónico de duraciones
├── utils.py                       # Funciones utilitarias
└── assets/                        # Iconos y recursos gráficos
```

## 🎯 Formatos soportados

- **Video**: MP4, AVI, MOV, MKV, WMV, FLV
- **Configuración**: TOML

## 🔧 Herramientas Disponibles

### Funcionalidades Principales

| Herramienta | Descripción |
|-------------|-------------|
| **Frame Navigator** | Navega fotograma a fotograma en videos |
| **Video Clipper** | Recorta segmentos específicos |
| **OCR Engine** | Extrae texto de fotogramas con preprocesamiento |
| **Metadata Manager** | Gestiona información de episodios |
| **Lyric Manager** | Aplicación separada para gestionar letras |
| **SMB Manager** | Accede a comparticiones de red |

## 📝 Notas Importantes

- El proyecto está optimizado para Windows (usa Windows Shell API)
- Requiere Python 3.12+ para funcionalidades modernas (como `tomllib`)
- La interfaz utiliza PyQt6 con tema oscuro personalizado
- El procesamiento de video es asincrónico para mejor experiencia de usuario

## 🐛 Solución de Problemas

### OCR no funciona
- Verifica que Tesseract esté instalado correctamente
- Actualiza la ruta de instalación en las variables de entorno

### Problemas con SMB
- Asegúrate de tener permisos en las comparticiones de red
- Verifica la conectividad Windows a la red

### Caché lleno
- Aumenta `CACHE_SIZE` en configuración si necesitas más capacidad
- Limpia manualmente la carpeta de caché en `%APPDATA%\FrameEtude`

## 👨‍💻 Autor

**mhz698a** - [Perfil GitHub](https://github.com/mhz698a)

## 📄 Licencia

Este proyecto no tiene licencia especificada. Ver detalles en el repositorio.

---

**Última actualización**: Julio 2026  
**Estado**: En desarrollo activo
**Tipo de proyecto**: Prototipo
**NOTA CRITICA**: Este es un proyecto personal de automatización diseñado específicamente para ejecutarse en entornos locales parametrizados.


