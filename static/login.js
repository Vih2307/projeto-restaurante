/* ==========================================================
   Restaurante BKV - lógica da página de acesso
   Dois passos: entrar e pedir o link de recuperação por e-mail.
   A nova senha é escolhida na página do Firebase aberta pelo link do e-mail.
   ========================================================== */

const ESPERA_REENVIO = 60; // segundos; o back-end também bloqueia reenvios em 60 s
let temporizadorReenvio = null;

function pegar(id) {
    return document.getElementById(id);
}

/* ---------- Navegação entre os passos ---------- */
function mostrarTela(nome) {
    ["acesso", "recuperacao"].forEach(function (id) {
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
        if (!temporizadorReenvio || botao.id !== "botao-enviar-link") botao.disabled = false;
    }
}

// Conta 60 segundos no botão "Enviar link" para evitar pedidos repetidos.
function iniciarContagemReenvio() {
    const botao = pegar("botao-enviar-link");
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
            botao.textContent = "Enviar link";
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
    if (sucesso) iniciarContagemReenvio();
});
