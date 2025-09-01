import os
import re
import shutil
import zipfile
import rarfile
import datetime
import pandas as pd
import xml.etree.ElementTree as ET
from pathlib import Path
import PyPDF2
import textract
import docx2txt
import pytesseract
from PIL import Image
import logging
import mimetypes
import magic
import time
from dateutil.parser import parse

# Configuração de log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("document_classifier.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

# Caminho base para processamento
BASE_PATH = r"C:\Users\laurob\Desktop\amostragem"

# Função para extrair texto de diferentes tipos de arquivos
def extract_text(file_path):
    """Extrai texto de diferentes tipos de arquivos."""
    try:
        file_extension = os.path.splitext(file_path)[1].lower()
        mime = magic.Magic(mime=True)
        mime_type = mime.from_file(file_path)
        
        # PDF
        if file_extension == '.pdf' or 'pdf' in mime_type:
            try:
                text = ""
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page_num in range(len(pdf_reader.pages)):
                        text += pdf_reader.pages[page_num].extract_text() + "\n"
                
                # Se o PDF não tiver texto extraível (scan), usar OCR
                if not text.strip():
                    text = textract.process(file_path, method='tesseract').decode('utf-8')
                return text
            except Exception as e:
                logger.error(f"Erro ao extrair texto do PDF {file_path}: {e}")
                return ""
        
        # XML
        elif file_extension == '.xml':
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
                return ET.tostring(root, encoding='utf-8').decode('utf-8')
            except Exception as e:
                logger.error(f"Erro ao extrair texto do XML {file_path}: {e}")
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    return file.read()
        # HTML
        elif file_extension == '.html':
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
                return ET.tostring(root, encoding='utf-8').decode('utf-8')
            except Exception as e:
                logger.error(f"Erro ao extrair texto do HTML {file_path}: {e}")
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    return file.read()
        
        # Excel
        elif file_extension in ['.xlsx', '.xls']:
            try:
                df = pd.read_excel(file_path)
                # Contar colunas
                num_columns = len(df.columns)
                # Converter DataFrame para string
                text = df.to_string()
                # Adicionar informação sobre número de colunas
                text = f"NUM_COLUMNS: {num_columns}\n" + text
                return text
            except Exception as e:
                logger.error(f"Erro ao extrair texto do Excel {file_path}: {e}")
                return ""
        
        # Texto plano
        elif file_extension in ['.txt', '.csv', '.html', '.xml']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                return file.read()
        
        # OFX/OFC (arquivos de extrato bancário)
        elif file_extension in ['.ofx', '.ofc']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                return file.read()
        
        # Imagens
        elif file_extension in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp']:
            try:
                return pytesseract.image_to_string(Image.open(file_path), lang='por')
            except Exception as e:
                logger.error(f"Erro ao extrair texto da imagem {file_path}: {e}")
                return ""
        
        # DOCX
        elif file_extension == '.docx':
            return docx2txt.process(file_path)
        
        # Outros tipos
        else:
            try:
                return textract.process(file_path).decode('utf-8')
            except:
                logger.warning(f"Não foi possível extrair texto de {file_path}")
                return ""
    except Exception as e:
        logger.error(f"Erro ao processar arquivo {file_path}: {e}")
        return ""

