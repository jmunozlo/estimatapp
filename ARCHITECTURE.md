# Arquitectura DDD - EstimatApp

Este documento describe la arquitectura Domain-Driven Design (DDD) implementada en EstimatApp.

## Estructura de Carpetas

```
app/
├── domain/                    # Capa de Dominio (núcleo)
│   ├── aggregates/           # Aggregate Roots
│   │   └── room.py           # Room: el aggregate principal
│   ├── entities/             # Entidades del dominio
│   │   ├── player.py         # Player: jugador en la sala
│   │   ├── story.py          # StoryHistory: historial de historias
│   │   └── enums.py          # RoomStatus, VotingMode
│   ├── value_objects/        # Value Objects inmutables
│   │   ├── identifiers.py    # PlayerId, RoomId, Vote, etc.
│   │   └── voting.py         # VotingScale, VoteSummary
│   ├── repositories/         # Interfaces de repositorio
│   │   └── room_repository.py
│   └── services/             # Servicios de dominio (futuro)
│
├── application/              # Capa de Aplicación
│   ├── use_cases/            # Casos de uso
│   │   ├── room_use_cases.py   # CreateRoom, JoinRoom, etc.
│   │   └── voting_use_cases.py # Vote, Reveal, Reset, etc.
│   └── dto/                  # Data Transfer Objects (futuro)
│
├── infrastructure/           # Capa de Infraestructura
│   ├── repositories/         # Implementaciones de repositorio
│   │   └── in_memory_room_repository.py
│   └── web/                  # WebSocket/HTTP
│       └── connection_manager.py
│
├── routes/                   # Adaptadores HTTP (FastAPI)
│   ├── rooms.py              # Endpoints REST para salas
│   └── websocket.py          # Endpoint WebSocket
│
├── models/                   # Compatibilidad (re-exporta del dominio)
├── manager.py                # Compatibilidad (usa repositorio)
└── websocket.py              # Compatibilidad (usa ConnectionManager)
```

## Capas de la Arquitectura

### 1. Domain Layer (Capa de Dominio)

El núcleo de la aplicación, contiene toda la lógica de negocio.

**Aggregate Root: Room**
- Encapsula toda la lógica de una sala de estimación
- Gestiona jugadores, votos, escalas e historial
- Es la única entrada para modificar el estado del juego

**Entities:**
- `Player`: Representa un jugador con identidad y estado mutable
- `StoryHistory`: Almacena resultados de votaciones completadas

**Value Objects:**
- `VotingScale`: Escala de votación inmutable
- `PlayerId`, `RoomId`, `Vote`: Identificadores tipados

**Repository Interface:**
- `RoomRepository`: Define el contrato para persistencia

### 2. Application Layer (Capa de Aplicación)

Orquesta los casos de uso de la aplicación.

**Use Cases:**
- `CreateRoomUseCase`: Crear una nueva sala
- `JoinRoomUseCase`: Unirse a una sala (con reconexión)
- `VoteUseCase`: Emitir un voto
- `RevealVotesUseCase`: Revelar votos (facilitador)
- `ResetVotesUseCase`: Nueva ronda (facilitador)
- `ChangeScaleUseCase`: Cambiar escala de votación

### 3. Infrastructure Layer (Capa de Infraestructura)

Implementaciones concretas de interfaces del dominio.

**Repositories:**
- `InMemoryRoomRepository`: Almacenamiento en memoria

**Web:**
- `ConnectionManager`: Gestión de conexiones WebSocket

## Principios Aplicados

1. **Separation of Concerns**: Cada capa tiene responsabilidades claras
2. **Dependency Inversion**: El dominio no depende de infraestructura
3. **Single Responsibility**: Cada clase tiene una única razón para cambiar
4. **Rich Domain Model**: La lógica está en las entidades, no en servicios

## Compatibilidad

Para mantener compatibilidad con el código existente:
- `app/models/__init__.py` re-exporta las clases del dominio
- `app/manager.py` delega al repositorio
- `app/websocket.py` re-exporta ConnectionManager

## Tests

Los tests existentes siguen funcionando gracias a:
- Re-exports manteniendo los imports originales
- Fixture `clean_rooms()` que resetea el repositorio singleton

## Futuras Mejoras

1. **Event Sourcing**: Emitir eventos de dominio
2. **CQRS**: Separar comandos y queries
3. **Persistencia**: Implementar `PostgresRoomRepository`
4. **DTOs**: Añadir objetos de transferencia para la API
