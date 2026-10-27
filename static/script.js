/* ==========================================================
   Restaurante BKV - lógica da interface principal
   Este arquivo conversa com as rotas do back-end (Flask) e
   desenha as telas: Garçom, Pedidos, Caixa e Gerente.
   ========================================================== */

/* ---------- 1. Estado da aplicação ---------- */
let dadosSistema = null;          // última resposta de /api/dados
let ultimoJson = "";              // usado para só redesenhar quando algo mudou
let mesaSelecionada = null;       // número da mesa escolhida pelo garçom
let carrinho = [];                // itens ainda não enviados à cozinha
let categoriaAtual = "Todos";     // filtro do cardápio
let textoBusca = "";              // texto digitado na busca do cardápio
let pagamentoEscolhido = {};      // {numeroDoPedido: "PIX"} - lembra a escolha no caixa
let pedidoParaCancelar = null;    // pedido aberto no diálogo de cancelamento

const INTERVALO_ATUALIZACAO = 15000; // 15 segundos
const FORMAS_PAGAMENTO = ["Dinheiro", "PIX", "Débito", "Crédito"];
const TITULOS_TELA = {
    garcom: "Atendimento",
    pedidos: "Pedidos em andamento",
    caixa: "Caixa",
    gerente: "Gerência"
};

const dinheiro = new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL"
});

/* ---------- 2. Funções utilitárias ---------- */

// Cria um elemento HTML de forma segura (usa textContent, nunca innerHTML).
// Assim, nomes de produtos ou motivos digitados não conseguem injetar código.
function el(tag, props, ...filhos) {
    const no = document.createElement(tag);
    Object.entries(props || {}).forEach(function ([chave, valor]) {
        if (valor === null || valor === undefined || valor === false) return;
        if (chave === "class") no.className = valor;
        else if (chave === "texto") no.textContent = valor;
        else if (chave.startsWith("on")) no.addEventListener(chave.slice(2), valor);
        else no.setAttribute(chave, valor === true ? "" : valor);
    });
    filhos.flat().forEach(function (filho) {
        if (filho === null || filho === undefined || filho === false) return;
        no.append(filho.nodeType ? filho : document.createTextNode(filho));
    });
    return no;
}

// Cria um ícone SVG a partir da biblioteca definida no index.html.
function icone(nome) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "icone");
    svg.setAttribute("aria-hidden", "true");
    const uso = document.createElementNS("http://www.w3.org/2000/svg", "use");
    uso.setAttribute("href", "#i-" + nome);
    svg.appendChild(uso);
    return svg;
}

function pegar(id) {
    return document.getElementById(id);
}

function limpar(no) {
    no.replaceChildren();
}

function tokenCsrf() {
    return document.querySelector('meta[name="token"]').content;
}

// Única função que fala com o servidor. Trata login expirado (401) e falta de conexão.
async function api(rota, corpo) {
    const opcoes = {};
    if (corpo !== undefined) {
        opcoes.method = "POST";
        opcoes.headers = {"Content-Type": "application/json", "X-CSRF-Token": tokenCsrf()};
        opcoes.body = JSON.stringify(corpo);
    }

    let resposta;
    try {
        resposta = await fetch(rota, opcoes);
    } catch (erro) {
        return {ok: false, dados: {erro: "Sem conexão com o servidor."}, offline: true};
    }

    if (resposta.status === 401) {
        window.location.href = "/login";
        return {ok: false, dados: {}};
    }

    let dados = {};
    try {
        dados = await resposta.json();
    } catch (erro) {
        dados = {};
    }
    return {ok: resposta.ok, dados: dados};
}

function plural(quantidade, singular, pluralTexto) {
    return quantidade + " " + (quantidade === 1 ? singular : pluralTexto);
}

function classeStatus(status) {
    if (status === "Em preparo") return "preparo";
    if (status === "Pronto") return "pronto";
    return "";
}

