from dataclasses import dataclass

@dataclass(frozen=True)
class RulesConfig:
    # Semana operativa: Lunes(0) a Sábado(5)
    days_open = [0, 1, 2, 3, 4, 5]

    # Ventanas de no repetición (contra historial real)
    repeat_window_days = 20
    pasta_repeat_window_days = 15

    # Sábado: complemento en duda -> lo dejamos configurable
    saturday_has_complemento = False

    # Rotación de ensaladas (slots)
    salad_map = {
        0: "ensalada_A",  # lunes
        1: "ensalada_B",  # martes
        2: "ensalada_C",  # miércoles
        3: "ensalada_A",  # jueves
        4: "ensalada_B",  # viernes
        5: "ensalada_C",  # sábado
    }

CFG = RulesConfig()
