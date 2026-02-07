const socket = io();
const gamePin = document.getElementById('game-pin').innerText;

// Join as Host
socket.emit('join', { nickname: 'HOST', pin: gamePin });

function startQuiz() {
    socket.emit('start_quiz', gamePin);
}

socket.on('update_lobby', (players) => {
    const list = document.getElementById('player-list');
    const actualPlayers = players.filter(p => p !== 'HOST');
    document.getElementById('player-count').innerText = actualPlayers.length;

    if (actualPlayers.length === 0) {
        list.innerHTML = '<p class="text-slate-600 text-xs italic">Waiting for players to join...</p>';
        return;
    }

    list.innerHTML = actualPlayers.map(p => `
        <div class="bg-slate-800 border border-slate-700 px-6 py-3 text-white text-sm font-bold">
            ${p}
        </div>
    `).join('');
});

socket.on('new_question', (data) => {
    // Hide Lobby, Show Question
    document.getElementById('lobby-view').classList.add('hidden');
    document.getElementById('question-view').classList.remove('hidden');

    document.getElementById('question-text').innerText = data.question;
    const grid = document.getElementById('options-grid');
    
    grid.innerHTML = data.options.map((opt, i) => `
        <div class="border-2 border-slate-800 p-6 flex items-center bg-slate-900/50">
            <span class="w-10 h-10 border border-cyan-500 text-cyan-500 flex items-center justify-center mr-6 font-bold">${i + 1}</span>
            <span class="text-2xl font-bold">${opt}</span>
        </div>
    `).join('');
});

socket.on('timer_update', (time) => {
    document.getElementById('timer').innerText = time;
});