function estoqueDe(nome) {
    if (!dadosSistema) return 0;
    const item = dadosSistema.estoque.find(function (i) { return i.nome === nome; });
    return item ? item.quantidade : 0;
}

function pedidoDaMesa(numeroMesa) {
    if (!dadosSistema) return null;
    return dadosSistema.pedidos.find(function (p) { return p.mesa === numeroMesa; }) || null;
}

/* ---------- 3. Inicialização ---------- */
document.addEventListener("DOMContentLoaded", function () {
    mostrarData();
    mostrarUsuario();
    prepararEventos();
    renderizarCarrinho();
    carregarDados();
    setInterval(atualizarEmSegundoPlano, INTERVALO_ATUALIZACAO);
});

function mostrarData() {
    pegar("data-atual").textContent = new Date().toLocaleDateString("pt-BR", {
        weekday: "long",
        day: "2-digit",
        month: "long"
    });
}

// O back-end guarda nome e e-mail na sessão (vêm do cadastro no Neon).
// Se o nome não vier, usamos a parte do e-mail antes do "@".
function mostrarUsuario() {
    const email = document.body.dataset.email || "";
    const nomeCadastrado = (document.body.dataset.nome || "").trim();
    const nome = nomeCadastrado || email.split("@")[0].replace(/[._-]+/g, " ").trim() || "Usuário";
    const exibido = nome.charAt(0).toUpperCase() + nome.slice(1);
    pegar("nome-usuario").textContent = exibido;
    pegar("avatar").textContent = exibido.slice(0, 2).toUpperCase();
}

function prepararEventos() {
    document.querySelectorAll(".aba").forEach(function (botao) {
        botao.addEventListener("click", function () {
            abrirTela(botao.dataset.tela);
        });
    });

    pegar("limpar-pedido").addEventListener("click", function () {
        carrinho = [];
        renderizarCarrinho();
    });
    pegar("enviar-pedido").addEventListener("click", enviarPedido);
    pegar("botao-sair").addEventListener("click", sair);
    pegar("filtro-estoque").addEventListener("change", renderizarEstoque);

    pegar("busca-cardapio").addEventListener("input", function (evento) {
        textoBusca = evento.target.value.trim().toLowerCase();
        renderizarCardapio();
    });

    pegar("form-reposicao").addEventListener("submit", function (evento) {
        evento.preventDefault();
        reporEstoque();
    });
    document.querySelectorAll(".atalho").forEach(function (botao) {
        botao.addEventListener("click", function () {
            pegar("quantidade-reposicao").value = botao.dataset.qtd;
        });
    });

    pegar("resumo-fixo").addEventListener("click", function () {
        pegar("comanda").scrollIntoView({behavior: "smooth", block: "start"});
    });

    prepararDialogoCancelamento();
}

/* ---------- 4. Navegação entre telas ---------- */
function abrirTela(nome) {
    document.querySelectorAll(".tela").forEach(function (tela) {
        tela.classList.remove("ativa");
    });
    document.querySelectorAll(".aba").forEach(function (aba) {
        aba.classList.remove("ativa");
        aba.removeAttribute("aria-current");
    });

    pegar("tela-" + nome).classList.add("ativa");
    const abaAtiva = document.querySelector('.aba[data-tela="' + nome + '"]');
    abaAtiva.classList.add("ativa");
    abaAtiva.setAttribute("aria-current", "page");
    document.title = TITULOS_TELA[nome] + " - Restaurante BKV";
    window.scrollTo({top: 0});
}

