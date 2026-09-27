# Plata Clara — Backend

Backend de **Plata Clara**, aplicación de finanzas personales desarrollada para Argentina.

API desarrollada en Python para gestionar autenticación, usuarios, movimientos financieros e integración con servicios externos.

## Tecnologías

* Python
* Flask
* Supabase / PostgreSQL
* REST API
* Gunicorn
* Railway
* Mercado Pago OAuth
* Groq API

## Arquitectura

El proyecto organiza la lógica de la API en diferentes componentes:

* `app.py` — punto de entrada de la aplicación Flask.
* `routes/` — endpoints y rutas de la API.
* `services/` — lógica de negocio e integración con servicios externos.
* `auth.py` — autenticación y protección de endpoints.
* `database.py` — acceso y operaciones sobre la base de datos.

## Integraciones

El backend integra servicios externos utilizados por Plata Clara, entre ellos:

* Supabase para persistencia y autenticación.
* Mercado Pago mediante OAuth para consultar información asociada a pagos.
* Groq para funcionalidades de inteligencia artificial.

## Deploy

La aplicación está preparada para ejecutarse mediante Gunicorn y fue desplegada utilizando Railway.

## Relación con Plata Clara

Este repositorio contiene exclusivamente el backend de la aplicación.

El cliente Android se encuentra en:

`plata-clara-android`

## Estado

Proyecto desarrollado como parte de Plata Clara.

La aplicación se encuentra actualmente pausada y sujeta a futuras mejoras.

## Autor

Juan Barreto

Portfolio: https://juan-barreto-portfolio.vercel.app/
GitHub: https://github.com/juan-barreto

## Licencia

Proyecto privado. Todos los derechos reservados. El código se publica con fines demostrativos y de portfolio.
