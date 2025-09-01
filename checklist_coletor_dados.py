import requests
import json
import os
from datetime import datetime
from typing import List, Dict, Any

class PendenciasExtractor:
    def __init__(self):
        self.base_url = "http://intranetmg:xxxx/services/checklist/api/pendencias/ListarPendencias"
        self.campos_extrair = [
            'obrigacaoDescricao',
            'idCliente', 
            'tipo'
        ]
        self.pasta_dados = "dados_extraidos"
        self._criar_pasta_dados()
    
    def _criar_pasta_dados(self):
        """
        Cria a pasta dados_extraidos se não existir
        """
        if not os.path.exists(self.pasta_dados):
            os.makedirs(self.pasta_dados)
            print(f"Pasta '{self.pasta_dados}' criada com sucesso.")
        else:
            print(f"Pasta '{self.pasta_dados}' já existe.")
    
    def fazer_requisicao(self, url: str, tentativas: int = 3) -> Dict[str, Any]:
        """
        Faz requisição HTTP e retorna dados JSON com múltiplas tentativas
        """
        timeouts = [300, 450, 600]  # Timeouts: 5min, 7.5min, 10min
        
        for tentativa in range(tentativas):
            timeout_atual = timeouts[min(tentativa, len(timeouts)-1)]
            timeout_min = timeout_atual // 60
            timeout_seg = timeout_atual % 60
            
            try:
                print(f"Fazendo requisição para: {url}")
                print(f"Tentativa {tentativa + 1}/{tentativas} - Timeout: {timeout_min}min {timeout_seg}s")
                print(f"⏱ Aguardando resposta... (pode demorar)")
                
                response = requests.get(url, timeout=timeout_atual)
                response.raise_for_status()
                
                print(f"✓ Requisição bem-sucedida - Status: {response.status_code}")
                print(f"✓ Tamanho da resposta: {len(response.content)} bytes")
                
                return response.json()
                
            except requests.exceptions.ReadTimeout as e:
                print(f"⚠ Timeout na tentativa {tentativa + 1}: {timeout_min}min {timeout_seg}s")
                if tentativa < tentativas - 1:
                    print(f"Tentando novamente com timeout ainda maior...")
                else:
                    print(f"✗ Todas as tentativas falharam por timeout: {e}")
                    
            except requests.exceptions.RequestException as e:
                print(f"✗ Erro de requisição na tentativa {tentativa + 1}: {e}")
                if tentativa < tentativas - 1:
                    print(f"Tentando novamente...")
                else:
                    print(f"✗ Todas as tentativas falharam: {e}")
                    
            except json.JSONDecodeError as e:
                print(f"✗ Erro ao decodificar JSON: {e}")
                return {}
        
        return {}
    
    def extrair_campos(self, dados: Any, tipo_servico: str) -> List[Dict[str, Any]]:
        """
        Extrai os campos especificados dos dados JSON
        """
        registros_extraidos = []
        
        # Debug: mostra estrutura dos dados recebidos
        print(f"Tipo de dados recebidos para {tipo_servico}: {type(dados)}")
        
        # Verifica se os dados são uma lista ou um dicionário
        if isinstance(dados, list):
            itens = dados
            print(f"Dados são uma lista com {len(itens)} itens")
        elif isinstance(dados, dict):
            # Tenta encontrar a lista de itens dentro do dicionário
            # Procura por várias possíveis chaves que podem conter os dados
            chaves_possiveis = ['items', 'data', 'pendencias', 'resultados', 'registros']
            itens = None
            
            for chave in chaves_possiveis:
                if chave in dados:
                    itens = dados[chave]
                    print(f"Dados encontrados na chave '{chave}'")
                    break
            
            # Se não encontrou em nenhuma chave específica, usa o próprio dicionário
            if itens is None:
                itens = [dados]
                print(f"Usando o próprio dicionário como item único")
        else:
            print(f"Formato de dados não reconhecido para {tipo_servico}: {type(dados)}")
            return []
        
        # Se itens não é uma lista, converte para lista
        if not isinstance(itens, list):
            itens = [itens]
            print(f"Convertido para lista com {len(itens)} item(ns)")
        
        print(f"Processando {len(itens)} item(ns) de {tipo_servico}")
        
        for i, item in enumerate(itens):
            if isinstance(item, dict):
                registro = {}
                
                # Debug: mostra as chaves disponíveis no primeiro item
                if i == 0:
                    print(f"Chaves disponíveis no primeiro item de {tipo_servico}: {list(item.keys())}")
                
                # Extrai os campos solicitados
                for campo in self.campos_extrair:
                    valor = item.get(campo)
                    registro[campo] = valor
                    
                    # Debug para o campo obrigacaoDescricao
                    if campo == 'obrigacaoDescricao' and valor:
                        print(f"Campo '{campo}' extraído: {str(valor)[:100]}..." if len(str(valor)) > 100 else f"Campo '{campo}' extraído: {valor}")
                
                # Adiciona informação sobre o tipo de serviço
                registro['tipoServico'] = tipo_servico
                
                registros_extraidos.append(registro)
            else:
                print(f"Item {i} não é um dicionário: {type(item)}")
        
        print(f"Total de registros extraídos de {tipo_servico}: {len(registros_extraidos)}")
        return registros_extraidos
    
    def processar_servico(self, tipo_servico: str, mes: int = 6, ano: int = 2025) -> Dict[str, Any]:
        """
        Processa dados de um serviço específico
        """
        url = f"{self.base_url}/{tipo_servico}?mes={mes}&ano={ano}"
        
        resultado = {
            'metadados': {
                'data_extracao': datetime.now().isoformat(),
                'tipo_servico': tipo_servico,
                'mes': mes,
                'ano': ano,
                'url': url,
                'total_registros': 0,
                'status': 'erro'
            },
            'dados': []
        }
        
        print(f"\nProcessando dados de {tipo_servico}...")
        
        # Faz requisição com múltiplas tentativas
        dados = self.fazer_requisicao(url, tentativas=3)
        
        if dados:
            # Extrai campos
            registros = self.extrair_campos(dados, tipo_servico)
            resultado['dados'] = registros
            resultado['metadados']['total_registros'] = len(registros)
            resultado['metadados']['status'] = 'sucesso'
            
            print(f"✓ {len(registros)} registros extraídos de {tipo_servico}")
        else:
            print(f"✗ Nenhum dado obtido de {tipo_servico}")
        
        return resultado
    
    def salvar_dados_json(self, dados: Dict[str, Any], tipo_servico: str, mes: int, ano: int) -> str:
        """
        Salva os dados extraídos em formato JSON
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'pendencias_{tipo_servico}_{ano}_{mes:02d}_{timestamp}.json'
        filepath = os.path.join(self.pasta_dados, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
            print(f"✓ Dados de {tipo_servico} salvos em: {filepath}")
            return filepath
        except Exception as e:
            print(f"✗ Erro ao salvar arquivo JSON para {tipo_servico}: {e}")
            return None
    
    def exibir_resumo_servico(self, dados: Dict[str, Any]):
        """
        Exibe resumo dos dados extraídos para um serviço
        """
        metadados = dados['metadados']
        registros = dados['dados']
        tipo_servico = metadados['tipo_servico']
        
        print(f"\n--- RESUMO: {tipo_servico} ---")
        print(f"Status: {metadados['status']}")
        print(f"Registros extraídos: {metadados['total_registros']}")
        
        if registros and metadados['status'] == 'sucesso':
            # Estatísticas dos dados
            clientes_unicos = set()
            tipos_unicos = set()
            obrigacoes_com_descricao = 0
            
            for registro in registros:
                if registro.get('idCliente'):
                    clientes_unicos.add(registro['idCliente'])
                if registro.get('tipo'):
                    tipos_unicos.add(registro['tipo'])
                if registro.get('obrigacaoDescricao'):
                    obrigacoes_com_descricao += 1
            
            print(f"Clientes únicos: {len(clientes_unicos)}")
            print(f"Tipos únicos: {len(tipos_unicos)}")
            print(f"Registros com obrigacaoDescricao: {obrigacoes_com_descricao}")
            
            # Exemplo de registro (primeiro com obrigacaoDescricao)
            exemplo = next((r for r in registros if r.get('obrigacaoDescricao')), registros[0] if registros else None)
            if exemplo:
                print(f"Exemplo de registro:")
                for campo in self.campos_extrair:
                    valor = exemplo.get(campo, 'N/A')
                    valor_str = str(valor)[:50] + "..." if len(str(valor)) > 50 else str(valor)
                    print(f"  {campo}: {valor_str}")

def main():
    """
    Função principal - execução automática
    """
    print("EXTRATOR AUTOMÁTICO DE DADOS DE PENDÊNCIAS")
    print("=" * 60)
    
    # Parâmetros fixos para extração automática
    mes = 6
    ano = 2025
    servicos = ['EF', 'CTB']
    
    print(f"Configuração: mês={mes}, ano={ano}")
    print(f"Serviços: {', '.join(servicos)}")
    print(f"⚠ Nota: O serviço CTB pode demorar mais para responder")
    print(f"Timeouts configurados: 5min, 7.5min, 10min (3 tentativas)")
    print(f"⏱ Tempo máximo total por serviço: até 22.5 minutos")
    print()
    
    # Inicializa o extrator
    extractor = PendenciasExtractor()
    
    resultados = {}
    arquivos_salvos = []
    
    try:
        # Processa cada serviço separadamente
        for tipo_servico in servicos:
            resultado = extractor.processar_servico(tipo_servico, mes, ano)
            resultados[tipo_servico] = resultado
            
            # Salva os dados em JSON separado
            if resultado['dados']:
                filepath = extractor.salvar_dados_json(resultado, tipo_servico, mes, ano)
                if filepath:
                    arquivos_salvos.append(filepath)
            
            # Exibe resumo do serviço
            extractor.exibir_resumo_servico(resultado)
        
        # Resumo geral
        print(f"\n{'='*60}")
        print("RESUMO GERAL DA EXTRAÇÃO")
        print(f"{'='*60}")
        
        total_registros = sum(r['metadados']['total_registros'] for r in resultados.values())
        servicos_sucesso = sum(1 for r in resultados.values() if r['metadados']['status'] == 'sucesso')
        
        print(f"Total de registros extraídos: {total_registros}")
        print(f"Serviços processados com sucesso: {servicos_sucesso}/{len(servicos)}")
        print(f"Arquivos salvos: {len(arquivos_salvos)}")
        
        for arquivo in arquivos_salvos:
            print(f"  ✓ {os.path.basename(arquivo)}")
        
        if total_registros > 0:
            print(f"\n✓ Extração concluída com sucesso!")
        else:
            print(f"\n⚠ Nenhum dado foi extraído dos serviços.")
        
    except Exception as e:
        print(f"\n✗ Erro durante a execução: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()

    print(f"\nProcessamento finalizado (código: {exit_code})")  
