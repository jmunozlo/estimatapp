# 🎯 Estimatapp - Scrum Poker

Una aplicación web moderna de Planning Poker para equipos ágiles, construida con Python, FastAPI y WebSockets.

## ✨ Características

- 🎴 **Cartas de Planning Poker**: Escala Fibonacci completa (0, 0.5, 1, 2, 3, 5, 8, 13, 20, 40, 100) más ? y ☕
- 🔄 **Actualizaciones en tiempo real**: Usando WebSockets para sincronización instantánea
- 👥 **Múltiples jugadores**: Soporte para votantes y observadores
- � **Reconexión inteligente**: Los jugadores pueden reconectarse sin crear duplicados
- 👑 **Rol de facilitador**: El creador de la sala tiene permisos especiales
- 🔒 **Modo de votación anónimo/público**: Oculta o muestra quién votó qué
- 📊 **Estadísticas automáticas**: Resumen de votos y cálculo de promedio
- 📜 **Historial de votaciones**: Mantiene registro de todas las historias votadas
- 🎨 **Interfaz moderna**: Diseño responsive y amigable
- 🚀 **100% Python**: Backend completamente en Python con FastAPI

## 🆕 Mejoras Recientes

### Sistema de Reconexión Inteligente
- Detecta cuando un jugador con el mismo nombre se une nuevamente
- Reconecta automáticamente sin crear duplicados
- Mantiene el historial de votos del jugador
- Los jugadores desconectados ya no bloquean la votación

### Escalas de Votación Personalizables ⚖️
- **5 escalas predefinidas**:
  - Fibonacci clásica (1, 2, 3, 5, 8, 13, 21, 34, 55, 89)
  - Fibonacci modificada (0, 0.5, 1, 2, 3, 5, 8, 13, 20, 40, 100) - por defecto
  - Potencias de 2 (1, 2, 4, 8, 16, 32, 64)
  - T-Shirt (XXS, XS, S, M, L, XL, XXL)
  - Lineal (0-10)
- **Escala personalizada**: Crea tu propia escala con los valores que prefieras
- Solo el facilitador puede cambiar la escala
- Promedio se redondea automáticamente al valor más cercano de la escala

### Historial de Votaciones
- Registra automáticamente cada historia votada
- Muestra resumen de votos y promedio redondeado
- Incluye fecha y hora de cada votación
- **Respeta el modo anónimo/público**: Solo muestra votos individuales en modo público
- Disponible en tiempo real para todos los jugadores

### Planificación de Sprint 📊
- **Sumatoria total de story points**: Calcula automáticamente la suma de todas las estimaciones
- Visible en la sección de historial
- Ayuda a determinar la velocidad del equipo
- Útil para planificar cuántos puntos puede abordar el sprint

### Sistema de Roles
- **Facilitador**: El primer jugador que entra a la sala
  - Puede revelar los votos
  - Puede iniciar nuevas rondas
  - Puede cambiar el modo de votación (anónimo/público)
  - Puede cambiar la escala de votación
- **Votantes**: Participan activamente en las votaciones
- **Observadores**: Pueden ver pero no votan

### Modo de Votación Anónimo/Público
- **Modo Público** (predeterminado): Los votos individuales son visibles en el historial
- **Modo Anónimo**: Solo se muestra el resumen y promedio, sin identificar quién votó qué
- Solo el facilitador puede cambiar el modo
- Afecta tanto a las votaciones actuales como al historial

## 🛠️ Requisitos

- Python 3.13+
- uv (gestor de paquetes)
- ruff (linter y formateador)

## 📦 Instalación

1. Clona el repositorio:
```bash
git clone <tu-repo>
cd estimatapp
```

2. Instala las dependencias con uv:
```bash
uv sync
```

## 🚀 Uso

### Ejecutar la aplicación

```bash
python main.py
```

O usando uvicorn directamente:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

La aplicación estará disponible en `http://localhost:8000`

### Desarrollo

El proyecto usa ruff para linting y formateo:

```bash
# Verificar código
ruff check .

# Formatear código
ruff format .

# Arreglar problemas automáticamente
ruff check --fix .
```

## 📁 Estructura del Proyecto

```
estimatapp/
├── app/
│   ├── __init__.py
│   ├── main.py              # Aplicación FastAPI principal
│   ├── manager.py           # Gestor de salas
│   ├── websocket.py         # Gestor de conexiones WebSocket
│   ├── models/
│   │   ├── __init__.py
│   │   └── poker.py         # Modelos de datos (Room, Player, Vote)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── rooms.py         # API REST para gestión de salas
│   │   └── websocket.py     # Endpoints WebSocket
│   ├── static/
│   │   ├── styles.css       # Estilos CSS
│   │   ├── home.js          # JavaScript página principal
│   │   └── room.js          # JavaScript sala de votación
│   └── templates/
│       ├── index.html       # Página principal
│       └── room.html        # Página de sala
├── main.py                  # Punto de entrada
├── pyproject.toml          # Configuración del proyecto
└── README.md
```

## 🎮 Cómo usar

1. **Crear una sala**:
   - Ve a la página principal
   - Ingresa un nombre para la sala
   - Haz clic en "Crear Sala"

2. **Unirse a una sala**:
   - Copia el ID de la sala
   - Compártelo con tu equipo
   - Cada miembro ingresa su nombre y el ID de la sala
   - Opcionalmente pueden unirse como observadores

3. **Votar**:
   - Cada jugador selecciona su estimación
   - Los demás verán quién ha votado pero no el valor
   - Cuando todos hayan votado, se activa el botón "Revelar"

4. **Revelar votos**:
   - Haz clic en "Revelar Votos"
   - Se mostrarán todos los votos y el promedio
   - Discute las diferencias y conversa

5. **Nueva ronda**:
   - Haz clic en "Nueva Ronda"
   - Opcionalmente ingresa el nombre de la nueva historia
   - Los votos se resetean y comienza de nuevo

## 🔧 API Endpoints

### REST API

- `POST /api/rooms` - Crear una nueva sala
- `GET /api/rooms` - Listar salas activas
- `GET /api/rooms/{room_id}` - Obtener información de una sala
- `POST /api/rooms/{room_id}/join` - Unirse a una sala
- `DELETE /api/rooms/{room_id}` - Eliminar una sala

### WebSocket

- `WS /ws/{room_id}/{player_id}` - Conexión WebSocket para actualizaciones en tiempo real

#### Mensajes WebSocket

**Cliente → Servidor:**
```json
{
  "action": "vote",
  "vote": "5"
}

{
  "action": "reveal"
}

{
  "action": "reset",
  "story_name": "Nueva historia"
}
```

**Servidor → Cliente:**
```json
{
  "type": "room_update",
  "data": {
    "room_id": "abc123",
    "status": "voting",
    "players": [...],
    "all_voted": false
  }
}
```

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto es de código abierto y está disponible bajo la licencia MIT.

## 👨‍💻 Autor

Desarrollado con ❤️ para equipos ágiles

---

¿Preguntas o sugerencias? Abre un issue en el repositorio.
