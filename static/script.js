let dadosSistema = null;
let mesaSelecionada = null;
let carrinho = [];
let categoriaAtual = "Todos";

const dinheiro = new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL"
});

document.addEventListener("DOMContentLoaded", function () {
    mostrarData();
    prepararEventos();
    carregarDados();
});

function prepararEventos() {
    document.querySelectorAll(".botao-menu").forEach(function (botao) {
        botao.addEventListener("click", function () {
            abrirTela(botao.dataset.tela);
        });
    });

    document.getElementById("limpar-pedido").addEventListener("click", function () {
        carrinho = [];
        renderizarCarrinho();
    });

    document.getElementById("enviar-pedido").addEventListener("click", enviarPedido);
    document.getElementById("repor-estoque").addEventListener("click", reporEstoque);
    document.getElementById("filtro-estoque").addEventListener("change", renderizarEstoque);
}

function mostrarData() {
    const data = new Date().toLocaleDateString("pt-BR", {
        weekday: "long",
        day: "2-digit",
        month: "long"
    });
    document.getElementById("data-atual").textContent = data;
}

function abrirTela(nome) {
    const informacoes = {
        garcom: ["Atendimento do garçom", "Garçom"],
        caixa: ["Caixa e pagamentos", "Operador de caixa"],
        gerente: ["Visão do gerente", "Gerente"]
    };

    document.querySelectorAll(".tela").forEach(function (tela) {
        tela.classList.remove("ativa");
    });

    document.querySelectorAll(".botao-menu").forEach(function (botao) {
        botao.classList.remove("ativo");
    });

    document.getElementById("tela-" + nome).classList.add("ativa");
    document.querySelector('[data-tela="' + nome + '"]').classList.add("ativo");
    document.getElementById("titulo-tela").textContent = informacoes[nome][0];
    document.getElementById("perfil-atual").textContent = informacoes[nome][1];
}

async function carregarDados() {
    try {
        const resposta = await fetch("/api/dados");
        dadosSistema = await resposta.json();

        renderizarMesas();
        renderizarFiltros();
        renderizarCardapio();
        renderizarCaixa();
        renderizarGerente();

        document.getElementById("status-caixa-menu").textContent =
            dadosSistema.caixa.status.toLowerCase();
    } catch (erro) {
        mostrarMensagem("Não foi possível carregar os dados do sistema.", true);
    }
}

function renderizarMesas() {
    const area = document.getElementById("lista-mesas");
    area.innerHTML = "";

    dadosSistema.mesas.forEach(function (mesa) {
        const botao = document.createElement("button");
        botao.className = "mesa " + (mesa.status === "Livre" ? "" : "ocupada");

        if (mesa.numero === mesaSelecionada) {
            botao.classList.add("selecionada");
        }

        botao.innerHTML = "<strong>Mesa " + mesa.numero + "</strong><small>" + mesa.status + "</small>";
        botao.addEventListener("click", function () {
            mesaSelecionada = mesa.numero;
            document.getElementById("mesa-pedido").textContent = "Mesa " + mesa.numero;
            renderizarMesas();
        });
        area.appendChild(botao);
    });
}

function renderizarFiltros() {
    const area = document.getElementById("filtros-cardapio");
    const categorias = ["Todos"];

    dadosSistema.cardapio.forEach(function (produto) {
        if (!categorias.includes(produto.categoria)) {
            categorias.push(produto.categoria);
        }
    });

    area.innerHTML = "";
    categorias.forEach(function (categoria) {
        const botao = document.createElement("button");
        botao.className = "filtro" + (categoria === categoriaAtual ? " ativo" : "");
        botao.textContent = categoria;
        botao.addEventListener("click", function () {
            categoriaAtual = categoria;
            renderizarFiltros();
            renderizarCardapio();
        });
        area.appendChild(botao);
    });
}

function renderizarCardapio() {
    const area = document.getElementById("lista-cardapio");
    const produtos = dadosSistema.cardapio.filter(function (produto) {
        return categoriaAtual === "Todos" || produto.categoria === categoriaAtual;
    });

    area.innerHTML = "";
    produtos.forEach(function (produto) {
        const botao = document.createElement("button");
        botao.className = "produto";
        botao.innerHTML =
            "<small>" + produto.categoria + "</small>" +
            "<strong>" + produto.nome + "</strong>" +
            "<span class='preco'>" + dinheiro.format(produto.preco) + "</span>";
        botao.addEventListener("click", function () {
            adicionarAoCarrinho(produto);
        });
        area.appendChild(botao);
    });
}

