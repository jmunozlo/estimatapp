// Página principal - home.js

// Sistema de notificaciones personalizado
function showNotification(message, type = 'info', showCancel = false) {
    return new Promise((resolve) => {
        const modal = document.getElementById('notificationModal');
        const messageEl = document.getElementById('notificationMessage');
        const iconEl = document.getElementById('notificationIcon');
        const okBtn = document.getElementById('notificationOk');
        const cancelBtn = document.getElementById('notificationCancel');
        
        // Configurar icono según tipo
        const icons = {
            'error': '❌',
            'warning': '⚠️',
            'success': '✅',
            'info': 'ℹ️',
            'question': '❓'
        };
        
        iconEl.textContent = icons[type] || icons.info;
        messageEl.textContent = message;
        
        // Mostrar/ocultar botón cancelar
        cancelBtn.style.display = showCancel ? 'inline-block' : 'none';
        okBtn.textContent = showCancel ? 'Aceptar' : 'Entendido';
        
        modal.style.display = 'flex';
        
        // Limpiar listeners previos
        const newOkBtn = okBtn.cloneNode(true);
        const newCancelBtn = cancelBtn.cloneNode(true);
        okBtn.parentNode.replaceChild(newOkBtn, okBtn);
        cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);
        
        newOkBtn.addEventListener('click', () => {
            modal.style.display = 'none';
            resolve(true);
        });
        
        newCancelBtn.addEventListener('click', () => {
            modal.style.display = 'none';
            resolve(false);
        });
        
        // Cerrar con Escape
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                modal.style.display = 'none';
                resolve(showCancel ? false : true);
                document.removeEventListener('keydown', handleEscape);
            }
        };
        document.addEventListener('keydown', handleEscape);
        
        newOkBtn.focus();
    });
}

document.addEventListener('DOMContentLoaded', () => {
    loadActiveRooms();
    setupCreateRoomForm();
    setupJoinRoomForm();
});

async function loadActiveRooms() {
    try {
        const response = await fetch('/api/rooms');
        const rooms = await response.json();

        if (rooms.length > 0) {
            const activeRoomsSection = document.getElementById('activeRooms');
            const roomsList = document.getElementById('roomsList');

            activeRoomsSection.style.display = 'block';
            roomsList.innerHTML = rooms.map(room => `
                <div class="room-item" id="room-${room.id}">
                    <div class="room-item-info">
                        <h4>${escapeHtml(room.name)}</h4>
                        <div class="room-item-meta">
                            ID: ${room.id} | 
                            ${room.player_count} jugador${room.player_count !== 1 ? 'es' : ''} |
                            Estado: ${room.status === 'voting' ? 'Votando' : 'Revelado'}
                        </div>
                    </div>
                    <div class="room-item-actions">
                        <button 
                            class="btn btn-primary" 
                            onclick="joinRoomDirect('${room.id}')"
                        >
                            Unirse
                        </button>
                        <button 
                            class="btn btn-danger btn-icon-only" 
                            onclick="deleteRoom('${room.id}', '${escapeHtml(room.name)}')"
                            title="Eliminar sala"
                        >
                            🗑️
                        </button>
                    </div>
                </div>
            `).join('');
        } else {
            document.getElementById('activeRooms').style.display = 'none';
        }
    } catch (error) {
        console.error('Error al cargar salas:', error);
    }
}

function setupCreateRoomForm() {
    const form = document.getElementById('createRoomForm');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const roomName = document.getElementById('roomName').value.trim();

        if (!roomName) return;

        try {
            const response = await fetch('/api/rooms', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: roomName })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Error al crear la sala' }));
                throw new Error(errorData.detail || 'Error al crear la sala');
            }

            const room = await response.json();
            
            // Redirigir a la página de unirse con el ID de la sala
            document.getElementById('roomId').value = room.id;
            document.getElementById('playerName').focus();
            
            // Scroll a la sección de unirse
            document.getElementById('joinRoomForm').scrollIntoView({ behavior: 'smooth' });
        } catch (error) {
            console.error('Error al crear sala:', error);
            showNotification('Error al crear la sala. Por favor, intenta de nuevo.', 'error');
        }
    });
}

