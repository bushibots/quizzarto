const socket = io();

function joinGame() {
    const nickname = document.getElementById('nickname').value;
    const pin = document.getElementById('pin').value;
    
    if(!nickname || !pin) {
        alert("ERROR: MISSING DATA FIELDS");
        return;
    }

    socket.emit('join', { nickname, pin });
    
    // Switch to "Waiting" UI
    document.getElementById('join-screen').innerHTML = `
        <div class="text-center animate-pulse border border-cyan-500/30 p-8 bg-cyan-500/5 rounded-lg">
            <h2 class="text-xl text-cyan-500 uppercase tracking-widest mb-2 font-bold">Uplink Established</h2>
            <p class="text-slate-500 text-xs font-mono">Standby for Host Injection...</p>
        </div>
    `;
}