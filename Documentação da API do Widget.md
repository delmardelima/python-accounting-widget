# **Documentação da API \- Widget Desktop (SageCont-Win)**

Esta documentação descreve os endpoints expostos pela aplicação web (Flask) para consumo exclusivo do Widget Desktop. O widget atua como uma extensão da plataforma, permitindo a sincronização e manipulação de tarefas, tickets de atendimento e solicitações de novos clientes.

## **🔐 Autenticação**

O Widget Desktop não utiliza sessões ou cookies. Toda requisição enviada para a API deve conter o cabeçalho X-API-Key com a chave gerada exclusivamente para o usuário na plataforma web.

**Cabeçalhos Obrigatórios (Headers):**

Content-Type: application/json  
X-API-Key: SUA\_CHAVE\_GERADA\_NA\_PLATAFORMA

*Nota: Se a chave for inválida ou não for enviada, a API retornará o status HTTP 401 Unauthorized com {"success": false, "message": "Usuário não identificado"}.*

## **📡 1\. Sincronização Geral de Demandas**

Retorna todas as demandas relevantes para o usuário conectado, consolidando **Tarefas Internas** (públicas do escritório e privadas do usuário), **Solicitações de Cadastro** (pendentes) e **Tickets de Atendimento** (abertos e em análise).

* **URL:** /tarefas/api/widget/sync  
* **Método:** GET  
* **Cabeçalho:** X-API-Key obrigatório

### **Resposta de Sucesso (200 OK)**

{  
  "success": true,  
  "tasks": \[  
    {  
      "id": "TASK-12",  
      "nome": "Conciliação Bancária",  
      "descricao": "Conciliar mês de Abril",  
      "prioridade": "media",  
      "escopo": "privada"  
    },  
    {  
      "id": "SOL-5",  
      "nome": "Solicitação de Acesso: João Silva",  
      "descricao": "Empresa: Silva ME",  
      "prioridade": "alta",  
      "escopo": "escritorio"  
    },  
    {  
      "id": "TK-89",  
      "nome": "Ticket: Dúvida sobre NF-e",  
      "descricao": "Setor: Fiscal",  
      "prioridade": "media",  
      "escopo": "escritorio"  
    }  
  \]  
}

### **Prefixos de ID (Muito Importante)**

O widget deve usar o prefixo retornado no id para saber como lidar com a demanda localmente:

* TASK-: Tarefas criadas internamente no escritório.  
* SOL-: Solicitações públicas de cadastro (novos clientes/acessos).  
* TK-: Tickets do módulo de atendimento ao cliente.

## **🚀 2\. Atualizar Status da Demanda (Concluir / Excluir)**

Permite que o widget marque qualquer demanda como concluída ou a exclua do sistema.

* **URL:** /tarefas/api/widget/task/\<task\_id\>/status  
* **Parâmetro da URL:** \<task\_id\> (deve incluir o prefixo, ex: TASK-12, SOL-5, TK-89)  
* **Método:** POST  
* **Cabeçalho:** X-API-Key obrigatório

### **Corpo da Requisição (JSON)**

| Parâmetro | Tipo | Descrição |
| :---- | :---- | :---- |
| status | string | Ação desejada. Valores aceitos: "concluida" ou "excluida". |

{  
  "status": "concluida"  
}

### **Comportamento no Servidor Web**

* **TASK- (Tarefas)**: concluida altera ativa=False. excluida deleta o registro do banco.  
* **SOL- (Solicitações)**: concluida avança o status do card para EM\_ANALISE para que a equipe dê continuidade via painel Web. excluida é ignorado.  
* **TK- (Tickets)**: concluida encerra o chamado mudando o status para Finalizado. excluida é ignorado.

### **Resposta de Sucesso (200 OK)**

{  
  "success": true  
}

## **✏️ 3\. Editar Informações da Tarefa**

Permite editar os dados básicos de uma tarefa. **Atenção:** Este endpoint aceita apenas a edição de Tarefas Internas (TASK-).

* **URL:** /tarefas/api/widget/task/\<task\_id\>/edit  
* **Parâmetro da URL:** \<task\_id\> (Ex: TASK-12)  
* **Método:** PUT  
* **Cabeçalho:** X-API-Key obrigatório

### **Corpo da Requisição (JSON)**

Qualquer campo não enviado será mantido com o valor atual no servidor.

| Parâmetro | Tipo | Descrição |
| :---- | :---- | :---- |
| nome | string | (Opcional) Novo título da tarefa |
| descricao | string | (Opcional) Nova descrição da tarefa |
| prioridade | string | (Opcional) Nova prioridade (baixa, media, alta) |

{  
  "nome": "Conciliação Bancária \- Atualizado",  
  "descricao": "Conciliar mês de Abril e Maio",  
  "prioridade": "alta"  
}

### **Respostas**

**Sucesso (200 OK):**

{  
  "success": true  
}

**Erro \- Prefixo Inválido (400 Bad Request):**

{  
  "success": false,  
  "message": "Somente tarefas internas do escritório podem ser editadas."  
}

## **💡 Guia de Implementação no Widget (ApiClient)**

1. **Header Fixo:** No seu app.api\_client.ApiClient do Widget, configure a sessão de requests (ex: requests.Session()) para injetar automaticamente o cabeçalho:  
   self.session.headers.update({  
       'Content-Type': 'application/json',  
       'X-API-Key': config.get("api", "api\_key")   
   })

2. **Fluxo do SyncWorker**:  
   * **Passo 1 (Upload local)**: O worker varre o banco SQLite local buscando tarefas editadas/concluídas enquanto estava sem internet (sincronizado \== 0). Ele envia essas alterações via POST .../status ou PUT .../edit.  
   * **Passo 2 (Download)**: Após enviar as alterações pendentes, ele faz o GET .../sync para baixar o estado real do servidor e atualizar o banco do PyQt6, garantindo que "Abertura de Empresa" (SOL-) apareça para todos.  
3. **Resiliência Offline**: Se o requests.get ou requests.post falhar (ex: ConnectionError), o Widget não deve travar. Ele simplesmente pula o sync e o usuário continua manipulando o banco SQLite local do PyQt6 até que a internet retorne.