function mostrarTela(nome) {
    document.getElementById("acesso").hidden = nome !== "acesso";
    document.getElementById("recuperacao").hidden = nome !== "recuperacao";
    document.getElementById("alteracao").hidden = nome !== "alteracao";
    document.getElementById("mensagem").textContent = "";
}

async function enviarDados(rota, dados, formulario) {
    const botao = formulario.querySelector("button");
    botao.disabled = true;
    try {
        const resposta = await fetch(rota, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(dados)
        });
        const resultado = await resposta.json();
        document.getElementById("mensagem").textContent = resultado.mensagem || resultado.erro;
        return resposta.ok;
    } catch {
        document.getElementById("mensagem").textContent = "Não foi possível conectar ao servidor.";
        return false;
    } finally {
        botao.disabled = false;
    }
}

document.getElementById("form-login").addEventListener("submit", async function (evento) {
    evento.preventDefault();
    const dados = {
        email: document.getElementById("email-login").value,
        senha: document.getElementById("senha-login").value
    };
    const sucesso = await enviarDados("/api/login", dados, this);
    if (sucesso) window.location.href = "/";
});

document.getElementById("form-recuperacao").addEventListener("submit", async function (evento) {
    evento.preventDefault();
    const email = document.getElementById("email-recuperacao").value;
    const sucesso = await enviarDados("/api/recuperar-senha", {email: email}, this);
    if (sucesso) document.getElementById("email-alteracao").value = email;
});

document.getElementById("form-alteracao").addEventListener("submit", async function (evento) {
    evento.preventDefault();
    const dados = {
        email: document.getElementById("email-alteracao").value,
        codigo: document.getElementById("codigo").value,
        senha: document.getElementById("nova-senha").value,
        confirmacao: document.getElementById("confirmacao").value
    };
    const sucesso = await enviarDados("/api/alterar-senha", dados, this);
    if (sucesso) {
        this.reset();
        mostrarTela("acesso");
        document.getElementById("mensagem").textContent = "Senha alterada. Entre com sua nova senha.";
    }
});
