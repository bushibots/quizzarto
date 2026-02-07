const socket = io();
let myNickname = "";
let myPin = "";

function joinGame() {
    myNickname = document.getElementById('nickname').value;
    myPin = document.getElementById('pin').value;
    
    if(!myNickname || !myPin) return;

    socket.emit('join', { nickname: myNickname, pin: myPin });
    
    document.getElementById('join-screen').innerHTML = `
        <div class="text-center">
            <h2 class="text-xl text-cyan-500 uppercase tracking-widest mb-2 font-bold">Connected</h2>
            <p class="text-slate-500 text-sm">Waiting for the game to start...</p>
        </div>
    `;
}

socket.on('new_question', (data) => {
    // Target the specific join-screen container instead of the whole body
    const main = document.getElementById('join-screen');
    if (!main) return;

    main.innerHTML = `
        <div class="flex flex-col justify-center">
            <h2 class="text-2xl font-black text-cyan-400 mb-6 text-center italic tracking-tighter">
                ${data.question}
            </h2>
            
            <p id="status" class="text-center text-slate-500 uppercase tracking-widest text-[10px] mb-8 font-bold">
                Select Authorized Response
            </p>
            
            <div class="grid grid-cols-1 gap-4">
                ${data.options.map((opt, i) => `
                    <button onclick="submitAnswer(${i})" class="w-full border-2 border-slate-800 py-6 text-xl font-black hover:border-cyan-500 transition-all active:scale-95 text-white bg-slate-900/50">
                        ${["A", "B", "C", "D"][i]}
                    </button>
                `).join('')}
            </div>
        </div>
    `;
});

socket.on('join_error', (data) => {
    // Find the PIN input and turn it red/show error
    const pinInput = document.getElementById('pin');
    pinInput.classList.add('border-red-500');
    pinInput.value = "";
    pinInput.placeholder = data.message;
    
    // Reset the button state if needed
    alert(data.message); 
});

function submitAnswer(idx) {
    socket.emit('submit_answer', { pin: myPin, nickname: myNickname, answer: idx });
    document.getElementById('status').innerText = "Answer Submitted";
    // Disable all buttons
    const buttons = document.querySelectorAll('button');
    buttons.forEach(b => {
        b.disabled = true;
        b.style.opacity = "0.3";
    });
}

// Add these to the bottom of player.js

socket.on('show_results', (data) => {
    const status = document.getElementById('status');
    if (status) {
        status.innerText = "ROUND COMPLETE";
        status.classList.add('text-cyan-400');
    }
});

socket.on('game_over', (data) => {
    const main = document.querySelector('body');
    // Find this player's specific rank in the leaderboard
    const myRank = data.leaderboard.findIndex(p => p.nickname === myNickname) + 1;
    const myScore = data.leaderboard.find(p => p.nickname === myNickname)?.score || 0;

    main.innerHTML = `
        <div class="min-h-screen flex flex-col items-center justify-center p-6 text-center">
            <h1 class="text-4xl font-black mb-2 italic">DISCONNECTED</h1>
            <p class="text-slate-500 uppercase tracking-[0.3em] mb-12">Session Finalized</p>
            
            <div class="border-4 border-cyan-500 p-8 mb-8">
                <p class="text-xs uppercase tracking-widest text-cyan-500 mb-2">Rank</p>
                <h2 class="text-7xl font-black">#${myRank}</h2>
            </div>
            
            <p class="text-xl font-bold mb-12">SCORE: ${myScore}</p>
            
            <button onclick="location.reload()" class="w-full max-w-xs bg-white text-black py-4 font-black uppercase tracking-widest">
                Re-Initialize
            </button>
        </div>
    `;
});