# Sistema de Classificação de Documentos Contábeis/Fiscais e Coleta de Dados de Checklist

Este repositório contém dois scripts Python que trabalham em conjunto para automatizar a coleta, classificação e organização de documentos relacionados a documentos contábeis e fiscais. O `checklist_coletor_dados.py` é responsável por extrair dados de pendências de uma API interna, enquanto o `organizador_arquivos_contabeis-fiscais.py` lida com a descompactação, extração de texto, classificação inteligente e organização de diversos tipos de documentos em uma estrutura de pastas padronizada.

## Visão Geral do Projeto

O objetivo principal deste sistema é otimizar o fluxo de trabalho de gerenciamento de documentos, reduzindo a necessidade de intervenção manual na organização e categorização de arquivos. Ele é especialmente útil para empresas que lidam com um grande volume de documentos digitais, como notas fiscais, extratos bancários, boletos e outros comprovantes, garantindo que sejam armazenados de forma lógica e acessível.

### Componentes Principais:

1.  **`checklist_coletor_dados.py`**: Um script focado na extração de dados de pendências de uma API RESTful interna. Ele foi projetado para ser robusto, com tratamento de erros e retentativas para garantir a coleta de dados mesmo em condições de rede instáveis. Os dados coletados são salvos em formato JSON para posterior análise ou integração.

2.  **`organizador_arquivos_contabeis-fiscais.py`**: Este é o coração do sistema de classificação. Ele processa arquivos de diversas fontes (incluindo compactados), extrai texto usando diferentes técnicas (OCR para imagens e PDFs escaneados, leitura direta para outros formatos), e então aplica um conjunto de regras inteligentes para classificar cada documento em categorias predefinidas. Após a classificação, os arquivos são movidos para uma estrutura de diretórios organizada por cliente, ano, mês e tipo de documento.

## `checklist_coletor_dados.py` - Coletor de Dados de Pendências

### Descrição Detalhada

O script `checklist_coletor_dados.py` é uma ferramenta especializada para interagir com uma API interna (`http://intranetmg:1010/services/checklist/api/pendencias/ListarPendencias`) e extrair informações sobre pendências. Ele é configurado para buscar dados de serviços específicos (atualmente 'EF' e 'CTB') para um determinado mês e ano. A principal característica deste coletor é sua resiliência, implementando um mecanismo de retentativas com timeouts progressivos para lidar com falhas de rede ou lentidão da API.

### Funcionalidades:

*   **Extração de Dados da API**: Conecta-se a uma API RESTful para obter listas de pendências.
*   **Tratamento de Erros Robusto**: Implementa múltiplas tentativas de requisição com timeouts crescentes (5, 7.5, 10 minutos) para superar problemas de conexão ou lentidão da API.
*   **Extração Seletiva de Campos**: Configurado para extrair campos específicos (`obrigacaoDescricao`, `idCliente`, `tipo`) dos dados JSON retornados pela API.
*   **Organização de Saída**: Salva os dados extraídos em arquivos JSON separados por tipo de serviço, com nomes de arquivo que incluem timestamp para evitar sobrescrita e facilitar o rastreamento.
*   **Relatórios de Resumo**: Fornece um resumo detalhado da extração para cada serviço e um resumo geral ao final, incluindo o número total de registros e o status de processamento.
*   **Estrutura de Pastas**: Cria automaticamente uma pasta `dados_extraidos` para armazenar os arquivos JSON resultantes.

### Como Funciona:

1.  **Inicialização**: A classe `PendenciasExtractor` é instanciada, configurando a URL base da API, os campos a serem extraídos e a pasta de saída.
2.  **Criação de Pasta**: Verifica e cria a pasta `dados_extraidos` se ela ainda não existir.
3.  **Requisição HTTP com Retentativas**: O método `fazer_requisicao` tenta acessar a API. Em caso de `ReadTimeout` ou `RequestException`, ele aguarda e tenta novamente com um timeout maior, até um máximo de 3 tentativas.
4.  **Extração de Campos**: O método `extrair_campos` processa a resposta JSON da API. Ele é flexível o suficiente para lidar com respostas que são listas ou dicionários, procurando por chaves comuns (`items`, `data`, `pendencias`, etc.) que contenham os dados reais. Para cada item, ele extrai os campos definidos e adiciona um `tipoServico`.
5.  **Processamento de Serviço**: O método `processar_servico` orquestra a chamada à API e a extração de dados para um tipo de serviço específico (ex: 'EF', 'CTB'). Ele encapsula os dados extraídos com metadados como data de extração, URL e status.
6.  **Salvamento JSON**: Os dados processados são salvos em um arquivo JSON na pasta `dados_extraidos`. O nome do arquivo é gerado dinamicamente com base no tipo de serviço, ano, mês e um timestamp.
7.  **Exibição de Resumo**: Após cada serviço, um resumo é exibido, mostrando o status, o número de registros extraídos e estatísticas básicas como clientes e tipos únicos. Ao final, um resumo geral consolida os resultados de todos os serviços.