# Função para descompactar arquivos
def extract_compressed_files(file_path, extract_dir):
    """Descompacta arquivos ZIP e RAR."""
    try:
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.zip':
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            logger.info(f"Arquivo ZIP extraído: {file_path}")
            return True
        elif file_extension == '.rar':
            with rarfile.RarFile(file_path, 'r') as rar_ref:
                rar_ref.extractall(extract_dir)
            logger.info(f"Arquivo RAR extraído: {file_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"Erro ao descompactar {file_path}: {e}")
        return False

# Função para classificar documentos
def classify_document(file_path, file_content, file_name):
    """Classifica o documento com base no conteúdo e nome do arquivo."""
    
    # Normalizar conteúdo e nome para facilitar a busca
    content_lower = file_content.lower() if file_content else ""
    name_lower = file_name.lower()
    
    # Extrair extensão do arquivo
    file_extension = os.path.splitext(file_path)[1].lower()
    
    # Verificar número de colunas em tabelas (para Excel)
    num_columns = 0
    if "NUM_COLUMNS:" in file_content:
        match = re.search(r"NUM_COLUMNS: (\d+)", file_content)
        if match:
            num_columns = int(match.group(1))
    
    # Classificação por regras específicas
    
    # A. Classificação de "CONTA CORRENTE"
    if file_extension in ['.ofx', '.ofc']:
        return "EXTRATO", "CONTA CORRENTE"
    
    if num_columns <= 6 and num_columns > 0:
        if "extrato de conta" in content_lower or "lançamento" in content_lower:
            return "EXTRATO", "CONTA CORRENTE"
        if any(keyword in content_lower for keyword in ["Inter", "CC_", "CEF"]) and any(keyword in content_lower for keyword in ["Extrato Bradesco", "Extrato Inter", "Extrato Itau", "Extrato banco", "Extrato Bancario", "Saldo"]):
            return "EXTRATO", "CONTA CORRENTE"
    
        # Verificar se há 17 dias do mesmo mês no conteúdo
    months_pattern = r'(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)'
    if re.search(months_pattern, content_lower):
        # Implementação simplificada - na prática precisaria de uma análise mais detalhada
        return "EXTRATO", "CONTA CORRENTE"
    
    # B. Classificação de "APLICAÇÃO FINANCEIRA"
    if ("irrf" in content_lower and "i.r." in content_lower) and num_columns >= 7:
        return "EXTRATO", "APLICAÇÃO FINANCEIRA"
    
    if "cdb" in name_lower:
        return "EXTRATO", "APLICAÇÃO FINANCEIRA"
    
    # C. Classificação de "BOLETO"
    if num_columns <= 2 and num_columns > 0:
        if "extrato" not in content_lower:
            return "BOLETO", None
    
    # D. Classificação de "NOTA FISCAL"
    nf_keywords_content = [
        "danfe", "prefeitura", "nota fiscal", "nf", "nfe", "nf-e", "autnfe", 
        "tomador", "fornecedor", "classificação", "classificacao", 
        "documento auxiliar", "chave de acesso", "autorização de uso", "serie", 
        "danfse"
    ]
    nf_keywords_filename = ["nfe", "nf-e", "nf", "autnfe", "danfe", "-can"]

    if any(kw in content_lower for kw in nf_keywords_content) or any(kw in name_lower for kw in nf_keywords_filename):
        logger.info(f"[NF] Arquivo identificado como NOTA FISCAL: {file_name}")

        # Caso seja uma Nota de Débito
        if "nota de débito" in content_lower or "nota de debito" in content_lower:
            logger.info(f"[NF] Classificado como NOTA DE DEBITO")
            return "NOTA FISCAL", "NOTA DE DEBITO"

        # Verificação de tipo via tag <tpNF> para XML/HTML
        if file_extension in ['.xml', '.html']:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    raw_text = f.read()
                match = re.search(r"<tpNF>\s*(\d)\s*</tpNF>", raw_text)
                if match:
                    tpnf_value = match.group(1)
                    if tpnf_value == '1':
                        logger.info(f"[NF] Tag <tpNF> = 1 -> ENTRADA")
                        return "NOTA FISCAL", "ENTRADA"
                    elif tpnf_value == '0':
                        logger.info(f"[NF] Tag <tpNF> = 0 -> SAIDA")
                        return "NOTA FISCAL", "SAIDA"
            except Exception as e:
                logger.warning(f"[NF] Falha ao ler tag <tpNF>: {e}")

        # Verificações textuais
        entrada_patterns = [
            r'\bentrada\b',
            r'tipo\s*de\s*opera[çc][ãa]o\s*:\s*entrada',
            r'1\s*-\s*entrada'
        ]
        saida_patterns = [
            r'\bsa[íi]da\b',
            r'tipo\s*de\s*opera[çc][ãa]o\s*:\s*sa[íi]da',
            r'0\s*-\s*sa[íi]da'
        ]

        for pattern in entrada_patterns:
            if re.search(pattern, content_lower):
                logger.info(f"[NF] Conteúdo indica ENTRADA")
                return "NOTA FISCAL", "ENTRADA"

        for pattern in saida_patterns:
            if re.search(pattern, content_lower):
                logger.info(f"[NF] Conteúdo indica SAIDA")
                return "NOTA FISCAL", "SAIDA"

        logger.info(f"[NF] Nenhum padrão de entrada/saída detectado -> classificado como SERVIÇO")
        return "NOTA FISCAL", "SERVIÇO"

    # F. Classificação de "DACTE"
    dacte_keywords = ["dacte", "cte", "ct-e", "ct_e"]
    if any(kw in name_lower for kw in dacte_keywords) or any(kw in content_lower for kw in dacte_keywords):
        logger.info(f"[DACTE] Arquivo identificado como DACTE: {file_name}")

        if file_extension == '.xml':
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
                client_cnpj = extract_cnpj_from_path(file_path)
                for elem in root.iter():
                    if elem.tag.lower().endswith("emit"):
                        for sub in elem.iter():
                            if sub.tag.lower().endswith("cnpj"):
                                cnpj_emissor = sub.text.strip().replace(".", "").replace("/", "").replace("-", "")
                                if cnpj_emissor == client_cnpj:
                                    logger.info(f"[DACTE] Classificado como SAIDA (CNPJ emissor igual ao cliente): {file_name}")
                                    return "DACTE", "SAIDA"
                                else:
                                    logger.info(f"[DACTE] Classificado como ENTRADA (CNPJ emissor diferente): {file_name}")
                                    return "DACTE", "ENTRADA"
            except Exception as e:
                logger.warning(f"[DACTE] Erro ao processar XML: {e}")

        # Caso não consiga acessar XML ou não seja XML, assume ENTRADA como padrão seguro
        logger.info(f"[DACTE] Classificação padrão como ENTRADA (fallback): {file_name}")
        return "DACTE", "ENTRADA"

    # G. Classificação de "FATURA"
    fatura_keywords = ["fatura", "recibo", "energia", "light", "vivo", "claro", "tim", "água", "agua"]
    if (any(keyword in content_lower for keyword in fatura_keywords) or 
        any(keyword in name_lower for keyword in fatura_keywords)):
        # Verificar se não é "faturamento"
        if not any(word in content_lower for word in ["faturamento", "mento"]) and not any(word in name_lower for word in ["faturamento", "mento"]):
            return "FATURA", None
    
    # H. Classificação de "FATURAMENTO"
    faturamento_keywords = ["faturamento", "faturamento_"]
    if any(keyword in name_lower for keyword in faturamento_keywords):
        return "FATURAMENTO", None
    
    # I. Classificação de "INFORME DE RENDIMENTOS"
    informe_keywords = ["dirf_", "informe de rendimento", "informe de rendimentos", "informe_rendimentos", "informe rendimentos"]
    if (any(keyword in content_lower for keyword in informe_keywords) or 
        any(keyword in name_lower for keyword in informe_keywords)):
        if "extrato" not in content_lower:
            return "INFORME DE RENDIMENTOS", None
    
    # J. Classificação de "RELATÓRIOS"
    relatorio_keywords = ["relatorio", "relatório", "relatórios"]
    if (any(keyword in content_lower for keyword in relatorio_keywords) or 
        any(keyword in name_lower for keyword in relatorio_keywords)):
        if "extrato" not in content_lower:
            return "RELATORIOS", None
    
    # K. Classificação de "COMPROVANTES"
    comprovante_keywords = ["comprovante", "comprovantes"]
    if (any(keyword in content_lower for keyword in comprovante_keywords) or 
        any(keyword in name_lower for keyword in comprovante_keywords)):
        if "extrato" not in content_lower:
            return "COMPROVANTES", None
    
    # L. Classificação de "SPEDS"
    sped_keywords = ["sped"]
    if (any(keyword in content_lower for keyword in sped_keywords) or 
        any(keyword in name_lower for keyword in sped_keywords)):
        return "SPEDs", None
    
    # Se chegou até aqui, não foi possível classificar
    return "REVISÃO MANUAL", None

# Função para extrair CNPJ do caminho do arquivo
def extract_cnpj_from_path(file_path):
    """Extrai o CNPJ do cliente do caminho do arquivo."""
    try:
        # Padrão para encontrar CNPJ no formato XX.XXX.XXX/XXXX-XX ou sem pontuação
        cnpj_pattern = r'(\d{2}\.?\d{3}\.?\d{3}\/?\d{4}\-?\d{2})'
        path_parts = file_path.split(os.sep)
        
        for part in path_parts:
            match = re.search(cnpj_pattern, part)
            if match:
                # Remover pontuação para comparação
                cnpj = match.group(1).replace('.', '').replace('/', '').replace('-', '')
                return cnpj
        return None
    except Exception as e:
        logger.error(f"Erro ao extrair CNPJ do caminho: {e}")
        return None

# Função para criar estrutura de pastas
def create_folder_structure(client_path):
    """Cria a estrutura de pastas para o cliente."""
    try:
        # Obter ano e mês atual
        current_date = datetime.datetime.now()
        year_folder = str(current_date.year)
        month_folder = current_date.strftime("%m - %B")
        
        # Criar pasta do ano
        year_path = os.path.join(client_path, f"[{year_folder}]")
        os.makedirs(year_path, exist_ok=True)
        
        # Criar pasta do mês
        month_path = os.path.join(year_path, f"[{month_folder}]")
        os.makedirs(month_path, exist_ok=True)
        
        # Criar pastas para cada tipo de documento
        document_types = [
            "EXTRATO", "BOLETO", "NOTA FISCAL", "DACTE", "FATURA", 
            "FATURAMENTO", "INFORME DE RENDIMENTOS", "RELATORIOS", 
            "COMPROVANTES", "SPEDs", "REVISÃO MANUAL"
        ]
        
        for doc_type in document_types:
            type_path = os.path.join(month_path, f"[{doc_type}]")
            os.makedirs(type_path, exist_ok=True)
            
            # Criar subpastas específicas
            if doc_type == "EXTRATO":
                os.makedirs(os.path.join(type_path, "[CONTA CORRENTE]"), exist_ok=True)
                os.makedirs(os.path.join(type_path, "[APLICAÇÃO FINANCEIRA]"), exist_ok=True)
            elif doc_type == "NOTA FISCAL":
                os.makedirs(os.path.join(type_path, "[ENTRADA]"), exist_ok=True)
                os.makedirs(os.path.join(type_path, "[SAIDA]"), exist_ok=True)
                os.makedirs(os.path.join(type_path, "[SERVIÇO]"), exist_ok=True)
                os.makedirs(os.path.join(type_path, "[NOTA DE DEBITO]"), exist_ok=True)
            elif doc_type == "DACTE":
                os.makedirs(os.path.join(type_path, "[ENTRADA]"), exist_ok=True)
                os.makedirs(os.path.join(type_path, "[SAIDA]"), exist_ok=True)
        
        logger.info(f"Estrutura de pastas criada para: {client_path}")
        return year_path, month_path
    except Exception as e:
        logger.error(f"Erro ao criar estrutura de pastas: {e}")
        return None, None

# Função para mover arquivo para a pasta correta
def move_file_to_destination(file_path, client_path, doc_type, doc_subtype, file_date=None):
    """Move o arquivo para a pasta de destino correta."""
    try:
        # Determinar ano e mês com base na data do arquivo
        if file_date:
            year_folder = str(file_date.year)
            month_folder = file_date.strftime("%m - %B")
        else:
            # Usar data de modificação do arquivo
            file_mod_time = os.path.getmtime(file_path)
            file_date = datetime.datetime.fromtimestamp(file_mod_time)
            year_folder = str(file_date.year)
            month_folder = file_date.strftime("%m - %B")
        
        # Verificar se o ano é 2025 ou posterior
        if int(year_folder) < 2025:
            year_folder = "2025"  # Forçar para 2025 conforme requisito
        
        # Criar caminhos das pastas
        year_path = os.path.join(client_path, f"[{year_folder}]")
        month_path = os.path.join(year_path, f"[{month_folder}]")
        type_path = os.path.join(month_path, f"[{doc_type}]")
        
        # Garantir que as pastas existam
        os.makedirs(year_path, exist_ok=True)
        os.makedirs(month_path, exist_ok=True)
        os.makedirs(type_path, exist_ok=True)
        
        # Determinar caminho final com base no subtipo
        if doc_subtype and doc_type in ["EXTRATO", "NOTA FISCAL", "DACTE"]:
            final_path = os.path.join(type_path, f"[{doc_subtype}]")
            os.makedirs(final_path, exist_ok=True)
        else:
            final_path = type_path
        
        # Mover o arquivo
        file_name = os.path.basename(file_path)
        destination = os.path.join(final_path, file_name)
        
        # Verificar se o arquivo já existe no destino
        if os.path.exists(destination):
            base_name, ext = os.path.splitext(file_name)
            destination = os.path.join(final_path, f"{base_name}_{int(time.time())}{ext}")
        
        shutil.move(file_path, destination)
        logger.info(f"Arquivo movido: {file_path} -> {destination}")
        return True
    except Exception as e:
        logger.error(f"Erro ao mover arquivo {file_path}: {e}")
        return False

# Função principal para processar todos os clientes
def process_all_clients():
    """Processa todos os clientes no diretório base."""
    try:
        # Listar todas as pastas de clientes
        client_folders = [f for f in os.listdir(BASE_PATH) if os.path.isdir(os.path.join(BASE_PATH, f))]
        
        for client_folder in client_folders:
            client_path = os.path.join(BASE_PATH, client_folder)
            logger.info(f"Processando cliente: {client_folder}")
            
            # Verificar se existem pastas de CNPJ
            cnpj_folders = [f for f in os.listdir(client_path) if os.path.isdir(os.path.join(client_path, f)) and re.search(r'\d{14}', f.replace('.', '').replace('/', '').replace('-', ''))]
            
            # Se não houver pastas de CNPJ, criar estrutura na raiz
            if not cnpj_folders:
                logger.info(f"Nenhuma pasta de CNPJ encontrada para {client_folder}. Criando estrutura na raiz.")
                year_path, month_path = create_folder_structure(client_path)
                process_directory(client_path, client_path)
            else:
                # Processar cada pasta de CNPJ
                for cnpj_folder in cnpj_folders:
                    cnpj_path = os.path.join(client_path, cnpj_folder)
                    logger.info(f"Processando CNPJ: {cnpj_folder}")
                    
                    # Criar estrutura de pastas
                    year_path, month_path = create_folder_structure(cnpj_path)
                    
                    # Processar arquivos na pasta do CNPJ
                    process_directory(cnpj_path, cnpj_path)
        
        logger.info("Processamento concluído para todos os clientes.")
    except Exception as e:
        logger.error(f"Erro ao processar clientes: {e}")

# Função para processar um diretório
def process_directory(directory, client_path):
    """Processa todos os arquivos em um diretório e suas subpastas."""
    try:
        for root, dirs, files in os.walk(directory):
            # Verificar se estamos em uma pasta de destino (criada pelo script)
            if any(marker in root for marker in ["[EXTRATO]", "[BOLETO]", "[NOTA FISCAL]", "[DACTE]", 
                                               "[FATURA]", "[FATURAMENTO]", "[INFORME DE RENDIMENTOS]", 
                                               "[RELATORIOS]", "[COMPROVANTES]", "[SPEDs]", "[REVISÃO MANUAL]"]):
                continue
            
            for file in files:
                file_path = os.path.join(root, file)
                
                # Verificar se é um arquivo compactado
                if file.lower().endswith(('.zip', '.rar')):
                    # Criar pasta temporária para extração
                    extract_dir = os.path.join(root, f"temp_extract_{int(time.time())}")
                    os.makedirs(extract_dir, exist_ok=True)
                    
                    # Extrair arquivos
                    if extract_compressed_files(file_path, extract_dir):
                        # Processar arquivos extraídos
                        process_directory(extract_dir, client_path)
                        
                        # Remover pasta temporária após processamento
                        try:
                            shutil.rmtree(extract_dir)
                        except:
                            logger.warning(f"Não foi possível remover pasta temporária: {extract_dir}")
                    
                    # Mover o arquivo compactado para REVISÃO MANUAL
                    move_file_to_destination(file_path, client_path, "REVISÃO MANUAL", None)
                else:
                    # Extrair conteúdo do arquivo
                    file_content = extract_text(file_path)
                    
                    # Classificar documento
                    doc_type, doc_subtype = classify_document(file_path, file_content, file)
                    
                    # Mover para pasta correta
                    move_file_to_destination(file_path, client_path, doc_type, doc_subtype)
    except Exception as e:
        logger.error(f"Erro ao processar diretório {directory}: {e}")


# Executar o processamento
if __name__ == "__main__":
    logger.info("Iniciando processamento de documentos")
    process_all_clients()
    logger.info("Processamento concluído")

print("Programa de classificação e organização de documentos concluído!")

# --- Configuração ---
# !!! ATENÇÃO: MUDE PARA False PARA EXECUTAR AS OPERAÇÕES REAIS !!!
DRY_RUN = True  # Se True, apenas simula as ações. Mude para False para execução real.
# !!! ATENÇÃO: MUDE PARA False PARA EXECUTAR AS OPERAÇÕES REAIS !!!

BASE_PATH = r"C:\Users\laurob\Desktop\amostragem" # Use raw string para caminhos no Windows
 
YEAR_FOLDER_NAME = "[2025]"
FISCAL_FOLDER_NAME = "[FISCAL]"
CONTABIL_FOLDER_NAME = "[CONTABIL]"
MANUAL_REVIEW_FOLDER_NAME = "[REVISÃO MANUAL]"

FOLDERS_TO_CONTABIL = [
    "[BOLETO]",
    "[COMPROVANTES]",
    "[EXTRATO]",
    "[FATURAMENTO]",
    "[INFORME DE RENDIMENTO]",
]
FOLDERS_TO_FISCAL = [
    "[DACTE]",
    "[FATURA]",
    "[NOTA FISCAL]",
    "[RELATORIOS]",
    "[SPEDs]",
]

# --- Funções Auxiliares ---
def clear_folder_contents(folder_path):
    """Deleta todo o conteúdo de uma pasta (arquivos e subpastas)."""
    if not os.path.exists(folder_path):
        print(f"    AVISO: Tentativa de limpar conteúdo de pasta inexistente: {folder_path}")
        return
    if not os.listdir(folder_path): # Verifica se a pasta já está vazia
        #print(f"    INFO: Pasta já está vazia: {folder_path}") # Log opcional
        return

    for item_name in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item_name)
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                if not DRY_RUN:
                    os.unlink(item_path)
                print(f"    {'[DRY RUN] ' if DRY_RUN else ''}Deletado arquivo: {item_path}")
            elif os.path.isdir(item_path):
                if not DRY_RUN:
                    shutil.rmtree(item_path)
                print(f"    {'[DRY RUN] ' if DRY_RUN else ''}Deletada pasta: {item_path}")
        except Exception as e:
            print(f"    ERRO ao deletar {item_path}: {e}")

