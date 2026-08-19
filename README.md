# 🏢 Automação de Programação de Pagamentos — Monte Carmo Shopping

Sistema automatizado desenvolvido em Python para varredura de boletos/notas fiscais em rede, extração inteligente de dados em PDF, cálculo de datas de pagamento respeitando regras de negócios da empresa (dias úteis: **Segunda, Terça e Quarta-feira**) e integração nativa com o **Microsoft Outlook** para criação de rascunhos.

---

## 📌 Principais Recursos

- **Varredura Automatizada de Pastas de Rede**: Identificação inteligente de subpastas por fornecedor/serviço.
- **Extração de Dados em PDF (`pdfplumber` + `pypdf`)**: Captura automática de Cedente/Fornecedor, Data de Vencimento, Valor (R$) e Descrição.
- **Motor de Regras de Pagamento**:
  - Pagamentos realizados **exclusivamente nas segundas, terças e quartas-feiras**.
  - Recuo automático de vencimentos em quinta/sexta/sábado para a quarta-feira anterior.
  - Vencimento em domingo ajustado para a segunda-feira seguinte (caso não vencido).
  - Alerta automático para boletos com data de vencimento no passado.
- **Geração de Rascunhos no Outlook (`pywin32`)**:
  - Redação de e-mail no padrão do Monte Carmo Shopping.
  - Saudação dinâmica conforme horário (*Bom dia*, *Boa tarde*, *Boa noite*).
  - Salvamento como **RASCUNHO** (sem disparo automático).
  - Anexação de todos os PDFs correspondentes à pasta.
- **Interface Gráfica (`CustomTkinter`) e Modo CLI**:
  - GUI moderna e intuitiva para acompanhamento dos logs em tempo real.
  - Executável de linha de comando para execuções agendadas.
- **Logs e Auditoria**: Histórico de execução salvo em formatos `.log` (texto) e `.json`.

---

## 🛠️ Pré-requisitos

- Windows 10/11
- Python 3.10 ou superior
- Microsoft Outlook instalado e configurado na máquina

---

## 🚀 Instalação e Configuração

1. **Clonar o Repositório**:
   ```bash
   git clone https://github.com/SEU_USUARIO/automacao-pagamentos-montecarmo.git
   cd automacao-pagamentos-montecarmo
   ```

2. **Criar e Ativar o Ambiente Virtual**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Instalar as Dependências**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Configurar o Arquivo `config.json`**:
   Ajuste os e-mails e o caminho padrão da rede conforme necessário:
   ```json
   {
       "caminho_rede": "\\\\SERVIDOR\\Pagamentos",
       "email_contas_pagar": "contasapagar@montecarmo.com.br",
       "email_michel": "michel@montecarmo.com.br",
       "email_marcus": "marcus@montecarmo.com.br",
       "email_harley": "harley@montecarmo.com.br"
   }
   ```

---

## 💻 Como Utilizar

### Modo Interface Gráfica (Recomendado)
```powershell
python gui.py
```

### Modo Linha de Comando (CLI)
```powershell
python main.py --path "\\SERVIDOR\Pagamentos"
```

### Executar Testes Automatizados
```powershell
pytest tests/test_payment_calculator.py
```

---

## 📝 Licença

Projeto desenvolvido para uso interno — Monte Carmo Shopping / TI.
