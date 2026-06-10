"""Base de protocolos médicos simulados — populada na inicialização."""

from __future__ import annotations

PROTOCOLOS_SEED = [
    {
        "codigo": "PCR-001",
        "titulo": "Protocolo de PCR / SAVC",
        "descricao": (
            "Acionar equipe de emergência imediatamente. Iniciar compressões torácicas, "
            "obter via aérea avançada e desfibrilador. Notificar UTI cardiológica. "
            "Tempo-alvo: chegada da equipe em < 90s."
        ),
        "severidade": "CRITICO",
        "gatilhos": [
            {"campo": "frequencia_cardiaca", "op": ">=", "valor": 160},
            {"campo": "frequencia_cardiaca", "op": "<=", "valor": 40},
            {"campo": "spo2", "op": "<", "valor": 88},
            {"campo": "probabilidade", "op": ">=", "valor": 0.85},
        ],
    },
    {
        "codigo": "SCA-002",
        "titulo": "Síndrome Coronariana Aguda — manejo inicial",
        "descricao": (
            "Administrar AAS 300mg mastigado, monitorar ECG de 12 derivações, "
            "obter acesso venoso, dosar troponina seriada e encaminhar para hemodinâmica "
            "se elevação ST persistente. Não usar nitrato se PA sistólica < 90."
        ),
        "severidade": "ALTO",
        "gatilhos": [
            {"campo": "dor_toracica", "op": "==", "valor": True},
            {"campo": "historico_infarto", "op": "==", "valor": True},
            {"campo": "probabilidade", "op": ">=", "valor": 0.55},
        ],
    },
    {
        "codigo": "ARR-003",
        "titulo": "Manejo de arritmia sintomática",
        "descricao": (
            "Realizar ECG completo, avaliar estabilidade hemodinâmica, considerar "
            "cardioversão elétrica se instável. Em FA com RVR estável, considerar "
            "betabloqueador IV; reavaliar resposta em 30 min."
        ),
        "severidade": "ALTO",
        "gatilhos": [
            {"campo": "historico_arritmia", "op": "==", "valor": True},
            {"campo": "frequencia_cardiaca", "op": ">=", "valor": 130},
        ],
    },
    {
        "codigo": "HAS-004",
        "titulo": "Crise hipertensiva — urgência/emergência",
        "descricao": (
            "Se PAS ≥ 180 ou PAD ≥ 120 com lesão de órgão-alvo: emergência hipertensiva, "
            "reduzir PA em 20-25% em 1h com anti-hipertensivo IV. Sem lesão: urgência, "
            "redução gradual em 24-48h via oral."
        ),
        "severidade": "ALTO",
        "gatilhos": [
            {"campo": "pressao_sistolica", "op": ">=", "valor": 180},
            {"campo": "pressao_diastolica", "op": ">=", "valor": 115},
        ],
    },
    {
        "codigo": "HIPO-005",
        "titulo": "Hipotensão sintomática",
        "descricao": (
            "Posição de Trendelenburg, oxigênio suplementar, expansão volêmica com "
            "cristaloide 500ml em bolus. Pesquisar causa (sepse, hemorragia, choque "
            "cardiogênico). Reavaliar PA a cada 5 minutos."
        ),
        "severidade": "MODERADO",
        "gatilhos": [
            {"campo": "pressao_sistolica", "op": "<", "valor": 95},
        ],
    },
    {
        "codigo": "DM-006",
        "titulo": "Descompensação glicêmica",
        "descricao": (
            "Hiperglicemia (>250): hidratação, insulina regular conforme protocolo. "
            "Hipoglicemia (<60): glicose 50% IV ou carboidrato VO se consciente. "
            "Reavaliar em 15 minutos."
        ),
        "severidade": "MODERADO",
        "gatilhos": [
            {"campo": "glicemia", "op": ">=", "valor": 250},
            {"campo": "glicemia", "op": "<=", "valor": 60},
        ],
    },
    {
        "codigo": "MON-007",
        "titulo": "Monitorização cardiológica ambulatorial",
        "descricao": (
            "Holter 24h, MAPA, dosagem de perfil lipídico e função renal. "
            "Reforço de adesão a medicação anti-hipertensiva e estatina. "
            "Reavaliação clínica em 7 dias."
        ),
        "severidade": "MODERADO",
        "gatilhos": [
            {"campo": "probabilidade", "op": ">=", "valor": 0.30},
            {"campo": "tabagista", "op": "==", "valor": True},
            {"campo": "diabetico", "op": "==", "valor": True},
        ],
    },
    {
        "codigo": "EDU-008",
        "titulo": "Orientação preventiva e educação em saúde",
        "descricao": (
            "Reforçar hábitos saudáveis: atividade física moderada 150 min/semana, "
            "dieta DASH, cessação do tabagismo, controle de estresse. "
            "Retorno em 30 dias para nova avaliação."
        ),
        "severidade": "BAIXO",
        "gatilhos": [
            {"campo": "probabilidade", "op": "<", "valor": 0.30},
        ],
    },
    {
        "codigo": "OPS-009",
        "titulo": "Plano de contingência operacional",
        "descricao": (
            "Carga do sistema elevada e recursos limitados: ativar fila prioritária, "
            "alocar ambulância de retaguarda e notificar central de regulação. "
            "Reavaliar paciente a cada 10 minutos enquanto aguarda."
        ),
        "severidade": "ALTO",
        "gatilhos": [
            {"campo": "carga_sistema", "op": ">=", "valor": 0.7},
            {"campo": "recursos_disponiveis", "op": "<=", "valor": 0.4},
            {"campo": "probabilidade", "op": ">=", "valor": 0.4},
        ],
    },
]