/* ---------- 5. Carregamento dos dados (GET /api/dados) ---------- */
async function carregarDados(forcar) {
    const resultado = await api("/api/dados");

    if (resultado.offline) {
        pegar("aviso-conexao").hidden = false;
        if (!dadosSistema) mostrarMensagem("Não foi possível carregar os dados do sistema.", true);
        return;
    }
    pegar("aviso-conexao").hidden = true;
    if (!resultado.ok) return;

    const texto = JSON.stringify(resultado.dados);
    dadosSistema = resultado.dados;
    pegar("atualizacao").textContent = "Atualizado às " +
        new Date().toLocaleTimeString("pt-BR", {hour: "2-digit", minute: "2-digit"});

    // Nada mudou desde a última vez: não redesenha (evita perder o foco do teclado).
    if (texto === ultimoJson && !forcar) return;
    ultimoJson = texto;

    renderizarTudo();
}

function renderizarTudo() {
    renderizarStatusCaixa();
    renderizarMesas();
    renderizarFiltros();
    renderizarCardapio();
    renderizarCarrinho();
    renderizarQuadro();
    renderizarCaixa();
    renderizarGerente();
}

// Atualiza sozinho de tempos em tempos, mas não atrapalha quem está usando o diálogo.
function atualizarEmSegundoPlano() {
    if (document.hidden || pegar("modal-cancelar").open) return;
    carregarDados();
}

function renderizarStatusCaixa() {
    const aberto = dadosSistema.caixa.status === "Aberto";
    pegar("status-caixa").classList.toggle("aberto", aberto);
    pegar("status-caixa-texto").textContent = "Caixa " + dadosSistema.caixa.status.toLowerCase();
}

/* ---------- 6. Tela do garçom ---------- */
function renderizarMesas() {
    const area = pegar("lista-mesas");
    limpar(area);

    dadosSistema.mesas.forEach(function (mesa) {
        const pedido = pedidoDaMesa(mesa.numero);
        let classe = "mesa";
        if (mesa.status === "Ocupada") classe += " ocupada";
        if (mesa.status === "Aguardando fechamento") classe += " conta";
        if (mesa.numero === mesaSelecionada) classe += " selecionada";

        const botao = el("button", {
            type: "button",
            class: classe,
            "aria-pressed": mesa.numero === mesaSelecionada ? "true" : "false",
            onclick: function () { selecionarMesa(mesa.numero); }
        },
            el("span", {class: "mesa-numero", texto: mesa.numero}),
            el("span", {class: "mesa-estado", texto: mesa.status}),
            pedido ? el("span", {class: "mesa-total", texto: dinheiro.format(pedido.total)}) : null
        );
        area.appendChild(botao);
    });
}

function selecionarMesa(numero) {
    mesaSelecionada = numero;
    renderizarMesas();
    renderizarCarrinho();
}

function renderizarFiltros() {
    const area = pegar("filtros-cardapio");
    const categorias = ["Todos"];

    dadosSistema.cardapio.forEach(function (produto) {
        if (!categorias.includes(produto.categoria)) categorias.push(produto.categoria);
    });

    limpar(area);
    categorias.forEach(function (categoria) {
        area.appendChild(el("button", {
            type: "button",
            class: "filtro" + (categoria === categoriaAtual ? " ativo" : ""),
            "aria-pressed": categoria === categoriaAtual ? "true" : "false",
            texto: categoria,
            onclick: function () {
                categoriaAtual = categoria;
                renderizarFiltros();
                renderizarCardapio();
            }
        }));
    });
}

function renderizarCardapio() {
    const area = pegar("lista-cardapio");
    const produtos = dadosSistema.cardapio.filter(function (produto) {
        const daCategoria = categoriaAtual === "Todos" || produto.categoria === categoriaAtual;
        const naBusca = produto.nome.toLowerCase().includes(textoBusca);
        return daCategoria && naBusca;
    });

    limpar(area);
    if (produtos.length === 0) {
        area.appendChild(el("div", {class: "sem-registro", texto: "Nenhum prato encontrado. Tente outra busca."}));
        return;
    }

    produtos.forEach(function (produto) {
        const estoque = dadosSistema.estoque.find(function (i) { return i.nome === produto.nome; });
        const disponivel = estoque ? estoque.quantidade : 0;
        const esgotado = disponivel <= 0;

        let etiqueta = null;
        if (esgotado) etiqueta = el("span", {class: "etiqueta-estoque esgotado", texto: "Esgotado"});
        else if (estoque && estoque.baixo) etiqueta = el("span", {class: "etiqueta-estoque", texto: "Restam " + disponivel});

        area.appendChild(el("button", {
            type: "button",
            class: "produto",
            disabled: esgotado,
            onclick: function () { adicionarAoCarrinho(produto); }
        },
            el("span", {class: "produto-categoria", texto: produto.categoria}),
            el("span", {class: "produto-nome", texto: produto.nome}),
            el("span", {class: "produto-rodape"},
                el("span", {class: "preco", texto: dinheiro.format(produto.preco)}),
                etiqueta
            )
        ));
    });
}

