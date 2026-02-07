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
    const main = document.querySelector('body');
    main.innerHTML = `
        <div class="min-h-screen flex flex-col p-6 max-w-md mx-auto justify-center">
            <p id="status" class="text-center text-slate-500 uppercase tracking-widest text-xs mb-8 font-bold">Select an Answer</p>
            <div class="grid grid-cols-1 gap-4">
                ${data.options.map((opt, i) => `
                    <button onclick="submitAnswer(${i})" class="w-full border-2 border-slate-800 py-8 text-2xl font-black hover:border-cyan-500 transition-all active:scale-95">
                        ${["A", "B", "C", "D"][i]}
                    </button>
                `).join('')}
            </div>
        </div>
    `;
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