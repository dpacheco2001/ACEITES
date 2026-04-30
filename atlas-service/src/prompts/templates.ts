export const promptTemplates = {
  dashboard:
    'Explica el dashboard usando getDashboardResults y getModelContext antes de pedir slices.',
  equipment:
    'Para diagnosticar un equipo, usa getEquipmentResults. Solo crea slice si falta evidencia historica.',
  metric:
    'Para explicar una metrica, usa getModelContext y relaciona reglas, confianza y unidades operativas.',
  chart:
    'Para graficos, crea un slice acotado y ejecuta Python con matplotlib sobre ese slice.',
  eda:
    'El analisis exploratorio desde cero es ultimo recurso y debe justificar por que los resultados existentes no bastan.',
};
