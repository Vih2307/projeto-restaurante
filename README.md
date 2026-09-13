Restaurante

Projeto acadêmico desenvolvido para representar um sistema de atendimento presencial de um restaurante. O sistema permite controlar as mesas, registrar os pedidos feitos pelos garçons, finalizar as contas no caixa, atualizar o estoque e acompanhar o faturamento da loja.

Alunos responsáveis

Bruno Ferreira

Kennedy Fernando

Vinicius dos Anjos

Objetivo do projeto

O objetivo é facilitar o atendimento dentro do restaurante e organizar as principais atividades realizadas pelos funcionários. Cada área possui uma tela própria, mas todas utilizam os mesmos dados de mesas, pedidos, produtos, vendas e estoque.

O sistema foi dividido em três áreas principais:

Tela do garçom.

Tela do caixa.

Tela do gerente.

Funcionalidades desenvolvidas

Tela do garçom

Na tela do garçom é possível:

visualizar as mesas livres e ocupadas;

selecionar a mesa que está sendo atendida;

consultar o cardápio separado por categorias;

adicionar produtos ao pedido;

aumentar ou diminuir a quantidade dos produtos;

visualizar o valor total do pedido;

enviar o pedido para o sistema;

adicionar novos produtos a uma mesa que já possui uma conta aberta.

Quando o primeiro pedido de uma mesa é enviado, ela muda do estado Livre para Ocupada. Caso o cliente faça outro pedido, os novos itens são adicionados na mesma conta.

Tela do caixa

Na tela do caixa é possível:

visualizar todas as contas que ainda estão abertas;

conferir o número do pedido e da mesa;

consultar os produtos consumidos;

visualizar o valor total da conta;

escolher a forma de pagamento;

finalizar a venda;

acompanhar o total vendido e a quantidade de vendas.

As formas de pagamento disponíveis são:

Dinheiro;

PIX;

Débito;

Crédito.

Depois que o pagamento é registrado, o pedido recebe o estado Finalizado, a venda é somada ao faturamento e a mesa volta a ficar livre.

Tela do gerente

Na tela do gerente é possível:

visualizar o faturamento total;

consultar a quantidade de vendas realizadas;

acompanhar o ticket médio das vendas;

consultar as últimas vendas;

verificar a quantidade disponível de cada produto;

identificar produtos com estoque baixo;

filtrar somente os produtos que precisam de reposição;

registrar a entrada de novas unidades no estoque.

O sistema considera que um produto está com estoque baixo quando sua quantidade é menor ou igual ao estoque mínimo cadastrado.

Cardápio

O cardápio está dividido nas seguintes categorias:

Entradas;

Pratos principais;

Bebidas;

Sobremesas.

Os produtos e preços estão cadastrados no arquivo categoria.py. O front-end recebe essas informações do sistema e monta o cardápio automaticamente.

Tecnologias utilizadas

Python;

Flask;

HTML5;

CSS3;

JavaScript;

Programação Orientada a Objetos.

O Flask faz a comunicação entre a interface e as classes Python. O HTML cria a estrutura das telas, o CSS cuida da aparência e o JavaScript envia e recebe os dados sem precisar atualizar a página inteira.

Estrutura do projeto

projeto-restaurante/
├── app.py
├── caixa.py
├── categoria.py
├── estoque.py
├── mesa.py
├── pedido.py
├── requirements.txt
├── test_app.py
├── static/
│   ├── script.js
│   └── style.css
└── templates/
    └── index.html

Explicação dos arquivos

Arquivo

Função

app.py

Inicia o sistema, cria as rotas e conecta a interface às classes Python.

caixa.py

Controla a abertura do caixa, as vendas e o faturamento.

categoria.py

Armazena os produtos, categorias e preços do cardápio.

estoque.py

Controla as quantidades, entradas, saídas e alertas de estoque baixo.

mesa.py

Controla o número e a situação de cada mesa.

pedido.py

Armazena os itens, quantidades, total, pagamento e estado do pedido.

templates/index.html

Contém a estrutura das três telas do sistema.

static/style.css

Contém a aparência e a adaptação das telas para diferentes tamanhos.

static/script.js

Controla as ações dos botões e a comunicação com o Flask.

test_app.py

Testa a abertura da página e o fluxo de uma venda.

Como executar o projeto

Clonar o repositório
git clone https://github.com/Vih2307/projeto-restaurante.git

Entrar na pasta
cd projeto-restaurante

Instalar as dependências
pip install -r requirements.txt

Iniciar o sistema
python app.py

Abrir no navegador
Acesse o seguinte endereço:

http://127.0.0.1:5000

Fluxo de utilização

O garçom seleciona uma mesa.

O garçom adiciona os produtos e envia o pedido.

A mesa fica ocupada e a quantidade dos produtos é retirada do estoque.

O caixa consulta a conta da mesa.

O caixa escolhe a forma de pagamento e finaliza a venda.

O valor é adicionado ao faturamento.

A mesa volta a ficar disponível.

O gerente pode consultar as vendas e verificar o estoque atualizado.

Testes

Para executar os testes do projeto, utilize:

python -m unittest -v

Os testes verificam se a página inicial abre corretamente e se o fluxo de criação e finalização de uma venda está funcionando.

Situação atual do projeto

Até o momento, o sistema possui as três telas principais funcionando e integradas com as classes Python. Os pedidos alteram a situação das mesas, atualizam o estoque e são registrados no caixa quando o pagamento é finalizado.

Nesta versão, os dados ficam armazenados somente na memória do programa. Isso significa que pedidos, vendas, mesas e quantidades do estoque voltam aos valores iniciais quando o servidor é encerrado. Como melhoria futura, o projeto poderá receber um banco de dados, cadastro de usuários, controle de acesso por função e histórico permanente das vendas.
