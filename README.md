
# Ferramentas para RH e DP - by Anderson Marinho

Este repositório contém duas ferramentas práticas desenvolvidas com Python e foco em automação de processos de **Recursos Humanos** e **Departamento Pessoal**, com interface moderna usando **CustomTkinter** e integração com **Outlook**.

---

## 📄 PDF Protect Tool

Ferramenta para proteção de arquivos PDF contendo CPFs, ideal para envio seguro de informes e documentos confidenciais.

### ✅ Funcionalidades

- Seleciona o PDF através de uma interface gráfica.
- Extrai automaticamente o CPF (formato 999.999.999-99).
- Gera senha automática com base no CPF ou senha personalizada.
- Protege o PDF com senha.
- Gera e-mail automático com PDF protegido anexado no Outlook.

### 📥 Download

🔗 [**Clique aqui para baixar o PDF Protect Tool**](https://drive.google.com/file/d/1FgWPq7p1ShX5k9WXnTP-oZbHzE05kWyS/view?usp=sharing)

### ⚙️ Requisitos

- Python 3.7 ou superior
- Windows com Outlook instalado

### 📦 Dependências

```bash
pip install customtkinter PyPDF2 pikepdf pywin32 pandas pyfiglet
```

---

## 📬 Outlook Classificador

Classificador inteligente de e-mails do Outlook com exportação para Excel. Ideal para times de RH, Financeiro ou Jurídico.

### ✅ Funcionalidades

- Lê e-mails não lidos do Outlook.
- Sugere temas com base nas palavras mais frequentes.
- Permite classificação em grupo ou individual.
- Exporta para Excel com remetente, assunto, data e tema.
- Permite responder ao e-mail diretamente pela interface.
- Interface moderna com **CustomTkinter**.

### 📁 Estrutura de Arquivos

- C:\_RPA\Email\_RPA_email.xlsx: onde os e-mails são salvos.
- C:\_RPA\Email\classification_themes.json: temas usados para classificação.

### 📥 Download

🔗 [**Clique aqui para baixar o Outlook Classificador**](https://drive.google.com/file/d/1VWCEg7wy7OUX5FV7DBli7C8X5NUc5hx2/view?usp=sharing)

> Substitua o link acima pelo seu Google Drive ou GitHub Releases.

### ⚙️ Requisitos

- Python 3.7 ou superior
- Windows com Outlook instalado

### 📦 Dependências

```bash
pip install customtkinter pywin32 openpyxl
```

### ▶️ Como Usar

1. Execute o script OutlookClassificador.py
2. Clique em "Processar Emails"
3. Escolha a pasta do Outlook
4. Confirme o tema ou classifique individualmente
5. Dados salvos automaticamente no Excel

### 💼 Exemplos de Uso

- RH: admissões, desligamentos, folha, benefícios
- Financeiro: boletos, faturas, cobranças
- Jurídico: contratos, ações, clientes

---

## 🤝 Contribuições

Contribuições são bem-vindas! Abra uma issue ou envie um pull request com sugestões ou melhorias.

## 📜 Licença

Projeto licenciado sob a [MIT License](LICENSE).

---

Desenvolvido por **Anderson Marinho**  
🔗 LinkedIn: [https://www.linkedin.com/in/andersonadv/ ](https://www.linkedin.com/in/anderson-marinho-ads/) 
🔗 GitHub: https://github.com/advmarinho  
🔗 Projeto Igarapé Digital: https://advmarinho.github.io/igarape_digital/

