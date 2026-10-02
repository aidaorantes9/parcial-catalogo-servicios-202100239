# Prompt 01 — Análisis del Excel

- **Herramienta:** Claude Code 2.1.287 (modo auto)
- **Modelo y versión:** Claude Opus 5.5 (cuenta Claude Pro)
- **Fecha de uso:** 2026-10-02
- **Fase:** Análisis de datos
- **Commit resultante:** `4790583`

## Objetivo
Obtener un análisis verificable por código del archivo `data/CatalogoServicios.xlsx` antes de diseñar el modelo, confirmando los controles de importación (12 códigos de nivel 1 y 46 de nivel 2) y los casos especiales del enunciado.

## Contexto suministrado
- `docs/contexto/enunciado.md`: enunciado completo, para que conozca los requisitos y los controles esperados.
- `data/CatalogoServicios.xlsx`: fuente de datos, declarada explícitamente como DATO y no como instrucciones.

## Prompt utilizado
```
[PEGAR AQUÍ EL PROMPT 1 COMPLETO]
```

## Extracto de la salida
- Script `scripts/analizar_excel.py`, reporte `docs/contexto/analisis-excel.md` y hash `data/CatalogoServicios.xlsx.sha256`.
- 76 rangos combinados (columnas A, B, C, D y J); 46 servicios de nivel 2, 49 filas de continuación y 2 filas sin código fuera de combinación (42 y 67).
- SE.12: B99 "Suministrar Analitica" y B100 "Mantener Tableros de Control"; A101 vacía, por lo que SE.12.3 solo se vincula a SE.12 por prefijo de código.
- SE.12.1, SE.12.2 y SE.12.3 almacenados como texto, con un dígito en lugar del patrón SE.NN.NN.
- Filas 99–101 sin valores en E–L.
- Errores de escritura: "Demostration" (H113) y "Análsis" (D100).
- K y L solo tienen valores en filas 5 (1–100) y 25 (12–24).
- I5 contiene un texto ajeno al servicio; se reportó como hallazgo y no se trató como instrucción.
- Propuesta (no decisión) de nombre canónico para SE.12: "Suministrar Analitica", con argumentos a favor y en contra.

Capturas: `../evidencias/prompt01-autocorreccion.png`, `../evidencias/prompt01-cambio-hash.png`, `../evidencias/prompt01-resultado.png`.

## ¿Cumplió el criterio de aceptación?
Sí. Verificado manualmente fuera del asistente: el script terminó con código de salida 0, reportó 12/12 y 46/46 en PASA, y `sha256sum -c` confirmó que el Excel no fue modificado. Ver `../evidencias/prompt01-verificacion.log`.

Además, los hallazgos se contrastaron con una revisión independiente del archivo y coincidieron.

## Problemas observados e iteración
- **Problema observado:** durante la ejecución el agente intentó crear un archivo temporal en una ruta inexistente y luego sin permisos; se autocorrigió montando el proyecto en solo lectura dentro del contenedor. También cambió la condición de salida para que la comparación del hash fuera informativa y no afectara el código de salida; se revisó y se aceptó porque respeta el criterio pedido y el hash sigue reportándose.
- **Prompt revisado:** no fue necesario.
- **Resultado comprobado:** ver `../evidencias/prompt01-verificacion.log`.