function adicionarAoCarrinho(produto) {
    const existente = carrinho.find(function (item) { return item.nome === produto.nome; });
    const naComanda = existente ? existente.quantidade : 0;

    // Não deixa pedir mais do que existe no estoque (o back-end também valida).
    if (naComanda + 1 > estoqueDe(produto.nome)) {
        mostrarMensagem("Só restam " + estoqueDe(produto.nome) + " unidades de " + produto.nome + ".", true);
        return;
    }

    if (existente) existente.quantidade += 1;
    else carrinho.push({nome: produto.nome, preco: produto.preco, quantidade: 1});

    renderizarCarrinho();
}

function alterarQuantidade(nome, valor) {
    const item = carrinho.find(function (i) { return i.nome === nome; });
    if (!item) return;

    if (valor > 0 && item.quantidade + valor > estoqueDe(nome)) {
        mostrarMensagem("Só restam " + estoqueDe(nome) + " unidades de " + nome + ".", true);
        return;
    }

    item.quantidade += valor;
    if (item.quantidade <= 0) {
        carrinho = carrinho.filter(function (i) { return i.nome !== nome; });
    }
    renderizarCarrinho();
}

function renderizarCarrinho() {
    const area = pegar("itens-pedido");
    const total = carrinho.reduce(function (soma, item) { return soma + item.preco * item.quantidade; }, 0);
    const quantidade = carrinho.reduce(function (soma, item) { return soma + item.quantidade; }, 0);

    pegar("total-pedido").textContent = dinheiro.format(total);
    pegar("enviar-pedido").disabled = carrinho.length === 0;
    pegar("limpar-pedido").disabled = carrinho.length === 0;

    // Cabeçalho: qual mesa está sendo atendida
    const titulo = pegar("mesa-pedido");
    titulo.textContent = mesaSelecionada ? "Mesa " + mesaSelecionada : "Escolha uma mesa";
    titulo.classList.toggle("vazia", !mesaSelecionada);

    // Botão fixo para celular
    const resumo = pegar("resumo-fixo");
    resumo.hidden = carrinho.length === 0;
    pegar("resumo-fixo-qtd").textContent = plural(quantidade, "item", "itens");
    pegar("resumo-fixo-total").textContent = dinheiro.format(total);

    renderizarItensEnviados();

    limpar(area);
    if (carrinho.length === 0) {
        area.appendChild(el("div", {class: "vazio", texto: "Comanda vazia. Toque em um prato para começar."}));
        return;
    }

    carrinho.forEach(function (item) {
        area.appendChild(el("div", {class: "item-pedido"},
            el("strong", {texto: item.nome}),
            el("div", {class: "controle-quantidade"},
                el("button", {
                    type: "button",
                    "aria-label": "Diminuir quantidade de " + item.nome,
                    onclick: function () { alterarQuantidade(item.nome, -1); }
                }, icone("menos")),
                el("span", {texto: item.quantidade}),
                el("button", {
                    type: "button",
                    "aria-label": "Aumentar quantidade de " + item.nome,
                    onclick: function () { alterarQuantidade(item.nome, 1); }
                }, icone("mais"))
            ),
            el("small", {texto: dinheiro.format(item.preco * item.quantidade)})
        ));
    });
}

