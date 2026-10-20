/* ==========================================================
   Sabor da Casa - lógica da página de acesso
   Três passos: entrar, pedir código por e-mail, definir nova senha.
   ========================================================== */

const ESPERA_REENVIO = 60; // segundos; o back-end também bloqueia reenvios em 60 s
let temporizadorReenvio = null;

function pegar(id) {
    return document.getElementById(id);
}

/* ---------- Navegação entre os passos ---------- */
function mostrarTela(nome) {
    ["acesso", "recuperacao", "alteracao"].forEach(function (id) {
        pegar(id).hidden = id !== nome;
    });
    mostrarMensagem("", false);

    // Leva o foco ao título da nova tela (ajuda leitores de tela e teclado).
    pegar("titulo-" + nome).focus();
}

function mostrarMensagem(texto, erro) {
    const mensagem = pegar("mensagem");
    mensagem.textContent = texto;
    mensagem.className = erro ? "erro" : "";
}

document.querySelectorAll("[data-ir]").forEach(function (botao) {
    botao.addEventListener("click", function () {
        mostrarTela(botao.dataset.ir);
    });
});

/* ---------- Mostrar ou esconder a senha ---------- */
document.querySelectorAll(".ver-senha").forEach(function (botao) {
    botao.addEventListener("click", function () {
        const campo = pegar(botao.dataset.alvo);
        const visivel = campo.type === "text";
        campo.type = visivel ? "password" : "text";
        botao.textContent = visivel ? "Mostrar" : "Ocultar";
        botao.setAttribute("aria-pressed", visivel ? "false" : "true");
        botao.setAttribute("aria-label", visivel ? "Mostrar senha" : "Ocultar senha");
    });
});

/* ---------- Regras da nova senha, marcadas enquanto digita ---------- */
function atualizarRegras() {
    const senha = pegar("nova-senha").value;
    const confirmacao = pegar("confirmacao").value;
    const regras = {
        tamanho: senha.length >= 8 && senha.length <= 128,
        letra: /[A-Za-zÀ-ÿ]/.test(senha),
        numero: /[0-9]/.test(senha),
        igual: senha !== "" && senha === confirmacao
    };

    document.querySelectorAll("#regras-senha li").forEach(function (item) {
        item.classList.toggle("ok", regras[item.dataset.regra]);
    });
}
pegar("nova-senha").addEventListener("input", atualizarRegras);
pegar("confirmacao").addEventListener("input", atualizarRegras);

// O código só aceita números.
pegar("codigo").addEventListener("input", function () {
    this.value = this.value.replace(/\D/g, "").slice(0, 6);
});

/* ---------- Envio para o servidor ---------- */
async function enviarDados(rota, dados, formulario) {
    const botao = formulario.querySelector(".botao");
    botao.disabled = true;
    try {
        const resposta = await fetch(rota, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(dados)
        });
        const resultado = await resposta.json();
        mostrarMensagem(resultado.mensagem || resultado.erro, !resposta.ok);
        return resposta.ok;
    } catch (erro) {
        mostrarMensagem("Não foi possível conectar ao servidor.", true);
        return false;
    } finally {
        // O botão de código fica bloqueado pela contagem; os demais voltam ao normal.
        if (!temporizadorReenvio || botao.id !== "botao-enviar-codigo") botao.disabled = false;
    }
}

// Conta 60 segundos no botão "Enviar código" para evitar pedidos repetidos.
function iniciarContagemReenvio() {
    const botao = pegar("botao-enviar-codigo");
    let restante = ESPERA_REENVIO;
    botao.disabled = true;
    botao.textContent = "Enviar de novo em " + restante + " s";

    clearInterval(temporizadorReenvio);
    temporizadorReenvio = setInterval(function () {
        restante -= 1;
        if (restante <= 0) {
            clearInterval(temporizadorReenvio);
            temporizadorReenvio = null;
            botao.disabled = false;
            botao.textContent = "Enviar código";
            return;
        }
        botao.textContent = "Enviar de novo em " + restante + " s";
    }, 1000);
}

pegar("form-login").addEventListener("submit", async function (evento) {
    evento.preventDefault();
    const dados = {
        email: pegar("email-login").value,
        senha: pegar("senha-login").value
    };
    const sucesso = await enviarDados("/api/login", dados, this);
    if (sucesso) window.location.href = "/";
});

pegar("form-recuperacao").addEventListener("submit", async function (evento) {
    evento.preventDefault();
    const email = pegar("email-recuperacao").value;
    const sucesso = await enviarDados("/api/recuperar-senha", {email: email}, this);
    if (sucesso) {
        pegar("email-alteracao").value = email;
        iniciarContagemReenvio();
    }
});

pegar("form-alteracao").addEventListener("submit", async function (evento) {
    evento.preventDefault();
    const dados = {
        email: pegar("email-alteracao").value,
        codigo: pegar("codigo").value,
        senha: pegar("nova-senha").value,
        confirmacao: pegar("confirmacao").value
    };
    const sucesso = await enviarDados("/api/alterar-senha", dados, this);
    if (sucesso) {
        this.reset();
        atualizarRegras();
        mostrarTela("acesso");
        mostrarMensagem("Senha alterada. Entre com sua nova senha.", false);
    }
});