function setupJoinRoomForm() {
    const form = document.getElementById('joinRoomForm');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const roomId = document.getElementById('roomId').value.trim();
        const playerName = document.getElementById('playerName').value.trim();
        const isObserver = document.getElementById('isObserver').checked;

        if (!roomId || !playerName) return;

        try {
            const response = await fetch(`/api/rooms/${roomId}/join`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    player_name: playerName,
                    is_observer: isObserver
                })
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Error al unirse a la sala' }));
                throw new Error(errorData.detail || 'Error al unirse a la sala');
            }
            if (!response.ok) {
                throw new Error('Sala no encontrada');
            }

            const data = await response.json();
            
            // Guardar información del jugador en localStorage
            localStorage.setItem('playerId', data.player_id);
            localStorage.setItem('playerName', data.player_name);
            
            // Redirigir a la sala
            window.location.href = `/room/${roomId}`;
        } catch (error) {
            console.error('Error al unirse a la sala:', error);
            showNotification('Error al unirse a la sala. Verifica el ID de la sala.', 'error');
        }
    });
}



function joinRoomDirect(roomId) {
    const modal = document.getElementById('joinDirectModal');
    const nameInput = document.getElementById('joinDirectName');
    const okBtn = document.getElementById('joinDirectOk');
    const cancelBtn = document.getElementById('joinDirectCancel');

    nameInput.value = '';
    modal.style.display = 'flex';
    nameInput.focus();

    function cleanup() {
        modal.style.display = 'none';
        okBtn.removeEventListener('click', onOk);
        cancelBtn.removeEventListener('click', onCancel);
        nameInput.removeEventListener('keydown', onEnter);
    }

    async function onOk() {
        const playerName = nameInput.value.trim();
        if (!playerName) {
            nameInput.focus();
            return;
        }
        try {
            const response = await fetch(`/api/rooms/${roomId}/join`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ player_name: playerName, is_observer: false })
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Error al unirse a la sala' }));
                throw new Error(errorData.detail || 'Error al unirse a la sala');
            }
            const data = await response.json();
            localStorage.setItem('playerId', data.player_id);
            localStorage.setItem('playerName', data.player_name);
            cleanup();
            window.location.href = `/room/${roomId}`;
        } catch (error) {
            console.error('Error al unirse a la sala:', error);
            cleanup();
            showNotification('Error al unirse a la sala. Verifica el ID de la sala.', 'error');
        }
    }
    function onCancel() {
        cleanup();
    }
    function onEnter(e) {
        if (e.key === 'Enter') {
            onOk();
        }
    }
    okBtn.addEventListener('click', onOk);
    cancelBtn.addEventListener('click', onCancel);
    nameInput.addEventListener('keydown', onEnter);
}

async function deleteRoom(roomId, roomName) {
    const confirmed = await showNotification(
        `¿Estás seguro de eliminar la sala "${roomName}"? Esta acción no se puede deshacer.`,
        'warning',
        true
    );
    
    if (!confirmed) return;
    
    try {
        const response = await fetch(`/api/rooms/${roomId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            // Remover el elemento de la lista con animación
            const roomElement = document.getElementById(`room-${roomId}`);
            if (roomElement) {
                roomElement.style.transition = 'all 0.3s ease';
                roomElement.style.opacity = '0';
                roomElement.style.transform = 'translateX(-20px)';
                setTimeout(() => {
                    roomElement.remove();
                    // Si no quedan salas, ocultar la sección
                    const roomsList = document.getElementById('roomsList');
                    if (roomsList && roomsList.children.length === 0) {
                        document.getElementById('activeRooms').style.display = 'none';
                    }
                }, 300);
            }
            showNotification('Sala eliminada correctamente', 'success');
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Error al eliminar la sala', 'error');
        }
    } catch (error) {
        console.error('Error al eliminar sala:', error);
        showNotification('Error al eliminar la sala', 'error');
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