// Mostra, dentro da comanda, o que a mesa já pediu antes.
function renderizarItensEnviados() {
    const area = pegar("itens-enviados");
    const pedido = mesaSelecionada ? pedidoDaMesa(mesaSelecionada) : null;

    if (!pedido) {
        area.hidden = true;
        return;
    }

    limpar(area);
    area.hidden = false;
    area.appendChild(el("strong", {texto: "Já enviado (" + pedido.status + ")"}));
    pedido.itens.forEach(function (item) {
        area.appendChild(el("div", {class: "linha-enviada"},
            el("span", {texto: item.quantidade + "x " + item.nome}),
            el("span", {texto: dinheiro.format(item.preco * item.quantidade)})
        ));
    });
}

async function enviarPedido() {
    if (!mesaSelecionada) {
        mostrarMensagem("Primeiro escolha uma mesa.", true);
        return;
    }
    if (carrinho.length === 0) {
        mostrarMensagem("Adicione pelo menos um item à comanda.", true);
        return;
    }

    const botao = pegar("enviar-pedido");
    botao.disabled = true;
    const resultado = await api("/api/pedidos", {mesa: mesaSelecionada, itens: carrinho});

    if (!resultado.ok) {
        mostrarMensagem(resultado.dados.erro || "Não foi possível enviar o pedido.", true);
        botao.disabled = false;
        return;
    }

    mostrarMensagem(resultado.dados.mensagem);
    carrinho = [];
    await carregarDados(true);
}

/* ---------- 7. Quadro de pedidos (status e cancelamento) ---------- */
function renderizarQuadro() {
    const area = pegar("quadro-pedidos");
    const colunas = [
        {status: "Em preparo", classe: "preparo", titulo: "Em preparo"},
        {status: "Pronto", classe: "pronto", titulo: "Prontos para entregar"},
        {status: "Entregue", classe: "entregue", titulo: "Entregues"}
    ];

    const emAndamento = dadosSistema.pedidos.filter(function (p) { return p.status === "Em preparo" || p.status === "Pronto"; });
    const contador = pegar("contador-pedidos");
    contador.hidden = emAndamento.length === 0;
    contador.textContent = emAndamento.length;

    limpar(area);
    colunas.forEach(function (coluna) {
        const pedidos = dadosSistema.pedidos.filter(function (p) { return p.status === coluna.status; });
        const lista = el("div", {class: "coluna-lista"});

        if (pedidos.length === 0) {
            lista.appendChild(el("div", {class: "sem-registro", texto: "Nenhum pedido aqui."}));
        }
        pedidos.forEach(function (pedido) {
            lista.appendChild(criarCartaoPedido(pedido));
        });

        area.appendChild(el("section", {class: "coluna " + coluna.classe, "aria-label": coluna.titulo},
            el("div", {class: "coluna-topo"},
                el("h2", {texto: coluna.titulo}),
                el("span", {texto: pedidos.length})
            ),
            lista
        ));
    });
}

function criarCartaoPedido(pedido) {
    const acoes = el("div", {class: "cartao-acoes"});

    if (pedido.status === "Em preparo") {
        acoes.appendChild(el("button", {
            type: "button",
            class: "botao botao-principal",
            texto: "Marcar como pronto",
            onclick: function () { atualizarStatus(pedido.numero, "Pronto"); }
        }));
        acoes.appendChild(el("button", {
            type: "button",
            class: "botao botao-texto",
            texto: "Cancelar pedido",
            onclick: function () { abrirDialogoCancelamento(pedido); }
        }));
    }
    if (pedido.status === "Pronto") {
        acoes.appendChild(el("button", {
            type: "button",
            class: "botao botao-principal",
            texto: "Marcar como entregue",
            onclick: function () { atualizarStatus(pedido.numero, "Entregue"); }
        }));
    }

    return el("article", {class: "cartao"},
        el("div", {class: "cartao-topo"},
            el("h3", {texto: "Mesa " + pedido.mesa}),
            el("span", {class: "cartao-numero", texto: "Pedido " + pedido.numero})
        ),
        el("ul", null, pedido.itens.map(function (item) {
            return el("li", null, el("b", {texto: item.quantidade + "x"}), item.nome);
        })),
        el("div", {class: "cartao-rodape"},
            el("span", {class: "etiqueta " + classeStatus(pedido.status), texto: pedido.status}),
            el("strong", {class: "preco", texto: dinheiro.format(pedido.total)})
        ),
        pedido.status === "Entregue"
            ? el("p", {class: "cartao-nota", texto: "Aguardando pagamento no caixa."})
            : null,
        acoes
    );
}