def safe_move_folder(src_path, dest_parent_path):
    """Move uma pasta de origem para uma pasta de destino pai."""
    if not os.path.exists(src_path):

        return
    if not os.path.isdir(src_path):
        print(f"    AVISO: Item de origem não é uma pasta: {src_path}")
        return

    folder_name = os.path.basename(src_path)
    final_dest_path = os.path.join(dest_parent_path, folder_name)

    # Verificação para não mover uma pasta para dentro dela mesma ou para o mesmo local exato
    if os.path.abspath(src_path) == os.path.abspath(final_dest_path):
        #print(f"    INFO: Origem e destino são os mesmos, não é necessário mover: {src_path}") # Log opcional
        return
    
    # Se a pasta de origem já estiver no local de destino correto (mesmo pai)
    if os.path.abspath(os.path.dirname(src_path)) == os.path.abspath(dest_parent_path):
        #print(f"    INFO: Pasta {folder_name} já está em {dest_parent_path}. Nenhuma ação de movimentação necessária.") # Log opcional
        return

    if os.path.exists(final_dest_path):
        print(f"    ERRO CRÍTICO AO MOVER: Destino final já existe! {final_dest_path}. Não foi possível mover {src_path}.")
        print(f"    Esta situação pode ocorrer se duas pastas com o mesmo nome de fontes diferentes tentarem ser movidas para o mesmo local,")
        print(f"    ou se a limpeza inicial das pastas [2025]/[FISCAL] e [2025]/[CONTABIL] não foi suficiente.")
        print(f"    VERIFIQUE MANUALMENTE. Regra 9 impede a sobrescrita de conteúdo existente nas pastas alvo de movimentação (itens 2 e 3).")
        return

    try:
        if not DRY_RUN:
            os.makedirs(dest_parent_path, exist_ok=True) # Garante que o diretório pai de destino exista
            shutil.move(src_path, dest_parent_path) # shutil.move(src, dst_dir) move src para dentro de dst_dir
        print(f"    {'[DRY RUN] ' if DRY_RUN else ''}Movida pasta: {src_path} -> {dest_parent_path}")
    except Exception as e:
        print(f"    ERRO ao mover {src_path} para {dest_parent_path}: {e}")

