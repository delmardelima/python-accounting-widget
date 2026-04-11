# **SageCont-Win — Widget de Tarefas**

O **SageCont-Win** é um widget de área de trabalho moderno, desenvolvido em Python e PyQt6, projetado especificamente para a rotina de escritórios de contabilidade. Ele oferece uma interface ágil e leve para o gerenciamento de demandas, com suporte a sincronização em nuvem e funcionamento offline.

## **✨ Funcionalidades**

* **Interface Fluent Design:** UI inspirada no Windows 11, com cantos arredondados, transparências e animações suaves.  
* **Temas Inteligentes:** Suporte a temas Claro e Escuro com detecção automática do tema do sistema operacional.  
* **Sincronização em Background:** SyncWorker dedicado que realiza o *push* de alterações locais e o *pull* de novas tarefas da API de forma assíncrona.  
* **Modo Tray:** Minimiza para a bandeja do sistema para economizar espaço, mantendo notificações ativas para tarefas urgentes.  
* **Drag-and-Drop:** Reordenação intuitiva de tarefas através de arrastar e soltar.  
* **Resiliência Offline:** Banco de dados SQLite local (modo WAL) que garante o funcionamento mesmo sem conexão com a internet.  
* **Filtros Avançados:** Filtragem rápida por tarefas "Minhas", "Escritório" ou de "Alta Prioridade".

## **🛠️ Tecnologias e Dependências**

* **Python 3.10+**  
* **PyQt6:** Interface gráfica.  
* **Requests:** Comunicação com a API REST.  
* **SQLite:** Persistência local de dados.  
* **Configparser:** Gestão de preferências do utilizador (config.ini).

## **🚀 Instalação e Execução**

1. **Clonar o Repositório:**  
   ```
   git clone https://github.com/delmardelima/python-accounting-widget.git  
   cd python-accounting-widget
   ```

2. **Criar e Ativar Ambiente Virtual (Recomendado):**  
   ```
   python -m venv venv  
   # No Windows:  
   venv\\Scripts\\activate
   ```

3. **Instalar Dependências:**  
   ```
   pip install PyQt6 requests
   ```
   ou
   ```
   pip install -r requirements.txt
   ```
4. **Executar a Aplicação:**  
   ```
   python main.py
   ```

## **⚙️ Configuração**

Ao iniciar pela primeira vez, o aplicativo criará um arquivo config.ini na raiz do projeto. Você pode configurar:

* **API URL:** Endereço do servidor de tarefas.  
* **API Key:** Chave de autenticação para sincronização.  
* **Opacidade:** Transparência da janela do widget.  
* **Sincronização:** Intervalo de tempo entre as actualizações.

## **📂 Estrutura do Código**

* <kbd>main.py</kbd>: Ponto de entrada e inicialização dos serviços.  
* <kbd>app/api_client.py</kbd>: Comunicação HTTP com o servidor.  
* <kbd>app/database.py</kbd>: Camada de persistência local SQLite.  
* <kbd>app/sync_worker.py</kbd>: Lógica de sincronização em thread separada.  
* <kbd>app/ui/</kbd>:  
  * <kbd>main_widget.py</kbd>: Janela principal e lógica da interface.  
  * <kbd>task_card.py</kbd>: Componente visual de cada tarefa individual.  
  * <kbd>styles.py</kbd>: Definições de QSS e paletas de cores (Dark/Light).  
  * <kbd>tray_icon.py</kbd>: Gestão do ícone na bandeja do sistema.


## **📦 Compilação e Geração do Instalador**

Para distribuir o aplicativo para os usuários finais, você não precisa enviar o código fonte. O projeto está configurado para ser compilado em um executável (.exe) e empacotado em um instalador do Windows.

### **Pré-requisitos para Build**

* **PyInstaller:** Usado para converter o código Python em um .exe autossuficiente.  
  ```
  pip install pyinstaller
  ```

* **Inno Setup (Windows):** Usado para criar o instalador profissional (setup.exe).  
  * Baixe e instale: [jrsoftware.org/isinfo.php](https://jrsoftware.org/isinfo.php)  

### **Gerando Manualmente**

**1. Gerar o Executável (.exe):**

No terminal, na raiz do projeto, execute:
```
pyinstaller --noconfirm --onedir --windowed --icon "imgs/sagecont-win.ico" --name "Sagecont-Win" main.py
```
*O executável será gerado na pasta dist/Sagecont-Win/.*

**2. Gerar o Instalador:**

Abra o arquivo instalador.iss no Inno Setup Compiler e clique em **Compile** (ou pressione Ctrl+F9).

*O instalador será gerado na pasta Instalador/.*

## **📄 Licença**

Este projeto está licenciado sob a **Licença MIT** \- consulte o arquivo [LICENSE](https://choosealicense.com/licenses/mit) para mais detalhes.

*Desenvolvido para optimização de produtividade em ambientes contabilísticos.*