async function atualizarStatus(numero, status) {
    const resultado = await api("/api/pedidos/" + numero + "/status", {status: status});
    mostrarMensagem(resultado.dados.mensagem || resultado.dados.erro, !resultado.ok);
    if (resultado.ok) await carregarDados(true);
}

/* ---------- 8. Diálogo de cancelamento (POST /api/pedidos/<n>/cancelar) ---------- */
function prepararDialogoCancelamento() {
    const dialogo = pegar("modal-cancelar");
    const campo = pegar("motivo-cancelamento");

    campo.addEventListener("input", validarMotivo);
    pegar("cancelar-fechar").addEventListener("click", function () { dialogo.close(); });
    pegar("form-cancelar").addEventListener("submit", function (evento) {
        evento.preventDefault();
        confirmarCancelamento();
    });
}

function validarMotivo() {
    const tamanho = pegar("motivo-cancelamento").value.trim().length;
    const valido = tamanho >= 5 && tamanho <= 200;
    pegar("motivo-contador").textContent = pegar("motivo-cancelamento").value.length + "/200";
    pegar("cancelar-confirmar").disabled = !valido;
    pegar("motivo-ajuda").classList.toggle("invalido", tamanho > 0 && !valido);
    return valido;
}

function abrirDialogoCancelamento(pedido) {
    pedidoParaCancelar = pedido;
    pegar("modal-descricao").textContent =
        "Mesa " + pedido.mesa + ", pedido " + pedido.numero + ". Os itens voltam para o estoque e a mesa é liberada.";
    pegar("motivo-cancelamento").value = "";
    validarMotivo();
    pegar("modal-cancelar").showModal();
    pegar("motivo-cancelamento").focus();
}

async function confirmarCancelamento() {
    if (!pedidoParaCancelar || !validarMotivo()) return;

    const numero = pedidoParaCancelar.numero;
    const motivo = pegar("motivo-cancelamento").value.trim();
    const resultado = await api("/api/pedidos/" + numero + "/cancelar", {motivo: motivo});

    mostrarMensagem(resultado.dados.mensagem || resultado.dados.erro, !resultado.ok);
    if (resultado.ok) {
        pegar("modal-cancelar").close();
        pedidoParaCancelar = null;
        await carregarDados(true);
    }
}

/* ---------- 9. Tela do caixa ---------- */
function renderizarCaixa() {
    pegar("caixa-total").textContent = dinheiro.format(dadosSistema.caixa.total_vendido);
    pegar("caixa-vendas").textContent = dadosSistema.caixa.quantidade_vendas;
    pegar("caixa-abertas").textContent = dadosSistema.pedidos.length;

    const area = pegar("lista-contas");
    limpar(area);

    if (dadosSistema.pedidos.length === 0) {
        area.appendChild(el("div", {class: "sem-registro", texto: "Nenhuma conta em aberto no momento."}));
        return;
    }

    dadosSistema.pedidos.forEach(function (pedido) {
        area.appendChild(criarConta(pedido));
    });
}

