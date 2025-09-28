# Huby App - Gerenciador de Contatos e Disparador WhatsApp

Uma aplicação de desktop construída em Python com Tkinter para gerenciar listas de contatos e automatizar o envio de mensagens no WhatsApp, utilizando a integração com o WPPConnect Server.

![Placeholder para Screenshot](https://i.imgur.com/g8e1BAb.png)
*(Recomenda-se substituir esta imagem por um screenshot real da aplicação em funcionamento)*

## Principais Funcionalidades

- **👨‍👩‍👧‍👦 Gerenciamento de Múltiplos Perfis**: Adicione e gerencie várias contas de WhatsApp. A aplicação salva as sessões para reconexão rápida.
- **📂 Carregamento de Listas CSV**: Importe facilmente suas listas de contatos a partir de arquivos `.csv`.
- **🤖 Envio Automático em Massa**: Inicie uma campanha de envio para uma lista de contatos, com intervalos de tempo aleatórios e configuráveis entre cada mensagem para simular o comportamento humano.
- **✍️ Envio Manual e Personalizado**:
    - Envie mensagens usando templates pré-carregados com um único clique (botão `W`).
    - Abra um painel para escrever e enviar mensagens personalizadas na hora (botão `Wpp`).
- **📝 Templates de Mensagem**: Carregue múltiplos arquivos `.txt` para usar como modelos de mensagem. A aplicação escolhe um aleatoriamente para cada envio, aumentando a variabilidade.
- **📞 Gerenciamento de Contatos**:
    - Edite o nome e o telefone de um contato diretamente na interface.
    - Adicione novos contatos à lista CSV ativa.
    - Atribua status pré-definidos (`Não atendeu`, `Sem interesse`, etc.) a cada contato.
- **🗒️ Observações e Histórico**:
    - Adicione anotações persistentes para cada contato.
    - Visualize o histórico recente das conversas do WhatsApp diretamente na aplicação.
- **🔎 Pesquisa e Ordenação**: Filtre sua lista de contatos por nome e ordene as colunas como desejar.
- **💾 Persistência de Estado**: A aplicação salva o último arquivo carregado, os templates de mensagem, a geometria da janela e o perfil ativo, para que você continue de onde parou.
- **📊 Relatório de Envios**: Ao final de uma campanha automática, gere um arquivo `.txt` com o resumo dos envios bem-sucedidos e das falhas.

## Pré-requisitos

Antes de executar a aplicação, você precisa ter o seguinte instalado e configurado:

1.  **Python 3.7+**: [Download Python](https://www.python.org/downloads/)
2.  **WPPConnect Server**: Esta aplicação **não se conecta diretamente ao WhatsApp**. Ela atua como um cliente para o WPPConnect Server, que é o responsável por criar a ponte com o WhatsApp Web.
    - Você precisa instalar e executar o servidor localmente. Siga as instruções no repositório oficial: [github.com/wppconnect-team/wppconnect-server](https://github.com/wppconnect-team/wppconnect-server)
    - Por padrão, a aplicação tentará se conectar ao servidor no endereço `http://localhost:21465`. Certifique-se de que seu servidor esteja rodando nesta porta.

## Instalação e Configuração

1.  **Clone o repositório:**
    ```bash
    git clone [https://github.com/seu-usuario/seu-repositorio.git](https://github.com/seu-usuario/seu-repositorio.git)
    cd seu-repositorio
    ```

2.  **Instale as dependências Python:**
    A única dependência externa é a biblioteca `requests`. Crie um arquivo `requirements.txt` com o seguinte conteúdo:
    ```
    requests
    ```
    Em seguida, instale-o usando o pip:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Inicie o WPPConnect Server:**
    Siga as instruções do projeto WPPConnect para iniciar o servidor. Você verá logs no seu terminal, incluindo um QR Code para escanear na primeira vez.

4.  **Execute a Aplicação:**
    ```bash
    python huby.py
    ```

## Como Usar

1.  **Adicionar um Perfil**:
    - Clique no botão `+` ao lado do menu de perfis.
    - Dê um nome para o seu perfil (ex: "Trabalho", "Pessoal").

2.  **Conectar ao WhatsApp**:
    - Com o perfil desejado selecionado, clique em **"Conectar"**.
    - Vá até o terminal onde o **WPPConnect Server** está rodando. Um QR Code será exibido.
    - Abra o WhatsApp no seu celular, vá em "Aparelhos conectados" e escaneie o QR Code.
    - O botão na aplicação mudará para **"Desconectar"**, indicando que a sessão está ativa.

3.  **Carregar Contatos**:
    - Clique em **"LOAD"** e selecione um arquivo `.csv`.
    - O formato esperado do CSV é: `Nome, [coluna_opcional], Telefone, Status` (sem cabeçalho na primeira linha ou com a aplicação pulando-o).

4.  **Carregar Templates de Mensagem**:
    - Clique em **"TXT"** e selecione um ou mais arquivos de texto (`.txt`).
    - Em seus arquivos de texto, use a tag `[nome]` onde você quer que o primeiro nome do contato seja inserido. Ex: `Olá, [nome]! Tudo bem?`.

5.  **Enviar Mensagens**:
    - **Manualmente (Template)**: Selecione um contato na lista e clique no botão **`W`** (ou use o atalho `Alt+W`).
    - **Manualmente (Personalizada)**: Clique em **`Wpp`** para abrir o painel de mensagem. Digite sua mensagem, selecione um contato e clique no botão `>` (ou pressione `Enter`).
    - **Automaticamente**:
        1. Selecione o contato a partir do qual você deseja **iniciar** os envios.
        2. Configure o **Intervalo** mínimo e máximo de segundos entre os disparos.
        3. Clique em **"START"**. A aplicação começará a percorrer a lista, enviando as mensagens e atualizando o status.
        4. Para parar, clique em **"STOP"**.

## Estrutura de Arquivos

-   `huby.py`: O código-fonte principal da aplicação.
-   `config.json`: Criado automaticamente no primeiro fechamento. Armazena o estado da aplicação, como o caminho do último arquivo CSV, perfis, etc.
-   `comentarios.json`: Criado automaticamente. Armazena todas as observações adicionadas aos contatos, usando o número de telefone como chave.
-   `contatos.csv` (Exemplo):
    ```csv
    João da Silva,,11987654321,
    Maria Oliveira,,21912345678,Sem interesse
    Dr. Carlos Andrade,,31999998888,
    ```
-   `mensagem_1.txt` (Exemplo):
    ```
    Olá, [nome]. Como vai? Gostaria de falar sobre nossos novos serviços.
    ```

## Contribuições

Contribuições são bem-vindas! Se você tiver ideias para novas funcionalidades, melhorias ou correções de bugs, sinta-se à vontade para abrir uma *issue* ou enviar um *pull request*.

## Licença

Este projeto é distribuído sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.
