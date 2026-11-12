# SPA de inventario de Nextep Bookstore

Aplicación React con TypeScript, Vite, CSS Modules, TanStack Query, Axios e iconos
Lucide. Las fuentes Inter y JetBrains Mono se sirven localmente. La implementación
sigue la especificación visual proporcionada y consume la API de Django.

## Ejecución

Desde la raíz del repositorio, preparar `.env` siguiendo el
[README principal](../README.md) y ejecutar:

```powershell
docker compose up --build
```

Abrir http://localhost:5173. El mismo comando inicia Django y PostgreSQL y aplica
las migraciones pendientes. Para cargar datos de demostración opcionales:

```powershell
docker compose exec backend python manage.py seed_demo_books
```

Para desarrollar el frontend fuera de Docker, mantener el backend en ejecución
y usar Node.js 24. Desde `frontend/`:

```powershell
npm ci
npm run dev
```

La configuración opcional se documenta en `.env.example`. `VITE_API_URL=/api`
utiliza el proxy de Vite hacia `API_PROXY_TARGET`: `http://127.0.0.1:8000` por
defecto y `http://backend:8000` dentro de Compose. El proxy elimina el prefijo
`/api` antes de enviar las peticiones a las rutas de Django sin barra final.

Un despliegue estático de producción debe proporcionar un proxy equivalente o
compilar con una URL explícita de la API y configurar CORS y los hosts permitidos
en Django. Solo las variables con prefijo `VITE_` se exponen al navegador; no
deben contener secretos. Compose activa el sondeo de archivos para detectar
cambios de forma fiable en Windows con Docker.

## Funcionalidades

- Indicadores globales de inventario; búsqueda por título, autor o ISBN con
  espera de 300 ms; filtros combinados de categoría y existencias bajas;
  orden por ID y paginación del servidor con tamaños de 10, 25 o 50.
- Tabla y tarjetas adaptables, copia de ISBN, detalle de libro, creación,
  edición y eliminación con confirmación. El tema, la moneda y la vista
  preferida se conservan en el almacenamiento del navegador.
- Validación de ISBN-10 e ISBN-13 con comprobación del dígito de control y
  normalización de separadores; título y autor de al menos dos caracteres;
  categoría y país obligatorios; costo USD positivo con hasta dos decimales;
  existencias enteras no negativas. Los errores de ISBN duplicado se muestran
  en el campo correspondiente y se conserva el contenido del formulario.
- Diálogos nativos con gestión del foco, cierre mediante Escape o fondo,
  etiquetas accesibles, notificaciones, errores con reintento, estados de carga
  y vistas para inventario vacío o búsqueda sin resultados.
- El cálculo llama automáticamente a la acción POST al abrir el modal. Muestra
  la tasa utilizada, costo convertido, recargo del 40 %, importe final guardado,
  origen de la tasa y fechas. **Recalculate** solicita otro cálculo; **Done**
  cierra el resultado, que ya está guardado en la base de datos.

El selector EUR/USD/GBP/MXN de la cabecera convierte los precios guardados solo
para visualizarlos mediante `GET /books/exchange-rate`; no cambia su moneda de
almacenamiento. `GET /books/summary` proporciona los indicadores de todo el
inventario y la moneda local configurada, independientemente de los filtros
y de la página del listado.

Los errores HTTP 400 se vinculan a los campos del formulario. Un libro no
encontrado (404) genera una notificación y actualiza el inventario. Los errores
del servidor (500) ofrecen controles de reintento. Un error 503 en el cálculo
explica que no se guardó un precio nuevo. Si el servidor devuelve correctamente
un cálculo con tasa de respaldo, se muestra un aviso ámbar que identifica la
tasa predeterminada o la captura anterior utilizada. Se incluye la atribución
del proveedor en la interfaz y en el modal de cálculo.

## Pruebas y compilación

Desde `frontend/`, con las dependencias instaladas:

```powershell
npm test
npm run build
npm run test:e2e
```

Las pruebas unitarias cubren las validaciones del formulario y la conversión
segura de errores del cliente HTTP. La compilación verifica TypeScript y genera
los archivos estáticos en `dist/`.

La suite de navegador requiere la aplicación en http://localhost:5173 y el
conjunto de 25 libros de demostración en su estado inicial. En Windows utiliza
Microsoft Edge instalado; en otros sistemas ejecutar primero:

```sh
npx playwright install chromium
```

Se puede indicar otra dirección con la variable `E2E_BASE_URL`. Las pruebas crean
y eliminan sus propios libros. Cubren CRUD y persistencia, validaciones, filtros,
paginación, conversión de visualización, diseño móvil, teclado, comprobaciones
automatizadas de accesibilidad, estados de carga/vacío y respuestas simuladas
404, 500, 503 y de respaldo correcto. Los cálculos y conversiones no interceptados
consultan el backend real y pueden depender de la disponibilidad del proveedor;
las pruebas de tasas del backend utilizan respuestas simuladas y son deterministas.

Los informes y capturas se generan en `playwright-report/` y `test-results/`,
directorios excluidos de Git. Las pruebas de navegador de filtros suponen las
categorías y existencias de demostración originales; conviene usar una base de
datos de desarrollo dedicada si se han modificado esos registros.

## Organización del código

- `src/api/apiClient.ts`: contrato HTTP, tiempos de espera y tratamiento de errores.
- `src/hooks/useInventory.ts`: consultas, caché, cancelación y espera de búsqueda.
- `src/lib/validation.ts`: reglas del formulario y dígitos de control del ISBN.
- `src/components/`: cabecera, indicadores, vistas de inventario, modales y avisos.
- `src/index.css` y `src/styles/`: variables de temas claro/oscuro y controles comunes.
- `tests/unit/` y `tests/e2e/`: pruebas unitarias y flujos completos de navegador.
