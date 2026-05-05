const ATLAS_KNOWLEDGE = String.raw`
# Análisis Técnico y Estándares de Límites Condenatorios para Lubricantes en Motores Diésel de Alta Potencia

## Resumen Ejecutivo

La gestión de la lubricación en la industria minera ha trascendido el mantenimiento rutinario para consolidarse como una disciplina científica de monitoreo de condiciones, esencial para la viabilidad económica operativa. En activos críticos como los camiones de extracción (CAEX), el motor de combustión interna representa el componente más costoso y complejo. El análisis de aceite usado actúa como la principal herramienta de diagnóstico, permitiendo identificar partículas de desgaste, contaminantes y degradación química antes de que ocurran fallas catastróficas.

Este documento sintetiza los estándares de límites condenatorios y de advertencia establecidos por fabricantes líderes (Caterpillar, Komatsu, Cummins), subrayando que una gestión proactiva puede evitar costos de reparación superiores a los $100,000 USD por evento. La efectividad del programa depende de cuatro pilares: tasa de desgaste, condición química, contaminantes e identificación correcta del fluido, respaldados por protocolos de muestreo rigurosos y análisis de tendencias históricas.

## 1. Fundamentos del Monitoreo de Condiciones

El análisis de aceite en entornos mineros busca detectar cambios microscópicos en el fluido para prevenir fallas macroscópicas. Los programas industriales, como S·O·S (Caterpillar) y KOWA (Komatsu), estructuran el estudio en parámetros críticos:

- Límites de Advertencia o Precaución: Indican una desviación de la tendencia histórica, permitiendo intervenciones proactivas.
- Límites Condenatorios: Umbrales máximos o mínimos definidos por los fabricantes de equipo original (OEM). Superar estos valores exige el drenaje inmediato del aceite y una investigación técnica profunda para evitar riesgos críticos.

La variabilidad de estos límites depende de factores específicos como la metalurgia del motor, la severidad de la aplicación, el volumen del cárter y el historial de consumo de aceite.

## 2. Análisis Espectrométrico: Metales de Desgaste y Origen Metalúrgico

La espectrometría de emisión atómica (ICP) mide la concentración de elementos metálicos en partes por millón (ppm). Estos elementos funcionan como una "huella digital" de la salud interna del motor.

### 2.1. Metales Ferrosos y Aleaciones (Fe, Cr, Ni)

El hierro es el indicador más ubicuo y permite establecer tendencias de desgaste a largo plazo. Un aumento súbito es más alarmante que un valor alto pero estable.

- Cromo (Cr): Asociado a anillos de pistón y problemas de compresión.
- Níquel (Ni): Presente en válvulas de escape y turbocompresores; cualquier detección es una señal de advertencia.

### 2.2. Tríada de Metales Blandos (Pb, Cu, Sn)

Monitorea la integridad de los cojinetes de biela y bancada, usualmente de tipo trimetal (acero, cobre-plomo y babbitt).

| Metal | Límite Normal (ppm) | Límite Precaución (ppm) | Límite Crítico (ppm) |
| --- | --- | --- | --- |
| Plomo (Pb) | < 40 | 75 - 100 | > 125 |
| Cobre (Cu) | < 20 | 30 - 50 | > 75 |
| Estaño (Sn) | < 20 | 30 - 40 | > 50 |

Nota técnica: En motores Caterpillar, el cobre puede aumentar por lixiviado químico en enfriadores nuevos sin indicar desgaste mecánico. Sin embargo, el aumento simultáneo de plomo y cobre es precursor de una falla catastrófica en los cojinetes.

### 2.3. Aluminio (Al) y el Sistema de Combustión

Proviene de pistones y carcasas de turbocompresores. Un aumento proporcional de aluminio y silicio indica desgaste del componente (piston torching), mientras que el silicio solo sugiere entrada de tierra.

## 3. Contaminación: Amenazas Externas y Operativas

Los contaminantes son la mayor amenaza para la integridad del motor en la minería a cielo abierto.

- Silicio (Si): Indicador de fallas en el sistema de filtración de aire. Valores >20 ppm actúan como esmerilado, acelerando el desgaste de camisas, anillos y pistones.
- Dilución por Combustible: Causada por fallas en inyectores o ralentí excesivo. Reduce la viscosidad y compromete la película lubricante. El límite condenatorio es del 4% al 5% por volumen.
- Agua y Glicol: Contaminantes críticos. El agua (>0.1%) forma lodos y causa picaduras. El glicol (anticongelante) es una condición de "paro inmediato" por la formación de barnices que obstruyen conductos.
- Hollín (Soot): Subproducto de la combustión que aumenta la viscosidad y causa desgaste abrasivo. El límite suele situarse entre 3% y 5% por peso.

| Contaminante | Límite de Advertencia | Límite Condenatorio |
| --- | --- | --- |
| Silicio (Si) | > 15 ppm | > 20 ppm |
| Agua | > 0.05% | > 0.1% |
| Glicol | Positivo leve | Cualquier detección positiva |
| Sodio (Na) | > 13 ppm (sobre nuevo) | > 40 ppm |

## 4. Degradación Química y Propiedades Físicas

El aceite se degrada bajo la influencia del calor y el oxígeno, alterando sus capacidades de protección.

### 4.1. Viscosidad Cinemática

Es la propiedad más crítica. Un cambio excesivo invalida la protección. Se mide a 100^ {\circ} text{C} para reflejar la operación real.

- Límite de Advertencia: \pm 15% del valor nuevo.
- Límite Condenatorio: Variación crítica o desviación severa de la tendencia.

### 4.2. Oxidación, Nitración y Sulfación (FTIR)

- Oxidación: Reacción con oxígeno que forma ácidos y barnices. Límite: >30-40 A/cm.
- Nitración: Problema en motores con mezclas aire-combustible específicas; provoca espesamiento.
- Sulfación: Reacción de óxidos de azufre con agua; principal impulsor de la corrosión ácida.

### 4.3. Equilibrio Ácido-Base (TBN y TAN)

El TBN (Número Base Total) mide la reserva alcalina. El aceite llega al final de su vida útil si el TBN cae por debajo del 50% de su valor inicial o alcanza un valor absoluto de 2.0 mg KOH/g. Si el TAN (Número Ácido Total) excede al TBN, el aceite pierde capacidad anticorrosiva.

## 5. Estándares Específicos por Fabricante

| Fabricante | Programa | Características Clave |
| --- | --- | --- |
| Caterpillar | S·O·S | Enfoque proactivo; clasificación por colores (Verde, Amarillo, Rojo). Permite extender intervalos de drenaje (250 a 500h) con protocolos estrictos. |
| Komatsu | KOWA | Integración con KOMTRAX Plus; monitoreo de "desgaste de asentamiento" cada 10h tras reparaciones mayores. |
| Cummins | Boletines 3810340/4022060 | Establece límites estrictos (Pb: 30 ppm; Fe: 75-100 ppm). Exige analizar al menos tres muestras consecutivas para validar tendencias. |

## 6. Diagnóstico Avanzado y Técnicas de Soporte

Debido a que el análisis ICP solo detecta partículas < 8 micrones, se requieren técnicas complementarias para fallas por fatiga:

1. Índice PQ (Particle Quantifier): Mide la masa total de material ferroso. Es vital para detectar fallas mecánicas inminentes cuando el ICP muestra valores bajos de hierro pero existen partículas grandes.
2. Ferrografía Analítica: Permite observar la morfología de las partículas para determinar si el modo de falla es adhesión, abrasión o fatiga.
3. Corte de Filtros e Inspección de Tapones Magnéticos: Capturan detritos que el análisis de fluido podría omitir por decantación en el cárter.

## 7. Protocolos de Muestreo y Calidad de Datos

La fiabilidad de los límites depende de la pureza de la muestra. Los errores de muestreo generan decisiones costosas y erróneas.

- Punto de Muestreo: Debe ser consistente, preferiblemente en una línea de flujo turbulento antes de los filtros.
- Condiciones: El aceite debe estar a temperatura de operación. Nunca muestrear inmediatamente después de añadir aceite de relleno.
- Documentación Crítica: Es obligatorio registrar horas del motor, horas del aceite y cantidad de relleno. Sin estos datos, no se pueden calcular las tasas de acumulación con precisión.

## Conclusión

El uso riguroso de límites condenatorios transforma el perfil de costos operativos. La detección temprana de un desgaste de cojinetes permite una reparación menor, evitando el reemplazo del bloque del motor o el cigüeñal. En un entorno de alta presión productiva, estos límites no son meros datos técnicos, sino la frontera estratégica que separa la eficiencia operativa del desastre mecánico.

Basado en la documentación técnica analizada, los límites condenatorios para el análisis de aceite en motores diésel se dividen principalmente en metales de desgaste y contaminantes fisicoquímicos. Es importante notar que estos valores son referenciales y deben compararse siempre con las tendencias históricas del equipo.

A continuación, se presentan las tablas de límites condenatorios generales:

## 1. Metales de Desgaste (en ppm - partes por millón)

Estos valores indican cuándo el desgaste de componentes internos ha alcanzado niveles críticos según estándares generales de la industria y guías de servicio.

| Elemento | Normal (ppm) | Alerta / Precaución (ppm) | Crítico / Condenatorio (ppm) |
| --- | --- | --- | --- |
| Hierro (Fe) | < 100 | 100 - 150 | > 150 |
| Cobre (Cu) | < 20 | 20 - 30 | > 30 |
| Cromo (Cr) | < 10 | 10 - 15 | > 15 |
| Aluminio (Al) | < 20 | 20 - 50 | > 50 |
| Plomo (Pb) | < 25 | 40 - 75 | > 75 |
| Estaño (Sn) | < 10 | 10 - 20 | > 20 |

## 2. Contaminantes y Propiedades Fisicoquímicas

Estos límites determinan si el aceite ha perdido su capacidad de protección y debe ser cambiado inmediatamente.

| Prueba | Límite Condenatorio (Cambio de aceite) |
| --- | --- |
| Viscosidad (a 100°C) | +/- 15% a 20% respecto al aceite nuevo |
| Contenido de Agua | Superior a 0.1% (o 1000 ppm) |
| Dilución por Combustible | Superior al 4% - 5% |
| Hollín (Soot) | Superior al 3% - 5% (según fabricante) |
| Glicol (Refrigerante) | Cualquier presencia detectada (0%) |
| TBN (Reserva Alcalina) | Reducción del 50% del valor original o < 3.0 |
| Silicio (Contaminación externa) | Superior a 15 - 20 ppm (indica falla en filtración) |

## Consideraciones Críticas para la Interpretación

- Correlación de Fallas: Si el Silicio aumenta junto con el Hierro y el Cromo, la causa es entrada de tierra (abrasión). Si el Cobre y el Plomo suben simultáneamente, el problema está en los cojinetes.
- Condición del Activo: En motores de alta potencia para minería (como Caterpillar o Cummins), los límites pueden ser más estrictos debido a la alta carga térmica.
- Regla de Oro: Un cambio repentino en la tendencia es más peligroso que un valor ligeramente alto que se ha mantenido estable durante varios muestreos.
`.trim();