def safe_delete_folder(folder_path):
    """Deleta uma pasta de forma segura."""
    if not os.path.exists(folder_path):
        #print(f"    AVISO: Tentativa de deletar pasta inexistente: {folder_path}") # Pode ser normal se já foi deletada como parte de um pai
        return
    if not os.path.isdir(folder_path):
        print(f"    AVISO: Item a ser deletado não é uma pasta: {folder_path}")
        return
    try:
        if not DRY_RUN:
            shutil.rmtree(folder_path)
        print(f"    {'[DRY RUN] ' if DRY_RUN else ''}Deletada pasta (rogue/fora de {YEAR_FOLDER_NAME}): {folder_path}")
    except Exception as e:
        print(f"    ERRO ao deletar pasta {folder_path}: {e}")


# --- Lógica Principal de Processamento ---
def process_cnpj_folder(cnpj_folder_path):
    """Processa uma única pasta de CNPJ."""
    print(f"\n--- Processando pasta CNPJ: {cnpj_folder_path} ---")

    # Item 7 & 1.B.III: Criar a pasta [2025]
    year_folder_path = os.path.join(cnpj_folder_path, YEAR_FOLDER_NAME)
    if not DRY_RUN:
        os.makedirs(year_folder_path, exist_ok=True)
    print(f"  {'[DRY RUN] ' if DRY_RUN else ''}Garantida existência da pasta: {year_folder_path}")

    # Definir caminhos para [FISCAL] e [CONTABIL] dentro de [2025]
    fiscal_in_2025_path = os.path.join(year_folder_path, FISCAL_FOLDER_NAME)
    contabil_in_2025_path = os.path.join(year_folder_path, CONTABIL_FOLDER_NAME)

    # Item 1.A: Se [FISCAL]/[CONTABIL] dentro de [2025] existem, deletar conteúdo.
    # Item 1.B: Se não existem (dentro de [2025]), criar.
    for target_structured_folder in [fiscal_in_2025_path, contabil_in_2025_path]:
        if os.path.exists(target_structured_folder):
            print(f"  Pasta {os.path.basename(target_structured_folder)} existe em {year_folder_path}. Limpando conteúdo (Item 1.A)...")
            clear_folder_contents(target_structured_folder) # DRY_RUN é verificado dentro
        else:
            if not DRY_RUN:
                os.makedirs(target_structured_folder, exist_ok=True)
            print(f"  {'[DRY RUN] ' if DRY_RUN else ''}Criada pasta: {target_structured_folder} (Item 1.B)")
    
    actions_to_take = {
        "delete_rogue": [], 
        "move": []          
    }

    # Usamos topdown=True para poder modificar dirnames e evitar descer em pastas que serão movidas/deletadas
    for root, dirnames, filenames in os.walk(cnpj_folder_path, topdown=True):
        
        # Não processar nada que já esteja dentro das pastas finais [FISCAL] ou [CONTABIL] em [2025]
        if os.path.abspath(root) == os.path.abspath(fiscal_in_2025_path) or \
           os.path.abspath(root) == os.path.abspath(contabil_in_2025_path):
            dirnames[:] = [] 
            continue
        
        # Iterar sobre uma cópia de dirnames porque podemos modificá-la de trás para frente
        for d_idx in range(len(dirnames) - 1, -1, -1): 
            folder_name = dirnames[d_idx]
            current_folder_path = os.path.join(root, folder_name)

            # Item 1.C: Identificar [FISCAL] e [CONTABIL] fora de [2025] para deleção.
            is_fiscal_folder = (folder_name == FISCAL_FOLDER_NAME)
            is_contabil_folder = (folder_name == CONTABIL_FOLDER_NAME)

            if (is_fiscal_folder and os.path.abspath(current_folder_path) != os.path.abspath(fiscal_in_2025_path)) or \
               (is_contabil_folder and os.path.abspath(current_folder_path) != os.path.abspath(contabil_in_2025_path)):
                if current_folder_path not in actions_to_take["delete_rogue"]: # Evitar duplicatas
                    actions_to_take["delete_rogue"].append(current_folder_path)
                del dirnames[d_idx] # Não descer mais nesta pasta, pois será deletada
                continue # Processada para deleção, não considerar para mover

            # Itens 2, 3, 4: Identificar pastas para mover
            dest_parent_path = None
            if folder_name in FOLDERS_TO_CONTABIL:
                dest_parent_path = contabil_in_2025_path
            elif folder_name in FOLDERS_TO_FISCAL:
                dest_parent_path = fiscal_in_2025_path
            elif folder_name == MANUAL_REVIEW_FOLDER_NAME:
                dest_parent_path = year_folder_path
            
            if dest_parent_path:
                # Só marcar para mover se a pasta PAI atual (root) não for já a pasta PAI de destino.
                if os.path.abspath(root) != os.path.abspath(dest_parent_path):
                    is_already_listed_to_move = any(op[0] == current_folder_path for op in actions_to_take["move"])
                    if not is_already_listed_to_move:
                        actions_to_take["move"].append((current_folder_path, dest_parent_path))
                    del dirnames[d_idx] # Não descer mais nesta pasta, pois ela será movida
    
    # Executar deleções (pastas rogue) - mais profundas primeiro (ordenando pelo comprimento do caminho)
    actions_to_take["delete_rogue"].sort(key=len, reverse=True)
    if actions_to_take["delete_rogue"]:
        print(f"  Deletando pastas [FISCAL]/[CONTABIL] encontradas fora de '{YEAR_FOLDER_NAME}' (Item 1.C)...")
        for folder_path in actions_to_take["delete_rogue"]:
            safe_delete_folder(folder_path)

    # Executar movimentações
    if actions_to_take["move"]:
        print(f"  Movendo pastas para suas localizações designadas (Itens 2, 3, 4)...")
        for src_path, dest_parent_path in actions_to_take["move"]:
            safe_move_folder(src_path, dest_parent_path)