function adicionarAoCarrinho(produto) {
    const itemExistente = carrinho.find(function (item) {
        return item.nome === produto.nome;
    });

    if (itemExistente) {
        itemExistente.quantidade += 1;
    } else {
        carrinho.push({
            nome: produto.nome,
            preco: produto.preco,
            quantidade: 1
        });
    }

    renderizarCarrinho();
}

function alterarQuantidade(nome, valor) {
    const item = carrinho.find(function (produto) {
        return produto.nome === nome;
    });

    if (!item) return;

    item.quantidade += valor;
    if (item.quantidade <= 0) {
        carrinho = carrinho.filter(function (produto) {
            return produto.nome !== nome;
        });
    }

    renderizarCarrinho();
}

function renderizarCarrinho() {
    const area = document.getElementById("itens-pedido");
    const total = carrinho.reduce(function (soma, item) {
        return soma + item.preco * item.quantidade;
    }, 0);

    document.getElementById("total-pedido").textContent = dinheiro.format(total);

    if (carrinho.length === 0) {
        area.innerHTML = "<div class='vazio'><span>🧾</span><p>Nenhum item adicionado</p></div>";
        return;
    }

    area.innerHTML = "";
    carrinho.forEach(function (item) {
        const linha = document.createElement("div");
        linha.className = "item-pedido";
        linha.innerHTML =
            "<div><strong>" + item.nome + "</strong>" +
            "<small>" + dinheiro.format(item.preco * item.quantidade) + "</small></div>" +
            "<div class='controle-quantidade'>" +
            "<button class='diminuir'>−</button><span>" + item.quantidade + "</span>" +
            "<button class='aumentar'>+</button></div>";

        linha.querySelector(".diminuir").addEventListener("click", function () {
            alterarQuantidade(item.nome, -1);
        });
        linha.querySelector(".aumentar").addEventListener("click", function () {
            alterarQuantidade(item.nome, 1);
        });
        area.appendChild(linha);
    });
}

async function enviarPedido() {
    if (!mesaSelecionada) {
        mostrarMensagem("Primeiro selecione uma mesa.", true);
        return;
    }

    if (carrinho.length === 0) {
        mostrarMensagem("Adicione pelo menos um item ao pedido.", true);
        return;
    }

    const resposta = await fetch("/api/pedidos", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({mesa: mesaSelecionada, itens: carrinho})
    });
    const resultado = await resposta.json();

    if (!resposta.ok) {
        mostrarMensagem(resultado.erro, true);
        return;
    }

    mostrarMensagem(resultado.mensagem);
    carrinho = [];
    renderizarCarrinho();
    await carregarDados();
}

function renderizarCaixa() {
    document.getElementById("caixa-total").textContent = dinheiro.format(dadosSistema.caixa.total_vendido);
    document.getElementById("caixa-vendas").textContent = dadosSistema.caixa.quantidade_vendas;
    document.getElementById("caixa-abertas").textContent = dadosSistema.pedidos.length;

    const area = document.getElementById("lista-contas");
    area.innerHTML = "";

    if (dadosSistema.pedidos.length === 0) {
        area.innerHTML = "<div class='sem-registro'>Nenhuma conta em aberto no momento.</div>";
        return;
    }

    dadosSistema.pedidos.forEach(function (pedido) {
        const itens = pedido.itens.map(function (item) {
            return item.quantidade + "x " + item.nome;
        }).join(" • ");

        const card = document.createElement("article");
        card.className = "conta";
        card.innerHTML =
            "<div class='conta-topo'><h3>Mesa " + pedido.mesa + "</h3>" +
            "<span class='etiqueta'>Pedido #" + pedido.numero + "</span></div>" +
            "<div class='conta-itens'>" + itens + "</div>" +
            "<div class='conta-rodape'><strong class='conta-total'>" + dinheiro.format(pedido.total) + "</strong>" +
            "<div class='pagamento'><select>" +
            "<option value=''>Pagamento</option><option>Dinheiro</option><option>PIX</option>" +
            "<option>Débito</option><option>Crédito</option></select>" +
            "<button>Finalizar</button></div></div>";

        card.querySelector("button").addEventListener("click", function () {
            const forma = card.querySelector("select").value;
            finalizarConta(pedido.numero, forma);
        });
        area.appendChild(card);
    });
}

