# Sistema de inventario de librería

Proyecto para la prueba técnica de Nextep Innovation. Incluye una API REST con
Django REST Framework, PostgreSQL 15 y una aplicación web de página única (SPA)
con React, TypeScript, Vite, CSS Modules y TanStack Query.

Permite gestionar libros, consultar existencias y calcular el precio de venta
sugerido con una tasa de cambio externa y un recargo comercial del 40 %.
La interfaz incluye tabla y tarjetas adaptables, búsqueda, filtros, formularios
validados, temas claro/oscuro y un desglose del cálculo de precios.

## Requisitos previos

- Git para clonar el repositorio.
- Docker Desktop con Docker Compose y el motor de Docker en ejecución.
- Puertos `5173` y `8000` disponibles.
- Conexión a Internet para descargar imágenes y dependencias, y consultar las
  tasas de cambio. Si el proveedor de tasas falla, se utiliza el respaldo configurado.

Con Docker no es necesario instalar Python, Node.js ni PostgreSQL en el equipo:
los contenedores usan Python 3.12, Node.js 24 y PostgreSQL 15. Para desarrollar
fuera de Docker se necesita Python 3.11 o superior, Node.js 24 y una instancia
de PostgreSQL accesible.

## Instalación y ejecución

Clonar el [repositorio de GitHub](https://github.com/AleGarofalo/Prueba-Nextep):

```powershell
git clone https://github.com/AleGarofalo/Prueba-Nextep.git
cd Prueba-Nextep
```

Desde la raíz del proyecto, crear `.env` solo si todavía no existe:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

En macOS o Linux, el comando equivalente es:

```sh
test -f .env || cp .env.example .env
```

Editar `.env` y reemplazar los valores de ejemplo de `DB_PASSWORD` y
`DJANGO_SECRET_KEY`. Para Docker, mantener `DB_HOST=db`. El archivo `.env` no se
incluye en Git; `.env.example` documenta las variables necesarias.
Se conservan las variables antiguas `POSTGRES_DB`, `POSTGRES_USER` y
`POSTGRES_PASSWORD`; los valores no vacíos de `DB_NAME`, `DB_USER` y `DB_PASSWORD`
tienen prioridad tanto en Django como en Compose.

Iniciar todo el proyecto:

```powershell
docker compose up --build
```

El backend espera a que PostgreSQL esté listo, aplica las migraciones pendientes
y arranca Django. El frontend instala las dependencias mediante `npm ci` y
arranca Vite; la primera ejecución puede tardar unos minutos.

| Servicio | Dirección |
| --- | --- |
| Aplicación web | http://localhost:5173 |
| API REST | http://localhost:8000/books |
| Raíz alternativa de la API | http://localhost:8000/api/inventory/ |

En ejecuciones posteriores basta con `docker compose up`. Usar `--build` cuando
cambie el Dockerfile o las dependencias del backend. Añadir `-d` permite ejecutar
los servicios en segundo plano. Para consultar los registros:

```powershell
docker compose logs -f backend frontend
```

Detener los servicios conservando la base de datos:

```powershell
docker compose down
```

Los datos se guardan en el volumen `postgres_data`. Las dependencias del frontend
se guardan en `frontend_node_modules`. No es necesario activar perfiles de Compose.
El frontend usa sondeo de archivos para detectar cambios en Windows con Docker.
Esta configuración utiliza servidores de desarrollo y está destinada a ejecución local.

## Datos de demostración

Cargar 25 libros ficticios para probar la aplicación:

```powershell
docker compose exec backend python manage.py seed_demo_books
```

El comando crea los ISBN de demostración que falten y conserva los registros
existentes, incluidas sus modificaciones y precios calculados. No duplica libros
ni consulta el proveedor de tasas. No se ejecuta automáticamente al arrancar.

Hay cinco libros por categoría: `Literatura Clásica`, `Ciencia`, `Tecnología`,
`Historia` y `Ficción`. Cada categoría incluye existencias de 0, 5, 10, 11 y 25
unidades. Los ISBN tienen dígitos de control válidos, pero los títulos, autores,
costos y asociaciones con ISBN son ficticios.

## Uso de la aplicación web

1. Abrir http://localhost:5173 y consultar el catálogo en tabla o tarjetas.
2. Usar la búsqueda por título, autor o ISBN, el filtro de categoría o el filtro
   de existencias bajas. Los resultados se paginan en el servidor.
3. Pulsar **New book**, completar los campos y guardar. La interfaz exige título
   y autor de al menos dos caracteres, categoría, país, ISBN válido, costo positivo
   con hasta dos decimales y existencias enteras no negativas.
4. Abrir el detalle desde el título, editar un libro o eliminarlo con confirmación.
5. Pulsar **Calculate price** para consultar la tasa, ver el desglose y guardar
   el precio sugerido. **Recalculate** repite la operación; **Done** cierra el resultado.

El ISBN no es un número arbitrario: debe tener 10 o 13 caracteres con un dígito
de control correcto, y no puede estar repetido. Por ejemplo, `978-84-376-0494-7`
es válido y se almacena como `9788437604947`. Para pruebas también puede usarse
`9780999002506`, siempre que no exista ya en la base de datos. En libros reales,
utilizar el ISBN impreso junto al código de barras.

El selector EUR/USD/GBP/MXN convierte la visualización de los precios guardados;
no cambia la moneda de almacenamiento. El cálculo siempre utiliza la moneda
local configurada en el backend. La interfaz conserva el tema, la moneda de
visualización y la vista preferida en el almacenamiento del navegador.

## Modelo de datos y validaciones

Ejemplo de datos basado en el PDF:

```json
{
  "title": "El Quijote",
  "author": "Miguel de Cervantes",
  "isbn": "978-84-376-0494-7",
  "cost_usd": "15.99",
  "selling_price_local": null,
  "stock_quantity": 25,
  "category": "Literatura Clásica",
  "supplier_country": "ES"
}
```

- `title` y `author`: obligatorios; no admiten texto compuesto solo por espacios.
- `isbn`: ISBN-10 o ISBN-13 válido y único. Antes de validar el formato, el dígito
  de control y la unicidad, se eliminan espacios y guiones y se convierte `x` en `X`.
- `cost_usd`: estrictamente positivo, con hasta dos decimales.
- `stock_quantity`: entero no negativo; su valor inicial es cero.
- `selling_price_local`: inicialmente `null` y de solo lectura en el CRUD.
  Solo el cálculo de precios lo modifica. Cambiar `cost_usd` mediante la API
  invalida el precio anterior y lo devuelve a `null` hasta recalcularlo.
- `category`: opcional en la API. `supplier_country`: código de dos letras
  mayúsculas o cadena vacía si se desconoce; se normalizan las minúsculas.
  La interfaz exige ambos campos y ofrece países ISO 3166-1 alfa-2.
- `id`, `created_at` y `updated_at`: de solo lectura y generados automáticamente.

Los importes se devuelven como cadenas decimales para conservar la precisión.
Los guardados normales del modelo ejecutan `full_clean()`. La base de datos
también impone costos positivos, existencias y precios no negativos, e ISBN únicos.
Las operaciones masivas del ORM omiten los métodos de validación del modelo,
como ocurre de forma habitual en Django.

La migración `0002_align_exam_book_fields` renombra `price` a `cost_usd` y `stock`
a `stock_quantity`, conservando los valores, identificadores y fechas. Añade
`selling_price_local` y `supplier_country` sin eliminar la migración inicial.

## Endpoints de la API

Las rutas principales del examen no llevan barra final:

| Método | Ruta | Respuesta correcta |
| --- | --- | --- |
| POST | `/books` | 201, libro creado |
| GET | `/books` | 200, lista paginada |
| GET | `/books/{id}` | 200, detalle del libro |
| PUT | `/books/{id}` | 200, libro actualizado |
| PATCH | `/books/{id}` | 200, actualización parcial adicional |
| DELETE | `/books/{id}` | 204, sin contenido |
| GET | `/books/search?category=Ciencia` | 200, resultados por categoría |
| GET | `/books/low-stock?threshold=10` | 200, libros con existencias bajas |
| POST | `/books/{id}/calculate-price` | 200, cálculo guardado y desglosado |
| GET | `/books/summary` | 200, indicadores globales y categorías |
| GET | `/books/exchange-rate?currency=GBP` | 200, conversión de visualización |

También se mantienen los alias `/api/inventory/books/` con barra final,
incluidas las acciones de búsqueda, existencias bajas y cálculo. Ambas familias
utilizan los campos del examen, `cost_usd` y `stock_quantity`.

Los listados devuelven `count`, `next`, `previous` y `results`. La página tiene
20 elementos por defecto; se puede elegir `page_size` hasta un máximo de 100
y cambiar de página con `page=2`. La interfaz ofrece tamaños de 10, 25 y 50.

La categoría se compara completa sin distinguir mayúsculas y minúsculas.
`/books/search` exige una categoría no vacía. El umbral predeterminado de
existencias bajas es 10; incluye ese límite y admite cero. Un umbral inválido
devuelve 400. Los filtros de categoría y existencias pueden combinarse.

El parámetro `search` busca títulos, autores o ISBN normalizados en todo el
inventario. `ordering=id` ordena por ID ascendente y `ordering=-id`, descendente.
Ejemplo de filtros combinados:

```text
GET /books?category=Fiction&low_stock=true&threshold=5&search=book&page_size=10
```

`low_stock` acepta `true`, `false`, `1` o `0`. Los indicadores de `/books/summary`
siempre abarcan todo el inventario, independientemente de los filtros y páginas;
incluyen la moneda local, la valoración `sum(cost_usd * stock_quantity)` y los
recuentos de títulos, existencias bajas y títulos agotados.

`/books/exchange-rate` devuelve un factor de conversión desde `LOCAL_CURRENCY`
hacia la moneda solicitada, su origen y la fecha de consulta. No modifica libros.
La moneda local devuelve factor `1` sin consultar al proveedor; las demás
conversiones utilizan una misma captura de tasas con base USD. Una moneda no
admitida devuelve 400 y una tasa no disponible sin respaldo utilizable devuelve 503.

## Ejemplos de uso de la API

Desde PowerShell, crear, consultar, actualizar, calcular y eliminar un libro:

```powershell
$bookPayload = @{
    title = 'El Quijote'
    author = 'Miguel de Cervantes'
    isbn = '978-84-376-0494-7'
    cost_usd = '15.99'
    stock_quantity = 25
    category = 'Literatura Clásica'
    supplier_country = 'ES'
} | ConvertTo-Json

$createdBook = Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/books' -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($bookPayload))
Invoke-RestMethod -Uri "http://localhost:8000/books/$($createdBook.id)"
Invoke-RestMethod -Method Put -Uri "http://localhost:8000/books/$($createdBook.id)" -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($bookPayload))
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/books/$($createdBook.id)/calculate-price" -ContentType 'application/json' -Body '{}'
Invoke-RestMethod -Uri 'http://localhost:8000/books/low-stock?threshold=10'
Invoke-RestMethod -Method Delete -Uri "http://localhost:8000/books/$($createdBook.id)"
```

Usar un ISBN válido que todavía no exista. Para probar únicamente consultas:

```text
GET /books?page_size=5
GET /books?page=2
GET /books/search?category=Ciencia
GET /books/low-stock?threshold=10
GET /books/low-stock?threshold=0
```

## Cálculo del precio sugerido

La moneda local predeterminada es EUR. La acción admite un cuerpo JSON vacío
o `target_currency` con la misma moneda configurada:

```http
POST /books/1/calculate-price
Content-Type: application/json

{"target_currency": "EUR"}
```

El servicio consulta `https://api.exchangerate-api.com/v4/latest/USD`, toma el
costo USD actual del libro, lo convierte y aplica el recargo del 40 %:

```text
precio sugerido = cost_usd × tasa USD→moneda local × 1.40
```

Se utiliza aritmética decimal sin redondear el costo convertido antes de aplicar
el recargo. Los importes mostrados se redondean a dos decimales con `ROUND_HALF_UP`.
Con la tasa de ejemplo `0.85` del PDF, la respuesta incluye:

```json
{
  "book_id": 1,
  "cost_usd": "15.99",
  "exchange_rate": "0.85",
  "cost_local": "13.59",
  "margin_percentage": 40,
  "selling_price_local": "19.03",
  "currency": "EUR",
  "calculation_timestamp": "2026-11-12T18:00:00+00:00"
}
```

También se devuelven `rate_source`, `rates_fetched_at`, `is_fallback`, `provider`
y `provider_url`. `calculation_timestamp` indica cuándo se calculó el precio;
`rates_fetched_at`, cuándo se consultó la captura de tasas.

El resultado se guarda de forma atómica en `selling_price_local`, actualizando
`updated_at`. La consulta externa ocurre antes de bloquear el registro; el cálculo
utiliza el costo vigente del libro una vez bloqueado. Un GET posterior devuelve
el mismo precio guardado.

Todos los precios persistidos usan `LOCAL_CURRENCY`. Solicitar otra moneda en
el cálculo devuelve 400. Si se cambia esa configuración, también se debe ajustar
su respaldo y recalcular los precios existentes. El país del proveedor del libro
es independiente de la moneda local.

### Fallos del proveedor y tasas de respaldo

Se controlan errores HTTP, tiempos de espera, fallos de conexión, JSON mal formado
y tasas inválidas. El origen utilizado queda identificado en la respuesta:

- `live`: tasas válidas recién consultadas al proveedor.
- `cache`: captura válida con menos de una hora de antigüedad.
- `stale_cache`: durante una caída, captura válida de menos de 24 horas.
- `default`: tasa de respaldo configurada cuando no hay una captura utilizable.
  No se almacena en caché como si fuera una tasa del proveedor.
- `identity`: conversión USD a USD con tasa 1; se aplica igualmente el recargo.

Las fuentes `stale_cache` y `default` devuelven `is_fallback=true`. Las fuentes
`default` e `identity` no tienen fecha de consulta al proveedor. Si ninguna tasa
permite obtener un precio compatible, se devuelve 503 sin guardar un precio nuevo.

El respaldo EUR de **0.85** procede del ejemplo del examen; no es una cotización
actual. La configuración se puede cambiar en `.env`:

| Variable | Valor predeterminado | Uso |
| --- | --- | --- |
| `LOCAL_CURRENCY` | `EUR` | Moneda de los precios de venta guardados |
| `EXCHANGE_RATE_DEFAULT_RATE` | `0.85` para EUR; `1` para USD | Respaldo USD a moneda local |
| `EXCHANGE_RATE_API_URL` | `https://api.exchangerate-api.com/v4/latest/USD` | Proveedor de tasas con base USD |
| `EXCHANGE_RATE_API_TIMEOUT` | `10` | Tiempo de espera de conexión/lectura, en segundos |
| `EXCHANGE_RATE_CACHE_TTL` | `3600` | Vigencia de la caché reciente, en segundos |
| `EXCHANGE_RATE_FALLBACK_TTL` | `86400` | Antigüedad máxima de la captura de respaldo, en segundos |
| `VITE_API_URL` | `/api` | Prefijo del frontend que Vite redirige a Django |

Para otra moneda local debe configurarse expresamente su tasa de respaldo.
Las tasas y tiempos deben ser positivos y finitos; la ventana de respaldo debe
ser al menos igual a la de caché reciente. Una URL vacía utiliza el proveedor
predeterminado. Cambiar variables del contenedor requiere recrearlo, por ejemplo:

```powershell
docker compose up -d --force-recreate backend
```

La caché predeterminada de Django reside en memoria por proceso y se reinicia
con este. La tasa de respaldo sigue disponible después de reiniciar. La API
pública de tasas no necesita clave. La aplicación muestra la atribución del
proveedor: [ExchangeRate-API](https://www.exchangerate-api.com/docs/free).

## Manejo de errores

| HTTP | Situación | Comportamiento de la interfaz |
| --- | --- | --- |
| 400 | Validación, ISBN duplicado o parámetros inválidos | Errores por campo y notificación, conservando el formulario |
| 404 | Libro o página inexistente | Notificación y actualización del inventario |
| 500 | Error inesperado del servidor | Alerta con opción de reintentar |
| 503 | Tasas no disponibles sin respaldo utilizable | Aviso en el cálculo y explicación de que no se guardó un precio nuevo |

Si se utiliza correctamente una tasa de respaldo, el cálculo devuelve 200 y la
interfaz muestra un aviso de su origen. Una respuesta 503 no se presenta como
un cálculo exitoso. También se gestionan errores de conexión y tiempos de espera,
estados de carga, botones en proceso y listados vacíos.

## Colección de Postman

Importar la [colección exportada](bookstore-inventory-api/postman/bookstore-inventory.postman_collection.json).
Configurar sus variables `base_url`, `isbn`, `category` y `currency`; por defecto
apuntan a http://localhost:8000 y EUR. El ISBN debe ser válido y no estar utilizado.

Ejecutar las peticiones en orden. La colección guarda el ID creado, prueba el
CRUD del examen, los filtros, el cálculo y su persistencia; después elimina
únicamente el libro que acaba de crear. Incluye validación, consulta de un ID
inexistente, alias de rutas, indicadores y conversión de visualización.
Sus scripts verifican códigos HTTP y resultados. El ISBN predeterminado está
separado de los usados por los 25 libros de demostración.

## Pruebas y comprobaciones

Con Docker en ejecución, desde la raíz:

```powershell
docker compose config --quiet
docker compose exec backend python manage.py check
docker compose exec backend python manage.py migrate --check
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend python manage.py test inventory --noinput
```

Las pruebas del backend utilizan una base de datos de prueba independiente y
simulan las respuestas del proveedor externo. Cubren modelo, restricciones,
CRUD, contrato del PDF, filtros, paginación, tasas, respaldo, persistencia,
conservación de datos en migraciones, datos de demostración y colección de Postman.

Desde `frontend/`, con las dependencias instaladas:

```powershell
npm ci
npm test
npm run build
npm run test:e2e
```

`npm run build` comprueba TypeScript y genera la compilación. Las pruebas de
navegador requieren la aplicación en http://localhost:5173 y los datos de
demostración en su estado inicial. Crean y eliminan sus propios libros; no borran
los libros existentes. En Windows usan Microsoft Edge instalado; en otros
sistemas se debe ejecutar antes `npx playwright install chromium`.
Véase la [guía del frontend](frontend/README.md) para los detalles de las pruebas.

## Desarrollo sin Docker

Configurar una instancia de PostgreSQL accesible y ajustar `DB_HOST`, `DB_PORT`
y sus credenciales en `.env`. El nombre `db` funciona dentro de Compose; fuera
de él se debe utilizar la dirección real de PostgreSQL. El servicio de base de
datos de Compose no publica un puerto hacia el equipo anfitrión por defecto.

Ejemplo para el backend en PowerShell, desde la raíz:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r bookstore-inventory-api/requirements.txt
.\.venv\Scripts\python.exe bookstore-inventory-api/manage.py migrate
.\.venv\Scripts\python.exe bookstore-inventory-api/manage.py runserver
```

Los comandos locales de Django cargan el `.env` de la raíz. `DEBUG` y
`ALLOWED_HOSTS` se leen del entorno; se conservan las alternativas antiguas con
prefijo `DJANGO_`. CORS admite los orígenes locales de Vite de forma predeterminada.
Para iniciar el frontend localmente, seguir la [guía correspondiente](frontend/README.md).

## Estructura del proyecto

- `bookstore-inventory-api/config/`: configuración de Django y rutas raíz.
- `bookstore-inventory-api/inventory/models.py`: persistencia y validación del modelo.
- `bookstore-inventory-api/inventory/serializers.py`: validación de peticiones y respuestas.
- `bookstore-inventory-api/inventory/views.py` y `urls.py`: controladores y rutas.
- `bookstore-inventory-api/inventory/services.py`: tasas externas y cálculo de precios.
- `bookstore-inventory-api/inventory/validators.py`: validación y normalización de ISBN.
- `bookstore-inventory-api/inventory/tests/`: pruebas automatizadas del backend.
- `bookstore-inventory-api/postman/`: colección exportada para probar la API.
- `frontend/src/`: SPA, componentes, cliente HTTP, estado y estilos.
- `frontend/tests/`: pruebas unitarias y flujos de navegador.
- `docker-compose.yml`: ejecución conjunta de los tres servicios.

## Cobertura de la prueba técnica

Revisión realizada contra las cinco páginas de «Nextep - Prueba Técnica -
Desarrollador Full stack.pdf». La especificación visual adicional se utiliza
para el diseño de la SPA; no sustituye los requisitos del examen.

| Requisito del examen | Implementación o evidencia |
| --- | --- |
| Carpeta `bookstore-inventory-api`, framework e historial inicial | Backend Django y commits existentes en Git |
| Modelo `Book` con todos los campos del ejemplo | `inventory/models.py` y migraciones |
| POST, GET de lista/detalle, PUT y DELETE | `inventory/views.py`, rutas `/books` y pruebas del contrato |
| Búsqueda por categoría y existencias bajas, opcionales | `/books/search` y `/books/low-stock` |
| Integración externa y recargo del 40 % | `inventory/services.py`, `/books/{id}/calculate-price` |
| Guardar `selling_price_local` y devolver el desglose | Guardado atómico y pruebas de persistencia |
| Costo positivo, existencias no negativas e ISBN válido y único | Modelo, serializador, restricciones y formulario |
| Tasa por defecto cuando falla el proveedor | Respaldo configurable y pruebas de errores del proveedor |
| Manejo de 400, 404, 500 y 503 | API, cliente HTTP, formularios, avisos y reintentos |
| SPA con catálogo y paginación del backend | Tabla/tarjetas, controles de página y tamaño |
| Filtros de categoría y existencias bajas | Barra de filtros y llamadas a las acciones de la API |
| Formularios POST/PUT y eliminación con confirmación | Modales de creación, edición y eliminación |
| Acción explícita de cálculo y desglose del servidor | Modal de precios con costo, tasa, recargo y precio final |
| Indicadores de carga y notificaciones | Estados de carga, botones en proceso, notificaciones y alertas |
| README con requisitos, instalación y ejemplos | Este documento y la guía del frontend |
| Colección de Postman exportada | Archivo JSON en `bookstore-inventory-api/postman/` |
| Repositorio con código completo | [Repositorio de GitHub](https://github.com/AleGarofalo/Prueba-Nextep) |
| Dockerización, adicional valorado | Dockerfile del backend y Compose para los tres servicios |