def main():
    """Função principal para percorrer as pastas dos clientes."""
    print("Iniciando script de organização de pastas de clientes.")
    if DRY_RUN:
        print("*" * 60)
        print("ATENÇÃO: RODANDO EM MODO DRY RUN (SIMULAÇÃO).")
        print("NENHUMA ALTERAÇÃO REAL SERÁ FEITA NO SISTEMA DE ARQUIVOS.")
        print("Para executar as alterações, mude DRY_RUN para False no script.")
        print("*" * 60)
        time.sleep(2) # Pausa para o usuário ler a mensagem

    if not os.path.exists(BASE_PATH):
        print(f"ERRO CRÍTICO: O caminho base '{BASE_PATH}' não existe. Verifique a configuração.")
        return

    # Nível 1: Pastas de "grupo de clientes" (ex: ftp4idistribuidora)
    for client_group_name in os.listdir(BASE_PATH):
        client_group_path = os.path.join(BASE_PATH, client_group_name)
        if not os.path.isdir(client_group_path):
            print(f"Item ignorado (não é diretório): {client_group_path}")
            continue
        
        print(f"\n>> Processando grupo de clientes: {client_group_name}")

        # Nível 2: Pastas de "CNPJ - ID - Nome_do_Cliente"
        for cnpj_id_name_folder_name in os.listdir(client_group_path):
            cnpj_folder_path = os.path.join(client_group_path, cnpj_id_name_folder_name)
            if not os.path.isdir(cnpj_folder_path):
                print(f"  Item ignorado (não é diretório): {cnpj_folder_path}")
                continue
            
            process_cnpj_folder(cnpj_folder_path)

    print("\n" + "="*30 + " PROCESSO DE ORGANIZAÇÃO CONCLUÍDO " + "="*30)
    if DRY_RUN:
        print("Lembre-se: Nenhuma alteração real foi feita (DRY RUN).")