function criarConta(pedido) {
    const escolhida = pagamentoEscolhido[pedido.numero] || "";
    const botaoFinalizar = el("button", {
        type: "button",
        class: "botao botao-principal",
        texto: "Finalizar conta",
        disabled: !escolhida,
        onclick: function () { finalizarConta(pedido.numero); }
    });

    const opcoes = FORMAS_PAGAMENTO.map(function (forma) {
        const id = "pg-" + pedido.numero + "-" + forma;
        return el("label", {"for": id},
            el("input", {
                type: "radio",
                id: id,
                name: "pagamento-" + pedido.numero,
                value: forma,
                checked: forma === escolhida,
                onchange: function () {
                    pagamentoEscolhido[pedido.numero] = forma;
                    botaoFinalizar.disabled = false;
                }
            }),
            el("span", {texto: forma})
        );
    });

    return el("article", {class: "conta"},
        el("div", {class: "conta-topo"},
            el("h3", {texto: "Mesa " + pedido.mesa}),
            el("span", {class: "etiqueta " + classeStatus(pedido.status), texto: pedido.status})
        ),
        el("ul", null, pedido.itens.map(function (item) {
            return el("li", null,
                el("span", {texto: item.quantidade + "x " + item.nome}),
                el("span", {class: "preco", texto: dinheiro.format(item.preco * item.quantidade)})
            );
        })),
        el("div", {class: "conta-total"},
            el("span", {texto: "Total"}),
            el("strong", {texto: dinheiro.format(pedido.total)})
        ),
        el("fieldset", {class: "pagamento"},
            el("legend", {texto: "Forma de pagamento"}),
            el("div", {class: "pagamento-opcoes"}, opcoes)
        ),
        botaoFinalizar
    );
}

async function finalizarConta(numero) {
    const forma = pagamentoEscolhido[numero];
    if (!forma) {
        mostrarMensagem("Escolha a forma de pagamento.", true);
        return;
    }

    const resultado = await api("/api/pedidos/" + numero + "/finalizar", {forma_pagamento: forma});
    mostrarMensagem(resultado.dados.mensagem || resultado.dados.erro, !resultado.ok);
    if (resultado.ok) {
        delete pagamentoEscolhido[numero];
        await carregarDados(true);
    }
}

/* ---------- 10. Tela do gerente ---------- */
function renderizarGerente() {
    pegar("gerente-total").textContent = dinheiro.format(dadosSistema.caixa.total_vendido);
    pegar("ticket-medio").textContent = dinheiro.format(dadosSistema.caixa.ticket_medio);

    const baixos = dadosSistema.estoque.filter(function (item) { return item.baixo; }).length;
    pegar("estoque-baixo").textContent = plural(baixos, "item", "itens");
    pegar("indicador-estoque").classList.toggle("alerta", baixos > 0);

    const marcador = pegar("contador-estoque");
    marcador.hidden = baixos === 0;
    marcador.textContent = baixos;

    renderizarEstoque();
    renderizarFormas();
    renderizarVendas();
    preencherSelectReposicao();
}

function preencherSelectReposicao() {
    const select = pegar("produto-reposicao");
    const anterior = select.value;
    limpar(select);
    dadosSistema.estoque.forEach(function (item) {
        select.appendChild(el("option", {value: item.nome, texto: item.nome}));
    });
    if (anterior) select.value = anterior;
}

