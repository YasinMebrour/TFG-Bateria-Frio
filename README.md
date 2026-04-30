# TFG-Bateria-Frio

Sistema de gemelo digital para la supervision, prediccion y optimizacion energetica de una instalacion de frio industrial con apoyo de bateria. El proyecto integra datos historicos y en tiempo real, visualizacion web, planificacion de modos de ahorro y un modulo de inteligencia artificial orientado a anticipar el consumo.

## Resumen del proyecto

Este Trabajo de Fin de Grado propone una plataforma software para mejorar la toma de decisiones en sistemas de refrigeracion industrial. La aplicacion permite consultar el estado de la instalacion, analizar consumos, detectar eventos criticos y generar planificaciones de ahorro energetico a partir de datos almacenados en InfluxDB y PostgreSQL.

El objetivo principal es demostrar como un gemelo digital puede ayudar a reducir costes, anticipar comportamientos y facilitar una operacion mas eficiente de equipos de frio, combinando monitorizacion, analitica de datos, automatizacion y modelos predictivos.

## Caracteristicas principales

- Panel web para visualizar variables energeticas y operativas.
- Gemelo digital con graficas, indicadores y eventos criticos.
- Modulo de planificacion para definir intervalos de modo ahorro.
- Prediccion de consumo mediante un servicio independiente de IA.
- API backend con FastAPI para autenticacion, usuarios, tarifas, planificacion y consulta de datos.
- Integracion con InfluxDB para series temporales y PostgreSQL para datos persistentes.
- Tareas periodicas con Celery y Redis.
- Notificaciones configurables por Telegram.
- Despliegue local mediante Docker Compose.

## Arquitectura

El repositorio esta dividido en tres bloques principales:

- `tfg_bateria_frontend`: interfaz web en React para el usuario final.
- `tfg_bateria_backend`: API principal en FastAPI, persistencia, autenticacion, planificacion y servicios de negocio.
- `tfg_bateria_backend_ia`: microservicio FastAPI dedicado a inferencia y prediccion de consumo.

Servicios auxiliares:

- `PostgreSQL`: almacenamiento relacional.
- `Redis`: broker para Celery y comunicacion de tareas.
- `InfluxDB`: fuente de datos de series temporales.

## Tecnologias utilizadas

- Python, FastAPI, SQLAlchemy, Alembic y Celery.
- React, React Router, React Query, Chart.js y Plotly.
- PostgreSQL, Redis e InfluxDB.
- Docker y Docker Compose.
- Modelos de machine learning para prediccion de consumo.

## Puesta en marcha

Crea un archivo `.env` a partir de `.env.example` y rellena los valores locales:

```bash
POSTGRES_USER=myuser
POSTGRES_PASSWORD=tu_password_local
POSTGRES_DB=mydb
SECRET_KEY=una_clave_larga_y_segura
```

Arranque principal:

```bash
docker compose up --build
```

El frontend queda disponible en `http://localhost:3000` y la API principal en `http://localhost:8000`.

El modulo de IA puede levantarse desde su carpeta:

```bash
cd tfg_bateria_backend_ia
docker compose up --build
```

## Seguridad

El repositorio esta preparado para no publicar secretos locales. Los valores sensibles deben definirse en `.env` o variables de entorno, y `.env` esta excluido del control de versiones. El archivo `.env.example` solo contiene valores de ejemplo.

## Utilidad del proyecto

La solucion esta pensada como demostrador tecnico para entornos donde el consumo energetico es un factor critico. Su valor esta en unir datos, prediccion y planificacion en una unica herramienta operativa, facilitando decisiones mas rapidas y trazables sobre el uso de energia en instalaciones de frio.

## Mantenimiento

Predicciones generadas antes de la correccion de zona horaria pueden almacenar marcas temporales en hora local. Para convertir entradas existentes a UTC:

```bash
python tfg_bateria_backend/scripts/rebuild_predictions_utc.py
```