if __name__ == "__main__":
    if not DRY_RUN:
        print("!"*70)
        print("!!! ATENÇÃO MODO REAL ATIVADO !!!")
        print("Este script MOVERÁ e DELETARÁ pastas e arquivos permanentemente.")
        print(f"O caminho base de operação é: {BASE_PATH}")
        print("É ALTAMENTE RECOMENDADO QUE VOCÊ TENHA FEITO UM BACKUP COMPLETO ANTES DE PROSSEGUIR.")
        print("!"*70)
        confirm = input("Digite 'SIM_EU_TENHO_CERTEZA' para confirmar e prosseguir com as operações reais: ")
        if confirm == "SIM_EU_TENHO_CERTEZA":
            print("\nConfirmação recebida. Iniciando operações reais em 5 segundos...")
            time.sleep(5)
            main()
        else:
            print("\nOperação cancelada pelo usuário. Nenhuma alteração foi feita.")
    else:
        main()


def forcar_remocao(path):
    """
    Força a remoção de arquivos/pastas mesmo com proteção.
    """
    try:
        # Remove atributo somente leitura
        os.chmod(path, stat.S_IWRITE)
        
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
        return True
    except:
        return False

def limpar_pasta_forcado(diretorio_pai):
    """
    Remove TUDO do diretório pai exceto a pasta [2025].
    Usa métodos mais agressivos.
    """
    print(f"\n🎯 LIMPANDO: {diretorio_pai}")
    
    try:
        # Listar tudo no diretório
        todos_itens = os.listdir(diretorio_pai)
        print(f"📋 Itens encontrados: {todos_itens}")
        
        removidos = 0
        falhas = 0
        
        for item_name in todos_itens:
            # NUNCA remover a pasta [2025]
            if item_name == '[2025]':
                print(f"✅ PRESERVANDO: {item_name}")
                continue
            
            item_path = os.path.join(diretorio_pai, item_name)
            print(f"🗑️ REMOVENDO: {item_name}")
            
            # Método 1: Tentar remoção normal
            try:
                if os.path.isfile(item_path):
                    os.remove(item_path)
                    print(f"   ✅ Arquivo removido: {item_name}")
                    removidos += 1
                    continue
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    print(f"   ✅ Pasta removida: {item_name}")
                    removidos += 1
                    continue
            except:
                pass
            
            # Método 2: Forçar remoção alterando permissões
            try:
                if os.path.isdir(item_path):
                    # Para pastas, alterar permissões recursivamente
                    for root, dirs, files in os.walk(item_path):
                        for d in dirs:
                            try:
                                os.chmod(os.path.join(root, d), stat.S_IWRITE)
                            except:
                                pass
                        for f in files:
                            try:
                                os.chmod(os.path.join(root, f), stat.S_IWRITE)
                            except:
                                pass
                    
                    # Alterar permissão da pasta principal
                    os.chmod(item_path, stat.S_IWRITE)
                    shutil.rmtree(item_path)
                    print(f"   ✅ Pasta removida (método 2): {item_name}")
                    removidos += 1
                    continue
                else:
                    # Para arquivos
                    os.chmod(item_path, stat.S_IWRITE)
                    os.remove(item_path)
                    print(f"   ✅ Arquivo removido (método 2): {item_name}")
                    removidos += 1
                    continue
            except:
                pass
            
            # Método 3: Usando subprocess para del/rmdir (Windows)
            if os.name == 'nt':  # Windows
                try:
                    import subprocess
                    if os.path.isdir(item_path):
                        subprocess.run(['rmdir', '/s', '/q', item_path], shell=True, check=True)
                        print(f"   ✅ Pasta removida (cmd): {item_name}")
                        removidos += 1
                        continue
                    else:
                        subprocess.run(['del', '/f', '/q', f'"{item_path}"'], shell=True, check=True)
                        print(f"   ✅ Arquivo removido (cmd): {item_name}")
                        removidos += 1
                        continue
                except:
                    pass
            
            # Se chegou aqui, não conseguiu remover
            print(f"   ❌ FALHA ao remover: {item_name}")
            falhas += 1
        
        print(f"📊 RESULTADO: {removidos} removidos, {falhas} falhas")
        
        if falhas == 0:
            print("🎉 SUCESSO TOTAL! Todos os itens foram removidos!")
        else:
            print(f"⚠️ {falhas} itens não puderam ser removidos")
            
    except Exception as e:
        print(f"❌ ERRO CRÍTICO ao processar {diretorio_pai}: {e}")