### Dependências:

*   `requests`: Para fazer requisições HTTP.
*   `json`: Para trabalhar com dados JSON.
*   `os`: Para operações de sistema de arquivos (criação de pastas, manipulação de caminhos).
*   `datetime`: Para manipulação de datas e timestamps.
*   `typing`: Para anotações de tipo (opcional, mas boa prática).

Para instalar as dependências, execute:

```bash
pip install requests
```

### Como Executar:

Basta executar o script Python diretamente:

```bash
python checklist_coletor_dados.py
```

O script imprimirá o progresso no console e salvará os arquivos JSON na pasta `dados_extraidos` (criada no mesmo diretório do script, se não existir).

## `organizador_arquivos_contabeis-fiscais.py` - Classificador e Organizador de Documentos

### Descrição Detalhada

O `organizador_arquivos_contabeis-fiscais.py` é um sistema abrangente para automatizar a classificação e organização de documentos digitais. Ele é capaz de processar uma vasta gama de formatos de arquivo, incluindo PDFs, imagens, documentos do Office (DOCX, XLSX), XML, HTML, TXT, CSV e até mesmo arquivos compactados (ZIP, RAR). O script utiliza técnicas avançadas de extração de texto, incluindo OCR para conteúdo não textual, e um motor de classificação baseado em regras e palavras-chave para categorizar os documentos. Após a classificação, os arquivos são movidos para uma estrutura de pastas hierárquica, facilitando a recuperação e o gerenciamento.

### Funcionalidades:

*   **Descompactação Automática**: Extrai o conteúdo de arquivos `.zip` e `.rar` recursivamente.
*   **Extração de Texto Multi-formato**: Suporta extração de texto de:
    *   **PDFs**: Leitura direta de texto e OCR (via `textract` e Tesseract) para PDFs escaneados ou baseados em imagem.
    *   **Imagens**: OCR (via Tesseract) para JPG, JPEG, PNG, TIFF, TIF, BMP.
    *   **Documentos Office**: DOCX (via `docx2txt`), XLSX/XLS (via `pandas`).
    *   **Web/Estruturados**: XML, HTML (leitura direta e parsing básico).
    *   **Texto Plano**: TXT, CSV, OFX, OFC.
*   **Classificação Inteligente de Documentos**: Utiliza um conjunto de regras e palavras-chave (com pesos e indicadores positivos/negativos) para classificar documentos em categorias como:
    *   Nota Fiscal Eletrônica (com subtipos ENTRADA, SAIDA, SERVIÇO, NOTA DE DÉBITO)
    *   Extrato Bancário (com subtipos CONTA CORRENTE, APLICAÇÃO FINANCEIRA)
    *   Boleto de Pagamento
    *   DACTE (com subtipos ENTRADA, SAIDA)
    *   SPED Fiscal
    *   Relatório de Faturamento
    *   Fatura de Serviços
    *   Outros (COMPROVANTES, INFORME DE RENDIMENTOS, RELATÓRIOS, SPEDs)
    *   `REVISÃO MANUAL` para documentos não classificados automaticamente.
*   **Extração de CNPJ do Caminho**: Identifica o CNPJ do cliente a partir da estrutura de diretórios para auxiliar na organização.
*   **Estrutura de Pastas Dinâmica**: Cria automaticamente uma hierarquia de pastas baseada em `[ANO]/[MÊS - NOME_DO_MÊS]/[TIPO_DOCUMENTO]/[SUBTIPO_DOCUMENTO]`.
*   **Movimentação e Organização de Arquivos**: Move os arquivos processados para suas respectivas pastas classificadas, mantendo o diretório original limpo.
*   **Registro de Atividades (Logging)**: Gera um arquivo de log (`document_classifier.log`) detalhando o processo de extração, classificação e movimentação de cada arquivo, útil para depuração e auditoria.

### Como Funciona:

