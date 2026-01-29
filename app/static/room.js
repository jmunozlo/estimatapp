// Página de sala - room.js

// Sistema de notificaciones personalizado
function showNotification(message, type = 'info', showCancel = false) {
    return new Promise((resolve) => {
        const modal = document.getElementById('notificationModal');
        const messageEl = document.getElementById('notificationMessage');
        const iconEl = document.getElementById('notificationIcon');
        const okBtn = document.getElementById('notificationOk');
        const cancelBtn = document.getElementById('notificationCancel');
        
        const icons = {
            'error': '❌',
            'warning': '⚠️',
            'success': '✅',
            'info': 'ℹ️',
            'question': '❓'
        };
        
        iconEl.textContent = icons[type] || icons.info;
        messageEl.textContent = message;
        
        cancelBtn.style.display = showCancel ? 'inline-block' : 'none';
        okBtn.textContent = showCancel ? 'Aceptar' : 'Entendido';
        
        modal.style.display = 'flex';
        
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

let ws = null;
let playerId = localStorage.getItem('playerId');
let playerName = localStorage.getItem('playerName');
let currentVote = null;
let roomState = null;
let isObserver = false;
let isFacilitator = false;
let currentScale = [];

document.addEventListener('DOMContentLoaded', () => {
    if (!playerId || !playerName) {
        showNotification('Debes unirte a la sala primero', 'warning').then(() => {
            window.location.href = '/';
        });
        return;
    }

    // Verificar que la sala existe antes de conectar
    verifyRoomAndConnect();
});

async function verifyRoomAndConnect() {
    try {
        const response = await fetch(`/api/rooms/${ROOM_ID}`);
        if (!response.ok) {
            // La sala no existe, limpiar datos y redirigir
            localStorage.removeItem('playerId');
            localStorage.removeItem('playerName');
            showNotification('La sala ya no existe o ha sido eliminada', 'warning').then(() => {
                window.location.href = '/';
            });
            return;
        }
        // La sala existe, conectar al WebSocket
        connectWebSocket();
    } catch (error) {
        console.error('Error verificando sala:', error);
        showNotification('Error al conectar con el servidor', 'error').then(() => {
            window.location.href = '/';
        });
    }
}

function setupVotingCards() {
    const votingCards = document.getElementById('votingCards');
    
    if (!currentScale || currentScale.length === 0) {
        votingCards.innerHTML = '<p class="empty-state">🎴 Esperando escala de votación...</p>';
        return;
    }
    
    votingCards.innerHTML = currentScale.map(value => `
        <div class="poker-card" onclick="castVote('${value}')" data-value="${value}">
            ${value}
        </div>
    `).join('');
}

let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 3;

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${ROOM_ID}/${playerId}`;
    
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('Conectado al WebSocket');
        reconnectAttempts = 0; // Resetear contador al conectar
        updateConnectionStatus(true);
    };

    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
    };

    ws.onerror = (error) => {
        console.error('Error de WebSocket:', error);
        updateConnectionStatus(false);
    };

    ws.onclose = (event) => {
        console.log('Desconectado del WebSocket, código:', event.code);
        updateConnectionStatus(false);
        
        // Si fue rechazado (403), la sala no existe o el jugador no está registrado
        if (event.code === 1006 || event.code === 403) {
            reconnectAttempts++;
            if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
                localStorage.removeItem('playerId');
                localStorage.removeItem('playerName');
                showNotification('La sala ya no existe o tu sesión ha expirado', 'warning').then(() => {
                    window.location.href = '/';
                });
                return;
            }
        }
        
        // Intentar reconectar después de 3 segundos
        setTimeout(() => {
            if (ws.readyState === WebSocket.CLOSED && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                console.log(`Reintentando conexión (${reconnectAttempts + 1}/${MAX_RECONNECT_ATTEMPTS})...`);
                connectWebSocket();
            }
        }, 3000);
    };
}

function handleWebSocketMessage(message) {
    if (message.type === 'room_update') {
        roomState = message.data;
        updateRoomUI();
    } else if (message.type === 'error') {
        console.error('Error del servidor:', message.message);
        showNotification(message.message, 'error');
    }
}

function updateRoomUI() {
    if (!roomState) return;

    // Actualizar nombre de la sala
    document.getElementById('roomName').textContent = roomState.room_name;
    document.getElementById('roomIdDisplay').textContent = roomState.room_id;

    // Actualizar historia actual
    const currentStory = document.getElementById('currentStory');
    currentStory.textContent = roomState.story_name || 'Esperando historia...';
    
    // Actualizar el campo de entrada de historia
    const storyNameInput = document.getElementById('storyName');
    if (storyNameInput) {
        storyNameInput.value = roomState.story_name || '';
    }

    // Actualizar escala de votación
    if (roomState.current_scale) {
        currentScale = roomState.current_scale;
        setupVotingCards();
    }

    // Actualizar selector de escala
    if (isFacilitator && roomState.voting_scale) {
        document.getElementById('scaleSelect').value = roomState.voting_scale;
    }

    // Actualizar modo de votación
    updateVotingModeUI();

    // Actualizar lista de jugadores
    updatePlayersList();

    // Actualizar estado de votación
    updateVotingState();

    // Actualizar controles del facilitador
    updateFacilitatorControls();

    // Actualizar resultados si están revelados
    if (roomState.status === 'revealed') {
        showResults();
    } else {
        hideResults();
    }

    // Actualizar historial
    updateHistory();

    // Actualizar total de story points
    updateTotalPoints();

    // Actualizar botón de revelar
    const revealBtn = document.getElementById('revealBtn');
    if (isFacilitator) {
        revealBtn.style.display = 'inline-block';
        revealBtn.disabled = !roomState.all_voted || roomState.status === 'revealed';
    } else {
        revealBtn.style.display = 'none';
    }

    // Actualizar botón de resetear
    const resetBtn = document.getElementById('resetBtn');
    if (isFacilitator) {
        resetBtn.style.display = 'inline-block';
    } else {
        resetBtn.style.display = 'none';
    }

    // Actualizar campo y botón de establecer historia
    // storyNameInput ya fue declarado arriba, reutilizamos la referencia
    const setStoryBtn = document.querySelector('.story-input-group .btn-primary');
    if (roomState.status === 'revealed') {
        if (storyNameInput) storyNameInput.disabled = true;
        if (setStoryBtn) {
            setStoryBtn.disabled = true;
            setStoryBtn.title = 'Presiona "Nueva Ronda" para establecer una nueva historia';
        }
    } else {
        if (storyNameInput) storyNameInput.disabled = false;
        if (setStoryBtn) {
            setStoryBtn.disabled = false;
            setStoryBtn.title = '';
        }
    }
}

function updateVotingModeUI() {
    const votingModeBtn = document.getElementById('votingModeBtn');
    const votingModeIcon = document.getElementById('votingModeIcon');
    const votingModeText = document.getElementById('votingModeText');

    if (roomState.voting_mode === 'anonymous') {
        votingModeIcon.textContent = '🔒';
        votingModeText.textContent = 'Anónimo';
        votingModeBtn.title = 'Modo anónimo: Los votos individuales están ocultos';
    } else {
        votingModeIcon.textContent = '👁️';
        votingModeText.textContent = 'Público';
        votingModeBtn.title = 'Modo público: Los votos individuales son visibles';
    }
}

function updateFacilitatorControls() {
    const facilitatorControls = document.getElementById('facilitatorControls');
    if (isFacilitator) {
        facilitatorControls.style.display = 'flex';
    } else {
        facilitatorControls.style.display = 'none';
    }
}

function updatePlayersList() {
    const playersList = document.getElementById('playersList');
    
    if (!roomState.players || roomState.players.length === 0) {
        playersList.innerHTML = '<p class="empty-state">👥 Esperando jugadores...</p>';
        return;
    }
    
    playersList.innerHTML = roomState.players.map(player => {
        const isCurrentPlayer = player.id === playerId;
        const classes = ['player-card'];
        
        if (player.has_voted) classes.push('voted');
        if (player.is_observer) classes.push('observer');
        if (!player.connected) classes.push('disconnected');

        let voteDisplay = '';
        if (roomState.status === 'revealed' && player.vote) {
            // En modo anónimo, mostrar icono de incógnito en lugar del voto
            if (roomState.voting_mode === 'anonymous') {
                voteDisplay = `<div class="player-vote anonymous-vote" title="Voto anónimo">🕵️</div>`;
            } else {
                voteDisplay = `<div class="player-vote">${player.vote}</div>`;
            }
        } else if (player.has_voted) {
            voteDisplay = `<div class="player-status">✓</div>`;
        } else if (!player.is_observer) {
            voteDisplay = `<div class="player-status">⏳</div>`;
        }

        const badges = [];
        if (player.is_observer) {
            badges.push('<span class="player-badge badge-observer">OBSERVADOR</span>');
        }
        if (player.is_facilitator) {
            badges.push('<span class="player-badge badge-facilitator">FACILITADOR</span>');
        }

        const currentPlayerIndicator = isCurrentPlayer ? ' (Tú)' : '';

        return `
            <div class="${classes.join(' ')}">
                <div class="player-name">${escapeHtml(player.name)}${currentPlayerIndicator}</div>
                ${voteDisplay}
                ${badges.join(' ')}
            </div>
        `;
    }).join('');

    // Verificar si el jugador actual es observador o facilitador
    const currentPlayer = roomState.players.find(p => p.id === playerId);
    isObserver = currentPlayer?.is_observer || false;
    isFacilitator = currentPlayer?.is_facilitator || false;
}

function updateVotingState() {
    const cards = document.querySelectorAll('.poker-card');
    const isVoting = roomState.status === 'voting';

    cards.forEach(card => {
        const value = card.dataset.value;
        
        // Remover clases previas
        card.classList.remove('selected', 'disabled');

        if (isObserver) {
            card.classList.add('disabled');
        } else if (!isVoting) {
            card.classList.add('disabled');
        } else if (currentVote === value) {
            card.classList.add('selected');
        }
    });
}

function castVote(value) {
    if (isObserver || roomState.status !== 'voting') return;

    // Si hace clic en la misma carta, deseleccionar
    if (currentVote === value) {
        currentVote = null;
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                action: 'vote',
                vote: null
            }));
        }
    } else {
        // Seleccionar nueva carta
        currentVote = value;
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                action: 'vote',
                vote: value
            }));
        }
    }
}

function revealVotes() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            action: 'reveal'
        }));
    }
}

function resetVotes() {
    currentVote = null;

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            action: 'reset'
        }));
    }
}

function setStory() {
    const storyName = document.getElementById('storyName').value.trim();
    
    if (!storyName) return;
    
    // No permitir establecer historia si los votos están revelados
    if (roomState && roomState.status === 'revealed') {
        showNotification('Presiona "Nueva Ronda" antes de establecer una nueva historia', 'warning');
        return;
    }

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            action: 'set_story',
            story_name: storyName
        }));
    }
}

function showResults() {
    const resultsSection = document.getElementById('resultsSection');
    resultsSection.style.display = 'block';

    // Mostrar resumen de votos
    const voteSummary = document.getElementById('voteSummary');
    voteSummary.innerHTML = Object.entries(roomState.vote_summary || {})
        .sort((a, b) => {
            // Ordenar numéricamente cuando sea posible
            const aNum = parseFloat(a[0]);
            const bNum = parseFloat(b[0]);
            if (!isNaN(aNum) && !isNaN(bNum)) {
                return aNum - bNum;
            }
            return 0;
        })
        .map(([value, count]) => `
            <div class="vote-item">
                <div class="vote-value">${value}</div>
                <div class="vote-count">${count} voto${count !== 1 ? 's' : ''}</div>
            </div>
        `).join('');

    // Mostrar promedio
    const voteAverage = document.getElementById('voteAverage');
    if (roomState.average !== null && roomState.average !== undefined) {
        const roundedText = roomState.rounded_average 
            ? ` ≈ <strong>${roomState.rounded_average}</strong> SP` 
            : '';
        voteAverage.innerHTML = `
            <strong>Promedio:</strong> ${roomState.average.toFixed(2)} ${roundedText}
        `;
        voteAverage.style.display = 'block';
    } else {
        voteAverage.innerHTML = 'Sin votos numéricos para calcular promedio';
        voteAverage.style.display = 'block';
    }
}

let showIndividualVotes = false;

function toggleShowVotes() {
    showIndividualVotes = document.getElementById('showVotesCheckbox').checked;
    updateHistory();
}

function updateHistory() {
    const historyList = document.getElementById('historyList');
    const showVotesToggle = document.getElementById('showVotesToggle');
    
    if (!roomState.history || roomState.history.length === 0) {
        historyList.innerHTML = '<p class="empty-state">📊 No hay votaciones en el historial</p>';
        showVotesToggle.style.display = 'none';
        return;
    }

    // Mostrar toggle solo en modo público
    if (roomState.voting_mode === 'public') {
        showVotesToggle.style.display = 'flex';
    } else {
        showVotesToggle.style.display = 'none';
    }

    historyList.innerHTML = roomState.history
        .slice()
        .reverse() // Mostrar más reciente primero
        .map((item, index) => {
            const date = new Date(item.voted_at);
            const formattedDate = date.toLocaleString('es-ES', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });

            // Votos individuales (solo si está activado el toggle y en modo público)
            let votesHtml = '';
            if (roomState.voting_mode === 'public' && item.votes && showIndividualVotes) {
                const votesList = Object.entries(item.votes)
                    .map(([name, vote]) => `
                        <div class="history-vote-item">
                            <strong>${escapeHtml(name)}:</strong> ${vote}
                        </div>
                    `).join('');
                votesHtml = `
                    <div class="history-votes">
                        ${votesList}
                    </div>
                `;
            }

            // Resumen de votos
            const summaryHtml = Object.entries(item.vote_summary || {})
                .map(([value, count]) => `${value} (${count})`)
                .join(', ');

            // Mostrar promedio redondeado si existe
            const avgText = item.rounded_average 
                ? `${item.rounded_average} SP` 
                : (item.average !== null && item.average !== undefined ? item.average.toFixed(2) : 'N/A');

            return `
                <div class="history-item">
                    <div class="history-item-header-wrapper">
                        <div>
                            <div class="history-title">${escapeHtml(item.story_name)}</div>
                            <div class="history-date">${formattedDate}</div>
                        </div>
                        ${isFacilitator ? `
                        <div class="history-actions">
                            <button class="btn-revote" onclick="revoteStory('${escapeHtml(item.story_name)}', ${index})" title="Votar de nuevo esta historia">
                                🔄 Re-votar
                            </button>
                        </div>
                        ` : ''}
                    </div>
                    <div class="history-stats">
                        <div class="history-stat">
                            <div class="history-stat-label">Resumen</div>
                            <div class="history-stat-value">${summaryHtml}</div>
                        </div>
                        <div class="history-stat">
                            <div class="history-stat-label">Estimación</div>
                            <div class="history-stat-value">${avgText}</div>
                        </div>
                    </div>
                    ${votesHtml}
                </div>
            `;
        }).join('');
}

function revoteStory(storyName, historyIndex) {
    if (!isFacilitator) {
        showNotification('Solo el facilitador puede iniciar una re-votación', 'warning');
        return;
    }

    showNotification(`¿Deseas votar de nuevo la historia "${storyName}"?`, 'question', true).then((confirmed) => {
        if (confirmed) {
            // Resetear votos actuales
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    action: 'reset'
                }));
            }

            // Esperar un poco y establecer la historia
            setTimeout(() => {
                const storyInput = document.getElementById('storyName');
                storyInput.value = storyName;
                setStory();
            }, 300);
        }
    });
}

function updateTotalPoints() {
    const totalPoints = document.getElementById('totalPoints');
    const totalValue = document.getElementById('totalValue');
    
    if (roomState.total_story_points !== undefined && roomState.total_story_points > 0) {
        // Mostrar sin decimales si es número entero
        const total = roomState.total_story_points;
        totalValue.textContent = Number.isInteger(total) ? total : total.toFixed(1);
        totalPoints.style.display = 'flex';
    } else {
        totalPoints.style.display = 'none';
    }
}

function changeScale() {
    const scale = document.getElementById('scaleSelect').value;
    
    if (scale === 'custom') {
        openCustomScaleModal();
        return;
    }
    
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            action: 'change_scale',
            scale: scale
        }));
    }
}

function openCustomScaleModal() {
    document.getElementById('customScaleModal').style.display = 'flex';
}

function closeCustomScaleModal() {
    document.getElementById('customScaleModal').style.display = 'none';
    // Restaurar selector a la escala actual
    document.getElementById('scaleSelect').value = roomState.voting_scale || 'modified_fibonacci';
}

function saveCustomScale() {
    const input = document.getElementById('customScaleInput').value;
    const values = input.split(',').map(v => v.trim()).filter(v => v);
    
    if (values.length === 0) {
        showNotification('Por favor ingresa al menos un valor', 'warning');
        return;
    }
    
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            action: 'set_custom_scale',
            values: values
        }));
    }
    
    closeCustomScaleModal();
    document.getElementById('customScaleInput').value = '';
}

function toggleVotingMode() {
    if (!isFacilitator || !ws || ws.readyState !== WebSocket.OPEN) return;

    ws.send(JSON.stringify({
        action: 'toggle_voting_mode'
    }));
}

function hideResults() {
    const resultsSection = document.getElementById('resultsSection');
    resultsSection.style.display = 'none';
}

function updateConnectionStatus(connected) {
    const statusIndicator = document.querySelector('.status-indicator');
    const statusText = document.querySelector('.status-text');

    if (connected) {
        statusIndicator.classList.add('connected');
        statusIndicator.classList.remove('disconnected');
        statusText.textContent = 'Conectado';
    } else {
        statusIndicator.classList.remove('connected');
        statusIndicator.classList.add('disconnected');
        statusText.textContent = 'Desconectado';
    }
}

function copyRoomId() {
    const roomIdElement = document.getElementById('roomIdDisplay');
    if (!roomIdElement) {
        console.error('Elemento roomIdDisplay no encontrado');
        return;
    }
    
    const roomId = roomIdElement.textContent.trim();
    const btn = document.querySelector('.btn-copy-sm') || document.querySelector('.btn-copy');
    const copyIcon = document.getElementById('copyIcon');
    
    console.log('Intentando copiar:', roomId);
    
    // Crear textarea temporal
    const textArea = document.createElement('textarea');
    textArea.value = roomId;
    textArea.style.position = 'fixed';
    textArea.style.top = '0';
    textArea.style.left = '-9999px';
    textArea.setAttribute('readonly', '');
    document.body.appendChild(textArea);
    
    // Seleccionar y copiar
    textArea.select();
    textArea.setSelectionRange(0, 99999); // Para móviles
    
    let copied = false;
    try {
        copied = document.execCommand('copy');
        console.log('execCommand result:', copied);
    } catch (err) {
        console.error('Error con execCommand:', err);
    }
    
    document.body.removeChild(textArea);
    
    // Si execCommand falló, intentar con clipboard API
    if (!copied && navigator.clipboard) {
        navigator.clipboard.writeText(roomId).then(() => {
            updateCopyButton(btn, copyIcon, true);
        }).catch(err => {
            console.error('Error con clipboard API:', err);
            updateCopyButton(btn, copyIcon, false);
        });
    } else {
        updateCopyButton(btn, copyIcon, copied);
    }
}

function updateCopyButton(btn, copyIcon, success) {
    if (!btn) return;
    
    if (success) {
        btn.classList.add('copied');
        // Update icon to checkmark SVG
        if (copyIcon && copyIcon.tagName === 'svg') {
            copyIcon.innerHTML = '<polyline points="20 6 9 17 4 12"></polyline>';
        } else if (copyIcon) {
            copyIcon.textContent = '✓';
        }
        
        // Mostrar notificación flotante
        showCopyNotification();
        
        // Restaurar después de 2 segundos
        setTimeout(() => {
            btn.classList.remove('copied');
            if (copyIcon && copyIcon.tagName === 'svg') {
                copyIcon.innerHTML = '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>';
            } else if (copyIcon) {
                copyIcon.textContent = '📋';
            }
        }, 2000);
    } else {
        setTimeout(() => {
            // Reset on error
        }, 1500);
    }
}

function showCopyNotification() {
    // Crear notificación
    const notification = document.createElement('div');
    notification.className = 'copy-notification';
    notification.textContent = '✓ ID copiado al portapapeles';
    document.body.appendChild(notification);
    
    // Posicionar en la parte superior central
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.left = '50%';
    notification.style.transform = 'translateX(-50%) translateY(-20px)';
    notification.style.opacity = '0';
    
    // Animar entrada
    requestAnimationFrame(() => {
        notification.style.transition = 'all 0.3s ease-out';
        notification.style.opacity = '1';
        notification.style.transform = 'translateX(-50%) translateY(0)';
    });
    
    // Animar salida y remover
    setTimeout(() => {
        notification.style.transition = 'all 0.3s ease-in';
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(-50%) translateY(-20px)';
        
        setTimeout(() => {
            if (notification.parentNode) {
                document.body.removeChild(notification);
            }
        }, 300);
    }, 2000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Limpiar al salir
window.addEventListener('beforeunload', () => {
    if (ws) {
        ws.close();
    }
});