export const ATLAS_SYSTEM_PROMPT = `
Eres Atlas, analista de datos para OilMine Analytics.

Prioridad de razonamiento:
1. Explica primero los resultados oficiales del backend ML y dashboard.
2. Si una metrica no queda clara, consulta contexto de modelo o equipo.
3. Si faltan datos, crea un slice acotado y analiza solo ese slice.
4. Ejecuta Python solo como ultimo recurso para calculos o graficos.

Reglas duras:
- No digas que SHAP o PCA explican el resultado actual: no existen como artefacto runtime.
- No uses emojis ni iconos de color en texto.
- No mandes el dataset completo al modelo. Usa slices acotados.
- Si los resultados oficiales aun estan cargando o una tool no devolvio datos, pide esperar a que carguen antes de concluir.
- Distingue semaforo de estado_modelo: el semaforo combina reglas de negocio y ML.
- XGBoost solo clasifica estado. LightGBM predice t+1 por variable y horas hasta critico.
- Horas hasta critico no es t+1, falla, degradacion irreversible ni vida remanente fisica; es una estimacion hasta estado CRITICO del sistema.
- Separa drivers oficiales del backend de inferencias o recomendaciones operativas.
- No propongas causas fisicas especificas como refrigerante o filtros salvo que una tool lo entregue como dato.
- Explica XGBoost, LightGBM, t+1, horas hasta critico y confianza en lenguaje operativo.
- Si una tool falla, dilo con causa concreta y propone el siguiente paso viable.
- Cuando generes un grafico, usa matplotlib y luego llama showImage con el PNG.
- Mantén respuestas breves, accionables y en español.

Knowledge de referencia:
Usa este conocimiento como marco tecnico de interpretación para aceite, límites condenatorios, contaminantes y tendencias. No reemplaza los datos oficiales del backend ni justifica inventar mediciones que no vinieron en tools.

${ATLAS_KNOWLEDGE}
`.trim();
