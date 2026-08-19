import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def criar_pdf_simulado(caminho_pdf: str, fornecedor: str, valor: str, vencimento: str, descricao: str):
    """
    Cria um PDF simulado contendo o fluxo de texto real do boleto.
    """
    os.makedirs(os.path.dirname(caminho_pdf), exist_ok=True)
    c = canvas.Canvas(caminho_pdf, pagesize=letter)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 750, "MONTE CARMO SHOPPING - DOCUMENTO DE COBRANÇA")
    
    c.setFont("Helvetica", 11)
    c.drawString(50, 710, f"Cedente / Beneficiário: {fornecedor}")
    c.drawString(50, 690, f"Data de Vencimento: {vencimento}")
    c.drawString(50, 670, f"Valor do Documento: {valor}")
    c.drawString(50, 650, f"Descrição do Serviço: {descricao}")
    c.drawString(50, 630, "Forma de Pagamento: Boleto Bancário")
    c.drawString(50, 600, "Linha Digitável: 34191.79001 01043.510047 91020.150008 5 87150000064400")
    
    c.save()

def gerar_dados_teste():
    base_dir = "sample_data"
    
    # 1. GoTo (Ramal)
    criar_pdf_simulado(
        os.path.join(base_dir, "GoTo (Ramal)", "Boleto Goto.pdf"),
        fornecedor="GoTo Telecomunicações Ltda",
        valor="R$ 644,00",
        vencimento="15/08/2026",
        descricao="Serviço de Ramal IP e VOIP"
    )
    criar_pdf_simulado(
        os.path.join(base_dir, "GoTo (Ramal)", "NF-e - Nota Fiscal Eletronica.pdf"),
        fornecedor="GoTo Telecomunicações Ltda",
        valor="R$ 644,00",
        vencimento="15/08/2026",
        descricao="Nota Fiscal de Serviço Ramal"
    )

    # 2. Vivo Móvel
    criar_pdf_simulado(
        os.path.join(base_dir, "Vivo Móvel", "Vivo Movel.pdf"),
        fornecedor="Telefônica Brasil S.A. - Vivo",
        valor="R$ 1.250,50",
        vencimento="20/08/2026",
        descricao="Serviço Móvel Celular e Internet 5G"
    )

    # 3. Elevadores Atlas
    criar_pdf_simulado(
        os.path.join(base_dir, "Elevadores Atlas", "Boleto Elevadores Atlas.pdf"),
        fornecedor="Elevadores Atlas Otis Ltda",
        valor="R$ 3.890,00",
        vencimento="17/08/2026",
        descricao="Manutenção Preventiva de Elevadores e Escadas Rolantes"
    )

    print("Dados de teste em PDF real criados em 'sample_data/' com sucesso!")

if __name__ == "__main__":
    gerar_dados_teste()
