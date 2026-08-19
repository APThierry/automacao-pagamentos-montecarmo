import re
import os
from datetime import datetime, date
from typing import Dict, Any, Optional

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
    Extrator de dados de PDFs de boletos e notas fiscais.
    Extrai: Fornecedor, Valor (R$), Data de Vencimento e Descrição/Serviço.
    """

    def __init__(self):
        pass

    def extract_pdf_text(self, file_path: str) -> str:
        """Extrai todo o texto do PDF usando pdfplumber ou pypdf como fallback."""
        text = ""

        if pdfplumber:
            try:
                with pdfplumber.open(file_path) as pdf:
                    pages_text = []
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            pages_text.append(t)
                    text = "\n".join(pages_text)
            except Exception as e:
                print(f"pdfplumber falhou para {file_path}: {e}")

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
                print(f"pypdf falhou para {file_path}: {e}")

        return text.strip()

    def parse_boleto_data(self, file_path: str, nome_pasta_fallback: str) -> Dict[str, Any]:
        """
        Analisa o PDF e extrai as informações do boleto/NF.
        Retorna dicionário com os campos extraídos e status de leitura.
        """
        raw_text = self.extract_pdf_text(file_path)
        filename = os.path.basename(file_path)

        res = {
            "arquivo": filename,
            "caminho_completo": file_path,
            "fornecedor": nome_pasta_fallback,
            "fornecedor_pdf": None,
            "valor": 0.0,
            "valor_formatado": "R$ 0,00",
            "data_vencimento": None,
            "data_vencimento_str": "",
            "descricao": nome_pasta_fallback,
            "sucesso": False,
            "erro": None,
            "texto_extraido": bool(raw_text)
        }

        if not raw_text:
            res["erro"] = "Não foi possível extrair texto do PDF (pode ser imagem digitalizada ou arquivo corrompido)."
            return res

        # 1. Extração da Data de Vencimento
        vencimento_dt = self._extract_vencimento(raw_text)
        if vencimento_dt:
            res["data_vencimento"] = vencimento_dt
            res["data_vencimento_str"] = vencimento_dt.strftime("%d/%m/%Y")

        # 2. Extração do Valor
        valor_float, valor_str = self._extract_valor(raw_text)
        if valor_float > 0:
            res["valor"] = valor_float
            res["valor_formatado"] = valor_str

        # 3. Extração do Fornecedor / Beneficiário / Cedente
        fornecedor_pdf = self._extract_fornecedor(raw_text)
        if fornecedor_pdf:
            res["fornecedor_pdf"] = fornecedor_pdf
            res["fornecedor"] = fornecedor_pdf

        # 4. Extração de Descrição
        descricao = self._extract_descricao(raw_text, nome_pasta_fallback)
        res["descricao"] = descricao

        # Define se a extração foi satisfatória (mínimo: data ou valor encontrados)
        if res["data_vencimento"] or res["valor"] > 0:
            res["sucesso"] = True
        else:
            res["erro"] = "Dados cruciais (Vencimento/Valor) não puderam ser extraídos automaticamente."

        return res

    def _extract_vencimento(self, text: str) -> Optional[date]:
        """Procura por datas de vencimento no texto do PDF."""
        # Padrões comuns: Vencimento: DD/MM/AAAA, Data de Vencimento DD/MM/AAAA
        padroes = [
            r"(?:vencimento|venc\.?|data\s*de\s*vencimento|dt\.\s*venc\.?)\s*[:\-\s]?\s*(\d{2}[/\.]\d{2}[/\.]\d{4})",
            r"(\d{2}[/\.]\d{2}[/\.]\d{4})\s*(?:vencimento|venc)",
            r"vencimento\s*\n\s*(\d{2}[/\.]\d{2}[/\.]\d{4})",
            r"(\d{2}/\d{2}/\d{4})"  # Fallback: qualquer data DD/MM/AAAA no texto
        ]

        for p in padroes:
            matches = re.findall(p, text, re.IGNORECASE)
            for match in matches:
                dt_str = match.replace(".", "/")
                try:
                    dt = datetime.strptime(dt_str, "%d/%m/%Y").date()
                    # Ignorar datas improváveis (anos distantes)
                    if 2020 <= dt.year <= 2040:
                        return dt
                except ValueError:
                    continue
        return None

    def _extract_valor(self, text: str) -> tuple[float, str]:
        """Procura por valores numéricos em R$ no texto."""
        padroes = [
            r"(?:valor\s*do\s*documento|valor\s*cobrado|valor\s*total|valor\s*líquido|valor|total)\s*[:\-\s]?\s*(?:r\$\s*)?([\d\.]+\,\d{2})",
            r"r\$\s*([\d\.]+\,\d{2})",
            r"([\d\.]+\,\d{2})"
        ]

        for p in padroes:
            matches = re.findall(p, text, re.IGNORECASE)
            for m in matches:
                # Converter para float
                m_clean = m.replace(".", "").replace(",", ".")
                try:
                    val = float(m_clean)
                    if val > 0:
                        # Formata estilo brasileiro R$ X.XXX,XX
                        inteiro, decimal = f"{val:.2f}".split(".")
                        inteiro_fmt = "{:,}".format(int(inteiro)).replace(",", ".")
                        valor_fmt = f"R$ {inteiro_fmt},{decimal}"
                        return val, valor_fmt
                except ValueError:
                    continue

        return 0.0, "R$ 0,00"

    def _extract_fornecedor(self, text: str) -> Optional[str]:
        """Busca o nome do beneficiário/cedente/empresa emissora."""
        padroes = [
            r"(?:benefici[áa]rio|cedente|raz[ãa]o\s*social|nome\s*fantasia|emissor)\s*[:\-\s]?\s*([A-Za-z0-9\.\s\-\/&]+)(?:\n|cnpj|cpf|ag[êe]ncia)",
            r"(?:cedente/benefici[áa]rio)\s*[:\-\s]?\s*([A-Za-z0-9\.\s\-\/&]+)",
        ]

        for p in padroes:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                nome = match.group(1).strip()
                # Limpar ruídos comuns
                nome = re.sub(r"\s+", " ", nome)
                if len(nome) > 3 and not nome.isdigit():
                    return nome[:60]  # Limita tamanho para não pegar trecho longo
        return None

    def _extract_descricao(self, text: str, fallback: str) -> str:
        """Determina descrição breve do serviço se presente."""
        text_lower = text.lower()
        if "ramal" in text_lower or "telefonia" in text_lower or "voip" in text_lower:
            return "ramal/telefonia"
        elif "internet" in text_lower or "fibra" in text_lower or "link" in text_lower:
            return "internet"
        elif "aluguel" in text_lower or "locação" in text_lower:
            return "aluguel"
        elif "energia" in text_lower or "luz" in text_lower:
            return "energia elétrica"
        elif "água" in text_lower or "esgoto" in text_lower:
            return "água e esgoto"
        return fallback
