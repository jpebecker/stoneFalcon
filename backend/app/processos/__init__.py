"""Processos (v8): fluxos de blocos de baixo código que usam agentes, plugins, dados e aprovações.

Um AGENTE é um trabalhador de IA reutilizável. Um PROCESSO é o fluxo de blocos de uma pessoa e de uma área, ligado
ao processo AS IS -> TO BE do roteiro dela. O processo tem o mesmo ciclo de vida do agente (versões imutáveis, revisão
da Segurança para risco alto, pausa de emergência, trilha encadeada) e roda no mesmo runtime de passos: os blocos
viram passos do runtime (app/processos/compilar.py).
"""