1.  **Configuração Inicial**: Define o `BASE_PATH` (diretório raiz para processamento) e o caminho para o executável do Tesseract OCR e WinRAR (para RAR).
2.  **Varredura de Diretórios**: O script percorre recursivamente o `BASE_PATH`, identificando todos os arquivos a serem processados.
3.  **Descompactação**: Se um arquivo compactado (`.zip` ou `.rar`) for encontrado, ele é descompactado em um diretório temporário, e seus conteúdos são adicionados à fila de processamento.
4.  **Extração de Texto**: Para cada arquivo, o `extract_text` tenta extrair seu conteúdo textual. Ele usa bibliotecas específicas para cada tipo de arquivo e recorre ao OCR (Tesseract) para imagens e PDFs escaneados.
5.  **Classificação**: O texto extraído (e o nome do arquivo) são passados para a função `classify_document`. Esta função aplica um conjunto de regras complexas, incluindo:
    *   **Regras por Extensão/Formato**: Prioriza a classificação baseada em extensões de arquivo específicas (ex: `.ofx` para extratos).
    *   **Palavras-chave e Padrões Regex**: Busca por termos e padrões regex no conteúdo e nome do arquivo para identificar o tipo de documento (ex: 


    `danfe` para Nota Fiscal).
    *   **Análise de Estrutura (para XML/HTML)**: Para Notas Fiscais e DACTEs em XML, ele tenta ler tags específicas (`<tpNF>`) para determinar o tipo (entrada/saída).
    *   **Análise de Colunas (para Excel)**: Para arquivos Excel, ele pode inferir o tipo de documento com base no número de colunas (ex: poucas colunas para boletos, muitas para relatórios financeiros).
    *   **Extração de CNPJ**: O CNPJ do cliente é extraído do caminho do arquivo para ajudar na classificação e organização.
6.  **Organização de Pastas**: Com base na classificação, o script determina o caminho final do arquivo na estrutura de pastas. Ele cria as pastas necessárias (Ano, Mês, Tipo de Documento, Subtipo) se elas não existirem.
7.  **Movimentação**: O arquivo original é movido para sua pasta classificada. Se o arquivo não puder ser classificado, ele é movido para a pasta `REVISÃO MANUAL`.
8.  **Registro**: Todas as etapas são registradas no arquivo `document_classifier.log`, fornecendo um histórico detalhado do processamento de cada arquivo.

### Dependências:

*   `os`: Operações de sistema de arquivos.
*   `re`: Expressões regulares.
*   `shutil`: Operações de alto nível em arquivos e coleções de arquivos.
*   `zipfile`: Para trabalhar com arquivos ZIP.
*   `rarfile`: Para trabalhar com arquivos RAR (requer o executável do WinRAR/UnRAR instalado e configurado).
*   `datetime`: Manipulação de datas e horas.
*   `pandas`: Leitura e manipulação de dados de Excel.
*   `xml.etree.ElementTree`: Parsing de arquivos XML.
*   `pathlib`: Manipulação de caminhos de arquivo de forma orientada a objetos.
*   `PyPDF2`: Leitura de PDFs (texto).
*   `textract`: Extração de texto de vários formatos, incluindo OCR para PDFs.
*   `docx2txt`: Extração de texto de arquivos DOCX.
*   `pytesseract`: Interface Python para o Tesseract OCR (requer Tesseract instalado e configurado).
*   `PIL (Pillow)`: Processamento de imagens para OCR.
*   `logging`: Geração de logs.
*   `mimetypes`, `magic`: Identificação do tipo MIME de arquivos (requer `python-magic-bin` no Windows).
*   `time`: Funções relacionadas a tempo.
*   `dateutil`: Parsing de datas.

Para instalar as dependências, execute:

```bash
pip install pandas openpyxl PyPDF2 textract docx2txt pytesseract Pillow python-magic-bin rarfile
```

**Observações sobre `rarfile` e `pytesseract`:**

*   **`rarfile`**: Este módulo requer que o executável `UnRAR.exe` (parte do WinRAR) esteja instalado no seu sistema e que o caminho para ele seja configurado na variável `rarfile.UNRAR_TOOL` no script. Ex: `rarfile.UNRAR_TOOL = r"C:\Program Files\WinRAR\UnRAR.exe"`.
*   **`pytesseract`**: Este módulo requer que o Tesseract OCR esteja instalado no seu sistema. O caminho para o executável `tesseract.exe` deve ser configurado na variável `pytesseract.pytesseract.tesseract_cmd` no script. Ex: `pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"`.

### Como Executar:

1.  **Configuração**: Edite o script `organizador_arquivos_contabeis-fiscais.py` e ajuste as variáveis `BASE_PATH`, `rarfile.UNRAR_TOOL` e `pytesseract.pytesseract.tesseract_cmd` para refletir os caminhos corretos em seu ambiente.
2.  **Execução**: Execute o script Python diretamente:

    ```bash
    python organizador_arquivos_contabeis-fiscais.py
    ```

O script iniciará o processamento dos arquivos no `BASE_PATH`, imprimirá o progresso no console e registrará as atividades em `document_classifier.log`.

## Considerações Finais

Este sistema representa uma solução robusta para a automação da gestão de documentos. A combinação de coleta de dados de API e classificação inteligente de arquivos oferece uma poderosa ferramenta para otimizar processos e garantir a organização de informações críticas. A modularidade dos scripts permite que sejam adaptados e estendidos para atender a necessidades específicas, como a integração com outros sistemas ou a adição de novas regras de classificação.

### Autor:
Lauro Bonometti