async function finalizarConta(numero, formaPagamento) {
    if (!formaPagamento) {
        mostrarMensagem("Escolha a forma de pagamento.", true);
        return;
    }

    const resposta = await fetch("/api/pedidos/" + numero + "/finalizar", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({forma_pagamento: formaPagamento})
    });
    const resultado = await resposta.json();

    mostrarMensagem(resultado.mensagem || resultado.erro, !resposta.ok);
    if (resposta.ok) await carregarDados();
}

function renderizarGerente() {
    document.getElementById("gerente-total").textContent = dinheiro.format(dadosSistema.caixa.total_vendido);
    document.getElementById("ticket-medio").textContent = dinheiro.format(dadosSistema.caixa.ticket_medio);

    const baixos = dadosSistema.estoque.filter(function (item) {
        return item.baixo;
    }).length;
    document.getElementById("estoque-baixo").textContent = baixos + (baixos === 1 ? " item" : " itens");

    renderizarEstoque();
    renderizarVendas();

    const select = document.getElementById("produto-reposicao");
    const produtoSelecionado = select.value;
    select.innerHTML = "";
    dadosSistema.estoque.forEach(function (item) {
        const option = document.createElement("option");
        option.value = item.nome;
        option.textContent = item.nome;
        select.appendChild(option);
    });
    if (produtoSelecionado) select.value = produtoSelecionado;
}

function renderizarEstoque() {
    if (!dadosSistema) return;

    const filtro = document.getElementById("filtro-estoque").value;
    const area = document.getElementById("tabela-estoque");
    const itens = dadosSistema.estoque.filter(function (item) {
        return filtro === "todos" || item.baixo;
    });

    area.innerHTML = "";
    itens.forEach(function (item) {
        const linha = document.createElement("tr");
        linha.innerHTML =
            "<td><strong>" + item.nome + "</strong></td>" +
            "<td>" + item.quantidade + " " + item.unidade + "</td>" +
            "<td>" + item.estoque_minimo + " " + item.unidade + "</td>" +
            "<td><span class='situacao " + (item.baixo ? "baixo" : "") + "'>" +
            (item.baixo ? "Estoque baixo" : "Normal") + "</span></td>";
        area.appendChild(linha);
    });

    if (itens.length === 0) {
        area.innerHTML = "<tr><td colspan='4' class='sem-registro'>Nenhum produto com estoque baixo.</td></tr>";
    }
}

function renderizarVendas() {
    const area = document.getElementById("lista-vendas");
    area.innerHTML = "";

    if (dadosSistema.vendas.length === 0) {
        area.innerHTML = "<div class='sem-registro'>Nenhuma venda finalizada hoje.</div>";
        return;
    }

    dadosSistema.vendas.slice().reverse().forEach(function (venda) {
        const linha = document.createElement("div");
        linha.className = "venda";
        linha.innerHTML =
            "<div><strong>Pedido #" + venda.numero + " • Mesa " + venda.mesa + "</strong>" +
            "<small>Pagamento: " + venda.forma_pagamento + "</small></div>" +
            "<strong>" + dinheiro.format(venda.total) + "</strong>";
        area.appendChild(linha);
    });
}

async function reporEstoque() {
    const nome = document.getElementById("produto-reposicao").value;
    const quantidade = Number(document.getElementById("quantidade-reposicao").value);

    const resposta = await fetch("/api/estoque/entrada", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({nome: nome, quantidade: quantidade})
    });
    const resultado = await resposta.json();

    mostrarMensagem(resultado.mensagem || resultado.erro, !resposta.ok);
    if (resposta.ok) await carregarDados();
}

function mostrarMensagem(texto, erro) {
    const mensagem = document.getElementById("mensagem");
    mensagem.textContent = texto;
    mensagem.className = "mensagem" + (erro ? " erro" : "");

    setTimeout(function () {
        mensagem.classList.add("escondido");
    }, 3500);
}
