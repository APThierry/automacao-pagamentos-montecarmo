import re
import os
from datetime import datetime, date
from typing import Dict, Any, Optional, Tuple, List

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import pypdf
except ImportError:
    pypdf = None


class PDFExtractor:
    """
    Extrator avançado de dados de PDFs de boletos bancários, concessionárias e notas fiscais (DANFE/NFS-e).
    Suporta múltiplos motores (pdfplumber, pypdf, pypdfium2, OCR) e integração com a API do ChatGPT (OpenAI).
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    def extract_pdf_text(self, file_path: str) -> str:
        """
        Extrai todo o texto do PDF usando múltiplos motores (pdfplumber, pypdf e OCR fallback).
        """
        text = ""

        # Motor 1: pdfplumber (Leitura rica baseada em layout e tabelas)
        if pdfplumber:
            try:
                with pdfplumber.open(file_path) as pdf:
                    pages_text = []
                    for page in pdf.pages:
                        t = page.extract_text(layout=False) or page.extract_text(layout=True)
                        if t:
                            pages_text.append(t)
                        # Tenta extrair texto de tabelas se houver
                        tables = page.extract_tables()
                        for table in tables:
                            for row in table:
                                row_str = " | ".join([cell for cell in row if cell])
                                if row_str.strip():
                                    pages_text.append(row_str)
                    text = "\n".join(pages_text)
            except Exception as e:
                print(f"[pdfplumber] Erro em {file_path}: {e}")

        # Motor 2: pypdf (Fallback secundário de stream)
        if not text.strip() and pypdf:
            try:
                reader = pypdf.PdfReader(file_path)
                pages_text = []
                for page in reader.pages:
                    t = page.extract_text()
                    if t:
                        pages_text.append(t)
                text = "\n".join(pages_text)
            except Exception as e:
                print(f"[pypdf] Erro em {file_path}: {e}")

        # Motor 3: pypdfium2 (Renderização de texto de alta fidelidade)
        if not text.strip():
            try:
                import pypdfium2 as pdfium
                pdf = pdfium.PdfDocument(file_path)
                pages_text = []
                for page in pdf:
                    textpage = page.get_textpage()
                    t = textpage.get_text_range()
                    if t:
                        pages_text.append(t)
                pypdfium_text = "\n".join(pages_text)
                if pypdfium_text.strip():
                    text = pypdfium_text
            except Exception as e:
                pass

        # Motor 4: OCR Fallback (caso seja imagem escaneada e pytesseract/pdf2image estejam instalados)
        if not text.strip():
            text = self._try_ocr_extraction(file_path)

        return text.strip()

    def _try_ocr_extraction(self, file_path: str) -> str:
        """
        Tenta extrair texto via OCR caso o PDF seja uma imagem escaneada.
        Utiliza pypdfium2 para renderizar a imagem da página sem necessidade de poppler binaries.
        """
        ocr_text = []
        images = []

        # 1. Renderiza as páginas em imagem usando pypdfium2
        try:
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(file_path)
            for i, page in enumerate(pdf):
                if i >= 2:  # Limita a 2 páginas para otimizar velocidade
                    break
                image_pil = page.render(scale=2).to_pil()
                images.append(image_pil)
        except Exception as e:
            print(f"[OCR rendering pypdfium2] Erro em {file_path}: {e}")

        if not images:
            return ""

        # 2. Tenta OCR ultrarrápido via rapidocr_onnxruntime (ONNX)
        try:
            from rapidocr_onnxruntime import RapidOCR
            import numpy as np
            engine = RapidOCR()
            for img in images:
                img_np = np.array(img)
                result, _ = engine(img_np)
                if result:
                    txts = [line[1] for line in result if line and len(line) >= 2]
                    if txts:
                        ocr_text.append("\n".join(txts))
            if ocr_text:
                return "\n".join(ocr_text)
        except Exception:
            pass

        # 3. Tenta OCR via pytesseract
        try:
            import pytesseract
            for img in images:
                t = pytesseract.image_to_string(img, lang="por")
                if t.strip():
                    ocr_text.append(t)
            if ocr_text:
                return "\n".join(ocr_text)
        except Exception:
            pass

        # 4. Tenta OCR via easyocr como fallback neural
        try:
            import easyocr
            import numpy as np
            reader = easyocr.Reader(['pt'], gpu=False)
            for img in images:
                img_np = np.array(img)
                results = reader.readtext(img_np, detail=0)
                if results:
                    ocr_text.append("\n".join(results))
            if ocr_text:
                return "\n".join(ocr_text)
        except Exception:
            pass

        return ""

    def parse_boleto_data(self, file_path: str, nome_pasta_fallback: str) -> Dict[str, Any]:
        """
        Analisa o PDF e extrai de forma inteligente todas as informações do boleto/NF.
        """
        raw_text = self.extract_pdf_text(file_path)
        filename = os.path.basename(file_path)

        res = {
            "arquivo": filename,
            "caminho_completo": file_path,
            "fornecedor": nome_pasta_fallback,
            "fornecedor_pdf": None,
            "cnpj": None,
            "valor": 0.0,
            "valor_formatado": "R$ 0,00",
            "data_vencimento": None,
            "data_vencimento_str": "",
            "linha_digitavel": None,
            "descricao": nome_pasta_fallback,
            "sucesso": False,
            "erro": None,
            "texto_extraido": bool(raw_text)
        }

        if not raw_text:
            res["erro"] = "Não foi possível extrair texto do PDF (arquivo corrompido ou imagem sem camada de texto)."
            return res

        # 1. Extração da Linha Digitável / Código de Barras
        linha_dig = self._extract_linha_digitavel(raw_text)
        if linha_dig:
            res["linha_digitavel"] = linha_dig

        # 2. Extração da Data de Vencimento
        vencimento_dt = self._extract_vencimento(raw_text, linha_dig)
        if vencimento_dt:
            res["data_vencimento"] = vencimento_dt
            res["data_vencimento_str"] = vencimento_dt.strftime("%d/%m/%Y")

        # 3. Extração do Valor
        valor_float, valor_str = self._extract_valor(raw_text, linha_dig)
        if valor_float > 0:
            res["valor"] = valor_float
            res["valor_formatado"] = valor_str

        # 4. Extração do CNPJ e Fornecedor / Beneficiário / Cedente
        cnpj = self._extract_cnpj(raw_text)
        res["cnpj"] = cnpj

        fornecedor_pdf = self._extract_fornecedor(raw_text, nome_pasta_fallback)
        if fornecedor_pdf:
            res["fornecedor_pdf"] = fornecedor_pdf
            res["fornecedor"] = fornecedor_pdf

        # 5. Extração da Descrição/Serviço
        descricao = self._extract_descricao(raw_text, nome_pasta_fallback)
        res["descricao"] = descricao

        # 6. Classificação do Tipo de Documento (boleto vs nota_fiscal)
        res["tipo_documento"] = self._classificar_tipo_documento(raw_text, filename, linha_dig)

        # 7. Fallback com ChatGPT API (OpenAI) se a chave de API estiver configurada
        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        if api_key and (not res["data_vencimento"] or res["valor"] == 0.0 or not res["linha_digitavel"]):
            gpt_res = self._extract_with_chatgpt(raw_text, filename)
            if gpt_res:
                if not res["data_vencimento"] and gpt_res.get("data_vencimento"):
                    try:
                        dt = datetime.strptime(gpt_res["data_vencimento"], "%Y-%m-%d").date()
                        res["data_vencimento"] = dt
                        res["data_vencimento_str"] = dt.strftime("%d/%m/%Y")
                    except ValueError:
                        pass

                if res["valor"] == 0.0 and gpt_res.get("valor"):
                    try:
                        val = float(gpt_res["valor"])
                        if val > 0:
                            res["valor"] = val
                            res["valor_formatado"] = self._formatar_moeda(val)
                    except ValueError:
                        pass

                if not res["linha_digitavel"] and gpt_res.get("linha_digitavel"):
                    res["linha_digitavel"] = gpt_res["linha_digitavel"]

                if (not res["fornecedor_pdf"] or res["fornecedor"] == nome_pasta_fallback) and gpt_res.get("fornecedor"):
                    res["fornecedor_pdf"] = gpt_res["fornecedor"]
                    res["fornecedor"] = gpt_res["fornecedor"]

                if gpt_res.get("descricao") and res["descricao"] == nome_pasta_fallback:
                    res["descricao"] = gpt_res["descricao"]

                if gpt_res.get("tipo_documento"):
                    res["tipo_documento"] = gpt_res["tipo_documento"]

        # Validação do sucesso da extração
        if res["data_vencimento"] or res["valor"] > 0:
            res["sucesso"] = True
        else:
            res["erro"] = "Dados cruciais (Vencimento/Valor) não puderam ser identificados com precisão."

        return res

    def _extract_with_chatgpt(self, raw_text: str, filename: str) -> Optional[Dict[str, Any]]:
        """
        Utiliza a API do ChatGPT (OpenAI) para extrair informações estruturadas em JSON a partir do texto do PDF.
        """
        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None

        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)

            system_prompt = (
                "Você é um assistente financeiro especialista em extração de dados de boletos bancários e notas fiscais brasileiras.\n"
                "Sua tarefa é analisar o texto do documento e extrair estritamente um objeto JSON com as chaves:\n"
                "- fornecedor: nome da empresa emissora/beneficiária (string)\n"
                "- cnpj: CNPJ no formato XX.XXX.XXX/XXXX-XX (string ou null)\n"
                "- valor: número float do valor líquido/total do documento (ex: 1250.50)\n"
                "- data_vencimento: data no formato YYYY-MM-DD (string ou null)\n"
                "- linha_digitavel: linha digitável do código de barras de 47 ou 48 dígitos (string ou null)\n"
                "- descricao: breve resumo do serviço (ex: internet, ramal, aluguel, manutenção) (string)\n"
                "- tipo_documento: 'boleto' ou 'nota_fiscal'\n\n"
                "Responda APENAS com o objeto JSON válido."
            )

            user_prompt = f"Nome do Arquivo: {filename}\n\nTexto do PDF:\n{raw_text[:3500]}"

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            import json
            data = json.loads(response.choices[0].message.content)
            return data
        except Exception as e:
            print(f"[ChatGPT API] Erro ao extrair dados via OpenAI: {e}")
            return None

    def _classificar_tipo_documento(self, text: str, filename: str, linha_digitavel: Optional[str]) -> str:
        """Classifica se o PDF é um Boleto ou uma Nota Fiscal."""
        text_lower = text.lower()
        fn_lower = filename.lower()

        if linha_digitavel or "boleto" in fn_lower or "pagavel em qualquer banco" in text_lower or "nosso numero" in text_lower or "cedente" in text_lower or "beneficiario" in text_lower:
            return "boleto"
        elif "nota" in fn_lower or "nf" in fn_lower or "danfe" in text_lower or "nfs-e" in text_lower or "nf-e" in text_lower or "nota fiscal" in text_lower or "prestador" in text_lower:
            return "nota_fiscal"

        return "boleto"

    def _extract_linha_digitavel(self, text: str) -> Optional[str]:
        """Extrai linha digitável de 47 dígitos (Boleto) ou 48 dígitos (Concessionárias/Tributos)."""
        # Padrão Boleto Bancário: 5 blocos (ex: 34191.79001 01043.510047 91020.150008 5 87150000064400)
        padrao_boleto = r"\b(\d{5}[\.\s]?\d{5}\s?\d{5}[\.\s]?\d{6}\s?\d{5}[\.\s]?\d{6}\s?\d{1}\s?\d{14})\b"
        match_boleto = re.search(padrao_boleto, text)
        if match_boleto:
            linha = re.sub(r"[^\d]", "", match_boleto.group(1))
            if len(linha) == 47:
                # Formata com pontos e espaços
                return f"{linha[0:5]}.{linha[5:10]} {linha[10:15]}.{linha[15:21]} {linha[21:26]}.{linha[26:32]} {linha[32]} {linha[33:]}"

        # Padrão Concessionárias / Impostos: 4 blocos de 12 dígitos (ex: 84670000001-7 ...)
        padrao_arrecadacao = r"\b(\d{11}[\-\s]?\d{1}\s?\d{11}[\-\s]?\d{1}\s?\d{11}[\-\s]?\d{1}\s?\d{11}[\-\s]?\d{1})\b"
        match_arrec = re.search(padrao_arrecadacao, text)
        if match_arrec:
            linha = re.sub(r"[^\d]", "", match_arrec.group(1))
            if len(linha) == 48:
                return f"{linha[0:11]}-{linha[11]} {linha[12:23]}-{linha[23]} {linha[24:35]}-{linha[35]} {linha[36:47]}-{linha[47]}"

        return None

    def _extract_vencimento(self, text: str, linha_digitavel: Optional[str] = None) -> Optional[date]:
        """
        Extrai a data de vencimento com priorização de palavras-chave relativas a vencimento,
        evitando confundir com datas de emissão.
        """
        # Padrões com alta prioridade (associações diretas a Vencimento)
        padroes_alta_prioridade = [
            r"(?:vencimento|venc\.?|data\s*de\s*vencimento|dt\.\s*venc\.?|pagar\s*at[ée]|vencimento\s*em)\s*[:\-\s]?\s*(\d{2}[/\.]\d{2}[/\.]\d{4})",
            r"(\d{2}[/\.]\d{2}[/\.]\d{4})\s*(?:vencimento|venc)",
            r"vencimento\s*\n\s*(\d{2}[/\.]\d{2}[/\.]\d{4})",
            r"vencimento\s*[:\-\s]?\s*(\d{2}\s+de\s+[a-zç]+\s+de\s+\d{4})",  # Ex: 15 de agosto de 2026
        ]

        meses_extenso = {
            "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4,
            "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
            "outubro": 10, "novembro": 11, "dezembro": 12
        }

        for p in padroes_alta_prioridade:
            matches = re.findall(p, text, re.IGNORECASE)
            for match in matches:
                if " de " in match.lower():
                    # Trata data por extenso
                    parts = match.lower().split(" de ")
                    if len(parts) == 3:
                        dia = int(parts[0])
                        mes_str = parts[1].strip()
                        ano = int(parts[2])
                        mes = meses_extenso.get(mes_str)
                        if mes:
                            try:
                                return date(ano, mes, dia)
                            except ValueError:
                                pass
                else:
                    dt_str = match.replace(".", "/")
                    try:
                        dt = datetime.strptime(dt_str, "%d/%m/%Y").date()
                        if 2020 <= dt.year <= 2040:
                            return dt
                    except ValueError:
                        continue

        # Tenta extrair o fator de vencimento da linha digitável bancária (dígitos 33 a 37)
        if linha_digitavel:
            apenas_digitos = re.sub(r"[^\d]", "", linha_digitavel)
            if len(apenas_digitos) == 47:
                fator_str = apenas_digitos[33:37]
                try:
                    fator = int(fator_str)
                    if fator >= 1000:
                        # Data base bancária: 07/10/1997 + fator dias (com virada para fatores > 9999)
                        data_base = date(1997, 10, 7)
                        # Ajuste para nova regra do Banco Central (fatores após 22/02/2025)
                        if fator > 9999:
                            fator -= 9000
                            data_base = date(2025, 2, 22)
                        dt_calculada = data_base + timedelta(days=fator)
                        if 2020 <= dt_calculada.year <= 2040:
                            return dt_calculada
                except Exception:
                    pass

        # Fallback genérico: busca qualquer data no texto descartando rótulos de emissão
        linhas = text.split("\n")
        for linha in linhas:
            if any(termo in linha.lower() for termo in ["emissão", "emissao", "documento", "processamento", "cadastro"]):
                continue  # Ignora linhas de emissão
            matches = re.findall(r"\b(\d{2}/\d{2}/\d{4})\b", linha)
            for m in matches:
                try:
                    dt = datetime.strptime(m, "%d/%m/%Y").date()
                    if 2020 <= dt.year <= 2040:
                        return dt
                except ValueError:
                    continue

        return None

    def _extract_valor(self, text: str, linha_digitavel: Optional[str] = None) -> Tuple[float, str]:
        """
        Extrai o valor cobrado do documento, filtrando descontos e priorizando o valor final do documento.
        """
        # Padrões com alta prioridade
        padroes_alta_prioridade = [
            r"(?:valor\s*do\s*documento|\(\=\)\s*valor\s*do\s*documento|valor\s*cobrado|valor\s*total|total\s*a\s*pagar|valor\s*l[íi]quido|valor\s*da\s*nota|valor\s*do\s*servi[çc]o|valor\s*bruto|valor\s*fatura|total\s*r\$|vlr\.\s*total|vlr\.\s*doc)\s*[:\-\s]?\s*(?:r\$\s*)?([\d\.]+\,\d{2})",
            r"(?:valor|total)\s*[:\-\s]?\s*(?:r\$\s*)?([\d\.]+\,\d{2})",
            r"r\$\s*([\d\.]+\,\d{2})"
        ]

        valores_encontrados = []

        for p in padroes_alta_prioridade:
            matches = re.findall(p, text, re.IGNORECASE)
            for m in matches:
                m_clean = m.replace(".", "").replace(",", ".")
                try:
                    val = float(m_clean)
                    if val > 0:
                        valores_encontrados.append(val)
                except ValueError:
                    continue

        if valores_encontrados:
            # Pega o maior valor encontrado entre as correspondências diretas
            val_final = max(valores_encontrados)
            return val_final, self._formatar_moeda(val_final)

        # Tenta extrair os últimos 10 dígitos da linha digitável bancária (Valor)
        if linha_digitavel:
            apenas_digitos = re.sub(r"[^\d]", "", linha_digitavel)
            if len(apenas_digitos) == 47:
                valor_centavos_str = apenas_digitos[37:47]
                try:
                    val_centavos = int(valor_centavos_str)
                    if val_centavos > 0:
                        val = val_centavos / 100.0
                        return val, self._formatar_moeda(val)
                except ValueError:
                    pass

        # Fallback genérico: procura por qualquer valor no formato 1.234,56 ou 234,56 no texto
        matches_genericos = re.findall(r"\b(\d{1,3}(?:\.\d{3})*\,\d{2})\b", text)
        valores_genericos = []
        for m in matches_genericos:
            m_clean = m.replace(".", "").replace(",", ".")
            try:
                val = float(m_clean)
                if val > 0:
                    valores_genericos.append(val)
            except ValueError:
                continue

        if valores_genericos:
            val_final = max(valores_genericos)
            return val_final, self._formatar_moeda(val_final)

        return 0.0, "R$ 0,00"

    def _extract_cnpj(self, text: str) -> Optional[str]:
        """Extrai CNPJ no formato XX.XXX.XXX/XXXX-XX do texto."""
        match = re.search(r"\b(\d{2}\.\d{3}\.\d{3}/\d{4}\-\d{2})\b", text)
        if match:
            return match.group(1)
        return None

    def _extract_fornecedor(self, text: str, fallback: str) -> Optional[str]:
        """
        Busca o nome do beneficiário/cedente/prestador de serviços com limpeza de ruídos.
        """
        padroes = [
            r"(?:benefici[áa]rio|cedente|raz[ãa]o\s*social|nome\s*fantasia|emissor|prestador\s*de\s*servi[çc]os?)\s*[:\-\s]?\s*([A-Za-z0-9\.\s\-\/&]+)(?:\n|cnpj|cpf|ag[êe]ncia|endere[çc]o)",
            r"(?:cedente/benefici[áa]rio)\s*[:\-\s]?\s*([A-Za-z0-9\.\s\-\/&]+)",
            r"(?:nome/raz[ãa]o\s*social)\s*[:\-\s]?\s*([A-Za-z0-9\.\s\-\/&]+)"
        ]

        ruidos = [
            "comprovante", "autenticacao", "mecanica", "recibo", "sacado", "pagador",
            "banco", "pagamento", "agencia", "codigo", "carteira", "nosso numero"
        ]

        for p in padroes:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                nome = match.group(1).strip()
                nome = re.sub(r"\s+", " ", nome)
                
                # Descarta se contiver ruídos de cabeçalho bancário
                if any(r in nome.lower() for r in ruidos):
                    continue

                if len(nome) > 3 and not nome.isdigit():
                    return nome[:65].strip()

        return fallback

    def _extract_descricao(self, text: str, fallback: str) -> str:
        """Identifica a categoria/descrição do serviço a partir do texto do PDF."""
        text_lower = text.lower()
        if any(term in text_lower for term in ["ramal", "telefonia", "voip", "sip", "pabx"]):
            return "ramal/telefonia"
        elif any(term in text_lower for term in ["internet", "fibra", "banda larga", "link dedicado"]):
            return "internet"
        elif any(term in text_lower for term in ["aluguel", "locação", "condomínio", "crd"]):
            return "aluguel/condomínio"
        elif any(term in text_lower for term in ["energia", "luz", "cemig", "equatorial", "enel"]):
            return "energia elétrica"
        elif any(term in text_lower for term in ["água", "agua", "copasa", "esgoto", "saneamento"]):
            return "água e esgoto"
        elif any(term in text_lower for term in ["elevador", "escada rolante", "atlas", "otis", "thyssenkrupp"]):
            return "manutenção de elevadores"
        elif any(term in term.lower() for term in ["segurança", "vigilância", "portaria"]):
            return "segurança e vigilância"
        
        return fallback

    def _formatar_moeda(self, val: float) -> str:
        """Formata o valor float para o padrão brasileiro R$ X.XXX,XX."""
        inteiro, decimal = f"{val:.2f}".split(".")
        inteiro_fmt = "{:,}".format(int(inteiro)).replace(",", ".")
        return f"R$ {inteiro_fmt},{decimal}"
