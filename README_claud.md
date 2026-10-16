# 📊 GCP_Gestao_Contratos — Sistema de Gestão e Monitoramento de Contratos

| | |
|---|---|
| 🌐 **App publicado** | `COLAR_AQUI_O_LINK_DO_STREAMLIT` (acesso público, sem login) |
| 🎥 **Vídeo (até 3 min)** | `COLAR_AQUI_O_LINK_DO_LINKEDIN` |
| 👩‍💻 **Autora** | Claudia Ramos · [LinkedIn](COLAR_LINK) · [GitHub](COLAR_LINK) |
| 🎓 **Instituição / Programa** | SENAI/SC · LAB365 — Projeto Final |

---

## 📋 Sumário
1. [Documentação Inicial: Objetivo, Importância e Resultados Esperados](#1-documentação-inicial-objetivo-importância-e-resultados-esperados)
2. [O que é este Projeto? (Visão Geral para Leigos)](#2-o-que-é-este-projeto-visão-geral-para-leigos)
3. [Dicionário de Dados](#3-dicionário-de-dados)
4. [Arquitetura e Estrutura de Arquivos](#4-arquitetura-e-estrutura-de-arquivos)
5. [Tecnologias e Bibliotecas Utilizadas](#5-tecnologias-e-bibliotecas-utilizadas)
6. [Guia Passo a Passo Completo de Instalação e Execução](#6-guia-passo-a-passo-completo-de-instalação-e-execução)
7. [Como Utilizar o Dashboard (Guia do Usuário)](#7-como-utilizar-o-dashboard-guia-do-usuário)
8. [Próximos Passos de Desenvolvimento](#8-próximos-passos-de-desenvolvimento)
9. [Solução de Problemas Comuns (Troubleshooting)](#9-solução-de-problemas-comuns-troubleshooting)

---

## 1. Documentação inicial: objetivo, importância e resultados esperados

### Contexto do problema
Atuo há mais de 15 anos em prestação de contas de verbas público-privadas nas esferas federal, estadual e municipal. Dados frágeis na origem (duplicidades, campos em branco, divergências numéricas e sistemas que não conversam entre si) transformam o analista em um "auditor forense manual", perdendo semanas conferindo linha a linha notas fiscais, borderôs e extratos. Um único dado divergente pode gerar questionamentos severos, culminando em **glosa** (devolução do recurso corrigido ao erário) e deixando a instituição inidônea para novos convênios.

### Pergunta de análise
> **Como automatizar a validação e o cruzamento de dados contratuais e financeiros para mitigar o risco de glosas e garantir a conformidade em prestações de contas de convênios público-privados?**

### Para quem é útil
* **Equipes Financeiras e de Compliance:** Para monitoramento de saldos, prazos de vigência e fluxo de recursos.
* **Auditores, analistas e Gestores de Convênios:** Para mitigar riscos regulatórios, evitar glosas e agilizar análises de conformidade.
* **Tomadores de Decisão (Diretoria):** Que precisam de painéis executivos com métricas claras e confiáveis sobre o volume de recursos sob gestão.

### Escopo
* Centralização e tratamento de bases de dados contratuais e financeiras (via arquivos abertos/estruturados).
* Desenvolvimento de dashboard interativo em Streamlit com indicadores de desempenho (KPIs) e filtros dinâmicos por período, fornecedor, status e departamento.
* Geração automatizada de alertas de vencimentos críticos e cruzamentos numéricos para auditoria prévia.

### Resultados esperados e critério de conclusão
* **Redução do tempo operacional:** Substituição de conferências manuais e planilhas descentralizadas por um painel web instantâneo.
* **Mitigação de riscos:** Identificação antecipada de divergências e prazos de vencimento para evitar sanções e glosas.
* **Critério de conclusão:** Sistema funcional publicado no Streamlit Cloud, devidamente integrado com a base de dados tratada, código versionado no GitHub e documentado de forma clara para acesso e reprodução.

---

## 2. O que é este Projeto? 

Se você nunca trabalhou com programação ou análise de dados, pense neste projeto como a criação de um **painel inteligente de controle** para uma empresa.

Originalmente, as informações sobre contratos (valores, prazos, fornecedores e setores) costumam ficar espalhadas em planilhas do Excel ou documentos em PDF. Este projeto pega essa "montanha de dados", organiza automaticamente e transforma em uma página web interativa (o Dashboard).

Nele, qualquer pessoa consegue ver em segundos quantos contratos estão ativos, quanto dinheiro está comprometido e quais contratos estão prestes a vencer, evitando prejuízos financeiros e multas.

---

## 3. Dicionário de Dados

O dicionário de dados é o guia que explica o significado de cada coluna presente na tabela de dados utilizada pelo sistema (`data/contratos.csv`):

| Nome da Coluna | Tipo de Dado | O que significa este campo? | Exemplo de Conteúdo |
| :--- | :--- | :--- | :--- |
| `id_contrato` | Texto / Numérico | Código identificador único e exclusivo de cada contrato no sistema. | `CTR-2024-001` |
| `fornecedor` | Texto | Nome da empresa parceira, fornecedora ou prestadora do serviço. | `Empresa Tech Ltda` |
| `objeto_contrato` | Texto | Descrição resumida do serviço contratado ou produto adquirido. | `Manutenção de Servidores` |
| `valor_total` | Decimal (`float`) | Valor financeiro total que a instituição pagará ao longo do contrato (R$). | `150000.00` |
| `data_inicio` | Data (`YYYY-MM-DD`) | Data oficial em que o contrato passa a ter validade jurídica. | `2024-01-15` |
| `data_fim` | Data (`YYYY-MM-DD`) | Data oficial em que o contrato expira se não for renovado. | `2025-01-15` |
| `status` | Texto | Situação atual do contrato (`Ativo`, `Em Renovação`, `Encerrado`). | `Ativo` |
| `departamento` | Texto | Setor interno responsável pela gestão do contrato. | `Tecnologia da Informação` |

---

## 4. Arquitetura e Estrutura de Arquivos

Para entender como este projeto está organizado no seu computador, veja o mapa abaixo. Cada pasta e arquivo tem uma função específica para o funcionamento do sistema:

```text
GCP_Gestao_Contratos/
│
├── data/                      # PASTA DE DADOS
│   └── contratos.csv          # Arquivo contendo a tabela de dados com as informações dos contratos.
│
├── venv/                      # AMBIENTE VIRTUAL (Isolamento)
│                              # Pasta gerada automaticamente onde o Python guarda as ferramentas
│                              # e bibliotecas necessárias para este projeto rodar.
│                              # NOTA: Ela não precisa (e nem deve) ser enviada para o GitHub.
│
├── app.py                     # ARQUIVO PRINCIPAL DO SISTEMA
│                              # É o "cérebro" do projeto. Contém o código Python que lê os dados,
│                              # processa os cálculos e desenha a página web do Dashboard.
│
├── requirements.txt           # LISTA DE INGREDIENTES (Dependências)
│                              # Arquivo de texto simples que lista o nome e a versão exata de
│                              # todas as bibliotecas que o Python precisa instalar para rodar o app.py.
│
├── .gitignore                 # ARQUIVO DE REGRAS DO GIT
│                              # Diz ao Git quais pastas e arquivos temporários ou pesados (como a venv)
│                              # devem ser ignorados na hora de salvar o projeto na nuvem.
│
└── README.md                  # MANUAL DE INSTRUÇÕES (Este documento)
                               # Guia explicativo completo sobre o objetivo, instalação e uso do projeto.
```

---

## 5. Tecnologias e Bibliotecas Utilizadas

* **Python 3.10+** — Linguagem de programação principal utilizada para toda a lógica e processamento de dados do sistema.
* **Streamlit** — Framework open-source para a criação rápida e publicação da interface web interativa do dashboard executivo.
* **Pandas** — Biblioteca fundamental voltada para a manipulação, limpeza, filtragem e tratamento estruturado dos dados tabulares.
* **Plotly Express** — Biblioteca especializada na construção de gráficos dinâmicos, interativos e visuais de alta qualidade.
* **Virtualenv (`venv`)** — Módulo nativo do Python utilizado para o isolamento seguro e controle das dependências do ambiente de desenvolvimento.

---

## 6. Guia Passo a Passo Completo de Instalação e Execução

Instruções detalhadas para reprodução e execução do ambiente em qualquer máquina local.

### Pré-requisitos
* Ter o Python 3.10+ instalado ([Download](https://www.python.org/downloads/)). Dica: no Windows, marque a opção "Add Python to PATH".
* Ter o Git instalado (opcional) ([Download](https://git-scm.com/)).

### Passo 1: Baixar ou Clonar o Repositório
Abra o terminal e execute:

```bash
git clone https://github.com/seu-usuario/GCP_Gestao_Contratos.git
cd GCP_Gestao_Contratos
```

Caso não use o Git, baixe o arquivo `.zip` na página do repositório no GitHub e extraia a pasta.

### Passo 2: Criar o Ambiente Virtual (`venv`)
Na raiz da pasta do projeto, execute no terminal:

* **Windows:** `python -m venv venv`
* **macOS / Linux:** `python3 -m venv venv`

### Passo 3: Ativar o Ambiente Virtual
* **Windows (Prompt de Comando):** `venv\Scripts\activate.bat`
* **Windows (PowerShell):** `venv\Scripts\Activate.ps1`
* **macOS / Linux:** `source venv/bin/activate`

### Passo 4: Instalar as Dependências
Com o ambiente virtual ativado `(venv)`, instale os pacotes necessários:

```bash
pip install -r requirements.txt
```

### Passo 5: Executar o Dashboard
Inicie a aplicação executando:

```bash
streamlit run app.py
```

O navegador abrirá automaticamente no endereço local: `http://localhost:8501`.

---

## 7. Como Utilizar o Dashboard (Guia do Usuário)

1. **Filtros Laterais:** Utilize os seletores de período, fornecedores e departamentos para refinar o escopo dos dados exibidos no painel.
2. **Indicadores Executivos (KPIs):** Acompanhe o volume financeiro total sob gestão e o quantitativo de contratos vigentes em tempo real.
3. **Gráficos Interativos:** Analise visualmente a distribuição de custos por setor e o fluxo temporal de vencimentos dos contratos.
4. **Tabela de Auditoria:** Consulte os dados detalhados linha a linha com opções avançadas de ordenação por colunas.

---

## 8. Próximos Passos de Desenvolvimento

Sequência prevista de evolução do projeto, alinhada às premissas definidas na documentação inicial:

* **Passo A — Refinamento da Camada de Dados (`app.py`):** implementação de tratamentos robustos de conversão de datas e tratamento de valores nulos com `pandas`, para evitar falhas no carregamento de bases abertas reais.
* **Passo B — Validação de Regras de Negócio (Mitigação de Glosas):** inclusão de lógicas automáticas para identificação de prazos de vencimento em janelas críticas (30, 60 e 90 dias), alinhadas ao contexto de auditoria e prestação de contas.
* **Passo C — Aprimoramento Visual do Dashboard:** estruturação dos componentes do Streamlit com métricas customizadas e layout responsivo, focado na clareza executiva.
* **Passo D — Preparação para Deploy:** validação final do arquivo `requirements.txt` e testes de integridade local, visando a publicação no Streamlit Cloud.

---

## 9. Solução de Problemas Comuns (Troubleshooting)

* **Erro `'streamlit' não reconhecido`:** certifique-se de que o ambiente virtual está ativado (`venv`) e de que você executou o comando de instalação das dependências (`pip install -r requirements.txt`).
* **Bloqueio de script no PowerShell:** se o Windows bloquear a ativação do ambiente virtual, abra o PowerShell como Administrador e execute:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```