function renderizarEstoque() {
    if (!dadosSistema) return;

    const filtro = pegar("filtro-estoque").value;
    const area = pegar("tabela-estoque");
    const itens = dadosSistema.estoque.filter(function (item) { return filtro === "todos" || item.baixo; });
    const maior = Math.max(30, ...dadosSistema.estoque.map(function (i) { return i.quantidade; }));

    limpar(area);
    itens.forEach(function (item) {
        const porcentagem = Math.min(100, Math.round((item.quantidade / maior) * 100));
        area.appendChild(el("tr", null,
            el("td", null, el("strong", {texto: item.nome})),
            el("td", null,
                el("div", {class: "barra-estoque" + (item.baixo ? " baixo" : "")},
                    el("i", null, el("b", {style: "width:" + porcentagem + "%"})),
                    el("span", {texto: item.quantidade + " " + item.unidade})
                )
            ),
            el("td", {texto: item.estoque_minimo + " " + item.unidade}),
            el("td", null, el("span", {class: "situacao" + (item.baixo ? " baixo" : ""), texto: item.baixo ? "Estoque baixo" : "Normal"}))
        ));
    });

    if (itens.length === 0) {
        area.appendChild(el("tr", null, el("td", {colspan: "4", class: "sem-registro", texto: "Nenhum produto com estoque baixo."})));
    }
}

// Soma as vendas por forma de pagamento (cálculo feito aqui, com os dados de /api/dados).
function renderizarFormas() {
    const area = pegar("lista-formas");
    limpar(area);

    if (dadosSistema.vendas.length === 0) {
        area.appendChild(el("div", {class: "sem-registro", texto: "As vendas aparecem aqui depois da primeira conta finalizada."}));
        return;
    }

    const totais = {};
    FORMAS_PAGAMENTO.forEach(function (forma) { totais[forma] = 0; });
    dadosSistema.vendas.forEach(function (venda) {
        totais[venda.forma_pagamento] = (totais[venda.forma_pagamento] || 0) + venda.total;
    });
    const soma = Object.values(totais).reduce(function (a, b) { return a + b; }, 0);

    Object.keys(totais).forEach(function (forma) {
        const parte = soma > 0 ? Math.round((totais[forma] / soma) * 100) : 0;
        area.appendChild(el("div", {class: "forma-linha"},
            el("div", {class: "forma-topo"},
                el("span", {texto: forma}),
                el("span", {texto: dinheiro.format(totais[forma])})
            ),
            el("div", {class: "forma-barra", role: "img", "aria-label": forma + ": " + parte + "% do faturamento"},
                el("b", {style: "width:" + parte + "%"})
            )
        ));
    });
}

function renderizarVendas() {
    const area = pegar("lista-vendas");
    limpar(area);

    if (dadosSistema.vendas.length === 0) {
        area.appendChild(el("div", {class: "sem-registro", texto: "Nenhuma venda finalizada hoje."}));
        return;
    }

    dadosSistema.vendas.slice().reverse().forEach(function (venda) {
        area.appendChild(el("div", {class: "venda"},
            el("div", null,
                el("strong", {texto: "Pedido " + venda.numero + ", mesa " + venda.mesa}),
                el("small", {texto: "Pago em " + venda.forma_pagamento})
            ),
            el("strong", {texto: dinheiro.format(venda.total)})
        ));
    });
}

async function reporEstoque() {
    const nome = pegar("produto-reposicao").value;
    const quantidade = Number(pegar("quantidade-reposicao").value);

    if (!nome || !Number.isInteger(quantidade) || quantidade < 1) {
        mostrarMensagem("Informe um produto e uma quantidade inteira maior que zero.", true);
        return;
    }

    const resultado = await api("/api/estoque/entrada", {nome: nome, quantidade: quantidade});
    mostrarMensagem(resultado.dados.mensagem || resultado.dados.erro, !resultado.ok);
    if (resultado.ok) await carregarDados(true);
}

/* ---------- 11. Aviso na tela e saída do sistema ---------- */
let temporizadorAviso = null;

function mostrarMensagem(texto, erro) {
    const aviso = pegar("mensagem");
    aviso.textContent = texto;
    aviso.className = "aviso" + (erro ? " erro" : "");
    aviso.hidden = false;

    clearTimeout(temporizadorAviso);
    temporizadorAviso = setTimeout(function () { aviso.hidden = true; }, 4000);
}

async function sair() {
    const resultado = await api("/api/sair", {});
    if (resultado.ok) window.location.href = "/login";
}
