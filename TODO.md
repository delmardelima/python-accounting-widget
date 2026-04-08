[x] Modo Compacto Inteligente: Ao colapsar, mostrar apenas um pequeno contador de "Tarefas Pendentes para Hoje".
[ ] Task Details (Slide-over): Ao clicar em uma tarefa, abrir um painel lateral (sem fechar a lista) para ver descrição detalhada e observações do escritório.
[ ] Quick Add Hero: Atalho global (ex: Ctrl + Alt + T) para trazer o widget para frente e focar no campo de nova tarefa.
[x] Diferenciação Visual de Origem: - 🏢 Ícone de prédio para tarefas do Escritório. 👤 Ícone de usuário para tarefas Particulares.
[ ] Feedback de Conclusão: Efeito de "riscado" (strikethrough) suave e som discreto de sucesso ao marcar tarefas.

Formulário de Criação (Melhorado)
[ ] Smart Input: Reconhecer tags como #urgente ou @escritorio diretamente no texto para evitar cliques extras.
[ ] Data de Vencimento: Adicionar um seletor de data rápido (Hoje, Amanhã, Próxima Segunda).
[ ] Anexos/Links: Permitir colar um link (ex: link do sistema contábil ou documento) que se torna clicável no card da tarefa.

Notificações do Windows

[ ] Native Toast Notifications: Substituir alertas de texto simples por notificações nativas do Windows com botões de ação:
[Botão: Concluir Agora]
[Botão: Adiar 15min]
[ ] Resumo Matinal: Uma notificação única às 08:30 com o resumo: "Você tem 5 tarefas para hoje, sendo 2 urgentes".
[ ] Alerta de Inatividade: Se o usuário não concluiu nada em 4h, enviar um lembrete motivador.

Funcionalidades de Escritório (Core Team)
[ ] Sinalizador de "Em Andamento": Botão de play/pause no card para indicar que o usuário começou a trabalhar naquela tarefa (útil para o gestor via API).
[ ] Filtro de "Delegado por Mim": Ver tarefas que o usuário criou para outros membros (se a API suportar).

Melhorias Técnicas & Sincronização
[ ] Modo Offline Resiliente: Melhorar a indicação visual de "Sincronizando..." vs "Offline" para o usuário não ter medo de perder dados.
[ ] Auto-Update do Widget: Mecanismo para o widget se atualizar sozinho quando houver nova versão (importante para deploy em equipe).

Configurações & Experiência
[ ] Configuração de "Horário de Trabalho": Permitir ao usuário definir 08:00-12:00 e 13:00-18:00 para que o widget saiba quando "cobrar" atenção.
[ ] Backup Local Automático: Garantir que o SQLite faça backup diário em uma pasta oculta para evitar perda de dados em caso de falha do Windows.

