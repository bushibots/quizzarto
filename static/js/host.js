const socket = io();
const gamePin = document.getElementById('game-pin').innerText;

// Join as Host
socket.emit('join', { nickname: 'HOST', pin: gamePin });

function startQuiz() {
    const quizId = document.getElementById('quiz-select').value;
    if (!quizId) {
        alert("Please select or create a quiz first.");
        return;
    }
    // Send both the PIN and the selected Quiz ID
    socket.emit('start_quiz', { pin: gamePin, set_id: quizId });
}

socket.on('update_lobby', (players) => {
    const list = document.getElementById('player-list');
    // Filter out host and count players
    document.getElementById('player-count').innerText = players.length;

    if (players.length === 0) {
        list.innerHTML = '<p class="text-slate-600 text-xs italic">Waiting for players to join...</p>';
        return;
    }

    // Render detailed cards for the host
    list.innerHTML = players.map(p => `
        <div class="bg-slate-900 border border-slate-700 p-4 flex flex-col min-w-[200px]">
            <span class="text-cyan-500 font-black text-lg uppercase tracking-tighter">${p.nickname}</span>
            <div class="mt-2 pt-2 border-t border-slate-800">
                <p class="text-[10px] text-slate-500 uppercase tracking-widest">Email</p>
                <p class="text-xs font-mono text-slate-300">${p.email}</p>
            </div>
            <div class="mt-1">
                <p class="text-[10px] text-slate-500 uppercase tracking-widest">Phone</p>
                <p class="text-xs font-mono text-slate-300">${p.phone}</p>
            </div>
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

// Add these to the bottom of host.js

socket.on('show_results', (data) => {
    // Highlight the correct answer in the options grid
    const options = document.getElementById('options-grid').children;
    const correctIdx = data.correct_index;
    
    // Add a neon green border to the correct answer and dim others
    Array.from(options).forEach((opt, i) => {
        if (i === correctIdx) {
            opt.classList.remove('border-slate-800');
            opt.classList.add('border-green-500', 'bg-green-500/10');
        } else {
            opt.style.opacity = "0.2";
        }
    });

setTimeout(() => {
        startQuiz(); 
    }, 5000);
});

socket.on('game_over', (data) => {
    const container = document.getElementById('game-container');
    container.innerHTML = `
        <div class="text-center">
            <h1 class="text-6xl font-black mb-12 italic tracking-tighter text-cyan-500">FINAL STANDINGS</h1>
            <div class="max-w-md mx-auto space-y-4">
                ${data.leaderboard.map((player, i) => `
                    <div class="flex justify-between items-center p-6 border-2 ${i === 0 ? 'border-cyan-500 bg-cyan-500/10' : 'border-slate-800'}">
                        <span class="text-2xl font-bold">${i + 1}. ${player.nickname}</span>
                        <span class="text-2xl font-black text-cyan-400">${player.score}</span>
                    </div>
                `).join('')}
            </div>
            <button onclick="location.reload()" class="mt-12 border-2 border-white px-8 py-3 font-bold uppercase hover:bg-white hover:text-black transition-all">
                Terminate Session
            </button>
        </div>
    `;
});