def main():
    pasta_raiz = r"C:\Users\laurob\Desktop\amostragem"
    
    print("=" * 70)
    print("🔥 LIMPADOR AGRESSIVO DE DIRETÓRIOS [2025] 🔥")
    print("=" * 70)
    print(f"📂 Pasta raiz: {pasta_raiz}")
    print()
    
    if not os.path.exists(pasta_raiz):
        print(f"❌ ERRO: Pasta raiz não existe: {pasta_raiz}")
        return
    
    pastas_2025_encontradas = []
    
    # Encontrar todas as pastas [2025]
    print("🔍 Procurando pastas [2025]...")
    for root, dirs, files in os.walk(pasta_raiz):
        if '[2025]' in dirs:
            pastas_2025_encontradas.append(root)
            print(f"✅ Encontrada [2025] em: {root}")
    
    if not pastas_2025_encontradas:
        print("❌ Nenhuma pasta [2025] encontrada!")
        return
    
    print(f"\n🎯 Total de diretórios para processar: {len(pastas_2025_encontradas)}")
    print("\n🚀 INICIANDO LIMPEZA AGRESSIVA...")
    
    # Processar cada diretório que contém [2025]
    for diretorio in pastas_2025_encontradas:
        limpar_pasta_forcado(diretorio)
    
    print("\n" + "=" * 70)
    print("🏁 PROCESSO CONCLUÍDO!")
    print("=" * 70)

if __name__ == "__main__":
    main()